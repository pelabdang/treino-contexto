"""Camada de LLM trocavel (issue #326, ADR 0013 item 3).

Provedor e modelo vem de `LLM_PROVIDER` e `LLM_MODEL` do `.env`; trocar e mudar o `.env`, sem tocar no codigo. So esta
camada chama o LiteLLM. Contrato:

- `Redator.redigir(sistema, pacote)` NUNCA levanta e devolve um `ResultadoLLM`: ou o `texto`, ou um `motivo` (codigo
  fechado, os mesmos do `CHECK` da tabela `feedback_treino`, ADR 0013 item 2).
- Tempo limite por chamada; SEM nova tentativa dentro da chamada (a proxima execucao do worker e a nova tentativa).
- Limite de chamadas por instancia (uma instancia por execucao do worker); a chamada acima do limite nem vai ao provedor.
- NADA do prompt, do pacote, do texto nem da mensagem de excecao do provedor vai para log, excecao ou saida: o erro e
  reduzido a um motivo pela CLASSE da excecao e a mensagem e descartada (ela pode repetir o corpo da requisicao).
  O LiteLLM tambem e configurado para nao registrar conteudo (`_configurar_litellm`).
- O pacote e o texto sao dado de saude: nada disso e gravado aqui.
"""

from __future__ import annotations

import json
import logging
import os
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol

from app.config import Settings

MOTIVO_NAO_CONFIGURADO = "provedor_nao_configurado"
MOTIVO_ERRO = "provedor_erro"
MOTIVO_TEMPO_LIMITE = "provedor_tempo_limite"
MOTIVO_LIMITE = "limite_de_chamadas"
MOTIVOS = (MOTIVO_NAO_CONFIGURADO, MOTIVO_ERRO, MOTIVO_TEMPO_LIMITE, MOTIVO_LIMITE)

PROVEDOR_FALSO = "falso"
# provedor -> campo de `Settings` com a chave. Provedor fora daqui e "nao configurado".
CHAVES = {"groq": "groq_api_key", "openai": "openai_api_key", "anthropic": "anthropic_api_key"}


class TempoLimite(Exception):
    """O provedor nao respondeu a tempo."""


class LimiteDoProvedor(Exception):
    """O provedor recusou por limite de requisicoes ou de tokens por minuto (HTTP 429). Sem a mensagem do provedor."""


class ErroProvedor(Exception):
    """Qualquer outra falha do provedor (rede, limite do plano, resposta vazia...). Sem texto da falha original."""


@dataclass(frozen=True)
class ResultadoLLM:
    texto: str | None
    motivo: str | None
    provedor: str | None  # valor de LLM_PROVIDER no momento (vai para `feedback_treino.provedor`)
    modelo: str | None  # valor de LLM_MODEL no momento


class ProvedorLLM(Protocol):
    def completar(self, sistema: str, usuario: str, timeout_s: float) -> str: ...


class ProvedorFalso:
    """Provedor dos testes e do CI: sem rede, sem chave. `modo` escolhe o que devolve, para provar as checagens e os erros."""

    # Passa na `checar_texto` (checagens_feedback@2) com pacote comum: cada linha com verbo da lista (com acento), sem número.
    # Com o atalho `dor` reprova por `dor_regra` (nao traz a frase da dor); ver `test_texto_do_provedor_falso_nas_checagens_reais`.
    TEXTO_BOM = (
        "Este é um texto de teste do provedor falso.\n"
        "Esta linha foi escrita só para os testes.\n"
        "Nenhum dado real é usado aqui."
    )
    TEXTO_RUIM = (  # sinteticos: numero fora do pacote, linguagem proibida e mais de 5 linhas
        "Voce correu 99 km hoje.\nIsso foi por causa do calor, com certeza.\nDescanse amanha.\n"
        "Voce deveria treinar mais.\nO professor aprovou.\nLinha extra.\n"
    )

    def __init__(self, texto: str | None = None, modo: str = "bom") -> None:
        if modo not in ("bom", "ruim", "vazio", "erro", "tempo", "limite"):
            raise ValueError("modo invalido")
        self.texto, self.modo = texto, modo
        self.chamadas = 0

    def completar(self, sistema: str, usuario: str, timeout_s: float) -> str:
        self.chamadas += 1
        if self.modo == "erro":
            raise ErroProvedor()
        if self.modo == "tempo":
            raise TempoLimite()
        if self.modo == "limite":
            raise LimiteDoProvedor()
        if self.modo == "vazio":
            return ""
        if self.texto is not None:
            return self.texto
        return self.TEXTO_RUIM if self.modo == "ruim" else self.TEXTO_BOM


def _configurar_litellm():
    """Importa o LiteLLM sem rede e sem registrar conteudo. Nomes conferidos no codigo da 1.108.4 (ver a ADR 0013)."""
    # sem isso a importacao tenta baixar a tabela de precos de um repositorio remoto
    os.environ.setdefault("LITELLM_LOCAL_MODEL_COST_MAP", "True")
    # no modo padrao ("DEV") a importacao faz `load_dotenv()` e joga o `.env` mais proximo (com credenciais de outros
    # modulos) em `os.environ`; em "PRODUCTION" nao faz. Quem le o `.env` aqui e so o `Settings`.
    os.environ.setdefault("LITELLM_MODE", "PRODUCTION")
    import litellm

    litellm.turn_off_message_logging = True  # padrao False
    litellm.redact_messages_in_exceptions = True  # padrao False
    litellm.suppress_debug_info = True
    litellm.log_raw_request_response = False
    litellm.input_callback, litellm.success_callback = [], []
    litellm.failure_callback, litellm.callbacks = [], []
    for nome in ("LiteLLM", "LiteLLM Router", "LiteLLM Proxy", "httpx"):  # o padrao do LiteLLM e DEBUG
        logging.getLogger(nome).setLevel(logging.CRITICAL)
    return litellm


class ProvedorLiteLLM:
    """Chama `litellm.completion` com `<provedor>/<modelo>`. A chave vai explicita (nao polui `os.environ`)."""

    def __init__(self, provedor: str, modelo: str, chave: str, extra: dict[str, Any] | None = None) -> None:
        self.provedor, self.modelo, self._chave = provedor, modelo, chave
        self._extra = extra or {}  # so para testes offline (`mock_response`)

    def completar(self, sistema: str, usuario: str, timeout_s: float) -> str:
        litellm = _configurar_litellm()
        try:
            resp = litellm.completion(
                model=f"{self.provedor}/{self.modelo}",
                messages=[{"role": "system", "content": sistema}, {"role": "user", "content": usuario}],
                api_key=self._chave,
                timeout=timeout_s,
                num_retries=0,
                temperature=0.2,
                **self._extra,
            )
            texto = resp.choices[0].message.content
        except Exception as e:  # noqa: BLE001  (so a CLASSE conta; a mensagem pode ter dado de saude)
            if isinstance(e, TimeoutError) or "Timeout" in e.__class__.__name__:
                raise TempoLimite() from None
            if "RateLimit" in e.__class__.__name__ or getattr(e, "status_code", None) == 429:
                raise LimiteDoProvedor() from None
            raise ErroProvedor() from None
        if not isinstance(texto, str) or not texto.strip():
            raise ErroProvedor()
        return texto


class Redator:
    """Uma instancia por execucao do worker: conta as chamadas e traduz tudo em `ResultadoLLM`."""

    def __init__(self, provedor: ProvedorLLM | None, nome_provedor: str | None, modelo: str | None,
                 timeout_s: float = 20.0, limite_chamadas: int = 20, intervalo_s: float = 0.0,
                 dormir: Callable[[float], None] = time.sleep) -> None:
        self._provedor = provedor
        self.nome_provedor, self.modelo = nome_provedor, modelo
        self.timeout_s, self.limite_chamadas = timeout_s, limite_chamadas
        self.intervalo_s, self._dormir = max(0.0, intervalo_s), dormir
        self.chamadas = 0
        self.limite_do_provedor = False  # o provedor recusou por limite: quem chama deve parar a execucao

    @property
    def configurado(self) -> bool:
        return self._provedor is not None

    def _res(self, texto: str | None = None, motivo: str | None = None) -> ResultadoLLM:
        return ResultadoLLM(texto, motivo, self.nome_provedor, self.modelo)

    def redigir(self, sistema: str, pacote: dict | str) -> ResultadoLLM:
        self.limite_do_provedor = False  # vale so para ESTA chamada (um `Redator` reutilizado nao herda o 429 anterior)
        if self._provedor is None:
            return self._res(motivo=MOTIVO_NAO_CONFIGURADO)
        if self.chamadas >= self.limite_chamadas:
            return self._res(motivo=MOTIVO_LIMITE)
        if self.chamadas and self.intervalo_s:  # pausa so ENTRE chamadas, nunca antes da primeira
            self._dormir(self.intervalo_s)
        self.chamadas += 1
        usuario = pacote if isinstance(pacote, str) else json.dumps(pacote, ensure_ascii=False, separators=(",", ":"))  # compacto e na ordem do pacote (menos tokens)
        try:
            texto = self._provedor.completar(sistema, usuario, self.timeout_s)
        except TempoLimite:
            return self._res(motivo=MOTIVO_TEMPO_LIMITE)
        except LimiteDoProvedor:
            self.limite_do_provedor = True
            return self._res(motivo=MOTIVO_LIMITE)
        except Exception:  # noqa: BLE001  (nunca repete nem registra a excecao)
            return self._res(motivo=MOTIVO_ERRO)
        if not isinstance(texto, str) or not texto.strip():
            return self._res(motivo=MOTIVO_ERRO)
        return self._res(texto=limpar_texto(texto))


def limpar_texto(texto: str) -> str:
    """Tira os espacos do fim de cada linha e os do comeco e do fim do texto (#367).

    Feito na camada, e nao no worker, porque o resquicio e do provedor: toda saida de `redigir` ja sai limpa, e o texto que as
    checagens leem e o que o worker grava e o MESMO. Nao muda nenhuma regra das checagens.
    """
    return "\n".join(linha.rstrip() for linha in texto.strip().splitlines())


def criar_redator(config: Settings | None = None) -> Redator:
    """Monta o `Redator` do `.env`. Sem provedor, sem modelo, sem chave ou provedor desconhecido: `nao configurado`."""
    from app.config import settings

    c = config or settings
    provedor = (c.llm_provider or "").strip().lower()
    modelo = (c.llm_model or "").strip()
    comum = dict(timeout_s=c.llm_timeout_s, limite_chamadas=c.llm_limite_chamadas, intervalo_s=c.llm_intervalo_s)
    if provedor == PROVEDOR_FALSO:
        return Redator(ProvedorFalso(), PROVEDOR_FALSO, modelo or PROVEDOR_FALSO, **comum)
    campo = CHAVES.get(provedor)
    chave = getattr(c, campo, None) if campo else None
    chave_txt = chave.get_secret_value().strip() if chave is not None else ""
    if not (provedor and modelo and campo and chave_txt):
        return Redator(None, provedor or None, modelo or None, **comum)
    return Redator(ProvedorLiteLLM(provedor, modelo, chave_txt), provedor, modelo, **comum)
