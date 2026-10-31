# treino-contexto

App de análise de treinos com contexto. Regras do time: [AGENTS.md](AGENTS.md).
Plano: [docs/produto/plano-mvp-execucao.md](docs/produto/plano-mvp-execucao.md).

## Estrutura

    apps/mobile/        app Expo (iOS, Android, web)
    services/api/       API FastAPI, modelo de dados (SQLAlchemy) e migrações (Alembic)
    services/worker/    worker de ingestão e processamento
    infra/              docker-compose com Postgres
    tests/fixtures/     amostras pequenas e anonimizadas para testes

## Rodar local

    uv sync                                          # backend (Python 3.12)
    docker compose -f infra/docker-compose.yml up -d # Postgres
    cp .env.example .env
    (cd services/api && uv run alembic upgrade head)
    uv run uvicorn app.main:app --app-dir services/api --reload
    uv run pytest -q                                 # testes do backend
    cd apps/mobile && npm install && npx expo start  # app
    npm test --prefix apps/mobile                    # testes do app

Sem Postgres, os testes do backend usam SQLite em memória. No CI rodam contra Postgres 16.
