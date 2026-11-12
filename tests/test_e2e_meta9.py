"""QA de ponta a ponta da Meta 9, o feedback automático por treino (issue #332, ADR 0013).

Segue o roteiro de `docs/produto/meta-9-como-rodar.md`: migrações (alembic, até a 0013) -> as 18 atividades sintéticas de
`tests/fixtures/meta8/` e o check-in de 15/10 no banco (como o `carregar.py` do guia) -> API (TestClient): os oito `PUT` do passo 5
-> o `feedback` no `GET` da atividade em cada estado -> `worker.gerar_feedback` (em processo, com o provedor falso) em duas rodadas,
com texto reprovado, limite do provedor, `--refazer` -> editar e apagar o check-in -> `worker.apagar_checkin` em subprocesso ->
OpenAPI, cliente e documentos. Num SQLite temporário; só dado sintético; sem rede (guarda de socket, como no e2e da Meta 8).

Um teste por item do critério de pronto da Meta 9 (`docs/produto/roadmap.md`); o item de cada teste está no docstring.
Os testes seguem a ordem do arquivo e dividem o mesmo banco, então a ordem importa.

O que este arquivo NÃO cobre (exige olho humano ou rede): o cartão na tela (web e celular), o provedor de verdade e a revisão da Lia.
O `worker.gerar_feedback` com `LLM_PROVIDER=falso` na linha de comando é coberto pelo test_20 (o bug #361 foi corrigido).
"""

import importlib.util
import json
import logging
import os
import re
import socket
import subprocess
import sys
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

RAIZ = Path(__file__).resolve().parents[1]
PASTA8 = RAIZ / "tests" / "fixtures" / "meta8"
PASTA9 = RAIZ / "tests" / "fixtures" / "meta9"
API = RAIZ / "services" / "api"
WORKER = RAIZ / "services" / "worker"
MARCADOR = "MARCADOR-SINTETICO-TEXTO-LIVRE"
FORA_DO_PRAZO = "2026-10-15/cor1"
ATLETA = "Atleta Fictício"

# Texto que passa nas checagens@2 (3 linhas, verbo, sem número, sem nome próprio). É o mesmo `TEXTO_BOM` do provedor falso (corrigido no #361).
TEXTO_OK = (
    "Este é um texto de teste do provedor falso.\n"
    "Esta linha foi escrita só para os testes.\n"
    "Nenhum dado real é usado aqui."
)

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


def _carregar(nome, caminho):
    for p in (str(API), str(WORKER)):
        if p not in sys.path:
            sys.path.insert(0, p)
    spec = importlib.util.spec_from_file_location(nome, caminho)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[nome] = mod
    spec.loader.exec_module(mod)
    return mod


O9 = _carregar("oraculo_meta9_e2e", PASTA9 / "oraculo.py")
T9 = _carregar("textos_meta9_e2e", PASTA9 / "textos.py")
FIXTURES = json.loads((PASTA8 / "atividades.json").read_text(encoding="utf-8"))["atividades"]
CHECKINS = json.loads((PASTA8 / "checkins.json").read_text(encoding="utf-8"))
ESTADOS_PUBLICOS = {"pronto", "pendente", "desatualizado", "indisponivel", "sem_checkin"}


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


def _roda(args, env, cwd=RAIZ, esperado=0):
    r = subprocess.run([sys.executable, *args], env=env, cwd=cwd, capture_output=True, text=True)
    assert r.returncode == esperado, f"{args}\nstdout: {r.stdout}\nstderr: {r.stderr}"
    return r


def _carrega_fixtures(eng):
    """O passo 3 do guia: 18 atividades e o check-in de 15/10 (fora do prazo de criação). O de 12/11 leva o marcador no texto livre."""
    from app.db.models import Atividade, Atleta, CheckinTreino
    from app.servicos.checkin import hoje_local

    desloc = (hoje_local() - date(2026, 11, 9)).days
    agora = datetime.now(UTC)
    with Session(eng) as s:
        atleta = Atleta(nome=ATLETA)
        s.add(atleta)
        s.flush()
        for f in FIXTURES:
            a = Atividade(
                atleta_id=atleta.id, fonte="fixture", fonte_id=f["id"], modalidade=f["modalidade"], subtipo=f["subtipo"],
                inicio=datetime.fromisoformat(f["inicio"]) + timedelta(days=desloc), fuso_min=f["fuso_min"],
                duracao_s=f["duracao_s"])
            s.add(a)
            s.flush()
            c = CHECKINS.get(f["id"])
            if c and f["id"] == FORA_DO_PRAZO:
                s.add(CheckinTreino(
                    atividade_id=a.id, pse=c["pse"], sensacao=c["sensacao"], nada_a_relatar=c["nada_a_relatar"],
                    texto=c["texto"], versao="checkin@1", registrado_em=agora, atualizado_em=agora,
                    **{k: k in c["atalhos"] for k in ("dor", "cansaco", "sono_ruim", "calor", "trabalho_estresse")}))
        s.commit()
        return atleta.id, desloc


@pytest.fixture(scope="module")
def ctx(tmp_path_factory):
    from app.db.session import get_session
    from app.main import app

    base = tmp_path_factory.mktemp("e2e_meta9")
    guarda = base / "guarda"
    guarda.mkdir()
    (guarda / "sitecustomize.py").write_text(GUARDA, encoding="utf-8")
    url = f"sqlite:///{base / 'treino.db'}"
    assert url.startswith("sqlite:///")  # nunca o Postgres de ninguem
    env = {**os.environ, "DATABASE_URL": url, "PYTHONPATH": str(guarda)}
    for k in ("VIRTUAL_ENV", "LLM_PROVIDER", "LLM_MODEL", "GROQ_API_KEY"):
        env.pop(k, None)  # nenhum provedor de verdade, mesmo com um .env na maquina de quem roda
    r = subprocess.run(
        [sys.executable, "-c", "import socket; socket.create_connection(('example.com', 80), timeout=1)"],
        env=env, capture_output=True, text=True,
    )
    assert r.returncode != 0 and "conexao de rede" in r.stderr  # a guarda vale mesmo
    _roda(["-m", "alembic", "upgrade", "head"], env, API)
    eng = create_engine(url)

    def sessao():
        with Session(eng) as s:
            yield s

    app.dependency_overrides[get_session] = sessao
    try:
        yield {"client": TestClient(app), "eng": eng, "env": env, "app": app, "saidas": [], "fabrica": sessionmaker(eng)}
    finally:
        app.dependency_overrides.clear()
        eng.dispose()


def _sql(ctx, comando, **p):
    with ctx["eng"].begin() as c:
        r = c.execute(text(comando), p)
        return r.all() if r.returns_rows else []


def _ids(ctx):
    return {f: i for i, f in _sql(ctx, "select id, fonte_id from atividade where atleta_id = 1")}


def _fb(ctx, f):
    """O `feedback` do GET da atividade (fonte_id da fixture -> dict ou None)."""
    r = ctx["client"].get(f"/atletas/1/atividades/{_ids(ctx)[f]}")
    assert r.status_code == 200, (f, r.text[:200])
    return r.json()["feedback"]


def _put(ctx, f, corpo, status=200):
    r = ctx["client"].put(f"/atletas/1/atividades/{_ids(ctx)[f]}/checkin", json=corpo)
    assert r.status_code == status, (f, r.status_code, r.text[:300])
    return r


def _linhas_fb(ctx):
    return _sql(ctx, "select estado, motivo, count(*) from feedback_treino group by 1, 2 order by 1, 2")


def _gerar(ctx, *args, provedor=None, capsys=None, **kw):
    """`worker.gerar_feedback` em processo, com um provedor falso injetado. Devolve (código, saída, redator)."""
    from app.llm import Redator
    from app.llm.camada import ProvedorFalso
    from worker.gerar_feedback import main

    falso = provedor or ProvedorFalso(texto=TEXTO_OK)
    redator = Redator(falso, "falso", "falso", timeout_s=5, limite_chamadas=20, **kw)
    codigo = main(["--atleta", ATLETA, *args], redator=redator, session_factory=ctx["fabrica"])
    return codigo, redator, falso


def _saida(capsys):
    c = capsys.readouterr()
    return c.out + c.err


def _worker(ctx, modulo, *args, env_extra=None, esperado=0):
    env = {**ctx["env"], **(env_extra or {})}
    r = _roda(["-m", modulo, "--atleta", ATLETA, *args], env, esperado=esperado)
    ctx["saidas"].append(r.stdout + r.stderr)
    return r.stdout + r.stderr


# ---------------------------------------------------------------- migração e carga (passos 2, 3 e 5)

def test_01_migracao_0013_cria_feedback_treino_um_por_checkin(ctx):
    """Item: feedback guardado no banco, um por check-in (ADR 0013, item 2)."""
    assert _sql(ctx, "select version_num from alembic_version") == [("0013",)]
    colunas = {c[1] for c in _sql(ctx, "pragma table_info(feedback_treino)")}
    assert {"checkin_id", "estado", "motivo", "texto", "provedor", "modelo", "versao_fatos", "versao_prompt", "versao_checagens"} <= colunas
    unicos = [r for r in _sql(ctx, "pragma index_list(feedback_treino)") if r[2]]
    assert unicos, "feedback_treino precisa de um índice único por check-in"


def test_02_carga_das_18_atividades_e_dos_checkins(ctx):
    atleta, desloc = _carrega_fixtures(ctx["eng"])
    print(f"deslocamento {desloc} dias (data do teste: {datetime.now().astimezone():%d/%m/%Y %H:%M})")
    assert atleta == 1 and _sql(ctx, "select count(*) from atividade") == [(18,)]
    for f, corpo in CHECKINS.items():  # os oito da API (passo 5)
        if f != FORA_DO_PRAZO:
            _put(ctx, f, corpo)
    assert _sql(ctx, "select count(*) from checkin_treino") == [(9,)]
    ids = _ids(ctx)
    assert (ids["2026-11-09/cor2"], ids["2026-11-05/cor1"], ids["2026-11-01/cor1"], ids["2026-11-03/out1"]) == (18, 12, 2, 5)


# ---------------------------------------------------------------- pacote de fatos (item 2)

def test_03_pacote_de_fatos_do_banco_nao_leva_dado_pessoal_nem_o_texto_livre(ctx):
    """Item: fatos_treino@1 só com números que o código já calcula, sem identificador, data, posição nem texto livre."""
    from app.db.models import Atividade, CheckinTreino
    from app.servicos.feedback_fatos import fatos_da_atividade

    with ctx["fabrica"]() as s:  # o texto livre de um check-in recebe um marcador (direto no banco: so o pacote importa aqui)
        c = s.get(CheckinTreino, _sql(ctx, "select id from checkin_treino where atividade_id = 18")[0][0])
        c.texto = MARCADOR
        s.commit()
        n = 0
        for a in s.query(Atividade).order_by(Atividade.id):
            ck = s.query(CheckinTreino).filter_by(atividade_id=a.id).first()
            p = fatos_da_atividade(s, a, ck)
            if a.id in (5, 7, 9):  # pai e trocas: sem pacote
                assert p is None
                continue
            if ck is None:
                assert p is None
                continue
            n += 1
            assert p["versao"] == "fatos_treino@2"
            bruto = json.dumps(p, ensure_ascii=False)
            assert MARCADOR not in bruto and a.fonte_id not in bruto and "Atleta" not in bruto

            def chaves(x):
                if isinstance(x, dict):
                    for k, v in x.items():
                        yield k
                        yield from chaves(v)
                elif isinstance(x, list):
                    for v in x:
                        yield from chaves(v)

            assert not set(chaves(p)) & set(O9.NOMES_PROIBIDOS_NO_PACOTE)
    assert n == 9


def test_04_o_pacote_do_oraculo_e_a_chave_da_forma_do_pacote_real(ctx):
    """Item: o oráculo escrito à mão tem o mesmo formato (chaves) do pacote que o código monta."""
    from app.db.models import Atividade, CheckinTreino
    from app.servicos.feedback_fatos import fatos_da_atividade

    with ctx["fabrica"]() as s:
        a = s.get(Atividade, 18)
        p = fatos_da_atividade(s, a, s.query(CheckinTreino).filter_by(atividade_id=18).first())
    esperado = next(x for x in O9.PACOTES.values() if x is not None)
    assert tuple(p) == tuple(esperado)


# ---------------------------------------------------------------- GET antes do worker (passo 6)

def test_05_estados_do_get_antes_do_worker(ctx):
    """Item: `feedback` no GET da atividade, com os estados e a frase pronta em português."""
    f18 = _fb(ctx, "2026-11-09/cor2")
    assert f18["estado"] == "pendente" and f18["texto"] is None
    assert f18["mensagem"] == "O feedback deste treino ainda não foi gerado. Toque em Atualizar para ver se já está pronto."
    f12 = _fb(ctx, "2026-11-05/cor1")
    assert (f12["estado"], f12["checkin_aberto"], f12["mensagem"]) == ("sem_checkin", True, "Faça o check-in para ver o feedback.")
    f2 = _fb(ctx, "2026-11-01/cor1")
    assert (f2["estado"], f2["checkin_aberto"]) == ("sem_checkin", False)
    assert f2["mensagem"] == "O prazo do check-in deste treino acabou, então ele fica sem feedback."
    assert _fb(ctx, "2026-11-03/out1") is None  # multiesporte_pai: sem cartão
    assert _fb(ctx, "2026-11-03/out2") is None  # troca


# ---------------------------------------------------------------- worker, sem provedor e com o falso (passos 7 e 8)

def test_06_sem_provedor_configurado_o_worker_so_conta(ctx, capsys):
    """Item: sem provedor, nada é inventado: `indisponivel` com o motivo e só contagens na saída."""
    from app.llm import Redator

    from worker.gerar_feedback import main

    codigo = main(["--atleta", ATLETA], redator=Redator(None, None, None), session_factory=ctx["fabrica"])
    out = _saida(capsys)
    assert codigo == 0
    assert "feedback: gerados=0 sem_feedback=9 ignorados=0 adiados=0 erros=0" in out and "provedor_nao_configurado=9" in out
    f = _fb(ctx, "2026-11-09/cor2")
    assert (f["estado"], f["motivo"], f["mensagem"]) == ("indisponivel", "provedor_nao_configurado", "O feedback automático não está ligado neste app.")
    assert _linhas_fb(ctx) == [("sem_feedback", "provedor_nao_configurado", 9)]


def test_07_gera_em_duas_rodadas_e_e_idempotente(ctx, capsys):
    """Item: provedor falso, sem rede; o limite de chamadas é por execução; sem mudança nova, nenhuma chamada."""
    _, r1, f1 = _gerar(ctx, "--limite", "3")
    assert "gerados=3 sem_feedback=0 ignorados=0 adiados=6 erros=0" in _saida(capsys) and f1.chamadas == 3
    _, r2, f2 = _gerar(ctx)
    out = _saida(capsys)
    assert "gerados=5 sem_feedback=1 ignorados=3 adiados=0 erros=0" in out and "texto_reprovado=1" in out and "dor_regra=1" in out
    assert f2.chamadas == 6
    _, r3, f3 = _gerar(ctx)
    assert "gerados=0 sem_feedback=1 ignorados=8 adiados=0 erros=0" in _saida(capsys)
    assert f3.chamadas == 1  # so o reprovado e tentado de novo
    assert _linhas_fb(ctx) == [("pronto", None, 8), ("sem_feedback", "texto_reprovado", 1)]


def test_08_get_pronto_com_origem_teste_e_reprovado_sem_texto(ctx):
    """Item: texto pronto na API com a origem; texto reprovado nunca chega ao app."""
    ids = _ids(ctx)
    for f in ("2026-10-15/cor1", "2026-11-03/nat1", "2026-11-06/out1", "2026-11-07/cor1", "2026-11-08/nat1", "2026-11-08/cic1",
              "2026-11-09/cor1", "2026-11-09/cor2"):
        fb = _fb(ctx, f)
        assert (fb["estado"], fb["origem"], fb["texto"]) == ("pronto", "teste", TEXTO_OK), f
        assert fb["mensagem"] is None and fb["motivo"] is None
    dor = _fb(ctx, "2026-11-03/cic1")  # o check-in tem o atalho Dor
    assert (dor["estado"], dor["motivo"], dor["texto"], dor["origem"]) == ("indisponivel", "texto_reprovado", None, None)
    assert dor["mensagem"] == "Ainda não foi possível gerar o feedback deste treino. Uma nova tentativa será feita mais tarde."
    assert _sql(ctx, "select texto from feedback_treino where estado = 'sem_feedback'") == [(None,)]  # nada do reprovado no banco
    corpo = ctx["client"].get(f"/atletas/1/atividades/{ids['2026-11-03/cic1']}").text
    assert "dor_regra" not in corpo and "versao_fatos" not in corpo and "fatos_treino" not in corpo and "provedor" not in corpo.lower()


# ---------------------------------------------------------------- checagens (item 3)

def test_09_checagens_textos_bons_passam_e_ruins_reprovam_com_o_motivo():
    """Item: todo número no pacote, sem linguagem proibida; texto ruim sintético reprova com o motivo certo."""
    from app.explicacao import checagens as ck

    for i, (caso, texto) in T9.BONS.items():
        r = ck.checar_texto(O9.PACOTES[caso], texto)
        assert r.aprovado, (i, r.motivos)
    for i, (caso, texto, motivo, _p) in T9.RUINS.items():
        r = ck.checar_texto(O9.PACOTES[caso], texto)
        assert not r.aprovado and motivo in r.motivos, (i, motivo, r.motivos)


def test_10_texto_ruim_do_provedor_e_descartado_e_nunca_grava_nem_chega_ao_app(ctx, capsys):
    """Item: texto reprovado é descartado; o motivo é só um código."""
    from app.llm.camada import ProvedorFalso

    antes = _sql(ctx, "select count(*) from feedback_treino")
    _gerar(ctx, "--refazer", "--limite", "20", provedor=ProvedorFalso(modo="ruim"))
    out = _saida(capsys)
    assert "gerados=0" in out and "texto_reprovado" in out
    assert "99 km" not in out and "professor" not in out  # nunca o texto na saida
    # `--refazer` com texto ruim: o que estava pronto e em dia é mantido (o texto bom continua no GET)
    assert "mantidos=" in out
    assert _fb(ctx, "2026-11-09/cor2")["texto"] == TEXTO_OK
    assert _sql(ctx, "select count(*) from feedback_treino") == antes
    assert _sql(ctx, "select count(*) from feedback_treino where texto like '%99 km%'") == [(0,)]


def test_11_refazer_com_texto_bom_refaz_o_que_esta_pronto(ctx, capsys):
    _, _, f = _gerar(ctx, "--refazer", "--limite", "2")
    out = _saida(capsys)
    assert "gerados=2" in out and "adiados=7" in out and f.chamadas == 2


# ---------------------------------------------------------------- camada de LLM, sem log, texto livre (itens 4 e 5)

def test_12_limite_do_provedor_para_a_execucao_sem_gravar_linha(ctx, capsys):
    """Item: camada trocável; recusa por limite para a execução e o resto entra na próxima."""
    from app.llm.camada import ProvedorFalso

    antes = _linhas_fb(ctx)
    codigo, redator, f = _gerar(ctx, "--refazer", provedor=ProvedorFalso(modo="limite"))
    out = _saida(capsys)
    assert codigo == 0 and redator.limite_do_provedor and f.chamadas == 1  # parou na primeira recusa
    assert "adiados=" in out and "limite de requisicoes" in out
    assert _linhas_fb(ctx) == antes  # nenhuma linha gravada pelo limite


def test_13_erro_e_tempo_limite_viram_sem_feedback_com_o_motivo(ctx, capsys):
    from app.llm.camada import ProvedorFalso

    _put(ctx, "2026-11-09/cor2", CHECKINS["2026-11-09/cor2"])  # mesmo corpo: o feedback so desatualiza se algo mudar
    for modo, motivo in (("erro", "provedor_erro"), ("tempo", "provedor_tempo_limite")):
        _put(ctx, "2026-11-09/cor2", {**CHECKINS["2026-11-09/cor2"], "pse": 3 if modo == "erro" else 4})
        _gerar(ctx, provedor=ProvedorFalso(modo=modo))
        assert motivo in _saida(capsys), modo
        fb = _fb(ctx, "2026-11-09/cor2")
        assert fb["estado"] == "indisponivel" and fb["texto"] is None, modo
    _put(ctx, "2026-11-09/cor2", CHECKINS["2026-11-09/cor2"])
    _gerar(ctx)  # a proxima execucao conserta
    _saida(capsys)
    assert _fb(ctx, "2026-11-09/cor2")["estado"] == "pronto"


def test_14_o_prompt_so_leva_o_pacote_e_o_texto_livre_nunca_vai_ao_provedor(ctx, capsys):
    """Item: o texto livre da observação nunca vai ao provedor; nada em log nem na saída."""
    from app.llm.camada import ProvedorFalso

    vistos: list[str] = []

    class Espia(ProvedorFalso):
        def completar(self, sistema, usuario, timeout_s):
            vistos.append(sistema + "\n" + usuario)
            return super().completar(sistema, usuario, timeout_s)

    _put(ctx, "2026-11-09/cor2", {**CHECKINS["2026-11-09/cor2"], "nada_a_relatar": False, "atalhos": ["cansaco"], "texto": MARCADOR})
    _gerar(ctx, provedor=Espia(texto=TEXTO_OK))
    out = _saida(capsys)
    assert len(vistos) == 2  # o desse check-in e o da atividade 8 (reprovada por dor, tentada de novo a cada execucao)
    assert any('"cansaco"' in v for v in vistos) or any("cansaco" in v for v in vistos)
    for v in vistos:
        assert MARCADOR not in v and "fatos_treino@2" in v  # o pacote vai; o texto livre, o nome e a data nao
        assert "Atleta Fictício" not in v and "2026-11-0" not in v
    assert MARCADOR not in out
    _put(ctx, "2026-11-09/cor2", CHECKINS["2026-11-09/cor2"])  # volta o check-in do guia
    _gerar(ctx)
    _saida(capsys)


def test_15_nada_do_pacote_nem_do_texto_vai_para_o_log(ctx, caplog, capsys):
    caplog.set_level(logging.DEBUG)
    _gerar(ctx, "--refazer", "--limite", "2")
    ctx["client"].get(f"/atletas/1/atividades/{_ids(ctx)['2026-11-09/cor2']}")
    assert TEXTO_OK.split("\n")[0] not in caplog.text and "fatos_treino" not in caplog.text and MARCADOR not in caplog.text
    assert TEXTO_OK.split("\n")[0] not in _saida(capsys)


def test_16_so_a_camada_app_llm_chama_um_provedor():
    """Item: LLM só pela camada trocável (LiteLLM): nenhum outro módulo importa um cliente de provedor."""
    achados = []
    for pasta in (API / "app", WORKER / "worker"):
        for arq in pasta.rglob("*.py"):
            if arq.parent.name == "llm":
                continue
            if re.search(r"^\s*(import|from)\s+(litellm|openai|groq|anthropic)\b", arq.read_text(encoding="utf-8"), re.M):
                achados.append(str(arq.relative_to(RAIZ)))
    assert achados == []
    assert "litellm" in (API / "app" / "llm" / "camada.py").read_text(encoding="utf-8")
    assert "llm_provider" in (API / "app" / "config.py").read_text(encoding="utf-8")


# ---------------------------------------------------------------- editar e apagar o check-in (passo 9)

def test_17_editar_o_checkin_desatualiza_e_o_texto_antigo_nao_e_devolvido(ctx, capsys):
    """Item: o feedback acompanha o check-in."""
    _put(ctx, "2026-11-09/cor2", {"pse": 6, "sensacao": 3, "nada_a_relatar": True, "atalhos": []})
    fb = _fb(ctx, "2026-11-09/cor2")
    assert fb["estado"] == "desatualizado" and fb["texto"] is None and fb["origem"] is None
    assert fb["mensagem"] == "Você editou o check-in. O feedback será refeito."
    _gerar(ctx)
    assert "gerados=1" in _saida(capsys)
    assert _fb(ctx, "2026-11-09/cor2")["estado"] == "pronto"


def test_18_apagar_o_checkin_apaga_o_feedback(ctx):
    """Item: o feedback é apagado com o check-in (dado de saúde, Meta 6)."""
    n = _sql(ctx, "select count(*) from feedback_treino")[0][0]
    r = ctx["client"].delete(f"/atletas/1/atividades/{_ids(ctx)['2026-11-09/cor1']}/checkin")
    assert r.status_code == 204
    fb = _fb(ctx, "2026-11-09/cor1")
    assert (fb["estado"], fb["checkin_aberto"]) == ("sem_checkin", True)
    assert _sql(ctx, "select count(*) from feedback_treino")[0][0] == n - 1
    assert _sql(ctx, "select count(*) from feedback_treino where checkin_id not in (select id from checkin_treino)") == [(0,)]


def test_19_worker_apagar_checkin_leva_os_feedbacks_junto(ctx):
    """Item: feedback apagado com o check-in, também pelo worker (LGPD)."""
    n = _sql(ctx, "select count(*) from checkin_treino")[0][0]
    f = _sql(ctx, "select count(*) from feedback_treino")[0][0]
    assert n == 8 and f >= 7
    out = _worker(ctx, "worker.apagar_checkin")
    assert f"checkins: apagados={n}" in out and "feedbacks: apagados=" in out
    assert _sql(ctx, "select (select count(*) from checkin_treino), (select count(*) from feedback_treino), (select count(*) from atividade)") == [(0, 0, 18)]
    assert "checkins: apagados=0" in _worker(ctx, "worker.apagar_checkin")
    assert _fb(ctx, "2026-11-09/cor2")["estado"] == "sem_checkin"


def test_20_worker_na_linha_de_comando_com_llm_provider_falso_gera_feedback(ctx):
    """Item: o guia roda o worker com LLM_PROVIDER=falso (passo 8). O texto fixo passa nas checagens (#361)."""
    for f in ("2026-11-09/cor2", "2026-11-08/nat1"):
        _put(ctx, f, CHECKINS[f])
    out = _worker(ctx, "worker.gerar_feedback", env_extra={"LLM_PROVIDER": "falso"})
    assert "gerados=0" not in out
    assert _fb(ctx, "2026-11-09/cor2")["estado"] == "pronto"


def test_21_a_saida_do_worker_so_tem_contagens_e_nada_tentou_a_rede(ctx):
    for s in ctx["saidas"]:
        assert MARCADOR not in s and TEXTO_OK.split("\n")[0] not in s and "conexao de rede" not in s


# ---------------------------------------------------------------- contrato, documentos e cartão (item 6)

def test_22_openapi_declara_o_feedback_e_o_cliente_esta_regerado(ctx):
    """Item: endpoints no OpenAPI, adendo da ADR 0004 e cliente regerado; cartão com teste."""
    spec = ctx["app"].openapi()
    esquemas = spec["components"]["schemas"]
    fb = esquemas["FeedbackOut"]
    assert {"estado", "texto", "origem", "mensagem", "checkin_aberto", "motivo"} <= set(fb["properties"])
    assert any("feedback" in e.get("properties", {}) and e["properties"]["feedback"] for e in esquemas.values() if "checkin_aberto" in e.get("properties", {}))
    gravado = json.loads((RAIZ / "packages" / "api-client" / "openapi.json").read_text(encoding="utf-8"))
    assert gravado["components"]["schemas"]["FeedbackOut"] == fb
    schema_ts = (RAIZ / "packages" / "api-client" / "src" / "schema.d.ts").read_text(encoding="utf-8")
    assert "FeedbackOut" in schema_ts
    for estado in ESTADOS_PUBLICOS:
        assert estado in json.dumps(fb)  # os cinco estados estao no contrato
    adr4 = (RAIZ / "docs" / "decisoes" / "0004-contrato-tela-evolucao.md").read_text(encoding="utf-8")
    assert "Adendo 10" in adr4 and "feedback" in adr4
    assert (RAIZ / "apps" / "mobile" / "__tests__" / "CartaoFeedback.test.tsx").exists()


def test_23_adr_0013_e_notas_da_meta_existem():
    """Item: ADR 0013 com as decisões do Angelo; nota de fatos_treino e de checagens."""
    adr = (RAIZ / "docs" / "decisoes" / "0013-feedback-automatico.md").read_text(encoding="utf-8")
    assert "fatos_treino@1" in adr and "A confirmar" in adr
    for nota in ("fatos-treino.md", "fatos-treino-oraculo.md", "checagens-feedback.md"):
        assert (RAIZ / "docs" / "metricas" / nota).exists(), nota
    assert (RAIZ / "docs" / "design" / "telas" / "feedback.md").exists()
