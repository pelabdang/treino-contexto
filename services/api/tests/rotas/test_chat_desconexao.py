"""Se o cliente desconecta no meio do POST sincrono, a mensagem e gravada mesmo assim e aparece no GET (#598, pedido da spec da Lia).

A rota e `def`: o FastAPI a roda numa thread e o Starlette nao a cancela na desconexao. Os dois testes provam isso direto no ASGI, sem
o `TestClient` (que nao simula desconexao): (1) o servidor avisa `http.disconnect` e a escrita da resposta falha; (2) a tarefa da requisicao
e CANCELADA enquanto o provedor ainda responde. Sintetico, sem rede.
"""

import asyncio
import json
import threading

import pytest
from app.db.models import Mensagem
from app.db.session import get_session
from app.llm.camada import ChamadaFerramenta, ProvedorFalso, Redator, RespostaConversa
from app.main import criar_app
from app.rotas.chat import get_redator
from fastapi.testclient import TestClient

from tests.rotas.test_chat import SENHA, _h, mundo  # noqa: F401


class ProvedorLento(ProvedorFalso):
    """Espera o teste liberar, para a desconexao acontecer com a pergunta em andamento."""

    def __init__(self, texto: str) -> None:
        super().__init__(roteiro=[])
        self.texto, self.comecou, self.liberar = texto, threading.Event(), threading.Event()

    def conversar(self, mensagens, ferramentas, timeout_s):
        self.comecou.set()
        assert self.liberar.wait(10)
        return RespostaConversa(texto=self.texto)


@pytest.fixture
def lento():
    return ProvedorLento("Nenhum número aqui, só um texto de teste.")


@pytest.fixture
def app(session, lento):
    a = criar_app("http://localhost:8081")
    a.dependency_overrides[get_session] = lambda: session
    a.dependency_overrides[get_redator] = lambda: Redator(lento, "falso", "falso-1")
    return a


@pytest.fixture
def client(app):
    return TestClient(app, raise_server_exceptions=False)


def _escopo(caminho, token):
    return {"type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1", "method": "POST", "scheme": "http", "path": caminho, "raw_path": caminho.encode(),
            "query_string": b"", "server": ("teste", 80), "client": ("1.2.3.4", 1), "root_path": "",
            "headers": [(b"host", b"teste"), (b"content-type", b"application/json"), (b"authorization", f"Bearer {token}".encode())]}


def _token(client):
    return _h(client, "ana")["Authorization"].split()[1]


def _gravadas(session):
    session.expire_all()
    return session.query(Mensagem).all()


def test_cancelada_no_meio_a_mensagem_e_gravada_e_aparece_no_get(app, client, session, mundo, lento):  # noqa: F811
    token = _token(client)
    corpo = json.dumps({"pergunta": "Pergunta que sera interrompida?"}).encode()
    entregue = False

    async def receive():
        nonlocal entregue
        if not entregue:
            entregue = True
            return {"type": "http.request", "body": corpo, "more_body": False}
        await asyncio.sleep(3600)

    async def send(_msg):
        pass

    async def cena():
        tarefa = asyncio.ensure_future(app(_escopo(f"/atletas/{mundo['ana']}/conversas", token), receive, send))
        await asyncio.get_running_loop().run_in_executor(None, lento.comecou.wait, 5)
        tarefa.cancel()  # o servidor desistiu da requisicao com o provedor ainda respondendo
        lento.liberar.set()
        try:
            await tarefa
        except asyncio.CancelledError:
            pass
        await asyncio.sleep(1.0)  # a thread da rota termina e grava

    asyncio.run(cena())
    gravadas = _gravadas(session)
    assert len(gravadas) == 1, "a mensagem NAO foi gravada depois da desconexao"
    assert gravadas[0].estado == "respondida" and gravadas[0].pergunta == "Pergunta que sera interrompida?"
    lista = client.get(f"/atletas/{mundo['ana']}/conversas", headers=_h(client, "ana")).json()["conversas"]
    assert len(lista) == 1
    detalhe = client.get(f"/atletas/{mundo['ana']}/conversas/{lista[0]['id']}", headers=_h(client, "ana")).json()
    assert [m["pergunta"] for m in detalhe["mensagens"]] == ["Pergunta que sera interrompida?"]


def test_cliente_que_some_antes_da_resposta_nao_perde_a_mensagem(app, client, session, mundo, lento):  # noqa: F811
    token = _token(client)
    corpo = json.dumps({"pergunta": "Outra pergunta?"}).encode()
    chamadas = {"receive": 0}

    async def receive():
        chamadas["receive"] += 1
        if chamadas["receive"] == 1:
            return {"type": "http.request", "body": corpo, "more_body": False}
        await asyncio.get_running_loop().run_in_executor(None, lento.comecou.wait, 5)
        return {"type": "http.disconnect"}  # o servidor avisa que o cliente foi embora

    async def send(_msg):
        raise OSError("cliente desconectado")  # escrever a resposta falha

    lento.liberar.set()

    async def cena():
        try:
            await app(_escopo(f"/atletas/{mundo['ana']}/conversas", token), receive, send)
        except OSError:
            pass

    asyncio.run(cena())
    assert len(_gravadas(session)) == 1
