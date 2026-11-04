---
tipo: modulo
status: em-uso
dono: theo
atualizado: 2026-11-04
links: [[decisoes/0006-upload-de-fit]], [[modulos/api]], [[modulos/grafico-tiros]], [[modulos/infra]], [[modulos/ingestao-garmin]], [[modulos/banco]], [[modulos/clima]], [[decisoes/0007-clima-da-atividade]], [[produto/meta-4-como-rodar]]
---
# Módulo: worker

## Para que serve
Serviço de processamento em segundo plano (FastAPI). Hoje tem `/health` e a importação da exportação Garmin no banco (`worker/importar_garmin.py`, linha de comando; o parser e a gravação moram na API, em `app/ingestao/`, desde a #92 e a #94). Vai rodar tarefas pesadas
da importação e do cálculo de métricas, fora da [[modulos/api]].

## Entradas e saídas
- Saída: `GET /health` devolve `{"status": "ok"}`.
- Parser (na API desde a #92, [[decisoes/0006-upload-de-fit]]): `app.ingestao.garmin.ler_exportacao(caminho)` lê zip, pasta, `summarizedActivities.json` ou `.fit` e devolve atividades com voltas. Detalhes em [[modulos/ingestao-garmin]].
- Importação: `uv run python -m worker.importar_garmin <caminho> --atleta "<nome>" [--com-clima]` grava atividades e voltas no banco ([[modulos/banco]]), de forma idempotente. **Sem rede por padrão** (#132): sem `--com-clima` nenhuma conexão é aberta e o fim da importação imprime `clima: nao buscado` com o comando a rodar.
- Gráfico: `uv run python -m worker.grafico_tiros_1km --atleta-id <id> [--inicio AAAA-MM-DD] [--fim AAAA-MM-DD] [--saida <pasta>]`
  lê a série do banco e grava `entregas/meta-1/tiros-1km-atleta-<id>.png` e `.csv` (pasta criada se faltar; fora do
  git). Atleta inexistente: mensagem em stderr e código de saída 1. Formato em [[modulos/grafico-tiros]].
  Exemplo com as fixtures: ![[_anexos/tiros-1km-atleta-fixtures.png]]

- Apagar FIT enviados: `uv run python -m worker.apagar_fit --atleta-id <id>` apaga os arquivos de `FIT_DIR/<id>/` e limpa `arquivo_bruto`, sem apagar as atividades ([[decisoes/0006-upload-de-fit]]; uso na prática em [[produto/meta-3-como-rodar]]).
- Reclassificação: `uv run python -m worker.reclassificar --atleta-id <id>` roda `classificar_atividades` e mostra
  quantas corridas processou. Idempotente. Use quando a API devolve `reclassificacao_pendente: true`
  (passo a passo em "Reclassificar" de [[modulos/api]]). Atleta inexistente: stderr e saída 1.
- Clima: `uv run python -m worker.preencher_clima [--atleta-id N] [--exportacao CAMINHO] [--limite N] [--refazer-falhas] [--so-posicao]`.
  Primeiro relê a posição, da exportação (se dada) e, na falta dela, do FIT de `FIT_DIR`, para preencher `inicio_lat/lon` onde está `NULL`; depois busca
  o clima das atividades ao ar livre, com posição, sem `ok` válido e com fim a mais de 7 dias. Sequencial, pausa de 0,25 s,
  teto de 500 chamadas por rodada, um `commit` por atividade, para se o Open-Meteo limitar (429). Imprime posições
  preenchidas e atividades por estado. `--so-posicao` não usa a rede. Regras e estados em [[modulos/clima]]; passo a passo rodado em [[produto/meta-4-como-rodar]].
- Com `--com-clima`, no fim de `worker.importar_garmin` o clima é buscado **com a rede de verdade**, só das atividades que entraram ou mudaram (posições arredondadas vão ao Open-Meteo); erro de clima vira aviso
  e nunca derruba a importação. Sem a opção, rode `worker.preencher_clima` quando quiser. O upload de FIT (endpoint) não chama a rede: o clima fica `pendente` até a próxima rodada.

## Arquivos principais
- `services/worker/worker/main.py`
- O parser (`leitor.py`, `fit.py`, `tipos.py`, `unidades.py`, `modelos.py`) está em `services/api/app/ingestao/garmin/`; o worker importa de lá
- `services/worker/worker/importar_garmin.py` (importação no banco, CLI `python -m worker.importar_garmin`)
- `services/worker/worker/grafico_tiros_1km.py` (gráfico e CSV, CLI `python -m worker.grafico_tiros_1km`)
- `services/worker/worker/apagar_fit.py` (CLI `python -m worker.apagar_fit`)
- `services/worker/worker/reclassificar.py` (CLI `python -m worker.reclassificar`)
- `services/worker/worker/preencher_clima.py` (CLI `python -m worker.preencher_clima`); a lógica está em `services/api/app/servicos/clima.py`
- `services/worker/tests/test_preencher_clima.py`
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
