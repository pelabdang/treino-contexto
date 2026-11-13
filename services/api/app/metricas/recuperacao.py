"""`recuperacao@1`: a noite anterior ao treino comparada com o normal do próprio atleta (issue #373, ADR 0014).

Função pura: sem banco, sem rede, sem IA. Regra, exemplos e limites em docs/metricas/recuperacao.md. Qualquer mudança de
janela, mínimo, piso, limite, medida ou regra da noite do treino exige subir ``VERSAO``.

Fórmulas e fontes (as mesmas da ``linha_base@2``, ADR 0011):
  mediana = mediana(x) ;  MAD = mediana(|x_i - mediana|) ;
  desvio = max(1,4826 x MAD, PISO_REL x |mediana|) ;  z = (valor - mediana) / desvio.
  Mediana e MAD no lugar de média e desvio padrão: Leys, C. et al. (2013), "Detecting outliers: do not use standard
  deviation around the mean, use absolute deviation around the median", J. Exp. Soc. Psychol. 49(4):764-766 (limites 2, 2,5
  e 3). Constante 1,4826: Rousseeuw, P. J. e Croux, C. (1993), JASA 88(424):1273-1283. (Citações ainda a conferir nos
  textos, ADR 0011 "Fontes".)
  Escolhas nossas, sem artigo, sem calibração (Angelo, 12/11, ADR 0014): janela de 28 noites, mínimo de 14 noites com valor,
  ``PISO_REL`` de 0,05, limite 2,0 e corte das 06:00 para o treino de madrugada. Não é limiar clínico: só a comparação
  com o histórico do próprio atleta; "abaixo" e "acima" são direção, nunca bom ou ruim.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, time, timedelta

from app.metricas.linha_base import medida_robusta

VERSAO = "recuperacao@1"

MEDIDAS = ("sono", "vfc", "fc_repouso")  # ordem fixa do pacote (ADR 0014, item 4)

# Estados da medida.
DENTRO, ABAIXO, ACIMA, APRENDENDO, SEM_DADO = "dentro", "abaixo", "acima", "aprendendo", "sem_dado"
# Estados do bloco e motivos de ``sem_dado``.
OK = "ok"
SEM_NOITE, TREINO_DE_MADRUGADA, FORA_DO_PERIODO = "sem_noite", "treino_de_madrugada", "fora_do_periodo"


@dataclass(frozen=True)
class Parametros:
    janela_noites: int = 28  # escolha nossa (ADR 0014, item 3)
    minimo_noites: int = 14  # por medida, escolha nossa
    limite_fora: float = 2.0  # |z| >= 2,0: abaixo ou acima; escolha nossa
    piso_rel: float = 0.05  # 5% da mediana, escolha nossa, a calibrar
    mad_escala: float = 1.4826
    hora_corte: time = time(6, 0)  # treino antes disso: sem recuperação (ADR 0014, item 2)


PADRAO = Parametros()


@dataclass(frozen=True)
class Noite:
    """Uma linha de ``recuperacao_dia``: ``noite`` é a data local de acordar; ``None`` = a medida não veio."""

    noite: date
    sono_s: float | None = None
    vfc_ms: float | None = None
    fc_repouso_bpm: float | None = None

    def valor(self, chave: str) -> float | None:
        return {"sono": self.sono_s, "vfc": self.vfc_ms, "fc_repouso": self.fc_repouso_bpm}[chave]

    def vazia(self) -> bool:
        return all(self.valor(c) is None for c in MEDIDAS)


@dataclass(frozen=True)
class MedidaRecuperacao:
    chave: str
    estado: str  # dentro | abaixo | acima | aprendendo | sem_dado
    valor: float | None
    n: int  # noites da janela com valor desta medida
    mediana: float | None = None
    desvio: float | None = None
    z: float | None = None


@dataclass(frozen=True)
class Recuperacao:
    versao: str
    estado: str  # ok | sem_dado
    motivo: str | None  # só em sem_dado
    medidas: tuple[MedidaRecuperacao, ...]  # vazio em sem_dado


def noite_do_treino(dia: date, hora: time, noites: Sequence[Noite], p: Parametros = PADRAO,
                    primeira_noite: date | None = None) -> tuple[Noite | None, str | None]:
    """A noite que liga ao treino de data local ``dia`` e hora local ``hora`` (ADR 0014, item 2), ou o motivo de não haver.

    ``(noite, None)`` quando há; senão ``(None, motivo)``. Ordem: treino antes do corte (``treino_de_madrugada``), treino
    anterior à noite mais antiga gravada (``fora_do_periodo``), noite de ``dia`` ausente ou sem nenhuma medida (``sem_noite``).
    ``primeira_noite`` é a noite mais antiga que o atleta tem gravada (``recuperacao_banco.primeira_noite``): o banco passa-a
    porque ``noites`` pode ser só uma janela. Omitida, vale a mais antiga de ``noites``.
    Sem nenhuma noite gravada: ``sem_noite`` (a busca nunca rodou). É a mesma regra para montar o pacote e para a comparação do
    "desatualizado" (madrugada, fora do período e sem noite valem ``None`` dos dois lados).
    """
    if hora < p.hora_corte:
        return None, TREINO_DE_MADRUGADA
    primeira = primeira_noite if primeira_noite is not None else min((n.noite for n in noites), default=None)
    if primeira is not None and dia < primeira:
        return None, FORA_DO_PERIODO
    achada = next((n for n in noites if n.noite == dia and not n.vazia()), None)
    if achada is None:
        return None, SEM_NOITE
    return achada, None


def _medida(chave: str, valor: float | None, janela: Sequence[float], p: Parametros) -> MedidaRecuperacao:
    n = len(janela)
    if valor is None:
        return MedidaRecuperacao(chave, SEM_DADO, None, n)
    if n < p.minimo_noites:
        return MedidaRecuperacao(chave, APRENDENDO, valor, n)
    mediana, desvio = medida_robusta(janela, p)
    z = (valor - mediana) / desvio
    estado = ABAIXO if z <= -p.limite_fora else ACIMA if z >= p.limite_fora else DENTRO
    return MedidaRecuperacao(chave, estado, valor, n, mediana, desvio, z)


def recuperacao(dia: date, hora: time, noites: Sequence[Noite], p: Parametros = PADRAO,
                primeira_noite: date | None = None) -> Recuperacao:
    """Recuperação da noite anterior ao treino, comparada com o normal do atleta (ADR 0014, itens 2 e 3).

    A janela são as ``janela_noites`` noites que terminam na véspera da noite do treino (``dia - 28`` a ``dia - 1``,
    extremos incluídos); a própria noite do treino não entra. Cada medida conta só as noites que têm valor e é
    comparada à parte: menos de ``minimo_noites`` valores é ``aprendendo`` (sem mediana); ``sem_dado`` é a noite sem
    valor da medida. O bloco é ``ok`` quando a noite tem ao menos uma medida.
    """
    noite, motivo = noite_do_treino(dia, hora, noites, p, primeira_noite)
    if noite is None:
        return Recuperacao(VERSAO, "sem_dado", motivo, ())
    desde = dia - timedelta(days=p.janela_noites)
    janela = [n for n in noites if desde <= n.noite <= dia - timedelta(days=1)]
    medidas = []
    for chave in MEDIDAS:
        xs = [v for v in (n.valor(chave) for n in janela) if v is not None]
        medidas.append(_medida(chave, noite.valor(chave), xs, p))
    return Recuperacao(VERSAO, OK, None, tuple(medidas))
