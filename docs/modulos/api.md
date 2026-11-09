---
tipo: modulo
status: em-uso
dono: theo
atualizado: 2026-11-09
links: [[decisoes/0012-check-in-pos-treino]], [[decisoes/0011-linha-de-base-e-semana-padrao]], [[metricas/serie-carga]], [[decisoes/0010-carga-de-treino]], [[decisoes/0001-modelo-de-dados-minimo]], [[decisoes/0003-fuso-da-atividade]], [[decisoes/0004-contrato-tela-evolucao]], [[metricas/tiros-1km]], [[modulos/grafico-tiros]], [[modulos/banco]], [[modulos/worker]], [[modulos/infra]], [[modulos/api-client]], [[decisoes/0006-upload-de-fit]], [[produto/meta-2-como-rodar]], [[decisoes/0007-clima-da-atividade]], [[modulos/clima]], [[produto/meta-4-como-rodar]], [[decisoes/0008-deteccao-de-esforcos]], [[metricas/esforcos]], [[decisoes/0009-treino-de-transicao]]
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
- Entrada e saída: `/atletas/{atleta_id}/treinos-de-transicao` e `PUT`/`DELETE .../atividades/{id}/transicao` (#170, ver "Treino de transição" abaixo).
- Saída: `GET /atletas/{atleta_id}/carga` e o objeto `carga` da atividade (#142, ver "Carga" abaixo).
- Saída: `GET /atletas/{atleta_id}/checkins/pendentes` e `checkin` no `GET` da atividade (#298, ver "Check-in" abaixo).
- Entrada e saída: `PUT`, `GET` e `DELETE /atletas/{atleta_id}/atividades/{atividade_id}/checkin` (#296, ver "Check-in" abaixo).
- Entrada e saída: `GET` e `PUT /atletas/{atleta_id}/semana-padrao` (#264, ver "Semana-padrão" abaixo).

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
- `services/api/app/rotas/transicao.py` e `servicos/transicao_grupos.py`: listar, comparar e corrigir treinos de transição (#170). O rótulo e a regra estão em `servicos/transicao.py` ([[modulos/banco]], #157).
- `services/api/app/servicos/esforcos_leitura.py`: lê os blocos gravados para a resposta da atividade (#167).
- `services/api/app/servicos/evolucao_tiros.py`: liga as métricas ao banco (ver abaixo).
- `services/api/app/explicacao/`: pacote reservado.

## CORS
O app web roda em outra porta (`http://localhost:8081`), então a API libera as origens de `CORS_ORIGENS` (lista
separada por vírgula, lida em `app/config.py`; middleware em `criar_app` de `app/main.py`).
- Padrão local: `http://localhost:8081`. `GET`, `POST` (upload de FIT, #95), `PUT` e `DELETE` (correção da transição, #170; ampliam o item 7 da [[decisoes/0004-contrato-tela-evolucao]]) e o preflight deles; sem cookies nem cabeçalhos extras.
- Nunca `*`: com `*` na lista a API não sobe (`ValueError`). Variável vazia não libera nenhuma origem.
- Origem fora da lista recebe a resposta normal, sem `Access-Control-Allow-Origin` (o navegador bloqueia).
- Exemplo para mais de uma origem: `CORS_ORIGENS=http://localhost:8081,https://app.exemplo.com`.
- Testes: `services/api/tests/test_cors.py`. Variável em [[modulos/infra]].

## Série de tiros no banco (`servicos/evolucao_tiros.py`)
- `classificar_atividades(session, atleta_id)`: primeiro roda `detectar_esforcos` (blocos em `bloco_atividade`, [[metricas/esforcos]]); depois, para cada corrida, aplica a visão de tiros de 1 km ([[metricas/tiros-1km]], `tiros_1km@6`) e marca
  os segmentos como `tiro`, `recuperacao` ou `volta`, gravando `versao_deteccao` (ex.: `tiros_1km@6`) em todos os
  segmentos da corrida. Idempotente. A importação ([[modulos/ingestao-garmin]]) chama no fim.
- **Tipo do treino (desde a #265, [[decisoes/0011-linha-de-base-e-semana-padrao]]):** o `_classificar` só marca os segmentos; o tipo de
  **todas** as atividades do atleta (qualquer modalidade) vem de `servicos/tipo_treino.aplicar_tipos`, que chama a `tipo_treino@1`
  ([[metricas/tipo-treino]]) no fim de `classificar_atividades`: tipo confirmado, `professor` e `trainingpeaks` não mudam; depois a
  semana-padrão vigente na data local (`tipo_origem = semana_padrao`, com `tipo_divergencia` quando o formato contradiz o plano); por
  último a regra de reserva (`sugestao`: `intervalado` por 2 ou mais tiros, como antes, e agora `leve`/`longo` por duração em corrida
  sem esforço). Grava `tipo_treino`, `tipo_origem`, `tipo_versao` e `tipo_divergencia` só quando mudam; se o plano ou a regra deixam de
  valer, o tipo cai para a reserva ou `NULL`. A série de tiros (`sessoes_tiros_1km`) continua lendo só os blocos, nunca `tipo_treino`.
- `sessoes_tiros_1km(session, atleta_id, inicio=None, fim=None)`: o que a rota usa. Por sessão, o `PontoSessao`, o `inicio` em UTC e os tiros (`ordem`, `distancia_m`, `duracao_s`, `fc_media`). Desde a `@5` lê `bloco_atividade`: o tiro é um bloco `esforco` `d1000` e `ordem` é a `segmento.ordem` da primeira volta dele. `distancia_m` `None` segue possível no contrato, mas um bloco sem distância não é tiro.
- `reclassificacao_pendente(session, atleta_id, inicio=None, fim=None)`: `True` se alguma atividade (de qualquer modalidade, no período) tem `tipo_origem` `sugestao` ou `semana_padrao`, não confirmada, com `tipo_versao` diferente de `tipo_treino@1` (inclui o `sugestao` antigo de `tipo_versao` nulo), ou se algum segmento das corridas da série (fora a esteira, dentro do período) tem `versao_deteccao` diferente de `VERSAO`, inclusive `NULL` (nunca classificado), ou se algum bloco foi gravado por outra versão dos esforços. Só lê.
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
{"atleta_id": 1, "metrica": "tiros_1km", "versao_calculo": "tiros_1km@6", "reclassificacao_pendente": false,
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
  `data_local` (`AAAA-MM-DD`) e `hora_local` (`HH:MM`): início no fuso da atividade (`fuso_min`; sem ele, `America/Sao_Paulo`, [[decisoes/0003-fuso-da-atividade]]), por `inicio_local` em `app/servicos/fuso.py`. `duracao` em `h:mm:ss` (horas sem limite; segundos arredondados com meio para cima). `pace_medio` em `m:ss` (`formatar_pace` sobre duração / km, sem arredondar antes): só para `corrida` com distância e duração maiores que zero, senão `null`. `distancia` (#216, adendo 3 da ADR 0004): texto pronto; `natacao` em metros arredondados com ponto de milhar ("1.800 m"), as outras modalidades em km com 2 casas e vírgula ("10,00 km"); `null` sem distância ou com zero (`distancia_da_atividade`, em `app/servicos/distancia_texto.py`, que a lista de treinos de transição também usa). `clima.atribuicao` = "Weather data by Open-Meteo.com" só quando `estado` é `ok` (ADR 0007, item 4); nos outros estados a chave nem vem. `inicio` em UTC e os campos numéricos continuam. O objeto `carga` (#142) vem na mesma resposta (ver "Carga" abaixo).
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
- Exemplo de contrato: `packages/api-client/exemplos/atividade-esforcos.json` ([[modulos/api-client]]). Testes: `services/api/tests/rotas/test_atividade_distancia.py` (`distancia` por modalidade, #216) e `services/api/tests/rotas/test_atividade_esforcos.py`
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

## Treino de transição (#170, [[decisoes/0009-treino-de-transicao]])
Listar, comparar e corrigir o rótulo. O grupo **não é guardado**: sai dos rótulos finais (`transicao = true`, por linha `sugerido` ou
`atleta`) em `servicos/transicao_grupos.py`: atividades rotuladas em sequência, cada uma começando até `INTERVALO_MAX_S` (30 min) depois do
fim da anterior. O **fim** e o **intervalo** são **estimados** (`inicio + duracao_s` é tempo em movimento; o intervalo real pode ser menor).
Textos prontos pela [[decisoes/0004-contrato-tela-evolucao]] (a API formata, o app mostra).
- `GET /atletas/{id}/treinos-de-transicao?inicio=&fim=` (`listarTreinosDeTransicao`): `grupos`, mais recentes primeiro; `inicio`/`fim` (AAAA-MM-DD) são datas locais da primeira parte, inclusivas; `422` se `inicio` > `fim`. Cada grupo: `grupo_id` (o `id` da primeira atividade; **derivado**, muda quando uma correção parte ou junta o grupo, o app não deve guardá-lo), `forma` (`ciclismo>corrida`), `incompleto` (uma parte só: o atleta marcou "sim" avulso), `inicio`/`fim_estimado` (UTC), `data_local`, `hora_local`, `partes` e `transicoes`.
  - parte: `ordem`, `atividade_id`, `modalidade`, `duracao_s`/`duracao` (`h:mm:ss`), `distancia_m`/`distancia` (natação em metros, o resto em km, igual ao da atividade), `fc_media`, `ritmo_valor`/`ritmo_unidade`/`ritmo`: corrida `s/km` ("5:00 /km"), natação `s/100m` ("1:40 /100 m"), ciclismo `km/h` ("30,0 km/h"); ritmo `null` sem distância. A distância não se soma entre partes.
  - `transicoes[]` (uma a menos que as partes): `de_atividade_id`, `para_atividade_id`, `intervalo_estimado_s`/`intervalo_estimado` (`m:ss`, mínimo 0: a diferença do início da seguinte para o maior fim já visto).
  - totais: `soma_duracoes`, `soma_intervalos_estimados`, `tempo_total` (início da primeira ao fim estimado da última) com o `_s` ao lado, e `fc_media` ponderada pela duração só entre as partes com FC.
- `GET /atletas/{id}/treinos-de-transicao/comparar?a=&b=` (`compararTreinosDeTransicao`): `a` e `b` são `grupo_id` da listagem. Só compara a **mesma sequência de modalidades**: `400` com `detail` dizendo a forma de cada um; `404` para grupo inexistente, de outro atleta ou um `id` que é parte e não o início do grupo. Devolve `forma`, os dois grupos e a diferença **B menos A**, sem nota e sem "melhor": por parte (`duracao_dif`, `ritmo_dif` e texto, `fc_dif` e texto, `null` se faltar distância ou FC em um dos lados) e no total (`soma_duracoes_dif`, `soma_intervalos_estimados_dif`, `tempo_total_dif`, `fc_dif`). O intervalo estimado aparece mas **não ranqueia**.
- `PUT /atletas/{id}/atividades/{atividade_id}/transicao` (`corrigirTransicao`), corpo `{"transicao": true|false}`: grava (ou troca) a linha `origem = atleta`, `versao_regra` nulo; devolve `{"valor", "origem": "atleta"}`. Vale para qualquer atividade do atleta, sugerida ou não. A regra (`worker.sugerir_transicao`) nunca mexe nela.
- `DELETE` no mesmo caminho (`desfazerCorrecaoDeTransicao`): apaga só a linha `atleta`, roda `aplicar_sugestao` para o atleta (a mesma regra do `worker.sugerir_transicao`) e devolve `200` com `{valor, origem}` reais: `sugerido` se a regra sugere a atividade, senão `valor = false`, `origem = null`. Sem correção só devolve o estado; nunca apaga uma linha `sugerido`.
- `AtividadeOut.transicao` = `{"valor": bool, "origem": "sugerido"|"atleta"|null}`; sem linha é `valor = false`, `origem = null`.
- `404` (atleta ou atividade, inclusive de outro atleta) e `422` (corpo inválido) como nas outras rotas.
- Testes: `services/api/tests/rotas/test_treinos_de_transicao.py` (dois treinos inventados com contas à mão: intervalos de 120 s e 180 s, ritmos, FC ponderada 145,9, diferenças; corrigir para "não" e rodar a regra de novo; sim avulso `incompleto`; formas diferentes; 404/422). Exemplo de contrato: `packages/api-client/exemplos/treinos-de-transicao.json` ([[modulos/api-client]]).

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

## Carga: `GET /atletas/{atleta_id}/carga` e `carga` na atividade (#142, [[decisoes/0010-carga-de-treino]] itens 5 a 7)
`operationId`: `cargaDoAtleta`. Código: `app/rotas/carga.py` e `app/servicos/carga_leitura.py`. A API **não calcula carga por
atividade**: lê `carga_atividade`, gravada por `worker.calcular_carga` (#141). A série ([[metricas/serie-carga]],
`serie_carga@1`) é calculada na leitura por `calcular_serie`; o serviço faz o dia local ([[decisoes/0003-fuso-da-atividade]]) e
passa `ignoradas_multiesporte`.
- Resposta: `versao` (`serie_carga@1`), `versao_carga` (`carga@1`), `periodo` (o filtro pedido, ou `null`), `aviso`
  (`sem_carga_calculada` quando `dias` está vazio) e `dias`: `data` (dia local), `carga`, `ctl`, `atl`, `tsb`, `aprendendo`,
  `atividades`, `calculadas`, `sem_carga` (dia com `sem_carga > 0` não é descanso).
- `totais` (do atleta todo, não do período): `atividades_importadas`, `calculadas`, `sem_carga_total`, `por_motivo` (os seis
  motivos, sempre todos), `ignoradas_multiesporte` e `pendentes` (elegíveis sem linha **ou com linha de `versao` diferente da `carga@` atual**: desatualizadas até o `calcular_carga` rodar; ficam fora da série, e `atividades_importadas` fecha com a soma).
- `inicio` e `fim` (datas locais, inclusivas) só recortam `dias`; CTL e ATL partem sempre do primeiro dia com carga. `inicio` > `fim`
  é `422`; atleta inexistente é `404` (`Erro`). Atleta sem carga calculada: `dias` vazio com `aviso`.
- **Sem arredondar**: `carga`, `ctl`, `atl` e `tsb` saem com a precisão do cálculo; a tela mostra 1 casa (proposta do Caio).
- `GET .../atividades/{id}` ganha `carga`: `{estado, carga, metodo, cobertura_pct, motivo, versao}` (`calculada` traz carga e método;
  `sem_carga` traz o motivo). `estado: "pendente"` (demais campos `null`, `versao: null`) para atividade elegível sem linha ou com versão antiga; `carga: null` só para `multiesporte_pai` e `troca`.
- **Privacidade:** a API nunca devolve limiar, zonas, recordes nem a carga do Garmin: só carga, método, motivo e cobertura.
- Testes: `tests/rotas/test_carga.py` (oráculo da #137: `SERIE`, `TOTAIS`, `ESPERADO`). Exemplo: `packages/api-client/exemplos/carga.json`.

## Semana-padrão: `GET` e `PUT /atletas/{atleta_id}/semana-padrao` (#264, [[decisoes/0011-linha-de-base-e-semana-padrao]] itens 1, 8 e 9)
`operationId`: `semanaPadraoDoAtleta` e `gravarSemanaPadrao`. Código: `app/rotas/semana_padrao.py` e `app/servicos/semana_padrao.py`. Tabelas em [[modulos/banco]].
- **`GET ?em=AAAA-MM-DD`** (padrão: hoje em `America/Sao_Paulo`): `{atleta_id, em, vigente, vigencias}`. `vigente` é a linha de maior `vigente_desde <= em`, com `vigente_desde`, `definido_por`, `definido_em` (em `America/Sao_Paulo`) e `itens` (`dia_semana` 1 a 7, `dia_semana_texto`, `modalidade`, `tipo_treino` ou `null`), em ordem de dia e modalidade. **`vigente` é `null` só quando nenhuma vigência começou até `em`**; uma vigência vazia (encerra o plano) vem com `itens: []`. `vigencias` traz todas, da mais nova para a mais antiga, com `total_itens`. `404` atleta inexistente; `422` para `em` inválido.
- **`PUT`** `{vigente_desde, definido_por, itens}` cria ou substitui a vigência numa transação (reenviar é idempotente, `itens: []` é válido, `vigente_desde` no futuro é aceito, não há `DELETE`). Resposta `200`: o objeto `vigente` mais `atividades_reaplicadas`. `422` para `dia_semana` fora de 1 a 7, modalidade fora de `corrida`/`natacao`/`ciclismo`, tipo fora dos cinco, `definido_por` fora de `atleta`/`professor` ou ausente, `vigente_desde` inválido ou ausente, `itens` ausente ou repetindo (`dia_semana`, `modalidade`); `404` atleta inexistente.
- **Concorrência:** o upsert do cabeçalho usa `INSERT ... ON CONFLICT DO NOTHING` seguido de busca (dois `PUT` da mesma vigência, como um clique duplo, viram um insert e uma atualização, sem `500`), e atualiza o cabeçalho antes de trocar os itens para serializar os dois. Sem savepoint de propósito (no pysqlite o `RELEASE` commita a transação externa).
- **Reaplicação do tipo (#265).** Depois de gravar, o `PUT` chama `servicos.semana_padrao.reaplicar_tipos(session, atleta_id, vigente_desde)`, que roda a `tipo_treino@1` ([[metricas/tipo-treino]]) por dia nas atividades com **data local >= `vigente_desde`** (as anteriores não são lidas nem regravadas), usando os blocos já gravados (não roda `detectar_esforcos`), sem tocar tipo confirmado, `professor` nem `trainingpeaks`. `atividades_reaplicadas` é quantas mudaram de tipo, origem, versão ou divergência (reenviar o mesmo `PUT` dá 0). Tudo na mesma transação: se a reaplicação falhar, o `PUT` inteiro volta atrás.
- `definido_por` é rótulo declarado, não verificado: não há login (ADR 0011, "A confirmar" 1 e 7). Plano de treino é dado pessoal: não vai para log.
- Testes: `tests/rotas/test_semana_padrao.py` (vigência no dia, vigência vazia, antes da primeira vigência, `em` padrão em São Paulo, `422`/`404`, rollback, concorrência simulada e, no Postgres, duas sessões de verdade) e `tests/test_migracoes.py`.

## Tipo, divergência e linha de base no `GET /atletas/{atleta_id}/atividades/{atividade_id}` (#266, [[decisoes/0011-linha-de-base-e-semana-padrao]] itens 6, 7 e 9)
Código: `app/servicos/linha_base_leitura.py` (monta os valores e os textos) sobre a função pura `app/metricas/linha_base.py` ([[metricas/linha-base]]);
modelos Pydantic em `app/rotas/atividades.py`. **Calculada na leitura, nada é gravado.** Campos novos, sem remover nenhum (adendo 6 da [[decisoes/0004-contrato-tela-evolucao]]):
- `tipo_treino`, `tipo_origem` (`sugestao`, `professor`, `trainingpeaks`, `semana_padrao`), `tipo_confirmado` e `tipo_divergencia` (`null` ou `{motivo, texto}`;
  `sem_esforco`: "O plano diz intervalado, mas o treino não teve esforço detectado."; `tem_tiros`: "O plano diz leve, mas o treino teve 6 tiros de 1 km.").
- `linha_base`: `versao`, `estado` (`ok` ou `sem_linha_base`), `motivo`, `texto` (só em `sem_linha_base`), `modalidade`, `tipo_treino`, `janela_semanas`, `minimo_treinos` e `metricas`.
  Sem linha de base, o `motivo` é o primeiro de `multiesporte`, `modalidade_sem_metricas`, `sem_tipo`, `divergente`, com `metricas: []` (a parte de treino de transição tem base própria desde a `linha_base@2`).
  Por métrica (as do tipo, ADR 0011 item 7): `chave` (`pace_medio`, `melhor_pace`, `fc_media`, `fc_melhor_tiro`, `carga_hora`), `rotulo`, `unidade`, `estado`
  (`fora`, `dentro`, `aprendendo`, `sem_valor`), `motivo` (em `sem_valor`: `esteira`, `sem_tiros`, `sem_fc`, `sem_distancia`, `carga_pendente` ou o motivo da carga), `valor`,
  `valor_texto`, `mediana`, `mediana_texto`, `desvio`, `z`, `n`, `diferenca_texto` (só em `fora`) e `texto` pronto. Os números brutos saem **sem arredondar**; em `aprendendo` e `sem_valor` não há mediana, desvio nem z.
- Formato dos textos (a API formata, o app só mostra). `pontos/h` é só o **nome da unidade da carga por hora na tela** (a carga não tem unidade física); aparece igual em `valor_texto`, `mediana_texto` e `diferenca_texto`.

  | `chave` | `rotulo` | `unidade` | `valor_texto` / `mediana_texto` | `diferenca_texto` |
  |---|---|---|---|---|
  | `pace_medio` | Pace médio | `s/km` | `5:06/km` | `24 s/km mais rápido` ou `mais lento` |
  | `melhor_pace` | Pace do melhor tiro | `s/km` | `4:09/km` | `13 s/km mais rápido` ou `mais lento` |
  | `fc_media` | FC média | `bpm` | `148 bpm` | `5 bpm acima` ou `abaixo` |
  | `fc_melhor_tiro` | FC do melhor tiro | `bpm` | `172 bpm` | `4 bpm acima` ou `abaixo` |
  | `carga_hora` | Carga por hora | `pontos/h` | `55,0 pontos/h` | `13,0 pontos/h maior` ou `menor` |

  No texto de `sem_valor` o rótulo vai para minúsculas, mantendo a sigla `FC` ("Sem FC média neste treino: ...").
- Valores: `pace_medio` = duração / distância (corrida, fora a esteira); `melhor_pace` e `fc_melhor_tiro` = o melhor tiro da série `tiros_1km@6` (a FC dele, sem trocar de tiro; a esteira fica sem `melhor_pace`); `fc_media` = `atividade.fc_media`; `carga_hora` = a `carga@2` calculada dividida pelas horas de `duracao_s` (sem linha ou de versão antiga: `carga_pendente`; sem duração: `sem_duracao`).
- Janela: mesmo atleta, modalidade e tipo, 84 dias (12 semanas) antes da sessão pela data local, só treinos anteriores, sem divergentes e sem multiesporte; a parte de treino de transição compara só com partes de transição e a isolada só com isoladas (`linha_base@2`). Uma consulta por atividade, da ordem de dezenas de linhas.
- Testes: `tests/rotas/test_linha_base_atividade.py` (oráculo das fixtures de `tests/fixtures/meta7/` passando pelo banco e pela rota: `LINHA_BASE_ESPERADA`, `SEM_LINHA_BASE`, textos, esteira, sem FC). Exemplo: `packages/api-client/exemplos/atividade-esforcos.json`.

## Check-in pós-treino: `PUT`, `GET` e `DELETE /atletas/{atleta_id}/atividades/{atividade_id}/checkin` (#296, [[decisoes/0012-check-in-pos-treino]])
`operationId`: `registrarCheckin`, `checkinDaAtividade`, `apagarCheckin`. Código: `app/rotas/checkin.py` (modelos e rotas) e `app/servicos/checkin.py` (prazo, elegibilidade, upsert). Tabela `checkin_treino` em [[modulos/banco]]. **Dado pessoal e de saúde**: só nestas rotas, do próprio atleta (`/atletas/{id}/...`; atividade de outro atleta é `404`, nas três rotas, inclusive no `DELETE`).
- **`PUT`** `{pse, sensacao, nada_a_relatar, atalhos, texto}` cria ou **substitui** o check-in (um por atividade; `200` nos dois casos; atalho que não vier fica desligado). `pse` inteiro de 0 a 10 (CR-10), `sensacao` inteiro de 1 a 5, `atalhos` entre `dor`, `cansaco`, `sono_ruim`, `calor`, `trabalho_estresse` (sem repetir), `texto` até 500 caracteres (aparado; vazio vira `NULL`). Ou `nada_a_relatar = true` **sem** atalho e sem texto, ou `false` com ao menos um atalho ou texto. Resposta `CheckinOut`: `pse_texto` (âncora: repouso, muito leve, leve, moderado, um pouco difícil, difícil, muito difícil, máximo; 6, 8 e 9 só o número), `sensacao_texto` (muito mal ... muito bem), `atalhos` (`chave` e `texto`), `versao` (`checkin@1`), `registrado_em` e `atualizado_em` (`America/Sao_Paulo`; `registrado_em` não muda na edição).
- **`GET`**: o `CheckinOut`, ou `404` "sem check-in". **`DELETE`**: remove a linha (sem prazo), `204` também quando já não havia.
- **Prazo e elegibilidade (parâmetros de produto, "A confirmar" 1 e 2 da ADR):** `PRAZO_DIAS = 7` e `SUBTIPOS_SEM_CHECKIN = {multiesporte_pai, troca}` em `servicos/checkin.py`. Criar vale até 7 dias depois do dia local do treino (`dias_ate_hoje`, "hoje" em `America/Sao_Paulo`); depois, `422` `fora_do_prazo`. Editar e apagar não têm prazo. Pai e troca: `422` `atividade_sem_checkin`; cada parte do multiesporte tem o seu check-in.
- **`422` sem eco da entrada:** uma `APIRoute` própria (`RotaCheckin`), só neste router, devolve só `loc`, `msg` e `type` (nem `input`, nem `ctx`); os `422` de domínio usam o mesmo formato com o código em `type`. Mensagens do validador de coerência são fixas. Erro inesperado vira `500` com texto fixo e o log leva só o tipo da exceção e a rota (a mensagem de um erro de banco pode trazer os parâmetros). O `PUT` feliz loga só ids e a contagem de atalhos. As outras rotas da API mantêm o `422` padrão.
- **Upsert:** busca a linha; se não há, `INSERT ... ON CONFLICT DO NOTHING` em `atividade_id` (SQLite e Postgres), nova busca e `UPDATE` (sem `id` nem `registrado_em`). Sem savepoint (o do pysqlite commita a transação externa no `RELEASE`), como na semana-padrão.
- Sem login (ADR 0012, "A confirmar" 5): quem conhece o `atleta_id` lê, grava e apaga. Comando para apagar todos: `worker.apagar_checkin` ([[modulos/worker]]).
- **No `GET` da atividade e a lista de pendentes (#298):** `GET /atletas/{atleta_id}/atividades/{atividade_id}` ganha `checkin` (o `CheckinOut` ou `null`; carregado com `LEFT JOIN` na mesma consulta da atividade), `checkin_aberto` (`false` em `multiesporte_pai`/`troca` e quando o prazo passou sem check-in; `true` se já existe, pois editar não tem prazo) e `pse_sugerida` (numa parte de multiesporte, a PSE do check-in da parte anterior: a atividade elegível de `inicio` imediatamente menor dentro do intervalo do `multiesporte_pai` do atleta; `null` fora de multiesporte, na primeira parte ou sem check-in na anterior). `GET /atletas/{atleta_id}/checkins/pendentes?dias=7` (`listarCheckinsPendentes`) lista as atividades **sem check-in** com data local em `[hoje - dias, hoje]` (`hoje` em `America/Sao_Paulo`), mais recentes primeiro, toda modalidade menos pai e troca; cada item: `atividade_id`, `modalidade`, `data_local`, `hora_local`, `duracao`, `titulo` ("Corrida, 45 min"), **nenhum campo do check-in**; `dias` de 1 a 7 (padrão 7), fora disso `422` sem eco. `LEFT JOIN checkin_treino ... WHERE checkin_treino.id IS NULL` com `subtipo IS NULL OR subtipo NOT IN (...)`. A `carga_pse` no `GET` é da #297. Testes: `tests/rotas/test_checkin_get_pendentes.py` (oráculo das fixtures `tests/fixtures/meta8/`: `PENDENTES`, `PRAZO_CRIAR`, `NAO_ELEGIVEIS`).
- Testes: `tests/rotas/test_checkin.py` (gravar, ler, editar, apagar, "nada a relatar", `422` em 14 entradas, marcador sintético fora da resposta e do `caplog`, `404`, prazo nas bordas 23:00/00:00 locais, concorrência simulada e, no Postgres, duas sessões de verdade).

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
