"""Cliente Open-Meteo (Meta 4, issue #112; ADR 0007 itens 4 e 6).

Tudo com transporte falso (httpx.MockTransport) e espera falsa: nenhum teste abre conexao nem dorme.
Dados inventados (Parque do Exemplo); as respostas gravadas ficam em tests/fixtures/clima/.
"""

import json
import logging
import socket
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
import pytest

from app.clima import USER_AGENT, ClienteClima, ClienteOpenMeteo, ResultadoClima

FIXTURES = Path(__file__).resolve().parents[4] / "tests" / "fixtures" / "clima"
ORACULO = json.loads((FIXTURES / "oraculo_clima.json").read_text())
RESPOSTAS = {k: json.loads((FIXTURES / v).read_text()) for k, v in ORACULO["respostas"].items()}
CASOS_COM_CLIMA = [c for c in ORACULO["casos"] if c["clima"] is not None]
LAT, LON = 12.35, -45.68
PARAMS_ESPERADOS = {
    "latitude", "longitude", "start_date", "end_date", "hourly", "wind_speed_unit", "timezone",
}


def utc(texto: str) -> datetime:
    return datetime.fromisoformat(texto.replace("Z", "+00:00"))


@pytest.fixture(autouse=True)
def sem_rede(monkeypatch):
    """Falha (AssertionError, que o httpx nao engole) se qualquer coisa tentar abrir conexao."""

    def bloqueado(*a, **k):
        raise AssertionError("teste tentou abrir conexao de rede")

    monkeypatch.setattr(socket.socket, "connect", bloqueado)
    monkeypatch.setattr(socket, "create_connection", bloqueado)
    monkeypatch.setattr(socket, "getaddrinfo", bloqueado)


class Esperas:
    """Relogio falso: guarda as esperas pedidas em vez de dormir."""

    def __init__(self):
        self.valores: list[float] = []

    def __call__(self, s: float) -> None:
        self.valores.append(s)


class Servidor:
    """Transporte falso: responde na ordem da lista (a ultima se repete); guarda as requisicoes."""

    def __init__(self, *respostas):
        self.respostas = list(respostas)
        self.requisicoes: list[httpx.Request] = []

    def __call__(self, req: httpx.Request) -> httpx.Response:
        self.requisicoes.append(req)
        i = min(len(self.requisicoes), len(self.respostas)) - 1
        r = self.respostas[i]
        if isinstance(r, Exception):
            raise r
        return r


def ok(corpo: dict) -> httpx.Response:
    return httpx.Response(200, json=corpo)


def montar(*respostas):
    srv = Servidor(*respostas)
    esperas = Esperas()
    return ClienteOpenMeteo(transporte=httpx.MockTransport(srv), dormir=esperas), srv, esperas


def resposta_dias(dias: list[str], valor) -> dict:
    """Resposta sintetica com todas as horas dos dias dados; ``valor(variavel, indice)`` gera cada numero."""
    horas = [f"{d}T{h:02d}:00" for d in dias for h in range(24)]
    variaveis = ("temperature_2m", "apparent_temperature", "relative_humidity_2m", "wind_speed_10m")
    return {
        "hourly": {"time": horas, **{v: [valor(v, i) for i in range(len(horas))] for v in variaveis}}
    }


# --------------------------------------------------------------------------
# valores: tem de bater com o oraculo do Caio
# --------------------------------------------------------------------------
def test_cliente_cumpre_a_interface():
    cliente: ClienteClima = ClienteOpenMeteo(transporte=httpx.MockTransport(Servidor(ok({}))))
    assert hasattr(cliente, "buscar")


@pytest.mark.parametrize("caso", CASOS_COM_CLIMA, ids=lambda c: c["id"])
def test_resposta_gravada_bate_com_o_oraculo(caso):
    cliente, srv, esperas = montar(ok(RESPOSTAS["normal"]))
    r = cliente.buscar(LAT, LON, utc(caso["inicio_utc"]), caso["duracao_s"])
    assert r.estado == "ok" == caso["estado"]
    tol = ORACULO["tolerancia_abs"]
    for campo, esperado in caso["clima"].items():
        assert getattr(r.clima, campo) == pytest.approx(esperado, abs=max(tol, 1e-9))
    assert len(srv.requisicoes) == 1
    assert esperas.valores == []


@pytest.mark.parametrize("caso", CASOS_COM_CLIMA, ids=lambda c: c["id"])
def test_resposta_com_null_segue_o_oraculo(caso):
    cliente, _, _ = montar(ok(RESPOSTAS["com_null"]))
    r = cliente.buscar(LAT, LON, utc(caso["inicio_utc"]), caso["duracao_s"])
    assert r.estado == caso["estado_com_resposta_null"]
    if r.estado == "pendente":
        assert r.clima is None
        assert r.erro == "resposta com null na janela"
        assert not r.parar_rodada


def test_cruza_a_meia_noite_utc_usa_duas_datas():
    # 23:40 a 00:20 do dia seguinte: 20 min na hora 23h do dia 10 e 20 min na 00h do dia 11 (pesos 1/2 e 1/2).
    def valor(v, i):  # i: 0..47; hora 23 do dia 10 e 0 do dia 11 sao os indices 23 e 24
        return {23: 20.0, 24: 30.0}.get(i, 99.0) + (0 if v != "wind_speed_10m" else 1)

    cliente, srv, _ = montar(ok(resposta_dias(["2026-05-10", "2026-05-11"], valor)))
    r = cliente.buscar(LAT, LON, utc("2026-05-10T23:40:00Z"), 2400)
    params = dict(srv.requisicoes[0].url.params)
    assert params["start_date"] == "2026-05-10"
    assert params["end_date"] == "2026-05-11"
    assert r.estado == "ok"
    assert r.clima.temperatura_c == pytest.approx(25.0)
    assert r.clima.vento_kmh == pytest.approx(26.0)


def test_cruza_a_meia_noite_com_pesos_desiguais():
    # 23:50 a 00:20: 10 min (1/4) na hora 23h e 20 min (3/4)... 30 min no total: 1/3 e 2/3.
    cliente, _, _ = montar(ok(resposta_dias(["2026-05-10", "2026-05-11"], lambda v, i: {23: 10.0, 24: 40.0}.get(i, 0.0))))
    r = cliente.buscar(LAT, LON, utc("2026-05-10T23:50:00Z"), 1800)
    assert r.clima.temperatura_c == pytest.approx(10 / 3 + 80 / 3)


def test_duracao_zero_usa_a_hora_do_inicio():
    cliente, srv, _ = montar(ok(resposta_dias(["2026-05-10"], lambda v, i: float(i))))
    r = cliente.buscar(LAT, LON, utc("2026-05-10T09:59:59Z"), 0)
    assert r.estado == "ok"
    assert r.clima.temperatura_c == 9.0
    params = dict(srv.requisicoes[0].url.params)
    assert params["start_date"] == params["end_date"] == "2026-05-10"


def test_duracao_ausente_ou_negativa_tambem_usa_a_hora_do_inicio():
    for duracao in (None, -5):
        cliente, _, _ = montar(ok(resposta_dias(["2026-05-10"], lambda v, i: float(i))))
        r = cliente.buscar(LAT, LON, utc("2026-05-10T09:30:00Z"), duracao)
        assert r.clima.temperatura_c == 9.0


def test_termina_na_hora_cheia_nao_conta_a_hora_seguinte():
    cliente, srv, _ = montar(ok(resposta_dias(["2026-05-10"], lambda v, i: float(i))))
    r = cliente.buscar(LAT, LON, utc("2026-05-10T09:00:00Z"), 3600)
    assert r.clima.temperatura_c == 9.0
    # Atividade que termina 00:00 em ponto: a data final vira o dia seguinte, mas a hora 00h do dia 11 pesa zero.
    cliente, srv, _ = montar(ok(resposta_dias(["2026-05-10", "2026-05-11"], lambda v, i: float(i))))
    r = cliente.buscar(LAT, LON, utc("2026-05-10T23:00:00Z"), 3600)
    assert r.clima.temperatura_c == 23.0
    assert dict(srv.requisicoes[0].url.params)["end_date"] == "2026-05-11"


def test_inicio_em_outro_fuso_e_convertido_para_utc():
    inicio = datetime(2026, 5, 10, 6, 20, tzinfo=timezone(timedelta(hours=-3)))  # 09:20 UTC
    cliente, _, _ = montar(ok(RESPOSTAS["normal"]))
    r = cliente.buscar(LAT, LON, inicio, 3000)
    assert r.clima.temperatura_c == pytest.approx(27.02)


def test_inicio_sem_fuso_e_recusado():
    cliente, _, _ = montar(ok(RESPOSTAS["normal"]))
    with pytest.raises(ValueError):
        cliente.buscar(LAT, LON, datetime(2026, 5, 10, 9, 20), 3000)


# --------------------------------------------------------------------------
# a chamada
# --------------------------------------------------------------------------
def test_url_so_leva_os_parametros_combinados():
    cliente, srv, _ = montar(ok(RESPOSTAS["normal"]))
    cliente.buscar(12.3456, -45.6789, utc("2026-05-10T09:20:00Z"), 3000)  # defesa: formata com 2 casas
    req = srv.requisicoes[0]
    assert req.method == "GET"
    assert (req.url.scheme, req.url.host, req.url.path) == ("https", "archive-api.open-meteo.com", "/v1/archive")
    assert dict(req.url.params) == {
        "latitude": "12.35",
        "longitude": "-45.68",
        "start_date": "2026-05-10",
        "end_date": "2026-05-10",
        "hourly": "temperature_2m,apparent_temperature,relative_humidity_2m,wind_speed_10m",
        "wind_speed_unit": "kmh",
        "timezone": "GMT",
    }
    assert set(req.url.params.keys()) == PARAMS_ESPERADOS
    assert req.url.fragment == "" and req.url.userinfo == b""


def test_cabecalhos_sem_identificacao_do_atleta():
    cliente, srv, _ = montar(ok(RESPOSTAS["normal"]))
    cliente.buscar(LAT, LON, utc("2026-05-10T09:20:00Z"), 3000)
    cab = srv.requisicoes[0].headers
    assert cab["user-agent"] == USER_AGENT
    for proibido in ("authorization", "cookie", "x-api-key", "referer", "from"):
        assert proibido not in cab
    assert not srv.requisicoes[0].content


def test_timeout_de_10_segundos():
    cliente, _, _ = montar(ok(RESPOSTAS["normal"]))
    t = cliente._http.timeout
    assert (t.connect, t.read, t.write, t.pool) == (10.0, 10.0, 10.0, 10.0)


def test_guarda_de_rede_funciona():
    """O cliente com transporte padrao tentaria abrir conexao: a guarda do teste tem de pegar."""
    with pytest.raises(AssertionError, match="conexao de rede"):
        ClienteOpenMeteo().buscar(LAT, LON, utc("2026-05-10T09:20:00Z"), 3000)


# --------------------------------------------------------------------------
# erros e tentativas
# --------------------------------------------------------------------------
def test_5xx_tenta_de_novo_e_recupera():
    cliente, srv, esperas = montar(httpx.Response(503), httpx.Response(500), ok(RESPOSTAS["normal"]))
    r = cliente.buscar(LAT, LON, utc("2026-05-10T09:20:00Z"), 3000)
    assert r.estado == "ok"
    assert len(srv.requisicoes) == 3
    assert esperas.valores == [1.0, 2.0]


def test_5xx_persistente_vira_pendente_depois_de_tres_esperas():
    cliente, srv, esperas = montar(httpx.Response(502, text="corpo secreto"))
    r = cliente.buscar(LAT, LON, utc("2026-05-10T09:20:00Z"), 3000)
    assert r == ResultadoClima("pendente", erro="HTTP 502")
    assert not r.parar_rodada
    assert len(srv.requisicoes) == 4  # 1 chamada + 3 repeticoes
    assert esperas.valores == [1.0, 2.0, 4.0]


def test_erro_de_rede_tenta_de_novo_e_vira_pendente():
    cliente, srv, esperas = montar(httpx.ConnectError("sem rota para 12.35,-45.68"))
    r = cliente.buscar(LAT, LON, utc("2026-05-10T09:20:00Z"), 3000)
    assert r.estado == "pendente"
    assert r.erro == "erro de rede (ConnectError)"
    assert "12.35" not in r.erro
    assert len(srv.requisicoes) == 4
    assert esperas.valores == [1.0, 2.0, 4.0]


def test_timeout_tenta_de_novo_e_vira_pendente():
    cliente, srv, esperas = montar(httpx.ReadTimeout("lento"))
    r = cliente.buscar(LAT, LON, utc("2026-05-10T09:20:00Z"), 3000)
    assert r == ResultadoClima("pendente", erro="tempo esgotado")
    assert len(srv.requisicoes) == 4
    assert esperas.valores == [1.0, 2.0, 4.0]


def test_rede_cai_e_volta():
    cliente, _, esperas = montar(httpx.ConnectTimeout("x"), ok(RESPOSTAS["normal"]))
    assert cliente.buscar(LAT, LON, utc("2026-05-10T09:20:00Z"), 3000).estado == "ok"
    assert esperas.valores == [1.0]


def test_429_respeita_retry_after():
    cliente, _, esperas = montar(
        httpx.Response(429, headers={"Retry-After": "7"}), ok(RESPOSTAS["normal"])
    )
    assert cliente.buscar(LAT, LON, utc("2026-05-10T09:20:00Z"), 3000).estado == "ok"
    assert esperas.valores == [7.0]


def test_retry_after_e_limitado_a_60_segundos():
    cliente, _, esperas = montar(
        httpx.Response(429, headers={"Retry-After": "3600"}), ok(RESPOSTAS["normal"])
    )
    cliente.buscar(LAT, LON, utc("2026-05-10T09:20:00Z"), 3000)
    assert esperas.valores == [60.0]


@pytest.mark.parametrize("valor", ["amanha", "-3", "nan", "Wed, 21 Oct 2026 07:28:00 GMT"])
def test_retry_after_invalido_usa_a_espera_padrao(valor):
    cliente, _, esperas = montar(
        httpx.Response(503, headers={"Retry-After": valor}), ok(RESPOSTAS["normal"])
    )
    cliente.buscar(LAT, LON, utc("2026-05-10T09:20:00Z"), 3000)
    assert esperas.valores == [1.0]


def test_429_persistente_vira_pendente_e_pede_para_parar_a_rodada():
    cliente, srv, esperas = montar(httpx.Response(429))
    r = cliente.buscar(LAT, LON, utc("2026-05-10T09:20:00Z"), 3000)
    assert r == ResultadoClima("pendente", erro="HTTP 429", parar_rodada=True)
    assert len(srv.requisicoes) == 4
    assert esperas.valores == [1.0, 2.0, 4.0]


def test_ultima_tentativa_nao_dorme_com_retry_after():
    cliente, _, esperas = montar(httpx.Response(429, headers={"Retry-After": "5"}))
    cliente.buscar(LAT, LON, utc("2026-05-10T09:20:00Z"), 3000)
    assert esperas.valores == [5.0, 5.0, 5.0]


def test_400_vira_falha_sem_nova_tentativa():
    cliente, srv, esperas = montar(httpx.Response(400, json={"error": True, "reason": "Latitude: 12.35"}))
    r = cliente.buscar(LAT, LON, utc("2026-05-10T09:20:00Z"), 3000)
    assert r == ResultadoClima("falha", erro="HTTP 400")
    assert len(srv.requisicoes) == 1
    assert esperas.valores == []


def test_404_tambem_vira_falha_sem_nova_tentativa():
    cliente, srv, _ = montar(httpx.Response(404))
    assert cliente.buscar(LAT, LON, utc("2026-05-10T09:20:00Z"), 3000).estado == "falha"
    assert len(srv.requisicoes) == 1


def _sem(variavel: str) -> dict:
    corpo = json.loads(json.dumps(RESPOSTAS["normal"]))
    del corpo["hourly"][variavel]
    return corpo


def _tamanho_errado() -> dict:
    corpo = json.loads(json.dumps(RESPOSTAS["normal"]))
    corpo["hourly"]["wind_speed_10m"].pop()
    return corpo


def _valor_texto() -> dict:
    corpo = json.loads(json.dumps(RESPOSTAS["normal"]))
    corpo["hourly"]["temperature_2m"][9] = "quente"
    return corpo


def _outro_dia() -> dict:
    return resposta_dias(["2026-05-11"], lambda v, i: 1.0)


@pytest.mark.parametrize(
    "resposta",
    [
        ok(_sem("apparent_temperature")),
        ok(_tamanho_errado()),
        ok(_valor_texto()),
        ok(_outro_dia()),
        ok({"hourly": {}}),
        ok({}),
        ok([1, 2]),
        httpx.Response(200, text="<html>nao e json</html>"),
    ],
    ids=["variavel-faltando", "tamanho", "valor-texto", "hora-fora", "hourly-vazio", "sem-hourly", "lista", "nao-json"],
)
def test_resposta_inconsistente_vira_falha_sem_nova_tentativa(resposta):
    cliente, srv, esperas = montar(resposta)
    r = cliente.buscar(LAT, LON, utc("2026-05-10T09:20:00Z"), 3000)
    assert r.estado == "falha"
    assert r.clima is None
    assert len(srv.requisicoes) == 1
    assert esperas.valores == []


def test_null_fora_da_janela_nao_atrapalha():
    corpo = json.loads(json.dumps(RESPOSTAS["normal"]))
    corpo["hourly"]["temperature_2m"][3] = None
    cliente, _, _ = montar(ok(corpo))
    assert cliente.buscar(LAT, LON, utc("2026-05-10T09:20:00Z"), 3000).estado == "ok"


def test_null_em_qualquer_variavel_da_janela_vira_pendente():
    corpo = json.loads(json.dumps(RESPOSTAS["normal"]))
    corpo["hourly"]["wind_speed_10m"][10] = None  # hora 10h, pesa 1/5
    cliente, _, _ = montar(ok(corpo))
    r = cliente.buscar(LAT, LON, utc("2026-05-10T09:20:00Z"), 3000)
    assert r.estado == "pendente" and r.clima is None


# --------------------------------------------------------------------------
# log: nunca coordenada, URL completa nem corpo
# --------------------------------------------------------------------------
@pytest.mark.parametrize(
    "respostas",
    [
        [ok(RESPOSTAS["normal"])],
        [httpx.Response(503, text="CORPO-SECRETO-503")],
        [httpx.Response(429, text="CORPO-SECRETO-429")],
        [httpx.Response(400, text="CORPO-SECRETO-400")],
        [httpx.ConnectError("falha em archive-api.open-meteo.com 12.35")],
        [ok(_sem("wind_speed_10m"))],
    ],
    ids=["ok", "5xx", "429", "400", "rede", "inconsistente"],
)
def test_log_sem_coordenada_url_nem_corpo(caplog, respostas):
    caplog.set_level(logging.DEBUG)
    cliente, _, _ = montar(*respostas)
    cliente.buscar(LAT, LON, utc("2026-05-10T09:20:00Z"), 3000)
    texto = "\n".join(r.getMessage() for r in caplog.records)
    for proibido in ("12.35", "45.68", "latitude", "longitude", "archive-api", "https://", "CORPO-SECRETO", "temperature_2m"):
        assert proibido not in texto
