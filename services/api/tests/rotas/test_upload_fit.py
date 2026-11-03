"""POST /atletas/{id}/atividades/fit (issue #95, ADR 0006). FIT sinteticos da #93; `FIT_DIR` sempre em `tmp_path`."""

from pathlib import Path

import pytest
from app.db.models import Atividade, Atleta
from app.db.session import get_session
from app.main import criar_app
from app.rotas.atividades import get_fit_dir
from app.ingestao.importacao import TAMANHO_MAX_FIT
from fastapi.testclient import TestClient
from sqlalchemy import func, select

RAIZ = Path(__file__).resolve().parents[4]
FITS = RAIZ / "tests" / "fixtures" / "garmin" / "fit"
URL = "/atletas/{}/atividades/fit"


@pytest.fixture
def pasta(tmp_path):
    return tmp_path / "fit"


@pytest.fixture
def atleta(session):
    a = Atleta(nome="Atleta Ficticio")
    session.add(a)
    session.commit()
    return a


@pytest.fixture
def client(session, pasta):
    app = criar_app("http://localhost:8081")
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[get_fit_dir] = lambda: pasta
    return TestClient(app)


def _enviar(client, atleta_id, conteudo, nome="treino.fit"):
    return client.post(URL.format(atleta_id), files={"arquivo": (nome, conteudo, "application/octet-stream")})


def _fit(nome):
    return (FITS / nome).read_bytes()


def _n(session):
    return session.scalar(select(func.count()).select_from(Atividade))


def test_201_atividade_inserida(client, atleta, session, pasta):
    r = _enviar(client, atleta.id, _fit("upload_intervalado_5x1km.fit"))
    assert r.status_code == 201
    j = r.json()
    assert j["resultado"] == "inserida" and j["avisos"] == []
    assert session.get(Atividade, j["atividade_id"]).fonte == "fit_upload"
    assert len(list(pasta.rglob("*.fit"))) == 1


def test_200_reenvio_ignorada(client, atleta, session):
    conteudo = _fit("upload_rodagem_6km.fit")
    primeiro = _enviar(client, atleta.id, conteudo).json()
    r = _enviar(client, atleta.id, conteudo)
    assert r.status_code == 200
    assert r.json() == {"resultado": "ignorada", "atividade_id": primeiro["atividade_id"], "avisos": []}
    assert _n(session) == 1


def test_200_fit_diferente_que_casa_atualiza(client, atleta, session, pasta):
    """B comeca 40 s depois de A (regra dos 60 s): mesma atividade, `id` igual, arquivo antigo apagado."""
    a = _enviar(client, atleta.id, _fit("empate_candidata_a.fit"))
    b = _enviar(client, atleta.id, _fit("empate_candidata_b.fit"))
    assert a.status_code == 201
    assert b.status_code == 200 and b.json()["resultado"] == "atualizada"
    assert b.json()["atividade_id"] == a.json()["atividade_id"]
    assert _n(session) == 1 and len(list(pasta.rglob("*.fit"))) == 1


def test_400_fit_truncado_nao_grava_nada(client, atleta, session, pasta):
    r = _enviar(client, atleta.id, _fit("upload_truncado.fit"))
    assert r.status_code == 400 and r.json() == {"detail": "FIT inválido ou corrompido"}
    assert _n(session) == 0 and not pasta.exists()


def test_400_conteudo_que_nao_e_fit(client, atleta):
    r = _enviar(client, atleta.id, b"isto nao e um fit")
    assert r.status_code == 400


def test_400_fit_que_nao_e_atividade(client, atleta, session, pasta):
    r = _enviar(client, atleta.id, _fit("upload_nao_atividade.fit"))
    assert r.status_code == 400 and "não é uma atividade" in r.json()["detail"]
    assert _n(session) == 0 and not pasta.exists()


@pytest.mark.parametrize("nome", ["treino.zip", "treino.fit.txt", "fit", ""])
def test_400_extensao_que_nao_e_fit(client, atleta, session, nome):
    r = _enviar(client, atleta.id, _fit("upload_rodagem_6km.fit"), nome=nome or "x")
    assert r.status_code == 400 and ".fit" in r.json()["detail"]
    assert _n(session) == 0


def test_extensao_maiuscula_vale(client, atleta):
    assert _enviar(client, atleta.id, _fit("upload_rodagem_6km.fit"), nome="TREINO.FIT").status_code == 201


def test_404_atleta_inexistente(client, session, pasta):
    r = _enviar(client, 999, _fit("upload_rodagem_6km.fit"))
    assert r.status_code == 404 and r.json() == {"detail": "atleta não encontrado"}
    assert _n(session) == 0 and not pasta.exists()


def test_413_acima_de_10_mb(client, atleta, session, pasta):
    r = _enviar(client, atleta.id, b"\0" * (TAMANHO_MAX_FIT + 1))  # sintetico, gerado aqui
    assert r.status_code == 413 and r.json() == {"detail": "arquivo acima de 10 MB"}
    assert _n(session) == 0 and not pasta.exists()


def test_exatamente_10_mb_passa_do_limite(client, atleta):
    r = _enviar(client, atleta.id, b"\0" * TAMANHO_MAX_FIT)
    assert r.status_code == 400  # passou do limite de tamanho; zeros nao sao FIT


def test_422_sem_arquivo(client, atleta):
    r = client.post(URL.format(atleta.id), files={"outro": ("x.fit", b"x")})
    assert r.status_code == 422
    assert r.json()["detail"][0]["loc"] == ["body", "arquivo"]


def test_422_sem_corpo(client, atleta):
    assert client.post(URL.format(atleta.id)).status_code == 422


def test_openapi_declara_o_upload(client):
    spec = client.get("/openapi.json").json()
    op = spec["paths"]["/atletas/{atleta_id}/atividades/fit"]["post"]
    assert op["operationId"] == "enviarAtividadeFit"
    assert set(op["responses"]) == {"200", "201", "400", "404", "413", "422"}
    for codigo in ("400", "404", "413"):
        assert op["responses"][codigo]["content"]["application/json"]["schema"]["$ref"].endswith("/Erro")
    for codigo in ("200", "201"):
        assert op["responses"][codigo]["content"]["application/json"]["schema"]["$ref"].endswith("/UploadFitOut")
    corpo = op["requestBody"]["content"]["multipart/form-data"]["schema"]["$ref"].rsplit("/", 1)[1]
    assert list(spec["components"]["schemas"][corpo]["properties"]) == ["arquivo"]
    assert spec["components"]["schemas"]["UploadFitOut"]["properties"]["resultado"]["enum"] == [
        "inserida", "atualizada", "ignorada"]
