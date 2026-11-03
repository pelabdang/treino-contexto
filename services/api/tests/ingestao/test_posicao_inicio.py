"""Posicao de inicio arredondada (issue #110, ADR 0007). FIT e JSON sinteticos gerados aqui, num lugar inventado.

A posicao fictícia (12.3456, -45.6789) vira (12.35, -45.68). Nenhum dado real.
"""

import json
from datetime import datetime, timezone

import pytest
from app.db.models import Atividade, Atleta
from app.ingestao.garmin import ler_atividade_fit, ler_exportacao
from app.ingestao.garmin.fit import ler_fit
from app.ingestao.garmin.posicao import arredondar_posicao, graus_de_semicirculos, posicao_de_semicirculos
from app.ingestao.garmin.tipos import de_fit, de_json
from app.ingestao.importacao import importar, importar_fit
from fit_tool.fit_file_builder import FitFileBuilder
from fit_tool.profile.messages.file_id_message import FileIdMessage
from fit_tool.profile.messages.lap_message import LapMessage
from fit_tool.profile.messages.record_message import RecordMessage
from fit_tool.profile.messages.session_message import SessionMessage
from fit_tool.profile.profile_type import FileType, Manufacturer, Sport, SubSport
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError

LAT, LON = 12.3456, -45.6789  # lugar inventado
ARRED = (12.35, -45.68)
INICIO_MS = 1_741_078_800_000  # 2025-03-04 09:00 UTC


def _fit(session_pos=None, lap_pos=None, sub_sport=SubSport.GENERIC, sport=Sport.RUNNING, serie=1,
         fim=None, records=()) -> bytes:
    b = FitFileBuilder(auto_define=True, min_string_size=50)
    fid = FileIdMessage()
    fid.type = FileType.ACTIVITY
    fid.manufacturer = Manufacturer.GARMIN.value
    fid.product = 1
    fid.serial_number = serie
    fid.time_created = INICIO_MS
    b.add(fid)
    for pos in records:  # trajeto: nada disto pode ser lido
        r = RecordMessage()
        r.timestamp = INICIO_MS + 1000
        r.position_lat, r.position_long = pos
        b.add(r)
    lap = LapMessage()
    lap.message_index = 0
    lap.start_time = INICIO_MS
    lap.timestamp = INICIO_MS + 600_000
    lap.total_timer_time = 600
    lap.total_elapsed_time = 600
    lap.total_distance = 2000
    if lap_pos:
        lap.start_position_lat, lap.start_position_long = lap_pos
    b.add(lap)
    s = SessionMessage()
    s.message_index = 0
    s.start_time = INICIO_MS
    s.timestamp = INICIO_MS + 600_000
    s.total_timer_time = 600
    s.total_elapsed_time = 600
    s.total_distance = 2000
    s.sport = sport
    s.sub_sport = sub_sport
    if session_pos:
        s.start_position_lat, s.start_position_long = session_pos
    if fim:
        s.end_position_lat, s.end_position_long = fim
    b.add(s)
    return b.build().to_bytes()


def _json(tmp_path, itens: list[dict], nome="x_summarizedActivities.json"):
    base = {"activityId": 9001, "startTimeGmt": INICIO_MS, "duration": 600_000, "distance": 200_000,
            "activityType": "running", "sportType": "RUNNING"}
    p = tmp_path / nome
    p.write_text(json.dumps([{"summarizedActivitiesExport": [{**base, **i} for i in itens]}]))
    return p


# ---------- funcoes de posicao ----------

def test_arredonda_a_2_casas():
    assert arredondar_posicao(LAT, LON) == ARRED
    assert arredondar_posicao(-12.3449, 45.6751) == (-12.34, 45.68)


@pytest.mark.parametrize("lat,lon", [
    (0, 0), (0.004, -0.004), (91, 10), (-90.5, 10), (10, 181), (10, -180.01),
    (None, 10), (10, None), ("12.3", "4.5"), (float("nan"), 1), (float("inf"), 1), (True, 1),
])
def test_valor_invalido_ou_zero_zero_vira_none(lat, lon):
    assert arredondar_posicao(lat, lon) is None


def test_limites_da_faixa_valem():
    assert arredondar_posicao(90, 180) == (90.0, 180.0)
    assert arredondar_posicao(-90, -180) == (-90.0, -180.0)


def test_semicirculos_para_graus():
    assert graus_de_semicirculos(2**30) == pytest.approx(90.0)
    assert graus_de_semicirculos(-(2**30)) == pytest.approx(-90.0)
    assert graus_de_semicirculos(0x7FFFFFFF) is None  # invalido do FIT
    assert graus_de_semicirculos(None) is None
    assert posicao_de_semicirculos(0x7FFFFFFF, 2**30) is None


# ---------- FIT ----------

def test_fitdecode_devolve_semicirculos_e_o_leitor_converte():
    lido = ler_fit(_fit(session_pos=(LAT, LON)))
    assert (lido.inicio_lat, lido.inicio_lon) == ARRED


def test_fit_sem_posicao_fica_none():
    lido = ler_fit(_fit())
    assert (lido.inicio_lat, lido.inicio_lon) == (None, None)


def test_fit_sem_posicao_na_session_usa_a_primeira_lap():
    lido = ler_fit(_fit(lap_pos=(LAT, LON)))
    assert (lido.inicio_lat, lido.inicio_lon) == ARRED


def test_session_vale_mais_que_a_lap():
    lido = ler_fit(_fit(session_pos=(LAT, LON), lap_pos=(-30.1, 20.2)))
    assert (lido.inicio_lat, lido.inicio_lon) == ARRED


def test_fit_zero_zero_vira_none():
    lido = ler_fit(_fit(session_pos=(0.0, 0.0)))
    assert (lido.inicio_lat, lido.inicio_lon) == (None, None)


def test_nada_do_trajeto_e_lido():
    """record e fim nao entram: sem posicao de inicio, o resultado e vazio mesmo com record e fim preenchidos."""
    dados = _fit(records=[(33.3, 44.4), (33.4, 44.5)], fim=(55.5, 66.6))
    lido = ler_fit(dados)
    assert (lido.inicio_lat, lido.inicio_lon) == (None, None)
    # com posicao de inicio, so ela aparece, arredondada
    lido = ler_fit(_fit(session_pos=(LAT, LON), records=[(33.3, 44.4)], fim=(55.5, 66.6)))
    assert (lido.inicio_lat, lido.inicio_lon) == ARRED
    campos = {k for k in vars(lido)}
    assert not any("fim" in c or "record" in c or "trajeto" in c for c in campos)


@pytest.mark.parametrize("sport,sub", [
    (Sport.RUNNING, SubSport.TREADMILL), (Sport.SWIMMING, SubSport.LAP_SWIMMING),
    (Sport.CYCLING, SubSport.VIRTUAL_ACTIVITY),
])
def test_fit_indoor_nao_guarda_posicao(sport, sub):
    a = ler_atividade_fit(_fit(session_pos=(LAT, LON), sport=sport, sub_sport=sub))
    assert a.subtipo in ("esteira", "piscina", "virtual")
    assert (a.inicio_lat, a.inicio_lon) == (None, None)


def test_fit_ao_ar_livre_guarda_posicao():
    for sport, sub in ((Sport.RUNNING, SubSport.TRAIL), (Sport.SWIMMING, SubSport.OPEN_WATER),
                       (Sport.CYCLING, SubSport.GENERIC)):
        a = ler_atividade_fit(_fit(session_pos=(LAT, LON), sport=sport, sub_sport=sub))
        assert (a.inicio_lat, a.inicio_lon) == ARRED


def test_subtipo_virtual():
    assert de_json("virtual_ride", "CYCLING") == ("ciclismo", "virtual")
    assert de_json("indoor_cycling", None) == ("ciclismo", "esteira")
    assert de_json("cycling", None) == ("ciclismo", None)
    assert de_fit("cycling", "virtual_activity") == ("ciclismo", "virtual")


# ---------- JSON ----------

def test_json_le_start_latitude_e_longitude(tmp_path):
    (a,) = ler_exportacao(_json(tmp_path, [{"startLatitude": LAT, "startLongitude": LON}]))
    assert (a.inicio_lat, a.inicio_lon) == ARRED


def test_json_sem_posicao_ou_invalida(tmp_path):
    itens = [
        {"activityId": 1, "startTimeGmt": INICIO_MS},
        {"activityId": 2, "startTimeGmt": INICIO_MS + 3_600_000, "startLatitude": 0.0, "startLongitude": 0.0},
        {"activityId": 3, "startTimeGmt": INICIO_MS + 7_200_000, "startLatitude": 123.4, "startLongitude": 5.0},
        {"activityId": 4, "startTimeGmt": INICIO_MS + 10_800_000, "startLatitude": LAT},  # par incompleto
    ]
    for a in ler_exportacao(_json(tmp_path, itens)):
        assert (a.inicio_lat, a.inicio_lon) == (None, None)


@pytest.mark.parametrize("tipo", ["treadmill_running", "lap_swimming", "virtual_ride", "indoor_cycling"])
def test_json_indoor_nao_guarda_posicao(tmp_path, tipo):
    (a,) = ler_exportacao(_json(tmp_path, [{"activityType": tipo, "startLatitude": LAT, "startLongitude": LON}]))
    assert a.subtipo in ("esteira", "piscina", "virtual")
    assert (a.inicio_lat, a.inicio_lon) == (None, None)


def test_json_e_fit_casam_vale_o_json(tmp_path):
    pasta = tmp_path / "exp"
    pasta.mkdir()
    _json(pasta, [{"startLatitude": 40.1234, "startLongitude": 10.9876}])
    (pasta / "a.fit").write_bytes(_fit(session_pos=(LAT, LON)))
    (a,) = ler_exportacao(pasta)
    assert (a.inicio_lat, a.inicio_lon) == (40.12, 10.99)
    assert len(a.voltas) == 1  # o FIT casou


def test_json_sem_posicao_e_fit_com_posicao_usa_o_fit(tmp_path):
    pasta = tmp_path / "exp"
    pasta.mkdir()
    _json(pasta, [{}])
    (pasta / "a.fit").write_bytes(_fit(session_pos=(LAT, LON)))
    (a,) = ler_exportacao(pasta)
    assert (a.inicio_lat, a.inicio_lon) == ARRED


def test_json_indoor_e_fit_com_posicao_continua_sem(tmp_path):
    pasta = tmp_path / "exp"
    pasta.mkdir()
    _json(pasta, [{"activityType": "treadmill_running"}])
    (pasta / "a.fit").write_bytes(_fit(session_pos=(LAT, LON)))
    (a,) = ler_exportacao(pasta)
    assert (a.subtipo, a.inicio_lat, a.inicio_lon) == ("esteira", None, None)


# ---------- banco ----------

@pytest.fixture
def atleta(session):
    a = Atleta(nome="Atleta Ficticio")
    session.add(a)
    session.commit()
    return a


def _todas(session):
    return list(session.scalars(select(Atividade).order_by(Atividade.id)))


def test_importar_fit_grava_a_posicao_arredondada(session, atleta, tmp_path):
    r = importar_fit(session, atleta.id, _fit(session_pos=(LAT, LON), records=[(33.3, 44.4)]), tmp_path / "fit")
    ativ = session.get(Atividade, r.atividade_id)
    assert (ativ.inicio_lat, ativ.inicio_lon) == ARRED


def test_importar_fit_indoor_grava_null(session, atleta, tmp_path):
    dados = _fit(session_pos=(LAT, LON), sub_sport=SubSport.TREADMILL)
    ativ = session.get(Atividade, importar_fit(session, atleta.id, dados, tmp_path / "fit").atividade_id)
    assert (ativ.subtipo, ativ.inicio_lat, ativ.inicio_lon) == ("esteira", None, None)


def test_importar_grava_a_posicao_e_reimportar_nao_muda(session, tmp_path):
    p = _json(tmp_path, [{"startLatitude": LAT, "startLongitude": LON}])
    rel = importar(session, p, "Atleta Ficticio")
    assert rel.inseridas == 1
    (ativ,) = _todas(session)
    assert (ativ.inicio_lat, ativ.inicio_lon) == ARRED
    rel = importar(session, p, "Atleta Ficticio")
    assert (rel.inseridas, rel.atualizadas, rel.ignoradas) == (0, 0, 1)


def test_reimportar_preenche_atividade_antiga_sem_duplicar(session, tmp_path):
    sem = _json(tmp_path, [{}], "a_summarizedActivities.json")
    importar(session, sem, "Atleta Ficticio")
    assert [(a.inicio_lat, a.inicio_lon) for a in _todas(session)] == [(None, None)]
    id_antes = _todas(session)[0].id

    com = _json(tmp_path, [{"startLatitude": LAT, "startLongitude": LON}], "b_summarizedActivities.json")
    rel = importar(session, com, "Atleta Ficticio")
    assert (rel.inseridas, rel.atualizadas) == (0, 1)
    (ativ,) = _todas(session)
    assert ativ.id == id_antes and (ativ.inicio_lat, ativ.inicio_lon) == ARRED
    assert importar(session, com, "Atleta Ficticio").ignoradas == 1


def test_reimportar_sem_posicao_nao_apaga_a_gravada(session, tmp_path):
    importar(session, _json(tmp_path, [{"startLatitude": LAT, "startLongitude": LON}], "a_summarizedActivities.json"),
             "Atleta Ficticio")
    importar(session, _json(tmp_path, [{}], "b_summarizedActivities.json"), "Atleta Ficticio")
    (ativ,) = _todas(session)
    assert (ativ.inicio_lat, ativ.inicio_lon) == ARRED


def test_atividade_que_virou_indoor_perde_a_posicao(session, tmp_path):
    importar(session, _json(tmp_path, [{"startLatitude": LAT, "startLongitude": LON}], "a_summarizedActivities.json"),
             "Atleta Ficticio")
    rel = importar(session, _json(tmp_path, [{"activityType": "treadmill_running", "startLatitude": LAT,
                                              "startLongitude": LON}], "b_summarizedActivities.json"),
                   "Atleta Ficticio")
    assert rel.atualizadas == 1
    (ativ,) = _todas(session)
    assert (ativ.subtipo, ativ.inicio_lat, ativ.inicio_lon) == ("esteira", None, None)


def test_upload_preenche_posicao_de_linha_da_exportacao_sem_duplicar(session, atleta, tmp_path):
    rel = importar(session, _json(tmp_path, [{}]), "Atleta Ficticio")
    assert rel.inseridas == 1
    atleta_id = _todas(session)[0].atleta_id
    r = importar_fit(session, atleta_id, _fit(session_pos=(LAT, LON)), tmp_path / "fit")
    assert r.resultado == "atualizada"
    assert session.scalar(select(func.count()).select_from(Atividade)) == 1
    ativ = _todas(session)[0]
    assert (ativ.fonte, ativ.inicio_lat, ativ.inicio_lon) == ("garmin_export", *ARRED)


def test_upload_repetido_com_posicao_e_ignorado(session, atleta, tmp_path):
    dados = _fit(session_pos=(LAT, LON))
    importar_fit(session, atleta.id, dados, tmp_path / "fit")
    assert importar_fit(session, atleta.id, dados, tmp_path / "fit").resultado == "ignorada"


def test_check_do_banco(session, atleta):
    def nova(**kw):
        return Atividade(atleta_id=atleta.id, fonte="x", fonte_id=str(kw), modalidade="corrida",
                         inicio=datetime(2025, 1, 1, tzinfo=timezone.utc),
                         duracao_s=60, **kw)

    for kw in ({"inicio_lat": 10.0}, {"inicio_lon": 10.0}, {"inicio_lat": 91.0, "inicio_lon": 0.0},
               {"inicio_lat": 0.0, "inicio_lon": 181.0}):
        session.add(nova(**kw))
        with pytest.raises(IntegrityError):
            session.flush()
        session.rollback()
    session.add(nova(inicio_lat=-90.0, inicio_lon=180.0))
    session.add(nova())
    session.commit()
    assert session.scalar(text("select count(*) from atividade")) == 2
