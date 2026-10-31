---
tipo: modulo
status: em-uso
dono: theo
atualizado: 2026-10-31
links: [[decisoes/0001-modelo-de-dados-minimo]], [[decisoes/0003-fuso-da-atividade]], [[metricas/tiros-1km]], [[modulos/grafico-tiros]], [[modulos/banco]], [[modulos/worker]], [[modulos/infra]]
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
- `services/api/app/metricas/`: funções puras das métricas (tiros de 1 km, [[metricas/tiros-1km]]).
- `services/api/app/graficos/`: desenho do gráfico e do CSV da série ([[modulos/grafico-tiros]]).
- `services/api/app/servicos/fuso.py`: `data_local(inicio, fuso_min)`, a data local da sessão ([[decisoes/0003-fuso-da-atividade]]).
- `services/api/app/servicos/evolucao_tiros.py`: liga as métricas ao banco (ver abaixo).
- `services/api/app/explicacao/`: pacote reservado.

## Série de tiros no banco (`servicos/evolucao_tiros.py`)
- `classificar_atividades(session, atleta_id)`: para cada corrida roda a detecção ([[metricas/tiros-1km]]) e marca
  os segmentos como `tiro`, `recuperacao` ou `volta`, gravando `versao_deteccao` (ex.: `tiros_1km@1`) em todos os
  segmentos da corrida. Idempotente. A importação ([[modulos/ingestao-garmin]]) chama no fim.
- **Tipo do treino:** se a corrida é intervalada, grava `tipo_treino = "intervalado"` e `tipo_origem = "sugestao"`.
  Nunca sobrescreve `tipo_origem` `professor` ou `trainingpeaks`, nem tipo com `tipo_confirmado`. Se uma sugestão
  `intervalado` anterior deixa de valer (a regra mudou ou as voltas mudaram), `tipo_treino` e `tipo_origem` voltam
  para `NULL`; tipo do professor, do TrainingPeaks ou confirmado nunca volta.
- `serie_tiros_1km(session, atleta_id, inicio=None, fim=None)`: um `PontoSessao` por sessão intervalada
  (3 ou mais tiros), por data crescente. Lê os segmentos já classificados (precisa de `classificar_atividades`
  antes). Uma sessão do professor marcada com outro tipo continua na série se tiver 3 ou mais tiros: a série
  segue a detecção, não o rótulo.
- **Data da sessão:** a data local do início (`inicio + fuso_min`, ou `America/Sao_Paulo` se `fuso_min` é `NULL`).
  `inicio` e `fim` do filtro também são datas locais, inclusivas.
- Testes: `services/api/tests/servicos/test_evolucao_tiros.py` (com as tabelas das fixtures e o oráculo da #30).

## Depende de
- [[modulos/banco]] (Postgres 16 via [[modulos/infra]]).

## Como testar
`uv run pytest -q` na raiz. Roda em SQLite local e em Postgres no CI.

## Pendências
- Endpoints da série de tiros (JSON e PNG) vêm na #16. Ver [[produto/roadmap]].
- Cada métrica nova ganha nota em [[metricas/]].
