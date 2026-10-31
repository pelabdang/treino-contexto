from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.db.models import Atividade, Atleta, Segmento


def _atividade(atleta: Atleta, fonte_id: str = "123") -> Atividade:
    return Atividade(
        atleta=atleta,
        fonte="garmin_export",
        fonte_id=fonte_id,
        modalidade="corrida",
        inicio=datetime(2026, 10, 1, 6, 0, tzinfo=UTC),
        duracao_s=3600,
        distancia_m=10000,
        fc_media=150,
        tipo_treino="intervalado",
    )


def test_atividade_com_segmentos(session):
    atleta = Atleta(nome="Atleta Teste")
    ativ = _atividade(atleta)
    ativ.segmentos = [
        Segmento(ordem=2, tipo="tiro", duracao_s=240, distancia_m=1000, pace_s_km=240, fc_media=170),
        Segmento(ordem=1, tipo="volta", duracao_s=600, distancia_m=2000, pace_s_km=300, fc_media=140),
    ]
    session.add(ativ)
    session.commit()

    lida = session.scalars(select(Atividade)).one()
    assert [s.ordem for s in lida.segmentos] == [1, 2]
    assert lida.tipo_confirmado is False
    assert lida.atleta.nome == "Atleta Teste"


def test_atividade_duplicada_da_mesma_fonte_e_rejeitada(session):
    atleta = Atleta(nome="A")
    session.add_all([_atividade(atleta, "1"), _atividade(atleta, "1")])
    with pytest.raises(IntegrityError):
        session.commit()


def test_modalidade_invalida_e_rejeitada(session):
    ativ = _atividade(Atleta(nome="A"))
    ativ.modalidade = "remo"
    session.add(ativ)
    with pytest.raises(IntegrityError):
        session.commit()


def test_tipo_de_segmento_invalido_e_rejeitado(session):
    ativ = _atividade(Atleta(nome="A"))
    ativ.segmentos = [Segmento(ordem=1, tipo="sprint", duracao_s=10)]
    session.add(ativ)
    with pytest.raises(IntegrityError):
        session.commit()


def test_segmento_intensidade_e_versao_opcionais(session):
    atleta = Atleta(nome="Atleta Teste")
    ativ = _atividade(atleta)
    ativ.segmentos = [
        Segmento(ordem=1, tipo="tiro", duracao_s=240, intensidade="active", versao_deteccao="tiros_1km@1"),
        Segmento(ordem=2, tipo="volta", duracao_s=600),
    ]
    session.add(ativ)
    session.commit()
    a, b = session.scalars(select(Segmento).order_by(Segmento.ordem)).all()
    assert (a.intensidade, a.versao_deteccao) == ("active", "tiros_1km@1")
    assert (b.intensidade, b.versao_deteccao) == (None, None)


def test_segmento_intensidade_invalida_e_rejeitada(session):
    ativ = _atividade(Atleta(nome="Atleta Teste"))
    ativ.segmentos = [Segmento(ordem=1, tipo="tiro", duracao_s=240, intensidade="Active")]
    session.add(ativ)
    with pytest.raises(IntegrityError):
        session.commit()
