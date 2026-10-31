---
tipo: modulo
status: em-uso
dono: theo
atualizado: 2026-10-31
links: [[decisoes/0001-modelo-de-dados-minimo]], [[modulos/banco]], [[modulos/worker]], [[modulos/infra]]
---
# Módulo: api

## Para que serve
API HTTP do produto (FastAPI). Hoje só expõe `/health`. É a dona do modelo de dados e das migrações.
Futuramente recebe a importação Garmin e serve métricas ao [[modulos/mobile]].

## Entradas e saídas
- Entrada: variável `DATABASE_URL` (ver `.env.example`).
- Saída: `GET /health` devolve `{"status": "ok"}`.

## Arquivos principais
- `services/api/app/main.py`: app FastAPI.
- `services/api/app/config.py`: configuração via pydantic-settings.
- `services/api/app/db/`: modelos, sessão e base. Veja [[modulos/banco]].
- `services/api/app/metricas/` e `services/api/app/explicacao/`: pacotes vazios, reservados.

## Depende de
- [[modulos/banco]] (Postgres 16 via [[modulos/infra]]).

## Como testar
`uv run pytest -q` na raiz. Roda em SQLite local e em Postgres no CI.

## Pendências
- Endpoints de importação (Meta 1). Ver [[produto/roadmap]].
- Cada métrica nova ganha nota em [[metricas/]].
