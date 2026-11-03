---
tipo: modulo
status: em-uso
dono: theo
atualizado: 2026-11-03
links: [[decisoes/0006-upload-de-fit]], [[modulos/api]], [[modulos/grafico-tiros]], [[modulos/infra]], [[modulos/ingestao-garmin]], [[modulos/banco]]
---
# Módulo: worker

## Para que serve
Serviço de processamento em segundo plano (FastAPI). Hoje tem `/health` e a importação da exportação Garmin no banco (o parser mora na API, em `app/ingestao/garmin/`, desde a #92) (`worker/importar_garmin.py`). Vai rodar tarefas pesadas
da importação e do cálculo de métricas, fora da [[modulos/api]].

## Entradas e saídas
- Saída: `GET /health` devolve `{"status": "ok"}`.
- Parser (na API desde a #92, [[decisoes/0006-upload-de-fit]]): `app.ingestao.garmin.ler_exportacao(caminho)` lê zip, pasta, `summarizedActivities.json` ou `.fit` e devolve atividades com voltas. Detalhes em [[modulos/ingestao-garmin]].
- Importação: `uv run python -m worker.importar_garmin <caminho> --atleta "<nome>"` grava atividades e voltas no banco ([[modulos/banco]]), de forma idempotente.
- Gráfico: `uv run python -m worker.grafico_tiros_1km --atleta-id <id> [--inicio AAAA-MM-DD] [--fim AAAA-MM-DD] [--saida <pasta>]`
  lê a série do banco e grava `entregas/meta-1/tiros-1km-atleta-<id>.png` e `.csv` (pasta criada se faltar; fora do
  git). Atleta inexistente: mensagem em stderr e código de saída 1. Formato em [[modulos/grafico-tiros]].
  Exemplo com as fixtures: ![[_anexos/tiros-1km-atleta-fixtures.png]]

- Reclassificação: `uv run python -m worker.reclassificar --atleta-id <id>` roda `classificar_atividades` e mostra
  quantas corridas processou. Idempotente. Use quando a API devolve `reclassificacao_pendente: true`
  (passo a passo em "Reclassificar" de [[modulos/api]]). Atleta inexistente: stderr e saída 1.

## Arquivos principais
- `services/worker/worker/main.py`
- O parser (`leitor.py`, `fit.py`, `tipos.py`, `unidades.py`, `modelos.py`) está em `services/api/app/ingestao/garmin/`; o worker importa de lá
- `services/worker/worker/importar_garmin.py` (importação no banco, CLI `python -m worker.importar_garmin`)
- `services/worker/worker/grafico_tiros_1km.py` (gráfico e CSV, CLI `python -m worker.grafico_tiros_1km`)
- `services/worker/worker/reclassificar.py` (CLI `python -m worker.reclassificar`)
- `services/worker/tests/test_reclassificar.py`
- `services/worker/tests/test_grafico_tiros_1km.py`
- `services/worker/tests/test_health.py`
- `services/api/tests/ingestao/test_garmin_parser.py` (testes do parser, na API)

## Depende de
- Mesmo workspace uv da [[modulos/api]]; a importação usa o parser de `app.ingestao.garmin` e chama `classificar_atividades` de `app.servicos` (ver "Série de tiros no banco" em [[modulos/api]]). Banco em [[modulos/banco]] quando houver tarefas.

## Como testar
`uv run pytest -q` na raiz.

## Pendências
- Definir fila e tarefas na Meta 1. Quando definir, abrir ADR em [[decisoes/]].
