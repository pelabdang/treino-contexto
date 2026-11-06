"""Blocos e esforços de uma atividade para a API (issue #167; ADR 0008, item 9 e decisões da #166).

Só lê o que `app.servicos.esforcos.detectar_esforcos` gravou em `bloco_atividade`; não detecta nada. A única conta
na leitura é a origem da referência (`ref_origem`), que o banco não guarda: recalcula-se com as mesmas funções de
referência da detecção (`pace_habitual` e `velocidade_habitual`). Há ritmo/velocidade habitual (histórico anterior
da modalidade) -> "habitual"; não há -> "atividade" (reserva: mediana dos blocos da própria atividade).
Limite conhecido: se atividades antigas entraram depois da detecção, a origem recalculada pode diferir da usada.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Atividade, BlocoAtividade
from app.metricas import esforcos as ef
from app.metricas.tiros_1km import CorridaHistorico, pace_habitual
from app.servicos.esforcos import (
    MODALIDADES_DETECTADAS,
    SUBTIPOS_INDOOR_CICLISMO,
    PedaladaHistorico,
    velocidade_habitual,
)
from app.servicos.fuso import data_local


@dataclass(frozen=True)
class EsforcosDaAtividade:
    versao: str
    ref_origem: str | None  # None sem blocos
    treino_chave: bool
    blocos: list[BlocoAtividade]  # em ordem


def origem_da_referencia(session: Session, a: Atividade) -> str:
    """"habitual" se a detecção teve histórico anterior para a referência, senão "atividade"."""
    # A referência usa `data < dia local`; a folga de 1 dia no filtro cobre diferença de fuso.
    historico = session.execute(
        select(Atividade.inicio, Atividade.fuso_min, Atividade.distancia_m, Atividade.duracao_s, Atividade.subtipo)
        .where(
            Atividade.atleta_id == a.atleta_id,
            Atividade.modalidade == a.modalidade,
            Atividade.inicio < a.inicio + timedelta(days=1),
        )
    ).all()
    dia = data_local(a.inicio, a.fuso_min)
    if a.modalidade == ef.MODALIDADE_CICLISMO:
        pedaladas = [
            PedaladaHistorico(data_local(i, f), d or 0.0, t, s in SUBTIPOS_INDOOR_CICLISMO)
            for i, f, d, t, s in historico
        ]
        ref = velocidade_habitual(pedaladas, dia)
    else:
        corridas = [CorridaHistorico(data_local(i, f), d or 0.0, t, s == "esteira") for i, f, d, t, s in historico]
        ref = pace_habitual(corridas, dia)
    return ef.REF_HABITUAL if ref is not None else ef.REF_ATIVIDADE


def esforcos_da_atividade(session: Session, a: Atividade) -> EsforcosDaAtividade | None:
    """None para modalidade sem detecção (natação...). Atividade sem blocos: lista vazia com a versão atual."""
    if a.modalidade not in MODALIDADES_DETECTADAS:
        return None
    blocos = list(a.blocos)
    if not blocos:
        return EsforcosDaAtividade(ef.VERSAO, None, False, [])
    return EsforcosDaAtividade(
        versao=blocos[0].versao_deteccao,
        ref_origem=origem_da_referencia(session, a),
        treino_chave=any(b.treino_chave for b in blocos),
        blocos=blocos,
    )
