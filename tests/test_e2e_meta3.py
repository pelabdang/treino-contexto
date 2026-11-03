"""QA de ponta a ponta da Meta 3 com os FIT sinteticos (issue #98, ADR 0006).

Migracoes (alembic) -> importacao da exportacao minima (CLI) -> upload de FIT pela API (TestClient, `FIT_DIR` em
tmp_path) -> serie de tiros. Num SQLite temporario; so dado sintetico. Os testes seguem a ordem do arquivo e dividem
o mesmo banco (como o e2e da Meta 2), entao a ordem importa.
"""

import hashlib
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

RAIZ = Path(__file__).resolve().parents[1]
ZIP = RAIZ / "tests" / "fixtures" / "garmin" / "exportacao_minima.zip"
FITS = RAIZ / "tests" / "fixtures" / "garmin" / "fit"
LIMITE = 10 * 1024 * 1024


def _roda(args, env, cwd):
    r = subprocess.run([sys.executable, *args], env=env, cwd=cwd, capture_output=True, text=True)
    assert r.returncode == 0, f"{args}\nstdout: {r.stdout}\nstderr: {r.stderr}"
    return r.stdout


def _fit(nome):
    return (FITS / nome).read_bytes()


@pytest.fixture(scope="module")
def ctx(tmp_path_factory):
    from app.db.models import Atleta
    from app.db.session import get_session
    from app.main import app
    from app.rotas.atividades import get_fit_dir

    base = tmp_path_factory.mktemp("e2e_meta3")
    url = f"sqlite:///{base / 'treino.db'}"
    fit_dir = base / "fit"
    env = {**os.environ, "DATABASE_URL": url}
    _roda(["-m", "alembic", "upgrade", "head"], env, RAIZ / "services" / "api")
    saida = _roda(["-m", "worker.importar_garmin", str(ZIP), "--atleta", "Atleta Ficticio"], env, RAIZ)
    assert "inseridas=5 atualizadas=0 ignoradas=0" in saida
    eng = create_engine(url)
    with Session(eng) as s:
        atleta_id = s.scalars(select(Atleta)).one().id

    def sessao():
        with Session(eng) as s:
            yield s

    app.dependency_overrides[get_session] = sessao
    app.dependency_overrides[get_fit_dir] = lambda: fit_dir
    try:
        yield {"client": TestClient(app), "atleta_id": atleta_id, "fit_dir": fit_dir, "eng": eng}
    finally:
        app.dependency_overrides.clear()
        eng.dispose()


def _enviar(ctx, conteudo, nome="treino.fit", atleta_id=None):
    return ctx["client"].post(
        f"/atletas/{atleta_id or ctx['atleta_id']}/atividades/fit",
        files={"arquivo": (nome, conteudo, "application/octet-stream")},
    )


def _serie(ctx):
    r = ctx["client"].get(f"/atletas/{ctx['atleta_id']}/evolucao/tiros-1km")
    assert r.status_code == 200
    return r.json()


def _n_atividades(ctx):
    from app.db.models import Atividade

    with Session(ctx["eng"]) as s:
        return s.scalar(select(func.count()).select_from(Atividade))


def _guardados(ctx):
    return sorted(p for p in ctx["fit_dir"].rglob("*") if p.is_file())


def test_1_serie_inicial_tem_duas_sessoes(ctx):
    assert [s["data"] for s in _serie(ctx)["sessoes"]] == ["2025-03-04", "2025-03-11"]
    assert _n_atividades(ctx) == 5


def test_2_upload_de_tiros_entra_como_ponto_novo(ctx):
    conteudo = _fit("upload_intervalado_5x1km.fit")
    r = _enviar(ctx, conteudo)
    assert r.status_code == 201
    j = r.json()
    assert j["resultado"] == "inserida" and j["avisos"] == []
    sessoes = _serie(ctx)["sessoes"]
    assert [s["data"] for s in sessoes] == ["2025-03-04", "2025-03-11", "2025-04-01"]
    assert sessoes[-1]["pace_medio"] == "4:06"  # 246,0 s/km (conta na #93)
    assert _n_atividades(ctx) == 6


def test_3_nome_guardado_e_atleta_id_sha256(ctx):
    conteudo = _fit("upload_intervalado_5x1km.fit")
    esperado = f"{ctx['atleta_id']}/{hashlib.sha256(conteudo).hexdigest()}.fit"
    guardados = _guardados(ctx)
    assert [str(p.relative_to(ctx["fit_dir"])) for p in guardados] == [esperado]
    assert re.fullmatch(r"\d+/[0-9a-f]{64}\.fit", esperado)
    assert "intervalado" not in esperado and "upload" not in esperado  # nome enviado nunca entra
    assert guardados[0].read_bytes() == conteudo


def test_4_reenvio_nao_duplica(ctx):
    antes = _serie(ctx)
    r = _enviar(ctx, _fit("upload_intervalado_5x1km.fit"), nome="outro-nome.fit")
    assert r.status_code == 200 and r.json()["resultado"] == "ignorada"
    assert _n_atividades(ctx) == 6 and len(_guardados(ctx)) == 1
    assert _serie(ctx) == antes


def test_5_mesma_atividade_da_exportacao_nao_duplica(ctx):
    antes = _serie(ctx)
    r = _enviar(ctx, _fit("upload_mesma_atividade_1000000001.fit"))
    assert r.status_code == 200 and r.json()["resultado"] == "atualizada"
    assert _n_atividades(ctx) == 6
    assert len(_serie(ctx)["sessoes"]) == len(antes["sessoes"])


def test_6_truncado_e_nao_atividade_dao_400_sem_gravar(ctx):
    n, guardados = _n_atividades(ctx), _guardados(ctx)
    r = _enviar(ctx, _fit("upload_truncado.fit"))
    assert r.status_code == 400 and r.json() == {"detail": "FIT inválido ou corrompido"}
    r = _enviar(ctx, _fit("upload_nao_atividade.fit"))
    assert r.status_code == 400 and r.json() == {"detail": "o arquivo é um FIT, mas não é uma atividade"}
    assert _n_atividades(ctx) == n and _guardados(ctx) == guardados


def test_7_acima_de_10_mb_da_413_sem_gravar(ctx):
    n, guardados = _n_atividades(ctx), _guardados(ctx)
    r = _enviar(ctx, b"\0" * (LIMITE + 1), nome="grande.fit")
    assert r.status_code == 413 and r.json() == {"detail": "arquivo acima de 10 MB"}
    assert _n_atividades(ctx) == n and _guardados(ctx) == guardados


def test_8_extensao_errada_e_atleta_inexistente(ctx):
    r = _enviar(ctx, _fit("upload_rodagem_6km.fit"), nome="treino.txt")
    assert r.status_code == 400 and r.json() == {"detail": "o arquivo precisa ter extensão .fit"}
    r = _enviar(ctx, _fit("upload_rodagem_6km.fit"), atleta_id=99)
    assert r.status_code == 404 and r.json() == {"detail": "atleta não encontrado"}


def test_9_rodagem_entra_no_banco_mas_fica_fora_da_serie(ctx):
    antes = _serie(ctx)["sessoes"]
    assert _enviar(ctx, _fit("upload_rodagem_6km.fit")).status_code == 201
    assert _serie(ctx)["sessoes"] == antes


def test_10_dados_upload_esta_no_gitignore():
    linhas = (RAIZ / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert "dados-upload/" in linhas
    r = subprocess.run(
        ["git", "check-ignore", "dados-upload/fit/1/x.fit"], cwd=RAIZ, capture_output=True, text=True
    )
    assert r.returncode == 0, "dados-upload/ nao esta ignorado pelo git"
