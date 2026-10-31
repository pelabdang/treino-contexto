---
tipo: modulo
status: em-uso
dono: theo
atualizado: 2026-10-31
links: [[modulos/api]], [[modulos/grafico-tiros]], [[modulos/infra]], [[modulos/ingestao-garmin]], [[modulos/banco]]
---
# Módulo: worker

## Para que serve
Serviço de processamento em segundo plano (FastAPI). Hoje tem `/health` e o parser da exportação Garmin (`worker/garmin/`, sem banco) e a importação dele no banco (`worker/importar_garmin.py`). Vai rodar tarefas pesadas
da importação e do cálculo de métricas, fora da [[modulos/api]].

## Entradas e saídas
- Saída: `GET /health` devolve `{"status": "ok"}`.
- Parser: `worker.garmin.ler_exportacao(caminho)` lê zip, pasta, `summarizedActivities.json` ou `.fit` e devolve atividades com voltas. Detalhes em [[modulos/ingestao-garmin]].
- Importação: `uv run python -m worker.importar_garmin <caminho> --atleta "<nome>"` grava atividades e voltas no banco ([[modulos/banco]]), de forma idempotente.
- Gráfico: `uv run python -m worker.grafico_tiros_1km --atleta-id <id> [--inicio AAAA-MM-DD] [--fim AAAA-MM-DD] [--saida <pasta>]`
  lê a série do banco e grava `entregas/meta-1/tiros-1km-atleta-<id>.png` e `.csv` (pasta criada se faltar; fora do
  git). Atleta inexistente: mensagem em stderr e código de saída 1. Formato em [[modulos/grafico-tiros]].
  Exemplo com as fixtures: ![[_anexos/tiros-1km-atleta-fixtures.png]]

## Arquivos principais
- `services/worker/worker/main.py`
- `services/worker/worker/garmin/` (parser: `leitor.py`, `fit.py`, `tipos.py`, `unidades.py`, `modelos.py`)
- `services/worker/worker/importar_garmin.py` (importação no banco, CLI `python -m worker.importar_garmin`)
- `services/worker/worker/grafico_tiros_1km.py` (gráfico e CSV, CLI `python -m worker.grafico_tiros_1km`)
- `services/worker/tests/test_grafico_tiros_1km.py`
- `services/worker/tests/test_health.py`
- `services/worker/tests/test_garmin_parser.py`

## Depende de
- Mesmo workspace uv da [[modulos/api]]; a importação chama `classificar_atividades` de `app.servicos` (ver "Série de tiros no banco" em [[modulos/api]]). Banco em [[modulos/banco]] quando houver tarefas.

## Como testar
`uv run pytest -q` na raiz.

## Pendências
- Definir fila e tarefas na Meta 1. Quando definir, abrir ADR em [[decisoes/]].
