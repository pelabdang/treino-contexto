"""`GET /atletas/{atleta_id}/inicio/cartoes`: os cartões "Seus números" do início v4 (issue #575). So o atleta dono (sessão)."""

from __future__ import annotations

from datetime import date
from typing import Literal

from app.db.session import get_session
from app.rotas.evolucao import Erro, _atleta_ou_404
from app.servicos import inicio_cartoes as ic
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

router = APIRouter(prefix="/atletas/{atleta_id}/inicio", tags=["início"])


class BarraOut(BaseModel):
    data_texto: str  # a segunda-feira da semana: "03/02"
    valor_texto: str  # "10"; a unidade vai no `apoio` do cartão
    destaque: bool  # a semana mais recente
    altura_pct: int  # 0 a 100: a altura da barra relativa à maior das 4 (meio para cima); o app só desenha


class DestinoOut(BaseModel):
    tela: Literal["evolucao", "semana_padrao", "treino"]
    serie_id: str | None = Field(None, exclude_if=lambda v: v is None)  # a série da Evolução a abrir (ids do catálogo)
    atividade_id: int | None = Field(None, exclude_if=lambda v: v is None)  # o treino a abrir (melhor marca com treino conhecido)


class DiaOut(BaseModel):
    rotulo: str  # "seg"
    estado: Literal["feito", "hoje", "vazio"]
    modalidades: list[str]  # "corrida", "natacao", "ciclismo", "outra" (sem repetir)
    rotulo_acessivel: str  # "segunda, corrida e natação feitas"


class CartaoOut(BaseModel):
    id: Literal["esta_semana", "hoje_na_semana", "volume_4_semanas", "em_movimento", "melhor_marca"]
    formato: Literal["pequeno", "largo"]
    rotulo: str  # "Esta semana", "Hoje, sexta"
    valor: str  # o número ou a frase curta grande
    apoio: str | None  # uma ou duas linhas de apoio
    texto: str | None  # a frase inteira (volume e em movimento)
    barras: list[BarraOut]  # só no volume das 4 semanas
    destino: DestinoOut
    rotulo_acessivel: str  # o que o leitor de tela lê, juntando tudo
    dias: list[DiaOut] = []  # só no `esta_semana`: os 7 dias da semana, seg a dom
    apoio_curto: str | None = None  # só no `esta_semana`: "3 treinos · 2 h 37 min"
    comparacao_texto: str | None = None  # só no `esta_semana`: "semana passada: 4" ou "sem semana anterior"


class CartoesOut(BaseModel):
    atleta_id: int
    data: date  # hoje do atleta; os cartões são calculados por dia
    cartoes: list[CartaoOut]  # só os que têm dado, na ordem fixa; vazio = a seção some


@router.get("/cartoes", response_model=CartoesOut, operation_id="cartoesDoInicio", responses={404: {"model": Erro, "description": "Atleta não encontrado"}})
def cartoes_do_inicio(atleta_id: int, session: Session = Depends(get_session)) -> CartoesOut:
    """Os cartões "Seus números" (#575): Esta semana, Hoje na sua semana, Volume das 4 semanas, Em movimento e Melhor marca. Sem dado, o cartão não vem."""
    _atleta_ou_404(session, atleta_id)
    r = ic.cartoes(session, atleta_id)
    return CartoesOut(
        atleta_id=atleta_id, data=r.hoje,
        cartoes=[CartaoOut(id=c.id, formato=c.formato, rotulo=c.rotulo, valor=c.valor, apoio=c.apoio, texto=c.texto,
                           barras=[BarraOut(**vars(b)) for b in c.barras],
                           destino=DestinoOut(tela=c.destino.tela, serie_id=c.destino.serie_id, atividade_id=c.destino.atividade_id),
                           rotulo_acessivel=c.rotulo_acessivel, dias=[DiaOut(**vars(d)) for d in c.dias], apoio_curto=c.apoio_curto,
                           comparacao_texto=c.comparacao_texto) for c in r.cartoes],
    )
