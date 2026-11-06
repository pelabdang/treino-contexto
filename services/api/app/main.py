from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import lista_origens, settings
from app.rotas import atividades, evolucao, transicao


def criar_app(cors_origens: str | None = None) -> FastAPI:
    """Monta o app. `cors_origens` (padrão: `CORS_ORIGENS` do ambiente) lista as origens liberadas, para GET, POST (upload de FIT), PUT e DELETE (correção da transição)."""
    app = FastAPI(title="treino-contexto API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=lista_origens(settings.cors_origens if cors_origens is None else cors_origens),
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=[],
        allow_credentials=False,
    )
    app.include_router(evolucao.router)
    app.include_router(atividades.router)
    app.include_router(transicao.router)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = criar_app()
