"""Parser da exportacao Garmin (issue #10), com as fixtures sinteticas da #8."""

import io
import json
import logging
import shutil
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

from worker.garmin import ler_exportacao, unidades

RAIZ = Path(__file__).resolve().parents[3]
ZIP = RAIZ / "tests" / "fixtures" / "garmin" / "exportacao_minima.zip"

# (intensidade, distancia_m, duracao_s, fc) -- tabela de tests/fixtures/garmin/gerar_fixtures.py
TABELA_A = [
    ("warmup", 2000, 720, 130),
    ("active", 1000, 255, 165), ("rest", 400, 150, 150),
    ("active", 1000, 252, 168), ("rest", 400, 150, 152),
    ("active", 1000, 250, 170), ("rest", 400, 150, 153),
    ("active", 1000, 251, 171), ("rest", 400, 150, 154),
    ("active", 1000, 249, 173), ("rest", 400, 150, 155),
    ("active", 1000, 248, 175),
    ("cooldown", 1500, 585, 135),
]


@pytest.fixture(autouse=True)
def _logger_ativo():
    """Outros testes (uvicorn/dictConfig) podem desativar loggers ja criados."""
    logger = logging.getLogger("worker.garmin.leitor")
    logger.disabled = False
    yield


def _por_id(ativs):
    return {a.fonte_id: a for a in ativs}


def _confere_fixture(ativs):
    assert len(ativs) == 5
    por_id = _por_id(ativs)
    a = por_id["1000000001"]
    assert a.fonte == "garmin_export"
    assert (a.modalidade, a.subtipo) == ("corrida", None)
    assert a.inicio == datetime(2025, 3, 4, 9, 0, tzinfo=timezone.utc)
    assert a.duracao_s == 3560 and a.distancia_m == 11500 and a.fc_media == 153
    assert len(a.voltas) == 13
    for v, (inten, dist, dur, fc) in zip(a.voltas, TABELA_A, strict=True):
        assert (v.intensidade, v.distancia_m, v.duracao_s, v.fc_media) == (inten, dist, dur, fc)
    assert [v.ordem for v in a.voltas] == list(range(13))
    assert a.voltas[0].inicio_offset_s == 0 and a.voltas[1].inicio_offset_s == 720
    assert a.arquivo_bruto.endswith("atleta-ficticio_1000000001.fit")

    b = por_id["1000000002"]  # FIT comeca 2 s depois do JSON: casa pela tolerancia
    assert (b.modalidade, b.subtipo) == ("corrida", "pista") and len(b.voltas) == 11
    assert b.inicio == datetime(2025, 3, 11, 9, 5, tzinfo=timezone.utc)  # horario do JSON
    assert len(por_id["1000000003"].voltas) == 8
    n = por_id["1000000004"]
    assert (n.modalidade, n.subtipo) == ("natacao", "piscina") and len(n.voltas) == 4
    e = por_id["1000000005"]
    assert (e.modalidade, e.subtipo) == ("corrida", "esteira")
    assert e.voltas == [] and e.arquivo_bruto.endswith("summarizedActivities.json")


def test_zip():
    _confere_fixture(ler_exportacao(ZIP))


def test_pasta(tmp_path):
    with zipfile.ZipFile(ZIP) as z:
        z.extractall(tmp_path)
    _confere_fixture(ler_exportacao(tmp_path))


def test_pasta_com_fits_ja_extraidos(tmp_path):
    with zipfile.ZipFile(ZIP) as z:
        z.extractall(tmp_path)
    interno = next(tmp_path.rglob("UploadedFiles_0-_Part1.zip"))
    with zipfile.ZipFile(interno) as z:
        z.extractall(interno.parent)
    interno.unlink()
    _confere_fixture(ler_exportacao(tmp_path))


def _extrair(tmp_path):
    with zipfile.ZipFile(ZIP) as z:
        z.extractall(tmp_path)
    json_ = next(tmp_path.rglob("*summarizedActivities.json"))
    interno = next(tmp_path.rglob("UploadedFiles_0-_Part1.zip"))
    with zipfile.ZipFile(interno) as z:
        z.extractall(tmp_path / "fits")
    interno.unlink()  # so os FITs soltos ficam na pasta
    return json_, tmp_path / "fits"


def test_json_solto(tmp_path):
    json_, _ = _extrair(tmp_path)
    ativs = ler_exportacao(json_)
    assert len(ativs) == 5
    assert all(a.voltas == [] for a in ativs)
    assert _por_id(ativs)["1000000001"].distancia_m == 11500


def test_fit_solto(tmp_path):
    _, fits = _extrair(tmp_path)
    [a] = ler_exportacao(fits / "atleta-ficticio_1000000001.fit")
    assert a.fonte_id.startswith("fit-")  # id derivado do file_id
    assert a.inicio == datetime(2025, 3, 4, 9, 0, tzinfo=timezone.utc)
    assert (a.modalidade, len(a.voltas)) == ("corrida", 13)
    assert a.distancia_m == 11500 and a.fc_media == 153
    assert ler_exportacao(fits / "atleta-ficticio_1000000001.fit")[0].fonte_id == a.fonte_id  # estavel


def test_fit_solto_pista_e_natacao(tmp_path):
    _, fits = _extrair(tmp_path)
    [b] = ler_exportacao(fits / "atleta-ficticio_1000000002.fit")
    assert (b.modalidade, b.subtipo) == ("corrida", "pista")
    [n] = ler_exportacao(fits / "atleta-ficticio_1000000004.fit")
    assert (n.modalidade, n.subtipo) == ("natacao", "piscina")


def test_fit_sem_json_correspondente_entra_como_atividade(tmp_path):
    json_, fits = _extrair(tmp_path)
    json_.write_text("[]")  # JSON vazio
    ativs = ler_exportacao(tmp_path)
    assert len(ativs) == 4 and all(a.fonte_id.startswith("fit-") for a in ativs)


def test_fit_corrompido_nao_derruba(tmp_path, caplog):
    json_, fits = _extrair(tmp_path)
    (fits / "atleta-ficticio_1000000001.fit").write_bytes(b"isto nao e um fit")
    with caplog.at_level(logging.WARNING):
        ativs = ler_exportacao(tmp_path)
    assert len(ativs) == 5
    assert _por_id(ativs)["1000000001"].voltas == []
    assert "FIT ignorado" in caplog.text and "sem FIT" in caplog.text


def test_fit_truncado_nao_derruba(tmp_path, caplog):
    _, fits = _extrair(tmp_path)
    f = fits / "atleta-ficticio_1000000003.fit"
    f.write_bytes(f.read_bytes()[:300])
    with caplog.at_level(logging.WARNING):
        assert len(ler_exportacao(tmp_path)) == 5
    assert "FIT ignorado" in caplog.text


def test_atividade_sem_fit_gera_aviso(caplog):
    with caplog.at_level(logging.WARNING):
        ler_exportacao(ZIP)
    assert "1000000005 sem FIT" in caplog.text


def test_json_invalido_nao_derruba(tmp_path, caplog):
    json_, _ = _extrair(tmp_path)
    json_.write_text("{ quebrado")
    with caplog.at_level(logging.WARNING):
        assert len(ler_exportacao(tmp_path)) == 4  # so os FITs
    assert "JSON invalido" in caplog.text


def test_fora_da_tolerancia_nao_casa(tmp_path):
    json_, fits = _extrair(tmp_path)
    texto = json_.read_text().replace("1741078800000", "1741078900000")  # +100 s
    json_.write_text(texto)
    por_id = _por_id(ler_exportacao(tmp_path))
    assert por_id["1000000001"].voltas == []
    assert len(ler_exportacao(tmp_path)) == 6  # o FIT sobra como atividade propria


def test_caminho_inexistente(tmp_path):
    with pytest.raises(FileNotFoundError):
        ler_exportacao(tmp_path / "nao-existe.zip")


def test_unidades():
    assert unidades.ms_para_s(3_560_000) == 3560
    assert unidades.cm_para_m(1_150_000) == 11500
    assert unidades.epoch_ms_para_datetime(1741078800000) == datetime(2025, 3, 4, 9, 0, tzinfo=timezone.utc)
    assert unidades.para_utc(datetime(2025, 1, 1)).tzinfo is timezone.utc


def test_inicio_local_das_fixtures():
    por_id = _por_id(ler_exportacao(ZIP))
    a, b = por_id["1000000001"], por_id["1000000002"]  # A e B em UTC-3
    assert a.inicio_local.isoformat() == "2025-03-04T06:00:00-03:00"
    assert b.inicio_local.isoformat() == "2025-03-11T06:05:00-03:00"
    assert a.inicio_local == a.inicio  # mesmo instante
    assert a.inicio_local.date().isoformat() == "2025-03-04"
    # as demais nao tem startTimeLocal: None (a #14 aplica o fallback)
    assert all(por_id[i].inicio_local is None for i in ("1000000003", "1000000004", "1000000005"))


def test_unidades_inicio_local():
    d = unidades.inicio_local(1741078800000, 1741078800000 - 3 * 3600_000)
    assert d.utcoffset().total_seconds() == -3 * 3600


def test_inicio_local_fora_de_utc_menos_12_a_mais_14_vira_none(tmp_path):
    json_, _ = _extrair(tmp_path)
    gmt = 1741078800000
    for horas, esperado_none in ((14, False), (15, True), (-12, False), (-13, True)):
        dados = json.loads(json_.read_text())
        item = dados[0]["summarizedActivitiesExport"][0]  # atividade A, que ja tem startTimeLocal
        item["startTimeLocal"] = gmt + horas * 3600_000
        novo = json.dumps(dados)
        alvo = tmp_path / f"j{horas}.json"
        alvo.write_text(novo)
        a = _por_id(ler_exportacao(alvo))["1000000001"]
        assert (a.inicio_local is None) == esperado_none


def _fit_nao_atividade() -> bytes:
    from fit_tool.fit_file_builder import FitFileBuilder
    from fit_tool.profile.messages.file_id_message import FileIdMessage
    from fit_tool.profile.profile_type import FileType, Manufacturer

    b = FitFileBuilder(auto_define=True, min_string_size=50)
    fid = FileIdMessage()
    fid.type = FileType.MONITORING_B
    fid.manufacturer = Manufacturer.GARMIN.value
    fid.product = 1
    fid.serial_number = 1
    fid.time_created = 1741078800000
    b.add(fid)
    return b.build().to_bytes()


def test_fit_que_nao_e_atividade_e_ignorado_sem_aviso(tmp_path, caplog):
    _, fits = _extrair(tmp_path)
    (fits / "monitoramento.fit").write_bytes(_fit_nao_atividade())
    with caplog.at_level(logging.WARNING):
        ativs = ler_exportacao(tmp_path)
    assert len(ativs) == 5  # nada de atividade nova
    assert "monitoramento" not in caplog.text and "FIT ignorado" not in caplog.text


def test_copias_do_mesmo_fit_sao_lidas_uma_vez(tmp_path):
    """A exportacao real traz a mesma arvore em varias copias (pasta, DI_CONNECT/, Arquivo.zip)."""
    _, fits = _extrair(tmp_path)
    copia = tmp_path / "copia"
    shutil.copytree(fits, copia)
    ativs = ler_exportacao(tmp_path)
    assert len(ativs) == 5 and len(_por_id(ativs)["1000000001"].voltas) == 13


def test_ignora_lixo_do_finder_e_arquivos_irrelevantes(tmp_path):
    json_, fits = _extrair(tmp_path)
    (tmp_path / "__MACOSX").mkdir()
    (tmp_path / "__MACOSX" / "._x.fit").write_bytes(b"lixo")
    (tmp_path / "._atleta_1.fit").write_bytes(b"lixo")
    (tmp_path / "foto.png").write_bytes(b"png")
    (tmp_path / "outro_gear.json").write_text("[]")
    assert len(ler_exportacao(tmp_path)) == 5


def test_json_paginado(tmp_path):
    """A exportacao real divide o resumo em varios arquivos (_1_, _301_...)."""
    json_, _ = _extrair(tmp_path)
    dados = json.loads(json_.read_text())
    itens = dados[0]["summarizedActivitiesExport"]
    json_.write_text(json.dumps([{"summarizedActivitiesExport": itens[:2]}]))
    (json_.parent / "x_301_summarizedActivities.json").write_text(
        json.dumps([{"summarizedActivitiesExport": itens[2:]}]))
    assert len(ler_exportacao(tmp_path)) == 5
