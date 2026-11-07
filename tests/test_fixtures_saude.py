"""Confere as fixtures sinteticas de saude e metricas da exportacao Garmin (Meta 6, issue #135).

A linha do tempo esperada esta no topo de tests/fixtures/garmin/gerar_fixtures_saude.py.
"""

import importlib.util
import io
import json
import re
import sys
import zipfile
from datetime import date, datetime, timezone
from pathlib import Path

import fitdecode
import pytest

PASTA = Path(__file__).parent / "fixtures" / "garmin"
ZIP_SAUDE = PASTA / "saude" / "exportacao_saude.zip"
ZIP_SEM = PASTA / "saude" / "exportacao_sem_saude.zip"

# Padrao de nome que o leitor (#136) usa: pasta + sufixo, nunca o identificador do usuario.
PADROES = {
    "limiar": re.compile(r"(^|/)DI-Connect-Wellness/[^/]*_userBioMetrics\.json$"),
    "zonas": re.compile(r"(^|/)DI-Connect-Wellness/[^/]*_heartRateZones\.json$"),
    "recordes": re.compile(r"(^|/)DI-Connect-Fitness/[^/]*_personalRecord\.json$"),
    "carga": re.compile(r"(^|/)DI-Connect-Metrics/MetricsAcuteTrainingLoad_\d{8}_\d{8}_[^/]*\.json$"),
}


@pytest.fixture(scope="module")
def gerador():
    spec = importlib.util.spec_from_file_location("gerar_fixtures_saude", PASTA / "gerar_fixtures_saude.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def _membros(caminho: Path) -> dict[str, bytes]:
    with zipfile.ZipFile(caminho) as z:
        return {n: z.read(n) for n in z.namelist()}


def _achar(membros, chave) -> list[str]:
    return sorted(n for n in membros if PADROES[chave].search(n))


def _json(membros, chave):
    achados = _achar(membros, chave)
    assert len(achados) == 1
    return json.loads(membros[achados[0]])


def test_geracao_e_deterministica_e_versionada(gerador, tmp_path):
    gerador.main(tmp_path / "a")
    gerador.main(tmp_path / "b")
    for nome, versionado in (("exportacao_saude.zip", ZIP_SAUDE), ("exportacao_sem_saude.zip", ZIP_SEM)):
        a = (tmp_path / "a" / "saude" / nome).read_bytes()
        assert a == (tmp_path / "b" / "saude" / nome).read_bytes()
        assert a == versionado.read_bytes(), f"{nome} desatualizado: rode gerar_fixtures_saude.py"


def test_arquivos_sao_achados_so_pela_pasta_e_pelo_sufixo():
    m = _membros(ZIP_SAUDE)
    assert len(_achar(m, "limiar")) == 1
    assert len(_achar(m, "zonas")) == 1
    assert len(_achar(m, "recordes")) == 1
    assert len(_achar(m, "carga")) == 2  # a carga vem em mais de um arquivo, cada um com um periodo no nome


def test_atleta_sem_saude_nao_tem_nenhum_dos_arquivos():
    m = _membros(ZIP_SEM)
    for chave in PADROES:
        assert _achar(m, chave) == []
    assert not any("Wellness" in n or "Metrics" in n for n in m)


def test_historico_de_limiar_tem_periodo_sem_limiar_e_duas_alteracoes():
    registros = _json(_membros(ZIP_SAUDE), "limiar")
    # 0 em lactateThresholdHearRate significa "sem limiar" (sentinela), nao uma FC de 0 bpm
    lt = sorted(
        ((r["metaData"]["calendarDate"][:10], r.get("lactateThresholdHearRate"), r.get("lactateThresholdSpeed"))
         for r in registros if "lactateThresholdHearRate" in r))
    assert lt == [("2025-02-25", 0, None), ("2025-03-05", 158, 0.370), ("2025-03-08", 159, None),
                  ("2025-03-10", 163, 0.385)]
    # o arquivo nao esta em ordem cronologica: o leitor precisa ordenar
    datas = [r["metaData"]["calendarDate"] for r in registros]
    assert datas != sorted(datas)
    # o nome do campo de FC tem o erro de grafia da Garmin ("Hear")
    assert all("lactateThresholdHeartRate" not in r for r in registros)


def test_zonas_sao_um_retrato_sem_data():
    zonas = _json(_membros(ZIP_SAUDE), "zonas")
    assert {z["sport"] for z in zonas} == {"DEFAULT", "RUNNING", "CYCLING"}
    assert all(z["trainingMethod"] == "HR_MAX" and "calendarDate" not in z for z in zonas)


def _fit_session_zonas(conteudo: bytes) -> dict | None:
    with fitdecode.FitReader(io.BytesIO(conteudo)) as r:
        for f in r:
            if isinstance(f, fitdecode.FitDataMessage) and f.name == "time_in_zone":
                if f.get_value("reference_mesg") == "session":
                    return {c: f.get_value(c, fallback=None) for c in (
                        "hr_calc_type", "max_heart_rate", "resting_heart_rate", "threshold_heart_rate",
                        "hr_zone_high_boundary", "time_in_hr_zone")}
    return None


def test_zonas_e_limiar_mudam_ao_longo_das_atividades_nos_fit():
    m = _membros(ZIP_SAUDE)
    interno = io.BytesIO(m["DI_CONNECT/DI-Connect-Uploaded-Files/UploadedFiles_0-_Part1.zip"])
    with zipfile.ZipFile(interno) as zi:
        fits = {n: zi.read(n) for n in zi.namelist()}
    z = {int(re.search(r"_(\d+)\.fit$", n).group(1)): _fit_session_zonas(c) for n, c in fits.items()}
    # A (04/03) antes de qualquer limiar; C e D (06 e 07/03) no 1o limiar; B (11/03) no 2o limiar e FC maxima nova
    assert z[1000000001]["threshold_heart_rate"] is None and z[1000000001]["max_heart_rate"] == 190
    assert z[1000000003]["threshold_heart_rate"] == 158 and z[1000000003]["max_heart_rate"] == 190
    assert z[1000000004]["threshold_heart_rate"] == 158
    assert z[1000000002]["threshold_heart_rate"] == 163 and z[1000000002]["max_heart_rate"] == 188
    assert z[1000000001]["hr_zone_high_boundary"] != z[1000000002]["hr_zone_high_boundary"]
    for v in z.values():
        assert v["hr_calc_type"] == "percent_max_hr" and v["resting_heart_rate"] == 52
        assert len(v["hr_zone_high_boundary"]) == 6 and len(v["time_in_hr_zone"]) == 7


def test_tempo_por_zona_soma_a_duracao_da_atividade(gerador):
    a = next(x for x in gerador.base.ATIVIDADES if x.id == 1000000003)
    limites = gerador.limites_zona(190)
    assert sum(gerador._tempos_por_zona(a.voltas, limites)) == sum(v[2] for v in a.voltas)


def test_carga_um_item_final_por_dia_e_dia_sem_razao():
    m = _membros(ZIP_SAUDE)
    itens = [i for n in _achar(m, "carga") for i in json.loads(m[n])]
    por_dia: dict[int, list[dict]] = {}
    for i in itens:
        por_dia.setdefault(i["calendarDate"], []).append(i)
    assert len(por_dia) == 25  # 24/02 a 20/03, sem buracos
    assert all(d % 86_400_000 == 0 for d in por_dia)  # calendarDate: meia-noite UTC em ms
    assert [d for d, v in por_dia.items() if len(v) > 1] != []  # ha dias com mais de um item
    primeiro = por_dia[min(por_dia)][0]
    assert primeiro["acwrStatus"] == "NONE" and "dailyAcuteChronicWorkloadRatio" not in primeiro
    dia = datetime(2025, 3, 4, tzinfo=timezone.utc)
    duplo = por_dia[int(dia.timestamp() * 1000)]
    assert len(duplo) == 2 and duplo[0]["timestamp"] < duplo[1]["timestamp"]


def test_recordes_ligam_a_atividade_e_o_recorde_sem_atividade_tem_id_zero():
    pr = _json(_membros(ZIP_SAUDE), "recordes")[0]["personalRecords"]
    ids = {1000000001, 1000000002, 1000000003, 1000000004, 0}
    assert {r["activityId"] for r in pr} <= ids
    atuais_1km = [r for r in pr if r["personalRecordType"] == "Best 1km Run" and r["current"]]
    assert len(atuais_1km) == 1
    assert re.fullmatch(r"[A-Z][a-z]{2} [A-Z][a-z]{2} \d\d \d\d:\d\d:\d\d GMT \d{4}", pr[0]["prStartTimeGMT"])


def test_parser_atual_ignora_os_arquivos_de_saude_e_le_as_cinco_atividades():
    sys.path.insert(0, str(Path(__file__).parent.parent / "services" / "api"))
    from app.ingestao.garmin.leitor import ler_exportacao

    atividades = ler_exportacao(ZIP_SAUDE)
    assert len(atividades) == 5
    sem = ler_exportacao(ZIP_SEM)
    assert [a.fonte_id for a in atividades] == [a.fonte_id for a in sem]
    assert date(2025, 3, 4) in {a.inicio.date() for a in atividades}
