from fastapi import FastAPI

from app.rotas import evolucao

app = FastAPI(title="treino-contexto API", version="0.1.0")
app.include_router(evolucao.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
