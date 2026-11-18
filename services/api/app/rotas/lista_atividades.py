"""`GET /atletas/{atleta_id}/atividades`: a lista de treinos do atleta (aba "Treinos" e tela inicial). So o atleta dono (`atleta_da_sessao`).

Item enxuto, sem dado de saude em texto (nada de check-in nem de feedback, so o ESTADO de cada um). Paginacao por cursor (`antes_de` /
`proximo`); mais recente primeiro. Ver `app/servicos/lista_atividades.py`.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.models import MODALIDADES, Atividade
from app.db.session import get_session
from app.rotas.atividades import _duracao_hms, _pace_medio
from app.rotas.evolucao import Erro
from app.servicos import lista_atividades as svc
from app.servicos.distancia_texto import distancia_da_atividade
from app.servicos.fuso import inicio_local

router = APIRouter(prefix="/atletas/{atleta_id}/atividades", tags=["atividades"])

Modalidade = Literal[*MODALIDADES]


class ItemOut(BaseModel):
    atividade_id: int
    inicio: datetime  # UTC
    data_local: str  # AAAA-MM-DD, pelo fuso da atividade
    hora_local: str  # HH:MM, pelo fuso da atividade
    modalidade: str
    subtipo: str | None
    tipo_treino: Literal["leve", "moderado", "longo", "intervalado", "fartlek"] | None
    duracao_s: float
    duracao: str  # h:mm:ss
    distancia_m: float | None
    distancia: str | None  # "10,00 km"; natacao em metros
    destaque: str | None  # frase curta pronta: "Pace médio 5:21 /km" (corrida) ou "Velocidade média 24,5 km/h" (ciclismo)
    checkin_estado: Literal["feito", "pendente", "vencido", "nao_se_aplica"]
    feedback_estado: Literal["pronto", "sem_checkin", "pendente", "desatualizado", "indisponivel"] | None  # null em multiesporte_pai e troca


class ListaOut(BaseModel):
    atleta_id: int
    limite: int
    itens: list[ItemOut]
    proximo: str | None  # passe em `antes_de` para a proxima pagina; null = acabou


def _destaque(a: Atividade) -> str | None:
    pace = _pace_medio(a)
    if pace is not None:
        return f"Pace médio {pace} /km"
    if a.modalidade == "ciclismo" and a.distancia_m and a.distancia_m > 0 and a.duracao_s > 0:
        return f"Velocidade média {a.distancia_m / a.duracao_s * 3.6:.1f}".replace(".", ",") + " km/h"
    return None


def _item(a: Atividade) -> ItemOut:
    local = inicio_local(a.inicio, a.fuso_min)
    return ItemOut(
        atividade_id=a.id, inicio=a.inicio, data_local=local.date().isoformat(), hora_local=local.strftime("%H:%M"),
        modalidade=a.modalidade, subtipo=a.subtipo, tipo_treino=a.tipo_treino, duracao_s=a.duracao_s, duracao=_duracao_hms(a.duracao_s),
        distancia_m=a.distancia_m, distancia=distancia_da_atividade(a.modalidade, a.distancia_m), destaque=_destaque(a),
        checkin_estado=svc.checkin_estado(a), feedback_estado=svc.feedback_estado(a),
    )


@router.get(
    "",
    response_model=ListaOut,
    operation_id="listarAtividades",
    responses={
        404: {"model": Erro, "description": "Atleta de outro (o mesmo 404 de atleta inexistente)"},
        422: {"description": "`antes_de` mal formado, `limite` fora de 1 a 100 ou `modalidade` desconhecida"},
    },
)
def listar_atividades(
    atleta_id: int,
    limite: int = Query(svc.LIMITE_PADRAO, ge=1, le=svc.LIMITE_MAX),
    antes_de: str | None = Query(None, description="cursor: o `proximo` da pagina anterior"),
    modalidade: Modalidade | None = None,
    checkin_pendente: bool = Query(False, description="so treinos que pedem check-in, ainda sem ele e dentro do prazo"),
    session: Session = Depends(get_session),
) -> ListaOut:
    """Os treinos do atleta, do mais recente para o mais antigo, `limite` por pagina."""
    try:
        cursor = None if antes_de is None else svc.ler_cursor(antes_de)
    except svc.CursorInvalido:
        raise HTTPException(status_code=422, detail=[{"loc": ["query", "antes_de"], "msg": "cursor invalido", "type": "cursor_invalido"}]) from None
    p = svc.pagina(session, atleta_id, limite, cursor, modalidade, checkin_pendente)
    return ListaOut(atleta_id=atleta_id, limite=limite, itens=[_item(a) for a in p.atividades], proximo=None if p.proximo is None else p.proximo.texto())
