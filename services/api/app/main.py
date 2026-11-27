from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.autenticacao import atleta_da_sessao
from app.config import lista_origens, settings
from app.rotas import atividades, caixa_do_dia, carga, checkin, consentimento, evolucao, inicio, lista_atividades, professor, semana_padrao, sessao, transicao


def criar_app(cors_origens: str | None = None) -> FastAPI:
    """Monta o app. `cors_origens` (padrão: `CORS_ORIGENS` do ambiente) lista as origens liberadas, para GET, POST (upload de FIT), PUT e DELETE (correção da transição)."""
    app = FastAPI(title="treino-contexto API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=lista_origens(settings.cors_origens if cors_origens is None else cors_origens),
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],  # o Bearer e o JSON; nada mais (#527). Sem credentials e sem "*"
        allow_credentials=False,
    )
    app.include_router(evolucao.router, dependencies=[Depends(atleta_da_sessao)])
    app.include_router(lista_atividades.router, dependencies=[Depends(atleta_da_sessao)])
    app.include_router(inicio.router, dependencies=[Depends(atleta_da_sessao)])
    app.include_router(atividades.router, dependencies=[Depends(atleta_da_sessao)])
    app.include_router(transicao.router, dependencies=[Depends(atleta_da_sessao)])
    app.include_router(carga.router, dependencies=[Depends(atleta_da_sessao)])
    app.include_router(checkin.router, dependencies=[Depends(atleta_da_sessao)])
    app.include_router(checkin.router_pendentes, dependencies=[Depends(atleta_da_sessao)])
    app.include_router(semana_padrao.router, dependencies=[Depends(atleta_da_sessao)])
    app.include_router(consentimento.router, dependencies=[Depends(atleta_da_sessao)])
    app.include_router(consentimento.router_termo)
    app.include_router(professor.router)
    app.include_router(caixa_do_dia.router)
    app.include_router(sessao.router)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = criar_app()
