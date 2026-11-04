---
tipo: modulo
status: em-uso
dono: theo
atualizado: 2026-11-04
links: [[modulos/banco]], [[modulos/api]], [[decisoes/0004-contrato-tela-evolucao]], [[decisoes/0006-upload-de-fit]], [[produto/meta-2-como-rodar]]
---
# Módulo: infra

## Para que serve
Ambiente local e CI. Postgres 16 em Docker Compose. Produção futura: DigitalOcean.

## Entradas e saídas
- Subir: `docker compose -f infra/docker-compose.yml up -d`.
- Variáveis `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` (padrão `treino`). Porta do host **5433** (dentro do container segue 5432), volume `pgdata`.
- `.env.example` lista `DATABASE_URL`, `CORS_ORIGENS`, `FIT_DIR`, `LLM_PROVIDER` e `LLM_MODEL` (IA sempre por camada trocável).
- `FIT_DIR`: pasta dos FIT enviados por upload ([[decisoes/0006-upload-de-fit]]). Padrão `dados-upload/fit`, relativo à raiz do repositório; a pasta `dados-upload/` fica na lista de ignorados do controle de versão (dado pessoal, nunca no repositório).
- `CORS_ORIGENS`: origens do app web liberadas na API, separadas por vírgula. Padrão `http://localhost:8081`
  (`npx expo start --web`). Nunca `*` (a API recusa subir). Vazia não libera nenhuma. iOS e Android não precisam de CORS.
  Ver [[modulos/api]] e [[decisoes/0004-contrato-tela-evolucao]].

- Cuidado: o compose tem `name: treino-contexto`; sem `-p` ele reusa o volume `treino-contexto_pgdata`. Para porta ocupada, veja a seção abaixo.

## Porta do Postgres ocupada
O padrão do projeto é `localhost:5433` (host) para `5432` (container), justamente porque um Postgres nativo costuma ocupar a 5432.
Se o `DATABASE_URL` apontar para a 5432 de um Postgres nativo, o erro é `role "treino" does not exist`: você está no banco errado, não no do projeto.
- Ver quem ocupa a porta: `lsof -iTCP:5433 -sTCP:LISTEN` (troque pela porta em dúvida; `docker ps` mostra os containers).
- Porta 5433 também ocupada: suba com override fora do repo, pelo stdin (Compose 2.24 ou mais novo), e ajuste a URL:
  ```
  docker compose -f infra/docker-compose.yml -f - up -d <<'EOF'
  services:
    postgres:
      ports: !override
        - "5439:5432"
  EOF
  export DATABASE_URL="postgresql+psycopg://treino:treino@localhost:5439/treino"
  ```
- Quem já tem `.env` com 5432 precisa trocar para 5433 (ou para a porta do container em uso). O CI não muda: ele usa a 5432 do serviço dele.

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
