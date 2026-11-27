"""Selo "normal" por treino (issue #551): agrega os estados por métrica da ``linha_base@3`` em um só.

Função pura: sem banco, sem rede, sem IA. Regra, exemplos e limitações em docs/metricas/normal-treino.md.
Qualquer mudança de regra ou de prioridade exige subir ``VERSAO``.

Fonte: regra própria do projeto (decisão do Caio na #551, spec v3 das telas). Coerente com a regra do elogio da caixa do dia
(``explicacao.checagens._elogio_sustentado``: ao menos uma métrica ``dentro`` e nenhuma ``fora``).
Descreve, nunca julga: ``fora`` vale para os dois lados da mediana.
"""

from __future__ import annotations

from collections.abc import Iterable

VERSAO = "normal_treino@1"


def normal_treino(estado_linha_base: str, estados_metricas: Iterable[str]) -> str | None:
    """``fora`` | ``dentro`` | ``aprendendo`` | ``None``.

    - linha de base diferente de ``ok`` (``sem_linha_base``): ``None``.
    - alguma métrica ``fora``: ``fora``; senão alguma ``dentro``: ``dentro`` (``dentro`` + ``aprendendo`` dá ``dentro``);
      senão alguma ``aprendendo``: ``aprendendo``; senão (tudo ``sem_valor`` ou sem métricas): ``None``.
    """
    if estado_linha_base != "ok":
        return None
    estados = set(estados_metricas)
    for estado in ("fora", "dentro", "aprendendo"):
        if estado in estados:
            return estado
    return None
