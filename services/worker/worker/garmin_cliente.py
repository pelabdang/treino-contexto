"""Cliente do Garmin Connect atras de uma interface pequena (issue #335).

Biblioteca NAO OFICIAL (`garminconnect`): pode quebrar quando o Garmin mudar o login. A API oficial da Garmin segue
sendo o caminho de producao. Aqui fica so o que o piloto local precisa: listar as atividades de um intervalo de datas e
baixar o FIT original de uma delas. Credenciais e token nunca vao para log nem para mensagem de erro: as mensagens
abaixo sao fixas e nunca repetem o texto da biblioteca.
"""

from __future__ import annotations

import io
import logging
import getpass
import os
import sys
import zipfile
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Callable, Protocol

from app.config import RAIZ_REPOSITORIO

TOKEN_PADRAO = "dados-garmin/token"  # relativo a raiz do repositorio; `dados-garmin/` esta no .gitignore
TAMANHO_MAX_FIT = 10 * 1024 * 1024  # o mesmo teto do upload (ADR 0006)


class ErroGarmin(Exception):
    """Erro esperado ao falar com o Garmin. `str(e)` e uma mensagem clara e segura; `codigo` e o codigo de saida."""

    codigo = 6


class ErroConfiguracao(ErroGarmin):
    codigo = 1


class ErroLogin(ErroGarmin):
    codigo = 2


class ErroMfa(ErroGarmin):
    codigo = 3


class ErroLimite(ErroGarmin):
    codigo = 4


class ErroRede(ErroGarmin):
    codigo = 5


@dataclass(frozen=True)
class AtividadeGarmin:
    id: int
    inicio_utc: datetime | None  # `startTimeGMT`; None se o Garmin nao mandou


class ClienteGarmin(Protocol):
    def listar(self, desde: date, ate: date) -> list[AtividadeGarmin]:
        """Atividades com data local entre `desde` e `ate` (inclusive)."""

    def baixar_fit(self, atividade_id: int) -> bytes:
        """Os bytes do FIT original da atividade (ja extraido do zip)."""


def extrair_fit(conteudo: bytes) -> bytes:
    """O `.fit` de dentro do zip que o Garmin devolve. Se vier um FIT cru, devolve como esta."""
    if not conteudo.startswith(b"PK"):
        return conteudo
    try:
        with zipfile.ZipFile(io.BytesIO(conteudo)) as z:
            fits = [i for i in z.infolist() if i.filename.lower().endswith(".fit") and not i.is_dir()]
            if not fits:
                raise ErroGarmin("o arquivo baixado do Garmin nao tem um .fit")
            info = fits[0]
            if info.file_size > TAMANHO_MAX_FIT:
                raise ErroGarmin("o FIT baixado do Garmin passa de 10 MB")
            with z.open(info) as f:
                dados = f.read(TAMANHO_MAX_FIT + 1)
    except zipfile.BadZipFile as e:
        raise ErroGarmin("o arquivo baixado do Garmin nao e um zip valido") from e
    if len(dados) > TAMANHO_MAX_FIT:
        raise ErroGarmin("o FIT baixado do Garmin passa de 10 MB")
    return dados


def pasta_token(valor: str | None = None) -> Path:
    """Pasta do token: `valor`, ou `GARMINTOKENS`, ou o padrao. Relativo conta a partir da raiz do repositorio."""
    caminho = Path(valor or TOKEN_PADRAO)
    return caminho if caminho.is_absolute() else RAIZ_REPOSITORIO / caminho


def _variavel(nome: str, env: dict[str, str]) -> str | None:
    valor = env.get(nome)
    return valor.strip() if valor and valor.strip() else None


def ler_ambiente(env: dict[str, str] | None = None) -> dict[str, str]:
    """`os.environ` por cima do `.env` local (cwd e raiz do repositorio). Nunca imprime nem registra os valores."""
    if env is not None:
        return env
    from dotenv import dotenv_values

    junto: dict[str, str] = {}
    for arq in (RAIZ_REPOSITORIO / ".env", Path(".env")):
        if arq.is_file():
            junto.update({k: v for k, v in dotenv_values(arq).items() if v is not None})
    junto.update(os.environ)
    return junto


def _hora_gmt(texto: object) -> datetime | None:
    if not isinstance(texto, str):
        return None
    try:
        return datetime.strptime(texto[:19], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def pedir_codigo_mfa() -> str | None:
    """Pergunta o codigo uma vez, so com terminal. Sem terminal devolve None sem perguntar. Nao ecoa nem registra."""
    if not sys.stdin.isatty():
        return None
    try:
        return getpass.getpass("Codigo de verificacao do Garmin: ").strip() or None
    except (EOFError, KeyboardInterrupt):
        return None


class ClienteGarminConnect:
    """Implementacao real, sobre `garminconnect`. So e criada por `entrar`; os testes usam um cliente falso."""

    def __init__(self, api, garmin_mod) -> None:
        self._api = api
        self._mod = garmin_mod

    @classmethod
    def entrar(cls, env: dict[str, str] | None = None,
               ler_codigo: Callable[[], str | None] = pedir_codigo_mfa) -> ClienteGarminConnect:
        """UMA tentativa de login. Usa o token salvo; sem token valido, usa `GARMIN_EMAIL`/`GARMIN_PASSWORD`."""
        env = ler_ambiente(env)
        email, senha = _variavel("GARMIN_EMAIL", env), _variavel("GARMIN_PASSWORD", env)
        pasta = pasta_token(_variavel("GARMINTOKENS", env))
        tem_token = (pasta / "garmin_tokens.json").is_file()
        if not tem_token and not (email and senha):
            raise ErroConfiguracao(
                "sem token salvo e sem credenciais: defina GARMIN_EMAIL e GARMIN_PASSWORD no .env local"
            )
        import garminconnect as mod

        # a biblioteca registra avisos sobre o login; nada dela vai para o nosso log
        logging.getLogger("garminconnect").setLevel(logging.CRITICAL)
        api = mod.Garmin(email=email, password=senha, return_on_mfa=True, retry_attempts=1)
        cliente = cls(api, mod)
        try:
            status, estado = api.login(str(pasta))
        except Exception as e:  # noqa: BLE001
            raise cliente._traduzir(e, ao_entrar=True, tinha_token=tem_token) from None
        if status == "needs_mfa":
            cliente._concluir_mfa(estado, ler_codigo)
        try:  # em modo `return_on_mfa` a biblioteca nao grava o token sozinha: gravamos aqui (0600 em pasta 0700)
            api.client.dump(str(pasta))
        except Exception:  # noqa: BLE001
            logging.getLogger(__name__).warning("aviso: token nao salvo; o proximo login vai usar as credenciais")
        return cliente

    def _concluir_mfa(self, estado, ler_codigo) -> None:
        """Pede o codigo UMA vez e conclui com `resume_login`. Sem terminal, codigo vazio ou recusado: `ErroMfa`."""
        sem_codigo = ErroMfa(
            "o Garmin pediu o codigo de verificacao (MFA); rode num terminal para digita-lo. "
            "Veja a nota do modulo ingestao-garmin"
        )
        codigo = ler_codigo()
        if not codigo:
            raise sem_codigo
        try:
            self._api.resume_login(estado, codigo)
        except Exception:  # noqa: BLE001  (texto da excecao pode ter dado de conta; nao repete)
            raise ErroMfa("o Garmin recusou o codigo de verificacao (MFA); rode de novo para tentar outro") from None

    def _traduzir(self, e: Exception, ao_entrar: bool = False, tinha_token: bool = False) -> ErroGarmin:
        """Mensagem fixa por tipo de erro; nunca repete o texto da biblioteca (pode ter dado de conta)."""
        if isinstance(e, ErroGarmin):
            return e
        m = self._mod
        if isinstance(e, m.GarminConnectTooManyRequestsError):
            return ErroLimite("o Garmin limitou as requisicoes (429); espere alguns minutos e rode de novo")
        if isinstance(e, m.GarminConnectAuthenticationError):
            if tinha_token or not ao_entrar:
                return ErroLogin(
                    "o Garmin recusou a sessao salva; apague a pasta do token e rode de novo "
                    "(vai usar GARMIN_EMAIL e GARMIN_PASSWORD)"
                )
            return ErroLogin("o Garmin recusou o login; confira GARMIN_EMAIL e GARMIN_PASSWORD")
        if isinstance(e, (m.GarminConnectConnectionError, OSError, TimeoutError)):
            return ErroRede("nao foi possivel falar com o Garmin (rede ou servico fora do ar); tente de novo mais tarde")
        return ErroGarmin(f"erro inesperado ao falar com o Garmin ({e.__class__.__name__})")

    def listar(self, desde: date, ate: date) -> list[AtividadeGarmin]:
        try:
            bruto = self._api.get_activities_by_date(desde.isoformat(), ate.isoformat(), sortorder="asc")
        except Exception as e:  # noqa: BLE001
            raise self._traduzir(e) from None
        itens = []
        for a in bruto or []:
            try:
                itens.append(AtividadeGarmin(id=int(a["activityId"]), inicio_utc=_hora_gmt(a.get("startTimeGMT"))))
            except (KeyError, TypeError, ValueError):
                continue  # sem `activityId` utilizavel: nao da para baixar
        return itens

    def baixar_fit(self, atividade_id: int) -> bytes:
        try:
            zip_bytes = self._api.download_activity(
                atividade_id, dl_fmt=self._mod.Garmin.ActivityDownloadFormat.ORIGINAL
            )
        except Exception as e:  # noqa: BLE001
            raise self._traduzir(e) from None
        return extrair_fit(zip_bytes)
