---
tipo: modulo
status: em-uso
dono: theo
atualizado: 2026-10-31
links: [[modulos/api]], [[modulos/infra]]
---
# Módulo: worker

## Para que serve
Serviço de processamento em segundo plano (FastAPI). Hoje só tem `/health`. Vai rodar tarefas pesadas
da importação e do cálculo de métricas, fora da [[modulos/api]].

## Entradas e saídas
- Saída: `GET /health` devolve `{"status": "ok"}`.

## Arquivos principais
- `services/worker/worker/main.py`
- `services/worker/tests/test_health.py`

## Depende de
- Mesmo workspace uv da [[modulos/api]]. Banco em [[modulos/banco]] quando houver tarefas.

## Como testar
`uv run pytest -q` na raiz.

## Pendências
- Definir fila e tarefas na Meta 1. Quando definir, abrir ADR em [[decisoes/]].
