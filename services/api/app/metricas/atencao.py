"""Atenção da caixa do dia do professor: os quatro motivos de `atencao@2` (issue #422, ADR 0015, item 4).

Função pura: sem banco, sem rede, sem IA, sem relógio (o `hoje` entra por parâmetro, a data local de `America/Sao_Paulo`).
Regra, exemplos e limites em docs/metricas/atencao.md. Qualquer mudança de motivo, janela, ordem ou texto exige subir ``VERSAO``.

Nada de número novo e nada de causa: cada motivo usa só o que o código já calcula (check-in `dor`, `linha_base@3`, divergência da
semana-padrão da ADR 0011, prazo do check-in da ADR 0012). Os limiares ``JANELA_DIAS``, ``AVISO_CHECKIN_DIAS`` e
``JANELA_NOVOS_DIAS`` são escolha nossa do produto (regra própria do projeto, sem artigo); o limite de "fora do normal" é o da
`linha_base@3` (``PADRAO.limite_fora``, 2,5; mediana e MAD: Leys et al., 2013, citação ainda a conferir, ADR 0011).

A entrada NÃO tem campo de observação nem de texto livre: só o booleano `dor` do check-in (ADR 0015, item 7).
"""

from __future__ import annotations

from collections.abc import Hashable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date

from app.metricas.carga_pse import elegivel
from app.metricas.linha_base import PADRAO

VERSAO = "atencao@2"  # @2 (issue #454): checkin_vencendo vira uma linha por aluno e a modalidade `outra` não gera o aviso

JANELA_DIAS = 7  # treinos de hoje - 7 a hoje; o mesmo prazo do check-in (ADR 0012)
PRAZO_CHECKIN_DIAS = 7  # `servicos.checkin.PRAZO_DIAS`
AVISO_CHECKIN_DIAS = 5  # avisa nos 3 últimos dias do prazo (5, 6 e 7 dias depois do treino)
JANELA_NOVOS_DIAS = 14  # treinos novos (tipo sugerido a confirmar): hoje - 14 a hoje
SEM_ATENCAO_TEXTO = "Nada a destacar nos últimos 7 dias."

DOR, FORA_DO_NORMAL, DIVERGENCIA, CHECKIN_VENCENDO = "dor", "fora_do_normal", "divergencia", "checkin_vencendo"
PRIORIDADE = (DOR, FORA_DO_NORMAL, DIVERGENCIA, CHECKIN_VENCENDO)  # ordem dos motivos no treino e entre atletas

DIAS_SEMANA = ("segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo")
# Ordem e vocabulário das medidas (ADR 0015, item 4): (chave, z > 0, z < 0). Pace é s/km: z > 0 é mais lento.
MEDIDAS = (
    ("fc_media", "FC média acima do habitual", "FC média abaixo do habitual"),
    ("fc_melhor_tiro", "FC do melhor tiro acima do habitual", "FC do melhor tiro abaixo do habitual"),
    ("pace_medio", "pace médio mais lento", "pace médio mais rápido"),
    ("melhor_pace", "melhor pace mais lento", "melhor pace mais rápido"),
    ("carga_hora", "carga por hora acima do habitual", "carga por hora abaixo do habitual"),
)
MODALIDADE_SEM_AVISO = "outra"  # sem modalidade definida: não gera `checkin_vencendo` (o check-in do atleta continua aberto)
ORIGENS_SUGERIDAS = ("sugestao", "semana_padrao")


@dataclass(frozen=True)
class TreinoAtencao:
    """O que a função precisa de um treino; tudo já calculado por quem chama."""

    id: Hashable
    dia: date  # data local (ADR 0003)
    modalidade: str
    subtipo: str | None
    tipo_treino: str | None
    tipo_origem: str | None
    tipo_confirmado: bool
    tipo_divergencia: str | None  # sem_esforco | tem_tiros (só com origem semana_padrao)
    metricas_fora: tuple[tuple[str, float], ...] = ()  # (chave, z assinado) das métricas com estado `fora` na linha_base@3
    dor: bool | None = None  # None = sem check-in


@dataclass(frozen=True)
class Motivo:
    codigo: str
    texto: str


@dataclass(frozen=True)
class TreinoComMotivos:
    id: Hashable
    dia: date
    motivos: tuple[Motivo, ...]


@dataclass(frozen=True)
class AtletaComAtencao:
    atleta: Hashable
    treinos: tuple[TreinoComMotivos, ...]  # do mais recente ao mais antigo


@dataclass(frozen=True)
class Atencao:
    versao: str
    com_atencao: tuple[AtletaComAtencao, ...]
    sem_atencao: tuple[Hashable, ...]
    sem_atencao_texto: str


def _dias_desde(t: TreinoAtencao, hoje: date) -> int:
    return (hoje - t.dia).days


def _juntar(partes: Sequence[str]) -> str:
    return partes[0] if len(partes) == 1 else ", ".join(partes[:-1]) + " e " + partes[-1]


def motivos_do_treino(t: TreinoAtencao, hoje: date) -> tuple[Motivo, ...]:
    """Os motivos de UM treino: `dor`, `fora_do_normal` e `divergencia`, nessa ordem. Fora da janela: nenhum.

    O `checkin_vencendo` não é por treino desde a `atencao@2`: é uma linha por aluno (`checkin_vencendo_do_atleta`)."""
    dias = _dias_desde(t, hoje)
    if not 0 <= dias <= JANELA_DIAS:
        return ()
    nome = DIAS_SEMANA[t.dia.weekday()]
    saida: list[Motivo] = []
    if t.dor:
        saida.append(Motivo(DOR, f"Treino de {nome} com dor marcada no check-in."))
    fora = {c: z for c, z in t.metricas_fora if abs(z) >= PADRAO.limite_fora}
    partes = [(positivo if fora[c] > 0 else negativo) for c, positivo, negativo in MEDIDAS if c in fora]
    if partes:
        saida.append(Motivo(FORA_DO_NORMAL, f"Treino de {nome} fora do normal: {_juntar(partes)}."))
    if t.tipo_origem == "semana_padrao" and t.tipo_divergencia and not t.tipo_confirmado:
        detalhe = "sem esforço detectado" if t.tipo_divergencia == "sem_esforco" else "com tiros detectados"
        saida.append(Motivo(DIVERGENCIA, f"Treino de {nome} diferente da semana-padrão: previsto {t.tipo_treino}, {detalhe}."))
    return tuple(saida)


def _pede_aviso_de_checkin(t: TreinoAtencao, hoje: date) -> bool:
    """Sem check-in, elegível, não é `outra` (sem modalidade definida) e de 5 a 7 dias depois do treino."""
    return (t.dor is None and elegivel(t.subtipo) and t.modalidade != MODALIDADE_SEM_AVISO
            and AVISO_CHECKIN_DIAS <= _dias_desde(t, hoje) <= PRAZO_CHECKIN_DIAS)


def checkin_vencendo_do_atleta(treinos: Sequence[TreinoAtencao], hoje: date) -> tuple[Hashable, Motivo] | None:
    """O motivo `checkin_vencendo` de UM aluno, numa linha só, preso ao treino mais antigo sem check-in (o de prazo mais curto).

    Um treino: "Treino de sexta sem check-in; o prazo termina em 2 dias." Vários: "3 treinos sem check-in; o prazo do mais antigo
    termina hoje." Empate de dia: o menor `id`. Sem treino a avisar: `None`."""
    pend = sorted((t for t in treinos if _pede_aviso_de_checkin(t, hoje)), key=lambda t: (t.dia, t.id))
    if not pend:
        return None
    antigo = pend[0]
    resta = PRAZO_CHECKIN_DIAS - _dias_desde(antigo, hoje)
    quando = "hoje" if resta == 0 else f"em {resta} dia{'s' if resta > 1 else ''}"
    if len(pend) == 1:
        return antigo.id, Motivo(CHECKIN_VENCENDO, f"Treino de {DIAS_SEMANA[antigo.dia.weekday()]} sem check-in; o prazo termina {quando}.")
    return antigo.id, Motivo(CHECKIN_VENCENDO, f"{len(pend)} treinos sem check-in; o prazo do mais antigo termina {quando}.")


def atencao(treinos_por_atleta: Mapping[Hashable, Sequence[TreinoAtencao]], hoje: date) -> Atencao:
    """A lista de atenção de um professor: atletas já filtrados por vínculo e consentimento (ADR 0015, item 3).

    Ordem: o motivo de maior prioridade presente; empate: o atleta com o treino com motivo mais recente; empate: a chave do
    atleta crescente. Quem não tem motivo vem depois, na ordem da chave. A função não filtra consentimento: quem chama só passa
    os atletas do professor."""
    com: list[tuple[int, int, Hashable, AtletaComAtencao]] = []
    sem: list[Hashable] = []
    for atleta, treinos in treinos_por_atleta.items():
        itens = []
        aviso = checkin_vencendo_do_atleta(treinos, hoje)  # uma linha por aluno, no treino mais antigo a avisar
        for t in sorted(treinos, key=lambda x: x.dia, reverse=True):
            motivos = motivos_do_treino(t, hoje)
            if aviso is not None and aviso[0] == t.id:
                motivos = (*motivos, aviso[1])
            if motivos:
                itens.append(TreinoComMotivos(t.id, t.dia, motivos))
        if not itens:
            sem.append(atleta)
            continue
        topo = min(PRIORIDADE.index(m.codigo) for i in itens for m in i.motivos)
        recente = max(i.dia for i in itens)
        com.append((topo, -recente.toordinal(), atleta, AtletaComAtencao(atleta, tuple(itens))))
    com.sort(key=lambda x: (x[0], x[1], x[2]))
    return Atencao(VERSAO, tuple(x[3] for x in com), tuple(sorted(sem)), SEM_ATENCAO_TEXTO)


def treinos_novos(treinos: Sequence[TreinoAtencao], hoje: date) -> tuple[Hashable, ...]:
    """Treinos com tipo sugerido a confirmar: tipo, origem `sugestao`/`semana_padrao`, não confirmado, elegível, em hoje - 14 a hoje.

    Não é motivo de atenção (ADR 0015, item 4). Mantém a ordem recebida."""
    return tuple(
        t.id for t in treinos
        if t.tipo_treino and t.tipo_origem in ORIGENS_SUGERIDAS and not t.tipo_confirmado and elegivel(t.subtipo)
        and 0 <= _dias_desde(t, hoje) <= JANELA_NOVOS_DIAS
    )
