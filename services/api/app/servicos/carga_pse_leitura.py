"""`carga_pse` no `GET` da atividade (issue #298, ADR 0012, itens 6 e 7): a funcao pura de `metricas/carga_pse.py` mais os textos.

Calculada na leitura, nunca gravada. O objeto nao traz a observacao nem a sensacao: so a PSE (um numero) e a duracao, que ja sao da
atividade e do check-in devolvidos na mesma resposta ao proprio atleta. Nada daqui vai para log.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.db.models import Atividade, CheckinTreino
from app.metricas import carga_pse as cp

TEXTO_SEM_CHECKIN = "Sem check-in: a carga pela PSE precisa da PSE do treino."
TEXTO_SEM_DURACAO = "Treino sem duração registrada: sem carga pela PSE."


@dataclass(frozen=True)
class CargaPseLida:
    versao: str
    estado: str  # calculada | sem_checkin | sem_duracao
    pse: int | None
    minutos: float
    valor: float | None  # UA, sem arredondar
    valor_texto: str | None  # "270 UA", "272,5 UA"; so em `calculada`
    texto: str  # pronto para a tela


def numero_pt(x: float) -> str:
    """Inteiro sem casas ("270"); senao 1 casa com virgula ("272,5")."""
    return str(int(x)) if float(x).is_integer() else f"{x:.1f}".replace(".", ",")


def duracao_pt(minutos: float) -> str:
    """Minutos inteiros ("45 min") ou minutos e segundos ("45 min 25 s"), para a conta fechar a mao (#316)."""
    total = round(minutos * 60)
    m, seg = divmod(total, 60)
    return f"{m} min" if seg == 0 else f"{m} min {seg} s"


def carga_pse_da_atividade(a: Atividade, c: CheckinTreino | None) -> CargaPseLida | None:
    """`None` em `multiesporte_pai` e `troca`; senao o estado, o valor e os textos."""
    r = cp.carga_pse(None if c is None else c.pse, a.duracao_s, a.subtipo)
    if r is None:
        return None
    if r.estado == cp.CALCULADA:
        valor_texto = f"{numero_pt(r.valor)} UA"
        texto = f"Carga pela PSE: {r.pse} x {duracao_pt(r.minutos)} = {valor_texto}."
    else:
        valor_texto = None
        texto = TEXTO_SEM_CHECKIN if r.estado == cp.SEM_CHECKIN else TEXTO_SEM_DURACAO
    return CargaPseLida(r.versao, r.estado, r.pse, r.minutos, r.valor, valor_texto, texto)
