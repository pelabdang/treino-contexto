"""Textos prontos da carga e da forma do dia no `GET` da atividade (issue #464, spec da tela #463, ADR 0004 adendo 12).

A API formata, o app mostra: 1 casa com virgula; o TSB leva sinal explicito, com o menos U+2212. Sem banco aqui, so texto e a
escolha do dia da serie (`forma_do_dia`). Nada de limiar nem zona.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from app.metricas import serie_carga as sc

MENOS = "−"

METODO_TEXTO = {"rtss": "Estimada pelo pace.", "hrtss": "Estimada pela FC."}
PENDENTE_TEXTO = "A carga deste treino ainda não foi calculada."
MOTIVO_TEXTO = {
    "sem_dados_saude": "Sem a FC de repouso e a máxima no seu perfil, não dá para estimar a carga deste treino.",
    "sem_limiar_na_data": "Sem o limiar cadastrado para esta data, não dá para estimar a carga.",
    "sem_fc": "Este treino não tem frequência cardíaca, então não dá para estimar a carga pela FC.",
    "sem_pace": "Este treino não tem pace, então não dá para estimar a carga pelo pace.",
    "cobertura_insuficiente": "A frequência cardíaca cobre pouco do treino, então a carga não foi estimada.",
    "modalidade_sem_carga": "Este tipo de treino não tem carga estimada.",
}


def numero_texto(x: float) -> str:
    """1 casa, virgula ("87,4")."""
    return f"{x:.1f}".replace(".", ",")


def tsb_texto(x: float) -> str:
    """Sinal sempre explicito: "+3,2", "−11,6"; zero (depois de arredondar) e "0,0"."""
    t = numero_texto(abs(x))
    if t == "0,0":
        return t
    return ("+" if x > 0 else MENOS) + t


def sem_carga_texto(n: int) -> str | None:
    if n <= 0:
        return None
    quem = "1 treino deste dia sem carga calculada" if n == 1 else f"{n} treinos deste dia sem carga calculada"
    return f"Há {quem}; a forma pode estar subestimada."


def aprendendo_texto(faltam: int) -> str:
    dias = "1 dia" if faltam == 1 else f"{faltam} dias"
    verbo = "falta" if faltam == 1 else "faltam"
    return f"Ainda aprendendo a sua forma: {verbo} {dias} de histórico para estimar."


@dataclass(frozen=True)
class FormaDoDia:
    estado: str  # calculada | aprendendo | sem_serie
    data_local: str
    ctl_texto: str | None
    atl_texto: str | None
    tsb_texto: str | None
    texto_aprendendo: str | None
    sem_carga_no_dia: int
    texto_sem_carga: str | None


def forma_do_dia(serie: sc.SerieCarga, dia: date) -> FormaDoDia:
    """CTL, ATL e TSB do fim do `dia` local. `sem_serie`: o dia nao esta na serie (nenhuma carga calculada ate aqui, ou a
    unica atividade do dia ainda esta `pendente`). `aprendendo` (menos de 42 dias desde o primeiro dia): os tres numeros NAO saem."""
    d = next((x for x in serie.dias if x.dia == dia), None)
    if d is None:
        return FormaDoDia("sem_serie", dia.isoformat(), None, None, None, None, 0, None)
    comum = dict(data_local=dia.isoformat(), sem_carga_no_dia=d.sem_carga, texto_sem_carga=sem_carga_texto(d.sem_carga))
    if d.aprendendo:
        faltam = sc.DIAS_APRENDENDO - (dia - serie.dias[0].dia).days
        return FormaDoDia("aprendendo", ctl_texto=None, atl_texto=None, tsb_texto=None,
                          texto_aprendendo=aprendendo_texto(faltam), **comum)
    return FormaDoDia("calculada", ctl_texto=numero_texto(d.ctl), atl_texto=numero_texto(d.atl), tsb_texto=tsb_texto(d.tsb),
                      texto_aprendendo=None, **comum)
