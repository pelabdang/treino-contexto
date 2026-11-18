"""Operacao da API no servidor (issue #504, ADR 0016, itens 4 e 9): `/docs` desligado, log sem dado de saude, 422 sem eco. Dados sinteticos."""

import logging

import pytest
from app.main import criar_app
from fastapi.testclient import TestClient

MARCA = "MARCA-SINTETICA-QUE-NAO-PODE-APARECER"


def test_em_producao_nao_ha_docs_redoc_nem_openapi():
    c = TestClient(criar_app("http://localhost:8081", ambiente="producao"))
    for caminho in ("/docs", "/redoc", "/openapi.json"):
        assert c.get(caminho).status_code == 404, caminho
    assert c.get("/health").json() == {"status": "ok"}


def test_fora_da_producao_a_documentacao_segue_ligada():
    c = TestClient(criar_app("http://localhost:8081"))
    assert c.get("/docs").status_code == 200 and c.get("/openapi.json").status_code == 200


def test_o_openapi_versionado_continua_saindo_do_app_em_producao():
    """O script `exportar_openapi.py` usa `app.openapi()`, que nao depende da rota `/openapi.json`."""
    assert criar_app("http://localhost:8081", ambiente="producao").openapi()["paths"]


def test_a_variavel_ambiente_liga_o_modo_producao(monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "ambiente", "producao")
    assert TestClient(criar_app("http://localhost:8081")).get("/docs").status_code == 404


def test_log_de_acesso_tem_metodo_caminho_status_e_duracao_sem_query_string(caplog):
    caplog.set_level(logging.INFO)
    c = TestClient(criar_app("http://localhost:8081"))
    c.get(f"/health?segredo={MARCA}", headers={"Authorization": f"Bearer {MARCA}"})
    linhas = [r.getMessage() for r in caplog.records if r.name == "app.acesso"]
    assert len(linhas) == 1 and linhas[0].startswith("acesso GET /health 200 ") and linhas[0].endswith("ms")
    assert MARCA not in " ".join(r.getMessage() for r in caplog.records)


def test_erro_nao_tratado_em_producao_loga_so_tipo_e_local_e_responde_500_fixo(caplog):
    caplog.set_level(logging.DEBUG)
    app = criar_app("http://localhost:8081", ambiente="producao")

    @app.get("/quebra")
    def quebra():
        raise ValueError(MARCA)

    r = TestClient(app).get("/quebra?x=" + MARCA)
    assert r.status_code == 500 and r.json() == {"detail": "erro ao processar o pedido"}
    texto = " ".join(x.getMessage() for x in caplog.records)
    assert "tipo=ValueError" in texto and "local=test_operacao.py:" in texto
    assert MARCA not in texto and MARCA not in r.text
    assert any(x.getMessage().startswith("acesso GET /quebra 500") for x in caplog.records)


def test_erro_nao_tratado_fora_da_producao_segue_o_caminho_normal():
    app = criar_app("http://localhost:8081")

    @app.get("/quebra")
    def quebra():
        raise ValueError("x")

    with pytest.raises(ValueError):
        TestClient(app).get("/quebra")


def test_422_nao_repete_o_que_foi_digitado_em_nenhuma_rota():
    c = TestClient(criar_app("http://localhost:8081"))
    r = c.post("/sessao", json={"email": "a@exemplo.com", "senha": MARCA * 40})  # senha maior que o limite
    assert r.status_code == 422 and MARCA not in r.text and '"input"' not in r.text and "ctx" not in r.text
    r = c.post("/sessao", json={"email": MARCA})  # falta a senha
    assert r.status_code == 422 and MARCA not in r.text
    assert set(r.json()["detail"][0]) == {"loc", "msg", "type"}
