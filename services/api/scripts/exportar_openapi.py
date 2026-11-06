"""Exporta o contrato da API para `packages/api-client/` (issue #68, ADR 0004 item 6).

    uv run python services/api/scripts/exportar_openapi.py

Grava, sem subir servidor:
  packages/api-client/openapi.json                        (`app.openapi()`)
  packages/api-client/exemplos/evolucao-tiros-1km.json    (resposta do TestClient com as fixtures sintéticas, atleta 1)
  packages/api-client/exemplos/atividade-esforcos.json    (a atividade com `esforcos`, FIT sintético da #161)
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
EXEMPLO_ESFORCOS = PACOTE / "exemplos" / "atividade-esforcos.json"
FIT_ESFORCOS = RAIZ / "tests" / "fixtures" / "garmin" / "esforcos" / "esforcos_corrida_1500_lap_automatico.fit"
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


def texto_exemplo_esforcos() -> str:
    """A atividade com `esforcos` (FIT sintético da #161, com uma corrida de histórico a 5:30 por km)."""
    from app.db import models  # noqa: F401
    from app.db.base import Base
    from datetime import datetime, timezone

    from app.db.models import Atividade, Atleta
    from app.db.session import get_session
    from app.ingestao.garmin import ler_atividade_fit
    from app.ingestao.importacao import duracao_da, gravar_atividade
    from app.main import app
    from app.servicos.esforcos import detectar_esforcos
    from fastapi.testclient import TestClient
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from sqlalchemy.pool import StaticPool

    engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        atleta = Atleta(nome="Atleta Ficticio")
        session.add(atleta)
        session.commit()
        session.add(Atividade(
            atleta_id=atleta.id, fonte="teste", fonte_id="historico", modalidade="corrida",
            inicio=datetime(2025, 1, 1, 8, tzinfo=timezone.utc), duracao_s=1650.0, distancia_m=5000.0,
        ))
        session.commit()
        a = ler_atividade_fit(FIT_ESFORCOS.read_bytes(), fonte="fit_upload")
        _, ativ, _ = gravar_atividade(session, atleta.id, a, duracao_da(a), [])
        session.commit()
        detectar_esforcos(session, atleta.id)
        app.dependency_overrides[get_session] = lambda: session
        try:
            r = TestClient(app).get(f"/atletas/{atleta.id}/atividades/{ativ.id}")
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
    EXEMPLO_ESFORCOS.write_text(texto_exemplo_esforcos(), encoding="utf-8")
    print(f"gravado: {OPENAPI}\ngravado: {EXEMPLO}\ngravado: {EXEMPLO_ESFORCOS}\nagora: cd packages/api-client && npm run gerar")


if __name__ == "__main__":
    main()
