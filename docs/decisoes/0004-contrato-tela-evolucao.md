---
tipo: decisao
status: em-uso
dono: theo
atualizado: 2026-11-09
links: [[modulos/api]], [[modulos/grafico-tiros]], [[modulos/mobile]], [[modulos/worker]], [[metricas/tiros-1km]], [[decisoes/0002-segmento-intensidade-e-versao]], [[decisoes/0003-fuso-da-atividade]], [[decisoes/0005-serie-de-tiros-o-que-entra]], [[decisoes/0006-upload-de-fit]], [[decisoes/0007-clima-da-atividade]], [[produto/roadmap]], [[design/telas/treino]], [[decisoes/0009-treino-de-transicao]]
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
