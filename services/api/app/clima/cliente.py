"""Cliente do Open-Meteo (Historical Weather API) atras de uma interface (ADR 0007, itens 4 e 6).

Recebe a posicao JA ARREDONDADA (2 casas) e o intervalo UTC da atividade e devolve o clima medio da atividade:
media ponderada pelo tempo de sobreposicao de cada hora cheia UTC com ``[inicio, inicio + duracao_s]``.

Privacidade: a chamada leva so latitude, longitude, datas, variaveis, unidade do vento e fuso. Nada que
identifique o atleta. O log nunca tem coordenada, URL completa nem corpo da resposta.
Weather data by Open-Meteo.com (CC BY 4.0).
"""

from __future__ import annotations

import logging
import math
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Literal, Protocol

import httpx

log = logging.getLogger(__name__)
# O httpx registra "HTTP Request: GET <url completa>" em INFO: isso vazaria a coordenada no log.
for _nome in ("httpx", "httpcore"):
    logging.getLogger(_nome).setLevel(logging.WARNING)

URL = "https://archive-api.open-meteo.com/v1/archive"
USER_AGENT = "treino-contexto/0.1 (app de analise de treinos)"
VARIAVEIS = ("temperature_2m", "apparent_temperature", "relative_humidity_2m", "wind_speed_10m")
TIMEOUT_S = 10.0
ESPERAS_S = (1.0, 2.0, 4.0)  # espera antes de cada nova tentativa (1 chamada + ate 3 repeticoes)
RETRY_AFTER_MAX_S = 60.0

Estado = Literal["ok", "pendente", "falha"]


@dataclass(frozen=True)
class ClimaMedio:
    temperatura_c: float
    sensacao_c: float
    umidade_pct: float
    vento_kmh: float


@dataclass(frozen=True)
class ResultadoClima:
    estado: Estado
    clima: ClimaMedio | None = None
    erro: str | None = None  # motivo curto (coluna `erro`): sem coordenada, URL nem corpo da resposta
    parar_rodada: bool = False  # 429 que persistiu depois das tentativas: a rodada deve parar (ADR item 6)


class ClienteClima(Protocol):
    def buscar(self, lat: float, lon: float, inicio: datetime, duracao_s: int | None) -> ResultadoClima: ...


class _Inconsistente(Exception):
    """Resposta que nao bate com o esperado (vira `falha`)."""


class ClienteOpenMeteo:
    """Cliente real. ``transporte`` (httpx.BaseTransport) e ``dormir`` sao injetaveis para os testes."""

    def __init__(
        self,
        transporte: httpx.BaseTransport | None = None,
        dormir: Callable[[float], None] = time.sleep,
    ) -> None:
        self._http = httpx.Client(
            transport=transporte,
            timeout=TIMEOUT_S,
            headers={"User-Agent": USER_AGENT},
        )
        self._dormir = dormir

    def fechar(self) -> None:
        self._http.close()

    # ------------------------------------------------------------------
    def buscar(self, lat: float, lon: float, inicio: datetime, duracao_s: int | None) -> ResultadoClima:
        if inicio.tzinfo is None:
            raise ValueError("inicio precisa ter fuso (UTC)")
        inicio = inicio.astimezone(timezone.utc)
        duracao = max(int(duracao_s or 0), 0)
        fim = inicio + timedelta(seconds=duracao)
        params = {
            "latitude": f"{lat:.2f}",
            "longitude": f"{lon:.2f}",
            "start_date": inicio.date().isoformat(),
            "end_date": fim.date().isoformat(),
            "hourly": ",".join(VARIAVEIS),
            "wind_speed_unit": "kmh",
            "timezone": "GMT",
        }
        resposta, erro = self._pedir(params)
        if resposta is None:
            return erro
        try:
            dados = resposta.json()
        except ValueError:
            return ResultadoClima("falha", erro="resposta nao e JSON")
        try:
            return self._calcular(dados, inicio, fim)
        except _Inconsistente as e:
            return ResultadoClima("falha", erro=str(e)[:200])

    # ------------------------------------------------------------------
    def _pedir(self, params: dict[str, str]) -> tuple[httpx.Response | None, ResultadoClima | None]:
        """Faz a chamada com as tentativas. Devolve (resposta 200, None) ou (None, resultado de erro)."""
        ultimo = "erro de rede"
        limitado = False
        for tentativa in range(len(ESPERAS_S) + 1):
            espera = ESPERAS_S[tentativa] if tentativa < len(ESPERAS_S) else None
            try:
                r = self._http.get(URL, params=params)
            except httpx.TimeoutException:
                ultimo, limitado = "tempo esgotado", False
            except httpx.TransportError as e:
                ultimo, limitado = f"erro de rede ({type(e).__name__})", False
            else:
                if r.status_code == 200:
                    return r, None
                if r.status_code == 429 or r.status_code >= 500:
                    ultimo, limitado = f"HTTP {r.status_code}", r.status_code == 429
                    espera = self._espera(r, espera)
                else:  # 400 e demais 4xx: bug ou parametro, nao instabilidade
                    log.warning("clima: HTTP %s do Open-Meteo, sem nova tentativa", r.status_code)
                    return None, ResultadoClima("falha", erro=f"HTTP {r.status_code}")
            if espera is None:
                break
            log.info("clima: %s, nova tentativa em %.0f s", ultimo, espera)
            self._dormir(espera)
        log.warning("clima: sem sucesso depois das tentativas (%s)", ultimo)
        return None, ResultadoClima("pendente", erro=ultimo, parar_rodada=limitado)

    @staticmethod
    def _espera(r: httpx.Response, padrao: float | None) -> float | None:
        """Retry-After (segundos, no maximo 60) vale no lugar da espera padrao; sem nova tentativa, nao espera."""
        valor = r.headers.get("Retry-After")
        if valor is None or padrao is None:
            return padrao
        try:
            segundos = float(valor)
        except ValueError:
            return padrao
        if not math.isfinite(segundos) or segundos < 0:
            return padrao
        return min(segundos, RETRY_AFTER_MAX_S)

    # ------------------------------------------------------------------
    @staticmethod
    def _calcular(dados: object, inicio: datetime, fim: datetime) -> ResultadoClima:
        if not isinstance(dados, dict) or not isinstance(dados.get("hourly"), dict):
            raise _Inconsistente("resposta sem hourly")
        hourly = dados["hourly"]
        tempos = hourly.get("time")
        if not isinstance(tempos, list) or not tempos:
            raise _Inconsistente("hourly sem time")
        series = {}
        for v in VARIAVEIS:
            s = hourly.get(v)
            if not isinstance(s, list):
                raise _Inconsistente(f"variavel faltando: {v}")
            if len(s) != len(tempos):
                raise _Inconsistente(f"tamanho de {v} diferente de time")
            series[v] = s
        indice = {}
        for i, t in enumerate(tempos):
            try:
                indice[datetime.fromisoformat(t).replace(tzinfo=timezone.utc)] = i
            except (TypeError, ValueError):
                raise _Inconsistente("time invalido") from None

        # Pesos: segundos de sobreposicao de cada hora cheia com [inicio, fim]. Duracao zero: hora do inicio.
        pesos: dict[datetime, float] = {}
        hora = inicio.replace(minute=0, second=0, microsecond=0)
        if fim <= inicio:
            pesos[hora] = 1.0
        else:
            while hora < fim:
                seg = (min(fim, hora + timedelta(hours=1)) - max(inicio, hora)).total_seconds()
                if seg > 0:
                    pesos[hora] = seg
                hora += timedelta(hours=1)

        if any(h not in indice for h in pesos):
            raise _Inconsistente("hora da atividade fora da resposta")
        total = sum(pesos.values())
        medias = {}
        nulo = False
        for v in VARIAVEIS:
            soma = 0.0
            for h, p in pesos.items():
                x = series[v][indice[h]]
                if x is None:
                    nulo = True
                    continue
                if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x):
                    raise _Inconsistente(f"valor invalido em {v}")
                soma += x * p
            medias[v] = soma / total
        if nulo:
            return ResultadoClima("pendente", erro="resposta com null na janela")
        return ResultadoClima(
            "ok",
            ClimaMedio(
                temperatura_c=medias["temperature_2m"],
                sensacao_c=medias["apparent_temperature"],
                umidade_pct=medias["relative_humidity_2m"],
                vento_kmh=medias["wind_speed_10m"],
            ),
        )
