"""Validador minimo de argumentos (subconjunto do JSON Schema que os esquemas das ferramentas usam). Sem dependencia nova.

Suporta: `type` (object, string, integer), `properties`, `required`, `additionalProperties: false`, `enum`, `minimum`, `maximum`,
`pattern`, `maxLength`. Devolve o CAMINHO do primeiro erro (nome do argumento), nunca o valor recebido (pode ser dado do atleta).
"""

from __future__ import annotations

import re
from typing import Any

_TIPOS = {"string": str, "integer": int, "object": dict}


class ArgumentoInvalido(ValueError):
    def __init__(self, caminho: str) -> None:
        super().__init__(caminho)
        self.caminho = caminho


def validar(esquema: dict[str, Any], valor: Any, caminho: str = "") -> None:
    tipo = esquema.get("type")
    if tipo is not None:
        certo = _TIPOS[tipo]
        if not isinstance(valor, certo) or (tipo == "integer" and isinstance(valor, bool)):
            raise ArgumentoInvalido(caminho or "argumentos")
    if "enum" in esquema and valor not in esquema["enum"]:
        raise ArgumentoInvalido(caminho)
    if tipo == "integer":
        if valor < esquema.get("minimum", valor) or valor > esquema.get("maximum", valor):
            raise ArgumentoInvalido(caminho)
    if tipo == "string":
        if len(valor) > esquema.get("maxLength", len(valor)) or ("pattern" in esquema and not re.fullmatch(esquema["pattern"], valor)):
            raise ArgumentoInvalido(caminho)
    if tipo == "object":
        props = esquema.get("properties", {})
        for nome in esquema.get("required", []):
            if nome not in valor:
                raise ArgumentoInvalido(nome)
        for nome, v in valor.items():
            if nome not in props:
                if esquema.get("additionalProperties") is False:
                    raise ArgumentoInvalido(str(nome)[:40])
                continue
            validar(props[nome], v, nome)
