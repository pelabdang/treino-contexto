---
tipo: modulo
status: em-uso
dono: theo
atualizado: 2026-11-06
links: [[decisoes/0006-upload-de-fit]], [[modulos/api]], [[modulos/grafico-tiros]], [[modulos/infra]], [[modulos/ingestao-garmin]], [[modulos/banco]], [[modulos/clima]], [[decisoes/0008-deteccao-de-esforcos]], [[metricas/esforcos]], [[decisoes/0007-clima-da-atividade]], [[produto/meta-4-como-rodar]]
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
- Esforços: `uv run python -m worker.detectar_esforcos --atleta-id <id>` (#166, [[decisoes/0008-deteccao-de-esforcos]]) lê as voltas
  de cada corrida e pedalada do atleta, monta os blocos ([[metricas/esforcos]]) e grava em `bloco_atividade` ([[modulos/banco]]).
  **Sem rede.** Idempotente: calcula os blocos de cada atividade e só regrava os que mudaram (valores ou
  `versao_deteccao`); a 2ª rodada muda 0 e os `id` ficam. Mudar `VERSAO` em `app/metricas/esforcos.py` (ou qualquer
  constante da regra) faz a rodada seguinte redetectar tudo. A referência é o ritmo habitual (corrida) ou a velocidade
  habitual (ciclismo: mediana das pedaladas de mais de 30 min, fora do trainer, 12 semanas antes, ou todo o histórico
  com menos de 10); sem histórico vale a mediana da própria atividade. Imprime atividades processadas (regravadas,
  sem mudança, sem blocos), esforços e treinos-chave por modalidade, esforços por faixa e quantas atividades usaram a
  referência de reserva. Atleta inexistente: stderr e saída 1. A importação (`importar`) e o upload de FIT
  (`importar_fit`) chamam a mesma detecção só para as atividades que entraram ou mudaram; um erro nela vira aviso no
  log e nunca derruba a importação (rode o comando para refazer). Nada é exposto pela API ainda (#167).
- Clima: `uv run python -m worker.preencher_clima [--atleta-id N] [--exportacao CAMINHO] [--limite N] [--refazer-falhas] [--so-posicao]`.
  Primeiro relê a posição, da exportação (se dada) e, na falta dela, do FIT de `FIT_DIR`, para preencher `inicio_lat/lon` onde está `NULL`; depois busca
  o clima das atividades ao ar livre, com posição, sem `ok` válido e com fim a mais de 7 dias. Sequencial, pausa de 0,25 s,
  teto de 500 chamadas por rodada, um `commit` por atividade, para se o Open-Meteo limitar (429). Imprime posições
  preenchidas e atividades por estado. `--so-posicao` não usa a rede. Regras e estados em [[modulos/clima]]; passo a passo rodado em [[produto/meta-4-como-rodar]].
- Subtipo: `uv run python -m worker.reclassificar_subtipo --exportacao CAMINHO [--atleta-id N] [--dry-run]` relê o tipo da
  exportação (sem rede) e grava o `subtipo` pelo `tipos.py` atual só onde está `NULL` ou diverge, nas linhas `garmin_export`
  (casa por `fonte_id`). Para bancos importados antes de um mapeamento existir (ex.: `virtual_ride` -> `virtual`, #183).
  Só mexe em `subtipo`; se o novo for indoor, apaga `inicio_lat/lon` (ADR 0007). Subtipo `None` na exportação nunca apaga
  o gravado. Idempotente (2ª rodada muda 0); `--dry-run` imprime `antigo -> novo: N` sem gravar. Reimportar a exportação
  também atualiza o subtipo, mas relê as voltas e reclassifica as corridas; este comando é o caminho estreito.
  **Limitações:** (1) se a atividade que vira indoor já tinha linha em `clima_atividade`, a linha fica órfã (não é apagada);
  a API mostra `indoor` pelo subtipo antes de olhar a linha, então nada aparece errado, só sobra um registro velho.
  (2) O caminho inverso (indoor que vira ao ar livre) não recupera a posição; `worker.preencher_clima --so-posicao` resolve.
- Com `--com-clima`, no fim de `worker.importar_garmin` o clima é buscado **com a rede de verdade**, só das atividades que entraram ou mudaram (posições arredondadas vão ao Open-Meteo); erro de clima vira aviso
  e nunca derruba a importação. Sem a opção, rode `worker.preencher_clima` quando quiser. O upload de FIT (endpoint) não chama a rede: o clima fica `pendente` até a próxima rodada.

## Arquivos principais
- `services/worker/worker/main.py`
- O parser (`leitor.py`, `fit.py`, `tipos.py`, `unidades.py`, `modelos.py`) está em `services/api/app/ingestao/garmin/`; o worker importa de lá
- `services/worker/worker/importar_garmin.py` (importação no banco, CLI `python -m worker.importar_garmin`)
- `services/worker/worker/grafico_tiros_1km.py` (gráfico e CSV, CLI `python -m worker.grafico_tiros_1km`)
- `services/worker/worker/apagar_fit.py` (CLI `python -m worker.apagar_fit`)
- `services/worker/worker/reclassificar.py` (CLI `python -m worker.reclassificar`)
- `services/worker/worker/reclassificar_subtipo.py` (CLI `python -m worker.reclassificar_subtipo`)
- `services/worker/worker/detectar_esforcos.py` (CLI `python -m worker.detectar_esforcos`); a lógica está em `services/api/app/servicos/esforcos.py`
- `services/worker/tests/test_detectar_esforcos.py`
- `services/worker/worker/preencher_clima.py` (CLI `python -m worker.preencher_clima`); a lógica está em `services/api/app/servicos/clima.py`
- `services/worker/tests/test_preencher_clima.py`
- `services/worker/tests/test_reclassificar.py`
- `services/worker/tests/test_reclassificar_subtipo.py`
- `services/worker/tests/test_grafico_tiros_1km.py`
- `services/worker/tests/test_health.py`
- `services/api/tests/ingestao/test_garmin_parser.py` (testes do parser, na API)

## Depende de
- Mesmo workspace uv da [[modulos/api]]; a importação usa o parser de `app.ingestao.garmin` e chama `classificar_atividades` de `app.servicos` (ver "Série de tiros no banco" em [[modulos/api]]). Banco em [[modulos/banco]] quando houver tarefas.

## Como testar
`uv run pytest -q` na raiz.

## Pendências
- Definir fila e tarefas na Meta 1. Quando definir, abrir ADR em [[decisoes/]].
