"""Tipo de treino: encaixe na semana-padrão e regra de reserva (issue #262, ADR 0011).

Função pura: sem banco, sem rede, sem IA. Regra, exemplos e limites em docs/metricas/tipo-treino.md. Qualquer mudança
de precedência, de encaixe, de constante, da tabela de reserva ou dos critérios de divergência exige subir ``VERSAO``
(gravada em ``atividade.tipo_versao``).

Fonte: regra própria do projeto (não há artigo): decisões do Angelo e do Theo de 09/11 (ADR 0011). A data local vem
da ADR 0003 e é calculada por quem chama (``Atividade.dia``). Os blocos vêm da ADR 0008 e a série de tiros de
``tiros_1km@6``; aqui entram já resumidos em ``estrutura``.

Precedência (ADR 0011, item 2): tipo confirmado / ``professor`` / ``trainingpeaks`` > semana-padrão > regra de reserva.
"""

from __future__ import annotations

from collections.abc import Hashable, Iterable, Sequence
from dataclasses import dataclass
from datetime import date, datetime

VERSAO = "tipo_treino@1"

# Constantes da regra de reserva (ADR 0011, item 5). Propostas; a calibração com o histórico real é da #269.
LEVE_MIN_S = 1200  # 20 min: corrida sem esforço abaixo disso fica sem tipo
LONGO_MIN_S = 4500  # 75 min: corrida sem esforço a partir daqui é `longo`
MIN_TIROS = 2  # a série de tiros da tiros_1km@6 exige 2 ou mais

SUBTIPOS_IGNORADOS = frozenset({"multiesporte_pai", "troca"})  # nunca recebem tipo (mesmo critério da carga, ADR 0010)
ORIGENS_PROTEGIDAS = frozenset({"professor", "trainingpeaks"})

# Resumo dos blocos da ADR 0008 (só corrida): todos `leve` / há esforço mas não é série / série de tiros.
SEM_ESFORCO, ESFORCO, TIROS = "sem_esforco", "esforco", "tiros"


@dataclass(frozen=True)
class Atividade:
    id: Hashable
    dia: date  # data local (ADR 0003)
    modalidade: str
    inicio: datetime  # desempate do dia
    duracao_s: float
    subtipo: str | None = None
    tipo_treino: str | None = None  # tipo já gravado
    tipo_origem: str | None = None
    tipo_confirmado: bool = False
    estrutura: str | None = None  # SEM_ESFORCO, ESFORCO, TIROS ou None (sem blocos gravados)
    n_tiros: int = 0


@dataclass(frozen=True)
class Item:
    dia_semana: int  # ISO: 1 = segunda ... 7 = domingo
    modalidade: str
    tipo_treino: str | None  # None = "treina essa modalidade nesse dia, sem tipo"


@dataclass(frozen=True)
class Vigencia:
    vigente_desde: date
    itens: tuple[Item, ...]


@dataclass(frozen=True)
class Resultado:
    tipo_treino: str | None
    tipo_origem: str | None
    divergencia: str | None  # sem_esforco | tem_tiros (só com origem semana_padrao)
    versao: str | None  # VERSAO quando a regra escreveu (sugestao ou semana_padrao); None nas demais origens


SEM_TIPO = Resultado(None, None, None, None)


def vigencia_na_data(vigencias: Iterable[Vigencia], dia: date) -> Vigencia | None:
    """Maior ``vigente_desde <= dia``. Sem nenhuma, não há plano: nunca olha a vigência seguinte (ADR 0011, item 1)."""
    candidatas = [v for v in vigencias if v.vigente_desde <= dia]
    return max(candidatas, key=lambda v: v.vigente_desde) if candidatas else None


def _chave_id(id_: Hashable) -> tuple[int, int | str]:
    """Menor id: inteiros ordenam como números (9 antes de 10); os demais, como texto, depois dos inteiros."""
    return (0, id_) if isinstance(id_, int) else (1, str(id_))


def _protegida(a: Atividade) -> bool:
    return a.tipo_confirmado or a.tipo_origem in ORIGENS_PROTEGIDAS


def _com_tiros(a: Atividade) -> bool:
    return a.estrutura == TIROS and a.n_tiros >= MIN_TIROS


def _divergencia(a: Atividade, plano: str) -> str | None:
    """Só corrida com blocos gravados (ADR 0011, item 4)."""
    if a.modalidade != "corrida" or a.estrutura is None:
        return None
    if plano == "intervalado" and a.estrutura == SEM_ESFORCO:
        return "sem_esforco"
    if plano in ("leve", "longo") and _com_tiros(a):
        return "tem_tiros"
    return None


def reserva(a: Atividade) -> Resultado:
    """Regra de reserva (ADR 0011, item 5): só corrida; ``moderado`` e ``fartlek`` nunca saem daqui."""
    if a.modalidade != "corrida":
        return SEM_TIPO
    if _com_tiros(a):
        return Resultado("intervalado", "sugestao", None, VERSAO)
    if a.estrutura == SEM_ESFORCO:
        if a.duracao_s >= LONGO_MIN_S:
            return Resultado("longo", "sugestao", None, VERSAO)
        if a.duracao_s >= LEVE_MIN_S:
            return Resultado("leve", "sugestao", None, VERSAO)
    return SEM_TIPO


def classificar(atividades: Sequence[Atividade], vigencias: Sequence[Vigencia]) -> dict[Hashable, Resultado]:
    """Tipo, origem e divergência de cada atividade. Idempotente: não depende do tipo sugerido antes.

    1. Atividade com tipo confirmado ou origem ``professor``/``trainingpeaks`` mantém o tipo e a origem, sem versão
       nem divergência. Pai e troca do multiesporte nunca recebem tipo.
    2. O item do dia (mesmo dia da semana local e modalidade, com tipo) vale para UMA atividade por modalidade e dia:
       a de maior ``duracao_s``, empate pela de ``inicio`` mais cedo, depois pelo menor ``id``. A escolhida pode ser
       protegida: ela consome o item. As demais seguem para a reserva.
    3. Sem tipo do plano (sem plano, sem item, item sem tipo ou não escolhida): regra de reserva.
    """
    elegiveis = [a for a in atividades if a.subtipo not in SUBTIPOS_IGNORADOS]
    dono: dict[tuple[date, str], Atividade] = {}
    for a in sorted(elegiveis, key=lambda a: (-a.duracao_s, a.inicio, _chave_id(a.id))):
        dono.setdefault((a.dia, a.modalidade), a)

    saida: dict[Hashable, Resultado] = {}
    for a in atividades:
        if a.subtipo in SUBTIPOS_IGNORADOS:
            saida[a.id] = SEM_TIPO
        elif _protegida(a):
            saida[a.id] = Resultado(a.tipo_treino, a.tipo_origem, None, None)
        else:
            vig = vigencia_na_data(vigencias, a.dia)
            plano = None
            if vig is not None and dono[(a.dia, a.modalidade)].id == a.id:
                plano = next(
                    (i.tipo_treino for i in vig.itens if i.dia_semana == a.dia.isoweekday() and i.modalidade == a.modalidade),
                    None,
                )
            if plano is not None:
                saida[a.id] = Resultado(plano, "semana_padrao", _divergencia(a, plano), VERSAO)
            else:
                saida[a.id] = reserva(a)
    return saida
