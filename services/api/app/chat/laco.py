"""O laco do chat (#596, ADR 0017, item 3): pergunta -> modelo escolhe ferramentas -> o servidor roda (escopo da sessao) -> modelo redige ->
`checagens_chat@1`.

Limites: no maximo 6 chamadas de ferramenta por pergunta (as paralelas contam uma a uma), 8 chamadas ao provedor (voltas e, no maximo,
uma regeneracao), 20 s por chamada e 45 s por pergunta, e 1 correcao de erro de ferramenta (o 2o erro encerra). Sem nova tentativa dentro
de uma chamada. Texto reprovado: uma regeneracao com os CODIGOS do motivo (nunca o texto); reprovou de novo, o texto e descartado.

Dado de saude: pergunta, argumentos, resultados e resposta NUNCA vao a log, excecao ou saida; o laco nao tem `logging` nem `print`.
O que a rota grava (`Mensagem`) vem do `ResultadoPergunta`; o texto reprovado nunca sai daqui.
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from app.chat import prompt
from app.chat.registro import Consulta, esquemas_para, erro
from app.explicacao import checagens_chat as ck
from app.llm.camada import ChamadaFerramenta, Redator

MAX_FERRAMENTAS = 6
MAX_CHAMADAS_PROVEDOR = 8
TIMEOUT_CHAMADA_S = 20.0
TIMEOUT_PERGUNTA_S = 45.0
MAX_ERROS_DE_FERRAMENTA = 1  # o segundo erro da pergunta encerra
MAX_TROCAS_NO_HISTORICO = 6

RESPONDIDA, RECUSADA, REPROVADA, ERRO = "respondida", "recusada", "reprovada", "erro"
Executor = Callable[[str, Any], dict[str, Any]]


@dataclass
class ResultadoPergunta:
    estado: str  # respondida | recusada | reprovada | erro
    resposta: str | None = None  # respondida: o texto aprovado; recusada: o texto fixo; reprovada e erro: None, sempre
    motivo: str | None = None  # codigo (reprovada: o primeiro das checagens; recusada: fora_do_tema ou pedido_de_mudanca)
    motivos: tuple[str, ...] = ()  # todos os codigos de checagem que reprovaram (so codigos)
    chamadas_ferramenta: list[dict[str, Any]] = field(default_factory=list)  # [{nome, argumentos, resultado}] na ordem
    provedor: str | None = None
    modelo: str | None = None


def _mensagem_do_modelo(chamadas: Sequence[ChamadaFerramenta]) -> dict[str, Any]:
    return {"role": "assistant", "content": None, "tool_calls": [
        {"id": c.id, "type": "function", "function": {"name": c.nome, "arguments": json.dumps(c.argumentos if c.argumentos is not None else {}, ensure_ascii=False)}}
        for c in chamadas]}


def historico_para_provedor(trocas: Sequence[tuple[str, str]]) -> list[dict[str, Any]]:
    """As ultimas 6 trocas APROVADAS (pergunta, resposta), sem os resultados das ferramentas antigas (ADR 0017, item 3)."""
    mensagens: list[dict[str, Any]] = []
    for pergunta, resposta in list(trocas)[-MAX_TROCAS_NO_HISTORICO:]:
        mensagens += [{"role": "user", "content": pergunta}, {"role": "assistant", "content": resposta}]
    return mensagens


def responder(
    redator: Redator,
    executar: Executor,
    consulta: Consulta,
    pergunta: str,
    historico: Sequence[tuple[str, str]] = (),
    hoje: date | None = None,
    relogio: Callable[[], float] = time.monotonic,
) -> ResultadoPergunta:
    """Roda uma pergunta ate o texto final. Nunca levanta. `executar(nome, argumentos)` ja leva a sessao e a `Consulta`."""
    inicio = relogio()
    mensagens = [{"role": "system", "content": prompt.sistema(hoje or consulta.hoje)}, *historico_para_provedor(historico),
                 {"role": "user", "content": pergunta}]
    ferramentas = esquemas_para(consulta.quem.papel)
    r = ResultadoPergunta(ERRO, provedor=redator.nome_provedor, modelo=redator.modelo)
    chamadas_ao_provedor = erros_de_ferramenta = 0
    regenerou = False

    def encerra(motivo: str) -> ResultadoPergunta:
        r.estado, r.resposta, r.motivo = ERRO, None, motivo
        return r

    while True:
        restante = TIMEOUT_PERGUNTA_S - (relogio() - inicio)
        if restante <= 0:
            return encerra("tempo_limite")
        if chamadas_ao_provedor >= MAX_CHAMADAS_PROVEDOR:
            return encerra("limite_de_chamadas")
        chamadas_ao_provedor += 1
        volta = redator.conversar(mensagens, ferramentas, min(TIMEOUT_CHAMADA_S, restante))
        r.provedor, r.modelo = volta.provedor, volta.modelo
        if volta.motivo is not None or volta.resposta is None:
            return encerra(volta.motivo or "provedor_erro")
        resposta = volta.resposta

        if resposta.chamadas:
            mensagens.append(_mensagem_do_modelo(resposta.chamadas))
            for chamada in resposta.chamadas:
                if len(r.chamadas_ferramenta) >= MAX_FERRAMENTAS:
                    return encerra("limite_de_ferramentas")
                resultado = erro("argumento_invalido", argumento="argumentos") if chamada.argumentos is None else executar(chamada.nome, chamada.argumentos)
                r.chamadas_ferramenta.append({"nome": chamada.nome, "argumentos": chamada.argumentos or {}, "resultado": resultado})
                mensagens.append({"role": "tool", "tool_call_id": chamada.id, "content": json.dumps(resultado, ensure_ascii=False)})
                if chamada.nome == "recusar" and resultado.get("estado") == "ok":
                    r.estado, r.motivo, r.resposta = RECUSADA, resultado["motivo"], ck.texto_da_recusa(resultado["motivo"])
                    return r
                if resultado.get("estado") == "erro":
                    erros_de_ferramenta += 1
                    if erros_de_ferramenta > MAX_ERROS_DE_FERRAMENTA:
                        return encerra("ferramenta_erro")
            continue

        veredito = ck.checar_texto(r.chamadas_ferramenta, resposta.texto or "")
        if veredito.aprovado:
            r.estado, r.resposta, r.motivo, r.motivos = RESPONDIDA, resposta.texto, None, ()
            return r
        if regenerou:
            r.estado, r.resposta, r.motivo, r.motivos = REPROVADA, None, veredito.motivos[0], veredito.motivos
            return r
        regenerou = True  # uma regeneracao; o texto reprovado NAO volta ao provedor, so os codigos
        mensagens.append({"role": "user", "content": prompt.pedido_de_correcao(veredito.motivos)})
