"""Formato das respostas do Garmin para a recuperacao (Meta 10, issue #371).

Confere que as fixtures de `tests/fixtures/meta10/` seguem o formato descrito em
`docs/modulos/ingestao-garmin.md` (secao "Sono, VFC e FC de repouso"): nomes de campo, tipos, unidades e as relacoes
entre campos. Nao ha leitor nem banco ainda (#372). Tudo sintetico: nenhum arquivo e resposta gravada de uma conta.
"""

import datetime as dt
import json
from pathlib import Path

import pytest

PASTA = Path(__file__).parent / "fixtures" / "meta10"
MARCADOR = "MARCADOR-SINTETICO-META10-NAO-LOGAR"
ARQUIVOS = sorted(p.name for p in PASTA.glob("*.json"))
SONO = [n for n in ARQUIVOS if n.startswith("sono_")]
SONO_COM_NOITE = [n for n in SONO if n not in ("sono_dia_sem_dado.json", "sono_dto_sem_duracao.json")]
VFC = [n for n in ARQUIVOS if n.startswith("vfc_")]
RHR = [n for n in ARQUIVOS if n.startswith("rhr_")]


def _ler(nome):
    return json.loads((PASTA / nome).read_text())


def _dia(ms):
    return dt.datetime.fromtimestamp(ms / 1000, dt.timezone.utc).date()


def _inteiro(v):
    return isinstance(v, int) and not isinstance(v, bool)


def test_as_fixtures_existem_e_sao_sinteticas():
    assert len(ARQUIVOS) >= 10
    for nome in ARQUIVOS:
        dado = _ler(nome)
        if dado in ({}, []) or isinstance(dado, list):  # "sem dado" e as listas da FC de repouso nao tem onde levar a marca
            continue
        assert dado["_sintetico"].startswith("SINTETICO"), nome


def test_nenhuma_data_fora_do_periodo_inventado():
    texto = "".join((PASTA / n).read_text() for n in ARQUIVOS)
    import re

    datas = set(re.findall(r"\d{4}-\d{2}-\d{2}", texto))
    assert datas and all(d.startswith("2026-03-") for d in datas)


@pytest.mark.parametrize("nome", SONO_COM_NOITE)
def test_sono_get_sleep_data_formato(nome):
    r = _ler(nome)
    s = r["dailySleepDTO"]
    # data da noite: texto AAAA-MM-DD, a data local de ACORDAR
    cal = dt.date.fromisoformat(s["calendarDate"])
    # instantes: inteiros em milissegundos; *Local = hora de parede lida como UTC; *GMT = instante real
    for k in ("sleepStartTimestampGMT", "sleepEndTimestampGMT", "sleepStartTimestampLocal", "sleepEndTimestampLocal"):
        assert _inteiro(s[k]) and s[k] > 10**12, k
    assert _dia(s["sleepEndTimestampLocal"]) == cal
    assert _dia(s["sleepStartTimestampLocal"]) < cal  # deitou na vespera
    desloc = s["sleepStartTimestampLocal"] - s["sleepStartTimestampGMT"]
    assert desloc == s["sleepEndTimestampLocal"] - s["sleepEndTimestampGMT"]
    assert desloc % 3_600_000 == 0 and abs(desloc) <= 14 * 3_600_000
    # duracoes: inteiros em segundos
    for k in ("sleepTimeSeconds", "napTimeSeconds", "deepSleepSeconds", "lightSleepSeconds", "remSleepSeconds",
              "awakeSleepSeconds", "unmeasurableSleepSeconds"):
        assert _inteiro(s[k]) and s[k] >= 0, k
    # sleepTimeSeconds e o tempo DORMINDO (sem os despertares); a janela inclui os despertares
    assert s["sleepTimeSeconds"] == s["deepSleepSeconds"] + s["lightSleepSeconds"] + s["remSleepSeconds"]
    janela = (s["sleepEndTimestampGMT"] - s["sleepStartTimestampGMT"]) // 1000
    assert janela == s["sleepTimeSeconds"] + s["awakeSleepSeconds"] + s["unmeasurableSleepSeconds"]
    assert 0 < s["sleepTimeSeconds"] <= 86400
    # FC de repouso: inteiro no topo (nao dentro do dailySleepDTO)
    assert _inteiro(r["restingHeartRate"]) and 20 <= r["restingHeartRate"] <= 150
    assert "restingHeartRate" not in s


def test_sono_vfc_no_topo_da_resposta():
    r = _ler("sono_noite_completa.json")
    assert isinstance(r["avgOvernightHrv"], float) and 0 < r["avgOvernightHrv"] <= 500
    assert isinstance(r["hrvStatus"], str)
    assert r["hrvData"] and all({"value", "startGMT"} <= set(x) for x in r["hrvData"])
    assert "avgSleepHRV" not in r["dailySleepDTO"]  # a biblioteca tipa esse campo, mas a resposta real nao o traz


@pytest.mark.parametrize("nome", ["sono_noite_sem_vfc.json", "sono_noite_sem_vfc_none.json"])
def test_sono_sem_vfc_ausente_ou_none(nome):
    r = _ler(nome)
    assert r.get("avgOvernightHrv") is None  # ausente e None valem o mesmo
    assert not r.get("hrvData")
    assert r["dailySleepDTO"]["sleepTimeSeconds"] > 0 and r["restingHeartRate"] > 0  # as outras medidas seguem


def test_sono_dia_sem_dado_e_vazio():
    assert _ler("sono_dia_sem_dado.json") == {}  # HTTP 204 na biblioteca vira {}


def test_sono_dto_sem_duracao():
    r = _ler("sono_dto_sem_duracao.json")
    assert r["dailySleepDTO"]["sleepTimeSeconds"] is None
    assert _inteiro(r["restingHeartRate"])  # a FC de repouso e independente do sono


def test_sesta_nao_entra_no_sono_da_noite():
    s = _ler("sono_noite_com_sesta.json")["dailySleepDTO"]
    assert s["napTimeSeconds"] > 0
    assert s["sleepTimeSeconds"] == s["deepSleepSeconds"] + s["lightSleepSeconds"] + s["remSleepSeconds"]


def test_marcador_so_no_arquivo_do_marcador():
    for nome in ARQUIVOS:
        texto = (PASTA / nome).read_text()
        assert (MARCADOR in texto) == (nome == "sono_noite_com_marcador.json"), nome
    r = _ler("sono_noite_com_marcador.json")
    assert r["campoDesconhecido"] == MARCADOR  # campo que o leitor nao conhece e nunca deve repetir


@pytest.mark.parametrize("nome", ["vfc_faixa.json", "vfc_faixa_com_buraco.json"])
def test_vfc_faixa_formato(nome):
    r = _ler(nome)
    assert isinstance(r["hrvSummaries"], list) and r["hrvSummaries"]
    datas = [x["calendarDate"] for x in r["hrvSummaries"]]
    assert datas == sorted(set(datas))
    for x in r["hrvSummaries"]:
        dt.date.fromisoformat(x["calendarDate"])
        assert _inteiro(x["lastNightAvg"]) and 0 < x["lastNightAvg"] <= 500  # ms, inteiro
        assert x["weeklyAvg"] is None or _inteiro(x["weeklyAvg"])
        assert isinstance(x["status"], str)
        assert set(x["baseline"]) == {"lowUpper", "balancedLow", "balancedUpper", "markerValue"}


def test_vfc_faixa_com_buraco_pula_o_dia():
    datas = [x["calendarDate"] for x in _ler("vfc_faixa_com_buraco.json")["hrvSummaries"]]
    assert "2026-03-11" not in datas and len(datas) == 2


def test_vfc_faixa_sem_dado_e_vazia():
    assert _ler("vfc_faixa_sem_dado.json") == {}


def test_rhr_faixa_formato():
    linhas = _ler("rhr_faixa.json")
    assert [set(x) for x in linhas] == [{"calendarDate", "value"}] * len(linhas)
    for x in linhas:
        dt.date.fromisoformat(x["calendarDate"])
        assert isinstance(x["value"], float) and 20 <= x["value"] <= 150  # a faixa devolve float; o dia, inteiro
    assert "2026-03-12" not in [x["calendarDate"] for x in linhas]  # dia sem valor: a linha nao existe
    assert _ler("rhr_faixa_sem_dado.json") == []


def test_biblioteca_versao_e_erro_de_limite():
    """Fixa o que a nota diz do erro de limite: na versao fixada, o 429 das rotas de dados NAO e `TooManyRequests`."""
    from importlib.metadata import version

    from garminconnect import exceptions as ex

    assert version("garminconnect") == "0.3.20"
    assert not issubclass(ex.GarminConnectTooManyRequestsError, ex.GarminConnectConnectionError)
    assert issubclass(ex.GarminConnectNotFoundError, ex.GarminConnectConnectionError)
