"""Confere as fixtures sinteticas do clima e o oraculo (Meta 4, issue #111; ADR 0007).

Tudo inventado (Parque do Exemplo). Os testes da #112 (leitor) e da #113 (cliente/comando) usam estes
arquivos e o ``oraculo_clima.json``. Aqui conferimos que as fixtures tem o que o oraculo diz e que o oraculo,
escrito a mao (ver docs/metricas/clima-oraculo.md), bate com a resposta gravada pela conta de media ponderada
pelo tempo de sobreposicao das horas cheias UTC (ADR 0007, item 4). Nenhum teste chama a rede.
"""

import importlib.util
import json
import sys
import zipfile
from datetime import datetime, timedelta, timezone
from fractions import Fraction
from pathlib import Path

import fitdecode
import pytest

PASTA = Path(__file__).parent / "fixtures" / "clima"
ANTIGAS = Path(__file__).parent / "fixtures" / "garmin" / "fit"
FATOR_SEMICIRCULO = 180 / 2**31
ORACULO = json.loads((PASTA / "oraculo_clima.json").read_text())
CASOS = {c["id"]: c for c in ORACULO["casos"]}
VARIAVEIS = {  # chave do oraculo -> variavel da resposta do Open-Meteo
    "temperatura_c": "temperature_2m",
    "sensacao_c": "apparent_temperature",
    "umidade_pct": "relative_humidity_2m",
    "vento_kmh": "wind_speed_10m",
}


@pytest.fixture(scope="module")
def gerador():
    spec = importlib.util.spec_from_file_location("gerar_fixtures_clima", PASTA / "gerar_fixtures_clima.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


# --------------------------------------------------------------------------
# leitura minima (so para conferir; o leitor de verdade e da #112)
# --------------------------------------------------------------------------
def _mensagens(caminho: Path, nome: str) -> list[dict]:
    saida = []
    with fitdecode.FitReader(str(caminho)) as r:
        for q in r:
            if isinstance(q, fitdecode.FitDataMessage) and q.name == nome:
                saida.append({
                    "lat": q.get_value("start_position_lat", fallback="AUSENTE"),
                    "lon": q.get_value("start_position_long", fallback="AUSENTE"),
                    "sub_sport": q.get_value("sub_sport", fallback=None),
                    "inicio": q.get_value("start_time", fallback=None),
                    "duracao": q.get_value("total_elapsed_time", fallback=None),
                })
    return saida


def _graus(semicirculos: int) -> float:
    return semicirculos * FATOR_SEMICIRCULO


def _itens_json() -> list[dict]:
    return json.loads((PASTA / "exportacao_clima.json").read_text())[0]["summarizedActivitiesExport"]


# --------------------------------------------------------------------------
# geracao
# --------------------------------------------------------------------------
def test_geracao_e_deterministica_e_versionada(gerador, tmp_path):
    gerador.main(tmp_path / "a")
    gerador.main(tmp_path / "b")
    for rel, conteudo in gerador.montar_tudo().items():
        assert (tmp_path / "a" / rel).read_bytes() == (tmp_path / "b" / rel).read_bytes()
        assert (PASTA / rel).read_bytes() == conteudo, f"{rel} desatualizado: rode gerar_fixtures_clima.py"


# --------------------------------------------------------------------------
# posicao nos FIT novos
# --------------------------------------------------------------------------
def test_posicao_na_session_vira_12_35_e_menos_45_68():
    for nome in ("corrida_ar_livre.fit", "corrida_longa_4_horas.fit"):
        (sessao,) = _mensagens(PASTA / "fit" / nome, "session")
        assert round(_graus(sessao["lat"]), 2) == 12.35
        assert round(_graus(sessao["lon"]), 2) == -45.68
        # exata e inventada: 12.3456 / -45.6789 (a 1 semicirculo de erro, ~8e-8 graus)
        assert _graus(sessao["lat"]) == pytest.approx(12.3456, abs=1e-6)
        assert _graus(sessao["lon"]) == pytest.approx(-45.6789, abs=1e-6)


def test_posicao_so_na_primeira_lap():
    arquivo = PASTA / "fit" / "corrida_posicao_na_lap.fit"
    (sessao,) = _mensagens(arquivo, "session")
    assert sessao["lat"] == "AUSENTE" and sessao["lon"] == "AUSENTE"
    lap1, lap2 = _mensagens(arquivo, "lap")
    assert round(_graus(lap1["lat"]), 2) == 12.35
    assert round(_graus(lap1["lon"]), 2) == -45.68
    # a segunda lap tem OUTRA posicao inventada, que o leitor nao pode usar
    assert round(_graus(lap2["lat"]), 2) == 12.90
    assert round(_graus(lap2["lon"]), 2) == -45.12


def test_esteira_tem_coordenada_no_arquivo_mas_e_esteira():
    arquivo = PASTA / "fit" / "esteira_com_posicao.fit"
    (sessao,) = _mensagens(arquivo, "session")
    assert round(_graus(sessao["lat"]), 2) == 12.35
    assert round(_graus(sessao["lon"]), 2) == -45.68
    assert sessao["sub_sport"] == "treadmill"


def test_posicao_zero_e_posicao_invalida():
    (zero,) = _mensagens(PASTA / "fit" / "corrida_posicao_zero.fit", "session")
    assert zero["lat"] == 0 and zero["lon"] == 0
    # 0x7FFFFFFF e o "invalido" do FIT: o fitdecode devolve None
    (invalida,) = _mensagens(PASTA / "fit" / "corrida_posicao_invalida.fit", "session")
    assert invalida["lat"] is None and invalida["lon"] is None


def test_so_ha_posicoes_inventadas_nos_fit():
    """Repositorio publico: toda posicao do arquivo e do Parque do Exemplo, da segunda lap inventada ou zero."""
    permitidas = {(12.35, -45.68), (12.90, -45.12), (0.0, 0.0)}
    for arquivo in sorted((PASTA / "fit").glob("*.fit")):
        for nome in ("session", "lap"):
            for m in _mensagens(arquivo, nome):
                if isinstance(m["lat"], int):
                    par = (round(_graus(m["lat"]), 2), round(_graus(m["lon"]), 2))
                    assert par in permitidas, f"{arquivo.name}: posicao fora da lista inventada"


def test_fit_novos_tem_inicio_e_duracao_do_oraculo():
    for caso in ORACULO["casos"]:
        if not caso["arquivo"].endswith(".fit"):
            continue
        (sessao,) = _mensagens(PASTA / caso["arquivo"], "session")
        assert sessao["inicio"].strftime("%Y-%m-%dT%H:%M:%SZ") == caso["inicio_utc"]
        assert sessao["duracao"] == caso["duracao_s"]


# --------------------------------------------------------------------------
# posicao ausente nas fixtures antigas
# --------------------------------------------------------------------------
def test_fit_antigos_nao_tem_posicao():
    antigos = sorted(ANTIGAS.glob("*.fit"))
    assert antigos, "fixtures antigas sumiram"
    for arquivo in antigos:
        if arquivo.name == "upload_truncado.fit":
            continue  # truncado de proposito: nao decodifica por inteiro
        for nome in ("session", "lap"):
            for m in _mensagens(arquivo, nome):
                assert m["lat"] == "AUSENTE" and m["lon"] == "AUSENTE", arquivo.name


def test_json_antigo_nao_tem_posicao():
    with zipfile.ZipFile(PASTA.parent / "garmin" / "exportacao_minima.zip") as z:
        nome = next(n for n in z.namelist() if n.endswith("summarizedActivities.json"))
        itens = json.loads(z.read(nome))[0]["summarizedActivitiesExport"]
    assert itens
    assert not any("startLatitude" in i or "startLongitude" in i for i in itens)


# --------------------------------------------------------------------------
# JSON de exportacao
# --------------------------------------------------------------------------
def test_json_tem_start_latitude_e_longitude_nas_atividades_com_posicao():
    por_id = {i["activityId"]: i for i in _itens_json()}
    corrida = por_id[3000000101]
    assert (corrida["startLatitude"], corrida["startLongitude"]) == (12.3456, -45.6789)
    assert (por_id[3000000102]["startLatitude"], por_id[3000000102]["activityType"]) == (12.3456, "treadmill_running")
    assert por_id[3000000104]["activityType"] == "virtual_ride"
    assert por_id[3000000104]["startLatitude"] == 12.3456
    assert (por_id[3000000103]["startLatitude"], por_id[3000000103]["startLongitude"]) == (0.0, 0.0)
    assert "startLatitude" not in por_id[3000000105] and "startLongitude" not in por_id[3000000105]


def test_json_bate_com_o_oraculo():
    por_id = {i["activityId"]: i for i in _itens_json()}
    for caso in ORACULO["casos"]:
        if "#" not in caso["arquivo"]:
            continue
        item = por_id[int(caso["arquivo"].split("#")[1])]
        inicio = datetime.fromtimestamp(item["startTimeGmt"] / 1000, tz=timezone.utc)
        assert inicio.strftime("%Y-%m-%dT%H:%M:%SZ") == caso["inicio_utc"]
        assert item["duration"] / 1000 == caso["duracao_s"]


# --------------------------------------------------------------------------
# resposta gravada
# --------------------------------------------------------------------------
def _resposta(chave: str) -> dict:
    return json.loads((PASTA / ORACULO["respostas"][chave]).read_text())


@pytest.mark.parametrize("chave", ["normal", "com_null"])
def test_resposta_tem_o_formato_documentado(chave):
    r = _resposta(chave)
    assert "sintetica" in r["_aviso"].lower() and "nao foi gravada da rede" in r["_aviso"].lower()
    assert r["timezone"] == "GMT" and r["utc_offset_seconds"] == 0
    h = r["hourly"]
    assert h["time"] == [f"2026-05-10T{n:02d}:00" for n in range(24)]
    for variavel in VARIAVEIS.values():
        assert len(h[variavel]) == len(h["time"]) == 24
    assert r["hourly_units"]["wind_speed_10m"] == "km/h"


def test_resposta_com_null_difere_so_nos_nulls():
    normal, com_null = _resposta("normal")["hourly"], _resposta("com_null")["hourly"]
    diferentes = [(v, i) for v in VARIAVEIS.values() for i in range(24) if normal[v][i] != com_null[v][i]]
    assert diferentes == [("temperature_2m", 10), ("apparent_temperature", 11)]
    assert all(com_null[v][i] is None for v, i in diferentes)


# --------------------------------------------------------------------------
# oraculo x resposta gravada
# --------------------------------------------------------------------------
def _janela(inicio_utc: str, duracao_s: int) -> dict[int, Fraction]:
    """Peso (fracao do total) de cada hora cheia UTC tocada por [inicio, inicio + duracao]. ADR 0007, item 4."""
    inicio = datetime.fromisoformat(inicio_utc.replace("Z", "+00:00"))
    fim = inicio + timedelta(seconds=duracao_s)
    pesos: dict[int, Fraction] = {}
    hora = inicio.replace(minute=0, second=0, microsecond=0)
    while hora < fim:
        segundos = (min(fim, hora + timedelta(hours=1)) - max(inicio, hora)).total_seconds()
        if segundos > 0:
            pesos[hora.hour] = Fraction(int(segundos), duracao_s)
        hora += timedelta(hours=1)
    return pesos


def _esperado(caso: dict, resposta: dict) -> tuple[str, dict | None]:
    """Estado e clima pela conta do ADR, direto da resposta (independente do oraculo escrito a mao)."""
    pesos = _janela(caso["inicio_utc"], caso["duracao_s"])
    clima = {}
    for chave, variavel in VARIAVEIS.items():
        valores = [resposta["hourly"][variavel][h] for h in pesos]
        if any(v is None for v in valores):
            return "pendente", None
        clima[chave] = sum(p * Fraction(str(resposta["hourly"][variavel][h])) for h, p in pesos.items())
    return "ok", {k: float(v) for k, v in clima.items()}


COM_CLIMA = [c["id"] for c in ORACULO["casos"] if c["estado"] == "ok"]


@pytest.mark.parametrize("id_", COM_CLIMA)
def test_oraculo_janela_pesos_somam_um_e_batem_com_a_conta(id_):
    caso = CASOS[id_]
    pesos = _janela(caso["inicio_utc"], caso["duracao_s"])
    assert sum(pesos.values()) == 1
    # o oraculo escreve o peso como veio da conta a mao (por exemplo 6/15); compara como fracao
    assert [(j["hora_utc"], j["segundos"], Fraction(j["peso"])) for j in caso["janela"]] == [
        (f"2026-05-10T{h:02d}:00", int(p * caso["duracao_s"]), p) for h, p in pesos.items()
    ]


@pytest.mark.parametrize("id_", COM_CLIMA)
def test_oraculo_bate_com_a_resposta_normal(id_):
    caso = CASOS[id_]
    estado, clima = _esperado(caso, _resposta("normal"))
    assert estado == "ok" == caso["estado"]
    for chave, valor in clima.items():
        assert caso["clima"][chave] == pytest.approx(valor, abs=ORACULO["tolerancia_abs"] + 1e-12), chave


@pytest.mark.parametrize("id_", COM_CLIMA)
def test_oraculo_com_null_na_janela_e_pendente(id_):
    caso = CASOS[id_]
    estado, clima = _esperado(caso, _resposta("com_null"))
    assert estado == caso["estado_com_resposta_null"]
    assert (clima is None) == (estado == "pendente")


def test_contas_a_mao_da_nota():
    """As contas escritas em docs/metricas/clima-oraculo.md, uma a uma, com os numeros da resposta."""
    assert 0.8 * 26.8 + 0.2 * 27.9 == pytest.approx(27.02)
    assert 0.8 * 30.1 + 0.2 * 31.6 == pytest.approx(30.40)
    assert 0.8 * 71 + 0.2 * 67 == pytest.approx(70.2)
    assert 0.8 * 9.6 + 0.2 * 10.8 == pytest.approx(9.84)
    assert (27.9 + 28.7) / 2 == pytest.approx(28.3)
    assert (31.6 + 32.8) / 2 == pytest.approx(32.2)
    assert (67 + 63) / 2 == 65
    assert (10.8 + 11.5) / 2 == pytest.approx(11.15)
    assert (2 * 29.9 + 6 * 30.1 + 6 * 29.8 + 29.2) / 15 == pytest.approx(448.4 / 15)
    assert (2 * 34.7 + 6 * 35.0 + 6 * 34.4 + 33.5) / 15 == pytest.approx(34.62)
    assert (2 * 58 + 6 * 57 + 6 * 58 + 61) / 15 == pytest.approx(57.8)
    assert (2 * 12.9 + 6 * 13.1 + 6 * 12.6 + 11.7) / 15 == pytest.approx(12.78)


def test_oraculo_sem_clima_para_indoor_e_sem_posicao():
    for caso in ORACULO["casos"]:
        if caso["estado"] != "ok":
            assert caso["estado"] in {"indoor", "sem_posicao"}
            assert caso["posicao_guardada"] is None and caso["clima"] is None and caso["janela"] == []
            assert caso["estado_com_resposta_null"] == caso["estado"]
        else:
            assert caso["posicao_guardada"] == ORACULO["posicao_guardada_esperada"]


def test_estado_indoor_do_oraculo_vem_do_tipo_da_atividade():
    por_id = {i["activityId"]: i for i in _itens_json()}
    for id_, tipo in {"fit_esteira_com_posicao": None, "json_esteira_com_posicao": 3000000102,
                      "json_pedal_virtual_com_posicao": 3000000104}.items():
        assert CASOS[id_]["estado"] == "indoor"
        if tipo:
            assert por_id[tipo]["activityType"] in {"treadmill_running", "virtual_ride"}
