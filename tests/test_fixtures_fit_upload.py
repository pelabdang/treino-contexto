"""FIT sinteticos do upload (Meta 3, issue #93; ADR 0006). Sem banco, sem dado real.

Os arquivos de tests/fixtures/garmin/fit/ sao gerados por gerar_fixtures.py. Aqui estao os valores esperados,
com a conta a mao, lidos pelo leitor FIT (ler_fit) e pela deteccao de tiros (tiros_1km@4).
"""

import importlib.util
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from app.metricas.tiros_1km import VoltaEntrada, agregar_sessao, detectar_tiros

try:  # o leitor esta mudando para a API (#92); aceita os dois lugares
    from app.ingestao.garmin.fit import FitSemAtividade, ler_fit
    from app.ingestao.garmin.tipos import de_fit
except ImportError:  # pragma: no cover
    from worker.garmin.fit import FitSemAtividade, ler_fit
    from worker.garmin.tipos import de_fit

PASTA = Path(__file__).parent / "fixtures" / "garmin"
FITS = PASTA / "fit"


def _utc(*a) -> datetime:
    return datetime(*a, tzinfo=timezone.utc)


def _ler(nome: str):
    return ler_fit((FITS / nome).read_bytes())


def _voltas(fit) -> list[VoltaEntrada]:
    return [
        VoltaEntrada(v.ordem, v.distancia_m, v.duracao_s, v.fc_media, v.intensidade) for v in fit.voltas
    ]


def _dist_s(x, y) -> float:
    return abs((x.inicio - y.inicio).total_seconds())


@pytest.fixture(scope="module")
def gerador():
    spec = importlib.util.spec_from_file_location("gerar_fixtures_upload", PASTA / "gerar_fixtures.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_arquivos_versionados_batem_com_o_gerador(gerador, tmp_path):
    gerador.main(tmp_path)
    gerados = {p.name: p.read_bytes() for p in (tmp_path / "fit").iterdir()}
    versionados = {p.name: p.read_bytes() for p in FITS.iterdir()}
    assert len(gerados) == 11
    assert gerados == versionados, "FIT versionado desatualizado: rode gerar_fixtures.py"


def test_intervalado_5x1km_entra_na_serie():
    fit = _ler("upload_intervalado_5x1km.fit")
    assert fit.inicio == _utc(2025, 4, 1, 9, 0, 0)
    assert de_fit(fit.sport, fit.sub_sport) == ("corrida", None)
    assert len(fit.voltas) == 11
    # distancia: 2000 + 5 x 1000 + 4 x 400 + 1500 = 10100 m; duracao: 720 + 1230 + 600 + 585 = 3135 s
    assert fit.distancia_m == 10100 and fit.duracao_s == 3135
    res = detectar_tiros(_voltas(fit))
    assert res.eh_intervalado and res.tiros == (1, 3, 5, 7, 9)
    tiros = [v for v in _voltas(fit) if v.ordem in res.tiros]
    p = agregar_sessao(1, fit.inicio.date(), tiros)
    # pace: (250+248+246+244+242) / 5000 x 1000 = 1230 / 5 = 246,0 s/km
    assert p.pace_s_km == pytest.approx(246.0)
    # FC: (250x166 + 248x169 + 246x171 + 244x173 + 242x176) / 1230 = 210282 / 1230 = 170,961
    assert p.fc_media == pytest.approx(210282 / 1230)
    assert p.fc_media == pytest.approx(170.961, abs=1e-3)


def test_rodagem_nao_entra_na_serie():
    fit = _ler("upload_rodagem_6km.fit")
    assert de_fit(fit.sport, fit.sub_sport) == ("corrida", None)
    assert len(fit.voltas) == 6
    # 6 x 1000 m = 6000 m; 355+352+350+351+349+348 = 2105 s
    assert fit.distancia_m == 6000 and fit.duracao_s == 2105
    assert not detectar_tiros(_voltas(fit)).eh_intervalado  # todos os km tem ritmo parecido


def test_mesma_atividade_da_exportacao_comeca_30_s_depois():
    fit = _ler("upload_mesma_atividade_1000000001.fit")
    original = _utc(2025, 3, 4, 9, 0, 0)  # inicio de 1000000001 na exportacao
    assert fit.inicio - original == timedelta(seconds=30)  # dentro da tolerancia de 60 s
    assert len(fit.voltas) == 13 and fit.distancia_m == 11500 and fit.duracao_s == 3560
    assert fit.id_derivado.startswith("fit-")  # chave diferente da do activityId: so os 60 s casam


def test_empate_candidatas_e_chegadas():
    a, b = _ler("empate_candidata_a.fit"), _ler("empate_candidata_b.fit")
    eq, perto_b = _ler("empate_chegada_equidistante.fit"), _ler("empate_chegada_mais_perto_de_b.fit")
    assert a.inicio == _utc(2025, 4, 8, 9, 0, 0)
    assert b.inicio == _utc(2025, 4, 8, 9, 0, 40)
    # chegada equidistante: 20 s de A e 20 s de B -> empate; vale a de menor id
    assert (_dist_s(eq, a), _dist_s(eq, b)) == (20, 20)
    # chegada perto de B: 30 s de A e 10 s de B -> vale B (inicio mais proximo)
    assert (_dist_s(perto_b, a), _dist_s(perto_b, b)) == (30, 10)
    # as candidatas estao a 40 s uma da outra: importadas em sequencia, B casaria com A (insira no banco)
    assert _dist_s(a, b) == 40
    assert len({f.id_derivado for f in (a, b, eq, perto_b)}) == 4
    for f in (a, b, eq, perto_b):
        assert de_fit(f.sport, f.sub_sport) == ("corrida", None)
        assert f.distancia_m == 3000 and f.duracao_s == 1074  # 360 + 358 + 356


def test_fit_truncado_e_invalido():
    with pytest.raises(ValueError) as e:
        _ler("upload_truncado.fit")
    assert not isinstance(e.value, FitSemAtividade)


def test_fit_que_nao_e_atividade():
    with pytest.raises(FitSemAtividade):
        _ler("upload_nao_atividade.fit")


def test_esteira_e_corrida_com_subtipo_esteira():
    fit = _ler("upload_esteira_4x1km.fit")
    assert de_fit(fit.sport, fit.sub_sport) == ("corrida", "esteira")  # a serie deixa a esteira de fora
    # 1500 + 4 x 1000 + 3 x 400 + 1000 = 7700 m; 560 + 1028 + 480 + 400 = 2468 s
    assert fit.distancia_m == 7700 and fit.duracao_s == 2468
    assert detectar_tiros(_voltas(fit)).tiros == (1, 3, 5, 7)  # tiros reais, mas fora da serie por ser esteira


def test_natacao_entra_no_banco_e_fica_fora_da_serie():
    fit = _ler("upload_natacao_400m.fit")
    modalidade, subtipo = de_fit(fit.sport, fit.sub_sport)
    assert (modalidade, subtipo) == ("natacao", "piscina")
    # 4 x 100 m = 400 m; 108 + 110 + 113 + 116 = 447 s
    assert fit.distancia_m == 400 and fit.duracao_s == 447
    assert len(fit.voltas) == 4
    assert not detectar_tiros(_voltas(fit), modalidade).eh_intervalado  # so corrida entra na serie


def test_nenhum_fit_tem_gps():
    from fit_tool.fit_file import FitFile
    from fit_tool.profile.messages.record_message import RecordMessage

    for caminho in FITS.glob("*.fit"):
        if caminho.name == "upload_truncado.fit":
            continue
        for r in FitFile.from_bytes(caminho.read_bytes()).records:
            if isinstance(r.message, RecordMessage):
                assert r.message.position_lat is None and r.message.position_long is None
