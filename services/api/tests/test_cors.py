"""CORS configurável por CORS_ORIGENS (issue #65, ADR 0004 item 7)."""

import pytest
from fastapi.testclient import TestClient

from app.config import Settings, lista_origens
from app.main import criar_app

APP_WEB = "http://localhost:8081"


def _get(app, origem=None):
    return TestClient(app).get("/health", headers={"Origin": origem} if origem else {})


def test_origem_da_lista_recebe_allow_origin():
    r = _get(criar_app(APP_WEB), APP_WEB)
    assert r.status_code == 200
    assert r.headers["access-control-allow-origin"] == APP_WEB
    assert "access-control-allow-credentials" not in r.headers


def test_origem_fora_da_lista_nao_recebe():
    r = _get(criar_app(APP_WEB), "http://outro.example")
    assert r.status_code == 200 and "access-control-allow-origin" not in r.headers


@pytest.mark.parametrize("valor", ["", "  ", " , ,"])
def test_variavel_vazia_nao_libera_nenhuma_origem(valor):
    assert lista_origens(valor) == []
    r = _get(criar_app(valor), APP_WEB)
    assert "access-control-allow-origin" not in r.headers


def test_varias_origens_com_espacos():
    app = criar_app(f" {APP_WEB} , https://app.example ")
    assert _get(app, "https://app.example").headers["access-control-allow-origin"] == "https://app.example"
    assert _get(app, APP_WEB).headers["access-control-allow-origin"] == APP_WEB


def test_so_metodos_da_api_no_preflight():
    app = criar_app(APP_WEB)

    def preflight(metodo):
        return TestClient(app).options(
            "/health", headers={"Origin": APP_WEB, "Access-Control-Request-Method": metodo}
        )

    ok, post, ruim = preflight("GET"), preflight("POST"), preflight("PATCH")
    assert ok.status_code == 200 and ok.headers["access-control-allow-methods"] == "GET, POST, PUT, DELETE"
    assert post.status_code == 200 and preflight("PUT").status_code == 200 and preflight("DELETE").status_code == 200  # #170
    assert ruim.status_code == 400


def test_asterisco_e_recusado():
    for valor in ("*", f"{APP_WEB},*"):
        with pytest.raises(ValueError, match=r"'\*'"):
            criar_app(valor)


def test_padrao_e_variavel_de_ambiente(monkeypatch):
    monkeypatch.delenv("CORS_ORIGENS", raising=False)
    assert lista_origens(Settings(_env_file=None).cors_origens) == [APP_WEB]
    monkeypatch.setenv("CORS_ORIGENS", f"{APP_WEB},https://app.example")
    assert lista_origens(Settings(_env_file=None).cors_origens) == [APP_WEB, "https://app.example"]
    monkeypatch.setenv("CORS_ORIGENS", "")
    assert lista_origens(Settings(_env_file=None).cors_origens) == []


# ---------- #527: o preflight do login (Authorization e Content-Type) ----------

def _preflight(app, origem, cabecalhos="authorization, content-type", metodo="POST", caminho="/sessao"):
    return TestClient(app).options(
        caminho, headers={"Origin": origem, "Access-Control-Request-Method": metodo, "Access-Control-Request-Headers": cabecalhos})


def test_preflight_do_login_com_authorization_e_content_type_da_200():
    r = _preflight(criar_app(APP_WEB), APP_WEB)
    assert r.status_code == 200
    assert r.headers["access-control-allow-origin"] == APP_WEB
    permitidos = {h.strip().lower() for h in r.headers["access-control-allow-headers"].split(",")}
    assert {"authorization", "content-type"} <= permitidos
    assert "access-control-allow-credentials" not in r.headers  # o acesso vai em cabecalho, nunca em cookie


def test_preflight_de_rota_de_dado_com_authorization_tambem_da_200():
    r = _preflight(criar_app(APP_WEB), APP_WEB, metodo="PUT", caminho="/atletas/1/semana-padrao")
    assert r.status_code == 200 and "authorization" in r.headers["access-control-allow-headers"].lower()


def test_preflight_de_origem_fora_da_lista_nao_recebe_allow_origin():
    r = _preflight(criar_app(APP_WEB), "http://outro.example")
    assert "access-control-allow-origin" not in r.headers


def test_preflight_so_libera_os_dois_cabecalhos():
    app = criar_app(APP_WEB)
    assert _preflight(app, APP_WEB, "authorization").status_code == 200
    assert _preflight(app, APP_WEB, "x-qualquer-coisa").status_code == 400  # nada alem dos dois
    permitidos = {h.strip().lower() for h in _preflight(app, APP_WEB).headers["access-control-allow-headers"].split(",")}
    seguros = {"accept", "accept-language", "content-language"}  # o Starlette sempre soma os cabecalhos seguros do navegador
    assert "*" not in permitidos and permitidos == seguros | {"authorization", "content-type"}
