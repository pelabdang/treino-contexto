"""worker.buscar_recuperacao e o leitor de recuperacao do cliente (issue #372, ADR 0014 e adendo 1 ao item 5). Cliente
FALSO, fixtures de `tests/fixtures/meta10/` (as respostas do sono; as de faixa so documentam o formato), nenhuma conexao de
rede, nenhum banco real. As tres medidas vem da MESMA resposta do sono. Dados inventados.
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
    ler_noite,
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
    """O objeto `garminconnect.Garmin` por dentro: so `get_sleep_data` existe (qualquer chamada de faixa levantaria
    `AttributeError`, o que prova que a busca nao as usa). `sono` mapeia a data ao nome da fixture OU a uma resposta pronta."""

    def __init__(self, sono=None, erros=None):
        self.sono = SONO_POR_DIA if sono is None else sono
        self.erros = erros or {}  # data ISO -> excecao (ou funcao que a cria)
        self.chamadas: list[str] = []

    def get_sleep_data(self, cdate):
        self.chamadas.append(cdate)
        e = self.erros.get(cdate)
        if e is not None:
            raise (e() if callable(e) else e)
        alvo = self.sono.get(cdate)
        return fx(alvo) if isinstance(alvo, str) else (alvo or {})


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


def e429():
    return _Erros.GarminConnectConnectionError(f"API Error 429 {MARCADOR}", 429)


def e502():
    return _Erros.GarminConnectConnectionError(f"API Error 502 {MARCADOR}", 502)


def resp(cal, sono=20000, vfc=90.0, fc=55):
    """Resposta minima valida do sono (sintetica), para os testes que precisam de valores diferentes dos das fixtures."""
    r = {"dailySleepDTO": {"calendarDate": cal, "sleepTimeSeconds": sono}}
    if vfc is not None:
        r["avgOvernightHrv"] = vfc
    if fc is not None:
        r["restingHeartRate"] = fc
    return r


def rodar(factory, cli, *args, hoje=D(2026, 3, 16), agora=datetime(2026, 3, 16, 9, 0, tzinfo=timezone.utc), pausas=None):
    pausas = [] if pausas is None else pausas
    return main(["--atleta", "Atleta Ficticio", *args], cliente=cli, session_factory=factory, hoje=hoje, agora=agora,
                pausa=pausas.append)


def _linhas(engine):
    with Session(engine) as s:
        return {r.noite: (r.sono_s, r.vfc_ms, r.fc_repouso_bpm) for r in s.scalars(select(RecuperacaoDia))}


def _gravar(session, atleta, noite, sono=20000, vfc=90.0, fc=55):
    banco.gravar_noite(session, atleta, noite, sono, vfc, fc, "v", datetime(2026, 3, 1, tzinfo=timezone.utc))


# ---------- leitor (dentro do cliente): as tres medidas da resposta do sono ----------

def test_leitor_com_as_fixtures_do_sono():
    n = ler_noite(fx("sono_noite_completa.json"), D(2026, 3, 10))
    assert n == NoiteRecuperacao(D(2026, 3, 10), 22500, 128.0, 54)  # sono sem despertares; VFC decimal; FC inteira
    assert ler_noite(fx("sono_noite_sem_vfc.json"), D(2026, 3, 11)) == NoiteRecuperacao(D(2026, 3, 11), 21600, None, 54)  # ausente
    assert ler_noite(fx("sono_noite_sem_vfc_none.json"), D(2026, 3, 12)) == NoiteRecuperacao(D(2026, 3, 12), 21600, None, 54)  # None
    assert ler_noite(fx("sono_dto_sem_duracao.json"), D(2026, 3, 13)) == NoiteRecuperacao(D(2026, 3, 13), None, None, 56)
    assert ler_noite(fx("sono_noite_com_sesta.json"), D(2026, 3, 14)).sono_s == 16500  # a sesta (1800 s) nao entra
    assert ler_noite(fx("sono_dia_sem_dado.json"), D(2026, 3, 10)) == NoiteRecuperacao(D(2026, 3, 10))  # {} (204): tudo None
    assert ler_noite(fx("sono_noite_completa.json"), D(2026, 3, 11)) == NoiteRecuperacao(D(2026, 3, 11))  # outra data: tudo None


@pytest.mark.parametrize("valor", [None, 0, -5, True, "25", float("nan"), float("inf"), [], {}])
def test_cada_medida_ausente_zero_ou_invalida_vira_none(valor):
    r = {"dailySleepDTO": {"calendarDate": "2026-03-10", "sleepTimeSeconds": valor}, "avgOvernightHrv": valor,
         "restingHeartRate": valor}
    assert ler_noite(r, D(2026, 3, 10)) == NoiteRecuperacao(D(2026, 3, 10))


@pytest.mark.parametrize("campo,valor", [("sono", 86401), ("vfc", 500.1), ("fc", 19), ("fc", 151)])
def test_fora_da_faixa_dos_check_vira_none(campo, valor):
    kw = {"sono": 20000, "vfc": 90.0, "fc": 55, campo: valor}
    n = ler_noite(resp("2026-03-10", **kw), D(2026, 3, 10))
    assert getattr(n, {"sono": "sono_s", "vfc": "vfc_ms", "fc": "fc_repouso_bpm"}[campo]) is None
    assert sum(x is not None for x in (n.sono_s, n.vfc_ms, n.fc_repouso_bpm)) == 2  # as outras seguem


def test_extremos_validos_e_fc_decimal_arredondada():
    n = ler_noite(resp("2026-03-10", sono=86400, vfc=500.0, fc=20.4), D(2026, 3, 10))
    assert (n.sono_s, n.vfc_ms, n.fc_repouso_bpm) == (86400, 500.0, 20)
    assert ler_noite(resp("2026-03-10", sono=1, vfc=0.1, fc=150), D(2026, 3, 10)).sono_s == 1


@pytest.mark.parametrize("lixo", [None, [], "x", 3, {"dailySleepDTO": None}, {"dailySleepDTO": []},
                                   {"dailySleepDTO": {"calendarDate": 20260310, "sleepTimeSeconds": 100}},
                                   {"avgOvernightHrv": 90.0, "restingHeartRate": 55}])  # sem o DTO: nao atribui a noite
def test_leitor_nao_quebra_com_formato_inesperado(lixo):
    assert ler_noite(lixo, D(2026, 3, 10)) == NoiteRecuperacao(D(2026, 3, 10))


# ---------- o cliente real, com a biblioteca trocada por um falso ----------

def test_cliente_faz_uma_requisicao_por_noite_so_no_sono():
    api = ApiFalsa()
    cli = cliente(api)
    assert cli.recuperacao(D(2026, 3, 10)) == NoiteRecuperacao(D(2026, 3, 10), 22500, 128.0, 54)
    assert cli.recuperacao(D(2026, 3, 20)) == NoiteRecuperacao(D(2026, 3, 20))  # sem dado: tudo None, nao levanta
    assert api.chamadas == ["2026-03-10", "2026-03-20"]


@pytest.mark.parametrize("excecao,esperado", [
    (e429, ErroLimite),  # #386: o 429 das rotas de dados chega como erro de conexao com a resposta
    (_Erros.GarminConnectTooManyRequestsError, ErroLimite),
    (e502, ErroRede),
    (lambda: _Erros.GarminConnectConnectionError(f"sem resposta {MARCADOR}"), ErroRede),
    (_Erros.GarminConnectAuthenticationError, ErroLogin),
    (lambda: RuntimeError(MARCADOR), ErroGarmin),
])
def test_erros_viram_codigo_e_a_mensagem_nao_repete_a_resposta(excecao, esperado):
    cli = cliente(ApiFalsa(erros={"2026-03-10": excecao}))
    with pytest.raises(esperado) as e:
        cli.recuperacao(D(2026, 3, 10))
    assert type(e.value) is esperado and MARCADOR not in str(e.value)


def test_429_das_rotas_de_atividade_tambem_vira_limite():
    """#386: o mesmo tratamento vale para `listar` e `baixar_fit` do `buscar_garmin` (Meta 9)."""
    def cai(*a, **k):
        raise e429()

    api = types.SimpleNamespace(get_activities_by_date=cai, download_activity=cai)
    mod = types.SimpleNamespace(Garmin=types.SimpleNamespace(ActivityDownloadFormat=types.SimpleNamespace(ORIGINAL="o")),
                                **vars(_Erros))
    cli = ClienteGarminConnect(api, mod)
    with pytest.raises(ErroLimite):
        cli.listar(D(2026, 3, 10), D(2026, 3, 10))
    with pytest.raises(ErroLimite):
        cli.baixar_fit(1)

    def cai500(*a, **k):
        raise _Erros.GarminConnectConnectionError("API Error 500", 500)

    api.get_activities_by_date = cai500
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


def _noites(s, atleta, de, ate):
    d = de
    while d <= ate:
        _gravar(s, atleta, d)
        d += timedelta(days=1)
    s.commit()


def test_rodadas_seguintes_comecam_duas_noites_antes_da_ultima(factory, atleta):
    with factory() as s:
        _noites(s, atleta, D(2026, 3, 10), D(2026, 3, 14))  # tudo completo: sem buraco
        assert escolher_faixa(s, atleta, D(2026, 3, 15), None, None) == (D(2026, 3, 12), D(2026, 3, 15), [])
        ini, fim, av = escolher_faixa(s, atleta, D(2026, 8, 16), None, None)  # muito tempo sem rodar: teto de 60
        assert (fim - ini).days + 1 == 60 and len(av) == 1 and "60" in av[0]
        assert escolher_faixa(s, atleta, D(2026, 8, 16), D(2026, 3, 1), D(2026, 3, 5)) == (D(2026, 3, 1), D(2026, 3, 5), [])
        assert escolher_faixa(s, atleta, D(2026, 3, 15), D(2026, 1, 1), None)[:2] == (D(2026, 1, 1), D(2026, 3, 15))  # passa do teto


def test_buraco_linha_incompleta_puxa_o_inicio_da_rodada(factory, atleta):
    with factory() as s:
        _noites(s, atleta, D(2026, 3, 10), D(2026, 3, 15))
        s.query(RecuperacaoDia).filter(RecuperacaoDia.noite == D(2026, 3, 11)).update({"vfc_ms": None})  # a VFC faltou
        s.commit()
        assert escolher_faixa(s, atleta, D(2026, 3, 16), None, None) == (D(2026, 3, 11), D(2026, 3, 16), [])  # antes de 13/3


def test_buraco_noite_sem_linha_dentro_da_janela_puxa_o_inicio(factory, atleta):
    with factory() as s:
        _noites(s, atleta, D(2026, 3, 10), D(2026, 3, 15))
        s.query(RecuperacaoDia).filter(RecuperacaoDia.noite == D(2026, 3, 12)).delete()
        s.commit()
        assert escolher_faixa(s, atleta, D(2026, 3, 16), None, None)[0] == D(2026, 3, 12)


def test_buraco_antigo_sai_da_janela_e_nao_e_rebuscado_para_sempre(factory, atleta):
    """Uma noite que o Garmin realmente nao tem so puxa a rodada por 14 dias; depois sai da janela."""
    with factory() as s:
        _noites(s, atleta, D(2026, 3, 10), D(2026, 3, 23))
        s.query(RecuperacaoDia).filter(RecuperacaoDia.noite == D(2026, 3, 11)).delete()
        s.commit()
        assert escolher_faixa(s, atleta, D(2026, 3, 24), None, None)[0] == D(2026, 3, 11)  # janela 10/3 a 23/3: ainda puxa
        _noites(s, atleta, D(2026, 3, 24), D(2026, 3, 25))
        assert escolher_faixa(s, atleta, D(2026, 3, 26), None, None)[0] == D(2026, 3, 23)  # janela 12/3 a 25/3: 11/3 saiu


def test_buraco_so_conta_noite_que_ja_passou_e_depois_da_primeira_gravada(factory, atleta):
    with factory() as s:
        _gravar(s, atleta, D(2026, 3, 10), fc=None)  # a FC do dia ainda nao valia
        s.commit()
        # no proprio dia 10/3 a noite nao passou: nao e buraco (so ultima - 2)
        assert escolher_faixa(s, atleta, D(2026, 3, 10), None, None)[0] == D(2026, 3, 8)
        # em 11/3 ela passou e esta incompleta: e buraco, mas 10/3 > ultima - 2 (8/3): vale 8/3
        assert escolher_faixa(s, atleta, D(2026, 3, 11), None, None)[0] == D(2026, 3, 8)
        _gravar(s, atleta, D(2026, 3, 16))
        s.commit()
        # 10/3 incompleta e passou: e o buraco mais antigo (11 a 15/3 sem linha tambem sao); antes de 10/3 nada conta
        assert escolher_faixa(s, atleta, D(2026, 3, 17), None, None)[0] == D(2026, 3, 10)


# ---------- a busca ----------

def test_grava_as_tres_medidas_da_mesma_resposta_do_sono(engine, factory, atleta, capsys):
    api = ApiFalsa()
    pausas = []
    assert rodar(factory, cliente(api), "--desde", "2026-03-10", "--ate", "2026-03-15", pausas=pausas) == 0
    assert _linhas(engine) == {
        D(2026, 3, 10): (22500, 128.0, 54), D(2026, 3, 11): (21600, None, 54), D(2026, 3, 12): (21600, None, 54),
        D(2026, 3, 13): (None, None, 56),  # so a FC de repouso
        D(2026, 3, 14): (16500, 128.0, 54),  # sesta ignorada
        D(2026, 3, 15): (22500, 128.0, 54),
    }
    assert "recuperacao: noites_novas=6 atualizadas=0 iguais=0 sem_dado=0 falhas=0" in capsys.readouterr().out
    assert api.chamadas == [f"2026-03-{d}" for d in range(10, 16)]  # uma chamada por noite, em ordem crescente, sem faixa
    assert len(pausas) == 5 and set(pausas) == {br.PAUSA_S}  # pausa entre as chamadas, nao antes da primeira


def test_fc_de_repouso_so_quando_a_noite_ja_passou(engine, factory, atleta, capsys):
    """A FC e a do DIA: na noite de hoje (ou depois) fica vazia; a rodada seguinte preenche."""
    rodar(factory, cliente(ApiFalsa()), "--desde", "2026-03-10", "--ate", "2026-03-13", hoje=D(2026, 3, 13))
    assert _linhas(engine)[D(2026, 3, 11)][2] == 54 and D(2026, 3, 13) not in _linhas(engine)  # 13/3 era so FC e e hoje
    assert "sem_dado=1" in capsys.readouterr().out
    rodar(factory, cliente(ApiFalsa()), "--desde", "2026-03-10", "--ate", "2026-03-13", hoje=D(2026, 3, 14))
    assert _linhas(engine)[D(2026, 3, 13)] == (None, None, 56)


def test_idempotente_e_importado_em_so_muda_quando_um_valor_muda(engine, factory, atleta, capsys):
    a1 = datetime(2026, 3, 16, 9, 0, tzinfo=timezone.utc)
    args = ("--desde", "2026-03-10", "--ate", "2026-03-15")
    rodar(factory, cliente(ApiFalsa()), *args, agora=a1)
    capsys.readouterr()
    with Session(engine) as s:
        antes = {n: x.importado_em for n, x in banco.noites_do_atleta(s, atleta).items()}
    rodar(factory, cliente(ApiFalsa()), *args, agora=a1 + timedelta(days=1))
    assert "noites_novas=0 atualizadas=0 iguais=6" in capsys.readouterr().out
    with Session(engine) as s:
        assert {n: x.importado_em for n, x in banco.noites_do_atleta(s, atleta).items()} == antes
        assert s.scalar(select(func.count()).select_from(RecuperacaoDia)) == 6


def test_valor_diferente_substitui_e_nulo_nunca_apaga(engine, factory, atleta, capsys):
    a1 = datetime(2026, 3, 16, 9, 0, tzinfo=timezone.utc)
    a2 = a1 + timedelta(days=1)
    args = ("--desde", "2026-03-10", "--ate", "2026-03-11")
    rodar(factory, cliente(ApiFalsa()), *args, agora=a1)
    capsys.readouterr()
    # o Garmin recalcula a VFC de 11/3 e agora devolve a de 10/3 sem sono nem FC
    novo = ApiFalsa({"2026-03-10": resp("2026-03-10", sono=None, vfc=None, fc=None),
                     "2026-03-11": resp("2026-03-11", sono=21600, vfc=150.0, fc=54)})
    rodar(factory, cliente(novo), *args, agora=a2)
    assert "atualizadas=1 iguais=1" in capsys.readouterr().out
    assert _linhas(engine) == {D(2026, 3, 10): (22500, 128.0, 54), D(2026, 3, 11): (21600, 150.0, 54)}
    with Session(engine) as s:
        n = banco.noites_do_atleta(s, atleta)
        assert n[D(2026, 3, 11)].importado_em.replace(tzinfo=None) == a2.replace(tzinfo=None)
        assert n[D(2026, 3, 10)].importado_em.replace(tzinfo=None) == a1.replace(tzinfo=None)


def test_rodada_seguinte_refaz_o_buraco_e_diz_so_a_contagem(engine, factory, atleta, capsys):
    """10 a 15/3 em duas rodadas: a 1a perde a VFC de 11/3 (o Garmin ainda nao a tinha); a 2a, sem --desde, a refaz."""
    primeira = ApiFalsa({**SONO_POR_DIA, "2026-03-11": resp("2026-03-11", sono=21600, vfc=None, fc=54)})
    rodar(factory, cliente(primeira), "--desde", "2026-03-10", "--ate", "2026-03-15")
    capsys.readouterr()
    segunda = ApiFalsa({**SONO_POR_DIA, "2026-03-11": resp("2026-03-11", sono=21600, vfc=99.0, fc=54)})
    assert rodar(factory, cliente(segunda)) == 0
    saida = capsys.readouterr().out
    assert segunda.chamadas[0] == "2026-03-11"  # comecou no buraco (antes de ultima - 2 = 13/3)
    assert "aviso: rebuscadas=2" in saida and "2026" not in saida  # so a contagem, nenhuma data
    assert _linhas(engine)[D(2026, 3, 11)] == (21600, 99.0, 54)


def test_teto_de_130_chamadas_por_execucao(engine, factory, atleta, capsys):
    api = ApiFalsa(sono={})
    assert rodar(factory, cliente(api), "--desde", "2025-01-01", "--ate", "2026-03-01") == 0  # ~425 noites
    assert len(api.chamadas) == br.TETO_CHAMADAS == 130
    assert api.chamadas == sorted(api.chamadas)  # ordem crescente: a rodada seguinte continua dali
    saida = capsys.readouterr().out
    assert "aviso: teto_chamadas" in saida and "sem_dado=130" in saida


def test_429_para_a_execucao_e_preserva_o_gravado(engine, factory, atleta, capsys, caplog):
    api = ApiFalsa(erros={"2026-03-13": e429})
    with caplog.at_level(logging.DEBUG):
        rc = rodar(factory, cliente(api), "--desde", "2026-03-10", "--ate", "2026-03-15")
    saida = capsys.readouterr()
    assert rc == 4 and "2026-03-14" not in api.chamadas  # nao tentou as noites seguintes
    assert set(_linhas(engine)) == {D(2026, 3, 10), D(2026, 3, 11), D(2026, 3, 12)}  # o que veio, ficou
    assert "falhas=1" in saida.out and MARCADOR not in saida.out + saida.err + caplog.text


def test_falha_de_rede_numa_noite_nao_perde_as_outras(engine, factory, atleta, capsys):
    api = ApiFalsa(erros={"2026-03-11": e502})
    assert rodar(factory, cliente(api), "--desde", "2026-03-10", "--ate", "2026-03-12") == 5
    assert set(_linhas(engine)) == {D(2026, 3, 10), D(2026, 3, 12)}  # a de 11/3 fica sem linha: a proxima rodada a refaz
    saida = capsys.readouterr()
    assert "falhas=1" in saida.out and "sem_dado=0" in saida.out and MARCADOR not in saida.out + saida.err


def test_tres_falhas_seguidas_param_a_execucao(engine, factory, atleta, capsys):
    api = ApiFalsa(erros={f"2026-03-{d}": e502 for d in range(10, 16)})
    assert rodar(factory, cliente(api), "--desde", "2026-03-10", "--ate", "2026-03-15") == 5
    assert len(api.chamadas) == br.FALHAS_SEGUIDAS_MAX == 3
    assert "aviso: parou_por_falhas_seguidas" in capsys.readouterr().out and _linhas(engine) == {}


def test_precedencia_dos_codigos_limite_antes_de_rede(engine, factory, atleta):
    api = ApiFalsa(erros={"2026-03-10": e502, "2026-03-11": e429})
    assert rodar(factory, cliente(api), "--desde", "2026-03-10", "--ate", "2026-03-12") == 4


def test_sessao_recusada_no_meio_para_com_2(engine, factory, atleta):
    api = ApiFalsa(erros={"2026-03-11": _Erros.GarminConnectAuthenticationError})
    assert rodar(factory, cliente(api), "--desde", "2026-03-10", "--ate", "2026-03-12") == 2
    assert api.chamadas == ["2026-03-10", "2026-03-11"] and set(_linhas(engine)) == {D(2026, 3, 10)}


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


def test_o_comando_nao_conhece_campos_do_garmin_nem_rotas_de_faixa():
    """O nome de campo do Garmin nunca sai do cliente: o comando nao conhece `dailySleepDTO`, nem pede faixa."""
    fonte = Path(br.__file__).read_text()
    for campo in ("dailySleepDTO", "hrvSummaries", "sleepTimeSeconds", "avgOvernightHrv", "restingHeartRate", "garminconnect",
                  "get_hrv_data_range", "get_rhr_daily", "BLOCO"):
        assert campo not in fonte
    assert garmin_cliente.VERSAO_LEITURA == "recuperacao_leitura@1"
