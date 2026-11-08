"""Carga de treino por atividade no banco (issue #141; ADR 0010, itens 4, 5 e 7).

Liga a função pura `app.metricas.carga.calcular_carga` à tabela `carga_atividade`. Para cada atividade do atleta:
resolve o limiar vigente no dia local (`limiar_vigente`, ADR 0003 para o dia), calcula, e compara a `entrada`
(SHA-256 do que entrou na conta) e a `versao` com a linha gravada: só regrava se algum dos dois mudou. Rodar de novo
não muda nada (nem o `id`, nem o `calculado_em`); subir `VERSAO` recalcula tudo; um limiar novo recalcula só as
atividades cujo limiar usado mudou. `multiesporte_pai` e `troca` não têm linha (e perdem a que tinham). Sem rede.

Privacidade: o relatório e o log levam só contagens, nunca limiar, FC ou pace.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import date, datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.db.models import Atividade, CargaAtividade, LimiarAtleta
from app.ingestao.saude import limiar_vigente
from app.metricas import carga as cg
from app.servicos.fuso import data_local

GRANDEZA_DO_METODO = {"rtss": "velocidade_ms", "hrtss": "fc_bpm"}


@dataclass
class RelatorioCarga:
    versao: str = cg.VERSAO
    processadas: int = 0  # atividades com linha (elegíveis)
    gravadas: int = 0  # linhas novas ou regravadas nesta rodada
    inalteradas: int = 0  # já estavam atualizadas (mesma entrada e versão)
    ignoradas_multiesporte: int = 0  # multiesporte_pai e troca: sem linha
    removidas: int = 0  # linhas apagadas porque a atividade virou ignorada
    calculadas: int = 0  # estado final das elegíveis
    sem_carga: dict[str, int] = field(default_factory=lambda: {m: 0 for m in cg.MOTIVOS})

    @property
    def sem_carga_total(self) -> int:
        return sum(self.sem_carga.values())


def _num(x: float | None) -> str:
    return "-" if x is None else repr(float(x))


def entrada_de(a: Atividade, voltas: list[cg.Volta], limiares: cg.Limiares, desde: dict[str, date | None],
               fc_da_atividade: cg.Volta | None = None) -> str:
    """SHA-256 do que entra na conta: modalidade, subtipo, voltas (ou totais) e os limiares das grandezas do
    caminho da modalidade, com a vigência e se o atleta tem a grandeza (muda o motivo). Limiar de grandeza que a
    atividade não usa (ex.: velocidade na natação ou na esteira) não entra: não recalcula à toa. A duração e a FC média
    da atividade (``fc_da_atividade``) entram só quando a ``carga@2`` as usa (voltas sem nenhuma FC)."""
    if a.modalidade in cg.MODALIDADES_SEM_CARGA:
        grandezas: tuple[str, ...] = ()
    elif a.modalidade == "corrida" and a.subtipo != "esteira":
        grandezas = ("velocidade_ms", "fc_bpm")
    else:
        grandezas = ("fc_bpm",)
    valores = {"fc_bpm": (limiares.fc_bpm, limiares.atleta_tem_fc),
               "velocidade_ms": (limiares.velocidade_ms, limiares.atleta_tem_velocidade)}
    partes = [a.modalidade, a.subtipo or "-"]
    partes += [f"{_num(v.duracao_s)},{_num(v.distancia_m)},{_num(v.fc_media)}" for v in voltas]
    if fc_da_atividade is not None:
        partes.append(f"atividade={_num(fc_da_atividade.duracao_s)},{_num(fc_da_atividade.fc_media)}")
    for g in grandezas:
        valor, tem = valores[g]
        d = desde.get(g)
        partes.append(f"{g}={_num(valor)}|{int(tem)}|{d.isoformat() if d else '-'}")
    return hashlib.sha256("\n".join(partes).encode()).hexdigest()


def _limiares(session: Session, atleta_id: int, dia: date, tem: dict[str, bool]):
    fc = limiar_vigente(session, atleta_id, "fc_bpm", dia)
    vel = limiar_vigente(session, atleta_id, "velocidade_ms", dia)
    limiares = cg.Limiares(
        fc_bpm=fc.valor if fc else None, velocidade_ms=vel.valor if vel else None,
        atleta_tem_fc=tem["fc_bpm"], atleta_tem_velocidade=tem["velocidade_ms"],
    )
    return limiares, {"fc_bpm": fc.vigente_desde if fc else None, "velocidade_ms": vel.vigente_desde if vel else None}


def calcular_carga_do_atleta(session: Session, atleta_id: int, agora: datetime | None = None) -> RelatorioCarga:
    """Calcula e grava a carga de todas as atividades do atleta. Idempotente. Faz `commit`."""
    agora = agora or datetime.now(timezone.utc)
    rel = RelatorioCarga(versao=cg.VERSAO)
    tem = {g: session.scalar(select(func.count()).select_from(LimiarAtleta).where(
        LimiarAtleta.atleta_id == atleta_id, LimiarAtleta.grandeza == g)) > 0
        for g in ("fc_bpm", "velocidade_ms")}
    atividades = session.scalars(
        select(Atividade).where(Atividade.atleta_id == atleta_id).order_by(Atividade.inicio, Atividade.id)
        .options(selectinload(Atividade.segmentos), selectinload(Atividade.carga))
    ).all()
    for a in atividades:
        if cg.ignorada(a.subtipo):
            rel.ignoradas_multiesporte += 1
            if a.carga is not None:
                session.delete(a.carga)
                rel.removidas += 1
            continue
        voltas = [cg.Volta(s.duracao_s, s.distancia_m, s.fc_media) for s in a.segmentos]
        totais = cg.Volta(a.duracao_s, a.distancia_m, a.fc_media)
        limiares, desde = _limiares(session, atleta_id, data_local(a.inicio, a.fuso_min), tem)
        usa_atividade = cg.usa_fc_da_atividade(voltas, totais)
        entrada = entrada_de(a, voltas or [totais], limiares, desde, totais if usa_atividade else None)
        rel.processadas += 1
        linha = a.carga
        if linha is None or linha.entrada != entrada or linha.versao != cg.VERSAO:
            r = cg.calcular_carga(a.modalidade, a.subtipo, voltas, limiares, atividade=totais)
            valores = dict(
                estado=r.estado, carga=r.carga, metodo=r.metodo, carga_rtss=r.carga_rtss, carga_hrtss=r.carga_hrtss,
                motivo=r.motivo, cobertura_pct=r.cobertura_pct, granularidade=r.granularidade,
                limiar_fc_bpm=r.limiar_fc_bpm, limiar_velocidade_ms=r.limiar_velocidade_ms,
                limiar_vigente_desde=desde[GRANDEZA_DO_METODO[r.metodo]] if r.metodo else None,
                entrada=entrada, versao=cg.VERSAO, calculado_em=agora,
            )
            if linha is None:
                a.carga = linha = CargaAtividade(**valores)
            else:
                for k, v in valores.items():
                    setattr(linha, k, v)
            rel.gravadas += 1
        else:
            rel.inalteradas += 1
        if linha.estado == "calculada":
            rel.calculadas += 1
        else:
            rel.sem_carga[linha.motivo] += 1
    session.commit()
    return rel
