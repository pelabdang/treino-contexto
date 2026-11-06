---
tipo: modulo
status: em-uso
dono: theo
atualizado: 2026-11-06
links: [[decisoes/0001-modelo-de-dados-minimo]], [[decisoes/0003-fuso-da-atividade]], [[decisoes/0004-contrato-tela-evolucao]], [[metricas/tiros-1km]], [[modulos/grafico-tiros]], [[modulos/banco]], [[modulos/worker]], [[modulos/infra]], [[modulos/api-client]], [[decisoes/0006-upload-de-fit]], [[produto/meta-2-como-rodar]], [[decisoes/0007-clima-da-atividade]], [[modulos/clima]], [[produto/meta-4-como-rodar]], [[decisoes/0008-deteccao-de-esforcos]], [[metricas/esforcos]]
---
# Módulo: api

## Para que serve
API HTTP do produto (FastAPI). Hoje expõe `/health`, a evolução dos tiros de 1 km, o upload de FIT e a atividade com o clima. É a dona do modelo de dados e das migrações.
Futuramente recebe a importação Garmin e serve métricas ao [[modulos/mobile]].

## Entradas e saídas
- Entrada: variável `DATABASE_URL` (ver `.env.example`).
- Entrada: variável `CORS_ORIGENS` (ver "CORS" abaixo) e `FIT_DIR` (pasta dos FIT do upload, ver [[modulos/ingestao-garmin]]).
- Saída: `GET /health` devolve `{"status": "ok"}`.
- Saída: `GET /atletas/{atleta_id}/evolucao/tiros-1km` (ver "Endpoint" abaixo).
- Entrada e saída: `POST /atletas/{atleta_id}/atividades/fit` (ver "Upload de FIT" abaixo).
- Saída: `GET /atletas/{atleta_id}/atividades/{atividade_id}` (ver "Atividade e clima" abaixo).

## Arquivos principais
- `services/api/app/main.py`: app FastAPI.
- `services/api/app/rotas/evolucao.py`: roteador e modelos Pydantic da evolução dos tiros (aparecem em `/openapi.json`).
- `services/api/app/rotas/atividades.py`: roteador do upload de FIT (`UploadFitOut`) e da atividade com clima (`AtividadeOut`, `ClimaOut`).
- `services/api/app/config.py`: configuração via pydantic-settings.
- `services/api/app/db/`: modelos, sessão e base. Veja [[modulos/banco]].
- `services/api/app/metricas/`: funções puras das métricas (tiros de 1 km, [[metricas/tiros-1km]]).
- `services/api/app/graficos/`: desenho do gráfico e do CSV da série ([[modulos/grafico-tiros]]).
- `services/api/app/servicos/fuso.py`: `data_local(inicio, fuso_min)`, a data local da sessão ([[decisoes/0003-fuso-da-atividade]]).
- `services/api/app/ingestao/garmin/`: parser da exportação Garmin e do FIT (`ler_exportacao`, `ler_atividade_fit`), sem banco; o worker importa daqui ([[modulos/ingestao-garmin]], [[decisoes/0006-upload-de-fit]]).
- `services/api/app/ingestao/importacao.py` e `fit_guardado.py`: gravação da exportação e do upload (`importar`, `importar_fit`) e guarda dos FIT em `FIT_DIR`. O endpoint de upload está em `app/rotas/atividades.py` (#95).
- `services/api/app/servicos/esforcos_leitura.py`: lê os blocos gravados para a resposta da atividade (#167).
- `services/api/app/servicos/evolucao_tiros.py`: liga as métricas ao banco (ver abaixo).
- `services/api/app/explicacao/`: pacote reservado.

## CORS
O app web roda em outra porta (`http://localhost:8081`), então a API libera as origens de `CORS_ORIGENS` (lista
separada por vírgula, lida em `app/config.py`; middleware em `criar_app` de `app/main.py`).
- Padrão local: `http://localhost:8081`. `GET` e `POST` (o `POST` é o upload de FIT, #95; amplia o item 7 da [[decisoes/0004-contrato-tela-evolucao]]) e o preflight deles; sem cookies nem cabeçalhos extras.
- Nunca `*`: com `*` na lista a API não sobe (`ValueError`). Variável vazia não libera nenhuma origem.
- Origem fora da lista recebe a resposta normal, sem `Access-Control-Allow-Origin` (o navegador bloqueia).
- Exemplo para mais de uma origem: `CORS_ORIGENS=http://localhost:8081,https://app.exemplo.com`.
- Testes: `services/api/tests/test_cors.py`. Variável em [[modulos/infra]].

## Série de tiros no banco (`servicos/evolucao_tiros.py`)
- `classificar_atividades(session, atleta_id)`: primeiro roda `detectar_esforcos` (blocos em `bloco_atividade`, [[metricas/esforcos]]); depois, para cada corrida, aplica a visão de tiros de 1 km ([[metricas/tiros-1km]], `tiros_1km@5`) e marca
  os segmentos como `tiro`, `recuperacao` ou `volta`, gravando `versao_deteccao` (ex.: `tiros_1km@5`) em todos os
  segmentos da corrida. Idempotente. A importação ([[modulos/ingestao-garmin]]) chama no fim.
- **Tipo do treino:** se a corrida é intervalada, grava `tipo_treino = "intervalado"` e `tipo_origem = "sugestao"`.
  Nunca sobrescreve `tipo_origem` `professor` ou `trainingpeaks`, nem tipo com `tipo_confirmado`. Se uma sugestão
  `intervalado` anterior deixa de valer (a regra mudou ou as voltas mudaram), `tipo_treino` e `tipo_origem` voltam
  para `NULL`; tipo do professor, do TrainingPeaks ou confirmado nunca volta.
- `sessoes_tiros_1km(session, atleta_id, inicio=None, fim=None)`: o que a rota usa. Por sessão, o `PontoSessao`, o `inicio` em UTC e os tiros (`ordem`, `distancia_m`, `duracao_s`, `fc_media`). Desde a `@5` lê `bloco_atividade`: o tiro é um bloco `esforco` `d1000` e `ordem` é a `segmento.ordem` da primeira volta dele. `distancia_m` `None` segue possível no contrato, mas um bloco sem distância não é tiro.
- `reclassificacao_pendente(session, atleta_id, inicio=None, fim=None)`: `True` se algum segmento das corridas da série (fora a esteira, dentro do período) tem `versao_deteccao` diferente de `VERSAO`, inclusive `NULL` (nunca classificado), ou se algum bloco foi gravado por outra versão dos esforços. Só lê.
- `serie_tiros_1km(session, atleta_id, inicio=None, fim=None)` (só os pontos, sobre a mesma consulta): um `PontoSessao` por sessão intervalada
  (2 ou mais tiros), por data crescente. Lê os blocos já gravados (precisa de `classificar_atividades` ou
  `detectar_esforcos` antes). Uma sessão do professor marcada com outro tipo continua na série se tiver 2 ou mais tiros: a série
  segue a detecção, não o rótulo.
  Desde a `tiros_1km@3`, a série só aceita a sessão cujo pace médio dos tiros é pelo menos 10% (desde a `@4`; era 5% na `@3`) mais rápido que o ritmo
  habitual do atleta (mediana das corridas de mais de 3 km, sem esteira, das 12 semanas anteriores; ver [[metricas/tiros-1km]]).
  O histórico usa todas as corridas do atleta, mesmo fora de `inicio`/`fim`. A `@5` mudou a fonte e a regra: é preciso rodar `classificar_atividades` (ou `worker.reclassificar`) para recriar os blocos e regravar `tipo` e `versao_deteccao` dos segmentos já gravados.
- **O que entra na série:** corridas com 2 ou mais tiros de 1 km. Atividades de `subtipo = "esteira"` ficam **de fora** da série, do JSON, do PNG e do CSV (decisão do Angelo, issue #51), mas continuam no banco e são classificadas normalmente. A regra está em `SUBTIPOS_FORA_DA_SERIE`, usada por `sessoes_tiros_1km` e `serie_tiros_1km`.
- **Data da sessão:** a data local do início (`inicio + fuso_min`, ou `America/Sao_Paulo` se `fuso_min` é `NULL`).
  `inicio` e `fim` do filtro também são datas locais, inclusivas.
- Testes: `services/api/tests/servicos/test_evolucao_tiros.py` (com as tabelas das fixtures e o oráculo da #30) e `test_serie_pace_habitual.py` (filtro do ritmo habitual).

## Blocos e esforços no banco (`servicos/esforcos.py`)
- `detectar_esforcos(session, atleta_id, atividade_ids=None)` (#166, [[decisoes/0008-deteccao-de-esforcos]]): para cada corrida e
  pedalada monta os blocos com `app.metricas.esforcos` ([[metricas/esforcos]]) e grava em `bloco_atividade` ([[modulos/banco]]),
  com a faixa de cada esforço e o `treino_chave` (os esforços da sequência contínua). Idempotente: só regrava a atividade
  cujos blocos mudaram (ou cuja `versao_deteccao` é outra). Devolve um `RelatorioEsforcos`. Sem rede. A API só lê o que isto grava (#167, abaixo).
- `velocidade_habitual(historico, data)`: a referência do ciclismo (mediana da velocidade das pedaladas de mais de 30 min,
  fora do trainer e do `virtual`, nas 12 semanas antes; todo o histórico anterior com menos de 10). A da corrida é a `pace_habitual`.
- A importação e o upload de FIT chamam `detectar_esforcos` para as atividades que entraram ou mudaram. Comando: `worker.detectar_esforcos` ([[modulos/worker]]).
- Testes: `services/api/tests/servicos/test_esforcos_banco.py` (oráculo da #161 no banco, idempotência, versão nova, voltas que mudam, relatório).

## Endpoint: `GET /atletas/{atleta_id}/evolucao/tiros-1km`
Query opcional `inicio` e `fim` (`AAAA-MM-DD`, datas **locais**, inclusivas; ver [[decisoes/0003-fuso-da-atividade]]).
Usa só `sessoes_tiros_1km` (serviço acima). Exemplo (ids e valores das fixtures):
```
curl "http://localhost:8000/atletas/1/evolucao/tiros-1km?inicio=2025-03-01"
```
```json
{"atleta_id": 1, "metrica": "tiros_1km", "versao_calculo": "tiros_1km@5", "reclassificacao_pendente": false,
 "unidades": {"pace": "s/km", "fc": "bpm", "distancia": "m", "duracao": "s"},
 "periodo": {"inicio": "2025-03-01", "fim": null},
 "eixos": {"pace": {"min_s_km": 226.0, "max_s_km": 256.0, "invertido": true,
                    "marcas": [{"valor_s_km": 230.0, "rotulo": "3:50"}, {"valor_s_km": 240.0, "rotulo": "4:00"}, {"valor_s_km": 250.0, "rotulo": "4:10"}]},
           "fc": {"min_bpm": 173.5, "max_bpm": 178.5,
                  "marcas": [{"valor_bpm": 174.0, "rotulo": "174"}, {"valor_bpm": 175.0, "rotulo": "175"}, {"valor_bpm": 176.0, "rotulo": "176"}, {"valor_bpm": 177.0, "rotulo": "177"}, {"valor_bpm": 178.0, "rotulo": "178"}]}},
 "sessoes": [{"atividade_id": 1, "data": "2025-03-04", "inicio": "2025-03-04T09:00:00Z", "n_tiros": 6,
              "pace_medio_s_km": 250.8, "pace_medio": "4:11", "fc_media": 170.3,
              "pace_melhor_s_km": 248.0, "pace_melhor": "4:08", "fc_melhor_tiro": 175.0, "ordem_melhor_tiro": 11,
              "tiros": [{"ordem": 1, "distancia_m": 1000.0, "duracao_s": 255.0, "pace_s_km": 255.0, "pace": "4:15", "fc_media": 165.0}]}]}
```
- `versao_calculo` é sempre a `VERSAO` da regra atual (não vem do banco). `reclassificacao_pendente` é `true` quando algum segmento foi gravado com outra versão; o `GET` nunca reclassifica nem escreve. Para voltar a `false`, veja "Reclassificar".
- `metrica` é sempre `"tiros_1km"` (`Literal` no OpenAPI). Todos os campos de `unidades` são obrigatórios no schema.
- Todo decimal sai com 1 casa, inclusive os do tiro. `distancia_m` do tiro é `null` (e `pace_s_km` e `pace` também) quando o segmento não tem distância, nunca `0`.
- **Melhor tiro (#152, [[decisoes/0004-contrato-tela-evolucao]], adendo 1):** `pace_melhor_s_km`, `pace_melhor` (`m:ss` de `formatar_pace`), `fc_melhor_tiro` (`null` se o melhor tiro não tem FC; não troca de tiro) e `ordem_melhor_tiro`. É o valor principal do gráfico e do painel de FC; `pace_medio*` e `fc_media` ficam como secundários.
- O texto de pace (`pace_medio` da sessão, `pace` do tiro) é feito por `formatar_pace` a partir do valor **sem arredondar**; formatar o número de 1 casa pode dar outro resultado (239,46 s/km: texto `3:59`, número `239.5`). O app não formata pace.
- `eixos` (#66): faixa e marcas prontas para o app desenhar, calculadas por `escala_pace` e `escala_fc` (`app/graficos/escala.py`, #63), pelo **valor principal** (`pace_melhor_s_km` e `fc_melhor_tiro`, adendo 1 da ADR 0004; o PNG e o CSV seguem na média e não têm mais a mesma faixa), sobre os valores sem arredondar (1 casa só na saída). Escala mínima de 30 s/km no pace e 5 bpm na FC. `rotulo` do pace é `formatar_pace(valor_s_km)`; o da FC é o inteiro em texto. `invertido: true` no pace (mais rápido no alto). `eixos` é `null` sem sessões; `eixos.fc` é `null` se nenhum melhor tiro tem FC. O app não escolhe escala nem formata pace. O exemplo acima usa as fixtures (as duas sessões).
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

## Upload de FIT: `POST /atletas/{atleta_id}/atividades/fit`
Regras na [[decisoes/0006-upload-de-fit]] (itens 4 e 5). Multipart com um campo `arquivo`; só nome terminado em `.fit`
(maiúsculas valem). Usa `importar_fit` e as exceções de `app/ingestao/importacao.py`; o nome enviado nunca vai para o disco.
```
curl -F "arquivo=@treino.fit" http://localhost:8000/atletas/1/atividades/fit
```
```json
{"resultado": "inserida", "atividade_id": 7, "avisos": []}
```
| Status | Quando |
|---|---|
| `201` | atividade inserida |
| `200` | atividade que já existia (`atualizada` ou `ignorada`) |
| `400` | FIT corrompido, truncado ou sem início/duração; FIT que não é atividade; nome sem `.fit` |
| `404` | atleta inexistente (checado antes de ler o arquivo) |
| `413` | mais de 10 MB (10 485 760 bytes), contado pelos bytes realmente lidos (em pedaços de 64 KB, para em 10 MB + 1) |
| `422` | campo `arquivo` ausente (formato do FastAPI) |

- Erros `400`, `404` e `413` têm o corpo `Erro {detail}`; a mensagem não repete dado do arquivo. `operationId`: `enviarAtividadeFit`.
- Resposta de sucesso no modelo `UploadFitOut`; o tipo `RespostaUploadFit` está em [[modulos/api-client]].
- A pasta vem de `FIT_DIR`; a dependência `get_fit_dir` existe para os testes apontarem para um diretório temporário.
- Sem login: só para uso local (ADR 0006, item 6). `python-multipart` é dependência do `treino-api`.
- Testes: `services/api/tests/rotas/test_upload_fit.py` (um por resposta, o `413` com arquivo sintético gerado no teste, e o OpenAPI).

## Atividade e clima: `GET /atletas/{atleta_id}/atividades/{atividade_id}`
Item 5 da [[decisoes/0007-clima-da-atividade]]. Devolve a atividade (`atividade_id`, `modalidade`, `subtipo`, `inicio` em UTC,
`duracao_s`, `distancia_m`, `fc_media`) com o objeto `clima`, calculado por `clima_da_atividade` (`app/servicos/clima.py`).
`operationId`: `buscarAtividade`.
```json
{"estado": "ok", "temperatura_c": 24.3, "sensacao_c": 25.1, "umidade_pct": 61, "vento_kmh": 8.2}
{"estado": "indoor"}
```
- **Campos prontos para a tela (#158, [[decisoes/0004-contrato-tela-evolucao]], adendo 2):** a regra "a API formata, o app mostra" vale aqui também.
  `data_local` (`AAAA-MM-DD`) e `hora_local` (`HH:MM`): início no fuso da atividade (`fuso_min`; sem ele, `America/Sao_Paulo`, [[decisoes/0003-fuso-da-atividade]]), por `inicio_local` em `app/servicos/fuso.py`. `duracao` em `h:mm:ss` (horas sem limite; segundos arredondados com meio para cima). `pace_medio` em `m:ss` (`formatar_pace` sobre duração / km, sem arredondar antes): só para `corrida` com distância e duração maiores que zero, senão `null`. `clima.atribuicao` = "Weather data by Open-Meteo.com" só quando `estado` é `ok` (ADR 0007, item 4); nos outros estados a chave nem vem. `inicio` em UTC e os campos numéricos continuam. A `carga` (#142) entra na mesma resposta quando sair.
- **`esforcos` (#167, [[decisoes/0008-deteccao-de-esforcos]]):** objeto opcional (`null` fora de corrida e ciclismo) com os blocos que
  `detectar_esforcos` gravou. A API **não detecta** na leitura (`servicos/esforcos_leitura.py`). Campos: `versao` (`esforcos@1`, a gravada; sem
  blocos, a atual), `referencia_da_atividade` (`true` quando não havia histórico e a referência foi a da própria atividade: a tela avisa),
  `treino_chave` (algum esforço é de um treino-chave contínuo) e `blocos` em ordem. Cada bloco: `ordem`, `categoria`
  (`esforco`, `recuperacao`, `aquecimento`, `desaquecimento`, `leve`), `faixa` e `faixa_rotulo` (`d400` / "400 m", `t4` / "4 min"; `null`
  fora de faixa), `treino_chave`, números com 1 casa (`inicio_offset_s`, `duracao_s`, `distancia_m`, `parada_apos_s`, `fc_media`,
  `pace_s_km` só na corrida, `velocidade_kmh` só no ciclismo) e **textos prontos** (ADR 0004): `duracao` e `parada_apos` em `m:ss`
  (`formatar_pace`; `parada_apos` é `null` sem parada), `distancia` ("400 m" ou "1,50 km"), `pace` (`m:ss`, só corrida) e
  `velocidade` ("25,3 km/h", só ciclismo). Chaves de pace/velocidade da outra modalidade nem vêm.
- `ref_origem` não é gravado ([[decisoes/0008-deteccao-de-esforcos]], decisões da #166): `origem_da_referencia` recalcula na leitura com
  `pace_habitual` / `velocidade_habitual` (uma consulta leve ao histórico da modalidade; só colunas, sem blocos). Limite: atividade antiga importada
  depois da detecção pode mudar a origem recalculada em relação à usada; `detectar_esforcos` não regrava sozinho nesse caso.
- Exemplo de contrato: `packages/api-client/exemplos/atividade-esforcos.json` ([[modulos/api-client]]). Testes: `services/api/tests/rotas/test_atividade_esforcos.py`
  (oráculo da #161, textos, aviso de referência, lista vazia com a versão, `404`, modalidade sem detecção, a leitura não detecta, OpenAPI).
- `estado` é `ok`, `indoor`, `sem_posicao`, `pendente` ou `falha`. Os quatro valores só aparecem em `ok`; nos outros estados
  a chave nem vem. O texto do erro da consulta (`erro` da tabela) nunca sai.
- `clima` é campo opcional no schema. A posição de início (`inicio_lat/lon`) nunca está na resposta nem no OpenAPI.
- `404` com `Erro {detail}`: atleta inexistente (`atleta não encontrado`) ou atividade inexistente ou de outro atleta
  (`atividade não encontrada`).
- Por que aqui: é o lugar mais simples para "o clima de cada atividade". O contrato da evolução de tiros
  ([[decisoes/0004-contrato-tela-evolucao]]) não mudou, então o app e o exemplo de contrato continuam iguais.
  Se a tela precisar do clima por sessão, basta acrescentar um `clima` opcional em `SessaoOut`.
- Testes: `services/api/tests/rotas/test_atividade_clima.py` (um por estado, os `404`, a posição fora da resposta, os campos prontos e o OpenAPI).

## Rodar localmente com as fixtures
Passo a passo de ponta a ponta (Postgres, migrações, fixtures, API com `CORS_ORIGENS` e app web) em [[produto/meta-2-como-rodar]]; o do upload de FIT, com como forçar cada status, em [[produto/meta-3-como-rodar]]; o do clima (`GET` da atividade em cada estado), em [[produto/meta-4-como-rodar]]. Resumo: a API demora alguns segundos para subir; `docker compose` sem `-p` reusa o volume `treino-contexto_pgdata`.

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
literal). O cliente gerado (#68) está em [[modulos/api-client]]: depois de mudar o schema ou a resposta, regere com
`uv run python services/api/scripts/exportar_openapi.py` e `cd packages/api-client && npm run gerar`; o teste
`services/api/tests/test_contrato_cliente.py` falha enquanto estiver desatualizado.

## Depende de
- [[modulos/banco]] (Postgres 16 via [[modulos/infra]]).

## Como testar
`uv run pytest -q` na raiz. Roda em SQLite local e em Postgres no CI.

## Pendências
- Contrato da Meta 2 em [[decisoes/0004-contrato-tela-evolucao]]; cliente TypeScript em [[modulos/api-client]]. Ver [[produto/roadmap]].
- Passo a passo para reproduzir a Meta 1: [[produto/meta-1-como-reproduzir]].
- Cada métrica nova ganha nota em [[metricas/]].
