"""O feedback da atividade como a API o mostra (issue #328, ADR 0013 item 2): cinco estados e a `mensagem` pronta.

So le o que o `worker.gerar_feedback` gravou em `feedback_treino`; nunca gera, nunca chama o provedor. A API **não** devolve
`provedor`, `modelo` nem `versao_fatos`, e nunca devolve o texto de um feedback desatualizado (ele pode contradizer o check-in novo).
`motivo` so sai em `indisponivel` e e um codigo; o texto reprovado nao existe no banco. Dado de saude: so ao proprio atleta.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.db.models import Atividade, CheckinTreino
from app.explicacao.fatos_treino import VERSAO as VERSAO_FATOS
from app.servicos.checkin import elegivel
from app.servicos.feedback import _NAO_SEI, motivos_desatualizado

MSG_SEM_CHECKIN = "Faça o check-in para ver o feedback."
MSG_PRAZO_VENCIDO = "O prazo do check-in deste treino acabou, então ele fica sem feedback."
MSG_PENDENTE = "O feedback deste treino ainda não foi gerado. Toque em Atualizar para ver se já está pronto."
MSG_DESATUALIZADO = "Você editou o check-in. O feedback será refeito."
MSG_DESATUALIZADO_VERSAO = "O feedback será refeito."  # #402: so a versao do pacote de fatos mudou; o atleta nao fez nada
MSG_DESATUALIZADO_NOITE = "Os dados da noite anterior foram atualizados. O feedback será refeito."  # #396: so a noite mudou
MSG_DESATUALIZADO_CLIMA = "Os dados do clima foram atualizados. O feedback será refeito."  # #409: so o clima mudou
MSG_DESATUALIZADO_TIPO = "O tipo do treino mudou depois deste feedback. O feedback será refeito."  # #425: o professor corrigiu o tipo
MSG_DESATUALIZADO_TRANSICAO = "A marcação de treino de transição mudou depois deste feedback. O feedback será refeito."  # #510: o atleta corrigiu ou desfez o rótulo
MSG_DESATUALIZADO_TREINO = "O tipo e a marcação de transição do treino mudaram depois deste feedback. O feedback será refeito."
MSG_DESATUALIZADO_NOITE_CLIMA = "Os dados da noite anterior e do clima foram atualizados. O feedback será refeito."
MSG_INDISPONIVEL = "Ainda não foi possível gerar o feedback deste treino. Uma nova tentativa será feita mais tarde."
MSG_SEM_PROVEDOR = "O feedback automático não está ligado neste app."


@dataclass(frozen=True)
class FeedbackLido:
    estado: str  # pronto | sem_checkin | pendente | desatualizado | indisponivel
    texto: str | None = None  # so em pronto
    origem: str | None = None  # so em pronto: automatico | teste (provedor falso)
    mensagem: str | None = None  # frase pronta, em todos os estados menos pronto
    checkin_aberto: bool | None = None  # so em sem_checkin
    motivo: str | None = None  # so em indisponivel (codigo; o app nao o mostra)


def feedback_da_atividade(a: Atividade, checkin: CheckinTreino | None, checkin_aberto: bool,
                          versao_fatos: str = VERSAO_FATOS, recuperacao_hoje=_NAO_SEI, clima_hoje=_NAO_SEI, tipo_hoje=_NAO_SEI,
                          transicao_hoje=_NAO_SEI) -> FeedbackLido | None:
    """`None` para atividade que nao pede check-in (`multiesporte_pai` e `troca`): o cartao nao aparece.
    `recuperacao_hoje`: o `importado_em` da noite do treino hoje (ADR 0014, item 4b); omitido, a noite nao entra na conta.
    `clima_hoje`: a assinatura do clima hoje (#409); omitido, o clima nao entra na conta.
    `tipo_hoje`: o tipo da atividade hoje (#425); omitido, o tipo nao entra na conta.
    `transicao_hoje`: se a atividade e parte de uma transicao hoje (#510); omitido, nao entra na conta."""
    if not elegivel(a):
        return None
    if checkin is None:
        return FeedbackLido("sem_checkin", mensagem=MSG_SEM_CHECKIN if checkin_aberto else MSG_PRAZO_VENCIDO,
                            checkin_aberto=checkin_aberto)
    fb = checkin.feedback
    if fb is None:
        return FeedbackLido("pendente", mensagem=MSG_PENDENTE)
    if fb.estado == "sem_feedback":
        sem_provedor = fb.motivo == "provedor_nao_configurado"
        return FeedbackLido("indisponivel", mensagem=MSG_SEM_PROVEDOR if sem_provedor else MSG_INDISPONIVEL, motivo=fb.motivo)
    motivos = motivos_desatualizado(fb, checkin, versao_fatos, recuperacao_hoje, clima_hoje, tipo_hoje, transicao_hoje)
    if motivos:
        return FeedbackLido("desatualizado", mensagem=_mensagem_desatualizado(motivos))
    return FeedbackLido("pronto", texto=fb.texto, origem="teste" if fb.provedor == "falso" else "automatico")


def _mensagem_desatualizado(motivos: frozenset[str]) -> str:
    """A frase do check-in vale sempre que ele mudou (#396). A versao do pacote nao e acao de ninguem (#402): sozinha tem a frase
    curta; junto de outro motivo some e vale a frase do outro. Senao, a dos dados que chegaram: noite, clima, tipo (#409, #425)."""
    if "checkin" in motivos:
        return MSG_DESATUALIZADO
    motivos = motivos - {"versao"}
    if not motivos:
        return MSG_DESATUALIZADO_VERSAO
    if "transicao" in motivos and not ({"noite", "clima"} & motivos):
        return MSG_DESATUALIZADO_TREINO if "tipo" in motivos else MSG_DESATUALIZADO_TRANSICAO
    if "tipo" in motivos and not ({"noite", "clima"} & motivos):
        return MSG_DESATUALIZADO_TIPO
    if {"noite", "clima"} <= motivos:
        return MSG_DESATUALIZADO_NOITE_CLIMA
    return MSG_DESATUALIZADO_NOITE if "noite" in motivos else MSG_DESATUALIZADO_CLIMA
