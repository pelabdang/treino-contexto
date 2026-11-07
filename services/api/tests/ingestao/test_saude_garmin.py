"""Leitor dos dados de saude da exportacao Garmin (Meta 6, #136), com as fixtures sinteticas da #135.

As tabelas esperadas estao escritas a mao a partir da linha do tempo de tests/fixtures/garmin/gerar_fixtures_saude.py.
"""

import io
import json
import logging
import zipfile
from datetime import date, datetime, timezone
from pathlib import Path

import pytest

from app.ingestao.garmin.modelos_saude import LimiarRegistro, ZonaFc, pace_s_km, velocidade_ms
from app.ingestao.garmin.saude import (
    ler_carga_dia,
    ler_limiares,
    ler_recordes,
    ler_saude,
    ler_zonas_json,
)

RAIZ = Path(__file__).resolve().parents[4]
PASTA = RAIZ / "tests" / "fixtures" / "garmin" / "saude"
ZIP_SAUDE = PASTA / "exportacao_saude.zip"
ZIP_SEM = PASTA / "exportacao_sem_saude.zip"
D = date


@pytest.fixture(scope="module")
def saude():
    return ler_saude(ZIP_SAUDE, dia_retrato=D(2025, 3, 21))


def test_limiar_uma_serie_por_grandeza_com_vigencia_em_dia(saude):
    # (grandeza, dia em que passou a valer, valor). Sem limiar antes de 05/03; FC 0 de 25/02 nao vira registro;
    # 08/03 so a FC muda (a velocidade segue a de 05/03); registros de VO2 max e o fora de ordem nao entram.
    esperado = [
        ("fc_bpm", D(2025, 3, 5), 158.0),
        ("fc_bpm", D(2025, 3, 8), 159.0),
        ("fc_bpm", D(2025, 3, 10), 163.0),
        ("velocidade_ms", D(2025, 3, 5), 3.70),
        ("velocidade_ms", D(2025, 3, 10), 3.85),
    ]
    assert [(r.grandeza, r.vigente_desde, pytest.approx(r.valor)) for r in saude.limiares] == esperado
    assert {r.origem for r in saude.limiares} == {"garmin_export"}


def test_velocidade_vem_em_m_s_dividido_por_10_e_o_pace_confere_a_mao():
    # 0,370 na fonte -> 0,370 x 10 = 3,70 m/s -> 1000 / 3,70 = 270,27 s/km (= 100 / 0,370)
    assert velocidade_ms(0.370) == pytest.approx(3.70)
    assert pace_s_km(3.70) == pytest.approx(270.27, abs=0.01)
    assert 100 / 0.370 == pytest.approx(pace_s_km(velocidade_ms(0.370)))
    # 0,385 -> 3,85 m/s -> 1000 / 3,85 = 259,74 s/km
    assert pace_s_km(velocidade_ms(0.385)) == pytest.approx(259.74, abs=0.01)
    # sanidade: pace de limiar de corredor recreativo fica entre 3:00 e 7:00 por km
    assert 180 < pace_s_km(velocidade_ms(0.370)) < 420


def test_registro_de_velocidade_expoe_o_pace_e_o_de_fc_nao(saude):
    vel = [r for r in saude.limiares if r.grandeza == "velocidade_ms"]
    assert [round(r.pace_s_km, 2) for r in vel] == [270.27, 259.74]
    assert all(r.pace_s_km is None for r in saude.limiares if r.grandeza == "fc_bpm")


def test_limiar_ordena_por_data_e_guarda_o_ultimo_valor_do_dia():
    def reg(quando, seq, **campos):
        return {"metaData": {"calendarDate": quando, "sequence": seq}, **campos}
    registros = [  # fora de ordem
        reg("2025-03-02T10:00:00.5", 2, lactateThresholdHearRate=165),
        reg("2025-03-02T08:00:00.0", 1, lactateThresholdHearRate=160, lactateThresholdSpeed=0.35),
        reg("2025-03-02T10:00:00.5", 3, lactateThresholdHearRate=166),  # mesmo instante: vale a maior sequencia
        reg("2025-03-01T08:00:00.0", 9, vo2MaxRunning=50.0),
    ]
    assert ler_limiares(registros) == [
        LimiarRegistro("fc_bpm", D(2025, 3, 2), 166.0),
        LimiarRegistro("velocidade_ms", D(2025, 3, 2), pytest.approx(3.5)),
    ]


def test_fc_zero_e_sem_limiar_e_nao_cancela_o_anterior():
    registros = [
        {"metaData": {"calendarDate": "2025-03-01T08:00:00.0", "sequence": 1}, "lactateThresholdHearRate": 0},
        {"metaData": {"calendarDate": "2025-03-02T08:00:00.0", "sequence": 2}, "lactateThresholdHearRate": 150},
        {"metaData": {"calendarDate": "2025-03-03T08:00:00.0", "sequence": 3}, "lactateThresholdHearRate": 0},
    ]
    assert ler_limiares(registros) == [LimiarRegistro("fc_bpm", D(2025, 3, 2), 150.0)]


def test_limiar_invalido_e_ignorado_com_aviso_sem_excecao():
    avisos = []
    registros = [
        "lixo",
        {"metaData": {"calendarDate": "nao e data"}, "lactateThresholdHearRate": 150},
        {"metaData": {"calendarDate": "2025-03-02T08:00:00.0"}, "lactateThresholdHearRate": "alto"},
        {"metaData": {"calendarDate": "2025-03-03T08:00:00.0"}, "lactateThresholdHearRate": 900},
        {"metaData": {"calendarDate": "2025-03-04T08:00:00.0"}, "lactateThresholdSpeed": 37.0},  # unidade errada
        {"metaData": {"calendarDate": "2025-03-05T08:00:00.0"}, "lactateThresholdHearRate": 150, "lactateThresholdSpeed": 0.4},
    ]
    r = ler_limiares(registros, avisos.append)
    assert [(x.grandeza, x.vigente_desde) for x in r] == [("fc_bpm", D(2025, 3, 5)), ("velocidade_ms", D(2025, 3, 5))]
    assert avisos


def test_zonas_do_json_sao_o_retrato_por_esporte(saude):
    json_ = [z for z in saude.zonas if z.origem == "garmin_export"]
    assert [(z.esporte, z.metodo, z.fc_max_bpm, z.fc_repouso_bpm) for z in json_] == [
        ("padrao", "HR_MAX", 188, 52), ("corrida", "HR_MAX", 188, 52), ("ciclismo", "HR_MAX", 184, 52)]
    corrida = json_[1]
    assert (corrida.zona1_min_bpm, corrida.zona2_min_bpm, corrida.zona3_min_bpm, corrida.zona4_min_bpm,
            corrida.zona5_min_bpm, corrida.zona5_max_bpm) == (94, 113, 132, 150, 169, 188)  # 50..90 % de 188, teto 188
    assert {z.vigente_desde for z in json_} == {D(2025, 3, 21)}  # o dia do retrato informado


def test_zonas_do_json_sem_dia_do_retrato_ficam_sem_data():
    assert {z.vigente_desde for z in ler_saude(ZIP_SAUDE).zonas if z.origem == "garmin_export"} == {None}


def test_historico_de_zonas_nos_fit_so_tem_linha_quando_as_zonas_mudam(saude):
    fit = [z for z in saude.zonas if z.origem == "garmin_fit"]
    # A (04/03, corrida) e C (06/03, corrida) tem as mesmas zonas -> uma linha; D (07/03, natacao) tem esporte padrao;
    # B (11/03, corrida) tem FC maxima 188.
    tabela = [(z.esporte, z.vigente_desde, z.metodo, z.fc_max_bpm, z.fc_repouso_bpm, z.zona1_min_bpm, z.zona2_min_bpm,
               z.zona3_min_bpm, z.zona4_min_bpm, z.zona5_min_bpm, z.zona5_max_bpm) for z in fit]
    assert tabela == [
        ("corrida", D(2025, 3, 4), "percent_max_hr", 190, 52, 95, 114, 133, 152, 171, 190),
        ("padrao", D(2025, 3, 7), "percent_max_hr", 190, 52, 95, 114, 133, 152, 171, 190),
        ("corrida", D(2025, 3, 11), "percent_max_hr", 188, 52, 94, 113, 132, 150, 169, 188),
    ]


def test_recordes(saude):
    def t(r):
        return (r.modalidade, r.categoria, r.valor, r.unidade, r.alcancado_em, r.atividade_fonte_id, r.atual)
    utc = timezone.utc
    assert [t(r) for r in saude.recordes] == [
        ("corrida", "Best 1km Run", 248.0, "s", datetime(2025, 3, 4, 10, 0, tzinfo=utc), "1000000001", False),
        ("corrida", "Best 5km Run", 1750.0, "s", datetime(2025, 3, 6, 8, 30, tzinfo=utc), "1000000003", True),
        ("corrida", "Farthest Run", 8000.0, "m", datetime(2025, 3, 6, 8, 30, tzinfo=utc), "1000000003", True),
        ("natacao", "Best 400m Pool Swim", 440.0, "s", datetime(2025, 3, 7, 7, 0, tzinfo=utc), "1000000004", True),
        ("outra", "Most Steps in a Day", 9000.0, "passos", datetime(2025, 3, 9, 0, 0, tzinfo=utc), None, True),  # id 0
        ("corrida", "Best 1km Run", 234.0, "s", datetime(2025, 3, 11, 9, 5, tzinfo=utc), "1000000002", True),
    ]


def test_recorde_invalido_e_ignorado_com_aviso():
    avisos = []
    blocos = [{"personalRecords": [
        {"personalRecordType": "Best 5km Run", "value": 1500.0, "prStartTimeGMT": "Thu Mar 06 08:30:00 GMT 2025", "activityId": 5},
        {"personalRecordType": "Best 5km Run", "value": "x", "prStartTimeGMT": "Thu Mar 06 08:30:00 GMT 2025"},
        {"personalRecordType": "Best 5km Run", "value": 1.0, "prStartTimeGMT": "ontem"},
        {"value": 1.0, "prStartTimeGMT": "Thu Mar 06 08:30:00 GMT 2025"},
    ]}, "lixo"]
    r = ler_recordes(blocos, avisos.append)
    assert [(x.categoria, x.valor) for x in r] == [("Best 5km Run", 1500.0)] and avisos


def test_carga_um_valor_por_dia_vale_o_item_de_maior_timestamp(saude):
    c = saude.carga_dia
    assert len(c) == 25 and c[0].dia == D(2025, 2, 24) and c[-1].dia == D(2025, 3, 20)
    assert [x.dia for x in c] == sorted({x.dia for x in c})
    # primeiro dia: sem razao (acwrStatus NONE)
    assert (c[0].carga_aguda, c[0].carga_cronica, c[0].razao) == (34.0, 54.0, None)
    # 04/03 tem dois itens: o parcial (aguda 69, 9h) perde para o final (aguda 79, 21h)
    dia4 = next(x for x in c if x.dia == D(2025, 3, 4))
    assert (dia4.carga_aguda, dia4.carga_cronica, dia4.razao) == (79.0, 48.0, 1.6)
    # dia com um item so (05/03): aguda = round(0,85 x 79) = 67; cronica = round(0,96 x 48 + 0,04 x 67) = 49
    dia5 = next(x for x in c if x.dia == D(2025, 3, 5))
    assert (dia5.carga_aguda, dia5.carga_cronica) == (67.0, 49.0)


def test_carga_com_calendar_date_ruim_e_ignorada():
    avisos = []
    itens = [{"calendarDate": None, "dailyTrainingLoadAcute": 1}, {"calendarDate": "x"},
             {"calendarDate": 1_741_046_400_000, "timestamp": 5, "dailyTrainingLoadAcute": 10},
             {"calendarDate": 1_741_046_400_000, "timestamp": 9, "dailyTrainingLoadChronic": 20}]
    r = ler_carga_dia(itens, avisos.append)
    assert len(r) == 1 and r[0].dia == D(2025, 3, 4)
    assert (r[0].carga_aguda, r[0].carga_cronica, r[0].razao) == (None, 20.0, None) and avisos


def test_zonas_json_incompletas_sao_ignoradas_com_aviso():
    avisos = []
    r = ler_zonas_json([{"sport": "RUNNING", "maxHeartRateUsed": 190}, "x"], None, avisos.append)
    assert r == [] and avisos


def test_exportacao_sem_saude_devolve_vazio_e_avisos(caplog):
    with caplog.at_level(logging.WARNING):
        s = ler_saude(ZIP_SEM)
    assert (s.limiares, s.zonas, s.recordes, s.carga_dia) == ([], [], [], [])
    assert len(s.avisos) == 5 and all("sem " in a or "nenhum" in a for a in s.avisos)
    assert any("limiar" in a for a in s.avisos) and any("recordes" in a for a in s.avisos)
    assert caplog.records  # tambem no log


def test_arvore_duplicada_le_cada_conteudo_uma_vez(tmp_path):
    esperado = ler_saude(ZIP_SAUDE)
    pasta = tmp_path / "exp"
    with zipfile.ZipFile(ZIP_SAUDE) as z:
        z.extractall(pasta)  # DI_CONNECT/ descompactado
        z.extractall(pasta / "copia" / "outra_pasta")  # a mesma arvore em outra pasta
    outro = io.BytesIO()
    with zipfile.ZipFile(outro, "w") as zo:  # e dentro de um zip interno
        for n in zipfile.ZipFile(ZIP_SAUDE).namelist():
            zo.writestr(n, zipfile.ZipFile(ZIP_SAUDE).read(n))
    (pasta / "Arquivo.zip").write_bytes(outro.getvalue())
    s = ler_saude(pasta)
    assert s.limiares == esperado.limiares and s.carga_dia == esperado.carga_dia
    assert s.recordes == esperado.recordes and s.zonas == esperado.zonas


def test_acha_por_pasta_e_sufixo_sem_o_identificador_do_usuario(tmp_path):
    pasta = tmp_path / "qualquer" / "DI-Connect-Wellness"
    pasta.mkdir(parents=True)
    reg = [{"metaData": {"calendarDate": "2025-03-05T09:00:00.0", "sequence": 1}, "lactateThresholdHearRate": 150}]
    (pasta / "pessoa@exemplo.com_userBioMetrics.json").write_text(json.dumps(reg))
    (pasta / "outro_arquivo.json").write_text("[]")
    s = ler_saude(tmp_path)
    assert [(x.grandeza, x.valor) for x in s.limiares] == [("fc_bpm", 150.0)]


def test_arquivo_corrompido_vira_aviso_sem_excecao(tmp_path):
    pasta = tmp_path / "DI-Connect-Wellness"
    pasta.mkdir()
    (pasta / "1_userBioMetrics.json").write_text("{ nao e json")
    (pasta / "1_heartRateZones.json").write_text('{"nao": "lista"}')
    (tmp_path / "ruim.zip").write_bytes(b"nao e zip")
    (tmp_path / "x.fit").write_bytes(b"nao e fit")
    s = ler_saude(tmp_path)
    assert (s.limiares, s.zonas) == ([], [])
    assert any("ilegivel" in a for a in s.avisos)


def test_caminho_inexistente_levanta_filenotfound(tmp_path):
    with pytest.raises(FileNotFoundError):
        ler_saude(tmp_path / "nao_existe")


def test_avisos_nao_trazem_dado_pessoal(tmp_path):
    pasta = tmp_path / "DI-Connect-Wellness"
    pasta.mkdir()
    (pasta / "pessoa@exemplo.com_userBioMetrics.json").write_text("{ ruim")
    s = ler_saude(tmp_path)
    assert not any("exemplo" in a or str(tmp_path) in a for a in s.avisos)


def test_zona_fc_e_imutavel():
    z = ZonaFc("corrida", "garmin_fit", None, None, None, None, 1, 2, 3, 4, 5, 6)
    with pytest.raises(Exception):
        z.esporte = "x"
