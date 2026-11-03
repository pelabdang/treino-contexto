"""Clima das atividades: tabela, estados, comando idempotente (Meta 4, issue #113; ADR 0007 itens 2, 3, 6, 7 e 8).

Nenhuma chamada de rede: o cliente real usa `httpx.MockTransport` e os outros testes, um cliente falso. A guarda de
socket (a mesma da #112) derruba qualquer teste que tente abrir conexao. Dados inventados (Parque do Exemplo).
"""

import hashlib
import json
import os
import socket
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
import pytest
from app.clima import ClienteOpenMeteo, ClimaMedio, ResultadoClima
from app.db import models  # noqa: F401
from app.db.base import Base
from app.db.models import Atividade, Atleta, ClimaAtividade
from app.ingestao.importacao import importar, importar_fit
from app.servicos.clima import (
    MAX_RODADAS,
    clima_da_atividade,
    contar_estados,
    entrada_de,
    preencher_clima,
    preencher_posicoes,
)
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from worker.importar_garmin import clima_do_que_mudou
from worker.preencher_clima import imprimir, rodar

RAIZ = Path(__file__).resolve().parents[3]
FIXTURES = RAIZ / "tests" / "fixtures" / "clima"
EXPORTACAO = FIXTURES / "exportacao_clima.json"
ORACULO = json.loads((FIXTURES / "oraculo_clima.json").read_text())
RESPOSTA = json.loads((FIXTURES / ORACULO["respostas"]["normal"]).read_text())
CLIMA_ESPERADO = next(c for c in ORACULO["casos"] if c["id"] == "json_corrida_ar_livre")["clima"]
AGORA = datetime(2026, 11, 3, 12, 0, tzinfo=timezone.utc)
INICIO = datetime(2026, 5, 10, 9, 20, tzinfo=timezone.utc)
CLIMA = ClimaMedio(20.0, 21.0, 60.0, 10.0)


@pytest.fixture(autouse=True)
def sem_rede(monkeypatch):
    """Como na #112, mas deixa passar o Postgres local do CI (127.0.0.1 / localhost): so rede de fora e bloqueada."""
    locais = ("localhost", "127.0.0.1", "::1")
    connect, create, getaddr = socket.socket.connect, socket.create_connection, socket.getaddrinfo

    def bloqueia(host):
        raise AssertionError(f"teste tentou abrir conexao de rede ({'host nao local' if host else 'sem host'})")

    def _host(endereco):
        return endereco[0] if isinstance(endereco, tuple) else endereco

    def connect_(self, endereco, *a, **k):
        if _host(endereco) not in locais and self.family != socket.AF_UNIX:
            bloqueia(True)
        return connect(self, endereco, *a, **k)

    def create_(endereco, *a, **k):
        if _host(endereco) not in locais:
            bloqueia(True)
        return create(endereco, *a, **k)

    def getaddr_(host, *a, **k):
        if host not in locais and host is not None:
            bloqueia(True)
        return getaddr(host, *a, **k)

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
def session(engine):
    with Session(engine) as s:
        yield s


@pytest.fixture
def atleta(session):
    a = Atleta(nome="Atleta Ficticio")
    session.add(a)
    session.commit()
    return a


class Falso:
    """Cliente falso: responde na ordem da lista (a ultima se repete) e guarda as chamadas."""

    def __init__(self, *respostas):
        self.respostas = list(respostas) or [ResultadoClima("ok", CLIMA)]
        self.chamadas = []

    def buscar(self, lat, lon, inicio, duracao_s):
        self.chamadas.append((lat, lon, inicio, duracao_s))
        return self.respostas[min(len(self.chamadas), len(self.respostas)) - 1]


def ativ(session, atleta, n=1, inicio=INICIO, duracao_s=3000.0, lat=12.35, lon=-45.68, subtipo=None, **extra):
    a = Atividade(atleta_id=atleta.id, fonte="garmin_export", fonte_id=f"x{atleta.id}-{n}", modalidade="corrida",
                  subtipo=subtipo, inicio=inicio + timedelta(days=n), duracao_s=duracao_s, inicio_lat=lat,
                  inicio_lon=lon, **extra)
    session.add(a)
    session.commit()
    return a


def linha(session, a):
    return session.scalars(select(ClimaAtividade).where(ClimaAtividade.atividade_id == a.id)).first()


def rodada(session, cliente, **kw):
    kw.setdefault("agora", AGORA)
    kw.setdefault("dormir", lambda s: None)
    return preencher_clima(session, cliente, **kw)


# ---------- exportacao inteira com o cliente real (transporte falso) ----------

def _cliente_real(chamadas):
    def atende(req: httpx.Request) -> httpx.Response:
        chamadas.append(req)
        return httpx.Response(200, json=RESPOSTA)

    return ClienteOpenMeteo(transporte=httpx.MockTransport(atende), dormir=lambda s: None)


def test_exportacao_inteira_e_rodar_duas_vezes_nao_repete_chamada(session):
    importar(session, EXPORTACAO, "Atleta Ficticio")
    chamadas = []
    cliente = _cliente_real(chamadas)

    r1 = rodada(session, cliente)
    assert r1.chamadas == 1 and len(chamadas) == 1  # so a corrida ao ar livre com posicao
    a = session.scalars(select(Atividade).where(Atividade.fonte_id == "3000000101")).one()
    c = clima_da_atividade(session, a.id)
    assert c.estado == "ok"
    for campo, valor in CLIMA_ESPERADO.items():
        assert getattr(c, campo) == pytest.approx(valor, abs=1e-6)
    linha_ok = linha(session, a)
    assert linha_ok.fonte == "open-meteo-archive" and linha_ok.entrada == entrada_de(a) and len(linha_ok.entrada) == 64

    r2 = rodada(session, cliente)
    assert r2.chamadas == 0 and len(chamadas) == 1
    assert session.scalar(select(func.count()).select_from(ClimaAtividade)) == 1
    assert contar_estados(session) == {"ok": 1, "indoor": 2, "sem_posicao": 2, "pendente": 0, "falha": 0}


def test_importar_nao_chama_a_rede_e_lista_o_que_mudou(session):
    rel = importar(session, EXPORTACAO, "Atleta Ficticio")
    assert len(rel.ids_alterados) == 5
    assert importar(session, EXPORTACAO, "Atleta Ficticio").ids_alterados == []


def test_fim_da_importacao_busca_so_o_que_mudou_e_nunca_derruba(session, engine, capsys):
    rel = importar(session, EXPORTACAO, "Atleta Ficticio")
    cliente = Falso()
    clima_do_que_mudou(rel, cliente, lambda: Session(engine))
    assert len(cliente.chamadas) == 1
    clima_do_que_mudou(importar(session, EXPORTACAO, "Atleta Ficticio"), cliente, lambda: Session(engine))
    assert len(cliente.chamadas) == 1  # nada mudou: nem sessao nem chamada

    class Quebra:
        def buscar(self, *a):
            raise RuntimeError("falhou")

    session.query(ClimaAtividade).delete()
    session.commit()
    clima_do_que_mudou(rel, Quebra(), lambda: Session(engine))  # nao levanta
    assert "clima nao preenchido" in capsys.readouterr().err


# ---------- estados calculados na leitura ----------

def test_indoor_e_sem_posicao_nao_tem_linha_nem_chamada(session, atleta):
    esteira = ativ(session, atleta, 1, subtipo="esteira", lat=None, lon=None)
    piscina = ativ(session, atleta, 2, subtipo="piscina", lat=None, lon=None)
    virtual = ativ(session, atleta, 3, subtipo="virtual", lat=12.35, lon=-45.68)  # indoor vence, mesmo com posicao
    sem = ativ(session, atleta, 4, lat=None, lon=None)
    cliente = Falso()
    assert rodada(session, cliente).chamadas == 0 and cliente.chamadas == []
    assert session.scalar(select(func.count()).select_from(ClimaAtividade)) == 0
    assert [clima_da_atividade(session, x.id).estado for x in (esteira, piscina, virtual, sem)] == [
        "indoor", "indoor", "indoor", "sem_posicao"]
    assert clima_da_atividade(session, 99999) is None


def test_pendente_dentro_dos_7_dias_nao_consulta_nem_conta_rodada(session, atleta):
    a = ativ(session, atleta, 0)
    cliente = Falso()
    inicio = a.inicio.replace(tzinfo=timezone.utc)
    recente = inicio + timedelta(days=6)  # fim ainda dentro dos 7 dias
    for _ in range(MAX_RODADAS + 2):
        assert rodada(session, cliente, agora=recente).chamadas == 0
    assert linha(session, a) is None and clima_da_atividade(session, a.id).estado == "pendente"
    assert rodada(session, cliente, agora=inicio + timedelta(days=8)).chamadas == 1


# ---------- rodadas, falhas, parar ----------

def test_cinco_rodadas_pendentes_viram_falha(session, atleta):
    a = ativ(session, atleta)
    cliente = Falso(ResultadoClima("pendente", erro="tempo esgotado"))
    for n in range(1, MAX_RODADAS):
        rodada(session, cliente)
        assert (linha(session, a).estado, linha(session, a).tentativas) == ("pendente", n)
    rodada(session, cliente)
    l = linha(session, a)
    assert (l.estado, l.tentativas) == ("falha", MAX_RODADAS) and "tempo esgotado" in l.erro
    assert rodada(session, cliente).chamadas == 0 and len(cliente.chamadas) == MAX_RODADAS


def test_falha_so_e_refeita_com_refazer_falhas(session, atleta):
    a = ativ(session, atleta)
    cliente = Falso(ResultadoClima("falha", erro="HTTP 400"), ResultadoClima("ok", CLIMA))
    rodada(session, cliente)
    assert linha(session, a).estado == "falha" and linha(session, a).erro == "HTTP 400"
    assert rodada(session, cliente).chamadas == 0
    assert rodada(session, cliente, refazer_falhas=True).chamadas == 1
    l = linha(session, a)
    assert l.estado == "ok" and l.erro is None and l.temperatura_c == 20.0 and l.tentativas == 1


def test_parar_rodada_para_e_guarda_o_que_ja_foi_feito(session, atleta):
    a1, a2, a3 = (ativ(session, atleta, n) for n in (1, 2, 3))
    cliente = Falso(ResultadoClima("ok", CLIMA), ResultadoClima("pendente", erro="HTTP 429", parar_rodada=True))
    rel = rodada(session, cliente)
    assert rel.parou and rel.chamadas == 2 and len(cliente.chamadas) == 2
    session.rollback()  # um commit por atividade: nada se perde
    assert linha(session, a1).estado == "ok" and linha(session, a2).estado == "pendente"
    assert linha(session, a3) is None


def test_entrada_diferente_refaz_e_igual_nao(session, atleta):
    a = ativ(session, atleta)
    cliente = Falso()
    rodada(session, cliente)
    antes = linha(session, a).entrada
    a.duracao_s += 600
    session.commit()
    assert entrada_de(a) != antes
    assert clima_da_atividade(session, a.id).estado == "pendente"  # a linha ok e de outra entrada
    assert rodada(session, cliente).chamadas == 1 and linha(session, a).entrada == entrada_de(a)
    a.inicio_lat = 13.0
    session.commit()
    assert rodada(session, cliente).chamadas == 1 and len(cliente.chamadas) == 3
    assert rodada(session, cliente).chamadas == 0


def test_limite_pausa_e_filtros(session, atleta):
    outro = Atleta(nome="Outro Ficticio")
    session.add(outro)
    session.commit()
    a1, a2, a3 = (ativ(session, atleta, n) for n in (1, 2, 3))
    ativ(session, outro, 4)
    pausas = []
    cliente = Falso()
    rel = rodada(session, cliente, atleta_id=atleta.id, limite=2, dormir=pausas.append)
    assert rel.chamadas == 2 and rel.atingiu_limite and pausas == [0.25]
    assert linha(session, a3) is None
    rel = rodada(session, cliente, atividade_ids=[a3.id])
    assert rel.chamadas == 1 and linha(session, a3).estado == "ok"
    assert [c[0] for c in cliente.chamadas] == [12.35] * 3


def test_so_envia_posicao_e_horario(session, atleta):
    a = ativ(session, atleta)
    cliente = Falso()
    rodada(session, cliente)
    assert cliente.chamadas == [(12.35, -45.68, a.inicio.replace(tzinfo=timezone.utc), 3000)]


# ---------- posicao: relendo o FIT guardado e a exportacao ----------

def _guardar(fit_dir, atleta, nome="corrida_ar_livre.fit"):
    dados = (FIXTURES / "fit" / nome).read_bytes()
    rel = f"{atleta.id}/{hashlib.sha256(dados).hexdigest()}.fit"
    (fit_dir / str(atleta.id)).mkdir(parents=True)
    (fit_dir / rel).write_bytes(dados)
    return rel


def test_posicao_relendo_o_fit_guardado(session, atleta, tmp_path):
    rel = _guardar(tmp_path, atleta)
    a = ativ(session, atleta, 1, lat=None, lon=None, arquivo_bruto=rel)
    sem_arquivo = ativ(session, atleta, 2, lat=None, lon=None, arquivo_bruto=f"{atleta.id}/{'0' * 64}.fit")
    do_zip = ativ(session, atleta, 3, lat=None, lon=None, arquivo_bruto="x.zip!/DI_CONNECT/a.fit")
    ja_tem = ativ(session, atleta, 4, lat=40.0, lon=10.0, arquivo_bruto=rel)  # nunca sobrescreve
    indoor = ativ(session, atleta, 5, lat=None, lon=None, subtipo="esteira", arquivo_bruto=rel)
    assert preencher_posicoes(session, fit_dir=tmp_path) == 1
    for x in (a, sem_arquivo, do_zip, ja_tem, indoor):
        session.refresh(x)
    assert (a.inicio_lat, a.inicio_lon) == (12.35, -45.68)
    assert sem_arquivo.inicio_lat is None and do_zip.inicio_lat is None and indoor.inicio_lat is None
    assert (ja_tem.inicio_lat, ja_tem.inicio_lon) == (40.0, 10.0)
    assert preencher_posicoes(session, fit_dir=tmp_path) == 0


def test_posicao_relendo_a_exportacao(session):
    importar(session, EXPORTACAO, "Atleta Ficticio")
    a = session.scalars(select(Atividade).where(Atividade.fonte_id == "3000000101")).one()
    a.inicio_lat = a.inicio_lon = None  # como uma atividade importada antes da Meta 4
    session.commit()
    assert preencher_posicoes(session) == 0  # sem exportacao nem FIT guardado
    assert preencher_posicoes(session, exportacao=EXPORTACAO) == 1
    session.refresh(a)
    assert (a.inicio_lat, a.inicio_lon) == (12.35, -45.68)
    assert session.scalars(select(Atividade).where(Atividade.subtipo == "esteira")).one().inicio_lat is None


def test_so_posicao_nao_usa_a_rede_e_imprime(session, atleta, tmp_path, capsys):
    rel = _guardar(tmp_path, atleta)
    ativ(session, atleta, 1, lat=None, lon=None, arquivo_bruto=rel)
    ativ(session, atleta, 2, subtipo="piscina", lat=None, lon=None)
    posicoes, estados, relatorio = rodar(session, None, so_posicao=True, fit_dir=tmp_path)
    assert posicoes == 1 and relatorio is None and session.scalar(select(func.count()).select_from(ClimaAtividade)) == 0
    imprimir(posicoes, estados, relatorio)
    saida = capsys.readouterr().out
    assert "posicoes preenchidas=1" in saida and "pendente=1" in saida and "indoor=1" in saida
    assert "12.35" not in saida


def test_rodar_completo_imprime_estados(session, atleta, tmp_path, capsys):
    ativ(session, atleta, 1)
    posicoes, estados, relatorio = rodar(session, Falso(), fit_dir=tmp_path, dormir=lambda s: None)
    imprimir(posicoes, estados, relatorio)
    saida = capsys.readouterr().out
    assert "chamadas=1" in saida and "ok=1" in saida and estados["ok"] == 1


# ---------- upload nao chama a rede ----------

def test_upload_de_fit_grava_sem_clima_e_sem_rede(session, atleta, tmp_path):
    r = importar_fit(session, atleta.id, (FIXTURES / "fit" / "corrida_ar_livre.fit").read_bytes(), tmp_path)
    assert r.resultado == "inserida"
    assert session.scalar(select(func.count()).select_from(ClimaAtividade)) == 0
    assert clima_da_atividade(session, r.atividade_id).estado == "pendente"


def test_a_guarda_pega_o_cliente_sem_transporte_falso():
    with pytest.raises(AssertionError, match="rede"):
        ClienteOpenMeteo(dormir=lambda s: None).buscar(12.35, -45.68, INICIO, 3000)
