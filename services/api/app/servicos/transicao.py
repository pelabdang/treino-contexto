"""Rotulo "treino de transicao" no banco (issue #157; ADR 0009, itens 1 e 3).

Liga a funcao pura `app.metricas.transicao.sugerir_transicao` a tabela `rotulo_transicao`. Sem rede.

Por atleta, a cada rodada: calcula o conjunto sugerido sobre todas as atividades dele; insere linha `sugerido` para as
sugeridas sem linha; atualiza `versao_regra` e `definido_em` das `sugerido` cuja versao mudou; apaga as `sugerido` que a
regra nao sugere mais; ignora toda atividade com linha `atleta` (a correcao do atleta sempre vence). Idempotente: com a
mesma versao e as mesmas atividades, a segunda rodada nao altera nenhuma linha (nem `definido_em`).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Atividade, RotuloTransicao
from app.metricas import transicao as regra

ORIGEM_SUGERIDO = "sugerido"
ORIGEM_ATLETA = "atleta"


@dataclass
class RelatorioTransicao:
    versao: str = ""
    atividades: int = 0  # atividades do atleta consideradas
    elegiveis: int = 0  # de modalidade corrida, natacao ou ciclismo
    sugeridas: int = 0  # o que a regra sugere (inclui as que o atleta ja corrigiu)
    inseridas: int = 0
    atualizadas: int = 0  # versao da regra mudou
    removidas: int = 0  # a regra nao sugere mais
    mantidas: int = 0  # sugerido, sem mudanca
    do_atleta: int = 0  # atividades com correcao do atleta (nunca tocadas)
    sugeridas_corrigidas: int = 0  # sugeridas pela regra em que o atleta ja decidiu


def aplicar_sugestao(session: Session, atleta_id: int, agora: datetime | None = None) -> RelatorioTransicao:
    """Grava as sugestoes `transicao@N` do atleta. Idempotente; um unico `commit` no fim."""
    agora = agora or datetime.now(timezone.utc)
    rel = RelatorioTransicao(versao=regra.VERSAO)
    leves = [
        regra.AtividadeLeve(a.id, a.modalidade, a.inicio, a.duracao_s)
        for a in session.scalars(select(Atividade).where(Atividade.atleta_id == atleta_id))
    ]
    rel.atividades = len(leves)
    rel.elegiveis = sum(1 for a in leves if a.modalidade in regra.MODALIDADES_DE_TRANSICAO)
    sugeridas = regra.sugerir_transicao(leves)
    rel.sugeridas = len(sugeridas)

    linhas = {
        r.atividade_id: r
        for r in session.scalars(select(RotuloTransicao).join(Atividade).where(Atividade.atleta_id == atleta_id))
    }
    for atividade_id, linha in linhas.items():
        if linha.origem == ORIGEM_ATLETA:
            rel.do_atleta += 1
            if atividade_id in sugeridas:
                rel.sugeridas_corrigidas += 1
            continue
        if atividade_id not in sugeridas:
            session.delete(linha)
            rel.removidas += 1
        elif linha.versao_regra != regra.VERSAO:
            linha.versao_regra = regra.VERSAO
            linha.definido_em = agora
            rel.atualizadas += 1
        else:
            rel.mantidas += 1
    for atividade_id in sorted(sugeridas - linhas.keys()):
        session.add(
            RotuloTransicao(
                atividade_id=atividade_id,
                transicao=True,
                origem=ORIGEM_SUGERIDO,
                versao_regra=regra.VERSAO,
                definido_em=agora,
            )
        )
        rel.inseridas += 1
    session.commit()
    return rel
