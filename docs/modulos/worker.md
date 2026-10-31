---
tipo: modulo
status: em-uso
dono: theo
atualizado: 2026-10-31
links: [[modulos/api]], [[modulos/infra]], [[modulos/ingestao-garmin]]
---
# Módulo: worker

## Para que serve
Serviço de processamento em segundo plano (FastAPI). Hoje tem `/health` e o parser da exportação Garmin (`worker/garmin/`, sem banco). Vai rodar tarefas pesadas
da importação e do cálculo de métricas, fora da [[modulos/api]].

## Entradas e saídas
- Saída: `GET /health` devolve `{"status": "ok"}`.
- Parser: `worker.garmin.ler_exportacao(caminho)` lê zip, pasta, `summarizedActivities.json` ou `.fit` e devolve atividades com voltas. Detalhes em [[modulos/ingestao-garmin]].

## Arquivos principais
- `services/worker/worker/main.py`
- `services/worker/worker/garmin/` (parser: `leitor.py`, `fit.py`, `tipos.py`, `unidades.py`, `modelos.py`)
- `services/worker/tests/test_health.py`
- `services/worker/tests/test_garmin_parser.py`

## Depende de
- Mesmo workspace uv da [[modulos/api]]. Banco em [[modulos/banco]] quando houver tarefas.

## Como testar
`uv run pytest -q` na raiz.

## Pendências
- Definir fila e tarefas na Meta 1. Quando definir, abrir ADR em [[decisoes/]].
