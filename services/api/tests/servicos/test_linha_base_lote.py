"""`linha_base_resultados` (a lista de treinos, 1 consulta de historico) == `linha_base_resultado` (a tela de treino), por metrica. Dados sinteticos."""

from datetime import datetime, timedelta, timezone

from app.db.models import Atividade, Atleta
from app.servicos.linha_base_leitura import linha_base_resultado, linha_base_resultados
from sqlalchemy import event

AGORA = datetime(2025, 6, 30, 12, 0, tzinfo=timezone.utc)


def _ativ(session, atleta, n, dias_atras, tipo="leve", modalidade="corrida", dist=5000.0, dur=1800.0, fc=140.0, **kw):
    a = Atividade(atleta_id=atleta.id, fonte="t", fonte_id=str(n), modalidade=modalidade, inicio=AGORA - timedelta(days=dias_atras),
                  duracao_s=dur, distancia_m=dist, fuso_min=-180, tipo_treino=tipo, fc_media=fc, **kw)
    session.add(a)
    session.flush()
    return a


def _cenario(session):
    x, y = Atleta(nome="X Ficticio"), Atleta(nome="Y Ficticio")
    session.add_all([x, y])
    session.flush()
    for i in range(8):  # historico do X: leves e moderados; o ultimo leve foge do normal
        _ativ(session, x, i, 40 - i * 4, dur=1800.0 + i * 5, fc=140.0 + i % 2)
    _ativ(session, x, 20, 5, tipo="moderado", dist=8000.0, dur=2400.0)
    _ativ(session, x, 24, 4, dur=1820.0, fc=141.0)  # leve no normal
    _ativ(session, x, 21, 3, dur=2600.0, fc=170.0)  # leve fora do normal
    _ativ(session, x, 22, 2, tipo=None)  # sem tipo
    _ativ(session, x, 23, 1, modalidade="natacao", tipo="leve", dist=1500.0)
    for i in range(6):  # outro atleta: nao pode entrar no historico do X
        _ativ(session, y, 100 + i, 30 - i, dur=900.0, fc=120.0)
    session.commit()
    return x


def test_lote_igual_ao_individual_em_todas_as_atividades(session):
    x = _cenario(session)
    atividades = session.query(Atividade).filter_by(atleta_id=x.id).order_by(Atividade.inicio.desc()).all()
    lote = linha_base_resultados(session, atividades)
    assert set(lote) == {a.id for a in atividades}
    for a in atividades:
        assert lote[a.id] == linha_base_resultado(session, a), a.id
    estados = {m.estado for r in lote.values() for m in r.metricas}
    assert {"fora", "dentro"} <= estados  # o cenario exercita fora e dentro (nao e igualdade vazia)


def test_lote_faz_uma_consulta_de_historico_por_pagina(session):
    x = _cenario(session)
    atividades = session.query(Atividade).filter_by(atleta_id=x.id).all()
    n = []
    engine = session.get_bind()
    conta = lambda *a, **k: n.append(1)  # noqa: E731
    event.listen(engine, "before_cursor_execute", conta)
    try:
        linha_base_resultados(session, atividades)
    finally:
        event.remove(engine, "before_cursor_execute", conta)
    por_atividade = len(n)
    n.clear()
    event.listen(engine, "before_cursor_execute", conta)
    try:
        for a in atividades:
            linha_base_resultado(session, a)
    finally:
        event.remove(engine, "before_cursor_execute", conta)
    assert por_atividade <= 6 < len(n)  # 1 consulta + selectinloads, contra 1 por atividade


def test_lote_vazio(session):
    assert linha_base_resultados(session, []) == {}
