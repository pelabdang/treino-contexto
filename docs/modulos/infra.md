---
tipo: modulo
status: em-uso
dono: theo
atualizado: 2026-10-31
links: [[modulos/banco]], [[modulos/api]]
---
# Módulo: infra

## Para que serve
Ambiente local e CI. Postgres 16 em Docker Compose. Produção futura: DigitalOcean.

## Entradas e saídas
- Subir: `docker compose -f infra/docker-compose.yml up -d`.
- Variáveis `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` (padrão `treino`). Porta 5432, volume `pgdata`.
- `.env.example` lista `DATABASE_URL`, `LLM_PROVIDER` e `LLM_MODEL` (IA sempre por camada trocável).

## Arquivos principais
- `infra/docker-compose.yml`
- `.github/workflows/testes.yml`: CI `testes` (Postgres de serviço, `alembic upgrade head` e `downgrade base`, pytest, `npm test`).
- `.claude/hooks/testes.sh`

## Depende de
- Usado por [[modulos/banco]] e [[modulos/api]].

## Como testar
O CI `testes` valida tudo. Localmente: `uv run pytest -q`.

## Pendências
- Serviços api e worker no compose, quando houver necessidade.
