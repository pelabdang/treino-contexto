---
tipo: decisao
status: em-uso
dono: theo
atualizado: 2026-11-27
links: [[decisoes/0013-feedback-automatico]], [[modulos/api]], [[modulos/grafico-tiros]], [[modulos/mobile]], [[modulos/worker]], [[metricas/tiros-1km]], [[decisoes/0002-segmento-intensidade-e-versao]], [[decisoes/0003-fuso-da-atividade]], [[decisoes/0005-serie-de-tiros-o-que-entra]], [[decisoes/0006-upload-de-fit]], [[decisoes/0007-clima-da-atividade]], [[produto/roadmap]], [[design/telas/treino]], [[decisoes/0009-treino-de-transicao]], [[metricas/evolucao-series]]
---
# ADR: 0004 Contrato da tela de evolução dos tiros (Meta 2)

**Status: aceita**, com a aprovação do Theo neste PR. A numeração 0004 ficou reservada na [[decisoes/0005-serie-de-tiros-o-que-entra]].

## Contexto
A Meta 2 leva o gráfico da Meta 1 para o app (web, iOS e Android). O app lê o JSON de
`GET /atletas/{atleta_id}/evolucao/tiros-1km` ([[modulos/api]]). Antes de abrir as issues, o contrato foi conferido
com o código do `main` (regra `tiros_1km@4`) e com o OpenAPI gerado por `app.main`. Apareceram divergências entre o
que o endpoint declara e o que devolve. Isso afeta a API, o PNG ([[modulos/grafico-tiros]]), o cliente gerado e o
app, por isso é ADR.

Duas decisões de produto guiam o texto: o app **não formata pace** e **não escolhe a escala dos eixos**. A API
manda tudo pronto.

## Decisão
1. **Pace só pela API.** Todo pace que o app mostra vem em `m:ss`, feito por `formatar_pace`
   ([[metricas/tiros-1km]]): o da sessão, o do tiro e os rótulos dos eixos. O app não tem nenhuma função de pace.
   Um teste do app usa um JSON em que o texto foi trocado de propósito (por exemplo `"9:99"`) e confere que a tela
   mostra esse texto (#70).
2. **Bloco `eixos`** no JSON, com faixa (`min`, `max`) e marcas com `rotulo` para pace e FC, pela mesma regra do PNG
   (função `escala_eixo`, #63). Escala mínima: **5 bpm na FC** (decisão do Angelo, não muda sem ele) e
   **30 s/km no pace** (valor inicial; o Caio e a Bia podem ajustar, registrando na nota). Rótulos de pace vêm de
   `formatar_pace`. Sem sessões, `eixos` é `null`; sem FC em nenhuma sessão, `eixos.fc` é `null` (#66).
3. **`versao_calculo` é sempre a constante `VERSAO`** da regra. Novo campo booleano `reclassificacao_pendente`:
   `true` quando algum segmento da série foi gravado com `versao_deteccao` diferente de `VERSAO` (#64).
   - A API **não reclassifica na leitura** e não escreve no banco num `GET`.
   - Reclassificar é um comando do operador: `python -m worker.reclassificar --atleta-id N`, criado na #64, que
     também escreve o passo a passo em [[modulos/api]] (seção "Reclassificar"). Reimportar a exportação continua
     como alternativa. Depois disso, `reclassificacao_pendente` volta a `false`.
   - O app só mostra a versão (rodapé "cálculo: ...") e nunca a compara com um texto fixo.
4. **Erros.** `404` declarado no OpenAPI, nos dois endpoints, com o modelo `Erro {detail: string}`. `inicio > fim`
   vira `422` (hoje devolve `200` vazio). `operationId` legível: `evolucaoTiros1km` e `evolucaoTiros1kmPng` (#64).
5. **Arredondamento e falta de dado.** Todo número decimal do JSON sai com 1 casa, inclusive o do tiro. Distância que
   falta é `null`, nunca `0` (#64). O pace em `m:ss` sai do valor **sem arredondar**, não do valor de 1 casa.
6. **Cliente gerado** em `packages/api-client/` a partir de um `openapi.json` versionado (gerado por
   `app.openapi()`, sem subir servidor), mais um exemplo de contrato sintético. Um teste do pytest falha quando o
   `openapi.json` ou o exemplo estão desatualizados e diz o comando para regerar (#68).
7. **CORS por variável de ambiente** `CORS_ORIGENS` (lista separada por vírgula). Padrão local
   `http://localhost:8081`, só `GET`, nunca `*`; variável vazia não libera nenhuma origem (#65). Ampliada pela [[decisoes/0006-upload-de-fit]]: libera também
   `POST` para o upload de FIT; continua sem `*`.
8. **Atleta por configuração.** Não há login nem lista de atletas nesta meta: o app lê `EXPO_PUBLIC_ATLETA_ID`
   (padrão `1`) e `EXPO_PUBLIC_API_URL` (#67).

### O que muda no contrato (antes e depois)
"Antes" conferido no `main` (`rotas/evolucao.py`, `servicos/evolucao_tiros.py`, `metricas/tiros_1km.py`, OpenAPI de `app.main`).

| # | Tema | Antes | Depois | Issue |
|---|---|---|---|---|
| D1 | Cliente TypeScript | `packages/` não existe; não há script de geração | `packages/api-client/` com `openapi.json`, tipos gerados, função `buscarEvolucaoTiros1km` e teste de "desatualizado" | #68 |
| D2 | Erro 404 | OpenAPI declara só `200` e `422`; o código devolve `404 {"detail": "atleta não encontrado"}` | `404` declarado com `Erro {detail: string}` nos dois endpoints | #64 |
| D3 | `versao_calculo` | Vem do primeiro `versao_deteccao` não nulo de cada sessão, e o JSON usa a da primeira sessão (`sessoes[0]`); sem sessões, `VERSAO`. O filtro do ritmo habitual (`@4`, 10%) roda na hora com a regra atual, então o JSON pode dizer uma versão e aplicar outra; versões misturadas ficam escondidas | Sempre `VERSAO`, mais `reclassificacao_pendente` | #64 |
| D4 | `Unidades` | Campos com `default`, sem `required` no schema (tipos opcionais no cliente) | Todos obrigatórios no schema | #64 |
| D5 | Arredondamento | Sessão: pace e FC com 1 casa. Tiro: só `pace_s_km`; `fc_media`, `distancia_m` e `duracao_s` saem crus | Todo decimal com 1 casa | #64 |
| D6 | `pace_medio` x `pace_medio_s_km` | `pace_medio` vem do valor cru e `pace_medio_s_km` do arredondado; formatar o segundo erra (239,46 s/km: API diz `3:59`, formatar 239,5 dá `4:00`) | Regra mantida e escrita: o texto é da API, o app nunca formata | #64, #70 |
| D7 | Pace do tiro em `m:ss` | `TiroOut` só tem `pace_s_km` | Novo campo `pace` (`m:ss`; `null` se `pace_s_km` é `null`) | #64 |
| D8 | Distância que falta | A origem é o serviço (`s.distancia_m or 0.0` em `servicos/evolucao_tiros.py`): segmento sem distância vira `distancia_m: 0.0` (e a rota põe `pace_s_km: null`) | `distancia_m: null` e `pace: null` | #64 |
| D9 | `inicio` > `fim` | `200` com `sessoes: []` | `422` | #64 |
| D10 | `operationId` | `evolucao_tiros_1km_atletas__atleta_id__evolucao_tiros_1km_get` | `evolucaoTiros1km` e `evolucaoTiros1kmPng` | #64 |
| D11 | `metrica` | `string` livre | `Literal["tiros_1km"]` | #64 |
| D12 | CORS | `main.py` sem `CORSMiddleware`; o app web (outra porta) é bloqueado | `CORS_ORIGENS` | #65 |
| D13 | Qual atleta mostrar | Só `GET /atletas/{id}/...` | Atleta por `EXPO_PUBLIC_ATLETA_ID` (login fica para outra meta) | #67 |
| D14 | App | `apps/mobile` é o modelo vazio do Expo (`App.tsx`), sem Expo Router | Expo Router em `src/app/` | #67 |
| E1 | Eixos | Não existe; o PNG escolhe a faixa pelos dados | Bloco `eixos` (decisão 2), mesma regra no PNG | #63, #66 |

Sem mudança: `data` local `AAAA-MM-DD` e `inicio` em UTC com `Z`; `periodo` `null` sem filtro; `fc_media` da sessão
pode ser `null`; `422` para data inválida; sessões por data crescente.

### Exemplo de JSON (sintético: fixtures, atleta 1)
Mostra o formato final. Os valores dos `eixos` ilustram a forma; o passo e as marcas exatas são da #63.
```json
{
  "atleta_id": 1,
  "metrica": "tiros_1km",
  "versao_calculo": "tiros_1km@6",
  "reclassificacao_pendente": false,
  "unidades": {"pace": "s/km", "fc": "bpm", "distancia": "m", "duracao": "s"},
  "periodo": {"inicio": "2025-03-01", "fim": null},
  "eixos": {
    "pace": {"min_s_km": 235.8, "max_s_km": 265.8, "invertido": true,
             "marcas": [{"valor_s_km": 240.0, "rotulo": "4:00"}, {"valor_s_km": 255.0, "rotulo": "4:15"}]},
    "fc":   {"min_bpm": 167.8, "max_bpm": 172.8,
             "marcas": [{"valor_bpm": 168.0, "rotulo": "168"}, {"valor_bpm": 170.0, "rotulo": "170"}, {"valor_bpm": 172.0, "rotulo": "172"}]}
  },
  "sessoes": [{
    "atividade_id": 1, "data": "2025-03-04", "inicio": "2025-03-04T09:00:00Z", "n_tiros": 6,
    "pace_medio_s_km": 250.8, "pace_medio": "4:11", "fc_media": 170.3,
    "tiros": [{"ordem": 1, "distancia_m": 1000.0, "duracao_s": 255.0, "pace_s_km": 255.0, "pace": "4:15", "fc_media": 165.0}]
  }]
}
```
Erro: `{"detail": "atleta não encontrado"}` com `404`. Resposta com `422` mantém o formato do FastAPI (`detail` é lista).

## Alternativas consideradas
- **`formatarPace` em TypeScript num pacote compartilhado:** duas implementações da mesma regra; a D6 mostra como
  elas divergem fácil.
- **Teste de contrato com tabela-gabarito nos dois lados (239,5 → 4:00; 238,5 → 3:59; 59,5 → 1:00):** pega
  divergência, mas continua com duas implementações e a tabela nunca cobre tudo.
- **Reclassificar na leitura (a API regrava os segmentos quando a versão está velha):** um `GET` passaria a escrever
  no banco e ficaria lento e imprevisível. Preferimos avisar com `reclassificacao_pendente`.
- **`versao_calculo` lida do banco (como hoje):** pode dizer uma versão e aplicar outra (o filtro do ritmo habitual
  roda na hora, com a regra atual).
- **App escolhe a escala dos eixos:** cada tela teria uma regra, diferente do PNG. A regra fica numa função só.
- **CORS com `*`:** libera qualquer origem; fica proibido.

## Consequências
- O JSON leva um pouco de apresentação (texto de pace e rótulos dos eixos). Em troca há uma implementação só de
  `formatar_pace` e da escala, a mesma no JSON, no PNG e no CSV.
- Mudar a escala mínima (pace) ou o formato de um campo muda o contrato: regerar `openapi.json` e o exemplo; o teste
  da #68 falha enquanto não regerar.
- Quem muda a regra de detecção (nova `VERSAO`) vê `reclassificacao_pendente: true` até reclassificar
  ([[decisoes/0005-serie-de-tiros-o-que-entra]], item 4). Misturas de versão deixam de ficar escondidas.
- O app depende do shape, não do valor, de `versao_calculo`.
- Sem login: o app mostra um atleta fixo até a meta de login.
- Ordem das issues: #63 (escala) e #64 (endpoint) primeiro, depois #66 (eixos), #68 (cliente e exemplo); #65 (CORS) e
  #67 (app) correm em paralelo. O gráfico e a tela do app vêm depois do cliente.

## Data e quem decidiu
2026-11-03. Pace só pela API (opção A) e `versao_calculo` com `reclassificacao_pendente`, sem reclassificar na
leitura: Theo. Escala mínima de 5 bpm na FC, app local sem deploy, atleta fixo por variável e Expo: Angelo. Escala
mínima de 30 s/km no pace: time (Caio e Bia ajustam). Aprovação do Theo no PR deste ADR.

## Adendo 1 (2026-11-04): melhor tiro como valor principal (#152)
**Status: aprovado (Theo, 04/11).** Decisão de produto do Angelo (04/11): o valor principal do gráfico
é o **melhor pace de tiro** da sessão; a média fica como secundária; o painel de FC mostra a **FC do melhor tiro**.
O melhor tiro vem de `agregar_sessao` (#151): o de menor pace; empate fica com o primeiro; se ele não tem FC, a FC
fica `null` (não se troca por outro tiro).

### Campos novos em cada item de `sessoes` (todos de uma vez, sem remover nenhum)
| Campo | Tipo | Regra |
|---|---|---|
| `pace_melhor_s_km` | número, obrigatório | pace do melhor tiro, 1 casa |
| `pace_melhor` | texto `m:ss`, obrigatório | `formatar_pace` sobre o valor **sem arredondar** (o app não formata pace) |
| `fc_melhor_tiro` | número ou `null` | FC do melhor tiro, 1 casa; `null` se ele não tem FC |
| `ordem_melhor_tiro` | inteiro, obrigatório | `ordem` do melhor tiro dentro de `tiros` (para o app destacá-lo; extra pedido pela leitura do contrato, além dos três da issue) |

Mantidos por compatibilidade: `pace_medio_s_km`, `pace_medio`, `fc_media` (a média, agora secundária), com as
mesmas regras de antes.

### Valor principal e bloco `eixos`
- Valor principal do gráfico de pace: `pace_melhor_s_km` (texto `pace_melhor`). Do painel de FC: `fc_melhor_tiro`.
  A média (`pace_medio*`, `fc_media`) é detalhe secundário.
- `eixos` passa a ser calculado **pelo valor principal**: `eixos.pace` sobre os `pace_melhor_s_km` e `eixos.fc`
  sobre os `fc_melhor_tiro` (sem arredondar, 1 casa só na saída), com a mesma `escala_eixo` e as mesmas escalas
  mínimas (30 s/km e 5 bpm). Sessão com `fc_melhor_tiro` `null` não entra na escala da FC; se nenhuma tem,
  `eixos.fc` é `null`. A média não entra nos eixos (se o app desenhar a média, ela pode sair da faixa).
- **O PNG e o CSV continuavam com a média na #152; a #153 os levou ao melhor tiro** (ver [[modulos/grafico-tiros]]). Entre a #152 e a #153 a decisão 2 ("mesma
  regra do PNG") valeu só quanto à função `escala_eixo`; com a #153 o JSON e o PNG voltam a ter a mesma faixa (pelo melhor tiro).

### Exemplo (fixtures, sessão 1 da amostra)
```json
{"atividade_id": 1, "data": "2025-03-04", "inicio": "2025-03-04T09:00:00Z", "n_tiros": 6,
 "pace_medio_s_km": 250.8, "pace_medio": "4:11", "fc_media": 170.3,
 "pace_melhor_s_km": 248.0, "pace_melhor": "4:08", "fc_melhor_tiro": 175.0, "ordem_melhor_tiro": 11,
 "tiros": [...]}
```

### Consequências
- Mudança aditiva no JSON; o cliente TypeScript é regerado (`SessaoOut` ganha os quatro campos). O app (#154) passa a
  ler os novos campos como principais.
- `PontoSessao` mantém os defaults `None` do melhor tiro: ponto montado à mão, sem os campos, só aparece na média do PNG
  e tem as colunas do melhor tiro vazias no CSV ([[modulos/grafico-tiros]], #153).

## Adendo 2 (2026-11-06): a regra "a API formata, o app mostra" vale também para a tela de um treino (#158)
**Status: aceito (Theo, 06/11).** Não muda o modelo de dados. `GET /atletas/{id}/atividades/{id}`
ganha campos prontos, para o app não formatar pace nem converter fuso: `data_local` (`AAAA-MM-DD`) e `hora_local`
(`HH:MM`) pelo fuso da atividade ([[decisoes/0003-fuso-da-atividade]]), `duracao` (`h:mm:ss`), `pace_medio` (`m:ss` de
`formatar_pace`, só para corrida com distância; `null` nas outras modalidades) e `clima.atribuicao` (só com clima `ok`,
[[decisoes/0007-clima-da-atividade]], item 4). Os campos antigos continuam. Detalhes em [[modulos/api]].

## Adendo 3 (2026-11-06): `distancia` pronta na tela de um treino (#216)
**Status: aceito (Theo, 06/11).** Não muda o modelo de dados. `GET /atletas/{id}/atividades/{id}` ganha `distancia`, o texto
da distância já na unidade da modalidade, como pede [[design/telas/treino]]: corrida, ciclismo e outras em km com duas casas e
vírgula ("10,00 km"); natação em metros arredondados, com ponto de milhar ("1.800 m"); `null` quando a atividade não tem
distância (ausente ou zero). `distancia_m` continua. A decisão da unidade é da API; o app só mostra. A troca no app, o
alinhamento do "Ver treino" e as capturas de natação ficam com o app (#216, parte do app). Detalhes em [[modulos/api]].

## Adendo 4 (2026-11-06): CORS libera também PUT e DELETE (#170)
**Status: aceito (Theo, 06/11).** Estende o item 7 (CORS): além de `GET` e `POST`, a API libera `PUT` e `DELETE` para as origens
de `CORS_ORIGENS`, para o app web corrigir e desfazer o rótulo de transição ([[decisoes/0009-treino-de-transicao]]). Nada mais muda
no CORS (sem `*`, sem cookies). Detalhes em [[modulos/api]].

## Adendo 5 (2026-11-09): semana-padrão entra no contrato (#264)
**Status: aceito (Theo, 09/11, modelo de dados da [[decisoes/0011-linha-de-base-e-semana-padrao]]).** Duas rotas novas, sem mudar
nenhuma existente: `GET` e `PUT /atletas/{atleta_id}/semana-padrao` (`semanaPadraoDoAtleta` e `gravarSemanaPadrao`). Valem a regra do
adendo 2 ("a API formata, o app mostra"): o item traz `dia_semana_texto` pronto (`segunda`, `terça`...) e `definido_em` já em
`America/Sao_Paulo`; o app não monta texto de dia. Erros no formato de sempre: `404` com `Erro` (`detail` string) e `422` do FastAPI
(`detail` lista). O `PUT` devolve `atividades_reaplicadas` (quantas atividades mudaram de tipo; a #265 reaplica o tipo). Os tipos entram em
`packages/api-client` (`SemanaPadrao`, `SemanaPadraoGravada` e afins); ainda sem função de busca (a tela é a #267).
O que a ADR 0011 prevê para a atividade (`tipo_origem` com `semana_padrao`, `tipo_divergencia` e `linha_base` no `GET .../atividades/{id}`)
**não entra aqui**: é a #266, com outro adendo. Detalhes em [[modulos/api]].

## Adendo 6 (2026-11-09): tipo, divergência e `linha_base` no `GET` da atividade (#266)
**Status: aceito (Theo, 09/11, [[decisoes/0011-linha-de-base-e-semana-padrao]] item 9).** `GET /atletas/{atleta_id}/atividades/{atividade_id}`
ganha campos, sem remover nenhum: `tipo_treino`, `tipo_origem` (agora também `semana_padrao`), `tipo_confirmado`, `tipo_divergencia`
(`null` ou `{motivo, texto}` com `motivo` `sem_esforco` ou `tem_tiros` e o texto pronto) e `linha_base`. Vale o adendo 2: a API formata e
o app mostra. `linha_base` traz `versao` (`linha_base@1`), `estado` (`ok` ou `sem_linha_base`, com `motivo` e `texto` pronto, e
`metricas: []`), `modalidade`, `tipo_treino`, `janela_semanas` (8), `minimo_treinos` (8) e `metricas`: por métrica `chave`, `rotulo`,
`unidade`, `estado` (`fora`, `dentro`, `aprendendo`, `sem_valor`), `motivo` (só em `sem_valor`), `valor`, `valor_texto`, `mediana`,
`mediana_texto`, `desvio`, `z`, `n`, `diferenca_texto` (só em `fora`) e `texto`. `valor`, `mediana`, `desvio` e `z` saem **sem
arredondar** (o exemplo da ADR 0011 mostrava 8,9 e -2,7 como ilustração), para o app ordenar e para o motor de explicação; em
`aprendendo` e `sem_valor` não há mediana, desvio nem z. O texto nunca julga o treino: compara com o histórico do atleta. Calculada na
leitura, nada é gravado. Detalhes em [[modulos/api]].

## Adendo 7 (2026-11-09): `linha_base@2` no `GET` da atividade (#288)
**Status: aceito (decisão do Angelo, 09/11; [[decisoes/0011-linha-de-base-e-semana-padrao]], adendo 2).** Muda o objeto `linha_base` do adendo 6 sem
mudar o modelo de dados: `versao` passa a `linha_base@2` e `janela_semanas` a 12; em cada métrica, `chave` troca `carga` por `carga_hora`
e `unidade` troca `pontos` por `pontos/h` (rótulo "Carga por hora"); `motivo` de `linha_base` perde `transicao` (a parte de treino de transição
tem base própria) e o `sem_valor` ganha `sem_duracao`. O `intervalado` ganha a métrica `fc_media`. O app ainda não lê o objeto. Detalhes em [[modulos/api]].


## Adendo 8 (2026-11-09): check-in pós-treino entra no contrato (#296)
**Status: aceito (Theo, 09/11, modelo de dados da [[decisoes/0012-check-in-pos-treino]]).** Três rotas novas, sem mudar nenhuma existente:
`PUT`, `GET` e `DELETE /atletas/{atleta_id}/atividades/{atividade_id}/checkin` (`registrarCheckin`, `checkinDaAtividade`,
`apagarCheckin`). O `CheckinOut` segue o adendo 2 ("a API formata, o app mostra"): `pse_texto` (a âncora da CR-10 quando existe, senão o
número), `sensacao_texto`, `atalhos` com `chave` e `texto` prontos e `registrado_em`/`atualizado_em` já em `America/Sao_Paulo`.
Erros: `404` com `Erro` (atleta, atividade ou, no `GET`, check-in inexistente; atividade de outro atleta também) e `422` **só nestas rotas**
no formato `{"detail": [{"loc", "msg", "type"}]}`, **sem `input` nem `ctx`** (o check-in é dado de saúde e o `422` padrão do FastAPI
repetiria o texto enviado); os `422` de domínio usam o código no `type`: `fora_do_prazo` e `atividade_sem_checkin`. O `DELETE` devolve
`204`, também quando já não havia. O corpo do `422` continua declarado no OpenAPI como `HTTPValidationError` (descrição só de `loc`,
`msg` e `type`). `checkin` e `carga_pse` no `GET` da atividade e a lista de pendentes são da #298, com outro adendo. Detalhes em [[modulos/api]].

## Adendo 9 (2026-11-09): `checkin`, `carga_pse`, `checkin_aberto`, `pse_sugerida` e lista de pendentes (#298)
**Status: aceito (Theo, 09/11, [[decisoes/0012-check-in-pos-treino]]).** `GET /atletas/{atleta_id}/atividades/{atividade_id}` ganha, sem remover campo: `checkin` (o
`CheckinOut` do adendo 8, ou `null` sem check-in ou em `multiesporte_pai` e `troca`), `checkin_aberto` (`false` em pai e troca e quando o
prazo de criação passou sem check-in; `true` se já existe check-in, porque editar não tem prazo) e `pse_sugerida` (inteiro ou `null`: numa
parte de multiesporte, a PSE do check-in da parte anterior do mesmo multiesporte, se houver). Os dois últimos campos saem do desenho da
tela (#295, decisão do Theo). `checkin_aberto` só orienta a tela: o `PUT` continua recusando o que não vale. Rota nova:
`GET /atletas/{atleta_id}/checkins/pendentes?dias=7` (`listarCheckinsPendentes`): `{dias, total, pendentes}`, cada item com
`atividade_id`, `modalidade`, `data_local`, `hora_local`, `duracao` e `titulo` prontos ("Corrida, 45 min"), mais recentes primeiro,
**sem nenhum campo do check-in**; `dias` de 1 a 7 (fora disso, `422` sem `input` nem `ctx`). O check-in só sai no `GET` da própria atividade, nunca
em lista. O `GET` da atividade ganha ainda `carga_pse` (`carga_pse@1`, [[metricas/carga-pse]]): `null` em pai e troca, senão `versao`, `estado`
(`calculada`, `sem_checkin`, `sem_duracao`), `pse`, `minutos`, `valor` (UA, sem arredondar) e, pelo adendo 2, `valor_texto` ("270 UA", "272,5 UA") e `texto`
prontos. Não traz a observação nem a sensação. Detalhes em [[modulos/api]].

## Adendo 10 (2026-11-11): `feedback` no `GET` da atividade (#328)
**Status: aceito (Theo, [[decisoes/0013-feedback-automatico]], item 2).** `GET /atletas/{atleta_id}/atividades/{atividade_id}` ganha, sem remover campo,
`feedback`: `null` em `multiesporte_pai` e `troca` (o cartão não aparece), senão um objeto com `estado` (`pronto`, `sem_checkin`, `pendente`,
`desatualizado`, `indisponivel`) e, conforme o estado: `texto` (3 a 5 linhas) e `origem` (`automatico` ou `teste`, esta quando o texto veio do provedor falso)
só em `pronto`; `mensagem` (**frase pronta em português, escrita pela API**, que o app mostra como veio; pelo adendo 2) nos demais; `checkin_aberto` só em
`sem_checkin` (falso = prazo vencido, sem botão); `motivo` (código fechado: `texto_reprovado`, `provedor_erro`, `provedor_tempo_limite`,
`provedor_nao_configurado`, `limite_de_chamadas`) só em `indisponivel`, para quem cuida do app: o app **não** o mostra. As frases: `sem_checkin` com prazo aberto
"Faça o check-in para ver o feedback."; com prazo vencido "O prazo do check-in deste treino acabou, então ele fica sem feedback."; `pendente` "O feedback deste
treino ainda não foi gerado. Ele é preparado em lote; volte mais tarde."; `desatualizado` "Você editou o check-in. O feedback será refeito." quando o check-in mudou (sozinho ou junto com outro motivo), "O feedback será refeito." quando só a versão dos fatos mudou (#402; junto com outro motivo vale a frase do outro) e "Os dados da noite anterior foram atualizados. O feedback será refeito." só quando foi só a noite do treino que chegou ou mudou (#396; a mesma `mensagem`, sem estado novo e sem mudar o contrato); `indisponivel`
"Ainda não foi possível gerar o feedback deste treino. Uma nova tentativa será feita mais tarde." (a mesma para texto reprovado, provedor fora e limite de chamadas) e, só para
`provedor_nao_configurado`, "O feedback automático não está ligado neste app." A API **nunca** devolve o texto de um feedback desatualizado, o texto reprovado (que nem é
gravado), o provedor, o modelo nem as versões; só o `GET` da própria atividade traz o campo (nunca lista; outro atleta recebe `404`). Dado de saúde derivado do
check-in. Tipos no cliente: `FeedbackTreino` e `EstadoFeedback`. Detalhes em [[modulos/api]].

## Adendo 11 (2026-11-16): caixa do dia do professor e `PUT` do tipo em lote (#424, #425)
**Status: aceito (Theo, [[decisoes/0015-caixa-do-dia-do-professor]]).** Duas rotas novas, sem mudar nenhuma existente (a API formata, o app mostra; adendo 2). Ambas entram por `/professores/{professor_id}` e respondem `404` com `type` `professor_inexistente` (mesmo corpo para id sem linha, id diferente do configurado e `PROFESSOR_ID` vazio).
- **`GET /professores/{professor_id}/caixa-do-dia`** (`buscarCaixaDoDia`, `Cache-Control: no-store`): `versao` (`atencao@2`; o formato não muda, só o texto do motivo `checkin_vencendo`: uma linha por aluno, no treino mais antigo; adendo 1 da ADR 0015), `hoje` (`AAAA-MM-DD`, `America/Sao_Paulo`), `janela_atencao_dias` (7), `janela_novos_dias` (14), `alunos[]` (ordem da API: `atleta_id`, `nome`, `sem_motivo`, `texto_sem_motivo`, `treinos[]` só com motivo, do mais recente ao mais antigo, cada um com `atividade_id`, `modalidade`, `data_local`, `hora_local`, `duracao_texto`, `motivos[]` `{codigo, texto}` e `detalhe`) e `novos[]` (mais recente primeiro: os mesmos campos do treino mais `atleta_id`, `atleta_nome`, `tipo_sugerido`, `tipo_sugerido_texto`, `origem_texto`). `detalhe`: `tipo_texto` e `tipo_origem_texto` (nulos sem tipo), `tipo_confirmado`, `checkin` (`null` sem check-in; `pse_texto`, `sensacao`, `sensacao_texto`, `atalhos[]`, `nada_a_relatar`, `observacao`) e `feedback` (os estados do adendo 10). A `observacao` só existe em `detalhe.checkin.observacao`.
- **`PUT /professores/{professor_id}/tipos-de-treino`**: corpo lista de `{atividade_id, tipo_treino?}` (1 a 200); resposta `{confirmados, corrigidos}`; erros `404 atividade_nao_encontrada`, `422 atividade_sem_tipo` e `422` de validação.
Dado de saúde: nada em log, nada de modelo de linguagem, só o professor com vínculo e consentimento. Tipos no cliente: `CaixaDoDiaOut`, `TiposConfirmadosOut`. Detalhes em [[modulos/api]].

## Adendo 12 (2026-11-17): textos da carga, `forma_do_dia` e `transicao.editavel` no `GET` da atividade (#464)
**Status: aceito (Theo, 17/11, no PR #480).** Só campos novos e opcionais no `GET /atletas/{id}/atividades/{id}`; nenhum campo sai nem muda de tipo (a API formata, o app mostra; adendo 2). Base: a spec [[design/telas/treino]], seção "Meta 12".
- **`linha_base.metricas[].valor_texto`** já saía no `MetricaBaseOut` desde a `linha_base@2` (adendo 7); a spec pedia por engano. Nada muda.
- **`carga`** ganha `valor_texto` (1 casa, vírgula: "87,4"; só em `calculada`), `metodo_texto` ("Estimada pelo pace." para `rtss`, "Estimada pela FC." para `hrtss`) e `texto` (a frase do motivo em `sem_carga`, as seis da spec; "A carga deste treino ainda não foi calculada." em `pendente`; `null` em `calculada`). O número `carga` continua sem arredondar.
- **`forma_do_dia`** (novo, `null` só em `multiesporte_pai` e `troca`, como `carga`): CTL, ATL e TSB do **fim do dia local do treino**, pela mesma `calcular_serie` (`serie_carga@1`) do `GET /carga`, calculada na leitura (sem série inteira). Campos: `estado` (`calculada`, `aprendendo`, `sem_serie`), `data_local`, `ctl_texto`, `atl_texto`, `tsb_texto` (1 casa e vírgula; o TSB com sinal explícito, menos U+2212, "+3,2", "0,0"), `texto_aprendendo`, `sem_carga_no_dia` (inteiro) e `texto_sem_carga` (`null` se 0).
  - `aprendendo` (menos de 42 dias desde o primeiro dia da série): **os três textos não saem**; vem `texto_aprendendo` com os dias que faltam. Isto segue a recomendação da Lia e depende da pergunta 4 com o Angelo; se ele quiser mostrar, os textos passam a sair junto do `estado`.
  - `sem_serie`: o dia não está na série (nenhuma carga calculada até ali, ou a atividade do dia ainda está `pendente`).
  - `sem_carga_no_dia` e `texto_sem_carga` saem em `calculada` e em `aprendendo`.
- **`transicao.editavel`** (`true` para corrida, natação e ciclismo; `false` para `outra`, `multiesporte_pai` e `troca`): também na resposta do `PUT` e do `DELETE` da transição. Com `editavel = false`, o `PUT` e o `DELETE` da transição respondem **`409`** (`detail`: "Este treino não tem rótulo de transição.") e não gravam nada (decisão do Theo em 17/11).
Tipos no cliente: `FormaDoDiaOut`, `CargaAtividadeOut` e `TransicaoOut` com os campos novos.

## Adendo 13 (2026-11-18): lista de treinos do atleta, `GET /atletas/{atleta_id}/atividades` (#537)
Base da aba "Treinos" e da tela inicial nova ([[design/auditoria-ux-e-inicio-do-atleta]], "O que falta na API"). Só o atleta dono (`atleta_da_sessao`, [[decisoes/0016-login-e-deploy-do-piloto]], item 5): sem sessão `401`, atleta de outro o mesmo `404` de inexistente.
1. **Rota e ordem.** `GET /atletas/{atleta_id}/atividades`, do mais recente para o mais antigo, por `(inicio, id)` decrescente. Parâmetros: `limite` (1 a 100, padrão 20), `antes_de` (cursor), `modalidade` (uma das conhecidas) e `checkin_pendente` (booleano). Valor inválido é `422`.
2. **Cursor.** A resposta traz `proximo`; passe-o em `antes_de` para a página seguinte. `null` quer dizer que acabou. O cursor é `"<início UTC ISO>~<id>"` e traz só o que vem **depois** dele na ordem, sem pular nem repetir treino mesmo que entre uma atividade nova no topo. Cursor mal formado dá `422` com `type` `cursor_invalido`.
3. **Item enxuto.** `atividade_id`, `inicio` (UTC), `data_local` e `hora_local` (pelo fuso da atividade), `modalidade`, `subtipo`, `tipo_treino`, `duracao_s` e `duracao` (`h:mm:ss`), `distancia_m` e `distancia` (texto pronto), `destaque` (frase pronta: "Pace médio m:ss /km" na corrida, "Velocidade média x,x km/h" no ciclismo; `null` nas demais), `checkin_estado` e `feedback_estado`. **Nada de texto de check-in nem de feedback, clima, esforços, carga ou linha de base** (dado de saúde fica no `GET` da atividade).
4. **`checkin_estado`:** `feito`, `pendente` (sem check-in e dentro do prazo da ADR 0012), `vencido` (sem check-in e fora do prazo) e `nao_se_aplica` (`multiesporte_pai` e `troca`). `checkin_pendente=true` filtra os `pendente`.
5. **`feedback_estado`:** o estado do cartão da ADR 0013 sem o texto: `pronto`, `sem_checkin`, `pendente`, `desatualizado`, `indisponivel`; `null` em `multiesporte_pai` e `troca`.
6. **Ressalva: a noite e o clima ficam fora do `feedback_estado` da lista.** A lista compara só o que a página já tem (check-in, versão, tipo e transição, motivos da ADR 0013). A recuperação da noite e o clima pedem outras consultas e não entram, para a lista continuar numa consulta só. Por isso um treino pode aparecer `pronto` na lista e `desatualizado` no detalhe. O detalhe (`GET` da atividade) é a fonte completa.
7. **`normal_estado` (#551):** o selo "normal" do treino, `fora`, `dentro`, `aprendendo` ou `null`, de [[metricas/normal-treino]] (`normal_treino@1`, decisão do Caio) sobre a `linha_base@3` do mesmo treino: a mesma que o `GET` da atividade devolve por métrica. `null` em `sem_linha_base` e quando todas as métricas são `sem_valor`. É só o estado: nenhum número nem texto de linha de base sai na lista. Continua uma consulta de histórico por página (`linha_base_resultados`), sem N+1.
7. **Custo.** Uma consulta por página (`LIMIT + 1`, para saber se há mais) com check-in, feedback e rótulo de transição por junção: sem N+1.

## Adendo 14 (2026-11-27): `clima.recente` e textos do clima em inteiro (#569)
1. **`recente`** (`bool`, em todo estado do `clima`): `true` quando o fim do treino tem menos de 7 dias, a regra do preenchimento ([[decisoes/0007-clima-da-atividade]]). O app mostra `pendente` recente como espera ("o clima chega em até 7 dias"), não como erro.
2. **Textos prontos** em `ok`: `temperatura_texto` ("24 °C"), `sensacao_texto`, `umidade_texto` ("61 %") e `vento_texto` ("8 km/h"). Inteiro, meio para longe do zero, sem "-0". Ausentes quando o valor é `null`. Os decimais continuam. O app não arredonda (o e2e proíbe `Math.` na TelaTreino).

## Adendo 15 (2026-11-27): catálogo de séries da Evolução, `GET /atletas/{atleta_id}/evolucao/series` (#573)
1. **Rota nova**, ao lado de `/evolucao/tiros-1km` (que continua). Devolve `series[]` (`id`, `titulo`, `descricao`, `modalidade`, `grupo`, `n_pontos`, `disponivel`, `motivo`) e `serie_padrao`. Detalhes em [[modulos/api]].
2. **Só as séries do atleta**, por modalidade, grupo e ordem do catálogo; indisponível aparece com o motivo escrito ("Poucos treinos leves de corrida nas últimas 12 semanas").
3. **Regra de disponível** (Caio, [[metricas/evolucao-series]]): 8 pontos em 12 semanas ou 3 (2 nos tiros) em cada janela de 28 dias; volume 3 semanas; condicionamento 8 dias.
4. **Ids estáveis**: o app guarda o último escolhido. Série nova entra sem mudar as antigas.
5. **Série, `GET /atletas/{atleta_id}/evolucao/series/{serie_id}?periodo=12s|6m|1a` (#574).** `pontos` com `atividade_id` (null no volume e no condicionamento), texto pronto e `rotulo` de leitor de tela; `eixo`; `referencia` (faixa do normal: mediana ± 2,5 desvios da `linha_base@3`, só com 8 pontos); `frase` da `frase_evolucao@1` (igual em todo período). O app não calcula nada.
6. **Cartões do início, `GET /atletas/{atleta_id}/inicio/cartoes` (#575).** Cinco cartões em texto pronto (`esta_semana`, `hoje_na_semana`, `volume_4_semanas`, `em_movimento`, `melhor_marca`); só vêm os que têm dado. Cada um traz `destino` (série da Evolução, semana-padrão ou treino). Regras em [[modulos/api]].
7. **`altura_pct` nas barras do volume (#586):** cada barra do `volume_4_semanas` traz `altura_pct` (0 a 100, relativo à maior das 4, meio para cima; 0 em todas sem volume). O app não calcula a altura.

## Adendo 16 (2026-11-28): conversas do chat, `/atletas/{atleta_id}/conversas` (#598)
**Status: proposto (Duda), conforme a [[decisoes/0017-chat-do-atleta]], itens 7 e 8.** Rotas novas, nenhuma muda. Todas só do atleta dono: `401` sem sessão, `404` uniforme para atleta de outro, professor (mesmo com vínculo e consentimento) e inexistente, e o mesmo `404` para conversa de outro ou inexistente. A API formata, o app mostra (adendo 2). Síncronas, sem streaming. O `422` não repete o que foi enviado e o `500` tem texto fixo; pergunta, resposta e resultado de ferramenta não vão a log.
- **`POST /atletas/{id}/conversas`** (`criarConversa`): corpo `{pergunta}` (1 a 1000 caracteres, aparada). Abre a conversa (título = a pergunta cortada em 80, sem passar pelo provedor) e **responde a primeira pergunta**. `201` com `ConversaOut`.
- **`POST /atletas/{id}/conversas/{conversa_id}/mensagens`** (`enviarMensagem`): mesmo corpo; continua a conversa. `200` com `MensagemOut`. O provedor recebe as últimas 6 trocas **aprovadas** da conversa.
- **`GET /atletas/{id}/conversas`** (`listarConversas`, `limite` 1 a 100, padrão 50): `{atleta_id, conversas[]}` com `id`, `titulo`, `criada_em`, `atualizada_em`, da mais recente para a mais antiga.
- **`GET /atletas/{id}/conversas/{conversa_id}`** (`buscarConversa`): a conversa com `mensagens[]`.
- **`DELETE /atletas/{id}/conversas/{conversa_id}`** (`apagarConversa`): `204`; apaga as mensagens junto.
- **`MensagemOut`**: `id`, `ordem`, `pergunta`, `estado` (`respondida`, `recusada`, `reprovada`, `erro`), `motivo` (código; só fora de `respondida`), `texto` (o que o app mostra: a resposta aprovada, o texto fixo da recusa ou a frase fixa "Não consegui responder agora. Tente de novo em instantes."), `links[]` e `criada_em` (`America/Sao_Paulo`). **Texto reprovado nunca é gravado nem devolvido.** Falha do provedor ainda é `201`/`200` com `estado = erro`: a pergunta fica guardada e o atleta pode repetir.
- **`links[]`**: `{tipo: "treino" | "evolucao", rotulo: "Abrir treino" | "Abrir na Evolução", atividade_id | serie_id, data_texto}` (`data_texto` só no treino, como veio da ferramenta, para o app distinguir links do mesmo tipo), montados **pelo código** a partir dos ids que apareceram nos resultados das ferramentas daquela pergunta (treino: só quando o texto cita a data dele; Evolução: o `serie_id` de um resultado usado), no máximo 5, só em `respondida`. O modelo não escreve link.
- **`429`** com `{detail, espere_texto, espere_s}` e `Retry-After` quando o atleta já fez **20 perguntas na última hora** (conta as linhas de `mensagem`; ADR 0017, "A confirmar" 5). `detail`: "Você fez 20 perguntas na última hora."; `espere_texto`: frase pronta em minutos para cima ("Você pode perguntar de novo em 12 min."); o app não converte `espere_s`. Não chega ao provedor.
- **Recusa sem professor:** `pedido_de_mudanca` de atleta **sem vínculo com professor** traz só a primeira frase ("Mudar o treino é com o seu professor."); com vínculo, as duas. A API decide ao gravar.
- **Desconexão:** a rota é síncrona e roda em thread; se o cliente desconectar (ou a requisição for cancelada) no meio, a thread termina e a mensagem é gravada; ela aparece no `GET` da conversa. Teste em `test_chat_desconexao.py`.

## Adendo 17 (2026-11-28): perguntas prontas e 👍/👎 nas respostas do chat (Angelo, 28/11)
**Status: proposto (Duda).** Duas mudanças pequenas no chat do adendo 16; nenhuma rota existente muda de formato além de um campo novo. Acesso igual ao do adendo 16: `401` sem sessão e `404` uniforme para atleta de outro, professor e inexistente.
- **`GET /atletas/{id}/chat/perguntas-prontas`** (`listarPerguntasProntas`): `{versao: "perguntas_prontas@2", atleta_id, perguntas: [string]}`, de **3 a 6** frases; o Início mostra as 3 primeiras. Os **textos são fixos no código**; a API escolhe pelo que o atleta tem, só por contagem, e a **ordem é estável** (a do catálogo, sem aleatório). As regras olham os rolantes de `comparar_periodos`, que **terminam ontem**: (1) último treino (algum treino em 8 semanas); (2) "últimos 7 dias comparados com os 7 anteriores" (1 corrida em cada período, contando até ontem); (3) pace dos leves "no último mês" (3 corridas leves nos 28 dias até ontem e 3 nos 28 anteriores); (4) forma de hoje (alguma carga calculada); (5) tiros "no último mês" (2 sessões em cada janela de 28 dias); (6) check-in de ontem; (7) sono (noite importada nos últimos 7 dias); (8) natação (3 treinos em 12 semanas); (9) ciclismo (algum treino em 8 semanas); (10) corrida mais longa "este ano" (a dica usa `de` = 01/01 e `ate` = hoje, não `ultimo_ano`); (11) "Em quais treinos eu me senti mal?" (algum check-in com sensação "mal" em 12 semanas). Quem não tem dado para 3 recebe frases de apoio ("Quais foram os meus últimos treinos?", entre outras), nunca uma lista vazia: a ferramenta responde `sem_dados` com o motivo. No catálogo cada frase leva a dica de argumentos das ferramentas (testada contra o esquema). O app envia a frase como pergunta comum (`POST` do adendo 16).
- **`PUT /atletas/{id}/conversas/{conversa_id}/mensagens/{mensagem_id}/avaliacao`** (`avaliarMensagem`): corpo `{valor: 1 | -1 | null}` (`1` é 👍, `-1` é 👎, `null` desfaz; `true`, outro número e campo extra dão `422`, sem texto livre). `200` com a `MensagemOut`, que ganha **`avaliacao`** (`1`, `-1` ou `null`). Só mensagem `respondida` (as outras dão `409`); mensagem ou conversa de outro, ou inexistente, dão o mesmo `404`. Migração 0020: `mensagem.avaliacao` e `avaliada_em` (CHECKs: valor `-1` ou `1`, as duas colunas juntas, só em `respondida`). A avaliação **não vai ao provedor** e some com a conversa e com a conta (cascata da 0019).

## Adendo 18 (2026-11-28): campos do Início v5, `esta_semana` e pendentes do check-in
**Status: proposto (Duda), a pedido do Theo para o Início v5 (Meta 15).** Só campos novos; nenhum campo existente muda de tipo ou de texto. O app não calcula nem concorda texto: tudo vem pronto.
- **`GET /atletas/{id}/inicio/cartoes`, cartão `esta_semana`:**
  - **`dias[]`**: sempre 7 itens, de segunda a domingo da semana em curso (data local). Cada um `{rotulo, estado, modalidades[], rotulo_acessivel}`. `rotulo`: `seg`, `ter`, `qua`, `qui`, `sex`, `sáb`, `dom`. `estado`: `hoje` (o dia de hoje, com ou sem treino, com as `modalidades[]` preenchidas se houve treino), `feito` (dia passado com treino), `vazio` (dia passado sem treino) ou `futuro` (o dia ainda não chegou; o app não compara datas). `modalidades`: as do dia, sem repetir (`corrida`, `natacao`, `ciclismo`, `outra`). `rotulo_acessivel` já concordado: "segunda, corrida e natação feitas", "terça, corrida e ciclismo feitos" (feminino só se todas forem femininas), "quarta, sem treino", "hoje, sem treino ainda" (`quinta, hoje, sem treino ainda`), "sexta, ainda por vir".
  - **`apoio_curto`** ("3 treinos · 2 h 37 min") e **`comparacao_texto`** ("semana passada: 4" ou "sem semana anterior"): o `apoio` antigo ("2 h 37 min · semana passada: 4") **continua igual**, por compatibilidade.
  - Os outros quatro cartões trazem `dias = []` e os dois textos `null`.
- **`GET /atletas/{id}/checkins/pendentes`, `PendenteOut.pergunta_texto`**: a pergunta pronta com a data relativa. Hoje e ontem por extenso ("Como foi a natação de ontem?"); de 2 a 6 dias atrás, o dia da semana ("Como foi a corrida de terça?"); antes disso, "do dia 08/03" (o dia da semana já se repetiu). Artigo e nome pela modalidade: "a corrida", "a natação", "o ciclismo", "o treino" (`outra`).

## Adendo 19 (2026-11-28): limite do provedor no chat, `provedor_limite` (#636)
**Status: proposto (Duda).** Nenhuma rota nem campo muda. Muda só o que acontece quando o Groq recusa por limite de requisições ou de tokens por minuto (HTTP 429).
- **Espera curta e uma repetição.** O laço espera `retry-after` do provedor (se vier como número) ou **5 s** e repete a chamada **uma vez** por pergunta (conta no teto de 8 chamadas ao provedor, [[decisoes/0017-chat-do-atleta]], item 3). Se o `retry-after` passar de **15 s**, ou se não sobrar tempo dos 45 s da pergunta, desiste sem esperar. Nada do corpo da resposta do provedor é lido ou guardado.
- **`MensagemOut` com `estado = "erro"` e `motivo = "provedor_limite"`** quando o limite persiste. O código é novo e só vale no chat (no feedback segue `limite_de_chamadas`). A coluna `mensagem.motivo` já aceita (texto de até 40, sem lista no `CHECK`).
- **`texto`** nesse caso é a frase fixa **"O serviço de IA está ocupado. Tente de novo em 1 minuto."**; os outros erros seguem com "Não consegui responder agora. Tente de novo em instantes.". O app mostra o `texto` como veio e não interpreta o `motivo`.
- Não é o `429` do limite de 20 perguntas por hora (adendo 16): aquele é status HTTP `429` da nossa rota, com `espere_texto`; este é uma resposta `200` com a mensagem em erro.
