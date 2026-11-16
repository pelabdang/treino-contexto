"""QA de ponta a ponta da Meta 10, a recuperação (sono, VFC e FC de repouso) no contexto do treino (issue #378, ADR 0014).

Segue o roteiro de `docs/produto/meta-10-como-rodar.md`: migrações (alembic, até o head lido do ScriptDirectory) -> as 18 atividades
sintéticas de `tests/fixtures/meta8/` e os check-ins (como o `carregar.py` do guia) -> `worker.gerar_feedback` sem nenhuma noite ->
`worker.buscar_recuperacao --fixtures` (cliente Garmin falso, sem rede, leitor de verdade) -> o bloco `recuperacao` do pacote
`fatos_treino@2` -> o feedback que desatualiza quando a noite chega -> o texto com a linha da recuperação pelas checagens reais ->
`--refazer` que reconfere o texto mantido (#407) -> o clima que chega depois (#409, migração 0015) -> `worker.apagar_recuperacao`.
Num SQLite temporário; só dado sintético; sem rede (guarda de socket, como nos e2e anteriores).

Um teste por item do critério de pronto da Meta 10 (`docs/produto/roadmap.md`); o item de cada teste está no docstring.
Os testes seguem a ordem do arquivo e dividem o mesmo banco, então a ordem importa.

O que este arquivo NÃO cobre (exige olho humano, rede ou dado real): o cartão na tela (Chrome em tamanho de celular, #369), o celular de
verdade, o leitor de tela, o provedor de verdade e a conta real do Garmin. Não verificado aqui.
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


def _head_do_alembic() -> str:
    """O head das migracoes lido do alembic: o teste nao quebra a cada migracao nova."""
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    cfg = Config(str(RAIZ / "services" / "api" / "alembic.ini"))
    cfg.set_main_option("script_location", str(RAIZ / "services" / "api" / "alembic"))
    return ScriptDirectory.from_config(cfg).get_current_head()


_HEAD = _head_do_alembic()
PASTA8 = RAIZ / "tests" / "fixtures" / "meta8"
PASTA9 = RAIZ / "tests" / "fixtures" / "meta9"
PASTA10 = RAIZ / "tests" / "fixtures" / "meta10"
NOITES_R01 = PASTA10 / "noites_r01"
API = RAIZ / "services" / "api"
WORKER = RAIZ / "services" / "worker"
ATLETA = "Atleta Fictício"
FORA_DO_PRAZO = "2026-10-15/cor1"
T18 = "2026-11-09/cor2"  # a corrida de 45 min do dia do treino (id 18): recebe a noite do caso R01

TEXTO_OK = (
    "Este é um texto de teste do provedor falso.\n"
    "Esta linha foi escrita só para os testes.\n"
    "Nenhum dado real é usado aqui."
)
# Texto com a linha da recuperação (o provedor falso fixo não fala de sono). Os números são os do pacote do treino 18 + caso R01.
TEXTO_REC = (
    "Foram 45 min de corrida, com carga pela PSE de 270 UA.\n"
    "Na noite anterior você dormiu 5 h 45 min, 1 h 30 min abaixo do seu normal de 7 h 15 min.\n"
    "A FC de repouso foi 58 bpm, 6 bpm acima do seu normal de 52 bpm, e a VFC, 41 ms, dentro do seu normal.\n"
    "Você marcou esforço 6, sensação 4 (bem) e os atalhos cansaço e trabalho/estresse."
)
VALORES_DA_NOITE = ("5 h 45 min", "7 h 15 min", "58 bpm", "41 ms", "52 bpm")

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


O9 = _carregar("oraculo_meta9_e2e10", PASTA9 / "oraculo.py")
OR = _carregar("oraculo_meta10_e2e10", PASTA10 / "oraculo_fatos_recuperacao.py")
TR = _carregar("textos_meta10_e2e10", PASTA10 / "textos_recuperacao.py")
FIXTURES = json.loads((PASTA8 / "atividades.json").read_text(encoding="utf-8"))["atividades"]
CHECKINS = json.loads((PASTA8 / "checkins.json").read_text(encoding="utf-8"))


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
    """O passo 3 do guia: 18 atividades e o check-in de 15/10 (fora do prazo de criacao)."""
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

    base = tmp_path_factory.mktemp("e2e_meta10")
    guarda = base / "guarda"
    guarda.mkdir()
    (guarda / "sitecustomize.py").write_text(GUARDA, encoding="utf-8")
    url = f"sqlite:///{base / 'treino.db'}"
    assert url.startswith("sqlite:///")  # nunca o Postgres de ninguem
    env = {**os.environ, "DATABASE_URL": url, "PYTHONPATH": str(guarda)}
    for k in ("VIRTUAL_ENV", "LLM_PROVIDER", "LLM_MODEL", "GROQ_API_KEY", "GARMIN_EMAIL", "GARMIN_PASSWORD"):
        env.pop(k, None)  # nenhum provedor de verdade nem conta, mesmo com um .env na maquina de quem roda
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
        yield {"client": TestClient(app), "eng": eng, "env": env, "app": app, "saidas": [], "fabrica": sessionmaker(eng),
               "prompts": []}
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
    r = ctx["client"].get(f"/atletas/1/atividades/{_ids(ctx)[f]}")
    assert r.status_code == 200, (f, r.text[:200])
    return r.json()["feedback"]


def _put(ctx, f, corpo):
    r = ctx["client"].put(f"/atletas/1/atividades/{_ids(ctx)[f]}/checkin", json=corpo)
    assert r.status_code == 200, (f, r.status_code, r.text[:300])


def _linhas_fb(ctx):
    return _sql(ctx, "select estado, motivo, count(*) from feedback_treino group by 1, 2 order by 1, 2")


def _saida(capsys):
    c = capsys.readouterr()
    return c.out + c.err


class Espia:
    """Provedor falso que guarda o prompt do usuario e devolve `TEXTO_REC` so para o treino com a noite do caso R01."""

    def __init__(self, ctx, texto_rec=TEXTO_REC, modo="bom"):
        from app.llm.camada import ProvedorFalso

        self.base = ProvedorFalso(texto=TEXTO_OK, modo=modo)
        self.ctx, self.texto_rec = ctx, texto_rec

    @property
    def chamadas(self):
        return self.base.chamadas

    def completar(self, sistema, usuario, timeout_s):
        self.ctx["prompts"].append(sistema + "\n" + usuario)
        if self.base.modo == "bom" and "5 h 45 min" in usuario:
            self.base.chamadas += 1
            return self.texto_rec
        return self.base.completar(sistema, usuario, timeout_s)


def _gerar(ctx, *args, provedor=None):
    """`worker.gerar_feedback` em processo, com o provedor falso e a checagem REAL. Devolve (codigo, redator, provedor)."""
    from app.llm import Redator
    from app.llm.camada import ProvedorFalso

    from worker.gerar_feedback import main

    falso = provedor or ProvedorFalso(texto=TEXTO_OK)
    redator = Redator(falso, "falso", "falso", timeout_s=5, limite_chamadas=20)
    codigo = main(["--atleta", ATLETA, *args], redator=redator, session_factory=ctx["fabrica"])
    return codigo, redator, falso


def _buscar(ctx, *args, cliente=None, hoje=None):
    from worker.buscar_recuperacao import main

    return main(["--atleta", ATLETA, *args], cliente=cliente, session_factory=ctx["fabrica"], hoje=hoje, pausa=lambda s: None)


def _worker(ctx, modulo, *args, esperado=0):
    r = _roda(["-m", modulo, "--atleta", ATLETA, *args], ctx["env"], esperado=esperado)
    ctx["saidas"].append(r.stdout + r.stderr)
    return r.stdout + r.stderr


def _pacote(ctx, fonte_id):
    from app.db.models import Atividade
    from app.servicos.feedback_fatos import fatos_da_atividade

    with ctx["fabrica"]() as s:
        a = s.get(Atividade, _ids(ctx)[fonte_id])
        return fatos_da_atividade(s, a, a.checkin)


def _pacote_com(caso):
    """O F01 da Meta 9 com o bloco `recuperacao` de um caso do oraculo da Meta 10."""
    bloco = TR.BLOCOS_EXTRA[caso] if caso in TR.BLOCOS_EXTRA else OR.CASOS[caso]["bloco"]
    return {**O9.PACOTES["F01"], "recuperacao": bloco}


# ---------------------------------------------------------------- migração e carga (passos 2 e 3)

def test_01_migracoes_ate_o_head_criam_recuperacao_dia_e_as_colunas_do_feedback(ctx):
    """Item: ADR 0014, um registro por noite com versão (migração 0014); #409, `clima_visto` (migração 0015)."""
    assert _sql(ctx, "select version_num from alembic_version") == [(_HEAD,)]
    assert int(_HEAD) >= 15
    cols = {c[1] for c in _sql(ctx, "pragma table_info(recuperacao_dia)")}
    assert {"atleta_id", "noite", "origem", "sono_s", "vfc_ms", "fc_repouso_bpm", "versao_leitura", "importado_em"} <= cols
    unicos = [r for r in _sql(ctx, "pragma index_list(recuperacao_dia)") if r[2]]
    assert unicos, "recuperacao_dia precisa de um indice unico por atleta, origem e noite"
    fcols = {c[1] for c in _sql(ctx, "pragma table_info(feedback_treino)")}
    assert {"recuperacao_importada_em", "clima_visto", "versao_checagens"} <= fcols


def test_02_carga_das_18_atividades_e_dos_checkins(ctx):
    atleta, desloc = _carrega_fixtures(ctx["eng"])
    print(f"deslocamento {desloc} dias")
    assert atleta == 1 and _sql(ctx, "select count(*) from atividade") == [(18,)]
    for f, corpo in CHECKINS.items():
        if f != FORA_DO_PRAZO:
            _put(ctx, f, corpo)
    assert _sql(ctx, "select count(*) from checkin_treino") == [(9,)]
    assert _ids(ctx)[T18] == 18


# ---------------------------------------------------------------- sem noite nenhuma (passo 5)

def test_03_sem_nenhuma_noite_o_pacote_diz_sem_dado_e_o_feedback_nao_quebra(ctx, capsys):
    """Item: a falta de dado de sono nunca vira número inventado; atleta sem noite não quebra o feedback."""
    p = _pacote(ctx, T18)
    assert p["versao"] == "fatos_treino@2"
    assert p["recuperacao"] == {"versao": "recuperacao@1", "estado": "sem_dado", "motivo": "sem_noite"}
    _gerar(ctx)
    out = _saida(capsys)
    assert "gerados=8 sem_feedback=1 ignorados=0 adiados=0 erros=0" in out and "dor_regra=1" in out
    assert _sql(ctx, "select count(*) from feedback_treino where recuperacao_importada_em is not null") == [(0,)]
    assert _fb(ctx, T18)["estado"] == "pronto"


def test_04_texto_sobre_sono_com_pacote_sem_dado_e_barrado_pelas_checagens_reais(ctx):
    """Item: prompt e checagens com versão nova; a frase pronta só passa em `sem_dado` com `sem_noite`."""
    from app.explicacao import checagens as ck

    assert ck.VERSAO.startswith("checagens_feedback@")
    pacote = _pacote(ctx, T18)  # sem_dado / sem_noite, do banco
    inventado = TEXTO_REC.replace("45 min de corrida, com carga pela PSE de 270 UA", "45 min de corrida")
    assert "recuperacao_sem_pacote" in ck.checar_texto(pacote, inventado).motivos
    assert ck.checar(pacote, TEXTO_OK) is None  # o texto do provedor falso, que nao fala de sono, passa
    frase = "Sem dado de sono, VFC e FC de repouso da noite anterior."
    assert ck.checar_texto(pacote, TEXTO_OK + "\n" + frase).motivos == ()  # a frase pronta e a unica fala aceita


# ---------------------------------------------------------------- busca com cliente falso (passo 6)

def test_05_busca_com_cliente_garmin_falso_grava_as_noites_e_e_idempotente(ctx, capsys):
    """Item: testes sem rede (cliente Garmin falso); um registro por noite, idempotente, saída só de contagens."""
    assert _buscar(ctx, "--fixtures", str(NOITES_R01), "--alinhar-ao-treino", T18) == 0
    out1 = _saida(capsys)
    assert "recuperacao: noites_novas=15 atualizadas=0 iguais=0 sem_dado=0 falhas=0" in out1
    assert _buscar(ctx, "--fixtures", str(NOITES_R01), "--alinhar-ao-treino", T18) == 0
    out2 = _saida(capsys)
    assert "recuperacao: noites_novas=0 atualizadas=0 iguais=15 sem_dado=0 falhas=0" in out2
    assert _sql(ctx, "select count(*), min(versao_leitura), max(versao_leitura) from recuperacao_dia") == [(15, "fixture", "fixture")]
    for out in (out1, out2):  # so contagens: nem valor nem data
        assert not re.search(r"\d{4}-\d{2}-\d{2}", out) and not any(v in out for v in VALORES_DA_NOITE)


def test_06_o_bloco_recuperacao_do_banco_bate_com_o_oraculo_a_mao(ctx):
    """Item: `recuperacao@1` comparada com o normal do atleta; `fatos_treino@2` com o bloco; oráculo à mão (caso R01)."""
    bloco = _pacote(ctx, T18)["recuperacao"]
    assert bloco == OR.CASOS["R01"]["bloco"]
    assert tuple(bloco) == OR.CHAVES_BLOCO_OK
    assert [m["chave"] for m in bloco["medidas"]] == ["sono", "vfc", "fc_repouso"]
    assert all(tuple(m) == OR.CHAVES_MEDIDA for m in bloco["medidas"])
    bruto = json.dumps(bloco)  # nada de data, serie, MAD, z ou mediana numerica
    assert not re.search(r"\d{4}-\d{2}-\d{2}", bruto) and "mad" not in bruto.lower() and "mediana" not in bruto.lower()
    # sem dado e sem inventar: treino antes da primeira noite e treino de dois dias antes (n = 12 < 14)
    assert _pacote(ctx, FORA_DO_PRAZO)["recuperacao"] == {"versao": "recuperacao@1", "estado": "sem_dado", "motivo": "fora_do_periodo"}
    aprendendo = _pacote(ctx, "2026-11-07/cor1")["recuperacao"]
    assert aprendendo["estado"] == "ok" and {m["estado"] for m in aprendendo["medidas"]} == {"aprendendo"}
    assert all(m["n"] == 12 and m["normal_texto"] is None and m["diferenca_texto"] is None for m in aprendendo["medidas"])


def test_07_fixtures_de_noites_nao_se_misturam_com_dado_real(ctx, capsys):
    """Item: regra do dado de saúde: `--fixtures` recusa atleta com noite que não é de fixture (e não grava)."""
    from app.db.models import Atleta, RecuperacaoDia

    with ctx["fabrica"]() as s:
        a = Atleta(nome="Outro Atleta Fictício")
        s.add(a)
        s.flush()
        s.add(RecuperacaoDia(atleta_id=a.id, noite=date(2030, 1, 1), origem="garmin_connect", sono_s=25000, versao_leitura="recuperacao_leitura@1",
                             importado_em=datetime.now(UTC)))
        s.commit()
    from worker.buscar_recuperacao import main

    codigo = main(["--atleta", "Outro Atleta Fictício", "--fixtures", str(NOITES_R01)], session_factory=ctx["fabrica"])
    assert codigo == 1 and "nao sao de fixture" in _saida(capsys)
    assert _sql(ctx, "select count(*) from recuperacao_dia where atleta_id = 2") == [(1,)]


# ---------------------------------------------------------------- o feedback acompanha a noite (passo 7)

def test_08_a_noite_que_chega_desatualiza_so_quem_tem_noite_na_janela(ctx):
    """Item: o feedback é refeito quando a noite chega (ADR 0014, 4b) e a API diz por quê."""
    msg = "Os dados da noite anterior foram atualizados. O feedback será refeito."
    for f in (T18, "2026-11-07/cor1", "2026-11-06/out1", "2026-11-08/nat1"):
        fb = _fb(ctx, f)
        assert (fb["estado"], fb["texto"], fb["mensagem"]) == ("desatualizado", None, msg), f
    antigo = _fb(ctx, FORA_DO_PRAZO)  # antes da primeira noite: fora_do_periodo dos dois lados, em dia
    assert antigo["estado"] == "pronto"
    dor = _fb(ctx, "2026-11-03/cic1")
    assert (dor["estado"], dor["motivo"]) == ("indisponivel", "texto_reprovado")


def test_09_gerar_refaz_o_desatualizado_soma_tentativa_e_e_idempotente(ctx, capsys):
    """Item: sem mudança nova, nenhuma chamada; noite nova soma 1 em `tentativas` e não barra o treino."""
    antes = dict(_sql(ctx, "select atividade_id, tentativas from feedback_treino f join checkin_treino c on c.id = f.checkin_id"))
    _, _, f1 = _gerar(ctx)
    out = _saida(capsys)
    assert re.search(r"gerados=7 sem_feedback=1 ignorados=1 adiados=0 erros=0", out), out
    _, _, f2 = _gerar(ctx)
    assert "gerados=0 sem_feedback=1 ignorados=8 adiados=0 erros=0" in _saida(capsys) and f2.chamadas == 1
    depois = dict(_sql(ctx, "select atividade_id, tentativas from feedback_treino f join checkin_treino c on c.id = f.checkin_id"))
    assert depois[18] == antes[18] + 1
    assert _sql(ctx, "select count(*) from feedback_treino where recuperacao_importada_em is not null") == [(8,)]  # os 7 prontos e o reprovado tentado de novo
    assert _fb(ctx, T18)["estado"] == "pronto"


# ---------------------------------------------------------------- o texto com a linha da recuperação (itens 4 e 5)

def test_10_texto_com_a_linha_da_recuperacao_passa_pelas_checagens_reais_e_chega_ao_get(ctx, capsys):
    """Item: a checagem real roda sobre o texto do provedor falso; recuperação lado a lado com o resultado, sem causa e sem conselho."""
    ctx["prompts"].clear()
    esp = Espia(ctx)
    _gerar(ctx, "--refazer", provedor=esp)
    out = _saida(capsys)
    assert "gerados=9" not in out and "erros=0" in out
    fb = _fb(ctx, T18)
    assert fb["estado"] == "pronto" and fb["origem"] == "teste"
    assert "5 h 45 min" in fb["texto"] and "1 h 30 min abaixo do seu normal de 7 h 15 min" in fb["texto"]
    assert fb["mensagem"] is None
    for causa in ("porque", "por causa", "deveria", "descanse"):
        assert causa not in fb["texto"].lower()


def test_11_ao_provedor_vai_so_a_comparacao_da_noite_nunca_a_serie_nem_datas(ctx):
    """Item: decisão 4 do Angelo: ao provedor de LLM vai só a comparação da noite anterior com o normal dele."""
    com_noite = [p for p in ctx["prompts"] if "5 h 45 min" in p]
    assert com_noite, "o prompt do treino 18 devia levar o bloco da recuperacao"
    for p in ctx["prompts"]:
        assert not re.search(r"\d{4}-\d{2}-\d{2}", p)  # nenhuma data
        assert "fatos_treino@2" in p and ATLETA not in p
        assert "sono_s" not in p and "vfc_ms" not in p and "importado_em" not in p
    assert '"normal_texto": "7 h 15 min"' in com_noite[0] or "7 h 15 min" in com_noite[0]
    assert not any(str(v) in com_noite[0] for v in (400 * 60, 410 * 60, 22200))  # nenhum valor da serie das 14 noites


def test_12_textos_bons_passam_e_ruins_reprovam_com_o_motivo_certo():
    """Item: prompt e checagens com versão nova e textos bons e ruins novos (6 bons e 25 ruins do guia, hoje mais)."""
    from app.explicacao import checagens as ck

    assert len(TR.BONS) >= 6 and len(TR.RUINS) >= 25
    for i, (caso, texto) in TR.BONS.items():
        assert ck.checar_texto(_pacote_com(caso), texto).motivos == (), i
    for i, (caso, texto, motivo) in TR.RUINS.items():
        assert motivo in ck.checar_texto(_pacote_com(caso), texto).motivos, (i, motivo)


def test_13_get_nao_devolve_a_noite_so_o_texto(ctx):
    """Item: sem rota que devolva `recuperacao_dia` (dado de saúde só no banco local)."""
    rotas = [r.path for r in ctx["app"].routes if hasattr(r, "path")]
    assert not any("recuperacao" in p for p in rotas)
    corpo = ctx["client"].get(f"/atletas/1/atividades/{_ids(ctx)[T18]}").text
    for proibido in ("recuperacao_dia", "sono_s", "vfc_ms", "fc_repouso_bpm", "recuperacao_importada_em", "fatos_treino", "versao_checagens"):
        assert proibido not in corpo


# ---------------------------------------------------------------- --refazer reconfere o texto mantido (#407)

def test_14_refazer_que_falha_reconfere_o_texto_mantido_e_derruba_o_reprovado(ctx, capsys):
    """Item: #407: `--refazer` só mantém o texto antigo se passar nas checagens atuais; senão `mantido_reprovado`."""
    from app.llm.camada import ProvedorFalso

    assert _fb(ctx, T18)["estado"] == "pronto"
    _sql(ctx, "update feedback_treino set texto = :t where checkin_id = (select id from checkin_treino where atividade_id = 18)",
         t="Você correu 99 km hoje.\nIsso foi por causa do calor, com certeza.\nDescanse amanhã.")
    _gerar(ctx, "--refazer", provedor=ProvedorFalso(modo="erro"))
    out = _saida(capsys)
    assert "mantido_reprovado=1" in out and "mantidos=" in out, out
    assert "99 km" not in out and "calor" not in out  # nunca o texto na saida
    fb = _fb(ctx, T18)
    assert (fb["estado"], fb["texto"], fb["motivo"]) == ("indisponivel", None, "texto_reprovado")
    assert _sql(ctx, "select count(*) from feedback_treino where texto like '%99 km%'") == [(0,)]
    # os que passam nas checagens atuais ficam, com a versao atual das checagens
    from app.explicacao import checagens as ck

    assert _fb(ctx, FORA_DO_PRAZO)["estado"] == "pronto"
    assert _sql(ctx, "select count(*) from feedback_treino where estado = 'pronto' and versao_checagens != :v", v=ck.VERSAO) == [(0,)]
    _gerar(ctx, provedor=Espia(ctx))  # a proxima execucao conserta (sem --refazer: a linha esta sem_feedback)
    _saida(capsys)
    assert _fb(ctx, T18)["estado"] == "pronto"


# ---------------------------------------------------------------- o clima que chega depois (#409, migração 0015)

def test_15_clima_que_chega_depois_desatualiza_o_feedback_com_a_mensagem_certa(ctx, capsys):
    """Item: #409: posição nova e clima `pendente` -> `ok` desatualizam o feedback uma vez cada; sem posição nada entra na fila."""
    from app.clima.cliente import ClimaMedio, ResultadoClima
    from app.servicos.clima import preencher_clima

    msg = "Os dados do clima foram atualizados. O feedback será refeito."
    f = FORA_DO_PRAZO  # treino de ha mais de 7 dias: o clima e consultado
    assert _fb(ctx, f)["estado"] == "pronto"
    _gerar(ctx)
    assert "gerados=0" in _saida(capsys)  # sem posicao: o clima nao desatualiza ninguem
    _sql(ctx, "update atividade set inicio_lat = -10, inicio_lon = -20 where id = :i", i=_ids(ctx)[f])
    fb = _fb(ctx, f)
    assert (fb["estado"], fb["texto"], fb["mensagem"]) == ("desatualizado", None, msg)
    _gerar(ctx)
    assert "gerados=1" in _saida(capsys) and _fb(ctx, f)["estado"] == "pronto"
    _gerar(ctx)
    assert "gerados=0" in _saida(capsys)

    class ClimaFalso:
        chamadas = 0

        def buscar(self, lat, lon, inicio, duracao_s):
            ClimaFalso.chamadas += 1
            return ResultadoClima("ok", ClimaMedio(19.0, 19.5, 60.0, 8.0))

    with ctx["fabrica"]() as s:
        rel = preencher_clima(s, ClimaFalso(), atleta_id=1, dormir=lambda s: None)
    assert rel.chamadas == 1 and ClimaFalso.chamadas == 1  # so a atividade com posicao
    assert _fb(ctx, f)["mensagem"] == msg  # pendente -> ok
    _gerar(ctx)
    assert "gerados=1" in _saida(capsys)
    pacote = _pacote(ctx, f)
    assert pacote["clima"]["estado"] == "ok" and pacote["clima"]["temperatura_c"] == 19.0
    _gerar(ctx)
    assert "gerados=0" in _saida(capsys)


def test_16_feedback_anterior_a_0015_nao_entra_por_clima(ctx, capsys):
    """Item: #409: `clima_visto` vazio (linha anterior à 0015) não desatualiza por clima; `--refazer` o põe no texto."""
    f = FORA_DO_PRAZO
    _sql(ctx, "update feedback_treino set clima_visto = null where checkin_id = (select id from checkin_treino where atividade_id = :i)", i=_ids(ctx)[f])
    _sql(ctx, "update clima_atividade set temperatura_c = 25.0 where atividade_id = :i", i=_ids(ctx)[f])
    assert _fb(ctx, f)["estado"] == "pronto"
    _gerar(ctx)
    assert "gerados=0" in _saida(capsys)
    _gerar(ctx, "--refazer")
    _saida(capsys)
    assert _sql(ctx, "select count(*) from feedback_treino where clima_visto is null") == [(0,)]


# ---------------------------------------------------------------- falta de dado, cliente falso proprio (item 5)

def test_17_noite_sem_dado_nunca_vira_numero_e_o_cliente_falso_nao_precisa_de_rede(ctx, capsys):
    """Item: a falta de dado de sono num dia nunca vira número inventado (cliente Garmin falso, sem login, sem rede)."""
    from worker.garmin_cliente import NoiteRecuperacao

    class ClienteFalso:
        def recuperacao(self, noite):
            if noite.day == 10:
                return NoiteRecuperacao(noite)  # resposta vazia
            if noite.day == 11:
                return NoiteRecuperacao(noite, sono_s=25200)  # so o sono: VFC e FC de repouso ficam vazias
            return NoiteRecuperacao(noite, sono_s=26000, vfc_ms=45.0, fc_repouso_bpm=52)

    _worker(ctx, "worker.apagar_recuperacao")  # outra conta de testes: comeca sem noites
    assert _buscar(ctx, "--desde", "2026-03-10", "--ate", "2026-03-12", cliente=ClienteFalso(), hoje=date(2026, 3, 20)) == 0
    out = _saida(capsys)
    assert "noites_novas=2 atualizadas=0 iguais=0 sem_dado=1 falhas=0" in out
    assert _sql(ctx, "select noite, sono_s, vfc_ms, fc_repouso_bpm, versao_leitura from recuperacao_dia where atleta_id = 1 order by noite") == [
        ("2026-03-11", 25200, None, None, "recuperacao_leitura@1"), ("2026-03-12", 26000, 45.0, 52, "recuperacao_leitura@1")]
    assert _sql(ctx, "select count(*) from recuperacao_dia where atleta_id = 1 and noite = '2026-03-10'") == [(0,)]  # nenhuma linha inventada
    assert _buscar(ctx, "--desde", "2026-03-10", "--ate", "2026-03-12", cliente=ClienteFalso(), hoje=date(2026, 3, 20)) == 0
    assert "noites_novas=0 atualizadas=0 iguais=2 sem_dado=1" in _saida(capsys)


# ---------------------------------------------------------------- apagar (passo 10)

def test_18_apagar_recuperacao_leva_as_noites_e_os_feedbacks_que_as_usaram(ctx):
    """Item: regra do dado de saúde: só banco local, comando para apagar (LGPD); check-ins e atividades ficam."""
    _sql(ctx, "delete from recuperacao_dia where atleta_id = 1")  # as noites do teste 17 (leitura normal) saem; volta o caso do guia
    assert _buscar(ctx, "--fixtures", str(NOITES_R01), "--alinhar-ao-treino", T18) == 0
    _gerar(ctx, provedor=Espia(ctx))  # os feedbacks refeitos com a noite
    n = _sql(ctx, "select count(*) from recuperacao_dia where atleta_id = 1")[0][0]
    usaram = _sql(ctx, "select count(*) from feedback_treino where recuperacao_importada_em is not null")[0][0]
    assert n == 15 and usaram >= 7
    out = _worker(ctx, "worker.apagar_recuperacao")
    assert f"recuperacao: apagadas={n}" in out and f"feedbacks: apagados={usaram}" in out
    assert _sql(ctx, "select (select count(*) from recuperacao_dia where atleta_id = 1), (select count(*) from checkin_treino), "
                     "(select count(*) from atividade)") == [(0, 9, 18)]
    assert _sql(ctx, "select count(*) from feedback_treino where recuperacao_importada_em is not null") == [(0,)]
    assert _fb(ctx, T18)["estado"] == "pendente"
    assert "recuperacao: apagadas=0" in _worker(ctx, "worker.apagar_recuperacao")
    assert _sql(ctx, "select count(*) from recuperacao_dia") == [(1,)]  # o outro atleta nao foi tocado


# ---------------------------------------------------------------- tudo sem rede e sem dado em saída (itens 5 e 6)

def test_19_a_saida_de_todos_os_comandos_so_tem_contagens(ctx):
    """Item: nada de valor, data nem texto em saída de comando; nada tentou a rede."""
    assert ctx["saidas"]
    for s in ctx["saidas"]:
        assert "conexao de rede" not in s
        assert not re.search(r"\d{4}-\d{2}-\d{2}", s) and not any(v in s for v in VALORES_DA_NOITE)


def test_20_nada_da_recuperacao_vai_para_o_log(ctx, caplog, capsys):
    """Item: dado de saúde nunca em log."""
    from app.llm.camada import ProvedorFalso  # noqa: F401

    caplog.set_level(logging.DEBUG)
    assert _buscar(ctx, "--fixtures", str(NOITES_R01), "--alinhar-ao-treino", T18) == 0
    _gerar(ctx, provedor=Espia(ctx))
    ctx["client"].get(f"/atletas/1/atividades/{_ids(ctx)[T18]}")
    saida = _saida(capsys)
    for valor in VALORES_DA_NOITE + ("fatos_treino", TEXTO_REC.split("\n")[1]):
        assert valor not in caplog.text and valor not in saida, valor


# ---------------------------------------------------------------- documentos, contrato e o que fica de fora (itens 1, 2 e 6)

def test_21_adr_0014_aceita_notas_da_metrica_e_guia_existem():
    """Item: ADR 0014 aceita, com "A confirmar" e padrões; notas da métrica e do oráculo; guia da meta."""
    adr = (RAIZ / "docs" / "decisoes" / "0014-recuperacao-diaria.md").read_text(encoding="utf-8")
    assert re.search(r"^status: aceita", adr, re.M) and "A confirmar" in adr
    for nota in ("recuperacao.md", "recuperacao-oraculo.md", "fatos-treino.md", "checagens-feedback.md"):
        assert (RAIZ / "docs" / "metricas" / nota).exists(), nota
    assert (RAIZ / "docs" / "produto" / "meta-10-como-rodar.md").exists()
    assert (RAIZ / "tests" / "fixtures" / "meta10" / "oraculo_fatos_recuperacao.py").exists()


def test_22_roteiro_e_guia_registram_que_celular_de_verdade_nao_foi_verificado():
    """Item: simulação no Chrome não é celular de verdade; o que não foi rodado fica escrito (decisão 6 do Angelo)."""
    roadmap = (RAIZ / "docs" / "produto" / "roadmap.md").read_text(encoding="utf-8")
    meta = roadmap[roadmap.index("### Meta 10:"):roadmap.index("### Meta 11:")]
    assert "simulação não é celular de verdade" in meta
    assert "celular de verdade" in meta and "decisão 6" in meta
    guia = (RAIZ / "docs" / "produto" / "meta-10-como-rodar.md").read_text(encoding="utf-8")
    assert "Não rodado aqui" in guia and "celular de" in guia and "verdade" in guia


def test_23_contrato_do_feedback_segue_sem_campos_novos_e_o_cartao_tem_teste_no_app():
    """Item: sem tela nova: a recuperação aparece só no texto do cartão que já existe."""
    spec = json.loads((RAIZ / "packages" / "api-client" / "openapi.json").read_text(encoding="utf-8"))
    campos = set(spec["components"]["schemas"]["FeedbackOut"]["properties"])
    assert campos == {"estado", "texto", "origem", "mensagem", "checkin_aberto", "motivo"}
    assert (RAIZ / "apps" / "mobile" / "__tests__" / "CartaoFeedback.test.tsx").exists()
