"""Camada de LLM trocavel (issue #326, ADR 0013 item 3). O resto do app so usa `criar_redator` e `Redator.redigir`."""

from app.llm.camada import (  # noqa: F401
    MOTIVOS,
    ProvedorFalso,
    ProvedorLiteLLM,
    Redator,
    ResultadoLLM,
    criar_redator,
)
