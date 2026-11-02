"""Classificação e série de tiros no banco (issue #14), com as tabelas das fixtures (#8) e o oráculo (#30)."""

import importlib.util
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.db.models import Atividade, Atleta, Segmento
from app.metricas.tiros_1km import para_apresentacao
from app.servicos.evolucao_tiros import classificar_atividades, serie_tiros_1km
from app.servicos.fuso import data_local

GERADOR = Path(__file__).parents[4] / "tests" / "fixtures" / "garmin" / "gerar_fixtures.py"

# id da fonte -> (n_tiros, pace s/km, FC bpm), à mão (docstring de tests/metricas/test_oraculo_fixtures.py)
ESPERADO = {
    "1000000001": (6, 1505 / 6000 * 1000, 256309 / 1505),
    "1000000002": (5, 1185 / 5000 * 1000, 203546 / 1185),
}


@pytest.fixture(scope="module")
def gerador():
    spec = importlib.util.spec_from_file_location("gerar_fixtures", GERADOR)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def _modalidade(a):
    return {"running": "corrida", "track_running": "corrida", "treadmill_running": "corrida",
            "lap_swimming": "natacao"}[a.activity_type]


@pytest.fixture
def atleta(session, gerador):
    """Atleta com as 5 atividades das fixtures, gravadas como a importação (#13) grava (tipo = volta)."""
    at = Atleta(nome="Ficticio")
    session.add(at)
    session.flush()
    for a in gerador.ATIVIDADES:
        dist, dur, fc = a.totais()
        ativ = Atividade(atleta_id=at.id, fonte="garmin_export", fonte_id=str(a.id), modalidade=_modalidade(a),
                         inicio=a.inicio, fuso_min=None if a.fuso_h is None else a.fuso_h * 60,
                         duracao_s=dur, distancia_m=dist, fc_media=fc)
        t = 0.0
        for i, (intens, d, du, hr) in enumerate(a.voltas or []):
            ativ.segmentos.append(Segmento(ordem=i, tipo="volta", inicio_offset_s=t, duracao_s=du, distancia_m=d,
                                           fc_media=hr, pace_s_km=du / d * 1000, intensidade=intens))
            t += du
        session.add(ativ)
    session.commit()
    return at


def _ativ(session, fonte_id):
    return session.scalars(select(Atividade).where(Atividade.fonte_id == fonte_id)).one()


def test_serie_bate_com_o_oraculo(session, atleta):
    assert classificar_atividades(session, atleta.id) == 4  # corridas: A, B, C, E
    serie = serie_tiros_1km(session, atleta.id)
    assert len(serie) == 2  # leve, natação e esteira sem FIT ficam fora
    por_id = {_ativ(session, f).id: f for f in ESPERADO}
    for ponto in serie:
        n, pace, fc = ESPERADO[por_id[ponto.atividade_id]]
        assert ponto.n_tiros == n
        assert ponto.pace_s_km == pytest.approx(pace, abs=0.01)
        assert ponto.fc_media == pytest.approx(fc, abs=0.01)
        assert ponto.versao == "tiros_1km@2"
    assert [p.data for p in serie] == [date(2025, 3, 4), date(2025, 3, 11)]
    assert para_apresentacao(serie[0].pace_s_km) == 250.8 and para_apresentacao(serie[0].fc_media) == 170.3


def test_marca_segmentos_e_tipo_do_treino(session, atleta):
    classificar_atividades(session, atleta.id)
    a = _ativ(session, "1000000001")
    assert [s.tipo for s in a.segmentos] == (
        ["volta"] + ["tiro", "recuperacao"] * 5 + ["tiro", "volta"])
    assert {s.versao_deteccao for s in a.segmentos} == {"tiros_1km@2"}
    assert (a.tipo_treino, a.tipo_origem) == ("intervalado", "sugestao")
    leve = _ativ(session, "1000000003")
    assert {s.tipo for s in leve.segmentos} == {"volta"} and leve.tipo_treino is None
    nat = _ativ(session, "1000000004")
    assert {s.tipo for s in nat.segmentos} == {"volta"} and {s.versao_deteccao for s in nat.segmentos} == {None}


def test_classificar_duas_vezes_nao_muda(session, atleta):
    classificar_atividades(session, atleta.id)

    def foto():
        session.expire_all()
        return ([(s.id, s.tipo, s.versao_deteccao) for s in session.scalars(select(Segmento).order_by(Segmento.id))],
                [(a.id, a.tipo_treino, a.tipo_origem) for a in session.scalars(select(Atividade).order_by(Atividade.id))])

    antes = foto()
    classificar_atividades(session, atleta.id)
    assert foto() == antes


def test_tipo_do_professor_e_mantido(session, atleta):
    a = _ativ(session, "1000000001")
    a.tipo_treino, a.tipo_origem = "moderado", "professor"
    session.commit()
    classificar_atividades(session, atleta.id)
    a = _ativ(session, "1000000001")
    assert (a.tipo_treino, a.tipo_origem) == ("moderado", "professor")
    assert sum(s.tipo == "tiro" for s in a.segmentos) == 6  # os segmentos são classificados mesmo assim


def test_tipo_confirmado_e_mantido(session, atleta):
    a = _ativ(session, "1000000002")
    a.tipo_treino, a.tipo_origem, a.tipo_confirmado = "fartlek", "sugestao", True
    session.commit()
    classificar_atividades(session, atleta.id)
    assert _ativ(session, "1000000002").tipo_treino == "fartlek"


def test_filtro_inicio_fim(session, atleta):
    classificar_atividades(session, atleta.id)
    assert len(serie_tiros_1km(session, atleta.id, inicio=date(2025, 3, 5))) == 1
    assert [p.data for p in serie_tiros_1km(session, atleta.id, fim=date(2025, 3, 10))] == [date(2025, 3, 4)]
    assert len(serie_tiros_1km(session, atleta.id, inicio=date(2025, 3, 4), fim=date(2025, 3, 11))) == 2  # inclusivo
    assert serie_tiros_1km(session, atleta.id, inicio=date(2025, 3, 12)) == []


def test_treino_noturno_cai_na_data_local(session, atleta):
    """22:30 local (UTC-3) = 01:30 UTC do dia seguinte: a data da sessão é a local."""
    a = _ativ(session, "1000000001")
    a.inicio = datetime(2025, 3, 5, 1, 30, tzinfo=timezone.utc)
    a.fuso_min = -180
    session.commit()
    classificar_atividades(session, atleta.id)
    assert serie_tiros_1km(session, atleta.id)[0].data == date(2025, 3, 4)
    a.fuso_min = None  # sem fuso da exportação: America/Sao_Paulo (UTC-3 em março de 2025)
    session.commit()
    assert serie_tiros_1km(session, atleta.id)[0].data == date(2025, 3, 4)
    # o filtro usa a data local, não a UTC
    assert len(serie_tiros_1km(session, atleta.id, fim=date(2025, 3, 4))) == 1


def test_data_local():
    utc = datetime(2025, 3, 5, 1, 30, tzinfo=timezone.utc)
    assert data_local(utc, -180) == date(2025, 3, 4)
    assert data_local(utc, 0) == date(2025, 3, 5)
    assert data_local(utc, 120) == date(2025, 3, 5)  # fuso da exportação vence o padrão
    assert data_local(utc, None) == date(2025, 3, 4)  # America/Sao_Paulo
    assert data_local(utc.replace(tzinfo=None), None) == date(2025, 3, 4)  # SQLite devolve sem fuso


def test_check_do_fuso(session, atleta):
    a = _ativ(session, "1000000001")
    for ok in (-720, 840, None):
        a.fuso_min = ok
        session.commit()
    for ruim in (-721, 841, 900):
        a.fuso_min = ruim
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()
