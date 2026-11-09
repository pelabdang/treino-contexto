"""Carga pela PSE: PSE x minutos (issue #297, ADR 0012, item 6).

Função pura: sem banco, sem rede, sem IA. Regra, exemplos e limites em docs/metricas/carga-pse.md. Qualquer mudança de
fórmula, dos minutos usados (cronômetro x tempo corrido), do tratamento de PSE 0 e de atividade sem duração, ou da regra
de elegibilidade exige subir ``VERSAO``.

Fórmula e fonte:
  carga_pse = PSE x minutos ;  minutos = duracao_s / 60 (tempo de cronômetro) ;  em UA (unidades arbitrárias).
  É a "sRPE" de Foster, C. et al. (2001), "A new approach to monitoring exercise training", J. Strength Cond. Res.
  15(1):109-115 (PSE da sessão na CR-10 modificada x duração em minutos); a CR-10 é de Borg, G. (1982), Med. Sci. Sports
  Exerc. 14(5):377-381, e Borg (1998), *Borg's Perceived Exertion and Pain Scales*, Human Kinetics. (Citações ainda a
  conferir nos textos, ADR 0012 "Fontes".) Escolha de usar o cronômetro e não o tempo total: regra própria do projeto
  (o tempo corrido não está gravado). Não se soma nem se compara com a ``carga@2`` (escalas diferentes).
"""

from __future__ import annotations

from dataclasses import dataclass

VERSAO = "carga_pse@1"

PSE_MIN, PSE_MAX = 0, 10  # CR-10 em inteiros (ADR 0012, item 2)
SUBTIPOS_SEM_CHECKIN = frozenset({"multiesporte_pai", "troca"})  # não pedem check-in nem têm carga pela PSE (ADR 0012, item 4)

CALCULADA, SEM_CHECKIN, SEM_DURACAO = "calculada", "sem_checkin", "sem_duracao"


@dataclass(frozen=True)
class CargaPse:
    versao: str
    estado: str  # calculada | sem_checkin | sem_duracao
    pse: int | None  # None em sem_checkin
    minutos: float  # duracao_s / 60
    valor: float | None  # UA; None fora de `calculada`


def elegivel(subtipo: str | None) -> bool:
    """Atividade que pede check-in e tem carga pela PSE: toda, menos o pai e a troca do multiesporte."""
    return subtipo not in SUBTIPOS_SEM_CHECKIN


def carga_pse(pse: int | None, duracao_s: float, subtipo: str | None = None) -> CargaPse | None:
    """Carga pela PSE de uma atividade, ou ``None`` se ela não é elegível (pai e troca).

    - sem check-in (``pse is None``): ``sem_checkin``, sem valor; nunca se estima a PSE;
    - com check-in e ``duracao_s <= 0``: ``sem_duracao``, sem valor;
    - senão ``calculada``: ``pse x duracao_s / 60``. PSE 0 vale 0.
    A PSE fora de 0 a 10 é erro de quem chama (a API já valida): levanta ``ValueError`` com mensagem fixa.
    """
    if not elegivel(subtipo):
        return None
    minutos = max(duracao_s, 0.0) / 60.0
    if pse is None:
        return CargaPse(VERSAO, SEM_CHECKIN, None, minutos, None)
    if not PSE_MIN <= pse <= PSE_MAX:
        raise ValueError("PSE fora de 0 a 10")
    if duracao_s <= 0:
        return CargaPse(VERSAO, SEM_DURACAO, pse, 0.0, None)
    return CargaPse(VERSAO, CALCULADA, pse, minutos, pse * minutos)
