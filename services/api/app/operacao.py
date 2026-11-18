"""Operacao da API no servidor: log de acesso sem dado de saude e erros sem eco (issue #504, ADR 0016, item 9).

Permitido em log: metodo, caminho COM ids, status e duracao. Proibido: query string, corpo, cabecalhos (`Authorization`), senha, e-mail,
check-in, observacao, feedback, carga, FC, posicao. Por isso o servidor sobe com `uvicorn --no-access-log` (o log de acesso dele grava a query
string) e este middleware escreve a linha de acesso no lugar.

- `LogDeAcesso`: uma linha `acesso metodo caminho status duracao_ms` por requisicao HTTP (sem query string).
- Em `producao` ele tambem pega a excecao nao tratada: loga so o TIPO e o LOCAL (`arquivo:linha`), nunca a mensagem (ela pode ter dado de
  saude), e responde um 500 de texto fixo. Fora da producao a excecao segue o caminho normal (traceback completo, util no teste).
- `422_sem_eco`: o 422 padrao do FastAPI devolve o campo `input` (a senha ou a observacao digitada). Aqui so `loc`, `msg` e `type`.
"""

from __future__ import annotations

import json
import logging
import time
import traceback

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

log = logging.getLogger("app.acesso")
if not log.handlers:  # sob o uvicorn so os loggers dele sao configurados; sem isto a linha de acesso nao sai
    _h = logging.StreamHandler()
    _h.setFormatter(logging.Formatter("%(levelname)s %(name)s %(message)s"))
    log.addHandler(_h)
    log.setLevel(logging.INFO)

MSG_500 = "erro ao processar o pedido"


class LogDeAcesso:
    def __init__(self, app, neutralizar_erros: bool = False) -> None:
        self.app = app
        self.neutralizar_erros = neutralizar_erros

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        inicio = time.perf_counter()
        estado = {"status": 0, "iniciou": False}

        async def send_(msg):
            if msg["type"] == "http.response.start":
                estado["status"] = msg["status"]
                estado["iniciou"] = True
            await send(msg)

        try:
            await self.app(scope, receive, send_)
        except Exception as e:  # noqa: BLE001
            if not self.neutralizar_erros:
                raise
            ultimo = traceback.extract_tb(e.__traceback__)[-1] if e.__traceback__ else None
            local = f"{ultimo.filename.rsplit('/', 1)[-1]}:{ultimo.lineno}" if ultimo else "?"
            log.error("erro nao tratado tipo=%s local=%s", type(e).__name__, local)  # nunca a mensagem
            if not estado["iniciou"]:
                corpo = json.dumps({"detail": MSG_500}).encode()
                await send_({"type": "http.response.start", "status": 500,
                             "headers": [(b"content-type", b"application/json"), (b"content-length", str(len(corpo)).encode())]})
                await send_({"type": "http.response.body", "body": corpo})
        finally:
            ms = round((time.perf_counter() - inicio) * 1000)
            log.info("acesso %s %s %s %sms", scope["method"], scope["path"], estado["status"], ms)  # path sem query string


async def validacao_sem_eco(_: Request, exc: RequestValidationError) -> JSONResponse:
    """422 so com `loc`, `msg` e `type`: sem `input` (eco do que foi digitado) e sem `ctx`."""
    return JSONResponse(status_code=422, content={"detail": [{"loc": list(e["loc"]), "msg": e["msg"], "type": e["type"]} for e in exc.errors()]})
