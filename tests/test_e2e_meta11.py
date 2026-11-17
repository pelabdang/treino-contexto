"""QA de ponta a ponta da Meta 11, a caixa do dia do professor no piloto local (issue #429, ADR 0015).

Segue o roteiro de `docs/produto/meta-11-como-rodar.md`: migracoes (alembic, ate o head lido do ScriptDirectory) -> o professor e os
oito atletas ficticios de `tests/fixtures/meta11/` pelo comando de verdade (`worker.carregar_professor`) -> cinco treinos sinteticos (o
`carregar_treinos.py` do guia) -> `GET /professores/1/caixa-do-dia` -> `PUT /professores/1/tipos-de-treino` -> a reimportacao do FIT, a
semana-padrao editada e o feedback depois da correcao. Num SQLite temporario (um arquivo copiado por teste, para um teste nao sujar o
outro); a API de verdade (uvicorn) so nos testes de `PROFESSOR_ID`. So dado sintetico; sem rede (guarda de socket, como nos e2e anteriores).

Um teste por item do criterio de pronto da Meta 11 (`docs/produto/roadmap.md`, ADR 0015); o item de cada teste esta no docstring.

O que este arquivo NAO cobre (exige olho humano, rede ou dado real): a tela rodando (conferencia no navegador, guia passos 7 e 8), o
celular de verdade, o leitor de tela, o login (nao existe: o `PROFESSOR_ID` nao e autenticacao) e qualquer aluno real. Nao verificado aqui.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

RAIZ = Path(__file__).resolve().parents[1]
API = RAIZ / "services" / "api"
WORKER = RAIZ / "services" / "worker"
PASTA11 = RAIZ / "tests" / "fixtures" / "meta11"
FIT = RAIZ / "tests" / "fixtures" / "garmin" / "fit" / "upload_rodagem_6km.fit"
for _p in (str(API), str(WORKER)):
    if _p not in sys.path:
        sys.path.insert(0, _p)


def _head_do_alembic() -> str:
    """O head das migracoes lido do alembic: o teste nao quebra a cada migracao nova."""
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    cfg = Config(str(API / "alembic.ini"))
    cfg.set_main_option("script_location", str(API / "alembic"))
    return ScriptDirectory.from_config(cfg).get_current_head()


_HEAD = _head_do_alembic()
OBS = "OBSERVACAO-SINTETICA-NAO-VAZAR"  # a observacao livre do check-in da Ana: so pode aparecer em `detalhe.checkin.observacao`
DIAS = ("segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo")

GUARDA = '''"""Guarda de rede dos subprocessos do e2e: so conexao local."""
import socket

_LOCAIS = ("localhost", "127.0.0.1", "::1")
_connect, _create, _getaddr = socket.socket.connect, socket.create_connection, socket.getaddrinfo


def _host(e):
    return e[0] if isinstance(e, tuple) else e


def _bloqueia():
    raise AssertionError("comando tentou abrir conexao de rede")


def _c(self, e, *a, **k):
    if _host(e) not in _LOCAIS and self.family != socket.AF_UNIX:
        _bloqueia()
    return _connect(self, e, *a, **k)


def _cc(e, *a, **k):
    if _host(e) not in _LOCAIS:
        _bloqueia()
    return _create(e, *a, **k)


def _g(h, *a, **k):
    if h is not None and h not in _LOCAIS:
        _bloqueia()
    return _getaddr(h, *a, **k)


socket.socket.connect, socket.create_connection, socket.getaddrinfo = _c, _cc, _g
'''

# O passo 4 do guia: (atleta, fonte_id, dias atras, modalidade, minutos, tipo sugerido, check-in)
TREINOS = [
    ("Atleta Fixture Ana", "m11-ana-1", 2, "corrida", 45, "leve", {"pse": 6, "sensacao": 3, "dor": True, "texto": OBS}),
    ("Atleta Fixture Bruno", "m11-bru-1", 1, "corrida", 50, "intervalado", {"pse": 7, "sensacao": 4, "dor": False, "texto": None}),
    ("Atleta Fixture Carla", "m11-car-1", 6, "ciclismo", 70, None, None),
    ("Atleta Fixture Carla", "m11-car-2", 3, "corrida", 40, "moderado", {"pse": 5, "sensacao": 4, "dor": False, "texto": None}),
    ("Atleta Fixture Eva Sem Consentimento", "m11-eva-1", 2, "corrida", 45, "leve", {"pse": 6, "sensacao": 3, "dor": True, "texto": OBS}),
]


@pytest.fixture(autouse=True)
def sem_rede(monkeypatch):
    """Derruba qualquer conexao que nao seja local, tambem dentro do processo do teste."""
    locais = ("localhost", "127.0.0.1", "::1")
    connect, create, getaddr = socket.socket.connect, socket.create_connection, socket.getaddrinfo

    def _host(e):
        return e[0] if isinstance(e, tuple) else e

    def bloqueia():
        raise AssertionError("teste tentou abrir conexao de rede")

    def connect_(self, e, *a, **k):
        if _host(e) not in locais and self.family != socket.AF_UNIX:
            bloqueia()
        return connect(self, e, *a, **k)

    def create_(e, *a, **k):
        if _host(e) not in locais:
            bloqueia()
        return create(e, *a, **k)

    def getaddr_(h, *a, **k):
        if h is not None and h not in locais:
            bloqueia()
        return getaddr(h, *a, **k)

    monkeypatch.setattr(socket.socket, "connect", connect_)
    monkeypatch.setattr(socket, "create_connection", create_)
    monkeypatch.setattr(socket, "getaddrinfo", getaddr_)


def _env(base: Path, url: str, **extra) -> dict:
    guarda = base / "guarda"
    guarda.mkdir(exist_ok=True)
    (guarda / "sitecustomize.py").write_text(GUARDA, encoding="utf-8")
    assert url.startswith("sqlite:///")  # nunca o Postgres de ninguem
    env = {**os.environ, "DATABASE_URL": url, "PYTHONPATH": str(guarda)}
    for k in ("VIRTUAL_ENV", "PROFESSOR_ID", "LLM_PROVIDER", "LLM_MODEL", "GROQ_API_KEY", "GARMIN_EMAIL", "GARMIN_PASSWORD"):
        env.pop(k, None)  # nenhum provedor, conta nem professor de verdade, mesmo com um .env na maquina de quem roda
    env.update(extra)
    return env


def _roda(args, env, cwd=RAIZ, esperado=0):
    r = subprocess.run([sys.executable, *args], env=env, cwd=cwd, capture_output=True, text=True)
    assert r.returncode == esperado, f"{args}\nstdout: {r.stdout}\nstderr: {r.stderr}"
    return r


def _carrega_treinos(url: str) -> None:
    """O passo 4 do guia (datas relativas a hoje)."""
    from app.db.models import Atividade, Atleta, CheckinTreino

    eng = create_engine(url)
    agora = datetime.now(UTC)
    with Session(eng) as s:
        for nome, fonte_id, dias, modalidade, minutos, tipo, ci in TREINOS:
            atleta = s.scalars(__import__("sqlalchemy").select(Atleta).where(Atleta.nome == nome)).one()
            a = Atividade(
                atleta_id=atleta.id, fonte="fixture", fonte_id=fonte_id, modalidade=modalidade, subtipo=None,
                inicio=(agora - timedelta(days=dias)).replace(hour=10, minute=0, second=0, microsecond=0),
                fuso_min=-180, duracao_s=minutos * 60.0, tipo_treino=tipo, tipo_origem="sugestao" if tipo else None)
            s.add(a)
            s.flush()
            if ci:
                s.add(CheckinTreino(
                    atividade_id=a.id, pse=ci["pse"], sensacao=ci["sensacao"], nada_a_relatar=not ci["dor"] and ci["texto"] is None,
                    texto=ci["texto"], versao="checkin@1", registrado_em=agora, atualizado_em=agora,
                    dor=ci["dor"], cansaco=False, sono_ruim=False, calor=False, trabalho_estresse=False))
        s.commit()
    eng.dispose()


@pytest.fixture(scope="module")
def base(tmp_path_factory):
    """Banco migrado ate o head, com o professor e os atletas das fixtures (comando de verdade) e os 5 treinos do guia."""
    pasta = tmp_path_factory.mktemp("e2e_meta11")
    url = f"sqlite:///{pasta / 'base.db'}"
    env = _env(pasta, url)
    r = subprocess.run(
        [sys.executable, "-c", "import socket; socket.create_connection(('example.com', 80), timeout=1)"],
        env=env, capture_output=True, text=True,
    )
    assert r.returncode != 0 and "conexao de rede" in r.stderr  # a guarda vale mesmo
    mig = _roda(["-m", "alembic", "upgrade", "head"], env, API)
    car = _roda(["-m", "worker.carregar_professor", "--fixtures", str(PASTA11)], env)
    _carrega_treinos(url)
    return SimpleNamespace(pasta=pasta, arquivo=pasta / "base.db", url=url, env=env, saida_alembic=mig.stderr + mig.stdout,
                           saida_carga=car.stdout + car.stderr)


def _sql(eng, comando, **p):
    with eng.begin() as c:
        r = c.execute(text(comando), p)
        return r.all() if r.returns_rows else []


@pytest.fixture
def mundo(base, tmp_path, monkeypatch):
    """Uma copia do banco da base + a API em processo (TestClient) como o professor 1. Um teste nao suja o outro."""
    from app.config import settings
    from app.db.session import get_session
    from app.main import app
    from app.rotas.atividades import get_fit_dir

    arq = tmp_path / "treino.db"
    shutil.copy(base.arquivo, arq)
    eng = create_engine(f"sqlite:///{arq}", connect_args={"check_same_thread": False})

    def sessao():
        with Session(eng) as s:
            yield s

    monkeypatch.setattr(settings, "professor_id", 1)
    app.dependency_overrides[get_session] = sessao
    app.dependency_overrides[get_fit_dir] = lambda: tmp_path / "fit"
    try:
        yield SimpleNamespace(client=TestClient(app, raise_server_exceptions=False), eng=eng, base=base, pasta=tmp_path,
                              sql=lambda comando, **p: _sql(eng, comando, **p), app=app)
    finally:
        app.dependency_overrides.clear()
        eng.dispose()


CAIXA = "/professores/1/caixa-do-dia"
LOTE = "/professores/1/tipos-de-treino"


def _caixa(m):
    r = m.client.get(CAIXA)
    assert r.status_code == 200, r.text[:300]
    return r.json()


def _estado(m):
    return m.sql("select id, tipo_treino, tipo_origem, tipo_versao, tipo_divergencia, tipo_confirmado, tipo_confirmado_por, "
                 "tipo_confirmado_em from atividade order by id")


def _novo_atleta(m, nome, *, treino_dias=1, vinculo="valido"):
    """Um atleta sintetico com um treino com dor e tipo sugerido (nunca pode vazar para quem nao tem vinculo com consentimento)."""
    from app.db.models import Atividade, Atleta, CheckinTreino, VinculoProfessorAtleta

    agora = datetime.now(UTC)
    with Session(m.eng) as s:
        a = Atleta(assessoria_id=1, nome=nome)
        s.add(a)
        s.flush()
        cons = {"valido": agora - timedelta(days=30), "nulo": None, "futuro": agora + timedelta(days=2)}
        if vinculo in cons:
            s.add(VinculoProfessorAtleta(professor_id=1, atleta_id=a.id, consentimento_em=cons[vinculo]))
        elif vinculo == "outro_professor":
            s.add(VinculoProfessorAtleta(professor_id=2, atleta_id=a.id, consentimento_em=agora - timedelta(days=30)))
        ativ = Atividade(atleta_id=a.id, fonte="fixture", fonte_id=f"m11-{a.id}", modalidade="corrida",
                         inicio=(agora - timedelta(days=treino_dias)).replace(hour=10, minute=0, second=0, microsecond=0),
                         fuso_min=-180, duracao_s=2700.0, tipo_treino="intervalado", tipo_origem="sugestao")
        s.add(ativ)
        s.flush()
        s.add(CheckinTreino(atividade_id=ativ.id, pse=8, sensacao=2, nada_a_relatar=False, texto=OBS, versao="checkin@1",
                            registrado_em=agora, atualizado_em=agora, dor=True, cansaco=False, sono_ruim=False, calor=False,
                            trabalho_estresse=False))
        s.commit()
        return a.id, ativ.id


def _percorre(valor, caminho=()):
    """Todas as folhas (caminho, valor) de um JSON."""
    if isinstance(valor, dict):
        for k, v in valor.items():
            yield from _percorre(v, (*caminho, k))
    elif isinstance(valor, list):
        for i, v in enumerate(valor):
            yield from _percorre(v, (*caminho, i))
    else:
        yield caminho, valor


# ------------------------------------------------------------------ migracao 0016 e carga (passos 2 e 3 do guia)

def test_01_migracoes_ate_o_head_e_a_0016_com_as_tres_colunas_e_a_fk_nomeada(mundo):
    """Item: ADR 0015, item 1 (migracao 0016, aprovada pelo Theo): `tipo_confirmado_por`, `tipo_confirmado_em`, `feedback_treino.tipo_visto`."""
    assert mundo.sql("select version_num from alembic_version") == [(_HEAD,)]
    assert int(_HEAD) >= 16
    ativ = {c[1] for c in mundo.sql("pragma table_info(atividade)")}
    assert {"tipo_confirmado", "tipo_confirmado_por", "tipo_confirmado_em"} <= ativ
    assert "tipo_visto" in {c[1] for c in mundo.sql("pragma table_info(feedback_treino)")}
    fks = mundo.sql("pragma foreign_key_list(atividade)")  # (id, seq, tabela, de, para, on_update, on_delete, match)
    assert any(f[2] == "professor" and f[3] == "tipo_confirmado_por" and f[6] == "SET NULL" for f in fks)


def test_02_migracao_0016_desce_e_sobe_sem_tocar_nas_linhas(tmp_path):
    """Item: a 0016 e aditiva e reversivel: o `downgrade` apaga so o que ela criou (ADR 0015, Consequencias)."""
    url = f"sqlite:///{tmp_path / 'm.db'}"
    env = _env(tmp_path, url)
    _roda(["-m", "alembic", "upgrade", "head"], env, API)
    eng = create_engine(url)
    _sql(eng, "insert into atleta (id, nome) values (1, 'Atleta Fixture Migracao')")
    _sql(eng, "insert into atividade (atleta_id, fonte, fonte_id, modalidade, inicio, duracao_s) "
              "values (1, 'fixture', 'mig-1', 'corrida', '2026-11-10 10:00:00', 1800)")
    _roda(["-m", "alembic", "downgrade", "0015"], env, API)
    assert "tipo_confirmado_por" not in {c[1] for c in _sql(eng, "pragma table_info(atividade)")}
    assert "tipo_visto" not in {c[1] for c in _sql(eng, "pragma table_info(feedback_treino)")}
    assert "clima_visto" in {c[1] for c in _sql(eng, "pragma table_info(feedback_treino)")}  # so o que a 0016 criou sai
    assert _sql(eng, "select count(*) from atividade") == [(1,)]
    _roda(["-m", "alembic", "upgrade", "head"], env, API)
    assert _sql(eng, "select tipo_confirmado_por, tipo_confirmado_em from atividade") == [(None, None)]
    assert _sql(eng, "select version_num from alembic_version") == [(_HEAD,)]
    eng.dispose()


def test_03_carga_do_professor_e_dos_oito_atletas_idempotente(base, mundo):
    """Item: passo 3 do guia: `professores=2 atletas=8 vinculos=8`, `PROFESSOR_ID=1`; rodar de novo nao muda nada."""
    assert "professores=2 atletas=8 vinculos=8" in base.saida_carga and "PROFESSOR_ID=1" in base.saida_carga
    antes = mundo.sql("select count(*) from atleta"), mundo.sql("select count(*) from vinculo_professor_atleta")
    r = _roda(["-m", "worker.carregar_professor", "--fixtures", str(PASTA11)], {**base.env, "DATABASE_URL": str(mundo.eng.url)})
    assert "professores=2 atletas=8 vinculos=8" in r.stdout
    assert (mundo.sql("select count(*) from atleta"), mundo.sql("select count(*) from vinculo_professor_atleta")) == antes
    assert antes == ([(8,)], [(8,)])


# ------------------------------------------------------------------ PROFESSOR_ID (ADR 0015, item 2)

def _porta_livre() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class Api:
    """A API de verdade (uvicorn) num banco copiado, com o `PROFESSOR_ID` que o teste escolher (ou nenhum)."""

    def __init__(self, base, pasta: Path, **extra):
        shutil.copy(base.arquivo, pasta / "api.db")
        self.porta = _porta_livre()
        env = _env(pasta, f"sqlite:///{pasta / 'api.db'}", **extra)
        self.proc = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(self.porta)],
                                     cwd=API, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

    def __enter__(self):
        for _ in range(100):
            if self.proc.poll() is not None:
                raise AssertionError("a API nao subiu:\n" + (self.proc.stdout.read() if self.proc.stdout else ""))
            try:
                if self.get("/health")[0] == 200:
                    return self
            except OSError:
                time.sleep(0.2)
        raise AssertionError("a API demorou demais para subir")

    def __exit__(self, *a):
        self.proc.terminate()
        try:
            self.proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self.proc.kill()
        if self.proc.stdout:
            self.saida = self.proc.stdout.read()
            self.proc.stdout.close()

    def get(self, caminho):
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{self.porta}{caminho}", timeout=10) as r:
                return r.status, r.read(), dict(r.headers)
        except urllib.error.HTTPError as e:
            return e.code, e.read(), dict(e.headers)


def test_04_professor_id_ausente_ou_vazio_a_api_sobe_e_o_404_e_uniforme_byte_a_byte(base, tmp_path):
    """Item: ADR 0015, item 2: a API sobe sem `PROFESSOR_ID` (ausente ou `PROFESSOR_ID=`), as rotas do professor dao o MESMO 404."""
    corpos = {}
    for rotulo, extra in (("ausente", {}), ("vazio", {"PROFESSOR_ID": ""})):
        pasta = tmp_path / rotulo
        pasta.mkdir()
        with Api(base, pasta, **extra) as api:
            assert api.get("/health")[0] == 200  # o resto do app nao depende do professor
            status, corpo, _ = api.get(CAIXA)
            assert status == 404, rotulo
            corpos[rotulo] = corpo
    pasta = tmp_path / "configurado"
    pasta.mkdir()
    with Api(base, pasta, PROFESSOR_ID="1") as api:
        status, corpo, cab = api.get(CAIXA)
        assert status == 200 and cab.get("Cache-Control", cab.get("cache-control")) == "no-store"
        corpos["outro_id"] = api.get("/professores/2/caixa-do-dia")[1]  # existe no banco, mas nao e o configurado
        corpos["sem_linha"] = api.get("/professores/999/caixa-do-dia")[1]
        assert api.get("/professores/1/qualquer-coisa")[0] == 404
    assert len(set(corpos.values())) == 1, corpos
    assert json.loads(corpos["ausente"]) == {
        "detail": [{"loc": ["path", "professor_id"], "msg": "professor inexistente", "type": "professor_inexistente"}]}


def test_05_404_do_professor_vem_antes_do_422_do_corpo_e_nao_grava(mundo, monkeypatch):
    """Item: ADR 0015, item 2 e Duda: professor inexistente e 404 antes de qualquer validacao do corpo do PUT."""
    antes = _estado(mundo)
    ruim = [{"atividade_id": 1, "tipo_treino": "inventado"}]
    r_outro = mundo.client.put("/professores/2/tipos-de-treino", json=ruim)
    r_sem_linha = mundo.client.put("/professores/999/tipos-de-treino", json=[])
    from app.config import settings

    monkeypatch.setattr(settings, "professor_id", None)
    r_sem_config = mundo.client.put(LOTE, json=ruim)
    assert (r_outro.status_code, r_sem_linha.status_code, r_sem_config.status_code) == (404, 404, 404)
    assert r_outro.content == r_sem_linha.content == r_sem_config.content
    assert _estado(mundo) == antes


# ------------------------------------------------------------------ filtro de vinculo e consentimento (decisao 4, ADR 0015, item 3)

SITUACOES = ["nulo", "futuro", "outro_professor", "sem_vinculo"]


def test_06_atleta_sem_vinculo_ou_sem_consentimento_nunca_aparece_nem_nos_novos(mundo):
    """Item: 'atleta sem vinculo com o professor, ou com vinculo sem `consentimento_em`, nunca aparece na caixa nem nos treinos dele'."""
    visivel, _ = _novo_atleta(mundo, "Atleta Fixture Matriz Valido", vinculo="valido")
    fora = {s: _novo_atleta(mundo, f"Atleta Fixture Matriz {s}", vinculo=s) for s in SITUACOES}
    j = _caixa(mundo)
    assert visivel in [a["atleta_id"] for a in j["alunos"]]
    for s, (atleta_id, atividade_id) in fora.items():
        assert atleta_id not in [a["atleta_id"] for a in j["alunos"]], s
        assert atividade_id not in [n["atividade_id"] for n in j["novos"]], s
    # nem por nome (a observacao so existe no detalhe de quem esta no filtro)
    corpo = json.dumps(j, ensure_ascii=False)
    for s_ in SITUACOES:
        assert f"Matriz {s_}" not in corpo
    assert "Eva Sem Consentimento" not in corpo and "Fabio De Outro" not in corpo


def test_07_o_put_em_lote_recusa_com_404_tudo_que_esta_fora_do_filtro_sem_gravar(mundo):
    """Item: a matriz rota x situacao, na rota PUT: nulo, futuro, outro professor, sem vinculo => 404 `atividade_nao_encontrada`."""
    fora = {s: _novo_atleta(mundo, f"Atleta Fixture Matriz {s}", vinculo=s)[1] for s in SITUACOES}
    inexistente = mundo.client.put(LOTE, json=[{"atividade_id": 987654, "tipo_treino": "longo"}])
    assert inexistente.status_code == 404
    antes = _estado(mundo)
    for s, atividade_id in fora.items():
        r = mundo.client.put(LOTE, json=[{"atividade_id": atividade_id, "tipo_treino": "longo"}])
        assert r.status_code == 404, s
        assert r.content == inexistente.content, s  # a mesma resposta de uma atividade que nao existe
        assert r.json()["detail"][0]["type"] == "atividade_nao_encontrada"
    assert _estado(mundo) == antes


def test_08_consentimento_retirado_some_na_proxima_leitura_e_o_put_passa_a_dar_404_mas_o_tipo_gravado_fica(mundo):
    """Item: ADR 0015, item 6 e 'A confirmar' 8: retirar o consentimento tira o atleta da caixa; o que o professor ja gravou fica."""
    atleta_id, atividade_id = _novo_atleta(mundo, "Atleta Fixture Matriz Retirado")
    assert atleta_id in [a["atleta_id"] for a in _caixa(mundo)["alunos"]]
    assert mundo.client.put(LOTE, json=[{"atividade_id": atividade_id, "tipo_treino": "longo"}]).json() == {"confirmados": 0, "corrigidos": 1}
    mundo.sql("update vinculo_professor_atleta set consentimento_em = NULL where atleta_id = :a", a=atleta_id)
    j = _caixa(mundo)
    assert atleta_id not in [a["atleta_id"] for a in j["alunos"]]
    assert atividade_id not in [n["atividade_id"] for n in j["novos"]]
    assert mundo.client.put(LOTE, json=[{"atividade_id": atividade_id, "tipo_treino": "leve"}]).status_code == 404
    assert mundo.sql("select tipo_treino, tipo_origem, tipo_confirmado_por from atividade where id = :i", i=atividade_id) == [("longo", "professor", 1)]


def test_09_consentimento_no_futuro_entra_quando_a_data_chega_e_o_do_passado_ja_vale(mundo):
    """Item: ADR 0015, item 6 (passagem do tempo): consentimento no futuro entra quando chega, sem ninguem agir."""
    atleta_id, _ = _novo_atleta(mundo, "Atleta Fixture Matriz Futuro", vinculo="futuro")
    assert atleta_id not in [a["atleta_id"] for a in _caixa(mundo)["alunos"]]
    mundo.sql("update vinculo_professor_atleta set consentimento_em = :quando where atleta_id = :a",
              quando=(datetime.now(UTC) - timedelta(minutes=1)).strftime("%Y-%m-%d %H:%M:%S"), a=atleta_id)
    assert atleta_id in [a["atleta_id"] for a in _caixa(mundo)["alunos"]]


# ------------------------------------------------------------------ GET da caixa (passo 5 do guia)

def test_10_get_da_caixa_ordem_motivos_novos_e_cabecalhos_como_no_guia(mundo):
    """Item: 'GET da caixa do dia': ordem por atencao, motivo em uma linha, sem motivo por ultimo, treinos novos, `no-store`."""
    r = mundo.client.get(CAIXA)
    assert r.status_code == 200 and r.headers["cache-control"] == "no-store"
    j = r.json()
    hoje = datetime.now(UTC).astimezone(__import__("zoneinfo").ZoneInfo("America/Sao_Paulo")).date()
    assert (j["versao"], j["janela_atencao_dias"], j["janela_novos_dias"]) == ("atencao@2", 7, 14)
    assert abs((date.fromisoformat(j["hoje"]) - hoje).days) <= 1
    assert [a["nome"] for a in j["alunos"]] == [
        "Atleta Fixture Ana", "Atleta Fixture Carla", "Atleta Fixture Igor", "Atleta Fixture Helena", "Atleta Fixture Bruno",
        "Atleta Fixture Davi"]
    ana, carla, *resto = j["alunos"]
    assert [m["codigo"] for m in ana["treinos"][0]["motivos"]] == ["dor"]
    assert re.fullmatch(r"Treino de \w+ com dor marcada no check-in\.", ana["treinos"][0]["motivos"][0]["texto"])
    assert [m["codigo"] for m in carla["treinos"][0]["motivos"]] == ["checkin_vencendo"]
    assert re.fullmatch(r"Treino de \w+ sem check-in; o prazo termina em [12] dias?\.", carla["treinos"][0]["motivos"][0]["texto"])
    assert carla["treinos"][0]["modalidade"] == "ciclismo"
    for a in resto:
        assert (a["sem_motivo"], a["texto_sem_motivo"], a["treinos"]) == (True, "Nada a destacar nos últimos 7 dias.", [])
    # os treinos novos: mais recente primeiro; o treino sem tipo (3) nao entra
    assert [(n["atividade_id"], n["tipo_sugerido"], n["origem_texto"]) for n in j["novos"]] == [
        (2, "intervalado", "sugerido pela regra"), (1, "leve", "sugerido pela regra"), (4, "moderado", "sugerido pela regra")]
    assert {n["atleta_nome"] for n in j["novos"]} == {"Atleta Fixture Bruno", "Atleta Fixture Ana", "Atleta Fixture Carla"}
    # quem esta fora do filtro (Eva sem consentimento, Fabio de outro professor) nao aparece em lugar nenhum
    assert "Eva" not in json.dumps(j) and "Fabio" not in json.dumps(j)


def test_11_a_observacao_livre_so_existe_no_detalhe_do_checkin(mundo):
    """Item: decisao 7: a observacao so viaja em `detalhe.checkin.observacao` (nunca na lista, no motivo nem em log)."""
    j = _caixa(mundo)
    achados = [c for c, v in _percorre(j) if v == OBS]
    assert achados, "a observacao do check-in da Ana tem que chegar ao professor, no detalhe"
    assert all(c[-3:] == ("detalhe", "checkin", "observacao") for c in achados), achados
    assert not [c for c, v in _percorre(j) if isinstance(v, str) and OBS in v and v != OBS]


def test_12_a_observacao_nunca_vai_ao_log_nem_ao_prompt_do_provedor(mundo, caplog):
    """Item: decisao 7: a observacao nunca vai ao provedor de LLM (o pacote nao tem o campo) nem a log."""
    import logging

    from app.llm import Redator
    from app.llm.camada import ProvedorFalso
    from worker.gerar_feedback import main

    caplog.set_level(logging.DEBUG)
    _caixa(mundo)
    mundo.client.put(LOTE, json=[{"atividade_id": 1}])
    prompts = []

    class Espia(ProvedorFalso):
        def completar(self, sistema, usuario, timeout_s):
            prompts.append(sistema + "\n" + usuario)
            return super().completar(sistema, usuario, timeout_s)

    redator = Redator(Espia(), "falso", "falso", timeout_s=5, limite_chamadas=20)
    from sqlalchemy.orm import sessionmaker

    main(["--atleta", "Atleta Fixture Ana"], redator=redator, session_factory=sessionmaker(mundo.eng))
    assert prompts, "o provedor falso precisa ter sido chamado para a prova valer"
    assert not [p for p in prompts if OBS in p]
    assert OBS not in caplog.text


def test_13_a_caixa_nao_importa_a_camada_de_llm():
    """Item: decisao 7 (b): a caixa nao chama LLM. Importar a rota nao carrega biblioteca de provedor, e o codigo da caixa nao importa a camada."""
    codigo = (
        "import sys\n"
        "import app.rotas.caixa_do_dia, app.rotas.professor, app.servicos.professor, app.servicos.tipo_professor, app.metricas.atencao\n"
        "ruim = sorted(m for m in sys.modules if m.split('.')[0] in ('litellm', 'openai', 'groq', 'anthropic') or m.startswith('app.llm'))\n"
        "print('IMPORTOU:' + ','.join(ruim))\n"
    )
    r = _roda(["-c", codigo], {k: v for k, v in os.environ.items() if k != "VIRTUAL_ENV"}, API)
    carregados = set(filter(None, r.stdout.strip().removeprefix("IMPORTOU:").split(",")))
    # Achado (nao e bug): `app.llm.camada` chega por import transitivo (rotas.atividades -> servicos.feedback, que o reaproveita para o
    # feedback do detalhe). So as definicoes; nenhuma biblioteca de provedor e carregada e nada e chamado (o teste 12 prova).
    assert carregados <= {"app.llm", "app.llm.camada"}, carregados
    # e a fonte tambem nao fala em provedor
    for arq in ("rotas/caixa_do_dia.py", "rotas/professor.py", "servicos/tipo_professor.py", "servicos/professor.py", "metricas/atencao.py"):
        fonte = (API / "app" / arq).read_text(encoding="utf-8")
        assert not re.search(r"^\s*(from|import)\s+(app\.llm|litellm|openai|groq|anthropic)", fonte, re.M), arq


def test_14_atencao_nao_recebe_a_observacao():
    """Item: ADR 0015, item 4: a funcao `atencao@1` nem tem o campo da observacao livre na entrada."""
    import dataclasses

    from app.metricas.atencao import TreinoAtencao

    campos = {f.name for f in dataclasses.fields(TreinoAtencao)}
    assert "texto" not in campos and "observacao" not in campos
    assert "dor" in campos


def test_15_os_quatro_motivos_pelo_banco_dor_checkin_vencendo_divergencia_e_fora_do_normal(mundo):
    """Item: `atencao@1` com quatro motivos. O guia so mostra dois pelo banco; aqui os outros dois (semana-padrao e linha de base)."""
    from app.db.models import Atividade, Atleta, BlocoAtividade, CheckinTreino

    agora = datetime.now(UTC)
    # fora_do_normal: 9 corridas leves de FC parecida (linha de base) e a de hoje -1 com FC muito acima
    with Session(mundo.eng) as s:
        helena = s.scalars(__import__("sqlalchemy").select(Atleta).where(Atleta.nome == "Atleta Fixture Helena")).one()
        for i in range(9):
            s.add(Atividade(atleta_id=helena.id, fonte="fixture", fonte_id=f"m11-lb-{i}", modalidade="corrida",
                            inicio=(agora - timedelta(days=15 + 4 * i)).replace(hour=9, minute=0, second=0, microsecond=0), fuso_min=-180,
                            duracao_s=2700.0 + 30 * (i % 3), fc_media=138.0 + (i % 4), tipo_treino="leve", tipo_origem="professor",
                            tipo_confirmado=True))
        atual = Atividade(atleta_id=helena.id, fonte="fixture", fonte_id="m11-lb-atual", modalidade="corrida",
                          inicio=(agora - timedelta(days=1)).replace(hour=9, minute=0, second=0, microsecond=0), fuso_min=-180,
                          duracao_s=2700.0, fc_media=178.0, tipo_treino="leve", tipo_origem="professor", tipo_confirmado=True)
        s.add(atual)
        s.flush()
        s.add(CheckinTreino(atividade_id=atual.id, pse=6, sensacao=3, nada_a_relatar=True, texto=None, versao="checkin@1",
                            registrado_em=agora, atualizado_em=agora, dor=False, cansaco=False, sono_ruim=False, calor=False,
                            trabalho_estresse=False))
        s.commit()
    # divergencia: semana-padrao manda 'intervalado' naquele dia, mas o treino do Davi e uma rodagem sem esforco
    dia = (agora - timedelta(days=2)).astimezone().date()
    with Session(mundo.eng) as s:
        davi = s.scalars(__import__("sqlalchemy").select(Atleta).where(Atleta.nome == "Atleta Fixture Davi")).one()
        trein = Atividade(atleta_id=davi.id, fonte="fixture", fonte_id="m11-dv-1", modalidade="corrida",
                          inicio=(agora - timedelta(days=2)).replace(hour=10, minute=0, second=0, microsecond=0), fuso_min=-180,
                          duracao_s=2700.0)
        s.add(trein)
        s.flush()
        # um unico bloco leve (rodagem sem esforco): so assim a semana-padrao 'intervalado' diverge (`sem_esforco`, ADR 0011, item 4)
        s.add(BlocoAtividade(atividade_id=trein.id, ordem=1, categoria="leve", volta_inicial=1, volta_final=1, inicio_offset_s=0.0,
                             duracao_s=2700.0, distancia_m=7000.0, versao_deteccao="esforcos@1"))
        s.commit()
        davi_id = davi.id
    r = mundo.client.put(f"/atletas/{davi_id}/semana-padrao", json={
        "vigente_desde": (dia - timedelta(days=7)).isoformat(), "definido_por": "professor",
        "itens": [{"dia_semana": i, "modalidade": "corrida", "tipo_treino": "intervalado"} for i in range(1, 8)]})
    assert r.status_code == 200, r.text
    j = _caixa(mundo)
    por_nome = {a["nome"]: a for a in j["alunos"]}
    codigos = {n: [m["codigo"] for t in a["treinos"] for m in t["motivos"]] for n, a in por_nome.items()}
    assert codigos["Atleta Fixture Ana"] == ["dor"]
    assert codigos["Atleta Fixture Carla"] == ["checkin_vencendo"]
    assert codigos["Atleta Fixture Helena"] == ["fora_do_normal"]
    assert codigos["Atleta Fixture Davi"] == ["divergencia"]
    texto = por_nome["Atleta Fixture Helena"]["treinos"][0]["motivos"][0]["texto"]
    assert "FC média acima do habitual" in texto
    assert not re.search(r"por causa|descanse|lesão|preocupante", texto, re.I)  # direcao e metrica, nunca causa nem conselho
    # a ordem de prioridade entre atletas: dor, fora do normal, divergencia, check-in vencendo
    nomes = [a["nome"] for a in j["alunos"] if not a["sem_motivo"]]
    assert nomes == ["Atleta Fixture Ana", "Atleta Fixture Helena", "Atleta Fixture Davi", "Atleta Fixture Carla"]


# ------------------------------------------------------------------ PUT em lote (passo 6 do guia)

def test_16_put_em_lote_confirma_e_corrige_como_no_guia(mundo):
    """Item: confirmar sem mudar so marca; corrigir grava origem `professor`, versao e divergencia zeradas, quem e quando."""
    antes = {r[0]: r for r in _estado(mundo)}
    r = mundo.client.put(LOTE, json=[{"atividade_id": 2}, {"atividade_id": 4, "tipo_treino": "longo"}])
    assert r.status_code == 200 and r.json() == {"confirmados": 1, "corrigidos": 1}
    depois = {r[0]: r for r in _estado(mundo)}
    # 2: confirmado, origem e versao ficam
    assert depois[2][1:5] == antes[2][1:5] == ("intervalado", "sugestao", None, None)
    assert depois[2][5:7] == (1, 1) and depois[2][7] is not None
    # 4: corrigido
    assert depois[4][1:7] == ("longo", "professor", None, None, 1, 1) and depois[4][7] is not None
    for outro in (1, 3, 5):
        assert depois[outro] == antes[outro]
    assert [n["atividade_id"] for n in _caixa(mundo)["novos"]] == [1]  # so o treino 1 segue por confirmar
    # repetir nao muda nada e nao renova o `tipo_confirmado_em`
    assert mundo.client.put(LOTE, json=[{"atividade_id": 2}, {"atividade_id": 4, "tipo_treino": "longo"}]).json() == {
        "confirmados": 2, "corrigidos": 0}
    assert {r[0]: r for r in _estado(mundo)} == depois


def test_17_corrigir_apaga_a_divergencia_e_confirmar_a_deixa_gravada_mas_cala_o_motivo(mundo):
    """Item: ADR 0015, item 5 (tabela): corrigir apaga `tipo_divergencia`; confirmar deixa a coluna e o motivo 3 para de disparar."""
    mundo.sql("update atividade set tipo_treino = 'intervalado', tipo_origem = 'semana_padrao', tipo_versao = 'tipo_treino@1', "
              "tipo_divergencia = 'sem_esforco' where id in (1, 4)")
    assert [m["codigo"] for a in _caixa(mundo)["alunos"] for t in a["treinos"] for m in t["motivos"]].count("divergencia") == 2
    assert mundo.client.put(LOTE, json=[{"atividade_id": 1}, {"atividade_id": 4, "tipo_treino": "leve"}]).json() == {
        "confirmados": 1, "corrigidos": 1}
    est = {r[0]: r for r in _estado(mundo)}
    assert est[1][1:6] == ("intervalado", "semana_padrao", "tipo_treino@1", "sem_esforco", 1)  # confirmar: a coluna fica
    assert est[4][1:6] == ("leve", "professor", None, None, 1)  # corrigir: apagada
    motivos = [m["codigo"] for a in _caixa(mundo)["alunos"] for t in a["treinos"] for m in t["motivos"]]
    assert "divergencia" not in motivos


def test_18_put_valida_o_lote_inteiro_vazio_repetido_mais_de_200_e_tipo_fora_dos_cinco_dao_422_sem_gravar(mundo):
    """Item: validacoes do lote (ADR 0015, item 5): lote vazio, `atividade_id` repetido, mais de 200 itens, tipo fora dos cinco."""
    antes = _estado(mundo)
    casos = {
        "vazio": [],
        "repetido": [{"atividade_id": 1}, {"atividade_id": 1, "tipo_treino": "longo"}],
        "mais_de_200": [{"atividade_id": 1000 + i} for i in range(201)],
        "tipo_fora": [{"atividade_id": 1, "tipo_treino": "regenerativo"}],
        "tipo_nulo_texto": [{"atividade_id": 1, "tipo_treino": ""}],
    }
    for nome, corpo in casos.items():
        r = mundo.client.put(LOTE, json=corpo)
        assert r.status_code == 422, (nome, r.status_code, r.text[:200])
        assert "regenerativo" not in r.text  # o 422 nao repete o que foi enviado
    assert _estado(mundo) == antes
    # 200 itens e aceito (o limite e inclusivo): todos inexistentes => 404, nao 422
    assert mundo.client.put(LOTE, json=[{"atividade_id": 1000 + i} for i in range(200)]).status_code == 404


def test_19_put_o_404_da_atividade_vem_antes_do_422_atividade_sem_tipo(mundo):
    """Item: ordem das recusas: atividade fora do filtro (404) antes de atividade sem tipo (422)."""
    antes = _estado(mundo)
    assert mundo.client.put(LOTE, json=[{"atividade_id": 3}]).status_code == 422  # ciclismo sem tipo: nada a confirmar
    assert mundo.client.put(LOTE, json=[{"atividade_id": 3}]).json()["detail"][0]["type"] == "atividade_sem_tipo"
    mista = mundo.client.put(LOTE, json=[{"atividade_id": 3}, {"atividade_id": 5}])  # 5 e da Eva, sem consentimento
    assert mista.status_code == 404 and mista.json()["detail"][0]["type"] == "atividade_nao_encontrada"
    assert _estado(mundo) == antes


def test_20_put_e_tudo_ou_nada(mundo):
    """Item: tudo ou nada: um item ruim derruba o lote e nada dos bons e gravado (404 e 422)."""
    antes = _estado(mundo)
    assert mundo.client.put(LOTE, json=[{"atividade_id": 2}, {"atividade_id": 4, "tipo_treino": "longo"}, {"atividade_id": 5}]).status_code == 404
    assert _estado(mundo) == antes
    assert mundo.client.put(LOTE, json=[{"atividade_id": 2}, {"atividade_id": 4, "tipo_treino": "longo"}, {"atividade_id": 3}]).status_code == 422
    assert _estado(mundo) == antes
    assert mundo.client.put(LOTE, json=[{"atividade_id": 2}, {"atividade_id": 4, "tipo_treino": "longo"}]).status_code == 200


# ------------------------------------------------------------------ a correcao vence o que vem depois (decisao 8)

def test_21_a_correcao_nao_e_desfeita_pela_reimportacao_do_fit(mundo):
    """Item: 'a correcao do professor vence a sugestao e nao e desfeita pela reimportacao': envia o FIT, corrige, envia de novo."""
    dados = FIT.read_bytes()
    r1 = mundo.client.post("/atletas/1/atividades/fit", files={"arquivo": ("treino.fit", dados, "application/octet-stream")})
    assert r1.status_code == 201, r1.text
    atividade_id = r1.json()["atividade_id"]
    tipo0 = mundo.sql("select tipo_treino from atividade where id = :i", i=atividade_id)[0][0]
    novo = "longo" if tipo0 != "longo" else "leve"
    assert mundo.client.put(LOTE, json=[{"atividade_id": atividade_id, "tipo_treino": novo}]).status_code == 200
    depois = mundo.sql("select tipo_treino, tipo_origem, tipo_versao, tipo_divergencia, tipo_confirmado, tipo_confirmado_por "
                       "from atividade where id = :i", i=atividade_id)
    assert depois == [(novo, "professor", None, None, 1, 1)]
    r2 = mundo.client.post("/atletas/1/atividades/fit", files={"arquivo": ("treino.fit", dados, "application/octet-stream")})
    assert r2.status_code == 200 and r2.json()["atividade_id"] == atividade_id
    assert mundo.sql("select tipo_treino, tipo_origem, tipo_versao, tipo_divergencia, tipo_confirmado, tipo_confirmado_por "
                     "from atividade where id = :i", i=atividade_id) == depois


def test_22_a_correcao_e_a_confirmacao_nao_sao_desfeitas_pela_semana_padrao_editada(mundo):
    """Item: 'nao e desfeita por semana-padrao': com controle positivo (o treino sem tipo e sem confirmacao RECEBE a semana-padrao)."""
    assert mundo.client.put(LOTE, json=[{"atividade_id": 2}, {"atividade_id": 4, "tipo_treino": "longo"}]).status_code == 200
    antes = {r[0]: r for r in _estado(mundo)}
    semana = {"vigente_desde": "2026-01-05", "definido_por": "professor"}
    itens = lambda tipo: [{"dia_semana": d, "modalidade": m, "tipo_treino": tipo} for d in range(1, 8) for m in ("corrida", "ciclismo")]  # noqa: E731
    for atleta in (4, 5):  # Bruno (treino 2 confirmado) e Carla (treino 4 corrigido; treino 3 sem tipo)
        assert mundo.client.put(f"/atletas/{atleta}/semana-padrao", json={**semana, "itens": itens("moderado")}).status_code == 200
    depois = {r[0]: r for r in _estado(mundo)}
    assert depois[2] == antes[2] and depois[4] == antes[4]  # confirmado e corrigido: intactos
    assert depois[3][1:3] == ("moderado", "semana_padrao")  # controle: a semana-padrao funciona onde nao ha decisao do professor
    # uma segunda edicao da semana, com outro tipo: o corrigido continua
    assert mundo.client.put("/atletas/5/semana-padrao", json={**semana, "itens": itens("fartlek")}).status_code == 200
    assert {r[0]: r for r in _estado(mundo)}[4] == antes[4]


def test_23_reclassificar_com_o_comando_do_worker_nao_desfaz_a_correcao(mundo, base):
    """Item: 'nem por versao nova da regra': `worker.reclassificar` (regra de tiros) roda inteira e a correcao fica."""
    assert mundo.client.put(LOTE, json=[{"atividade_id": 4, "tipo_treino": "longo"}]).status_code == 200
    antes = {r[0]: r for r in _estado(mundo)}
    for atleta_id in (1, 5):
        _roda(["-m", "worker.reclassificar", "--atleta-id", str(atleta_id)], {**base.env, "DATABASE_URL": str(mundo.eng.url)})
    assert {r[0]: r for r in _estado(mundo)}[4] == antes[4]


# ------------------------------------------------------------------ feedback depois da correcao (motivo `tipo`)

def test_24_corrigir_o_tipo_desatualiza_o_feedback_pelo_motivo_tipo_e_o_worker_refaz(mundo):
    """Item: 'motivo `tipo` no feedback': a correcao deixa o feedback desatualizado; confirmar sem mudar nao; o worker refaz."""
    from app.llm import Redator
    from app.llm.camada import ProvedorFalso
    from sqlalchemy.orm import sessionmaker
    from worker.gerar_feedback import main

    fab = sessionmaker(mundo.eng)

    def gerar(*args):
        redator = Redator(ProvedorFalso(), "falso", "falso", timeout_s=5, limite_chamadas=20)
        assert main(["--atleta", "Atleta Fixture Bruno", *args], redator=redator, session_factory=fab) == 0
        return redator

    def fb():
        return mundo.client.get("/atletas/4/atividades/2").json()["feedback"]

    gerar()
    pronto = fb()
    assert pronto["estado"] == "pronto", pronto
    assert mundo.sql("select tipo_visto from feedback_treino") == [("intervalado",)]
    # confirmar sem mudar nao desatualiza
    assert mundo.client.put(LOTE, json=[{"atividade_id": 2}]).status_code == 200
    assert fb()["estado"] == "pronto"
    # corrigir desatualiza, com a mensagem do motivo `tipo`
    assert mundo.client.put(LOTE, json=[{"atividade_id": 2, "tipo_treino": "fartlek"}]).json() == {"confirmados": 0, "corrigidos": 1}
    desatual = fb()
    assert desatual["estado"] == "desatualizado", desatual
    assert "O tipo do treino mudou depois deste feedback. O feedback será refeito." in json.dumps(desatual, ensure_ascii=False)
    # o worker entra na fila pelo motivo e refaz com o tipo novo
    redator = gerar()
    assert redator.chamadas >= 1
    assert fb()["estado"] == "pronto"
    assert mundo.sql("select tipo_visto from feedback_treino") == [("fartlek",)]
    # e a caixa mostra o feedback do detalhe sem texto de outro treino
    j = _caixa(mundo)
    assert j["hoje"]
