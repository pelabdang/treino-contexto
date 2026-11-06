"""Blocos e esforços no banco (issue #166; ADR 0008, item 9).

Liga as funções puras de `app.metricas.esforcos` (blocos, faixas, treino-chave) à tabela `bloco_atividade`.
Regras e limites em docs/metricas/esforcos.md. Sem rede.

Idempotência: para cada atividade calcula os blocos e os compara com os gravados (mesmos valores e mesma
`versao_deteccao`); só se forem diferentes apaga e recria os blocos da atividade, numa transação. Rodar duas vezes
não muda nada (nem os `id`); mudar `VERSAO` ou qualquer constante da regra redetecta tudo.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import date, timedelta
from statistics import median

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.models import Atividade, BlocoAtividade
from app.metricas import esforcos as ef
from app.metricas.tiros_1km import CorridaHistorico, pace_habitual
from app.servicos.fuso import data_local

MODALIDADES_DETECTADAS = (ef.MODALIDADE_CORRIDA, ef.MODALIDADE_CICLISMO)
SUBTIPOS_INDOOR_CICLISMO = ("esteira", "virtual")  # trainer: velocidade não diz nada sobre ritmo na rua

# Velocidade habitual do ciclismo (ADR 0008, item 5): mesma ideia do ritmo habitual da corrida. Regra própria do
# projeto, sem artigo; janela e mínimo ainda a confirmar com o Caio (ADR, "A confirmar" 6).
HABITUAL_CICLISMO_DURACAO_MIN_S = 1800.0  # pedaladas de mais de 30 min
HABITUAL_CICLISMO_JANELA_DIAS = 84  # 12 semanas
HABITUAL_CICLISMO_MIN_PEDALADAS_JANELA = 10  # com menos, todo o histórico anterior


@dataclass(frozen=True)
class PedaladaHistorico:
    data: date  # data local
    distancia_m: float
    duracao_s: float
    indoor: bool


def velocidade_habitual(historico: list[PedaladaHistorico], data_sessao: date) -> float | None:
    """Velocidade habitual (km/h) em bicicleta antes de `data_sessao`, ou None sem histórico.

    Mediana da velocidade (distância / duração x 3,6) das pedaladas de mais de 30 min, fora do trainer e com data
    anterior à da sessão, nas 12 semanas antes dela; com menos de 10 nessa janela, todo o histórico anterior.
    """

    def velocidades(desde: date | None) -> list[float]:
        return [
            c.distancia_m / c.duracao_s * 3.6
            for c in historico
            if c.data < data_sessao
            and (desde is None or c.data >= desde)
            and not c.indoor
            and c.duracao_s > HABITUAL_CICLISMO_DURACAO_MIN_S
            and c.distancia_m > 0
        ]

    todas = velocidades(None)
    if not todas:
        return None
    na_janela = velocidades(data_sessao - timedelta(days=HABITUAL_CICLISMO_JANELA_DIAS))
    return median(na_janela if len(na_janela) >= HABITUAL_CICLISMO_MIN_PEDALADAS_JANELA else todas)


@dataclass
class RelatorioEsforcos:
    """O que a rodada fez. Contagens de esforços e treinos-chave são das atividades processadas (todas)."""

    versao: str = ""
    processadas: int = 0  # corridas e pedaladas do atleta (ou da lista pedida)
    alteradas: int = 0  # as que tiveram blocos gravados de novo
    inalteradas: int = 0
    sem_blocos: int = 0  # sem nenhum bloco (sem voltas, ou só pausas)
    esforcos: Counter = field(default_factory=Counter)  # por modalidade
    treinos_chave: Counter = field(default_factory=Counter)  # por modalidade
    por_faixa: Counter = field(default_factory=Counter)  # "corrida d400" -> n
    referencia_da_atividade: int = 0  # sem histórico: referência de reserva (ref_origem = atividade)


def _linhas(atividade_id: int, resultado: ef.ResultadoBlocos, modalidade: str, versao: str) -> list[BlocoAtividade]:
    if modalidade == ef.MODALIDADE_CICLISMO:
        faixas = {e.bloco_ordem: e.faixa for e in ef.esforcos_ciclismo(resultado)}
    else:
        faixas = {e.bloco_ordem: e.faixa for e in ef.esforcos_corrida(resultado)}
    chave = ef.treino_chave_continuo(resultado, modalidade)
    em_chave = range(0)
    if chave.treino_chave:
        em_chave = range(chave.sequencia_bloco_inicial, chave.sequencia_bloco_final + 1)
    return [
        BlocoAtividade(
            atividade_id=atividade_id,
            ordem=b.ordem,
            categoria=b.categoria,
            volta_inicial=b.volta_inicial,
            volta_final=b.volta_final,
            inicio_offset_s=b.inicio_offset_s,
            duracao_s=b.duracao_s,
            parada_apos_s=b.parada_apos_s,
            distancia_m=b.distancia_m,
            fc_media=b.fc_media,
            pace_s_km=b.pace_s_km,
            faixa=faixas.get(b.ordem),
            treino_chave=b.categoria == ef.ESFORCO and b.ordem in em_chave,
            versao_deteccao=versao,
        )
        for b in resultado.blocos
    ]


def _assinatura(b: BlocoAtividade) -> tuple:
    def r(x: float | None) -> float | None:
        return None if x is None else round(x, 6)

    return (
        b.ordem, b.categoria, b.volta_inicial, b.volta_final, r(b.inicio_offset_s), r(b.duracao_s),
        r(b.parada_apos_s), r(b.distancia_m), r(b.fc_media), r(b.pace_s_km), b.faixa, bool(b.treino_chave),
        b.versao_deteccao,
    )  # fmt: skip


def _voltas(a: Atividade) -> list[ef.VoltaTreino]:
    return [
        ef.VoltaTreino(s.ordem, s.inicio_offset_s or 0.0, s.duracao_s, s.distancia_m or 0.0, s.fc_media, s.intensidade)
        for s in a.segmentos
    ]


def detectar_esforcos(session: Session, atleta_id: int, atividade_ids: list[int] | None = None) -> RelatorioEsforcos:
    """Detecta blocos e esforços das corridas e pedaladas do atleta e grava em `bloco_atividade`. Idempotente.

    `atividade_ids` limita as atividades processadas (o histórico para a referência usa todas do atleta).
    Nada de rede. Faz um único `commit` no fim; se algo falhar antes, nada é gravado.
    """
    versao = ef.VERSAO
    todas = session.scalars(
        select(Atividade)
        .where(Atividade.atleta_id == atleta_id, Atividade.modalidade.in_(MODALIDADES_DETECTADAS))
        .options(selectinload(Atividade.segmentos), selectinload(Atividade.blocos))
        .order_by(Atividade.inicio, Atividade.id)
    ).all()
    corridas = [
        CorridaHistorico(data_local(a.inicio, a.fuso_min), a.distancia_m or 0.0, a.duracao_s, a.subtipo == "esteira")
        for a in todas
        if a.modalidade == ef.MODALIDADE_CORRIDA
    ]
    pedaladas = [
        PedaladaHistorico(
            data_local(a.inicio, a.fuso_min), a.distancia_m or 0.0, a.duracao_s, a.subtipo in SUBTIPOS_INDOOR_CICLISMO
        )
        for a in todas
        if a.modalidade == ef.MODALIDADE_CICLISMO
    ]

    rel = RelatorioEsforcos(versao=versao)
    for a in todas:
        if atividade_ids is not None and a.id not in atividade_ids:
            continue
        dia = data_local(a.inicio, a.fuso_min)
        ref = (
            velocidade_habitual(pedaladas, dia)
            if a.modalidade == ef.MODALIDADE_CICLISMO
            else pace_habitual(corridas, dia)
        )
        resultado = ef.montar_blocos(_voltas(a), a.modalidade, referencia=ref)
        novos = _linhas(a.id, resultado, a.modalidade, versao)

        rel.processadas += 1
        if not novos:
            rel.sem_blocos += 1
        if novos and resultado.ref_origem == ef.REF_ATIVIDADE:
            rel.referencia_da_atividade += 1
        for b in novos:
            if b.categoria == ef.ESFORCO:
                rel.esforcos[a.modalidade] += 1
                if b.faixa:
                    rel.por_faixa[f"{a.modalidade} {b.faixa}"] += 1
        if any(b.treino_chave for b in novos):
            rel.treinos_chave[a.modalidade] += 1

        if [_assinatura(b) for b in novos] == [_assinatura(b) for b in a.blocos]:
            rel.inalteradas += 1
            continue
        a.blocos.clear()
        session.flush()  # remove os antigos antes de inserir (unique atividade_id + ordem)
        a.blocos.extend(novos)
        rel.alteradas += 1
    session.commit()
    return rel
