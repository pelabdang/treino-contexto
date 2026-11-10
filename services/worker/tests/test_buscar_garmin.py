"""worker.buscar_garmin (issue #335): cliente Garmin FALSO, FIT sintetico, nenhuma conexao de rede.

Nenhum teste entra em conta nenhuma. A guarda de socket derruba qualquer tentativa de abrir rede. Dados inventados.
"""

import io
import os
import socket
import subprocess
import sys
import types
import zipfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest
from app.db import models  # noqa: F401
from app.db.base import Base
from app.db.models import Atividade, Atleta
from app.ingestao.importacao import importar_fit
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from worker import garmin_cliente
from worker.buscar_garmin import main
from worker.garmin_cliente import (
    AtividadeGarmin,
    ClienteGarminConnect,
    ErroConfiguracao,
    ErroGarmin,
    ErroLimite,
    ErroLogin,
    ErroMfa,
    ErroRede,
    extrair_fit,
)

RAIZ = Path(__file__).resolve().parents[3]
FITS = RAIZ / "tests" / "fixtures" / "garmin" / "fit"
SENHA = "senha-sintetica-123"
EMAIL = "atleta@exemplo.invalid"
HOJE = date(2025, 4, 2)
RODAGEM = datetime(2025, 4, 2, 8, 0, tzinfo=timezone.utc)  # inicio de upload_rodagem_6km.fit
INTERVALADO = datetime(2025, 4, 1, 9, 0, tzinfo=timezone.utc)  # inicio de upload_intervalado_5x1km.fit


@pytest.fixture(autouse=True)
def sem_rede(monkeypatch):
    locais = ("localhost", "127.0.0.1", "::1")
    connect, create, getaddr = socket.socket.connect, socket.create_connection, socket.getaddrinfo

    def bloqueia():
        raise AssertionError("teste tentou abrir conexao de rede")

    def _host(e):
        return e[0] if isinstance(e, tuple) else e

    def connect_(self, e, *a, **k):
        if _host(e) not in locais and self.family != socket.AF_UNIX:
            bloqueia()
        return connect(self, e, *a, **k)

    def create_(e, *a, **k):
        if _host(e) not in locais:
            bloqueia()
        return create(e, *a, **k)

    def getaddr_(h, *a, **k):
        if h not in locais and h is not None:
            bloqueia()
        return getaddr(h, *a, **k)

    monkeypatch.setattr(socket.socket, "connect", connect_)
    monkeypatch.setattr(socket, "create_connection", create_)
    monkeypatch.setattr(socket, "getaddrinfo", getaddr_)


@pytest.fixture
def engine():
    eng = create_engine(os.environ.get("TEST_DATABASE_URL", "sqlite://"))
    Base.metadata.drop_all(eng)
    Base.metadata.create_all(eng)
    yield eng
    Base.metadata.drop_all(eng)
    eng.dispose()


@pytest.fixture
def factory(engine):
    return lambda: Session(engine)


@pytest.fixture
def atleta(engine):
    with Session(engine) as s:
        s.add(Atleta(nome="Atleta Ficticio"))
        s.commit()


@pytest.fixture
def pasta(tmp_path):
    return tmp_path / "fit"


def _zip(nome_fit: str) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("1_ACTIVITY.fit", (FITS / nome_fit).read_bytes())
    return buf.getvalue()


class Falso:
    """Cliente Garmin falso: lista fixa, FIT sintetico por id, e guarda as chamadas."""

    def __init__(self, atividades=None, erro_listar=None):
        self.atividades = atividades if atividades is not None else {
            1001: (RODAGEM, "upload_rodagem_6km.fit"),
            1002: (INTERVALADO, "upload_intervalado_5x1km.fit"),
        }
        self.erro_listar = erro_listar
        self.listagens, self.baixados = [], []

    def listar(self, desde, ate):
        self.listagens.append((desde, ate))
        if self.erro_listar:
            raise self.erro_listar
        return [AtividadeGarmin(i, v[0], v[2] if len(v) > 2 else None) for i, v in self.atividades.items()]

    def baixar_fit(self, atividade_id):
        self.baixados.append(atividade_id)
        return extrair_fit(_zip(self.atividades[atividade_id][1]))


def rodar(factory, cliente, pasta, *args):
    return main(["--atleta", "Atleta Ficticio", "--sem-clima", *args], cliente=cliente, session_factory=factory,
                hoje=HOJE, fit_dir=pasta)


def _n(engine):
    with Session(engine) as s:
        return s.scalar(select(func.count()).select_from(Atividade))


# ---------- importacao e idempotencia ----------

def test_importa_as_atividades_do_intervalo(engine, factory, atleta, pasta, capsys):
    cli = Falso()
    assert rodar(factory, cli, pasta, "--desde", "2025-04-01", "--ate", "2025-04-02") == 0
    assert cli.listagens == [(date(2025, 4, 1), date(2025, 4, 2))]
    assert _n(engine) == 2
    assert "listadas=2 ja_no_banco=0 inseridas=2" in capsys.readouterr().out
    with Session(engine) as s:  # mesmo caminho do upload: fonte, FIT guardado e classificacao
        for a in s.scalars(select(Atividade)):
            assert a.fonte == "fit_upload" and a.arquivo_bruto and (pasta / a.arquivo_bruto).is_file()
        assert s.scalars(select(Atividade).where(Atividade.fonte_id.is_not(None))).first().tipo_treino is not None


def test_padrao_e_hoje(engine, factory, atleta, pasta):
    cli = Falso({})
    assert rodar(factory, cli, pasta) == 0
    assert cli.listagens == [(HOJE, HOJE)]


def test_segunda_rodada_nao_duplica_e_nem_baixa(engine, factory, atleta, pasta, capsys):
    rodar(factory, Falso(), pasta)
    capsys.readouterr()
    segundo = Falso()
    assert rodar(factory, segundo, pasta) == 0
    assert _n(engine) == 2
    assert segundo.baixados == []  # ja no banco: nenhum download
    assert "ja_no_banco=2 inseridas=0" in capsys.readouterr().out


def test_atividade_ja_enviada_por_upload_nao_e_baixada(engine, factory, atleta, pasta):
    with Session(engine) as s:
        importar_fit(s, s.scalar(select(Atleta.id)), (FITS / "upload_rodagem_6km.fit").read_bytes(), pasta)
    cli = Falso()
    assert rodar(factory, cli, pasta) == 0
    assert cli.baixados == [1002]
    assert _n(engine) == 2


def test_baixada_que_ja_existe_nao_duplica(engine, factory, atleta, pasta):
    """Sem `startTimeGMT` o pre-filtro nao age; o `importar_fit` reconhece a atividade e nao duplica."""
    rodar(factory, Falso(), pasta)
    sem_hora = Falso({1001: (None, "upload_rodagem_6km.fit")})
    assert rodar(factory, sem_hora, pasta) == 0
    assert sem_hora.baixados == [1001] and _n(engine) == 2


def test_fit_que_nao_e_atividade_conta_falha_e_segue(engine, factory, atleta, pasta, capsys):
    cli = Falso({1: (RODAGEM, "upload_nao_atividade.fit"), 2: (INTERVALADO, "upload_intervalado_5x1km.fit")})
    assert rodar(factory, cli, pasta) == 6
    saida = capsys.readouterr()
    assert "inseridas=1" in saida.out and "falhas=1" in saida.out and _n(engine) == 1


def test_atleta_inexistente(engine, factory, pasta, capsys):
    assert rodar(factory, Falso(), pasta) == 1
    assert "atleta nao encontrado" in capsys.readouterr().err


def test_datas_invertidas(engine, factory, atleta, pasta):
    assert rodar(factory, Falso(), pasta, "--desde", "2025-04-03", "--ate", "2025-04-01") == 1


# ---------- inicio da lista diferente do inicio do FIT (#342) ----------

@pytest.mark.parametrize("deslocamento_s", [300, -300, 600])
def test_inicio_da_lista_deslocado_nao_baixa_de_novo(engine, factory, atleta, pasta, deslocamento_s):
    """Reproduz a #342: a lista traz o inicio diferente do FIT em mais de 60 s; antes, baixava a cada rodada."""
    rodar(factory, Falso({1001: (RODAGEM, "upload_rodagem_6km.fit")}), pasta)
    with Session(engine) as s:
        dur = s.scalar(select(Atividade.duracao_s))
    deslocada = Falso({1001: (RODAGEM + timedelta(seconds=deslocamento_s), "upload_rodagem_6km.fit", dur)})
    assert rodar(factory, deslocada, pasta) == 0
    assert deslocada.baixados == [] and _n(engine) == 1


def test_sem_duracao_na_lista_o_deslocado_ainda_baixa_mas_nao_duplica(engine, factory, atleta, pasta, capsys):
    rodar(factory, Falso({1001: (RODAGEM, "upload_rodagem_6km.fit")}), pasta)
    sem = Falso({1001: (RODAGEM + timedelta(seconds=300), "upload_rodagem_6km.fit")})
    assert rodar(factory, sem, pasta) == 0
    assert sem.baixados == [1001] and _n(engine) == 1
    assert "inicio da lista +300 s do FIT" in capsys.readouterr().out  # diagnostico: so numeros


def test_atividade_diferente_nao_e_confundida(engine, factory, atleta, pasta):
    rodar(factory, Falso({1001: (RODAGEM, "upload_rodagem_6km.fit")}), pasta)
    with Session(engine) as s:
        dur = s.scalar(select(Atividade.duracao_s))
    # outra atividade logo depois (mesma duracao, sem sobreposicao) e uma curta dentro da primeira (como uma filha)
    outra = Falso({
        1002: (RODAGEM + timedelta(seconds=dur + 600), "upload_intervalado_5x1km.fit", dur),
        1003: (RODAGEM + timedelta(seconds=600), "upload_esteira_4x1km.fit", dur / 5),
    })
    assert rodar(factory, outra, pasta) == 0
    assert sorted(outra.baixados) == [1002, 1003]


# ---------- erros do Garmin viram mensagem e codigo ----------

@pytest.mark.parametrize("erro,codigo,trecho", [
    (ErroLogin("o Garmin recusou o login; confira"), 2, "recusou o login"),
    (ErroMfa("o Garmin pediu o codigo de verificacao (MFA)"), 3, "MFA"),
    (ErroLimite("o Garmin limitou as requisicoes (429)"), 4, "429"),
    (ErroRede("nao foi possivel falar com o Garmin"), 5, "nao foi possivel falar"),
    (ErroConfiguracao("sem token salvo"), 1, "sem token"),
])
def test_erro_ao_listar(engine, factory, atleta, pasta, capsys, erro, codigo, trecho):
    assert rodar(factory, Falso(erro_listar=erro), pasta) == codigo
    err = capsys.readouterr().err
    assert err.startswith("erro: ") and trecho in err and "Traceback" not in err


def test_queda_de_rede_no_download_mantem_o_que_ja_entrou(engine, factory, atleta, pasta):
    class Cai(Falso):
        def baixar_fit(self, i):
            if self.baixados:
                raise ErroRede("nao foi possivel falar com o Garmin")
            return super().baixar_fit(i)

    assert rodar(factory, Cai(), pasta) == 5
    assert _n(engine) == 1
    assert rodar(factory, Falso(), pasta) == 0 and _n(engine) == 2  # a proxima rodada completa


# ---------- cliente real, com a biblioteca trocada por um falso ----------

class _Erros:
    class GarminConnectConnectionError(Exception): ...
    class GarminConnectTooManyRequestsError(Exception): ...
    class GarminConnectAuthenticationError(Exception): ...


def _biblioteca(login, dumps=None):
    chamadas = {"login": 0, "init": []}

    class Garmin:
        class ActivityDownloadFormat:
            ORIGINAL = "original"

        def __init__(self, **kw):
            chamadas["init"].append(kw)
            self.client = types.SimpleNamespace(dump=lambda p: (dumps if dumps is not None else []).append(p))

        def login(self, tokenstore=None):
            chamadas["login"] += 1
            return login(tokenstore)

        def resume_login(self, estado, codigo):
            chamadas.setdefault("resume", []).append((estado, codigo))
            if codigo != "123456":
                raise _Erros.GarminConnectAuthenticationError(f"codigo {codigo} recusado, {SENHA}")
            return None, None

        def get_activities_by_date(self, a, b, sortorder=None):
            return [{"activityId": 7, "startTimeGMT": "2025-04-02 08:00:00", "duration": 1800.5}, {"sem": "id"}]

        def download_activity(self, i, dl_fmt=None):
            assert dl_fmt == "original"
            return _zip("upload_rodagem_6km.fit")

    return types.SimpleNamespace(Garmin=Garmin, **vars(_Erros)), chamadas


@pytest.fixture
def env(tmp_path):
    return {"GARMIN_EMAIL": EMAIL, "GARMIN_PASSWORD": SENHA, "GARMINTOKENS": str(tmp_path / "token")}


def _instala(monkeypatch, mod):
    monkeypatch.setitem(sys.modules, "garminconnect", mod)


def test_login_com_credenciais_uma_tentativa_e_grava_o_token(monkeypatch, env, tmp_path):
    dumps: list[str] = []
    mod, ch = _biblioteca(lambda t: (None, None), dumps)
    _instala(monkeypatch, mod)
    cli = ClienteGarminConnect.entrar(env)
    assert ch["login"] == 1 and dumps == [str(tmp_path / "token")]
    assert ch["init"][0]["return_on_mfa"] is True and ch["init"][0]["retry_attempts"] == 1
    assert cli.listar(HOJE, HOJE) == [AtividadeGarmin(7, RODAGEM, 1800.5)]  # item sem activityId e ignorado
    assert cli.baixar_fit(7) == (FITS / "upload_rodagem_6km.fit").read_bytes()


def test_sem_token_e_sem_credenciais(monkeypatch, tmp_path):
    mod, ch = _biblioteca(lambda t: (None, None))
    _instala(monkeypatch, mod)
    with pytest.raises(ErroConfiguracao):
        ClienteGarminConnect.entrar({"GARMINTOKENS": str(tmp_path / "token")})
    assert ch["login"] == 0  # nem tentou


def test_com_token_salvo_nao_precisa_de_credenciais(monkeypatch, tmp_path):
    (tmp_path / "token").mkdir()
    (tmp_path / "token" / "garmin_tokens.json").write_text("{}")
    mod, ch = _biblioteca(lambda t: (None, None))
    _instala(monkeypatch, mod)
    ClienteGarminConnect.entrar({"GARMINTOKENS": str(tmp_path / "token")})
    assert ch["login"] == 1 and ch["init"][0]["email"] is None


def test_mfa_com_terminal_e_codigo_certo_grava_o_token(monkeypatch, env, tmp_path):
    dumps: list[str] = []
    mod, ch = _biblioteca(lambda t: ("needs_mfa", {"estado": "x"}), dumps)
    _instala(monkeypatch, mod)
    perguntas = []
    ClienteGarminConnect.entrar(env, ler_codigo=lambda: perguntas.append(1) or "123456")
    assert perguntas == [1] and ch["login"] == 1
    assert ch["resume"] == [({"estado": "x"}, "123456")]
    assert dumps == [str(tmp_path / "token")]


def test_mfa_codigo_errado_sai_com_3_e_nao_vaza(monkeypatch, env, capsys, caplog):
    dumps: list[str] = []
    mod, ch = _biblioteca(lambda t: ("needs_mfa", {}), dumps)
    _instala(monkeypatch, mod)
    with caplog.at_level("DEBUG"), pytest.raises(ErroMfa) as e:
        ClienteGarminConnect.entrar(env, ler_codigo=lambda: "999999")
    assert "999999" not in str(e.value) and SENHA not in str(e.value) and "999999" not in caplog.text
    assert dumps == [] and len(ch["resume"]) == 1  # uma pergunta, uma tentativa, nada gravado


def test_mfa_sem_terminal_nao_pergunta(monkeypatch, env):
    mod, ch = _biblioteca(lambda t: ("needs_mfa", {}))
    _instala(monkeypatch, mod)
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False, raising=False)
    monkeypatch.setattr(garmin_cliente.getpass, "getpass", lambda *a: pytest.fail("perguntou sem terminal"))
    with pytest.raises(ErroMfa, match="terminal"):
        ClienteGarminConnect.entrar(env)
    assert "resume" not in ch


def test_mfa_codigo_vazio(monkeypatch, env):
    mod, ch = _biblioteca(lambda t: ("needs_mfa", {}))
    _instala(monkeypatch, mod)
    with pytest.raises(ErroMfa):
        ClienteGarminConnect.entrar(env, ler_codigo=lambda: None)
    assert "resume" not in ch


def test_mfa_pelo_main_sai_com_3(monkeypatch, env, capsys):
    mod, _ = _biblioteca(lambda t: ("needs_mfa", {}))
    _instala(monkeypatch, mod)
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False, raising=False)
    assert main(["--atleta", "Atleta Ficticio"], session_factory=_sessao_com_atleta, env=env) == 3
    assert "MFA" in capsys.readouterr().err


def _sessao_com_atleta():
    eng = create_engine("sqlite://")
    Base.metadata.create_all(eng)
    s = Session(eng)
    s.add(Atleta(nome="Atleta Ficticio"))
    s.commit()
    return s


@pytest.mark.parametrize("excecao,esperado", [
    (_Erros.GarminConnectAuthenticationError, ErroLogin),
    (_Erros.GarminConnectTooManyRequestsError, ErroLimite),
    (_Erros.GarminConnectConnectionError, ErroRede),
    (ConnectionResetError, ErroRede),
    (RuntimeError, ErroGarmin),
])
def test_erros_do_login_e_nada_vaza(monkeypatch, env, capsys, caplog, excecao, esperado):
    def quebra(t):
        raise excecao(f"falha com {EMAIL} e {SENHA} e token-secreto-abc")

    mod, ch = _biblioteca(quebra)
    _instala(monkeypatch, mod)
    with caplog.at_level("DEBUG"):
        rc = main(["--atleta", "Atleta Ficticio"], session_factory=_sessao_com_atleta, env=env)
    saida = capsys.readouterr()
    visto = saida.err + saida.out + caplog.text
    assert rc == esperado.codigo and ch["login"] == 1
    for segredo in (EMAIL, SENHA, "token-secreto-abc"):
        assert segredo not in visto
    assert saida.err.startswith("erro: ")


def test_token_recusado_pede_para_apagar_a_pasta(monkeypatch, tmp_path):
    (tmp_path / "token").mkdir()
    (tmp_path / "token" / "garmin_tokens.json").write_text("{}")

    def recusa(t):
        raise _Erros.GarminConnectAuthenticationError("401")

    mod, ch = _biblioteca(recusa)
    _instala(monkeypatch, mod)
    with pytest.raises(ErroLogin, match="apague a pasta do token"):
        ClienteGarminConnect.entrar({"GARMINTOKENS": str(tmp_path / "token")})
    assert ch["login"] == 1  # sem segunda tentativa


def test_erro_no_download_vira_mensagem(monkeypatch, env):
    mod, _ = _biblioteca(lambda t: (None, None))
    _instala(monkeypatch, mod)
    cli = ClienteGarminConnect.entrar(env)

    def cai(*a, **k):
        raise _Erros.GarminConnectTooManyRequestsError(f"429 {SENHA}")

    cli._api.download_activity = cai
    with pytest.raises(ErroLimite) as e:
        cli.baixar_fit(7)
    assert SENHA not in str(e.value)


# ---------- zip, ambiente e arquivos do repositorio ----------

def test_extrair_fit():
    fit = (FITS / "upload_rodagem_6km.fit").read_bytes()
    assert extrair_fit(_zip("upload_rodagem_6km.fit")) == fit
    assert extrair_fit(fit) == fit  # FIT cru passa como esta
    vazio = io.BytesIO()
    with zipfile.ZipFile(vazio, "w") as z:
        z.writestr("leia-me.txt", "x")
    with pytest.raises(ErroGarmin):
        extrair_fit(vazio.getvalue())
    with pytest.raises(ErroGarmin):
        extrair_fit(b"PK\x03\x04quebrado")


def test_zip_grande_demais(monkeypatch):
    monkeypatch.setattr(garmin_cliente, "TAMANHO_MAX_FIT", 100)
    with pytest.raises(ErroGarmin, match="10 MB"):
        extrair_fit(_zip("upload_rodagem_6km.fit"))


def test_pasta_do_token_padrao_fica_no_repositorio_e_fora_do_controle_de_versao():
    assert garmin_cliente.pasta_token(None) == RAIZ / "dados-garmin" / "token"
    r = subprocess.run(["git", "check-ignore", "-q", "dados-garmin/token/garmin_tokens.json"], cwd=RAIZ)
    assert r.returncode == 0


def test_env_example_so_tem_os_nomes():
    linhas = dict(
        l.split("=", 1) for l in (RAIZ / ".env.example").read_text().splitlines() if "=" in l and not l.startswith("#")
    )
    for nome in ("GARMIN_EMAIL", "GARMIN_PASSWORD", "GARMINTOKENS"):
        assert linhas[nome] == ""


def test_variavel_do_ambiente_vence_o_env_local(monkeypatch):
    monkeypatch.setenv("GARMIN_EMAIL", "do-ambiente")
    assert garmin_cliente.ler_ambiente()["GARMIN_EMAIL"] == "do-ambiente"
