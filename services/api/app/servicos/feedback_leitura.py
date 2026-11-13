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
from app.servicos.feedback import _NAO_SEI, desatualizado

MSG_SEM_CHECKIN = "Faça o check-in para ver o feedback."
MSG_PRAZO_VENCIDO = "O prazo do check-in deste treino acabou, então ele fica sem feedback."
MSG_PENDENTE = "O feedback deste treino ainda não foi gerado. Toque em Atualizar para ver se já está pronto."
MSG_DESATUALIZADO = "Você editou o check-in. O feedback será refeito."
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
                          versao_fatos: str = VERSAO_FATOS, recuperacao_hoje=_NAO_SEI) -> FeedbackLido | None:
    """`None` para atividade que nao pede check-in (`multiesporte_pai` e `troca`): o cartao nao aparece.
    `recuperacao_hoje`: o `importado_em` da noite do treino hoje (ADR 0014, item 4b); omitido, a noite nao entra na conta."""
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
    if desatualizado(fb, checkin, versao_fatos, recuperacao_hoje):
        return FeedbackLido("desatualizado", mensagem=MSG_DESATUALIZADO)
    return FeedbackLido("pronto", texto=fb.texto, origem="teste" if fb.provedor == "falso" else "automatico")
