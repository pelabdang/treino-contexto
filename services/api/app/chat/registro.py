"""Registro e executor das ferramentas do chat (ADR 0017, itens 1 e 2).

- Toda ferramenta so le. O `atleta_id` vem da `Consulta` (montada pela rota a partir da sessao), NUNCA dos argumentos: o esquema
  nao tem esse campo e `additionalProperties: false` reprova qualquer argumento extra (inclusive `atleta_id`).
- O esquema enviado ao provedor so inclui as ferramentas do papel; o executor confere de novo (`ferramenta_nao_permitida`).
- Erros viram `{"estado": "erro", "codigo": ...}` para o modelo corrigir uma vez; a mensagem da excecao e descartada (so o tipo).
- Dado de saude: nada daqui escreve argumento ou resultado em log.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from typing import Any

from sqlalchemy.orm import Session

from app.chat.esquema import ArgumentoInvalido, validar


@dataclass(frozen=True)
class Quem:
    papel: str  # hoje so "atleta"; "professor" na Meta 16 (so desenho)
    conta_id: int


@dataclass(frozen=True)
class Consulta:
    """Quem pergunta e sobre quem. Montada pela ROTA (`atleta_da_sessao`); nunca vem do modelo."""

    quem: Quem
    atleta_id: int
    hoje: date  # "hoje" local do atleta


Funcao = Callable[[Session, Consulta, dict[str, Any]], dict[str, Any]]


@dataclass(frozen=True)
class Ferramenta:
    nome: str
    descricao: str
    esquema: dict[str, Any]  # JSON Schema do objeto de argumentos; sem campo de atleta
    papeis: frozenset[str]
    funcao: Funcao


REGISTRO: dict[str, Ferramenta] = {}


def registrar(nome: str, descricao: str, propriedades: dict[str, Any], papeis: tuple[str, ...], obrigatorios: tuple[str, ...] = ()):
    """Decorador: registra a funcao com o esquema `{type: object, additionalProperties: false}`."""

    def deco(funcao: Funcao) -> Funcao:
        assert nome not in REGISTRO and not {"atleta_id", "conta_id", "professor_id"} & set(propriedades)
        esquema = {"type": "object", "properties": propriedades, "additionalProperties": False}
        if obrigatorios:
            esquema["required"] = list(obrigatorios)
        REGISTRO[nome] = Ferramenta(nome, descricao, esquema, frozenset(papeis), funcao)
        return funcao

    return deco


def esquemas_para(papel: str) -> list[dict[str, Any]]:
    """As ferramentas do papel, no formato `tools` do provedor (OpenAI)."""
    return [{"type": "function", "function": {"name": f.nome, "description": f.descricao, "parameters": f.esquema}}
            for f in REGISTRO.values() if papel in f.papeis]


def erro(codigo: str, **extra: Any) -> dict[str, Any]:
    return {"estado": "erro", "codigo": codigo, **extra}


def executar(session: Session, consulta: Consulta, nome: str, argumentos: Any) -> dict[str, Any]:
    """Valida e roda uma ferramenta. Nunca levanta: devolve o resultado ou `{"estado": "erro", "codigo": ...}`."""
    f = REGISTRO.get(nome) if isinstance(nome, str) else None
    if f is None:
        return erro("ferramenta_desconhecida")
    if consulta.quem.papel not in f.papeis:
        return erro("ferramenta_nao_permitida")
    try:
        validar(f.esquema, argumentos if argumentos is not None else {})
    except ArgumentoInvalido as e:
        return erro("argumento_invalido", argumento=e.caminho)
    try:
        return f.funcao(session, consulta, argumentos or {})
    except Exception as e:  # noqa: BLE001 - so o tipo da excecao sai; a mensagem pode ter dado de saude
        session.rollback()
        return erro("ferramenta_erro", tipo=type(e).__name__)
