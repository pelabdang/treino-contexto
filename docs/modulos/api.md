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
- Entrada: variável `CORS_ORIGENS` (ver "CORS" abaixo).
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

## CORS
O app web roda em outra porta (`http://localhost:8081`), então a API libera as origens de `CORS_ORIGENS` (lista
separada por vírgula, lida em `app/config.py`; middleware em `criar_app` de `app/main.py`).
- Padrão local: `http://localhost:8081`. Só `GET` (e o preflight dele); sem cookies nem cabeçalhos extras.
- Nunca `*`: com `*` na lista a API não sobe (`ValueError`). Variável vazia não libera nenhuma origem.
- Origem fora da lista recebe a resposta normal, sem `Access-Control-Allow-Origin` (o navegador bloqueia).
- Exemplo para mais de uma origem: `CORS_ORIGENS=http://localhost:8081,https://app.exemplo.com`.
- Testes: `services/api/tests/test_cors.py`. Variável em [[modulos/infra]].

## Série de tiros no banco (`servicos/evolucao_tiros.py`)
- `classificar_atividades(session, atleta_id)`: para cada corrida roda a detecção ([[metricas/tiros-1km]]) e marca
  os segmentos como `tiro`, `recuperacao` ou `volta`, gravando `versao_deteccao` (ex.: `tiros_1km@4`) em todos os
  segmentos da corrida. Idempotente. A importação ([[modulos/ingestao-garmin]]) chama no fim.
- **Tipo do treino:** se a corrida é intervalada, grava `tipo_treino = "intervalado"` e `tipo_origem = "sugestao"`.
  Nunca sobrescreve `tipo_origem` `professor` ou `trainingpeaks`, nem tipo com `tipo_confirmado`. Se uma sugestão
  `intervalado` anterior deixa de valer (a regra mudou ou as voltas mudaram), `tipo_treino` e `tipo_origem` voltam
  para `NULL`; tipo do professor, do TrainingPeaks ou confirmado nunca volta.
- `sessoes_tiros_1km(session, atleta_id, inicio=None, fim=None)`: o que a rota usa. Por sessão, o `PontoSessao`, o `inicio` em UTC e os tiros (`ordem`, `distancia_m`, `duracao_s`, `fc_media`). `distancia_m` do tiro é `None` quando o segmento não tem distância (nunca `0`).
- `reclassificacao_pendente(session, atleta_id, inicio=None, fim=None)`: `True` se algum segmento das corridas da série (fora a esteira, dentro do período) tem `versao_deteccao` diferente de `VERSAO`, inclusive `NULL` (nunca classificado). Só lê.
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
{"atleta_id": 1, "metrica": "tiros_1km", "versao_calculo": "tiros_1km@4", "reclassificacao_pendente": false,
 "unidades": {"pace": "s/km", "fc": "bpm", "distancia": "m", "duracao": "s"},
 "periodo": {"inicio": "2025-03-01", "fim": null},
 "eixos": {"pace": {"min_s_km": 228.9, "max_s_km": 258.9, "invertido": true,
                    "marcas": [{"valor_s_km": 240.0, "rotulo": "4:00"}, {"valor_s_km": 255.0, "rotulo": "4:15"}]},
           "fc": {"min_bpm": 168.5, "max_bpm": 173.5,
                  "marcas": [{"valor_bpm": 169.0, "rotulo": "169"}, {"valor_bpm": 170.0, "rotulo": "170"}, {"valor_bpm": 171.0, "rotulo": "171"}, {"valor_bpm": 172.0, "rotulo": "172"}, {"valor_bpm": 173.0, "rotulo": "173"}]}},
 "sessoes": [{"atividade_id": 1, "data": "2025-03-04", "inicio": "2025-03-04T09:00:00Z", "n_tiros": 6,
              "pace_medio_s_km": 250.8, "pace_medio": "4:11", "fc_media": 170.3,
              "tiros": [{"ordem": 1, "distancia_m": 1000.0, "duracao_s": 255.0, "pace_s_km": 255.0, "pace": "4:15", "fc_media": 165.0}]}]}
```
- `versao_calculo` é sempre a `VERSAO` da regra atual (não vem do banco). `reclassificacao_pendente` é `true` quando algum segmento foi gravado com outra versão; o `GET` nunca reclassifica nem escreve. Para voltar a `false`, veja "Reclassificar".
- `metrica` é sempre `"tiros_1km"` (`Literal` no OpenAPI). Todos os campos de `unidades` são obrigatórios no schema.
- Todo decimal sai com 1 casa, inclusive os do tiro. `distancia_m` do tiro é `null` (e `pace_s_km` e `pace` também) quando o segmento não tem distância, nunca `0`.
- O texto de pace (`pace_medio` da sessão, `pace` do tiro) é feito por `formatar_pace` a partir do valor **sem arredondar**; formatar o número de 1 casa pode dar outro resultado (239,46 s/km: texto `3:59`, número `239.5`). O app não formata pace.
- `eixos` (#66): faixa e marcas prontas para o app desenhar, calculadas por `escala_pace` e `escala_fc` (`app/graficos/escala.py`, #63), a **mesma regra e a mesma faixa** do PNG para o mesmo filtro, sobre os valores sem arredondar da série (1 casa só na saída). Escala mínima de 30 s/km no pace e 5 bpm na FC. `rotulo` do pace é `formatar_pace(valor_s_km)`; o da FC é o inteiro em texto. `invertido: true` no pace (mais rápido no alto). `eixos` é `null` sem sessões; `eixos.fc` é `null` se nenhuma sessão tem FC. O app não escolhe escala nem formata pace. O exemplo acima usa as fixtures (as duas sessões).
- `sessoes` por `data` crescente; `fc_media` pode ser `null`; valores com 1 casa; `pace_medio` vem de `formatar_pace` ([[metricas/tiros-1km]]).
- `periodo` é `null` sem filtro; com algum filtro, os dois campos, `null` no que não veio.
- Atleta inexistente: `404` `{"detail": "atleta não encontrado"}`, declarado no OpenAPI com o modelo `Erro` nos dois endpoints. Sem sessões: `200` com `"sessoes": []`. Data inválida ou `inicio` depois de `fim`: `422` (formato do FastAPI, `detail` é lista).
- `operationId`: `evolucaoTiros1km` (JSON) e `evolucaoTiros1kmPng` (PNG).
- **PNG:** `GET /atletas/{atleta_id}/evolucao/tiros-1km.png`, mesmos filtros; `200` com `Content-Type: image/png` (1600 x 1000),
  o mesmo desenho de `render_png` ([[modulos/grafico-tiros]]) que o comando `worker.grafico_tiros_1km` (`entregas/`, ver [[modulos/worker]]) usa. Sem sessões gera o PNG com o aviso;
  atleta inexistente `404`; data inválida ou `inicio` > `fim` `422`.
  ```
  curl -o tiros.png "http://localhost:8000/atletas/1/evolucao/tiros-1km.png"
  ```
- Testes: `services/api/tests/rotas/test_evolucao_tiros.py` (banco com as fixtures importadas).

## Reclassificar
Quando uma regra nova de detecção sobe a `VERSAO` ([[metricas/tiros-1km]]), os segmentos já gravados ficam com a
versão velha e o JSON traz `reclassificacao_pendente: true` ([[decisoes/0004-contrato-tela-evolucao]]). A API não
reclassifica na leitura. Passo a passo, com o banco do `DATABASE_URL` no ar:
```
uv run python -m worker.reclassificar --atleta-id 1
```
O comando chama `classificar_atividades` e imprime `reclassificadas N corridas do atleta 1` (atleta inexistente: erro
em stderr e saída 1). É idempotente: rodar de novo dá o mesmo resultado. Depois, `reclassificacao_pendente` volta a
`false`. Reimportar a exportação Garmin ([[modulos/ingestao-garmin]]) tem o mesmo efeito. Ver [[modulos/worker]].

## Contrato da tela de evolução (Meta 2)
O contrato que o app consome está em [[decisoes/0004-contrato-tela-evolucao]], com a lista "antes e depois".
Já valem aqui (#64): D2 a D11 (erro `404` declarado, `versao_calculo` fixa mais `reclassificacao_pendente`, `Unidades`
obrigatória, 1 casa decimal, `pace` do tiro, distância `null`, `inicio` > `fim` com `422`, `operationId`, `metrica`
literal). Faltam o bloco `eixos` (#63 e #66) e o cliente gerado (#68).

## Depende de
- [[modulos/banco]] (Postgres 16 via [[modulos/infra]]).

## Como testar
`uv run pytest -q` na raiz. Roda em SQLite local e em Postgres no CI.

## Pendências
- Cliente TypeScript a partir do OpenAPI (Meta 2, #68; contrato em [[decisoes/0004-contrato-tela-evolucao]]). Ver [[produto/roadmap]].
- Passo a passo para reproduzir a Meta 1: [[produto/meta-1-como-reproduzir]].
- Cada métrica nova ganha nota em [[metricas/]].
