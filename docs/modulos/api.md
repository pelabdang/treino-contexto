---
tipo: modulo
status: em-uso
dono: theo
atualizado: 2026-11-03
links: [[decisoes/0001-modelo-de-dados-minimo]], [[decisoes/0003-fuso-da-atividade]], [[decisoes/0004-contrato-tela-evolucao]], [[metricas/tiros-1km]], [[modulos/grafico-tiros]], [[modulos/banco]], [[modulos/worker]], [[modulos/infra]]
---
# Módulo: api

## Para que serve
API HTTP do produto (FastAPI). Hoje expõe `/health` e a evolução dos tiros de 1 km. É a dona do modelo de dados e das migrações.
Futuramente recebe a importação Garmin e serve métricas ao [[modulos/mobile]].

## Entradas e saídas
- Entrada: variável `DATABASE_URL` (ver `.env.example`).
- Saída: `GET /health` devolve `{"status": "ok"}`.
- Saída: `GET /atletas/{atleta_id}/evolucao/tiros-1km` (ver "Endpoint" abaixo).

## Arquivos principais
- `services/api/app/main.py`: app FastAPI.
- `services/api/app/rotas/evolucao.py`: roteador e modelos Pydantic da evolução dos tiros (aparecem em `/openapi.json`).
- `services/api/app/config.py`: configuração via pydantic-settings.
- `services/api/app/db/`: modelos, sessão e base. Veja [[modulos/banco]].
- `services/api/app/metricas/`: funções puras das métricas (tiros de 1 km, [[metricas/tiros-1km]]).
- `services/api/app/graficos/`: desenho do gráfico e do CSV da série ([[modulos/grafico-tiros]]).
- `services/api/app/servicos/fuso.py`: `data_local(inicio, fuso_min)`, a data local da sessão ([[decisoes/0003-fuso-da-atividade]]).
- `services/api/app/servicos/evolucao_tiros.py`: liga as métricas ao banco (ver abaixo).
- `services/api/app/explicacao/`: pacote reservado.

## Série de tiros no banco (`servicos/evolucao_tiros.py`)
- `classificar_atividades(session, atleta_id)`: para cada corrida roda a detecção ([[metricas/tiros-1km]]) e marca
  os segmentos como `tiro`, `recuperacao` ou `volta`, gravando `versao_deteccao` (ex.: `tiros_1km@4`) em todos os
  segmentos da corrida. Idempotente. A importação ([[modulos/ingestao-garmin]]) chama no fim.
- **Tipo do treino:** se a corrida é intervalada, grava `tipo_treino = "intervalado"` e `tipo_origem = "sugestao"`.
  Nunca sobrescreve `tipo_origem` `professor` ou `trainingpeaks`, nem tipo com `tipo_confirmado`. Se uma sugestão
  `intervalado` anterior deixa de valer (a regra mudou ou as voltas mudaram), `tipo_treino` e `tipo_origem` voltam
  para `NULL`; tipo do professor, do TrainingPeaks ou confirmado nunca volta.
- `sessoes_tiros_1km(session, atleta_id, inicio=None, fim=None)`: o que a rota usa. Por sessão, o `PontoSessao`, o `inicio` em UTC e os tiros (`ordem`, `distancia_m`, `duracao_s`, `fc_media`).
- `serie_tiros_1km(session, atleta_id, inicio=None, fim=None)` (só os pontos, sobre a mesma consulta): um `PontoSessao` por sessão intervalada
  (3 ou mais tiros), por data crescente. Lê os segmentos já classificados (precisa de `classificar_atividades`
  antes). Uma sessão do professor marcada com outro tipo continua na série se tiver 3 ou mais tiros: a série
  segue a detecção, não o rótulo.
  Desde a `tiros_1km@3`, a série só aceita a sessão cujo pace médio dos tiros é pelo menos 10% (desde a `@4`; era 5% na `@3`) mais rápido que o ritmo
  habitual do atleta (mediana das corridas de mais de 3 km, sem esteira, das 12 semanas anteriores; ver [[metricas/tiros-1km]]).
  O histórico usa todas as corridas do atleta, mesmo fora de `inicio`/`fim`. A `@4` mudou a detecção: é preciso rodar `classificar_atividades` para regravar `tipo` e `versao_deteccao` dos segmentos já gravados.
- **O que entra na série:** corridas com 3 ou mais tiros. Atividades de `subtipo = "esteira"` ficam **de fora** da série, do JSON, do PNG e do CSV (decisão do Angelo, issue #51), mas continuam no banco e são classificadas normalmente. A regra está em `SUBTIPOS_FORA_DA_SERIE`, usada por `sessoes_tiros_1km` e `serie_tiros_1km`.
- **Data da sessão:** a data local do início (`inicio + fuso_min`, ou `America/Sao_Paulo` se `fuso_min` é `NULL`).
  `inicio` e `fim` do filtro também são datas locais, inclusivas.
- Testes: `services/api/tests/servicos/test_evolucao_tiros.py` (com as tabelas das fixtures e o oráculo da #30) e `test_serie_pace_habitual.py` (filtro do ritmo habitual).

## Endpoint: `GET /atletas/{atleta_id}/evolucao/tiros-1km`
Query opcional `inicio` e `fim` (`AAAA-MM-DD`, datas **locais**, inclusivas; ver [[decisoes/0003-fuso-da-atividade]]).
Usa só `sessoes_tiros_1km` (serviço acima). Exemplo (ids e valores das fixtures):
```
curl "http://localhost:8000/atletas/1/evolucao/tiros-1km?inicio=2025-03-01"
```
```json
{"atleta_id": 1, "metrica": "tiros_1km", "versao_calculo": "tiros_1km@4",
 "unidades": {"pace": "s/km", "fc": "bpm", "distancia": "m", "duracao": "s"},
 "periodo": {"inicio": "2025-03-01", "fim": null},
 "sessoes": [{"atividade_id": 1, "data": "2025-03-04", "inicio": "2025-03-04T09:00:00Z", "n_tiros": 6,
              "pace_medio_s_km": 250.8, "pace_medio": "4:11", "fc_media": 170.3,
              "tiros": [{"ordem": 1, "distancia_m": 1000.0, "duracao_s": 255.0, "pace_s_km": 255.0, "fc_media": 165.0}]}]}
```
- `sessoes` por `data` crescente; `fc_media` pode ser `null`; valores com 1 casa; `pace_medio` vem de `formatar_pace` ([[metricas/tiros-1km]]).
- `periodo` é `null` sem filtro; com algum filtro, os dois campos, `null` no que não veio.
- Atleta inexistente: `404` `{"detail": "atleta não encontrado"}`. Sem sessões: `200` com `"sessoes": []`. Data inválida: `422`.
- **PNG:** `GET /atletas/{atleta_id}/evolucao/tiros-1km.png`, mesmos filtros; `200` com `Content-Type: image/png` (1600 x 1000),
  o mesmo desenho de `render_png` ([[modulos/grafico-tiros]]) que o comando `worker.grafico_tiros_1km` (`entregas/`, ver [[modulos/worker]]) usa. Sem sessões gera o PNG com o aviso;
  atleta inexistente `404`; data inválida `422`.
  ```
  curl -o tiros.png "http://localhost:8000/atletas/1/evolucao/tiros-1km.png"
  ```
- Testes: `services/api/tests/rotas/test_evolucao_tiros.py` (banco com as fixtures importadas).

## Contrato da tela de evolução (Meta 2)
O contrato que o app consome (pace só pela API, bloco `eixos`, `reclassificacao_pendente`, erros, arredondamento,
cliente gerado e CORS) está decidido em [[decisoes/0004-contrato-tela-evolucao]], com a lista "antes e depois".
O texto acima descreve o endpoint **de hoje**; cada mudança entra aqui quando a issue dela (#63 a #68) for feita.

## Depende de
- [[modulos/banco]] (Postgres 16 via [[modulos/infra]]).

## Como testar
`uv run pytest -q` na raiz. Roda em SQLite local e em Postgres no CI.

## Pendências
- Cliente TypeScript a partir do OpenAPI (Meta 2, #68; contrato em [[decisoes/0004-contrato-tela-evolucao]]). Ver [[produto/roadmap]].
- Passo a passo para reproduzir a Meta 1: [[produto/meta-1-como-reproduzir]].
- Cada métrica nova ganha nota em [[metricas/]].
