"""`recusar` (ADR 0017, item 1): o modelo so decide SE recusa; o texto que o atleta le e fixo, do codigo (`checagens_chat.TEXTOS_FIXOS`)."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.chat.registro import Consulta, registrar

MOTIVOS_RECUSA = ("fora_do_tema", "pedido_de_mudanca")


@registrar(
    "recusar",
    "Use quando a pergunta nao e sobre os treinos do atleta (`fora_do_tema`) ou pede para mudar, montar ou prescrever treino "
    "(`pedido_de_mudanca`). Nao escreva resposta: o sistema mostra o texto fixo.",
    {"motivo": {"type": "string", "enum": list(MOTIVOS_RECUSA)}},
    ("atleta", "professor"),
    ("motivo",),
)
def recusar(session: Session, c: Consulta, a: dict[str, Any]) -> dict[str, Any]:
    return {"versao": "recusa@1", "estado": "ok", "motivo": a["motivo"]}
