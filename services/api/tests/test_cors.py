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


def test_so_get_e_post_no_preflight():
    app = criar_app(APP_WEB)

    def preflight(metodo):
        return TestClient(app).options(
            "/health", headers={"Origin": APP_WEB, "Access-Control-Request-Method": metodo}
        )

    ok, post, ruim = preflight("GET"), preflight("POST"), preflight("DELETE")
    assert ok.status_code == 200 and ok.headers["access-control-allow-methods"] == "GET, POST"
    assert post.status_code == 200
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
