"""worker.buscar_recuperacao e o leitor de recuperacao do cliente (issue #372, ADR 0014). Cliente FALSO, fixtures de
`tests/fixtures/meta10/`, nenhuma conexao de rede, nenhum banco real. Dados inventados.
"""

import json
import logging
import os
import re
import socket
import types
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest
from app.db import models  # noqa: F401
from app.db.base import Base
from app.db.models import Atividade, Atleta, CheckinTreino, RecuperacaoDia
from app.servicos import recuperacao_banco as banco
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from worker import buscar_recuperacao as br
from worker import garmin_cliente
from worker.buscar_recuperacao import buscar, escolher_faixa, main
from worker.garmin_cliente import (
    ClienteGarminConnect,
    ErroGarmin,
    ErroLimite,
    ErroLogin,
    ErroRede,
    NoiteRecuperacao,
    ler_fc_repouso,
    ler_sono,
    ler_vfc,
)

FIX = Path(__file__).resolve().parents[3] / "tests" / "fixtures" / "meta10"
MARCADOR = "MARCADOR-SINTETICO-META10-NAO-LOGAR"
D = date  # atalho


def fx(nome):
    return json.loads((FIX / nome).read_text())


SONO_POR_DIA = {
    "2026-03-10": "sono_noite_completa.json",
    "2026-03-11": "sono_noite_sem_vfc.json",
    "2026-03-12": "sono_noite_sem_vfc_none.json",
    "2026-03-13": "sono_dto_sem_duracao.json",
    "2026-03-14": "sono_noite_com_sesta.json",
    "2026-03-15": "sono_noite_com_marcador.json",
}


@pytest.fixture(autouse=True)
def sem_rede(monkeypatch):
    """Derruba qualquer conexao que nao seja local (o Postgres do CI e local)."""
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
        a = Atleta(nome="Atleta Ficticio")
        s.add(a)
        s.commit()
        return a.id


class ApiFalsa:
    """O objeto `garminconnect.Garmin` por dentro: devolve as fixtures (a faixa devolve sempre o arquivo inteiro, como um
    servidor que ignora o intervalo: o leitor filtra). Guarda as chamadas. `erros` mapeia o nome do metodo a uma excecao."""

    def __init__(self, vfc="vfc_faixa.json", rhr="rhr_faixa.json", sono=None, erros=None):
        self.vfc, self.rhr = vfc, rhr
        self.sono = SONO_POR_DIA if sono is None else sono
        self.erros = erros or {}
        self.chamadas: list[tuple] = []

    def _antes(self, nome, *args):
        self.chamadas.append((nome, *args))
        e = self.erros.get(nome)
        if e is not None:
            raise (e(args) if callable(e) else e)

    def get_sleep_data(self, cdate):
        self._antes("sono", cdate)
        arq = self.sono.get(cdate)
        return fx(arq) if arq else {}

    def get_hrv_data_range(self, a, b):
        self._antes("vfc", a, b)
        return fx(self.vfc)

    def get_rhr_daily(self, a, b):
        self._antes("fc", a, b)
        return fx(self.rhr)


class _Erros:
    class GarminConnectConnectionError(Exception):
        def __init__(self, msg="x", status=None):
            super().__init__(msg)
            self.response = types.SimpleNamespace(status_code=status) if status is not None else None

    class GarminConnectTooManyRequestsError(Exception): ...
    class GarminConnectAuthenticationError(Exception): ...


MOD = types.SimpleNamespace(**vars(_Erros))


def cliente(api):
    return ClienteGarminConnect(api, MOD)


def e429(args=None):
    return _Erros.GarminConnectConnectionError(f"API Error 429 {MARCADOR}", 429)


def rodar(factory, cli, *args, hoje=D(2026, 3, 16), agora=datetime(2026, 3, 16, 9, 0, tzinfo=timezone.utc), pausas=None):
    pausas = [] if pausas is None else pausas
    return main(["--atleta", "Atleta Ficticio", *args], cliente=cli, session_factory=factory, hoje=hoje, agora=agora,
                pausa=pausas.append)


def _linhas(engine):
    with Session(engine) as s:
        return {r.noite: (r.sono_s, r.vfc_ms, r.fc_repouso_bpm) for r in s.scalars(select(RecuperacaoDia))}


# ---------- leitor (dentro do cliente) ----------

def test_leitor_do_sono_com_as_fixtures():
    assert ler_sono(fx("sono_noite_completa.json"), D(2026, 3, 10)) == 22500  # profundo + leve + REM, sem despertares
    assert ler_sono(fx("sono_noite_sem_vfc.json"), D(2026, 3, 11)) == 21600
    assert ler_sono(fx("sono_noite_com_sesta.json"), D(2026, 3, 14)) == 16500  # a sesta (1800 s) nao entra
    assert ler_sono(fx("sono_dto_sem_duracao.json"), D(2026, 3, 13)) is None
    assert ler_sono(fx("sono_dia_sem_dado.json"), D(2026, 3, 10)) is None  # {} (204)
    assert ler_sono(fx("sono_noite_completa.json"), D(2026, 3, 11)) is None  # outra data: nao arrisca


@pytest.mark.parametrize("valor", [None, 0, -5, 86401, True, "25000", float("nan"), float("inf"), [], {}])
def test_leitor_do_sono_ausente_zero_e_fora_da_faixa_viram_none(valor):
    r = {"dailySleepDTO": {"calendarDate": "2026-03-10", "sleepTimeSeconds": valor}}
    assert ler_sono(r, D(2026, 3, 10)) is None


@pytest.mark.parametrize("lixo", [None, [], "x", 3, {"dailySleepDTO": None}, {"dailySleepDTO": []},
                                   {"dailySleepDTO": {"calendarDate": 20260310, "sleepTimeSeconds": 100}}])
def test_leitor_nao_quebra_com_formato_inesperado(lixo):
    assert ler_sono(lixo, D(2026, 3, 10)) is None
    assert ler_vfc(lixo) == {} and ler_fc_repouso(lixo) == {}


def test_leitor_da_vfc_e_da_fc_de_repouso():
    assert ler_vfc(fx("vfc_faixa.json")) == {D(2026, 3, 10): 128, D(2026, 3, 11): 121, D(2026, 3, 12): 136}
    assert list(ler_vfc(fx("vfc_faixa_com_buraco.json"))) == [D(2026, 3, 10), D(2026, 3, 12)]  # dia sem leitura nao aparece
    assert ler_vfc(fx("vfc_faixa_sem_dado.json")) == {}
    assert ler_fc_repouso(fx("rhr_faixa.json")) == {D(2026, 3, 10): 54, D(2026, 3, 11): 56, D(2026, 3, 13): 52}
    assert ler_fc_repouso(fx("rhr_faixa_sem_dado.json")) == {}
    ruins = [{"calendarDate": "2026-03-10", "value": v} for v in (None, 0, 19.0, 151.0, True, "54")]
    ruins += [{"calendarDate": "ontem", "value": 54.0}, "x", {"value": 54.0}]
    assert ler_fc_repouso(ruins) == {}
    vruins = [{"calendarDate": "2026-03-10", "lastNightAvg": v} for v in (None, 0, -1, 501, True, "90")]
    assert ler_vfc({"hrvSummaries": vruins}) == {}
    assert ler_fc_repouso([{"calendarDate": "2026-03-10", "value": 54.4}]) == {D(2026, 3, 10): 54}  # decimal da faixa


# ---------- o cliente real, com a biblioteca trocada por um falso ----------

def test_cliente_devolve_noites_normalizadas_por_medida():
    api = ApiFalsa()
    cli = cliente(api)
    assert cli.recuperacao(D(2026, 3, 10), D(2026, 3, 10), ("sono",)) == [NoiteRecuperacao(D(2026, 3, 10), sono_s=22500)]
    assert cli.recuperacao(D(2026, 3, 11), D(2026, 3, 12), ("vfc",)) == [
        NoiteRecuperacao(D(2026, 3, 11), vfc_ms=121), NoiteRecuperacao(D(2026, 3, 12), vfc_ms=136)]  # filtra pela faixa
    assert cli.recuperacao(D(2026, 3, 10), D(2026, 3, 13), ("fc",))[-1] == NoiteRecuperacao(D(2026, 3, 13), fc_repouso_bpm=52)
    assert [c[0] for c in api.chamadas] == ["sono", "vfc", "fc"]  # cada chamada ao cliente e UMA requisicao
    assert cli.recuperacao(D(2026, 3, 20), D(2026, 3, 20), ("sono",)) == []  # sem dado: lista vazia


def test_cliente_recusa_faixa_grande_e_sono_de_varios_dias():
    cli = cliente(ApiFalsa())
    with pytest.raises(ErroGarmin):
        cli.recuperacao(D(2026, 3, 1), D(2026, 3, 29), ("vfc",))  # 29 dias
    assert cli.recuperacao(D(2026, 3, 1), D(2026, 3, 28), ("vfc",))  # 28 dias passam
    with pytest.raises(ErroGarmin):
        cli.recuperacao(D(2026, 3, 10), D(2026, 3, 11), ("sono",))


@pytest.mark.parametrize("excecao,esperado", [
    (e429, ErroLimite),  # #386: o 429 das rotas de dados chega como erro de conexao com a resposta
    (_Erros.GarminConnectTooManyRequestsError, ErroLimite),
    (lambda a: _Erros.GarminConnectConnectionError(f"API Error 500 {MARCADOR}", 500), ErroRede),
    (lambda a: _Erros.GarminConnectConnectionError(f"sem resposta {MARCADOR}"), ErroRede),
    (_Erros.GarminConnectAuthenticationError, ErroLogin),
    (lambda a: RuntimeError(MARCADOR), ErroGarmin),
])
def test_erros_viram_codigo_e_a_mensagem_nao_repete_a_resposta(excecao, esperado):
    cli = cliente(ApiFalsa(erros={"sono": excecao, "vfc": excecao, "fc": excecao}))
    for medida, ini, fim in (("sono", D(2026, 3, 10), D(2026, 3, 10)), ("vfc", D(2026, 3, 10), D(2026, 3, 12)),
                             ("fc", D(2026, 3, 10), D(2026, 3, 12))):
        with pytest.raises(esperado) as e:
            cli.recuperacao(ini, fim, (medida,))
        assert type(e.value) is esperado and MARCADOR not in str(e.value)


def test_429_das_rotas_de_atividade_tambem_vira_limite():
    """#386: o mesmo tratamento vale para `listar` e `baixar_fit` do `buscar_garmin` (Meta 9)."""
    api = types.SimpleNamespace(get_activities_by_date=lambda *a, **k: (_ for _ in ()).throw(e429()),
                                download_activity=lambda *a, **k: (_ for _ in ()).throw(e429()))
    api.Garmin = None
    mod = types.SimpleNamespace(Garmin=types.SimpleNamespace(ActivityDownloadFormat=types.SimpleNamespace(ORIGINAL="o")),
                                **vars(_Erros))
    cli = ClienteGarminConnect(api, mod)
    with pytest.raises(ErroLimite):
        cli.listar(D(2026, 3, 10), D(2026, 3, 10))
    with pytest.raises(ErroLimite):
        cli.baixar_fit(1)
    erro500 = _Erros.GarminConnectConnectionError("API Error 500", 500)
    api.get_activities_by_date = lambda *a, **k: (_ for _ in ()).throw(erro500)
    with pytest.raises(ErroRede):  # so o 429 muda; o resto continua rede
        cli.listar(D(2026, 3, 10), D(2026, 3, 10))


# ---------- a faixa de datas ----------

def _checkin_em(session, atleta_id, inicio, fuso=None, fid="1"):
    at = Atividade(atleta_id=atleta_id, fonte="t", fonte_id=fid, modalidade="corrida", inicio=inicio, fuso_min=fuso,
                   duracao_s=1800.0)
    session.add(at)
    session.flush()
    session.add(CheckinTreino(atividade_id=at.id, pse=5, sensacao=3, nada_a_relatar=True, versao="checkin@1",
                              registrado_em=inicio, atualizado_em=inicio))
    session.commit()


def test_primeira_rodada_sem_checkin_busca_as_35_ultimas_noites(factory, atleta):
    with factory() as s:
        ini, fim, av = escolher_faixa(s, atleta, D(2026, 3, 16), None, None)
    assert (fim - ini).days + 1 == 35 and fim == D(2026, 3, 16) and av == []


def test_primeira_rodada_vai_do_treino_mais_antigo_com_checkin_menos_28(factory, atleta):
    with factory() as s:
        _checkin_em(s, atleta, datetime(2026, 2, 20, 12, 0, tzinfo=timezone.utc))
        _checkin_em(s, atleta, datetime(2026, 3, 1, 12, 0, tzinfo=timezone.utc), fid="2")
        ini, fim, av = escolher_faixa(s, atleta, D(2026, 3, 16), None, None)
    assert ini == D(2026, 2, 20) - timedelta(days=28) and (fim - ini).days + 1 == 53 and av == []


def test_primeira_rodada_usa_a_data_local_do_treino(factory, atleta):
    with factory() as s:  # 01:00 UTC com fuso -3 h = a vespera no calendario local
        _checkin_em(s, atleta, datetime(2026, 3, 10, 1, 0, tzinfo=timezone.utc), fuso=-180)
        ini, _, _ = escolher_faixa(s, atleta, D(2026, 3, 16), None, None)
    assert ini == D(2026, 3, 9) - timedelta(days=28)


def test_primeira_rodada_respeita_o_minimo_de_35_noites(factory, atleta):
    with factory() as s:  # treino recente: 15/3 - 28 daria so 30 noites; vale o minimo
        _checkin_em(s, atleta, datetime(2026, 3, 15, 12, 0, tzinfo=timezone.utc))
        ini, fim, _ = escolher_faixa(s, atleta, D(2026, 3, 16), None, None)
    assert (fim - ini).days + 1 == 35


def test_primeira_rodada_corta_no_teto_de_120_e_avisa(factory, atleta):
    with factory() as s:
        _checkin_em(s, atleta, datetime(2025, 1, 10, 12, 0, tzinfo=timezone.utc))
        ini, fim, av = escolher_faixa(s, atleta, D(2026, 3, 16), None, None)
    assert (fim - ini).days + 1 == 120 and len(av) == 1 and "120" in av[0]


def test_rodadas_seguintes_comecam_duas_noites_antes_da_ultima(factory, atleta):
    with factory() as s:
        banco.gravar_noite(s, atleta, D(2026, 3, 10), 20000, None, None, "v", datetime.now(timezone.utc))
        s.commit()
        assert escolher_faixa(s, atleta, D(2026, 3, 16), None, None) == (D(2026, 3, 8), D(2026, 3, 16), [])
        ini, fim, av = escolher_faixa(s, atleta, D(2026, 8, 16), None, None)  # muito tempo sem rodar: teto de 60
        assert (fim - ini).days + 1 == 60 and len(av) == 1 and "60" in av[0]
        assert escolher_faixa(s, atleta, D(2026, 8, 16), D(2026, 3, 1), D(2026, 3, 5)) == (D(2026, 3, 1), D(2026, 3, 5), [])  # sobrepoem
        assert escolher_faixa(s, atleta, D(2026, 3, 16), D(2026, 1, 1), None)[:2] == (D(2026, 1, 1), D(2026, 3, 16))  # --desde passa do teto


# ---------- a busca ----------

def test_grava_as_noites_independente_por_medida(engine, factory, atleta, capsys):
    api = ApiFalsa()
    pausas = []
    assert rodar(factory, cliente(api), "--desde", "2026-03-10", "--ate", "2026-03-15", hoje=D(2026, 3, 16), pausas=pausas) == 0
    assert _linhas(engine) == {
        D(2026, 3, 10): (22500, 128, 54), D(2026, 3, 11): (21600, 121, 56), D(2026, 3, 12): (21600, 136, None),
        D(2026, 3, 13): (None, None, 52),  # so a FC de repouso
        D(2026, 3, 14): (16500, None, None),  # so o sono; sesta ignorada
        D(2026, 3, 15): (22500, None, None),
    }
    assert "recuperacao: noites_novas=6 atualizadas=0 iguais=0 sem_dado=0 falhas=0" in capsys.readouterr().out
    assert [c[0] for c in api.chamadas] == ["vfc", "fc"] + ["sono"] * 6  # um bloco: 2 faixas e 6 noites
    assert len(pausas) == len(api.chamadas) - 1  # pausa entre as chamadas, nao antes da primeira


def test_fc_de_repouso_so_quando_a_noite_ja_passou(engine, factory, atleta, capsys):
    """A FC e a do DIA: na noite de hoje (ou depois) fica vazia; a rodada seguinte preenche."""
    rodar(factory, cliente(ApiFalsa()), "--desde", "2026-03-10", "--ate", "2026-03-13", hoje=D(2026, 3, 13))
    assert _linhas(engine)[D(2026, 3, 11)][2] == 56 and D(2026, 3, 13) not in _linhas(engine)  # 13/3 era so FC e hoje
    assert "sem_dado=1" in capsys.readouterr().out  # consultou as tres e nenhuma serve
    rodar(factory, cliente(ApiFalsa()), "--desde", "2026-03-10", "--ate", "2026-03-13", hoje=D(2026, 3, 14))
    assert _linhas(engine)[D(2026, 3, 13)] == (None, None, 52)


def test_idempotente_e_importado_em_so_muda_quando_um_valor_muda(engine, factory, atleta, capsys):
    a1 = datetime(2026, 3, 16, 9, 0, tzinfo=timezone.utc)
    a2 = a1 + timedelta(days=1)
    args = ("--desde", "2026-03-10", "--ate", "2026-03-15")
    rodar(factory, cliente(ApiFalsa()), *args, agora=a1)
    capsys.readouterr()
    with Session(engine) as s:
        antes = {n: x.importado_em for n, x in banco.noites_do_atleta(s, atleta).items()}
    rodar(factory, cliente(ApiFalsa()), *args, agora=a2)
    assert "noites_novas=0 atualizadas=0 iguais=6" in capsys.readouterr().out
    with Session(engine) as s:
        assert {n: x.importado_em for n, x in banco.noites_do_atleta(s, atleta).items()} == antes  # nada mudou
        assert s.scalar(select(func.count()).select_from(RecuperacaoDia)) == 6


def test_valor_diferente_substitui_e_nulo_nunca_apaga(engine, factory, atleta, capsys):
    a1 = datetime(2026, 3, 16, 9, 0, tzinfo=timezone.utc)
    a2 = a1 + timedelta(days=1)
    args = ("--desde", "2026-03-10", "--ate", "2026-03-11")
    rodar(factory, cliente(ApiFalsa()), *args, agora=a1)
    capsys.readouterr()
    # o Garmin recalcula a VFC de 11/3, e agora nao devolve mais o sono nem a FC de 10/3
    novo = {"_sintetico": "SINTETICO", "hrvSummaries": [
        {"calendarDate": "2026-03-11", "lastNightAvg": 150, "lastNight5MinHigh": 190, "weeklyAvg": None, "baseline": {},
         "status": "BALANCED", "feedbackPhrase": "x", "createTimeStamp": "x"}]}
    api = ApiFalsa(rhr="rhr_faixa_sem_dado.json", sono={})
    api.vfc = "vfc_nova.json"
    original = fx
    try:
        globals()["fx"] = lambda nome: novo if nome == "vfc_nova.json" else original(nome)
        rodar(factory, cliente(api), *args, agora=a2)
    finally:
        globals()["fx"] = original
    assert "atualizadas=1 iguais=1" in capsys.readouterr().out
    assert _linhas(engine) == {D(2026, 3, 10): (22500, 128, 54), D(2026, 3, 11): (21600, 150, 56)}
    with Session(engine) as s:
        n = banco.noites_do_atleta(s, atleta)
        assert n[D(2026, 3, 11)].importado_em.replace(tzinfo=None) == a2.replace(tzinfo=None)
        assert n[D(2026, 3, 10)].importado_em.replace(tzinfo=None) == a1.replace(tzinfo=None)


def test_blocos_de_28_dias_e_teto_de_12_chamadas_de_faixa(engine, factory, atleta, capsys):
    api = ApiFalsa(sono={})
    assert rodar(factory, cliente(api), "--desde", "2025-01-01", "--ate", "2026-03-01") == 0  # ~425 noites
    faixas = [c for c in api.chamadas if c[0] in ("vfc", "fc")]
    assert len(faixas) == br.TETO_CHAMADAS_FAIXA == 12  # parou no teto
    for _, ini, fim in faixas:
        assert (date.fromisoformat(fim) - date.fromisoformat(ini)).days + 1 <= 28
    assert sum(1 for c in api.chamadas if c[0] == "sono") <= br.TETO_CHAMADAS_SONO
    assert "aviso: teto_faixa" in capsys.readouterr().out


def test_429_para_a_execucao_e_preserva_o_gravado(engine, factory, atleta, capsys, caplog):
    api = ApiFalsa(erros={})
    original = api.get_sleep_data

    def sono(cdate):
        if cdate == "2026-03-13":
            raise e429()
        return original(cdate)

    api.get_sleep_data = sono
    with caplog.at_level(logging.DEBUG):
        rc = rodar(factory, cliente(api), "--desde", "2026-03-10", "--ate", "2026-03-15")
    saida = capsys.readouterr()
    assert rc == 4 and ("sono", "2026-03-14") not in api.chamadas  # nao tentou os dias seguintes
    assert _linhas(engine)[D(2026, 3, 10)] == (22500, 128, 54) and D(2026, 3, 12) in _linhas(engine)  # o que veio, ficou
    assert "falhas=1" in saida.out and MARCADOR not in saida.out + saida.err + caplog.text


def test_falha_de_rede_numa_medida_nao_perde_as_outras(engine, factory, atleta, capsys):
    api = ApiFalsa(erros={"vfc": lambda a: _Erros.GarminConnectConnectionError(f"API Error 502 {MARCADOR}", 502)})
    assert rodar(factory, cliente(api), "--desde", "2026-03-10", "--ate", "2026-03-12") == 5
    assert _linhas(engine) == {D(2026, 3, 10): (22500, None, 54), D(2026, 3, 11): (21600, None, 56), D(2026, 3, 12): (21600, None, None)}
    saida = capsys.readouterr()
    assert "falhas=1" in saida.out and "sem_dado=0" in saida.out and MARCADOR not in saida.out + saida.err
    assert [c[0] for c in api.chamadas].count("vfc") == 1  # nao insiste


def test_precedencia_dos_codigos_limite_antes_de_rede(engine, factory, atleta):
    api = ApiFalsa(erros={"vfc": lambda a: _Erros.GarminConnectConnectionError("API Error 502", 502), "fc": e429})
    assert rodar(factory, cliente(api), "--desde", "2026-03-10", "--ate", "2026-03-12") == 4


def test_login_recusado_sai_com_2_antes_de_qualquer_gravacao(engine, factory, atleta, monkeypatch, capsys):
    def recusa(env=None):
        raise ErroLogin("o Garmin recusou o login; confira GARMIN_EMAIL e GARMIN_PASSWORD")

    monkeypatch.setattr(ClienteGarminConnect, "entrar", staticmethod(recusa))
    rc = main(["--atleta", "Atleta Ficticio", "--desde", "2026-03-10", "--ate", "2026-03-12"], session_factory=factory,
              hoje=D(2026, 3, 16), env={})
    assert rc == 2 and _linhas(engine) == {} and capsys.readouterr().err.startswith("erro: ")


def test_atleta_inexistente_e_argumentos_invalidos(engine, factory, atleta, capsys):
    assert main(["--atleta", "Ninguem"], cliente=cliente(ApiFalsa()), session_factory=factory, hoje=D(2026, 3, 16)) == 1
    assert rodar(factory, cliente(ApiFalsa()), "--desde", "2026-03-12", "--ate", "2026-03-10") == 1
    assert _linhas(engine) == {}


def test_o_marcador_nunca_aparece_em_nenhuma_saida(engine, factory, atleta, capsys, caplog):
    """A noite de 15/3 traz o marcador em campos de texto e num campo desconhecido: nada disso passa para a saida,
    o log ou o banco; e a saida tem so contagens (nenhuma data nem valor)."""
    with caplog.at_level(logging.DEBUG):
        assert rodar(factory, cliente(ApiFalsa()), "--desde", "2026-03-10", "--ate", "2026-03-15") == 0
    saida = capsys.readouterr()
    visto = saida.out + saida.err + caplog.text
    assert MARCADOR not in visto
    assert re.search(r"\d{4}-\d{2}-\d{2}|22500|128|54", visto) is None
    with Session(engine) as s:
        assert MARCADOR not in json.dumps([[str(getattr(r, c.name)) for c in RecuperacaoDia.__table__.columns]
                                           for r in s.scalars(select(RecuperacaoDia))])


def test_nao_usa_nenhuma_outra_biblioteca_do_garmin_alem_do_cliente():
    """O nome de campo do Garmin nunca sai do cliente: o comando nao conhece `dailySleepDTO` nem `hrvSummaries`."""
    fonte = Path(br.__file__).read_text()
    for campo in ("dailySleepDTO", "hrvSummaries", "sleepTimeSeconds", "lastNightAvg", "restingHeartRate", "garminconnect"):
        assert campo not in fonte
    assert garmin_cliente.VERSAO_LEITURA == "recuperacao_leitura@1"
