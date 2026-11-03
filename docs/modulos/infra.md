---
tipo: modulo
status: em-uso
dono: theo
atualizado: 2026-11-03
links: [[modulos/banco]], [[modulos/api]], [[decisoes/0004-contrato-tela-evolucao]]
---
# Módulo: infra

## Para que serve
Ambiente local e CI. Postgres 16 em Docker Compose. Produção futura: DigitalOcean.

## Entradas e saídas
- Subir: `docker compose -f infra/docker-compose.yml up -d`.
- Variáveis `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` (padrão `treino`). Porta 5432, volume `pgdata`.
- `.env.example` lista `DATABASE_URL`, `CORS_ORIGENS`, `LLM_PROVIDER` e `LLM_MODEL` (IA sempre por camada trocável).
- `CORS_ORIGENS`: origens do app web liberadas na API, separadas por vírgula. Padrão `http://localhost:8081`
  (`npx expo start --web`). Nunca `*` (a API recusa subir). Vazia não libera nenhuma. iOS e Android não precisam de CORS.
  Ver [[modulos/api]] e [[decisoes/0004-contrato-tela-evolucao]].

- Cuidado: o compose tem `name: treino-contexto`; sem `-p` ele reusa o volume `treino-contexto_pgdata`. Com porta 5432 ocupada, veja [[produto/meta-2-como-rodar]].

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
