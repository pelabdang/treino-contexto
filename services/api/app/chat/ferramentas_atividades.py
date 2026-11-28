"""Ferramentas de atividades e check-ins do chat (#593, ADR 0017, itens 1, 2 e 6): `listar_atividades`, `ver_atividade`, `listar_checkins`.

So leem, com os servicos que a API ja usa (lista, linha de base, clima, carga, esforcos); nenhum calculo novo. O `atleta_id` vem da
`Consulta`. Datas sao as locais do atleta. Todo numero sai em texto pronto (`*_texto`) e so esse texto e citavel.
Atividade de outro atleta e atividade inexistente dao o MESMO resultado (`nao_encontrada`).
`observacao_texto` (decisao do Angelo, 28/11) so sai daqui, da tabela `checkin_treino`; o pacote do feedback nao muda.
Dado de saude: nada aqui vai para log.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.chat import periodo as per
from app.chat.registro import Consulta, erro, registrar
from app.db.models import CHECKIN_TEXTO_MAX, TIPOS_TREINO, Atividade, CheckinTreino
from app.explicacao import fatos_treino as ft
from app.metricas import carga_pse as cp
from app.metricas.tiros_1km import formatar_pace
from app.servicos import checkin as checkin_svc
from app.servicos import feedback_fatos as ff
from app.servicos.carga_pse_leitura import duracao_pt
from app.servicos.distancia_texto import distancia_da_atividade
from app.servicos.fuso import inicio_local
from app.servicos.lista_atividades import checkin_estado
from app.servicos.linha_base_leitura import linha_base_resultado, valores_e_motivos

VERSAO_LISTA = "lista_atividades@1"
VERSAO_CHECKINS = "checkin@1"
LIMITE_PADRAO, LIMITE_MAX = 10, 20
LIMITE_CHECKINS_PADRAO, LIMITE_CHECKINS_MAX = 20, 50
PERIODO_CHECKINS_PADRAO = "ultimos_28_dias"
MODALIDADES_CHAT = ("corrida", "natacao", "ciclismo")

_PERIODO = {"type": "string", "enum": list(per.PERIODOS), "description": "janela pronta, contada a partir de hoje (data local do atleta)"}
_DE = {"type": "string", "pattern": r"\d{4}-\d{2}-\d{2}", "description": "inicio AAAA-MM-DD; use com `ate`, sem `periodo`"}
_ATE = {"type": "string", "pattern": r"\d{4}-\d{2}-\d{2}", "description": "fim AAAA-MM-DD; use com `de`, sem `periodo`"}
_ATIVIDADE_ID = {"type": "integer", "minimum": 1, "description": "id que veio de `listar_atividades` ou `listar_checkins`"}


def _periodo(c: Consulta, a: dict[str, Any], padrao: str | None = None) -> per.Periodo | None:
    return per.resolver(c.hoje, a.get("periodo", padrao if "de" not in a and "ate" not in a else None), a.get("de"), a.get("ate"))


def _local(a: Atividade):
    return inicio_local(a.inicio, a.fuso_min)


def _data_texto(a: Atividade) -> str:
    return _local(a).strftime("%d/%m")


def _janela_utc(p: per.Periodo):
    """Corte grosso em UTC (um dia de folga de cada lado); a data local exata e conferida em Python."""
    ini = datetime(p.de.year, p.de.month, p.de.day, tzinfo=timezone.utc) - timedelta(days=1)
    fim = datetime(p.ate.year, p.ate.month, p.ate.day, tzinfo=timezone.utc) + timedelta(days=2)
    return ini, fim


def _pace_ou_velocidade(a: Atividade) -> dict[str, str]:
    if not a.distancia_m or a.distancia_m <= 0 or a.duracao_s <= 0:
        return {}
    if a.modalidade == "corrida":
        return {"pace_texto": formatar_pace(a.duracao_s / (a.distancia_m / 1000)) + "/km"}
    if a.modalidade == "ciclismo":
        return {"velocidade_texto": f"{a.distancia_m / a.duracao_s * 3.6:.1f}".replace(".", ",") + " km/h"}
    return {}


def _fc_texto(a: Atividade) -> dict[str, str]:
    return {} if a.fc_media is None else {"fc_media_texto": f"{int(a.fc_media + 0.5)} bpm"}


@registrar(
    "listar_atividades",
    "Lista os treinos do atleta (mais recentes ou maiores), com data, modalidade, tipo, distancia, duracao, pace ou velocidade e FC "
    "media em texto pronto. Use para achar um treino e o `atividade_id` dele, ou contar treinos num periodo.",
    {"modalidade": {"type": "string", "enum": list(MODALIDADES_CHAT)}, "periodo": _PERIODO, "de": _DE, "ate": _ATE,
     "tipo_treino": {"type": "string", "enum": list(TIPOS_TREINO)},
     "ordem": {"type": "string", "enum": ["recentes", "maiores"], "description": "`maiores` ordena pela distancia"},
     "limite": {"type": "integer", "minimum": 1, "maximum": LIMITE_MAX}},
    ("atleta", "professor"),
)
def listar_atividades(session: Session, c: Consulta, a: dict[str, Any]) -> dict[str, Any]:
    try:
        p = _periodo(c, a)
    except per.PeriodoInvalido as e:
        return erro("argumento_invalido", argumento=str(e))
    q = (select(Atividade).where(Atividade.atleta_id == c.atleta_id)
         .options(joinedload(Atividade.checkin).joinedload(CheckinTreino.feedback), joinedload(Atividade.rotulo_transicao)))
    if a.get("modalidade"):
        q = q.where(Atividade.modalidade == a["modalidade"])
    if a.get("tipo_treino"):
        q = q.where(Atividade.tipo_treino == a["tipo_treino"])
    if p is not None:
        ini, fim = _janela_utc(p)
        q = q.where(Atividade.inicio >= ini, Atividade.inicio < fim)
    q = q.order_by(Atividade.inicio.desc(), Atividade.id.desc())
    achadas = [x for x in session.scalars(q).unique() if p is None or p.contem(_local(x).date())]
    if a.get("ordem") == "maiores":
        achadas.sort(key=lambda x: (-(x.distancia_m or 0), -x.id))
    limite = a.get("limite", LIMITE_PADRAO)
    itens = []
    for x in achadas[:limite]:
        item = {"atividade_id": x.id, "data_texto": _data_texto(x), "modalidade": x.modalidade, "tipo_treino": x.tipo_treino,
                "distancia_texto": distancia_da_atividade(x.modalidade, x.distancia_m), "duracao_texto": duracao_pt(x.duracao_s / 60),
                **_pace_ou_velocidade(x), **_fc_texto(x), "checkin": checkin_estado(x, c.hoje)}
        itens.append({k: v for k, v in item.items() if v is not None})
    r: dict[str, Any] = {"versao": VERSAO_LISTA, "estado": "ok" if achadas else "sem_dados", "total": len(achadas), "atividades": itens}
    if p is not None:
        r["periodo_texto"] = p.texto
    if not achadas:
        r["motivo_texto"] = "nenhum treino encontrado com esses filtros"
    return r


def _observacao(ch: CheckinTreino) -> dict[str, str]:
    return {"observacao_texto": ch.texto[:CHECKIN_TEXTO_MAX]} if ch.texto else {}


def _pse_texto(pse: int) -> str:
    return str(pse)


def _atalhos(ch: CheckinTreino) -> list[str]:
    return ft._atalhos(ch)


@registrar(
    "ver_atividade",
    "Mostra um treino em detalhe: distancia e duracao, comparacao com o normal do atleta (linha de base), esforcos, clima, carga e "
    "o check-in (PSE, sensacao, atalhos e a observacao que o atleta escreveu). Precisa do `atividade_id`.",
    {"atividade_id": _ATIVIDADE_ID},
    ("atleta", "professor"),
    ("atividade_id",),
)
def ver_atividade(session: Session, c: Consulta, a: dict[str, Any]) -> dict[str, Any]:
    # O dono entra na consulta: atividade de outro atleta e inexistente dao exatamente o mesmo resultado.
    x = session.scalar(select(Atividade).where(Atividade.id == a["atividade_id"], Atividade.atleta_id == c.atleta_id)
                       .options(joinedload(Atividade.checkin), joinedload(Atividade.rotulo_transicao)))
    if x is None:
        return erro("nao_encontrada")
    ch = x.checkin
    transicao = bool(x.rotulo_transicao and x.rotulo_transicao.transicao)
    r: dict[str, Any] = {
        "versao": ft.VERSAO, "estado": "ok", "atividade_id": x.id, "data_texto": _data_texto(x),
        "treino": {**ft._treino(x, transicao), **_pace_ou_velocidade(x)},
        "linha_base": ft._linha_base(linha_base_resultado(session, x), valores_e_motivos(x)[1]),
        "esforcos": ft._esforcos(ff._esforcos(session, x)),
        "clima": ft._clima(ff._clima(session, x)),
        "carga": ft._carga(ff._carga(session, x)),
        "carga_pse": None,
        "checkin": None,
    }
    if ch is not None:
        carga_pse = cp.carga_pse(ch.pse, x.duracao_s, x.subtipo)
        r["carga_pse"] = None if carga_pse is None else ft._carga_pse(carga_pse)
        r["checkin"] = {**ft._checkin(ch), **_observacao(ch)}
    else:
        r["motivo_texto"] = "este treino ainda não tem check-in"
    return r


@registrar(
    "listar_checkins",
    "Lista os check-ins do atleta num periodo (padrao: ultimos 28 dias): PSE, sensacao, atalhos marcados e a observacao que ele escreveu.",
    {"periodo": _PERIODO, "de": _DE, "ate": _ATE, "limite": {"type": "integer", "minimum": 1, "maximum": LIMITE_CHECKINS_MAX}},
    ("atleta", "professor"),
)
def listar_checkins(session: Session, c: Consulta, a: dict[str, Any]) -> dict[str, Any]:
    try:
        p = _periodo(c, a, PERIODO_CHECKINS_PADRAO)
    except per.PeriodoInvalido as e:
        return erro("argumento_invalido", argumento=str(e))
    ini, fim = _janela_utc(p)
    q = (select(Atividade).join(CheckinTreino, CheckinTreino.atividade_id == Atividade.id)
         .where(Atividade.atleta_id == c.atleta_id, Atividade.inicio >= ini, Atividade.inicio < fim)
         .options(joinedload(Atividade.checkin)).order_by(Atividade.inicio.desc(), Atividade.id.desc()))
    achadas = [x for x in session.scalars(q).unique() if p.contem(_local(x).date())]
    limite = a.get("limite", LIMITE_CHECKINS_PADRAO)
    itens = []
    for x in reversed(achadas[:limite]):  # os mais recentes, mostrados do mais antigo ao mais novo
        ch = x.checkin
        itens.append({"data_texto": _data_texto(x), "atividade_id": x.id, "pse_texto": _pse_texto(ch.pse),
                      "sensacao_texto": checkin_svc.SENSACAO_TEXTO[ch.sensacao], "atalhos": _atalhos(ch), **_observacao(ch)})
    r: dict[str, Any] = {"versao": VERSAO_CHECKINS, "estado": "ok" if achadas else "sem_dados", "periodo_texto": p.texto,
                         "total": len(achadas), "checkins": itens}
    if not achadas:
        r["motivo_texto"] = "nenhum check-in neste período"
    return r
