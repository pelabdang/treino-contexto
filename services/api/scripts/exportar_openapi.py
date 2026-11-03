"""Exporta o contrato da API para `packages/api-client/` (issue #68, ADR 0004 item 6).

    uv run python services/api/scripts/exportar_openapi.py

Grava, sem subir servidor:
  packages/api-client/openapi.json                        (`app.openapi()`)
  packages/api-client/exemplos/evolucao-tiros-1km.json    (resposta do TestClient com as fixtures sintéticas, atleta 1)
Depois gere os tipos: `cd packages/api-client && npm run gerar` (ver docs/modulos/api-client.md).
O teste `services/api/tests/test_contrato_cliente.py` falha se algum destes arquivos ficar desatualizado.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]
PACOTE = RAIZ / "packages" / "api-client"
OPENAPI = PACOTE / "openapi.json"
EXEMPLO = PACOTE / "exemplos" / "evolucao-tiros-1km.json"
TIPOS = PACOTE / "src" / "schema.d.ts"
ZIP_FIXTURES = RAIZ / "tests" / "fixtures" / "garmin" / "exportacao_minima.zip"
COMANDO = "uv run python services/api/scripts/exportar_openapi.py && (cd packages/api-client && npm run gerar)"


def _json(obj, ordenar: bool = False) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=ordenar) + "\n"


def texto_openapi() -> str:
    from app.main import app

    return _json(app.openapi(), ordenar=True)


def texto_exemplo() -> str:
    """Resposta real do endpoint sobre um banco SQLite em memória com as fixtures importadas."""
    from app.db import models  # noqa: F401
    from app.db.base import Base
    from app.db.models import Atleta
    from app.db.session import get_session
    from app.main import app
    from fastapi.testclient import TestClient
    from sqlalchemy import create_engine
    from sqlalchemy.pool import StaticPool
    from sqlalchemy.orm import Session
    from worker.importar_garmin import importar

    engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        importar(session, ZIP_FIXTURES, "Atleta Ficticio")
        atleta = session.query(Atleta).one()
        app.dependency_overrides[get_session] = lambda: session
        try:
            r = TestClient(app).get(f"/atletas/{atleta.id}/evolucao/tiros-1km")
        finally:
            app.dependency_overrides.pop(get_session, None)
    r.raise_for_status()
    return _json(r.json())


def hash_openapi(texto: str) -> str:
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def main() -> None:
    OPENAPI.write_text(texto_openapi(), encoding="utf-8")
    EXEMPLO.parent.mkdir(parents=True, exist_ok=True)
    EXEMPLO.write_text(texto_exemplo(), encoding="utf-8")
    print(f"gravado: {OPENAPI}\ngravado: {EXEMPLO}\nagora: cd packages/api-client && npm run gerar")


if __name__ == "__main__":
    main()
