"""A frase da evolucao (`frase_evolucao@1`): as ultimas 4 semanas contra as 4 anteriores, em texto fixo. Funcao pura: sem banco, sem rede, sem IA.

DESCRICAO, nunca recomendacao: nada de "deve", "evite", nada de "melhorou/piorou", adjetivo de valor, causa ou sigla. Os textos sao fixos e aprovados pelo
Caio; mudar um texto, um piso, uma janela ou um minimo sobe a versao (`frase_evolucao@2`). Regra e exemplos a mao: docs/metricas/evolucao-series.md.

REGRAS (todas sobre a data LOCAL do treino; `hoje` vem de quem chama, como `hoje_do_atleta`):
  Janelas por treino: R = os 28 dias que terminam ONTEM; A = os 28 dias antes de R. Cada treino e um ponto; ponto sem valor (None ou nao finito) nao
    entra na conta, so no aviso.
  Minimo: 3 pontos com valor em cada janela (parametro `minimo`; 2 no melhor esforco de tiros). R vazia -> "sem treinos"; senao R ou A abaixo do
    minimo -> "poucos".
  Estatistica: mediana de cada janela. As regras decidem sobre os valores MOSTRADOS (arredondados, meio para cima), como a `frase_forma`:
    d = mR - mA; L = max(piso_abs, piso_rel x |mA|); |d| < L -> "parecido" (o limite entra como diferenca).
  Direcao: so a palavra do eixo (mais rapido/lento; mais alta/baixa; mais/menos); `a_favor` diz se a mudanca foi no sentido do "melhor" da serie, SO para
    quem desenha (cor/icone neutros); nunca vai para o texto.
  Aviso: pontos sem valor sao 20% ou mais dos treinos de R -> o texto diz quantos ficaram de fora.
  Volume (`volume_*`): os pontos sao treinos e a funcao soma por semana ISO (semana sem treino vale 0). R = 4 semanas completas ate o domingo passado
    (a semana em curso fica fora; no proprio domingo tambem, pois o dia ainda nao acabou), A = as 4 antes. Mediana das 4 somas; L = 10% de mA; minimo 1 treino
    com valor em cada janela (`minimo` pode subir); percentual so se mA >= 3 km, 0,5 h ou 300 m.
  Condicionamento (`ctl`): os pontos sao dias (`aprendendo` marca o dia que ainda aprende). Compara o de ontem com o de 28 dias antes; limiar =
    max(2, 5% do de 28 dias antes), sobre inteiros; dia `aprendendo` em qualquer ponta: so o valor. Acrescenta o maior valor do periodo (dias sem aprender).

Os pisos de pace (3%), FC (4 bpm) e carga por hora (5%) sao os da `linha_base@3`; os demais (3% em eficiencia e velocidade, 10% em volume, 5%/2 pontos em
condicionamento), as janelas, o minimo e o 20% sao ESCOLHA DE ENGENHARIA para descrever, sem artigo e sem calibracao. Fonte da mediana e da MAD:
Leys et al. (2013), J. Exp. Soc. Psychol. 49(4):764-766 (citacao a conferir, ADR 0011); condicionamento: Banister et al. (1976).
"""

from __future__ import annotations

import math
import statistics
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Literal

VERSAO = "frase_evolucao@1"
JANELA_DIAS = 28
MINIMO_PADRAO = 3
FRACAO_SEM_VALOR_AVISO = 0.20
VOLUME_PISO_REL = 0.10
CTL_PISO_ABS = 2
CTL_PISO_REL = 0.05

Tipo = Literal["sem_treino", "poucos", "comparada", "so_valor", "sem_dado"]
Mudanca = Literal["maior", "menor", "parecido"]
Sentido = Literal["menor", "maior"]


@dataclass(frozen=True)
class Ponto:
    """Um treino (ou, no condicionamento, um dia). `valor` None = a medida nao existe nesse treino (ex.: sem FC)."""

    dia: date
    valor: float | None
    aprendendo: bool = False


@dataclass(frozen=True)
class FraseEvolucao:
    versao: str
    tipo: Tipo
    mudanca: Mudanca | None  # direcao do VALOR (maior/menor/parecido); None se nao houve comparacao
    a_favor: bool | None  # a mudanca foi no sentido do "melhor" da serie; None se parecido ou sem comparacao. Nunca entra no texto
    texto: str
    valor_atual: float | None = None  # mediana mostrada de R (ou o condicionamento de ontem)
    valor_anterior: float | None = None
    n_atual: int = 0
    n_anterior: int = 0


@dataclass(frozen=True)
class Medida:
    """O que muda de uma serie para outra: o piso, as palavras e o formato dos numeros mostrados."""

    titulo: str
    sentido_melhor: Sentido
    piso_abs: float
    piso_rel: float
    casas: int  # casas do valor mostrado (0 = inteiro; pace em segundos)
    mais: str  # palavra do eixo quando o valor subiu
    menos: str
    parecido: str
    nome_medida: str  # "pace", "frequencia cardiaca": no aviso de treinos sem valor
    percentual: bool = False  # a diferenca aparece em % (eficiencia)


MEDIDAS: dict[str, Medida] = {
    "pace_km": Medida("Pace", "menor", 0, 0.03, 0, "mais lento", "mais rápido", "parecido", "pace"),
    "pace_100m": Medida("Ritmo por 100 m", "menor", 0, 0.03, 0, "mais lento", "mais rápido", "parecido", "ritmo"),
    "fc": Medida("Frequência cardíaca", "menor", 4, 0, 0, "mais alta", "mais baixa", "parecida", "frequência cardíaca"),
    "eficiencia": Medida("Metros por batimento", "maior", 0, 0.03, 2, "mais", "menos", "parecida", "frequência cardíaca", percentual=True),
    "velocidade": Medida("Velocidade", "maior", 0, 0.03, 1, "mais rápida", "mais lenta", "parecida", "velocidade"),
}
VOLUMES: dict[str, tuple[str, str, int, float]] = {  # tipo -> (titulo, unidade, casas, base minima para o percentual)
    "volume_km": ("Volume", "km", 1, 3.0),
    "volume_h": ("Volume", "h", 1, 0.5),
    "volume_m": ("Volume", "m", 0, 300.0),
}
TIPOS = (*MEDIDAS, *VOLUMES, "ctl")

# ---------- textos fixos (aprovados pelo Caio) ----------
TEXTO_SEM_TREINO = "Sem treinos desse tipo nas últimas 4 semanas."
TEXTO_POUCOS = "Poucos treinos para comparar: {nR} nas últimas 4 semanas, {nA} nas 4 anteriores."
TEXTO_COMPARADA = "{titulo} nas últimas 4 semanas: {vR} (mediana de {nR} treinos), {dif} que nas 4 semanas anteriores ({vA}, {nA} treinos)."
TEXTO_PARECIDO = "{titulo} nas últimas 4 semanas: {vR} (mediana de {nR} treinos), {parecido} com as 4 semanas anteriores ({vA}, {nA} treinos)."
TEXTO_VOLUME = "{titulo} nas últimas 4 semanas: {vR} por semana (mediana), {dif} que nas 4 semanas anteriores ({vA} por semana)."
TEXTO_VOLUME_PARECIDO = "{titulo} nas últimas 4 semanas: {vR} por semana (mediana), parecido com as 4 semanas anteriores ({vA} por semana)."
AVISO_SEM_VALOR_UM = "1 dos {n} treinos ficou de fora porque não tem {medida}."
AVISO_SEM_VALOR_VARIOS = "{k} dos {n} treinos ficaram de fora porque não têm {medida}."
TEXTO_CTL_SEM_DADO = "Sem condicionamento calculado até ontem."
TEXTO_CTL_VALOR = "Seu condicionamento está em {c}."
TEXTO_CTL_PARECIDO = "Seu condicionamento está em {c}, estável em relação a 4 semanas atrás ({c28})."
TEXTO_CTL_MAIOR = "Seu condicionamento está em {c}, acima do de 4 semanas atrás ({c28})."
TEXTO_CTL_MENOR = "Seu condicionamento está em {c}, abaixo do de 4 semanas atrás ({c28})."
TEXTO_CTL_MAXIMO = "O maior valor do período foi {m}, em {dia}."


# ---------- numeros ----------
def arredonda(x: float, casas: int = 0) -> float:
    """Meio para cima (a mesma `int(x + 0.5)` da `frase_forma`); o 1e-9 so absorve a imprecisao do ponto flutuante."""
    f = 10**casas
    return math.floor(x * f + 0.5 + 1e-9) / f


def _num(x: float, casas: int) -> str:
    s = f"{x:.{casas}f}".replace(".", ",")
    return s[:-2] if casas and s.endswith(",0") else s


def _mmss(s: float) -> str:
    s = int(s)
    return f"{s // 60}:{s % 60:02d}"


def _mostra(tipo: str, x: float) -> str:
    """O valor com a unidade."""
    if tipo == "pace_km":
        return f"{_mmss(x)}/km"
    if tipo == "pace_100m":
        return f"{_mmss(x)}/100 m"
    if tipo == "fc":
        return f"{_num(x, 0)} bpm"
    if tipo == "eficiencia":
        return f"{_num(x, 2)} m/bat"
    if tipo == "velocidade":
        return f"{_num(x, 1)} km/h"
    unidade = VOLUMES[tipo][1]
    return f"{_num(x, VOLUMES[tipo][2])} {unidade}"


def _dif(tipo: str, d: float, base: float) -> str:
    d = abs(d)
    if tipo == "pace_km":
        return f"{_num(d, 0)} s/km"
    if tipo == "pace_100m":
        return f"{_num(d, 0)} s/100 m"
    if tipo == "fc":
        return f"{_num(d, 0)} bpm"
    if tipo == "eficiencia":
        return f"{_num(arredonda(100 * d / base), 0)}%"  # percentual sobre a base mostrada
    if tipo == "velocidade":
        return f"{_num(d, 1)} km/h"
    return f"{_num(d, VOLUMES[tipo][2])} {VOLUMES[tipo][1]}"


def _validos(pontos: Sequence[Ponto], ini: date, fim: date) -> tuple[list[float], int]:
    """(valores validos, total de pontos) com `ini <= dia <= fim`."""
    na_janela = [p for p in pontos if ini <= p.dia <= fim]
    return [p.valor for p in na_janela if p.valor is not None and math.isfinite(p.valor)], len(na_janela)


def _a_favor(sentido: Sentido, mudanca: Mudanca) -> bool | None:
    return None if mudanca == "parecido" else mudanca == sentido


def _poucos(nr: int, na: int) -> FraseEvolucao:
    if nr == 0:
        return FraseEvolucao(VERSAO, "sem_treino", None, None, TEXTO_SEM_TREINO, None, None, 0, na)
    return FraseEvolucao(VERSAO, "poucos", None, None, TEXTO_POUCOS.format(nR=nr, nA=na), None, None, nr, na)


# ---------- por treino (pace, FC, eficiencia, velocidade) ----------
def _por_treino(tipo: str, pontos: Sequence[Ponto], hoje: date, titulo: str | None, minimo: int) -> FraseEvolucao:
    m = MEDIDAS[tipo]
    ontem = hoje - timedelta(days=1)
    vr, total_r = _validos(pontos, ontem - timedelta(days=JANELA_DIAS - 1), ontem)
    va, _ = _validos(pontos, ontem - timedelta(days=2 * JANELA_DIAS - 1), ontem - timedelta(days=JANELA_DIAS))
    if not vr or len(vr) < minimo or len(va) < minimo:
        out = _poucos(len(vr), len(va))
        return _com_aviso(out, total_r, len(vr), m)
    mr, ma = arredonda(statistics.median(vr), m.casas), arredonda(statistics.median(va), m.casas)
    d = arredonda(mr - ma, m.casas)
    limite = max(m.piso_abs, m.piso_rel * abs(ma))
    nome = titulo or m.titulo
    if abs(d) < limite - 1e-9 or d == 0:
        texto = TEXTO_PARECIDO.format(titulo=nome, vR=_mostra(tipo, mr), nR=len(vr), parecido=m.parecido, vA=_mostra(tipo, ma), nA=len(va))
        out = FraseEvolucao(VERSAO, "comparada", "parecido", None, texto, mr, ma, len(vr), len(va))
    else:
        mud: Mudanca = "maior" if d > 0 else "menor"
        dif = f"{_dif(tipo, d, ma)} {m.mais if d > 0 else m.menos}"
        texto = TEXTO_COMPARADA.format(titulo=nome, vR=_mostra(tipo, mr), nR=len(vr), dif=dif, vA=_mostra(tipo, ma), nA=len(va))
        out = FraseEvolucao(VERSAO, "comparada", mud, _a_favor(m.sentido_melhor, mud), texto, mr, ma, len(vr), len(va))
    return _com_aviso(out, total_r, len(vr), m)


def _com_aviso(out: FraseEvolucao, total_r: int, validos_r: int, m: Medida) -> FraseEvolucao:
    k = total_r - validos_r
    if k <= 0 or k < FRACAO_SEM_VALOR_AVISO * total_r - 1e-9:
        return out
    aviso = AVISO_SEM_VALOR_UM if k == 1 else AVISO_SEM_VALOR_VARIOS
    texto = out.texto + " " + aviso.format(k=k, n=total_r, medida=m.nome_medida)
    return FraseEvolucao(out.versao, out.tipo, out.mudanca, out.a_favor, texto, out.valor_atual, out.valor_anterior, out.n_atual, out.n_anterior)


# ---------- volume ----------
def _somas_semanais(pontos: Sequence[Ponto], domingo: date) -> tuple[list[float], list[float], int, int]:
    """(somas de R, somas de A, treinos de R, treinos de A); R = 4 semanas ate `domingo`, A = as 4 antes."""
    ini_r = domingo - timedelta(days=JANELA_DIAS - 1)
    ini_a = ini_r - timedelta(days=JANELA_DIAS)
    somas = [0.0] * 8  # 0..3 = A (mais antiga primeiro), 4..7 = R
    n = [0, 0]
    for p in pontos:
        if p.valor is None or not math.isfinite(p.valor) or not ini_a <= p.dia <= domingo:
            continue
        somas[(p.dia - ini_a).days // 7] += p.valor
        n[(p.dia - ini_a).days // JANELA_DIAS] += 1
    return somas[4:], somas[:4], n[1], n[0]


def _volume(tipo: str, pontos: Sequence[Ponto], hoje: date, titulo: str | None, minimo: int) -> FraseEvolucao:
    nome_padrao, _, casas, base_min = VOLUMES[tipo]
    domingo = hoje - timedelta(days=hoje.isoweekday())
    sr, sa, nr, na = _somas_semanais(pontos, domingo)
    if nr == 0 or nr < minimo or na < minimo:
        return _poucos(nr, na)
    mr, ma = arredonda(statistics.median(sr), casas), arredonda(statistics.median(sa), casas)
    d = arredonda(mr - ma, casas)
    nome = titulo or nome_padrao
    if abs(d) < VOLUME_PISO_REL * abs(ma) - 1e-9 or d == 0:
        texto = TEXTO_VOLUME_PARECIDO.format(titulo=nome, vR=_mostra(tipo, mr), vA=_mostra(tipo, ma))
        return FraseEvolucao(VERSAO, "comparada", "parecido", None, texto, mr, ma, nr, na)
    mud: Mudanca = "maior" if d > 0 else "menor"
    dif = f"{_mostra(tipo, abs(d))} a {'mais' if d > 0 else 'menos'}"
    if ma >= base_min:
        dif += f" ({_num(arredonda(100 * abs(d) / ma), 0)}%)"
    texto = TEXTO_VOLUME.format(titulo=nome, vR=_mostra(tipo, mr), dif=dif, vA=_mostra(tipo, ma))
    return FraseEvolucao(VERSAO, "comparada", mud, _a_favor("maior", mud), texto, mr, ma, nr, na)


# ---------- condicionamento ----------
def _ctl(pontos: Sequence[Ponto], hoje: date) -> FraseEvolucao:
    ontem = hoje - timedelta(days=1)
    por_dia = {p.dia: p for p in pontos if p.valor is not None and math.isfinite(p.valor)}
    p, p28 = por_dia.get(ontem), por_dia.get(ontem - timedelta(days=JANELA_DIAS))
    if p is None:
        return FraseEvolucao(VERSAO, "sem_dado", None, None, TEXTO_CTL_SEM_DADO)
    c = int(arredonda(p.valor))
    maximo = ""
    maduros = [q for q in pontos if q.valor is not None and math.isfinite(q.valor) and not q.aprendendo and q.dia <= ontem]
    if maduros:
        q = max(maduros, key=lambda x: (x.valor, -x.dia.toordinal()))  # empate: o primeiro dia
        maximo = " " + TEXTO_CTL_MAXIMO.format(m=int(arredonda(q.valor)), dia=q.dia.strftime("%d/%m"))
    if p.aprendendo or p28 is None or p28.aprendendo:
        return FraseEvolucao(VERSAO, "so_valor", None, None, TEXTO_CTL_VALOR.format(c=c) + maximo, c, None, 1, 0)
    c28 = int(arredonda(p28.valor))
    d = c - c28
    if abs(d) < max(CTL_PISO_ABS, CTL_PISO_REL * c28) - 1e-9:
        return FraseEvolucao(VERSAO, "comparada", "parecido", None, TEXTO_CTL_PARECIDO.format(c=c, c28=c28) + maximo, c, c28, 1, 1)
    mud: Mudanca = "maior" if d > 0 else "menor"
    texto = (TEXTO_CTL_MAIOR if d > 0 else TEXTO_CTL_MENOR).format(c=c, c28=c28) + maximo
    return FraseEvolucao(VERSAO, "comparada", mud, _a_favor("maior", mud), texto, c, c28, 1, 1)


def frase_evolucao(tipo: str, pontos: Sequence[Ponto], hoje: date, titulo: str | None = None, minimo: int | None = None) -> FraseEvolucao:
    """A frase de uma serie.

    `tipo`: um de `TIPOS` ("pace_km", "pace_100m", "fc", "eficiencia", "velocidade", "volume_km", "volume_h", "volume_m", "ctl").
    `pontos`: os treinos da serie (varios por dia vale), qualquer ordem e periodo; so entram os das janelas.
    `hoje`: a data local do atleta (o dia ainda nao acabou: as janelas terminam ontem).
    `titulo`: o sujeito da frase ("Pace dos seus treinos leves"); padrao: o nome da medida. Ignorado no condicionamento.
    `minimo`: pontos por janela; padrao 3 (2 no melhor esforco de tiros), 1 no volume. Ignorado no condicionamento.
    Sempre devolve uma frase (a serie sem treinos tem o seu texto)."""
    if tipo not in TIPOS:
        raise ValueError(f"tipo de serie desconhecido: {tipo!r}")
    if tipo == "ctl":
        return _ctl(pontos, hoje)
    if tipo in VOLUMES:
        return _volume(tipo, pontos, hoje, titulo, 1 if minimo is None else minimo)
    return _por_treino(tipo, pontos, hoje, titulo, MINIMO_PADRAO if minimo is None else minimo)
