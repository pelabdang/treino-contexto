"""A frase de analise da quinzena (`frase_forma@1`): fadiga (ATL) contra condicionamento (CTL), descrita em texto fixo.

DESCRICAO, nunca recomendacao: nada de "deve", "evite", "descanse", nada de adjetivo de valor (bom, ruim, risco, lesao) e nenhuma sigla (CTL, ATL,
TSB). Os textos sao fixos e aprovados pelo Caio; mudar um texto ou um limiar sobe a versao (`frase_forma@2`). Funcao pura: sem banco, sem rede, sem IA.

REGRAS (decidem SEMPRE sobre os INTEIROS mostrados, arredondados com `int(x + 0.5)`; F = fadiga de hoje, C = condicionamento de hoje; "hoje" aqui e o
ultimo dia da serie, que termina em `max(ontem, ultimo dia com atividade)`):
  R0 serie vazia: sem frase (quem chama devolve `None`; vale o `aviso` da API).
  R1 o dia esta `aprendendo`: sem comparacao; o texto e o `aprendendo_texto` ja existente.
  R2 nenhuma carga calculada nos 14 dias do grafico: texto proprio, sem faixa nem tendencia.
  Faixa (so se nao for R1 nem R2), com lim = max(2, 0,10 * C):
    |F - C| <= lim                      -> parecidos
    C >= 10 e F >= 1,5 * C              -> bem acima
    C >= 10 e F <= C / 1,5              -> bem abaixo
    F - C > lim                         -> acima
    C - F > lim                         -> abaixo
  Tendencia (so apos a faixa): C14 = condicionamento do PRIMEIRO dia do grafico (fim - 13), inteiro; limiar = max(2, 0,05 * C14);
    C - C14 >= limiar subiu; <= -limiar caiu; senao ficou perto. OMITIDA se o dia de C14 estava `aprendendo` (o numero nao existe).
  Avisos (valem tambem com R2; o de pendentes vem antes): "ha treinos ainda sem carga calculada" (`pendentes` > 0) e "treinos dos ultimos 14
    dias sem carga calculada" (so os sem dado; o motivo `modalidade_sem_carga` NAO conta: esse tipo de treino nao tem carga por definicao).

Os limiares (10 %, 1,5x, 5 %, 2 pontos, 14 dias) sao ESCOLHA DE ENGENHARIA para descrever, e nao valores publicados nem pontos de corte clinicos.
Fontes do que ha por tras dos numeros: modelo de impulso-resposta de Banister, Calvert, Savage e Bach (IEEE Trans. Syst. Man Cybern. SMC-6(2):94-102,
1976); a forma exata `1 - exp(-1/tau)` do GoldenCheetah (ver `app.metricas.serie_carga`). Nota (nunca no texto): a razao entre carga aguda e cronica
e estudada como marcador de risco de lesao (Impellizzeri et al., 2020, criticam esse uso); por isso a faixa "bem acima" so DESCREVE a diferenca e nao
diz nada sobre risco.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.metricas import serie_carga as sc
from app.servicos.carga_textos import aprendendo_texto

VERSAO = "frase_forma@1"
JANELA_DIAS = 14
LIMITE_MIN_PONTOS = 2
LIMITE_FRACAO_FAIXA = 0.10
FATOR_BEM = 1.5
CONDICIONAMENTO_MIN_BEM = 10
LIMITE_FRACAO_TENDENCIA = 0.05

Tipo = Literal["aprendendo", "sem_treino_recente", "parecidos", "acima", "abaixo", "bem_acima", "bem_abaixo"]
Tendencia = Literal["subiu", "caiu", "perto"]

# ---------- textos fixos (aprovados pelo Caio); `{F}` e `{C}` entram como inteiros ----------
TEXTO_SEM_TREINO = "Você não teve treino com carga calculada nos últimos 14 dias. Seu condicionamento está em {C} e sua fadiga em {F}."
TEXTOS_FAIXA: dict[str, str] = {
    "parecidos": "Sua fadiga ({F}) e o seu condicionamento ({C}) estão parecidos.",
    "acima": "Sua fadiga ({F}) está acima do seu condicionamento ({C}): seus últimos dias tiveram mais carga do que o seu ritmo das últimas semanas.",
    "abaixo": "Sua fadiga ({F}) está abaixo do seu condicionamento ({C}): seus últimos dias tiveram menos carga do que o seu ritmo das últimas semanas.",
    "bem_acima": "Sua fadiga ({F}) está bem acima do seu condicionamento ({C}): seus últimos dias tiveram bem mais carga do que o seu ritmo das últimas semanas.",
    "bem_abaixo": "Sua fadiga ({F}) está bem abaixo do seu condicionamento ({C}): seus últimos dias tiveram bem menos carga do que o seu ritmo das últimas semanas.",
}
TEXTOS_TENDENCIA: dict[str, str] = {
    "subiu": "Em 14 dias, seu condicionamento subiu de {C14} para {C}.",
    "caiu": "Em 14 dias, seu condicionamento caiu de {C14} para {C}.",
    "perto": "Em 14 dias, seu condicionamento ficou perto de {C}.",
}
AVISO_PENDENTES_UM = "Há 1 treino ainda sem carga calculada; a frase pode mudar quando ele for calculado."
AVISO_PENDENTES_VARIOS = "Há {n} treinos ainda sem carga calculada; a frase pode mudar quando forem calculados."
AVISO_SEM_CARGA_UM = "1 treino dos últimos 14 dias ficou sem carga calculada; os números podem estar subestimados."
AVISO_SEM_CARGA_VARIOS = "{n} treinos dos últimos 14 dias ficaram sem carga calculada; os números podem estar subestimados."


@dataclass(frozen=True)
class FraseForma:
    versao: str
    tipo: Tipo
    tendencia: Tendencia | None
    texto: str


def inteiro(x: float) -> int:
    """O inteiro mostrado: `int(x + 0.5)` (as regras decidem sobre ele, nunca sobre o decimal)."""
    return int(x + 0.5)


def faixa(f: int, c: int) -> str:
    lim = max(LIMITE_MIN_PONTOS, LIMITE_FRACAO_FAIXA * c)
    if abs(f - c) <= lim:
        return "parecidos"
    if c >= CONDICIONAMENTO_MIN_BEM:
        if 2 * f >= 3 * c:  # F >= 1,5 * C, sem ponto flutuante
            return "bem_acima"
        if 3 * f <= 2 * c:  # F <= C / 1,5
            return "bem_abaixo"
    return "acima" if f > c else "abaixo"


def tendencia(c14: int, c: int) -> str:
    limiar = max(LIMITE_MIN_PONTOS, LIMITE_FRACAO_TENDENCIA * c14)
    if c - c14 >= limiar:
        return "subiu"
    if c - c14 <= -limiar:
        return "caiu"
    return "perto"


def _avisos(pendentes: int, sem_carga: int) -> list[str]:
    out = []
    if pendentes > 0:
        out.append(AVISO_PENDENTES_UM if pendentes == 1 else AVISO_PENDENTES_VARIOS.format(n=pendentes))
    if sem_carga > 0:
        out.append(AVISO_SEM_CARGA_UM if sem_carga == 1 else AVISO_SEM_CARGA_VARIOS.format(n=sem_carga))
    return out


def frase_forma(serie: sc.SerieCarga, pendentes: int = 0) -> FraseForma | None:
    """`None` na serie vazia (R0). Os 14 dias do grafico sao os 14 ultimos de `serie.dias`."""
    if not serie.dias:
        return None
    janela = serie.dias[-JANELA_DIAS:]
    hoje = janela[-1]
    if hoje.aprendendo:
        faltam = sc.DIAS_APRENDENDO - (hoje.dia - serie.dias[0].dia).days
        return FraseForma(VERSAO, "aprendendo", None, aprendendo_texto(faltam))  # sem comparacao e sem avisos: nao ha o que comparar
    f, c = inteiro(hoje.atl), inteiro(hoje.ctl)
    avisos = _avisos(pendentes, sum(d.sem_carga_avisavel for d in janela))
    if not any(d.calculadas for d in janela):
        base = TEXTO_SEM_TREINO.format(F=f, C=c)
        return FraseForma(VERSAO, "sem_treino_recente", None, " ".join([base, *avisos]))
    tipo = faixa(f, c)
    partes = [TEXTOS_FAIXA[tipo].format(F=f, C=c)]
    tend = None
    primeiro = janela[0]
    if len(janela) == JANELA_DIAS and not primeiro.aprendendo:
        c14 = inteiro(primeiro.ctl)
        tend = tendencia(c14, c)
        partes.append(TEXTOS_TENDENCIA[tend].format(C14=c14, C=c))
    return FraseForma(VERSAO, tipo, tend, " ".join([*partes, *avisos]))
