"""Clima das atividades no banco (Meta 4, ADR 0007, itens 2, 3, 6, 7 e 8).

- `clima_da_atividade` / `estado_clima`: o que a API mostra. `indoor` e `sem_posicao` sao calculados aqui, na
  leitura, sem linha em `clima_atividade`.
- `preencher_clima`: busca o clima (sequencial, com pausa, um `commit` por atividade) e e idempotente.
- `preencher_posicoes`: relê o FIT guardado e a exportacao para preencher a posicao onde esta NULL.

Privacidade: o log e o relatorio so levam `atividade_id`, estado e contagens, nunca coordenada.
"""

from __future__ import annotations

import hashlib
import logging
import time
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Literal

from app.clima import ClienteClima
from app.config import pasta_fit
from app.db.models import Atividade, ClimaAtividade
from app.ingestao import fit_guardado
from app.ingestao.garmin import ler_atividade_fit, ler_exportacao
from app.ingestao.garmin.posicao import e_indoor
from app.ingestao.garmin.unidades import para_utc
from sqlalchemy import select
from sqlalchemy.orm import Session

log = logging.getLogger(__name__)

FONTE_CLIMA = "open-meteo-archive"
JANELA_ATRASO = timedelta(days=7)  # 5 dias de atraso da API + 2 de folga (item 4)
MAX_RODADAS = 5  # depois de 5 rodadas pendentes seguidas vira falha (item 6)
LIMITE_PADRAO = 500
PAUSA_S = 0.25
ESTADOS = ("ok", "indoor", "sem_posicao", "pendente", "falha")

EstadoClima = Literal["ok", "indoor", "sem_posicao", "pendente", "falha"]


@dataclass(frozen=True)
class ClimaDaAtividade:
    """O clima como a API o mostra. Os valores so existem em `ok`."""

    estado: EstadoClima
    temperatura_c: float | None = None
    sensacao_c: float | None = None
    umidade_pct: float | None = None
    vento_kmh: float | None = None


def entrada_de(a: Atividade) -> str:
    """SHA-256 de inicio (UTC, segundos), duracao (inteiro) e posicao (2 casas). Muda se qualquer um mudar."""
    inicio = para_utc(a.inicio).replace(microsecond=0).isoformat()
    texto = f"{inicio}|{int(a.duracao_s)}|{a.inicio_lat:.2f}|{a.inicio_lon:.2f}"
    return hashlib.sha256(texto.encode()).hexdigest()


def estado_clima(a: Atividade, linha: ClimaAtividade | None) -> ClimaDaAtividade:
    if e_indoor(a.subtipo):
        return ClimaDaAtividade("indoor")
    if a.inicio_lat is None or a.inicio_lon is None:
        return ClimaDaAtividade("sem_posicao")
    if linha is None or linha.entrada != entrada_de(a):  # nunca consultada, ou a consulta e de outra entrada
        return ClimaDaAtividade("pendente")
    if linha.estado == "ok":
        return ClimaDaAtividade("ok", linha.temperatura_c, linha.sensacao_c, linha.umidade_pct, linha.vento_kmh)
    return ClimaDaAtividade(linha.estado)  # type: ignore[arg-type]


def clima_da_atividade(session: Session, atividade_id: int) -> ClimaDaAtividade | None:
    """O clima da atividade (para a API). `None` se a atividade nao existe."""
    a = session.get(Atividade, atividade_id)
    if a is None:
        return None
    linha = session.scalars(select(ClimaAtividade).where(ClimaAtividade.atividade_id == atividade_id)).first()
    return estado_clima(a, linha)


def contar_estados(session: Session, atleta_id: int | None = None) -> dict[str, int]:
    consulta = select(Atividade)
    if atleta_id is not None:
        consulta = consulta.where(Atividade.atleta_id == atleta_id)
    linhas = {c.atividade_id: c for c in session.scalars(select(ClimaAtividade))}
    contagem = dict.fromkeys(ESTADOS, 0)
    for a in session.scalars(consulta):
        contagem[estado_clima(a, linhas.get(a.id)).estado] += 1
    return contagem


@dataclass
class RelatorioClima:
    chamadas: int = 0
    parou: bool = False  # 429 persistente: a rodada parou
    atingiu_limite: bool = False


def _fim(a: Atividade) -> datetime:
    return para_utc(a.inicio) + timedelta(seconds=a.duracao_s or 0)


def preencher_clima(
    session: Session,
    cliente: ClienteClima,
    *,
    atleta_id: int | None = None,
    atividade_ids: Iterable[int] | None = None,
    limite: int = LIMITE_PADRAO,
    refazer_falhas: bool = False,
    agora: datetime | None = None,
    dormir: Callable[[float], None] = time.sleep,
    pausa_s: float = PAUSA_S,
) -> RelatorioClima:
    """Uma rodada de clima. Idempotente: `ok` com a mesma `entrada` nao e consultada de novo."""
    agora = agora or datetime.now(timezone.utc)
    consulta = select(Atividade).where(Atividade.inicio_lat.is_not(None)).order_by(Atividade.id)
    if atleta_id is not None:
        consulta = consulta.where(Atividade.atleta_id == atleta_id)
    if atividade_ids is not None:
        consulta = consulta.where(Atividade.id.in_(list(atividade_ids)))
    linhas = {c.atividade_id: c for c in session.scalars(select(ClimaAtividade))}
    rel = RelatorioClima()
    for a in list(session.scalars(consulta)):
        if e_indoor(a.subtipo) or _fim(a) > agora - JANELA_ATRASO:
            continue  # dentro dos 7 dias: pendente sem consultar e sem contar rodada
        entrada = entrada_de(a)
        linha = linhas.get(a.id)
        mesma = linha is not None and linha.entrada == entrada
        if mesma and linha.estado == "ok":
            continue
        if mesma and linha.estado == "falha" and not refazer_falhas:
            continue
        if rel.chamadas >= limite:
            rel.atingiu_limite = True
            break
        if rel.chamadas:
            dormir(pausa_s)
        if linha is None:
            linha = ClimaAtividade(atividade_id=a.id, tentativas=0)
            session.add(linha)
        if not mesma or linha.estado == "falha":
            linha.tentativas = 0  # entrada nova, ou falha refeita de proposito: contagem de rodadas recomeca
        res = cliente.buscar(a.inicio_lat, a.inicio_lon, para_utc(a.inicio), int(a.duracao_s))
        rel.chamadas += 1
        linha.entrada = entrada
        linha.tentativas += 1
        linha.consultado_em = agora
        linha.erro = (res.erro or None) and res.erro[:200]
        if res.estado == "ok" and res.clima is not None:
            c = res.clima
            linha.estado, linha.fonte = "ok", FONTE_CLIMA
            linha.temperatura_c, linha.sensacao_c = c.temperatura_c, c.sensacao_c
            linha.umidade_pct, linha.vento_kmh = c.umidade_pct, c.vento_kmh
            linha.erro = None
        else:
            linha.temperatura_c = linha.sensacao_c = linha.umidade_pct = linha.vento_kmh = None
            linha.fonte = None
            if res.estado == "pendente" and linha.tentativas >= MAX_RODADAS:
                linha.estado = "falha"
                linha.erro = f"{MAX_RODADAS} rodadas sem sucesso: {res.erro or 'sem motivo'}"[:200]
            else:
                linha.estado = "falha" if res.estado == "falha" else "pendente"
        session.commit()
        linhas[a.id] = linha
        log.info("clima atividade_id=%s estado=%s", a.id, linha.estado)
        if res.parar_rodada:
            rel.parou = True
            break
    return rel


def preencher_posicoes(
    session: Session,
    *,
    atleta_id: int | None = None,
    exportacao: str | Path | None = None,
    fit_dir: Path | None = None,
) -> int:
    """Preenche `inicio_lat/lon` onde esta NULL, relendo a exportacao e o FIT guardado. Nunca sobrescreve.

    A exportacao vale primeiro (o JSON vale mais que o FIT, ADR 0006); sem posicao nela, o FIT em `FIT_DIR`.
    Atividade indoor nao recebe posicao. Devolve quantas atividades receberam posicao.
    """
    consulta = select(Atividade).where(Atividade.inicio_lat.is_(None)).order_by(Atividade.id)
    if atleta_id is not None:
        consulta = consulta.where(Atividade.atleta_id == atleta_id)
    alvo = [a for a in session.scalars(consulta) if not e_indoor(a.subtipo)]
    if not alvo:
        return 0
    da_exportacao: dict[tuple[str, str], tuple[float, float]] = {}
    if exportacao is not None:
        for i in ler_exportacao(exportacao):
            if i.inicio_lat is not None and i.inicio_lon is not None:
                da_exportacao[(i.fonte, i.fonte_id)] = (i.inicio_lat, i.inicio_lon)
    preenchidas = 0
    for a in alvo:
        pos = da_exportacao.get((a.fonte, a.fonte_id))
        if pos is None and fit_guardado.esta_guardado(a.arquivo_bruto):
            pos = _posicao_do_fit_guardado(a.arquivo_bruto, fit_dir)
        if pos is None:
            continue
        a.inicio_lat, a.inicio_lon = pos
        session.commit()
        preenchidas += 1
    return preenchidas


def _posicao_do_fit_guardado(relativo: str, fit_dir: Path | None) -> tuple[float, float] | None:
    arquivo = pasta_fit(fit_dir) / relativo
    try:
        lida = ler_atividade_fit(arquivo.read_bytes())
    except (OSError, ValueError):  # arquivo sumiu, ilegivel ou nao e atividade (FitSemAtividade e ValueError)
        return None
    if lida.inicio_lat is None or lida.inicio_lon is None:
        return None
    return lida.inicio_lat, lida.inicio_lon
