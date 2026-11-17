---
tipo: roteiro
status: em-uso
dono: paulo
atualizado: 2026-11-17
links: [[produto/plano-mvp-execucao]], [[produto/metas/meta-12-treino-inteiro]], [[produto/meta-12-como-rodar]], [[design/telas/treino]], [[produto/metas/meta-11-caixa-do-dia]], [[produto/meta-11-como-rodar]], [[decisoes/0015-caixa-do-dia-do-professor]], [[metricas/atencao]], [[design/telas/caixa-do-dia]], [[design/telas/conferencia-369]], [[produto/metas/meta-10-recuperacao]], [[produto/meta-10-como-rodar]], [[decisoes/0014-recuperacao-diaria]], [[metricas/recuperacao]], [[diario/2026-11-12]], [[diario/2026-11-13]], [[diario/2026-11-16]], [[produto/metas/meta-9-feedback-automatico]], [[produto/meta-9-como-rodar]], [[decisoes/0013-feedback-automatico]], [[diario/2026-11-11]], [[decisoes/0001-modelo-de-dados-minimo]], [[decisoes/0005-serie-de-tiros-o-que-entra]], [[produto/metas/meta-1-tiros-1km]], [[produto/metas/meta-2-evolucao-tiros-app]], [[produto/metas/meta-3-upload-fit]], [[decisoes/0004-contrato-tela-evolucao]], [[decisoes/0006-upload-de-fit]], [[decisoes/0003-fuso-da-atividade]], [[diario/2026-11-03]], [[00-inicio]], [[produto/metas/meta-4-clima-atividade]], [[decisoes/0007-clima-da-atividade]], [[produto/meta-4-como-rodar]], [[metricas/tiros-1km]], [[decisoes/0008-deteccao-de-esforcos]], [[diario/2026-11-04]], [[produto/metas/meta-5-deteccao-esforcos]], [[produto/meta-5-como-rodar]], [[decisoes/0009-treino-de-transicao]], [[metricas/esforcos]], [[metricas/transicao]], [[modulos/ingestao-garmin]], [[diario/2026-11-06]], [[produto/metas/meta-6-carga-treino]], [[produto/meta-6-como-rodar]], [[decisoes/0010-carga-de-treino]], [[metricas/carga-treino]], [[metricas/serie-carga]], [[metricas/conferencia-carga]], [[diario/2026-11-07]], [[diario/2026-11-08]], [[diario/2026-11-09]], [[produto/metas/meta-7-linha-de-base-semana-padrao]], [[produto/meta-7-como-rodar]], [[decisoes/0011-linha-de-base-e-semana-padrao]], [[metricas/linha-base]], [[metricas/tipo-treino]], [[design/tokens]], [[produto/metas/meta-8-check-in]], [[produto/meta-8-como-rodar]], [[decisoes/0012-check-in-pos-treino]], [[metricas/carga-pse]], [[design/telas/checkin]], [[diario/2026-11-10]]
---
# Roteiro de metas

Metas em ordem, cada uma com no máximo 1 semana de trabalho. Só se trabalha em issues da **meta atual**.
Ao fechar uma meta, o Paulo registra o resultado em `docs/produto/metas/` e revisa este roteiro.

| Meta | Tema | Situação |
|---|---|---|
| 0 | Fundação: monorepo, modelo mínimo, CI, base de docs | feita (#1, #3) |
| 1 | Tiros de 1 km a partir da exportação Garmin | feita (fixtures e dado real; [[produto/metas/meta-1-tiros-1km]]) |
| 2 | Evolução dos tiros no app | feita (web com fixtures; [[produto/metas/meta-2-evolucao-tiros-app]]) |
| 3 | Upload de arquivo FIT | feita (web com FIT sintéticos; [[produto/metas/meta-3-upload-fit]]) |
| 4 | Clima de cada atividade | feita (fixtures e resposta gravada, sem rede; [[produto/metas/meta-4-clima-atividade]]) |
| 5 | Detecção de esforços (corrida por distância, ciclismo por duração) e série de tiros com o melhor tiro | feita (fixtures, sem rede; conferência local com o histórico real; [[produto/metas/meta-5-deteccao-esforcos]]) |
| 6 | Carga de treino (rTSS, hrTSS, CTL, ATL, TSB) | feita (fixtures, sem rede; conferência local com o histórico real; [[produto/metas/meta-6-carga-treino]]) |
| 7 | Linha de base pessoal e semana-padrão (tipo de treino pelo plano, regra como reserva) | feita (fixtures, sem rede; conferência local com o histórico real; [[produto/metas/meta-7-linha-de-base-semana-padrao]]) |
| 8 | Check-in pós-treino e carga pela PSE | feita (fixtures, sem rede; celular não verificado; [[produto/metas/meta-8-check-in]]) |
| 9 | Feedback automático por treino | feita (fixtures e provedor falso; tela rodando, celular e revisão da Lia na tela não verificados; [[produto/metas/meta-9-feedback-automatico]]) |
| 10 | Sono, VFC e FC de repouso no contexto do treino | feita (fixtures, sem rede; conferência visual no Chrome em 390 px sem bloqueantes; celular de verdade não verificado; [[produto/metas/meta-10-recuperacao]]) |
| 11 | Caixa do dia do professor (piloto local, sem login, atletas sintéticos) | feita (fixtures, sem rede; design-ok da Lia na tela rodando; celular, leitor de tela, login e aluno real não verificados; [[produto/metas/meta-11-caixa-do-dia]]) |
| 12 | O treino inteiro na tela do atleta (linha de base, carga, esforços) | feita (fixtures, sem rede; tela viva contra a API e design-ok da Lia; celular, leitor de tela, login e aluno real não verificados; [[produto/metas/meta-12-treino-inteiro]]) |
| **13** | **Login e deploy do piloto** | **em curso** ("ok para as nove" em 17/11, a pergunta 6 em aberto; issues #496 a #510 e #472) |
| 14 | Agente do atleta (primeiras perguntas) | depois da Meta 13 (decisão 6 da Meta 12; era a Meta 12) |

Numeração: em 03/11 a linha de base virou meta própria e as metas seguintes andaram um número. Em 04/11 (decisão do
Angelo) a detecção de esforços entrou como Meta 5, antes da carga, e as seguintes andaram mais um número: carga = 6,
linha de base = 7, check-in = 8, feedback = 9, caixa do professor = 10, agente = 11. Notas antigas que citam "Meta 5"
para a carga falam da atual Meta 6; "Meta 8" para o feedback com LLM, da atual Meta 9. Em 12/11 (decisão do Angelo) a recuperação
(sono, VFC e FC de repouso) entrou como Meta 10, a caixa do professor virou 11 e o agente virou 12. Notas até a Meta 9 que citam
"Meta 10" para o professor e "Meta 11" para o agente falam das atuais Metas 11 e 12. Em 17/11 (decisões 5 e 6 do Angelo na Meta 12)
login e deploy viraram a Meta 13 e o agente a Meta 14; notas até a Meta 11 que citam "Meta 12" para o agente falam da atual Meta 14.

---

## Meta 1: tiros de 1 km a partir da exportação Garmin (feita)

### Objetivo
Provar o caminho completo do dado: exportação da Garmin, banco, métrica determinística, gráfico e API.
Definida pelo Angelo: ler a exportação em `dados-teste/garmin/`, guardar as atividades no Postgres local e
mostrar a evolução dos tiros de 1 km dos intervalados de corrida (pace e FC médios por sessão).

### Entrega visível
- `entregas/meta-1/tiros-1km-atleta-<id>.png`: dois painéis com o mesmo eixo X (data do treino, `dd/mm/aa`).
  Em cima, "Pace médio dos tiros (min/km)", eixo invertido (mais rápido para cima); embaixo,
  "FC média dos tiros (bpm)". Um ponto por sessão. Junto vai um `.csv` com a mesma série.
- `GET /atletas/{atleta_id}/evolucao/tiros-1km` (JSON) e `GET /atletas/{atleta_id}/evolucao/tiros-1km.png`.
  O formato exato está em #15 (gráfico) e #16 (JSON).
- `entregas/` e `dados-teste/` ficam fora do git: o gráfico com dado real é dado pessoal.

### Critério de pronto
Cumprido com as fixtures (QA da Bia, #18 / PR #45) e com o dado real (#19). Resultado completo em
[[produto/metas/meta-1-tiros-1km]].
- [x] Com as fixtures sintéticas (`tests/fixtures/garmin/`), num clone limpo e seguindo só a documentação:
      importar, gerar o PNG e o CSV e chamar os dois endpoints (Bia, #18).
- [x] Pace e FC de cada sessão batem com o cálculo à mão a partir da tabela das fixtures.
      Pace da sessão = soma das durações dos tiros / soma das distâncias x 1000; FC = média ponderada pela duração.
- [x] Reimportar a mesma exportação não duplica atividades nem segmentos.
- [x] Rodagem leve com auto-lap de 1 km, natação e intervalado sem arquivo FIT ficam fora da série.
- [x] Check `testes` verde (SQLite local e Postgres no CI) e "docs ok" da Nina em todos os PRs.
- [x] Notas: [[modulos/ingestao-garmin]], [[metricas/tiros-1km]], ADR 0002 e o passo a passo de reprodução.
- [x] **Com dado real (#19):** a exportação do Angelo importada no Postgres local, PNG gerado e a série conferida
      pelo atleta. Ficou de acordo com a conferência depois da evolução da regra até a `tiros_1km@4` (#48, #51, #53,
      #58). O gabarito fica só no relatório privado em `entregas/meta-1/`, fora do git.

### Issues e ordem
| # | Issue | Dono | Depende de | Situação |
|---|---|---|---|---|
| #8 | Formato da exportação Garmin e fixtures sintéticas | duda-dados | (#1, feita) | feita |
| #9 | ADR 0002: intensidade da volta e versão do cálculo no `segmento` | duda-dados (aprovação do Theo) | (#1, feita) | feita |
| #10 | Parser da exportação Garmin (JSON e FIT) | duda-dados | #8 | feita |
| #11 | Detecção dos tiros de 1 km numa corrida | caio-ciencia | (#1, feita) | feita |
| #12 | Agregação por sessão (pace e FC médios) | caio-ciencia | #11 | feita |
| #29 | `versao_deteccao` (`tiros_1km@1`) em `SessaoTiros`/`PontoSessao` | caio-ciencia | (#12, feita) | feita |
| #30 | Oráculo das fixtures: pace e FC por sessão calculados à mão | caio-ciencia | (#8, #12, feitas) | feita |
| #13 | Importar no banco (idempotente) | duda-dados | #9, #10 | feita |
| #14 | Classificar tiros no banco e montar a série (data local da sessão, ADR do fuso) | duda-dados | #12, #13, #29 (referência: #30) | feita (ADR 0003) |
| #39 | Desenho do gráfico com dados fixos (`render_png`, `linhas_csv`, `formatar_pace`) | caio-ciencia | (#29, #30, feitas) | feita |
| #15 | Comando que grava o gráfico e o CSV em `entregas/` | caio-ciencia (antes duda-dados) | #14, #39 | feita |
| #16 | Endpoint da API (JSON e PNG), com o serviço `sessoes_tiros_1km` | duda-dados | #14, #39 | feita |
| #17 | Documentação da Meta 1 e diário do ciclo | nina-docs | #16 | feita |
| #18 | QA de ponta a ponta com fixtures | bia-qa | #16, #17 (oráculo #30) | feita: critério de pronto ok com fixtures |
| #43 | Resultado da meta em `docs/produto/metas/` e roteiro (fixtures) | paulo-planejador | #18 | feita |
| #48 | Regra `tiros_1km@2`: separação por recuperação e bloco principal | caio-ciencia | #19 (achado no dado real) | feita |
| #51 | Esteira fora da série | duda-dados | #19 (decisão do Angelo) | feita |
| #53 | Regra `tiros_1km@3`: ritmo habitual do atleta | caio-ciencia | #48 | feita |
| #58 | Regra `tiros_1km@4`: progressivo e fartlek de 1 km não são tiros | caio-ciencia | #53 | feita |
| #19 | Validar com a exportação real e o Postgres local | duda-dados (com bia-qa) | #18, #58 e itens do Angelo | feita |
| #60 | Resultado com o dado real, roteiro e meta feita | paulo-planejador | #19 | esta |

Caminhos paralelos: a Duda começa por #8 e #9; o Caio faz #11 e #12 ao mesmo tempo, com voltas montadas à mão.
Os dois se encontram em #14. Depois de #12, o Caio faz #29 e #30, que servem de referência para #14 e #18.
Enquanto a Duda faz a #14, o Caio desenha o gráfico com dados fixos (#39). `formatar_pace` é a regra única de `m:ss`
(ao segundo, meio para cima) para o CSV da #15 e o JSON da #16.
Manutenção do roteiro (paulo-planejador): #27, #36 e #43 (feitas), #60.
Com o dado real, a regra evoluiu em quatro versões (#48, #53, #58) e a esteira saiu da série (#51); ver
[[metricas/tiros-1km]] e [[decisoes/0005-serie-de-tiros-o-que-entra]].
Resultado da meta: [[produto/metas/meta-1-tiros-1km]].

### Quem participa
- **duda-dados:** ingestão, banco, gráfico e API.
- **caio-ciencia:** regra dos tiros de 1 km e agregação por sessão, com testes calculados à mão.
- **nina-docs:** revisa as notas a cada PR ("docs ok"), fecha a documentação e escreve o diário (#17).
- **bia-qa:** entra em #18 para conferir o critério de pronto de ponta a ponta, e repete com o dado real em #19.
- **Theo:** aprova a ADR 0002 (#9) e faz os merges.
- **rafa-app:** não participa da Meta 1; entra na Meta 2.

### Fora desta meta
Tela no app; upload de FIT pela API; outras distâncias de tiro (400 m, 2 km) e outras modalidades;
clima, sono, check-in; tipo de treino confirmado pelo professor (o tipo `intervalado` entra só como sugestão
automática); séries por segundo em Parquet; webhook da Garmin; login e várias assessorias.

---

## Metas seguintes (esboço)

Revisadas ao fim de cada meta com o que se aprendeu. Ordem tirada da "Fundação de dados" do
[[produto/plano-mvp-execucao]] (seção 9), começando pelo que já dá para mostrar.

### Meta 2: evolução dos tiros no app (feita)
- **Objetivo:** o atleta vê no app (web, iOS e Android) a evolução dos tiros de 1 km da Meta 1, sem o app formatar
  pace nem escolher a escala dos eixos por conta própria.
- **Entrega visível:** tela "Evolução dos tiros de 1 km" no Expo, com os dados do endpoint da Meta 1, rodando local
  na web e no Expo Go.
- **Critério de pronto:**
  - na web, com as fixtures e seguindo só a documentação, a tela mostra a evolução com os valores da API;
  - estados carregando, vazio e erro cobertos no `npm test` e conferidos à mão;
  - o app não tem nenhuma função de pace: todo `m:ss` vem pronto da API (`formatar_pace`);
  - escala mínima nos eixos (5 bpm na FC; 30 s/km no pace para começar), a mesma no PNG e no app;
  - cliente TypeScript em `packages/api-client/` gerado do OpenAPI, com teste que pega cliente desatualizado;
  - o OpenAPI declara o que o endpoint devolve (404 incluído);
  - iOS e Android abertos no Expo Go, ou registrados como não verificados.
- **Decisões já tomadas (03/11):** sem deploy; atleta fixo por `EXPO_PUBLIC_ATLETA_ID` até a meta de login; stack
  Expo; a API devolve todo pace em `m:ss`; `versao_calculo` é a versão da regra, com o campo
  `reclassificacao_pendente` (a API não reclassifica na leitura). O contrato é formalizado na ADR 0004, aprovada
  no PR dela. Ver [[diario/2026-11-03]].
- **Resultado:** feita. Na web, com as fixtures, a tela mostra a evolução com os valores da API (QA da Bia, #72 /
  PR #85). Não verificados: iOS e Android (sem simulador) e os estados carregando e vazio na tela (só pelo
  `npm test`). Resultado completo em [[produto/metas/meta-2-evolucao-tiros-app]].
- **Issues e ordem:**

  | # | Issue | Dono | Situação |
  |---|---|---|---|
  | #62 | ADR 0004, contrato da tela | duda-dados (aprovação do Theo) | feita |
  | #63 | Escala mínima dos eixos, regra única também no PNG | caio-ciencia | feita |
  | #64 | Endpoint de acordo com o contrato e `worker.reclassificar` | duda-dados | feita |
  | #65 | CORS por `CORS_ORIGENS` | duda-dados | feita |
  | #66 | Bloco `eixos` no JSON | duda-dados | feita |
  | #67 | Expo Router, tela vazia e configuração | rafa-app | feita |
  | #68 | Cliente gerado do OpenAPI e exemplo de contrato | duda-dados | feita |
  | #69 | Gráfico de dois painéis | rafa-app | feita |
  | #70 | Tela ligada à API com os estados | rafa-app | feita |
  | #71 | Documentação e passo a passo de API e app | nina-docs | feita |
  | #72 | QA de ponta a ponta com fixtures | bia-qa | feita |
  | #73 | Resultado da meta e roteiro | paulo-planejador | esta |

- **Melhorias abertas depois da meta:** nenhuma. A #86 (aviso do `react-native-svg` na web) foi feita no PR #90 e a
  #87 (eixo de pace com poucas marcas) no PR #89.
- **Aprendido na Meta 2:** contrato antes do código (ADR 0004) evitou retrabalho; o teste com texto trocado (`9:99`)
  prova que o app não recalcula; ver a tela é uma etapa própria do QA; estados difíceis de provocar à mão precisam
  de um jeito documentado de forçar.
- **Quem:** rafa-app, duda-dados, caio-ciencia, nina-docs, bia-qa.
- **Fora:** login e lista de atletas; outras métricas; edição de dados; filtro de período na tela; deploy, EAS,
  lojas e conta Expo; dado real em prints, testes ou PRs.

### Meta 3: upload de arquivo FIT (feita)
- **Objetivo:** plano B enquanto a API da Garmin não é aprovada: o atleta envia um `.fit` pelo app, e a atividade
  entra no banco e, se for um treino de tiros, na série da Meta 2.
- **Entrega visível:** `POST /atletas/{atleta_id}/atividades/fit` na API e o botão "Enviar arquivo FIT" no app; a
  atividade aparece na série.
- **Critério de pronto:**
  - reaproveita o leitor FIT da Meta 1;
  - reenviar o mesmo arquivo não duplica, e a mesma atividade vinda do upload e da exportação também não;
  - arquivo inválido, que não é atividade ou grande demais dá erro claro, declarado no OpenAPI;
  - cliente regerado e botão com os estados enviando, sucesso e erro no `npm test`;
  - QA na web com FIT sintéticos, com um jeito documentado de forçar cada estado.
- **Decisões (Angelo e Theo, 03/11):** guardar o FIT localmente em `FIT_DIR`; sem login, só local; 10 MB; qualquer
  modalidade, só corrida na série; regra dos 60 s nos dois caminhos; leitor dentro da API. Tudo na
  [[decisoes/0006-upload-de-fit]].
- **Resultado:** feita. Na web, com FIT sintéticos, o envio pelo botão grava a atividade sem duplicar e o treino de
  tiros aparece na série (QA da Bia, #98 / PR #107). Não verificados: iOS e Android (sem aparelho) e, na tela, o
  `404` e a falta de rede (só nos testes). Passo a passo em [[produto/meta-3-como-rodar]]; resultado completo em
  [[produto/metas/meta-3-upload-fit]].
- **Issues e ordem:**

  | # | Issue | Dono | Situação |
  |---|---|---|---|
  | #91 | ADR 0006, upload de FIT | duda-dados (aprovação do Theo) | feita |
  | #92 | Leitor FIT num lugar que a API e o worker usam | duda-dados | feita |
  | #93 | FIT sintéticos para o upload | caio-ciencia | feita |
  | #94 | `importar_fit`, idempotente, regra dos 60 s e `apagar_fit` | duda-dados | feita |
  | #95 | Endpoint de upload e cliente regerado | duda-dados | feita |
  | #96 | Botão "Enviar arquivo FIT" no app | rafa-app | feita |
  | #97 | Documentação e diário | nina-docs | feita |
  | #98 | QA de ponta a ponta com FIT sintéticos | bia-qa | feita |
  | #99 | Resultado da meta e roteiro | paulo-planejador | esta |

- **Achados depois da meta (propostas, sem issue criada):** app web declara `lang="en"` e o Chrome traduz as
  mensagens (proposta: `pt-BR`, issue pequena do Rafa); o servidor grava o upload inteiro num temporário antes do
  limite de 10 MB (aceito local; limitar no proxy na meta de deploy); docs-ok aplicado antes do CI travou dois PRs
  (regra decidida pelo Theo em 03/11); a série de tiros com o histórico real pode estar incompleta (proposta de investigação, ordem com o Angelo). Detalhes em [[produto/metas/meta-3-upload-fit]].
- **Aprendido na Meta 3:** conferir o código antes da ADR achou o ciclo API-worker e a duplicação entre fontes; a
  identidade da atividade é regra única para toda fonte nova; o FIT do upload não traz horário local nem posição
  guardada; o navegador (tradutor, seletor de arquivo) também é parte do QA.
- **Quem:** duda-dados, caio-ciencia, rafa-app, nina-docs, bia-qa.
- **Fora:** GPX/TCX, webhook e API da Garmin, storage em nuvem, vários arquivos de uma vez, login, deploy, edição ou
  exclusão de atividade.

### Meta 4: clima de cada atividade (feita)
- **Objetivo:** cada atividade ao ar livre ganha temperatura, umidade, vento e sensação térmica na hora e no local do
  treino; esteira, piscina e pedal virtual ficam `indoor`, sem clima.
- **Entrega visível:** o objeto `clima` em `GET /atletas/{atleta_id}/atividades/{atividade_id}` (estado e, em `ok`, os
  quatro valores, nunca a posição) e o comando `worker.preencher_clima`, que preenche o passado relendo os arquivos locais.
- **Critério de pronto:**
  - ADR do clima aprovada pelo Theo (tabela, posição, indoor, API do Open-Meteo, falhas);
  - o leitor guarda a posição de início arredondada a 2 casas, do FIT (exportação e upload) e do JSON;
  - cliente Open-Meteo testado só com resposta gravada; clima de atividade sintética bate com o oráculo;
  - preencher o clima é idempotente;
  - esteira, piscina e atividade sem posição nunca ganham clima inventado;
  - funciona para exportação e upload; QA com fixtures com posição fictícia.
- **Decisões do Angelo (03/11):** só a posição de início, arredondada a ~1 km, nunca o trajeto; ao Open-Meteo só posição
  arredondada e horário, sem identificador, na API gratuita do desenvolvimento; o passado relendo os arquivos locais; a
  investigação da série de tiros em paralelo. Tudo na [[decisoes/0007-clima-da-atividade]].
- **Resultado:** feita. Com fixtures sintéticas e a resposta gravada, todos os itens do critério bateram, incluindo o
  upload de FIT seguido do clima (QA da Bia, #116 / PR #130). Não verificados: a chamada real ao Open-Meteo pelo código
  (só uma manual, na #112, com posição inventada), o `worker.importar_garmin` na linha de comando com as fixtures de clima
  e a tela (o clima não tem tela). Passo a passo em [[produto/meta-4-como-rodar]]; resultado completo em
  [[produto/metas/meta-4-clima-atividade]].
- **Issues e ordem:**

  | # | Issue | Dono | Situação |
  |---|---|---|---|
  | #109 | ADR 0007, clima da atividade | duda-dados (aprovação do Theo) | feita |
  | #110 | Leitor guarda a posição de início arredondada, migração 0004 | duda-dados | feita |
  | #111 | Fixtures sintéticas com posição e oráculo do clima | caio-ciencia | feita |
  | #112 | Cliente Open-Meteo com resposta gravada | duda-dados | feita |
  | #113 | `clima_atividade` e `preencher_clima` idempotente | duda-dados | feita |
  | #114 | Clima na resposta da API e cliente regerado | duda-dados | feita |
  | #115 | Documentação e diário | nina-docs | feita |
  | #116 | QA de ponta a ponta com fixtures com posição | bia-qa | feita |
  | #117 | Resultado da meta e roteiro | paulo-planejador | esta |
  | #118 | Investigação da série de tiros com o histórico real (paralela) | caio-ciencia | relatório privado entregue; recomendações esperam o Angelo |
  | #119 | App web em `pt-BR` (proposta da Meta 3) | rafa-app | feita |
  | #120 | Regra do docs-ok no `AGENTS.md` (proposta da Meta 3) | Theo | feita |

- **Achados depois da meta (propostas, sem issue criada):** o `worker.importar_garmin` chamava o Open-Meteo por padrão no
  fim da importação, e reimportar o histórico real mandaria as posições na hora (resolvido na #132, PR #160: o padrão
  virou sem rede, e o clima só entra com `--com-clima`); um FIT avulso importado depois do JSON duplica a atividade, porque a exclusão "exportação não casa
  com exportação" vale também para `fonte_id` `fit-…` (proposta: a exclusão só quando os dois lados têm `activityId`); a
  investigação da série de tiros deixou recomendações (R1, melhor tiro junto da média; R2, `tiros_1km@5`, que amplia
  o que entra) que esperam o Angelo; clima na tela do app fica como candidata a meta futura. Detalhes em
  [[produto/metas/meta-4-clima-atividade]].
- **Aprendido na Meta 4:** ADR com fontes e uma lista "a confirmar" deixou para a chamada real só a conferência; efeito
  colateral de rede que manda dado do atleta tem de ser pedido explícito; toda exceção à regra de identidade precisa de
  teste com as duas fontes; limite escrito como "no máximo N chamadas" e contador nomeado pelo que conta; investigação
  com dado real em paralelo, com só a conclusão genérica no repositório, funcionou.
- **Quem:** duda-dados, caio-ciencia, nina-docs, bia-qa, Theo (ADR); rafa-app só na #119.
- **Fora:** previsão do tempo; ajuste por vento ou calor; clima na tela; trajeto completo; plano comercial do Open-Meteo;
  deploy.

### Meta 5: detecção de esforços (feita)
- **Objetivo:** cada treino lido como blocos (aquecimento, esforços, recuperações, desaquecimento, treino leve), com
  esforços de qualquer distância na corrida e por **duração** no ciclismo, laps automáticos do mesmo esforço juntados e a
  recuperação reconhecida pelo tempo de pausa entre as voltas. Treinos contínuos fortes ficam marcados como treinos-chave.
  A série de tiros de 1 km passa a sair dos esforços e mostra o melhor tiro de cada sessão.
- **Entrega visível:** o objeto `esforcos` em `GET /atletas/{atleta_id}/atividades/{atividade_id}`, o comando
  `worker.detectar_esforcos` e a série de tiros com o **melhor pace** e a **FC do melhor tiro** como valores principais
  (média no detalhe) no JSON, no PNG/CSV e na tela do app.
- **Critério de pronto:**
  - ADR 0008 (detecção de esforços) aprovada pelo Theo;
  - oráculo sintético calculado à mão; blocos, esforços de corrida por distância, de ciclismo por duração e treino-chave,
    cada um com teste de valor à mão;
  - um esforço cortado pelo lap automático (ex.: 1000 m + 500 m no mesmo ritmo) vira um esforço só; aquecimento e
    desaquecimento nunca contam como esforço;
  - detecção idempotente e versionada (`esforcos@1`): rodar de novo não duplica, e mudar a versão detecta de novo;
  - série de tiros a partir dos esforços: mínimo de 2 tiros, tiros de 1 km do bloco principal de um treino misto contam,
    esteira fora; os casos das regras anteriores viram testes de regressão;
  - OpenAPI declarado e cliente regerado; QA com fixtures num clone limpo, seguindo só o guia;
  - conferência local com o histórico real, com os números só em `entregas/`.
- **Decisões de produto (04/11):** a detecção vem antes da carga, e as metas foram renumeradas. Na corrida o esforço se
  mede por distância e no ciclismo por tempo. Sessões com 2 tiros entram. Num treino misto, os tiros de 1 km do bloco
  principal contam. O valor principal da série é o melhor pace de tiro, e o painel de FC mostra a FC do melhor tiro.
  O treino de transição vira um rótulo sim/não (sugerido por regra e corrigível pelo atleta), em vez de juntar atividades.
  Dois esforços vizinhos que a regra de 5% não junta contam como dois.
- **Decisões de 06/11:** parada de 15 s ou mais (corrida) ou 30 s (ciclismo) corta a sequência do treino-chave (Angelo);
  "ok para todas" as recomendações do treino de transição (Angelo); ADR 0009 aceita, `ref_origem` recalculado na leitura,
  um único ponto de detecção (`classificar_atividades`), adendos 2 a 4 da ADR 0004 e subtipos do multiesporte sem migração
  (Theo). Ver [[diario/2026-11-06]].
- **Resultado:** feita. Com fixtures sintéticas, num clone limpo e seguindo só o [[produto/meta-5-como-rodar]], todos os
  itens do critério bateram (QA da Bia, #172 / PR #239, com `tests/test_e2e_meta5.py`); a conferência com o histórico real
  foi local (#169), e no repositório ficaram só as limitações genéricas ([[metricas/esforcos]], [[metricas/tiros-1km]]).
  Não verificados: a tela no navegador, no iOS e no Android (só `npm test` e capturas sintéticas) e o `downgrade` das
  migrações 0006 e 0007. Resultado completo em [[produto/metas/meta-5-deteccao-esforcos]].
- **Issues e ordem:**

  | # | Issue | Dono | Situação |
  |---|---|---|---|
  | #148 | ADR 0008, detecção de esforços | caio-ciencia com duda-dados (aprovação do Theo) | feita (PR #180) |
  | #161 | Fixtures sintéticas e oráculo dos esforços | caio-ciencia | feita (PR #187) |
  | #162 | Blocos do treino: pausas, laps juntados, aquecimento e desaquecimento | caio-ciencia | feita (PR #188) |
  | #163 | Esforços de corrida por distância (d200 a d5000) | caio-ciencia | feita (PR #200) |
  | #164 | Esforços de ciclismo por duração (t1 a t60) | caio-ciencia | feita (PR #205) |
  | #165 | Treino-chave contínuo | caio-ciencia | feita (PR #210) |
  | #151 | Melhor tiro da sessão na agregação | caio-ciencia | feita (PR #178) |
  | #152 | Melhor pace e FC do melhor tiro no contrato (ADR 0004) e na API | duda-dados (aprovação do Theo) | feita (PR #185) |
  | #153 | Melhor pace no PNG e no CSV | caio-ciencia | feita (PR #199) |
  | #154 | Melhor pace como valor principal na tela | rafa-app | feita (PR #201) |
  | #166 | Esforços no banco e `worker.detectar_esforcos` | duda-dados | feita (PR #222) |
  | #167 | Esforços na API e cliente regerado | duda-dados | feita (PR #226) |
  | #168 | Série de tiros de 1 km a partir dos esforços (`tiros_1km@5`) | caio-ciencia | feita (PR #228) |
  | #169 | Conferência local da detecção com o histórico real | caio-ciencia (com duda-dados) | feita (PR #235; relatório só em `entregas/`) |
  | #171 | Documentação, guia `meta-5-como-rodar` e diário | nina-docs | feita (PR #238) |
  | #172 | QA de ponta a ponta com fixtures de esforços | bia-qa | feita (PR #239) |
  | #173 | Resultado da meta e roteiro | paulo-planejador | esta |

- **Paralelas na Meta 5** (fora do critério de pronto), todas feitas: #132 (PR #160), #133 (PR #186), #183 (PR #184),
  treino de transição #155, #156, #157 e #170 (PRs #214, #223, #229, #232), tela de um treino #158, #159, #216, #217,
  #219, #220 e #233 (PRs #212, #215, #231, #227, #225, #221, #234), tela de evolução #202 (PR #211), HTML do app web #218
  (PR #224) e multiesporte #230 (PR #236). As #149 e #150 foram absorvidas pela #168. Lista com as entregas em
  [[produto/metas/meta-5-deteccao-esforcos]].
- **Pendências fora da meta (abertas):** #213 (rafa-app, acessibilidade e visual da tela de evolução), #237 (rafa-app com a
  Lia, mesma aparência para distância e pace na tela de um treino) e #74 (vault do Graphify, quando o Theo pedir o grafo).
  Não entram na Meta 6; o lugar natural das duas do app é a candidata "tela dos esforços" (abaixo).
- **Aprendido na Meta 5:** premissa marcada como pendente até a resposta do Angelo evitou retrabalho; o oráculo tem de dizer
  a referência que supõe (no banco com histórico, o mesmo pedal dá outro resultado); um único ponto de detecção manteve
  importação, upload e comando iguais; a regra "a API formata, o app mostra" escala, mas o formato pronto decide a
  aparência (#237); a meta cresceu pelas paralelas e o roteiro ficou defasado durante a semana (achado da Bia): a situação
  do dia a dia fica no GitHub, e o roteiro guarda plano, ordem e resultado.
- **Quem:** caio-ciencia (ADR, regras, oráculo, série, gráfico, conferência), duda-dados (banco, comandos, API,
  multiesporte), rafa-app (telas), lia-design (spec da tela de um treino), nina-docs, bia-qa, Theo (ADRs 0008 e 0009 e os
  adendos da 0004).
- **Fora:** calibração pela lista de recordes pessoais (os recordes chegam ao banco na Meta 6, #174); esforço por tempo
  na corrida; potência no ciclismo; esforços na natação; tela dos esforços e dos treinos de transição no app; evolução
  por faixa de distância na tela.

### Meta 6: carga de treino (feita)
- **Objetivo:** a primeira métrica derivada de carga: a carga de cada atividade (rTSS pelo pace, hrTSS pela FC) e, dia a dia,
  condicionamento (CTL), fadiga (ATL) e forma (TSB), sempre mostrados como estimativa.
- **Entrega visível:** `GET /atletas/{atleta_id}/carga` (série diária de CTL, ATL e TSB, com a carga de cada dia e quantas
  atividades ficaram sem carga), a carga de cada atividade no `GET` da atividade, o gráfico de carga em `entregas/` e a
  conferência com a carga calculada pelo Garmin.
- **Critério de pronto:**
  - ADR 0010 da carga aprovada pelo Theo: tabelas dos dados de saúde e da carga, fórmula por modalidade, versão do
    cálculo e o que fazer sem FC, sem pace ou sem limiar;
  - os dados de saúde e métricas da exportação Garmin lidos e guardados no banco local, de forma idempotente e com
    vigência (limiar, zonas, FC máxima e de repouso, recordes, carga do Garmin);
  - cada métrica (rTSS, hrTSS, CTL/ATL/TSB) com nota em `docs/metricas/` e teste com valor calculado à mão a partir de
    fixtures sintéticas (oráculo);
  - o cálculo é idempotente e versionado: rodar de novo não duplica, e mudar a versão ou o limiar recalcula;
  - atividade sem dado suficiente fica "sem carga", com o motivo, nunca com carga inventada; **atleta sem os dados de saúde
    importados fica "sem carga", sem estimar o limiar**; a série diária diz quantas ficaram de fora;
  - as atividades com subtipo `multiesporte_pai` e `troca` não entram na carga (nem contam em dobro com as partes);
  - conferência com a carga do Garmin com fixtures e, localmente, com o histórico real (números só em `entregas/`);
  - endpoint declarado no OpenAPI e cliente regerado; QA com fixtures sintéticas, num clone limpo, seguindo só o guia.
- **Decisões de produto (04/11):** o limiar vem dos dados de saúde da exportação Garmin, onde há limiar por FC e por
  velocidade com histórico, zonas de FC, recordes pessoais e a carga aguda/crônica do Garmin. Nada de estimar o limiar.
  Pode guardar todos esses dados (só no banco local). A carga é conferida com o histórico real localmente.
- **Decisões de 07/11 e 08/11:** as sete propostas da ADR 0010 (Angelo, "sim" para todas), o modelo de dados e as regras do
  leitor, dos recordes, da API e da conferência (Theo), `tiros_1km@6` (#243) e `carga@2` (#255) (Angelo). Lista completa em
  [[produto/metas/meta-6-carga-treino]], "Decisões"; ver [[diario/2026-11-07]] e [[diario/2026-11-08]].
- **Resultado:** feita. Com fixtures sintéticas, a Bia conferiu o critério de pronto com `tests/test_e2e_meta6.py` e seguiu o
  [[produto/meta-6-como-rodar]] de ponta a ponta, passos 1 a 9 iguais ao guia, sem bug (#146 / PR #258). A conferência com o
  histórico real foi local (#144), com os números só em `entregas/`. Não verificados: o que depende do dado real; a carga não
  tem tela. Resultado completo em [[produto/metas/meta-6-carga-treino]].
- **Conferido no código antes das issues (03/11):** só existe FC média (da atividade e de cada volta). Não há limiar, zonas
  nem tabela de métrica derivada, e `segmento.zona` nunca é preenchida. O leitor FIT não lê a série por segundo, então a
  primeira versão calcula **por volta**, sem ajuste de subida. `tipo_treino` só tem `intervalado`. Natação sem FC fica
  "sem carga". Ciclismo sem potência usa o hrTSS.
- **Aviso da Meta 5 para a ADR 0010 (#134):**
  - **A carga ignora os subtipos `multiesporte_pai` e `troca`** (decisão do Theo na #230). O pai agrupa as partes, que já
    são atividades com carga própria; contar o pai somaria a mesma carga duas vezes. A troca entra como `outra`. A ADR diz
    como os dois aparecem na série (fora da conta ou com um motivo próprio) e o teste cobre o caso com as fixtures de
    `tests/fixtures/multiesporte/`.
  - O "conferido no código" acima é de 03/11. O main de agora tem `bloco_atividade` (migração 0006), `rotulo_transicao`
    (0007), os subtipos novos e `worker.reclassificar_subtipo`; a próxima migração é a 0008. A ADR confere contra o main
    atual e diz se a carga usa as voltas (como planejado) ou os blocos da detecção.
  - Cada parte de um treino de transição tem a sua carga; o grupo não soma nada além das partes.
  - A conferir na ADR: esteira (distância do sensor) no rTSS e pedal `virtual` no hrTSS.
- **Issues e ordem:**

  | # | Issue | Dono | Depende de | Situação |
  |---|---|---|---|---|
  | #134 | ADR 0010, carga de treino | caio-ciencia com duda-dados (aprovação do Theo) | nenhuma | feita (PR #241) |
  | #135 | Formato dos dados de saúde da exportação Garmin e fixtures sintéticas | duda-dados | nenhuma | feita (PR #242) |
  | #136 | Leitor dos dados de saúde e métricas | duda-dados | #135 | feita (PR #244) |
  | #137 | Fixtures de algumas semanas e oráculo da carga | caio-ciencia | #134, #135 | feita (PR #245) |
  | #138 | rTSS e hrTSS por volta (função pura) | caio-ciencia | #134 (oráculo #137) | feita (PR #249) |
  | #139 | CTL, ATL e TSB diários (função pura) | caio-ciencia | #134 (oráculo #137) | feita (PR #248) |
  | #140 | Limiar e zonas no banco, importação idempotente | duda-dados | #134, #136, #132 | feita (PR #246) |
  | #174 | Recordes pessoais e carga do Garmin no banco | duda-dados | #134, #136 | feita (PR #247) |
  | #141 | Carga por atividade no banco e `worker.calcular_carga` | duda-dados | #138, #140 | feita (PR #251) |
  | #142 | Endpoint da carga, carga no `GET` da atividade e cliente regerado | duda-dados | #139, #141 | feita (PR #253) |
  | #143 | Gráfico de carga em `entregas/` | caio-ciencia | #139, #141 | feita (PR #252) |
  | #144 | Conferência da nossa carga com a carga do Garmin (fixtures e histórico real local) | caio-ciencia | #174, #141 | feita (PR #254; relatório só em `entregas/`) |
  | #145 | Documentação, guia `meta-6-como-rodar` e diário | nina-docs | #142, #143, #144 | feita (PR #257) |
  | #146 | QA de ponta a ponta com fixtures | bia-qa | #145 | feita (PR #258) |
  | #147 | Resultado da meta e roteiro | paulo-planejador | #146 | esta |

  A coluna "Situação" só muda para "feita" no fechamento da meta; o andamento do dia a dia fica no GitHub (aprendido na
  Meta 5). Funcionou: a tabela não ficou defasada durante a meta.

  **Ordem:**
  1. **Largada, em paralelo:** #134 (Caio, com a Duda) e #135 (Duda). Nenhuma das duas depende de outra.
  2. **Dados de saúde:** #135 → #136 (o leitor pode começar pelo limiar antes do merge da ADR).
  3. **Fórmulas, depois da ADR:** #137 (oráculo; precisa também do formato da #135) → #138 e #139 em paralelo.
  4. **Banco, depois da ADR e do leitor:** #140 e #174 (uma migração combinada entre as duas, a partir da 0008).
  5. **Carga gravada:** #141 (precisa da #138 e da #140). É o ponto onde os dois caminhos se encontram.
  6. **Saídas, em paralelo:** #142 (API; #139, #141), #143 (gráfico; #139, #141) e #144 (conferência com o Garmin; #174,
     #141).
  7. **Fechamento:** #145 → #146 → #147.

  Caminho crítico: #135 → #136 → #140 → #141 → #142 / #144 → #145 → #146 → #147, com a #134 liberando a #140 e a #174.
  Enquanto a ADR não entra, a Duda faz a #135 e a #136, e o Caio adianta o oráculo à mão sobre o formato da #135.
- **Paralelas na Meta 6:** #243, `tiros_1km@6` (PR #250, fora do critério de pronto), e #255, `carga@2` (PR #256).
- **Pendências fora da meta:** as duas observações da Bia sobre o guia viram paralela pequena da Meta 7 (nina-docs); tela
  da carga no app, #213, #237 e #74 ficam em "Candidatas sem número" ([[produto/metas/meta-6-carga-treino]]) e não entram na
  Meta 7. A paralela virou a #273.
- **Aprendido na Meta 6:** propostas de produto numa lista "A confirmar" da ADR deixaram o Angelo responder todas de uma vez;
  a regra do dado fisiológico (só banco local, nunca log nem API, comando para apagar) escrita na ADR evitou discussão em cada
  PR; duas trilhas com um único ponto de encontro (#141) fecharam a meta em três dias; um caso de origem fora do oráculo
  (volta sem FC) virou `carga@2` sem migração, graças à versão na linha; teste de comportamento compara com a constante
  `VERSAO`, não com o texto `carga@1` (três testes quebraram o CI no #256); o QA pode escrever o e2e antes do guia, mas o
  fechamento só vale com o guia seguido.
- **Quem:** caio-ciencia (fórmulas, oráculo, gráfico, conferência), duda-dados (dados de saúde, banco, comando, API),
  nina-docs, bia-qa, Theo (ADR).
- **Fora:** linha de base pessoal (Meta 7); estimar o limiar do histórico; NGP e ajuste de subida; leitura da série por
  segundo; TSS por potência; sTSS e carga por PSE na natação (o check-in é a Meta 8); ajuste por calor com o clima da
  Meta 4; tela de carga no app; motor de explicação.

### Meta 7: linha de base pessoal e semana-padrão (feita)
- **Objetivo:** cada treino comparado com o normal do próprio atleta, **só na mesma modalidade e no mesmo tipo de treino**:
  uma linha de base móvel (mediana da janela) e uma medida robusta de quanto a sessão fugiu do normal. O tipo de treino vem
  da **semana-padrão** que o atleta ou o treinador definem (para cada dia da semana, uma ou mais modalidades com o tipo); a
  regra automática (`leve`/`longo` na corrida) fica só como reserva para dia sem plano. É a camada 2 do
  [[produto/plano-mvp-execucao]] (seção 4.2), com os passos 1 e 2 da seção 3.1, e a base do motor de explicação e do
  feedback (Meta 9).
- **Entrega visível:** a tela da semana-padrão no app (web), sobre `GET` e `PUT /atletas/{atleta_id}/semana-padrao`; o tipo
  de cada atividade com a origem (`professor`, `trainingpeaks`, `semana_padrao`, `sugestao`) e a divergência quando o formato
  contradiz o plano; o objeto `linha_base` (`linha_base@2`) em `GET /atletas/{atleta_id}/atividades/{atividade_id}`, com
  valor, mediana, desvio, `z`, quantos treinos entraram, estado e texto pronto.
- **Critério de pronto (como ficou, com o adendo 2 da ADR 0011):**
  - ADR 0011 aprovada pelo Theo antes de qualquer migração (semana-padrão com `vigente_desde` e `definido_por`, precedência,
    encaixe, divergência, regra de reserva, medida robusta, limite "fora do normal", métricas por modalidade, versões
    `tipo_treino@1` e `linha_base@2`, migração 0011), com a seção "A confirmar" respondida pelo Angelo;
  - nota em `docs/metricas/` para a linha de base e para o tipo de treino, com teste de valor à mão (oráculo sobre fixtures
    sintéticas de 12 semanas, com uma semana-padrão que muda de vigência);
  - a semana-padrão é gravada e lida pela API e pela tela; mudar a semana-padrão não reescreve o tipo de atividades
    anteriores a `vigente_desde`;
  - o tipo nunca sobrescreve um tipo confirmado, do professor ou do TrainingPeaks; a semana-padrão vence a regra; dia sem
    plano cai na regra; divergência só como dado; idempotente e versionado; a série de tiros continua igual (regressão);
  - "ainda aprendendo" abaixo de **8 treinos do mesmo tipo nas últimas 12 semanas**; tipos e modalidades diferentes nunca se
    misturam; atividade sem tipo fica sem linha de base, com o motivo; a sessão nunca entra na própria linha de base;
  - endpoints no OpenAPI, adendos da ADR 0004 e cliente regerado; tela com teste e revisão da Lia; QA com fixtures num clone
    limpo, seguindo só o guia;
  - conferência local com o histórico real, números só em `entregas/`.
- **Decisões de 09/11 (Angelo):** as cinco perguntas da #147 (a quarta mudou o rumo para a semana-padrão); "ok para as
  sete" da seção "A confirmar" da ADR 0011; "ok para as quatro" do adendo 2 (`linha_base@2`: janela de 12 semanas com mínimo
  de 8; a parte de treino de transição com base própria; carga por hora no lugar da carga absoluta; no `intervalado` sem série
  de 1 km, FC média e carga por hora, com o esforço curto de fora). Lista completa em [[diario/2026-11-09]] e em
  [[produto/metas/meta-7-linha-de-base-semana-padrao]].
- **Decisões do Theo (09/11):** modelo de dados da ADR 0011 (semana-padrão por atleta com vigência, `tipo_versao` e
  `tipo_divergencia` em `atividade`); o `PUT` reaplica o tipo só de `vigente_desde` em diante; linha de base calculada na
  leitura e nunca gravada; textos prontos na API.
- **Issues e ordem:**

  | # | Issue | Dono | Depende de | Situação |
  |---|---|---|---|---|
  | #274 | Roteiro com a Meta 7 replanejada | paulo-planejador | nenhuma | feita (PR #275) |
  | #260 | ADR 0011: linha de base, semana-padrão e tipo de treino | caio-ciencia com duda-dados (aprovação do Theo) | nenhuma | feita (PR #277) |
  | #261 | Fixtures de 12 semanas com semana-padrão e oráculo | caio-ciencia | #260 | feita (PR #278) |
  | #262 | `tipo_treino@1`: encaixe na semana-padrão e regra de reserva | caio-ciencia | #260, #261 | feita (PR #280) |
  | #263 | `linha_base@1`: linha de base e desvio robusto | caio-ciencia | #260, #261 | feita (PR #281) |
  | #264 | Semana-padrão no banco (migração 0011), `GET`/`PUT`, cliente regerado | duda-dados | #260 | feita (PR #282) |
  | #265 | `classificar_atividades` com a semana-padrão e a precedência | duda-dados | #262, #264 | feita (PR #284) |
  | #266 | `linha_base`, tipo e divergência no `GET` da atividade | duda-dados | #263, #265 | feita (PR #286) |
  | #267 | Desenho da tela da semana-padrão | lia-design | #260 | feita (PR #279) |
  | #268 | Tela da semana-padrão no app | rafa-app (revisão da Lia) | #267, #264 | feita (PR #285) |
  | #288 | `linha_base@2` (adendo 2 da ADR 0011) | caio-ciencia | #266 | feita (PR #289) |
  | #269 | Conferência local com o histórico real | caio-ciencia com duda-dados | #265, #266 e a semana-padrão do Angelo | feita (só local; números em `entregas/`) |
  | #270 | Documentação, guia `meta-7-como-rodar` e diário | nina-docs | #266, #268, #269 | feita (PR #290) |
  | #271 | QA de ponta a ponta com fixtures | bia-qa | #270 | feita (PR #291) |
  | #272 | Resultado da meta e roteiro | paulo-planejador | #271 | esta |

  Paralelas: #273 (guia da Meta 6, PR #276), glossário (PR #283) e ícones em [[design/tokens]] (PR #287).
- **Resultado:** feita. Com fixtures sintéticas, a Bia conferiu o critério de pronto com `tests/test_e2e_meta7.py` (42
  testes) e seguiu o [[produto/meta-7-como-rodar]] do zero, passos 1 a 10 iguais ao guia, sem bug (#271 / PR #291). A
  conferência com o histórico real foi local (#269), com os números só em `entregas/`. Não verificados: o app em celular
  (só a web) e o que depende do dado real. Resultado completo em [[produto/metas/meta-7-linha-de-base-semana-padrao]].
- **Aprendido na Meta 7:** uma resposta do Angelo que muda o rumo antes da largada custa pouco se o roteiro é refeito no
  mesmo dia, antes de qualquer issue de código; a seção "A confirmar" funcionou de novo (sete respostas de uma vez, e mais
  quatro no adendo); a linha de base calculada na leitura deixou a `linha_base@2` sair sem migração; quando um adendo muda um
  número do critério de pronto, o PR do adendo atualiza também o roteiro (a QA achou o roteiro com 8 semanas e `linha_base@1`);
  fixtures sem voltas não servem para o `worker.reclassificar`, que refaz os blocos pelas voltas (o guia usa um segundo atleta
  com FIT sintéticos).
- **Quem:** caio-ciencia, duda-dados, lia-design, rafa-app, nina-docs, bia-qa, Theo (ADR 0011 e adendos da ADR 0004), Angelo
  (a semana-padrão dele no banco local).
- **Fora:** semana-padrão por grupo; login de professor e vínculo; confirmação em lote e a caixa das divergências (Meta 10);
  treino planejado com duração, zona ou equipamento; TrainingPeaks; motor de explicação; início frio com valores da
  literatura; tela da linha de base no app; `moderado` e `fartlek` pela regra; linha de base de CTL/ATL/TSB e da semana. As
  pendências da meta estão em "Candidatas sem número".

### Meta 8: check-in pós-treino (feita)
- **Objetivo:** o atleta registra, em **3 toques**, como foi o treino: PSE (esforço percebido), sensação e observação, com
  "nada a relatar" como resposta válida. É o "check-in é o produto" do [[produto/plano-mvp-execucao]] (seções 3.1 e 6) e o
  dado que falta para o motor de explicação (trabalho, estresse, dor) e para o feedback (Meta 9).
- **Entrega visível:**
  - a tela de check-in no app (web e celular), aberta a partir da tela de um treino, com no máximo uma pergunta por vez;
  - a lista dos treinos recentes sem check-in, para o atleta não perder nenhum;
  - `PUT`, `GET` e `DELETE` do check-in de uma atividade na API, e o check-in no `GET` da atividade;
  - a carga pela PSE (`carga_pse@1`, PSE × minutos) de cada atividade com check-in, separada da `carga@2` e sem série
    diária, o que dá uma carga também à natação.
- **Critério de pronto:**
  - ADR 0012 aprovada pelo Theo antes da migração: tabela do check-in (um por atividade), escalas, observação, "nada a
    relatar", edição e prazo, regra de dado sensível, versão da `carga_pse@1`; propostas de produto em "A confirmar";
  - check-in completo em 3 toques (teste de componente que conta os toques); "nada a relatar" válido; editar e apagar
    funcionam; uma atividade nunca tem dois check-ins;
  - a observação segue a regra do dado de saúde da Meta 6: só no banco local, nunca em log, devolvida só ao próprio atleta,
    com comando para apagar;
  - nota em `docs/metricas/` e teste de valor à mão para a `carga_pse@1`;
  - endpoints no OpenAPI, adendo da ADR 0004 e cliente regerado; tela com teste e revisão da Lia; aberta pelo menos uma vez
    num celular pelo Angelo, no fim da meta; QA com fixtures num clone limpo, seguindo só o guia.
- **Decisões de 09/11 (Angelo, "ok para as cinco"):** abrir as issues e começar; 3 toques com PSE de 0 a 10 (CR-10), sensação
  em 5 níveis e observação por atalhos com texto livre opcional e "nada a relatar"; `carga_pse@1` por atividade, sem série
  diária; ele abre a tela de check-in no celular uma vez no fim da meta; a observação segue a regra dos dados de saúde da
  Meta 6 (só no banco local, nunca em log, devolvida só ao próprio atleta, comando para apagar).
- **Decisões de 10/11 (Angelo, "ok para as cinco" do "A confirmar" da ADR 0012):** prazo de 7 dias para registrar, editar e
  apagar sem prazo; toda atividade pede check-in, menos o registro geral ("pai") do multiesporte e as trocas, com um check-in
  por parte; PSE, sensação e observação obrigatórias; nome "Carga pela PSE", em UA; check-in sem login enquanto é piloto local
  (identidade na Meta 10). A ADR 0012 passou a **aceita** (PR #305).
- **Decisões do Theo (09/11):** modelo de dados da ADR 0012 (`checkin_treino`, um por atividade, `CHECK` nas escalas e na
  coerência de "nada a relatar"); `carga_pse@1` calculada na leitura; `checkin_aberto` e `pse_sugerida` no `GET` da atividade;
  caminho mínimo em 3 toques e 4 com atalho ou texto; edição em tela única.
- **Issues e ordem:**

  | # | Issue | Dono | Depende de | Situação |
  |---|---|---|---|---|
  | #293 | ADR 0012, check-in pós-treino (modelo, escalas, prazo, dado sensível, `carga_pse@1`) | caio-ciencia com duda-dados (aprovação do Theo) | nenhuma | feita (PR #305, aceita em 10/11) |
  | #294 | Fixtures sintéticas de check-in e oráculo (inclui `carga_pse@1`) | caio-ciencia | #293 (adianta à mão) | feita (PR #307) |
  | #295 | Desenho da tela de check-in e da lista de treinos sem check-in | lia-design | #293 (pode rascunhar pelo plano) | feita (PR #309) |
  | #296 | Check-in no banco (migração 0012), `PUT`/`GET`/`DELETE`, comando para apagar, cliente regerado | duda-dados | #293 | feita (PR #310) |
  | #297 | `carga_pse@1`, carga pela PSE por atividade | caio-ciencia | #293 (oráculo #294) | feita (PR #308) |
  | #298 | Check-in no `GET` da atividade e lista de treinos sem check-in | duda-dados | #296 (fixtures #294) | feita (PR #311) |
  | #299 | Tela de check-in no app | rafa-app (revisão da Lia) | #295, #296, #298 | feita (PR #313) |
  | #300 | Documentação, guia `meta-8-como-rodar` e diário | nina-docs | #298, #297, #299 | feita (PR #315) |
  | #301 | QA de ponta a ponta com fixtures e o celular (o Angelo abre a tela uma vez) | bia-qa | #300 | feita (PR #317; celular não verificado) |
  | #302 | Resultado da meta e roteiro | paulo-planejador | #301 | esta |

  Entraram durante a meta: #306 (fixture do app depois do cliente regerado, PR #312) e #316 (texto da carga pela PSE em
  minutos e segundos, achado do guia, PR #318). Paralelas: #303 (hífen sem quebra, PR #304) e glossário com o
  [[00-inicio]] (PR #314).
- **Resultado:** feita. Com fixtures sintéticas, a Bia conferiu o critério de pronto com `tests/test_e2e_meta8.py` (15
  testes) e seguiu o [[produto/meta-8-como-rodar]] do zero, passos 1 a 14 iguais ao guia, inclusive os 12 estados forçados
  da API falsa na tela, sem bug no código (#301 / PR #317). `uv run pytest` com 1705 verdes e 2 pulados; `npm test` com 225.
  **Não verificado:** a tela num celular de verdade (o Angelo pelo Expo Go), que segue pendente. Resultado completo em
  [[produto/metas/meta-8-check-in]].
- **Aprendido na Meta 8:** modelo de dados aprovado e ADR aceita são etapas diferentes: o código andou com o modelo aprovado,
  mas a ADR ficou fora do `main` a meta toda e os links não resolviam (próxima vez: ADR no `main` como `proposta` logo depois
  da aprovação do modelo); a seção "A confirmar" com padrões funcionou pela terceira vez, sem mudar código, porque os padrões
  ficaram num só lugar; rodar o guia achou a conta da carga pela PSE que não fechava à mão (#316); dúvidas de desenho
  respondidas antes da tela viraram campos da API e tiraram regra do app; o passo que depende do Angelo (celular) ficou para
  o fim e ficou pendente: marcar junto da QA.
- **Quem:** caio-ciencia (ADR, escalas, carga pela PSE, oráculo), duda-dados (banco, API, cliente, comando para apagar),
  lia-design (desenho), rafa-app (tela), nina-docs, bia-qa, Theo (ADR 0012 e adendo 8 da ADR 0004), Angelo (respostas; o
  celular segue pendente).
- **Fora:** lembrete por WhatsApp ou e-mail (conta ou serviço novo, "PRECISA DO ANGELO" quando chegar a vez); check-in
  semanal; motivo de falta para o treino planejado que não aconteceu (candidata); equipamento e zona no check-in; série
  diária e CTL/ATL pela PSE; o check-in no motor de explicação e no feedback (Meta 9); o professor vendo o check-in (Meta 10).

### Meta 9: feedback automático por treino (feita)
> **Feita em 12/11, com três itens não verificados** (o cartão na tela rodando, o celular do Angelo e a revisão da Lia sobre a tela
> pronta). O Angelo deu "ok" às oito decisões em 10/11 (ver "PRECISA DO ANGELO"), com um esclarecimento no item 6: o feedback é
> **texto escrito**, sem áudio. Issues #322 a #335 e as que entraram durante a meta; resultado completo em
> [[produto/metas/meta-9-feedback-automatico]].

- **Objetivo:** depois do check-in, o atleta lê **3 a 5 linhas** sobre o treino: como foi em relação ao normal dele naquele
  tipo de treino, o que o check-in e o contexto (clima, carga) dizem, e uma observação positiva. É a camada 4 do
  [[produto/plano-mvp-execucao]] (seção 4.4) e a primeira linha da cadência da seção 4.6. **Quem calcula é o código; a IA só
  redige** a partir de um **pacote de fatos** (`fatos_treino@1`) montado com o que já existe: tipo de treino e linha de base
  (`linha_base@2`), clima, `carga@2`, `carga_pse@1`, esforços e o check-in.
- **Entrega visível:**
  - o cartão "Feedback" na tela de um treino no app (web e celular), abaixo do check-in;
  - o `feedback` no `GET` da atividade (texto, versão do pacote, de onde veio o texto e o motivo quando não há feedback);
  - `worker.gerar_feedback` para gerar ou refazer o feedback de um atleta, e o feedback apagado junto com o check-in.
- **Critério de pronto:**
  - ADR 0013 aprovada pelo Theo antes da migração: pacote de fatos e versão, onde o feedback fica guardado, quando é gerado
    e quando fica desatualizado, camada de LLM, checagens, o que vai e o que nunca vai ao provedor, regra do dado de saúde;
    as oito decisões do Angelo de 10/11 registradas; o que sobrar em "A confirmar"; o Angelo lê os 5 exemplos sintéticos
    (tom do texto) antes do código do feedback (#327);
  - `fatos_treino@1` como função pura, com nota em `docs/metricas/` e oráculo sobre fixtures sintéticas; o pacote só tem
    números que o código já calcula (nenhum número novo inventado) e não afirma causa;
  - checagens automáticas: **todo número do texto está no pacote** e **nenhum termo da lista de linguagem proibida**
    (diagnóstico médico, culpa, promessa, causa afirmada); texto reprovado é descartado e nunca chega ao app, com teste sobre
    textos ruins sintéticos;
  - LLM só pela **camada trocável** (LiteLLM, `LLM_PROVIDER` e `LLM_MODEL` do `.env`); testes e CI com um **provedor falso**,
    sem rede; nada do pacote nem do texto em log;
  - o texto livre da observação do check-in **nunca** vai ao provedor; o feedback segue a regra do dado de saúde da Meta 6 e
    é apagado com o check-in;
  - endpoints no OpenAPI, adendo da ADR 0004 e cliente regerado; cartão com teste e revisão da Lia;
  - QA com fixtures num clone limpo, seguindo só o guia, com o provedor falso; uma rodada com o provedor de verdade só com
    fixtures sintéticas (decisão 3); o Angelo abre no celular, **na mesma sessão**, o check-in (pendente da Meta 8) e o
    cartão de feedback.
- **Issues e ordem** (cada uma até 1 dia; abertas em 10/11; o critério curto de cada uma está na própria issue):

  | Proposta | Issue | Título | Dono | Depende de | Situação |
  |---|---|---|---|---|---|
  | P1 | #322 | ADR 0013: feedback automático por treino | caio-ciencia com duda-dados (aprovação do Theo) | nenhuma | feita (PR #340 como proposta, PR #345 aceita em 10/11) |
  | P2 | #323 | Fixtures sintéticas e oráculo do pacote de fatos, com textos bons e ruins | caio-ciencia | #322 | feita (PRs #341 e #346) |
  | P3 | #324 | `fatos_treino@1`: pacote de fatos como função pura | caio-ciencia | #322, #323 | feita (PR #347) |
  | P4 | #325 | Checagens: números do texto contra o pacote e linguagem proibida | caio-ciencia | #322, #323 | feita (PR #349; `checagens_feedback@2` no PR #360) |
  | P5 | #326 | Camada de LLM trocável (LiteLLM), provedor falso, tempo limite, sem log de conteúdo | duda-dados | #322 | feita (PR #343) |
  | P6 | #327 | Feedback no banco (migração 0013) e `worker.gerar_feedback` | duda-dados | #324, #325, #326 | feita (PR #348) |
  | P7 | #328 | `feedback` no `GET` da atividade, adendo da ADR 0004, cliente regerado | duda-dados | #327 | feita (PR #350, adendo 10) |
  | P8 | #329 | Desenho do cartão de feedback na tela do treino | lia-design | #322 | feita (PR #338) |
  | P9 | #330 | Cartão de feedback no app | rafa-app (revisão da Lia) | #328, #329 | feita (PR #352, design-ok sobre capturas) |
  | P10 | #331 | Documentação, guia `meta-9-como-rodar` e diário | nina-docs | #328, #330 | feita (PR #353) |
  | P11 | #332 | QA de ponta a ponta com fixtures, e o celular com o Angelo | bia-qa | #331 | feita (PR #362; tela e celular **não verificados**) |
  | P12 | #333 | Resultado da meta e roteiro | paulo-planejador | #332 | esta |
  | P13 | #334 | Capturas do check-in no tema escuro e nos estados de erro (paralela) | rafa-app (revisão da Lia) | nenhuma | feita (PR #351) |
  | P14 | #335 | Piloto local: buscar a atividade do dia no Garmin Connect, `worker.buscar_garmin` (paralela) | duda-dados | nenhuma | feita (PR #339) |

  Entraram durante a meta, todas feitas: #342 (o `buscar_garmin` não baixa de novo o que já importou, PR #344); #355
  (`feedback_prompt@2` e `checagens_feedback@2`, depois da primeira rodada com o provedor de verdade sobre fixtures, a pedido do
  Angelo; PRs #356 e #360); #357 (`LLM_INTERVALO_S`, parada no limite do provedor, `--refazer` que mantém o texto pronto; PR #358);
  #354 (o `.env` é sempre o da raiz do repositório, PR #359); #361 (texto do provedor falso reprovado pela checagem nova, achado da
  QA; PR #363). Em aberto, fora do critério: #364 (nina-docs, alinhar glossário, [[00-inicio]], guia, notas e diário depois da QA).

  **Ordem:** #322 na largada (Caio, com a Duda no modelo); #323 e #329 adiantam em paralelo; #326 começa assim que o Theo
  aprovar a parte da camada de LLM. Depois da ADR, #324 e #325 (Caio) em paralelo com #326 (Duda); #327 é o encontro do
  backend; #328 depois da #327; #330 precisa da #328 e da #329. Caminho crítico: #322 → #324 → #327 → #328 → #330 → #331 →
  #332 → #333. A QA usa só fixtures; o feedback dos treinos reais do Angelo no provedor foi autorizado por ele em 10/11, mas
  roda só localmente (por ele ou pelo Theo) e nada do resultado entra no repositório (ver "PRECISA DO ANGELO").
- **Paralelas (fora do critério de pronto, sem dependência):**
  - **P13 (#334):** capturas do check-in no tema escuro e nos estados de erro (item 4 da revisão da Lia no #313; rafa-app),
    já que o Rafa mexe na tela do treino nesta meta.
  - **P14 (#335), pedido do Angelo em 10/11:** o piloto local busca a atividade do dia direto da conta Garmin Connect dele,
    sem subir um FIT à mão. `worker.buscar_garmin` entra na conta com credenciais do `.env` local, lista as atividades de um
    intervalo de datas (padrão: hoje), baixa o FIT original de cada uma que ainda não está no banco e passa pelo **mesmo
    caminho do upload de FIT da Meta 3** (identidade, esforços, clima, carga, tipo). Usa a biblioteca Python `garminconnect`
    (não oficial), testada localmente pelo Theo em 10/11: login, lista por data e FIT original funcionam. Sem mudança no
    modelo de dados (se precisar, volta para o Theo). Critério curto: idempotente; sem rede nos testes e no CI (cliente
    Garmin falso); credenciais e token só no `.env` ou em pasta local fora do git, nunca em log; uma tentativa de login por
    execução e erro do Garmin como mensagem clara; limitação registrada (biblioteca não oficial, pode quebrar quando o Garmin
    mudar o login; a API oficial continua sendo o caminho de produção e depende do CNPJ); nota do módulo e guia
    atualizados. Dona: duda-dados. Só local e só na conta do Angelo (decidido por ele em 10/11; ver "PRECISA DO ANGELO").
- **Quem:** caio-ciencia (ADR, pacote de fatos, checagens, oráculo, exemplos de tom), duda-dados (camada de LLM, banco,
  worker, API, cliente; a P14), lia-design (cartão), rafa-app (tela), nina-docs, bia-qa, Theo (ADR 0013 e adendo da ADR
  0004), Angelo (leitura dos exemplos de tom e o celular).
- **Fora:** motor de explicação com estimativa de quanto cada fator pesa (seção 4.3, passo 3: o pacote só põe os fatos lado a
  lado, sem afirmar causa); resumos semanal, quinzenal e mensal; envio em nome do professor e revisão de amostra pelo
  professor (Meta 10); aviso ou envio por WhatsApp ou e-mail; agente com pergunta livre (Meta 11); feedback sem check-in
  (decisão 5); feedback em áudio (o feedback é texto, decisão 6); sono, VFC, estado de treino, prontidão e treinos planejados
  do Garmin Connect (candidata sem número).
- **Resultado:** feita, com três itens não verificados. Com fixtures sintéticas e o provedor falso, a Bia conferiu o critério de pronto
  com `tests/test_e2e_meta9.py` (23 testes, um por item) e seguiu o [[produto/meta-9-como-rodar]] do zero com um Postgres descartável
  (#332 / PR #362). O bug achado (#361, texto do provedor falso reprovado pela `checagens_feedback@2`) foi corrigido no PR #363. A rodada
  com o provedor de verdade, só com fixtures e 40 s de pausa, gerou 4 textos, sem reprovação nem recusa por limite. `uv run pytest` com
  2374 verdes e 2 pulados; `npm test` com 249. **Não verificados:** o cartão na tela do app rodando (ninguém viu a tela; a extensão do
  navegador não estava conectada), o celular do Angelo (check-in da Meta 8 e cartão da Meta 9; a sessão não aconteceu) e a revisão da
  Lia sobre a tela pronta (o design-ok foi sobre capturas). Resultado completo em [[produto/metas/meta-9-feedback-automatico]].
- **Pendências que seguem:** a conferência do cartão e do check-in na tela rodando virou a P1 da Meta 10 (#369), no Chrome em tamanho
  de celular; o celular de verdade virou pendência conhecida, sem data (decisão do Angelo em 12/11); #364 (docs, Nina) fecha à parte.
- **Aprendido na Meta 9:** versão nova de checagem confere também o texto do provedor falso (os testes do worker injetavam uma checagem
  própria e não pegaram o #361; o e2e pegou); o `.env` é lido da raiz do repositório, e numa worktree ou em outro clone essa raiz muda
  (#354); o plano gratuito do provedor recusa por limite por minuto, daí `LLM_INTERVALO_S` e a parada no primeiro limite (#357); mudar a
  versão do prompt ou das checagens não desatualiza o que já está pronto (só com `--refazer`), e isso foi escrito antes de subir a
  versão; a rodada pequena com o provedor de verdade sobre fixtures achou a forma do texto que as fixtures não achavam, e deve vir logo
  depois da camada e do prompt; "A confirmar" com padrões funcionou pela quarta vez; passo que depende de pessoa (celular) ou de
  ferramenta (extensão do navegador) não pode ficar para a QA: vira issue própria na largada, com data marcada.

### Meta 10: sono, VFC e FC de repouso no contexto do treino (feita)
> **Feita em 16/11, com o celular de verdade não verificado:** código, QA (#378, PR #413), conferência local (#379, PR #411) e conferência
> visual no Chrome em 390 px com a Lia, sem bloqueantes (#369, PR #416, [[design/telas/conferencia-369]]). Proposta do Paulo na #333; o Angelo respondeu "ok para as nove" em 12/11, com uma
> mudança na pergunta 6 (celular). Issues #369 a #380; roteiro na #368. Paralela fora do critério: #367. Resultado completo em
> [[produto/metas/meta-10-recuperacao]].

- **Decisões do Angelo (12/11, "ok para as nove"):**
  1. tema da Meta 10 = recuperação (sono, VFC e FC de repouso no contexto do treino);
  2. guardar a recuperação diária da conta dele no banco local, **só** duração do sono, VFC noturna e FC de repouso, com a regra do dado
     de saúde da Meta 6 (só banco local, nunca em log, comando para apagar);
  3. fonte = a mesma biblioteca não oficial do `worker.buscar_garmin`, só no piloto local; a API oficial segue como caminho de produção;
  4. ao provedor de LLM vai só a comparação da noite anterior com o normal dele, nunca a série diária;
  5. no feedback, a recuperação fica lado a lado com o resultado, sem causa e sem conselho;
  6. **mudou:** ele **não** fará a sessão do celular agora e pediu que o Theo abra o app no Chrome simulando o celular. A P2 (sessão do
     celular) **saiu** do critério de pronto; a conferência visual no Chrome em tamanho de celular entrou na P1 (#369). O Theo adiantou a
     simulação em 12/11, e o resultado vai anexado na #369. O celular de verdade é pendência conhecida, sem data;
  7. caixa do professor = Meta 11 (esboço), levantando antes login, vínculo professor-atleta e consentimento;
  8. #213, #237 e #74 fora da Meta 10;
  9. treinos planejados do Garmin fora da Meta 10.
- **Por que esta e não outra** (como proposto na #333). O plano pede no feedback de cada treino "o que pesou (sono, calor, carga)" (seção 4.6) e põe sono, VFC e
  FC de repouso entre os fatores do motor de explicação (seção 4.3); a Garmin é a fonte principal justamente por trazer sono e VFC (seção
  3.1). Calor e carga já estão no pacote de fatos; sono e recuperação são o fator que falta. O Angelo mostrou interesse em 10/11, e o
  caminho até a conta dele já existe (`worker.buscar_garmin`, P14 da Meta 9). Fica no piloto local, com um atleta, sem conta nem serviço
  novo. As outras candidatas e por que vêm depois:
  - **Caixa do dia do professor** (o esboço antigo da Meta 10): pede login, vínculo professor-atleta e dado de outros atletas (LGPD,
    consentimento de cada um), decisões que são do Angelo e ainda não foram levantadas. Proposta: Meta 11, com essas perguntas feitas
    antes.
  - **Telas da carga, da linha de base e dos esforços**, com #213 e #237: úteis, mas não mudam o que o atleta aprende do treino; viram uma
    meta de telas depois.
  - **Treinos planejados do Garmin:** alimentam a semana-padrão e o motivo de falta; pedem outro modelo de dados. Candidata.
- **Objetivo:** o pacote de fatos ganha a recuperação da noite anterior ao treino (duração do sono, VFC noturna e FC de repouso),
  comparada com o normal do próprio atleta, e o feedback passa a pôr esse fato **lado a lado** com o resultado, sem afirmar causa.
- **Entrega visível:** o cartão "Feedback" com uma linha sobre a recuperação quando há dado ("Você dormiu 5 h 40 min, abaixo do seu
  normal de 7 h 10 min.", exemplo sintético); o comando que busca e grava a recuperação diária; e o cartão e o check-in conferidos na
  tela rodando, no Chrome em tamanho de celular.
- **Critério de pronto:**
  - conferência visual do cartão e do check-in no Chrome com tamanho de tela de celular, com a API real e o provedor falso, e revisão da
    Lia sobre a tela rodando; registrado que a simulação não é celular de verdade;
  - ADR 0014 aprovada pelo Theo antes da migração: o que se guarda, de onde vem, um registro por dia com versão, idempotência, regra do
    dado de saúde da Meta 6 (só banco local, nunca log, comando para apagar), o que entra no pacote e o que vai ao provedor; "A confirmar"
    com padrões;
  - a comparação com o normal (`recuperacao@1`) como função pura, com nota em `docs/metricas/` e oráculo sobre fixtures sintéticas
    escritas à mão (nunca resposta real gravada);
  - `fatos_treino@2` com a recuperação; prompt e checagens com versão nova e textos bons e ruins novos; a checagem real roda sobre o texto
    do provedor falso (aprendido na Meta 9);
  - testes e CI sem rede (cliente Garmin falso, provedor falso); a falta de dado de sono num dia nunca vira número inventado;
  - QA com fixtures num clone limpo, seguindo só o guia; conferência local com a conta do Angelo, com nada no repositório.
- **Issues e ordem** (cada uma até 1 dia; abertas em 12/11; o critério curto de cada uma está na própria issue):

  | Proposta | Issue | Título | Dono | Depende de | Situação |
  |---|---|---|---|---|---|
  | P1 | #369 | Conferência visual do check-in e do cartão de feedback no Chrome em tamanho de celular, com revisão da Lia (simulação adiantada pelo Theo em 12/11) | bia-qa com lia-design | nenhuma | feita (Lia, 16/11, sem bloqueantes; PR #416, [[design/telas/conferencia-369]]) |
  | P2 | (sem issue) | Sessão do celular com o Angelo: **saiu da meta** (decisão 6); celular de verdade é pendência conhecida, sem data | | | fora |
  | P3 | #370 | ADR 0014: recuperação diária (sono, VFC, FC de repouso) no contexto do treino | caio-ciencia com duda-dados (aprovação do Theo) | nenhuma | feita (PR #383, aceita em 12/11) |
  | P4 | #371 | Formato da recuperação, fixtures sintéticas e oráculo | duda-dados (formato) e caio-ciencia (oráculo) | #370 (adianta à mão) | feita (PR #385) |
  | P5 | #372 | Recuperação no banco (migração 0014), busca pelo Garmin Connect e comando para apagar | duda-dados | #370, #371 | feita (PR #388) |
  | P6 | #373 | `recuperacao@1`: noite anterior ao treino comparada com o normal do atleta | caio-ciencia | #370, #371 | feita (PR #387) |
  | P7 | #374 | `fatos_treino@2` com a recuperação e o adaptador do banco | caio-ciencia com duda-dados | #372, #373 | feita (PR #390) |
  | P8 | #375 | Prompt e checagens com a recuperação (`feedback_prompt@5`, `checagens_feedback@4`; a `@3` foi do #384 e o `feedback_prompt@4` é da #374) | caio-ciencia | #374 | feita (PR #391) |
  | P9 | #376 | Rodada pequena com o provedor de verdade, só fixtures | caio-ciencia (rodada local pelo Theo) | #375 | feita (PR #393) |
  | P10 | #377 | Documentação, guia `meta-10-como-rodar` e diário | nina-docs | #372, #375 | feita (PRs #389 e #392) |
  | P11 | #378 | QA de ponta a ponta com fixtures | bia-qa | #377 | feita (PR #413) |
  | P12 | #379 | Conferência local da recuperação com a conta do Angelo (nada no repositório) | caio-ciencia com duda-dados | #372, #374 | feita (PR #411) |
  | P13 | #380 | Resultado da meta e roteiro | paulo-planejador | #378 (e #369, #379) | esta |

  Entraram durante a meta, todas feitas: #386 (429 das rotas de dados do Garmin vira limite, PR #388); #394 (`feedback_prompt@6`,
  recuperação em duas linhas, decisão do Angelo de 13/11; PR #398); #395 (teto de saída e esforço de raciocínio pelo `.env`, teste de
  tamanho fiel; PR #399); #397 (`buscar_recuperacao --fixtures`, PR #400); #396 (mensagem própria do desatualizado pela noite, PR #401);
  #403 (frase do "aprendendo" e concordância de "FC", `@7`/`@5`; PR #404); #405 (estado do clima no texto, `@8`/`@6`; PR #406); #407
  (`--refazer` reconfere o texto mantido, PR #408); #409 (clima que chega depois desatualiza, migração 0015; PR #410); PRs #412 (diário de
  16/11) e #414 (guias sem head fixo). Em aberto, fora do caminho: #402 (frase quando só a versão do pacote desatualiza); #382 foi feita no PR #432 (botão
  Salvar do check-in).

  **Ordem:** #369 e #370 na largada, em paralelo; #371 adianta à mão enquanto a ADR não entra. Depois da ADR, #372 (Duda) e #373 (Caio)
  em paralelo; #374 é o encontro; #375 e #376 em sequência; #379 depois da #374; #377 e #378 fecham. Caminho crítico: #370 → #372 →
  #374 → #375 → #377 → #378 → #380. Sem tela nova: a recuperação aparece só no texto do cartão que já existe.
- **Paralela (fora do critério de pronto):** #367, pedida pelo Angelo: espaços no fim da linha e PSE sem rótulo repetida ("esforço 6
  (6)") no texto do feedback (caio-ciencia). Se mudar prompt ou checagens antes da #375, a #375 parte da versão dela.
- **Candidata, fora do critério de pronto (feita no PR #432, 16/11):** #382 (app, rafa-app com a Lia): no check-in, o botão Salvar sobe quando a dica some e
  "Nada a relatar" fica onde ele estava. Achada na simulação no Chrome em tamanho de celular; o resultado da simulação está em
  comentário na #369. Entra na Meta 10 só se a #369 pedir o ajuste.
- **Quem:** caio-ciencia (ADR, métrica, pacote, prompt, checagens; a #367), duda-dados (formato, banco, busca, adaptador), bia-qa
  (conferência visual, QA), lia-design (revisão da tela rodando), nina-docs, Theo (ADR 0014, a simulação no Chrome e a rodada local),
  Angelo (respostas e a conferência local). O rafa-app só entra se a #369 achar um ajuste na tela.
- **Fora:** sessão no celular de verdade (decisão 6); tela própria da recuperação; estágios do sono, estresse, prontidão e estado de treino do Garmin (métricas proprietárias, sem
  fórmula aberta); motor de explicação com o peso de cada fator ("provável", "possível"); treinos planejados do Garmin; a exportação
  Garmin como segunda fonte da recuperação, salvo se a ADR mostrar que sai de graça; alerta de recuperação baixa; outros atletas.
- **Resultado:** feita (16/11), com o celular de verdade não verificado. Com fixtures sintéticas, a Bia conferiu o critério com `tests/test_e2e_meta10.py` (23 testes, um por
  item) e seguiu o [[produto/meta-10-como-rodar]] do zero com um Postgres descartável (#378, PR #413); a única diferença do guia (head da
  migração) foi corrigida no PR #414. Conferência local feita (#379, PR #411): regras da `recuperacao@1` mantidas, três limitações
  genéricas em [[metricas/recuperacao]]. Versões no fechamento: `fatos_treino@2`, `recuperacao@1`, `feedback_prompt@8`,
  `checagens_feedback@6`; migrações até 0015. `uv run pytest` no `main` em `4773722`: 2682 verdes e 2 pulados. **#369: feita** (Lia, 16/11):
  conferência no Chrome sem bloqueantes, 34 capturas sintéticas ([[design/telas/conferencia-369]]); cobriu o passo do navegador da QA (cartão `pronto` com a linha
  da recuperação, texto de teste rotulado) e confirmou a #382, pior em 390 px. Limites: 390 px dentro de um iframe (altura 690), contraste só
  olhado; a simulação não é celular de verdade. **Não verificados:** celular de verdade (decisão 6, terceira meta seguida) e
  leitor de tela real. Resultado completo em [[produto/metas/meta-10-recuperacao]].
- **Pendências que seguem:** #402 como paralela da Meta 11 (a #382, confirmada na #369, foi feita no PR #432); celular de verdade (pergunta 10 da Meta
  11).
- **Aprendido na Meta 10:** cada dado que chega depois do feedback (check-in, noite, clima, versão do pacote) precisa de regra de
  desatualizado e de mensagem própria, decididas na ADR; cada versão nova do prompt pede a sua rodada com o provedor de verdade; o uso
  local com o dado real, antes da QA, achou defeitos de forma que o sintético não achou (#403, #405); o `--refazer` só pode manter texto
  que passe nas checagens de hoje (#407); teste e guia não fixam o head da migração (#414); o limite do plano gratuito do provedor (por
  minuto e por dia) é parte do desenho (teto de saída, pausa de 65 s; #395); conferência visual que depende da extensão do navegador
  ficou para o fim pela terceira meta (na Meta 10 a Lia a fez no fechamento), e a próxima tela precisa de capturas que rodem sem ela.

### Meta 11: caixa do dia do professor (feita)
> **Feita em 17/11, com quatro itens não verificados** (celular de verdade, leitor de tela real, login e aluno real; todos fora por decisão
> do Angelo). Proposta do Paulo na #380; o Angelo respondeu **"ok para as 10"** em 16/11, todas com a recomendação (inclusive a P1, com a
> dependência só de desenvolvimento, e o "sim" da pergunta 5, que trouxe a P14). Issues #418 a #431; roteiro na #417. Resultado completo em
> [[produto/metas/meta-11-caixa-do-dia]].

- **Decisões do Angelo (16/11, "ok para as 10"):**
  1. abrir as issues e começar a Meta 11 (P1 a P14; paralelas #382 e #402);
  2. **sem login** nesta meta: o professor do piloto local é fixo por configuração, como o atleta fixo da Meta 2; login, contas e controle
     de acesso vêm com a meta de deploy;
  3. **só atletas sintéticos** (fictícios, escritos à mão); nenhum dado de outro aluno real até o termo de consentimento, o contrato com a
     assessoria e a consulta de LGPD;
  4. atleta sem vínculo com o professor, ou com vínculo sem consentimento registrado, **nunca** aparece na caixa nem nos treinos dele; o
     texto do termo fica para a consulta jurídica;
  5. a conta dele ligada a um professor de teste **só no banco local**, para conferir os motivos, com nada no repositório (#431);
  6. `atencao@1` com **quatro motivos**: divergência da semana-padrão, fora do normal na linha de base, atalho "dor" no check-in, treino sem
     check-in perto do fim do prazo de 7 dias; recuperação abaixo do normal e motivo de falta ficam fora;
  7. o professor vê tipo, PSE, sensação, atalhos, feedback e a observação livre; a observação **nunca** vai ao provedor de LLM; rever na
     consulta de LGPD antes do primeiro aluno real;
  8. a correção do professor **vence** a sugestão e a semana-padrão e **não é desfeita** pela reimportação nem por versão nova da regra;
     confirmar sem mudar só marca o tipo como confirmado;
  9. fora: rascunho de devolutiva, revisão de amostra do feedback, feedback com o nome do professor, semana-padrão por grupo, ficha
     completa do aluno;
  10. **celular de verdade amarrado ao ensaio** com professor e atletas (plano, seção 9); sai da lista de cada meta. Até lá valem a
      conferência no Chrome em tamanho de celular e as capturas da #418.

- **Por que esta e não outra.** O MVP é vendido pela assessoria com o professor no meio (plano, seção 1), e a hipótese a validar é que o
  professor gasta menos tempo por aluno com o contexto pronto. Até aqui tudo é do atleta; a semana-padrão (Meta 7), o check-in (Meta 8),
  o feedback (Meta 9) e a recuperação (Meta 10) já produzem os motivos de "precisa de atenção" e o tipo sugerido que a caixa do dia
  (plano, seção 5.1) mostra. O banco já tem `professor`, `vinculo_professor_atleta` com `consentimento_em` e a origem `professor` no tipo
  (ADR 0001, ADR 0011). As outras candidatas:
  - **Telas da carga, da linha de base e dos esforços**, com #213 e #237: úteis, mas seguem sendo só do atleta; meta de telas depois.
  - **Login e deploy:** pedem conta e serviço novo (banco gerenciado, autenticação), dinheiro e a consulta LGPD; viram meta própria quando o
    Angelo decidir (pergunta 2).
  - **Resumo semanal:** precisa do planejado; segue candidata.
- **Objetivo:** o professor abre a **caixa do dia** e vê os seus alunos ordenados por "precisa de atenção", com o motivo em uma linha, e os
  treinos novos com o tipo sugerido, que ele **confirma ou corrige em lote**. No piloto local: sem login (professor fixo por configuração,
  como o atleta fixo da Meta 2), só atletas sintéticos com vínculo e consentimento registrados, e o Angelo só se ele quiser, no banco local.
- **Entrega visível:**
  - a tela "Caixa do dia" no app web (Expo web), com a lista de atenção e a confirmação em lote;
  - `GET` da caixa do dia de um professor e o `PUT` em lote do tipo, no OpenAPI, com o cliente regerado;
  - capturas da tela em 390x844 e em largura de computador, claro e escuro, geradas por um comando, sem a extensão do navegador.
- **Critério de pronto:**
  - ADR 0015 aprovada pelo Theo antes de qualquer migração: identidade do professor no piloto local, vínculo e consentimento como filtro,
    regra de atenção com versão, confirmação em lote (o que vence o quê), o que o professor vê, o que nunca sai do banco local; "A
    confirmar" com padrões; uma tabela de "o que muda a caixa e quando" (aprendido na Meta 10);
  - `atencao@1` como função pura, com nota em `docs/metricas/` e oráculo sobre fixtures sintéticas escritas à mão; cada motivo usa só o que
    o código já calcula (nenhum número novo) e não afirma causa;
  - atleta sem vínculo com o professor, ou com vínculo sem `consentimento_em`, **nunca** aparece na caixa nem nos treinos dele, com teste;
  - a correção do professor vence a sugestão e a semana-padrão e não é desfeita pela reimportação nem por versão nova da regra, com teste;
  - endpoints no OpenAPI, adendo da ADR 0004 e cliente regerado; tela com teste e revisão da Lia **sobre as capturas do comando e sobre a
    tela rodando**;
  - testes e CI sem rede; nada de dado de saúde em log;
  - QA com fixtures num clone limpo, seguindo só o guia; registrado que nada disso é login de verdade nem celular de verdade.
- **Issues e ordem** (cada uma até 1 dia; abertas em 16/11; o critério curto de cada uma está na própria issue):

  | Proposta | Issue | Título | Dono | Depende de | Situação |
  |---|---|---|---|---|---|
  | P1 | #418 | Capturas da tela web por comando (navegador sem janela, 390x844 e largura de computador, claro e escuro), sem depender da extensão; dependência só de desenvolvimento, sem conta (aprovação do Theo) | rafa-app com bia-qa | nenhuma | feita (PR #434) |
  | P2 | #419 | ADR 0015: caixa do dia do professor no piloto local | caio-ciencia com duda-dados (aprovação do Theo) | nenhuma | feita (PR #435, aceita em 16/11) |
  | P3 | #420 | Desenho da caixa do dia (lista de atenção, motivo em uma linha, confirmação em lote, estados vazio e de erro) | lia-design | #419 (adianta) | feita (PRs #437, #443, #446) |
  | P4 | #421 | Fixtures sintéticas (um professor, cerca de 6 atletas fictícios, um sem consentimento e um de outro professor) e oráculo de `atencao@1` à mão | caio-ciencia | #419 (adianta à mão) | feita (PR #438) |
  | P5 | #422 | `atencao@1`: motivos de "precisa de atenção" como função pura, com nota | caio-ciencia | #419, #421 | feita (PR #441; `atencao@2` no PR #457) |
  | P6 | #423 | Professor do piloto por configuração e filtro de vínculo e consentimento na API (migração só se a ADR pedir) | duda-dados | #419 | feita (PR #436, migração 0016) |
  | P7 | #424 | `GET` da caixa do dia, adendo da ADR 0004, cliente regerado | duda-dados | #422, #423 | feita (PRs #442, #445) |
  | P8 | #425 | `PUT` em lote do tipo de treino pelo professor (origem `professor`, não desfeita pela reimportação) | duda-dados | #423 | feita (PR #440) |
  | P9 | #426 | Tela da caixa do dia: lista de atenção | rafa-app (revisão da Lia) | #418, #420, #424 | feita (PR #444) |
  | P10 | #427 | Tela da caixa do dia: confirmação e correção em lote | rafa-app (revisão da Lia) | #425, #426 | feita (PR #447) |
  | P11 | #428 | Documentação, guia `meta-11-como-rodar` e diário | nina-docs | #424, #427 | feita (PR #448) |
  | P12 | #429 | QA de ponta a ponta com fixtures, com as capturas da P1 e a revisão da Lia na tela rodando | bia-qa com lia-design | #428 | feita (PR #450) |
  | P13 | #430 | Resultado da meta e roteiro | paulo-planejador | #429 (e #431) | esta |
  | P14 | #431 | Conferência local da caixa do dia com a conta do Angelo (nada no repositório; decisão 5) | caio-ciencia com duda-dados | #424 | feita (PR #456) |

  **Ordem:** #418 e #419 na largada, em paralelo (a #418 tira a conferência visual do fim da meta, aprendido nas Metas 8 a 10); #420 e
  #421 adiantam enquanto a ADR não entra. Depois da ADR, #422 (Caio) em paralelo com #423 e #425 (Duda); #424 é o encontro; #426 e #427 em
  sequência; #431 depois da #424, só no banco local. Caminho crítico: #419 → #423 → #424 → #426 → #427 → #428 → #429 → #430.

  Entraram durante a meta, todas feitas: #449 (`CORS_ORIGENS` no passo 7 do guia, achado da QA; PR #451); #452 (ajustes da revisão da Lia
  na tela rodando; PR #453); #454 (`atencao@2`: aviso de check-in numa linha por aluno, sem a modalidade `outra`, achado da conferência
  local; PR #457); #458 (o "hoje" e o prazo do check-in pela data local, com teste nas viradas do dia; PR #459); PR #439 (diário e
  [[00-inicio]] de 16/11). Em aberto, fora do fechamento: #455 (investigação da `linha_base`, perguntas ao Angelo) e #402.
- **Paralelas (fora do critério, sem dependência):** #382 (feita em 16/11, PR #432) e #402 (caio-ciencia; só a
  `mensagem`, sem estado novo).
- **Quem:** caio-ciencia (ADR, regra de atenção, oráculo; #402), duda-dados (identidade, filtro, API, lote), lia-design (desenho e revisão),
  rafa-app (capturas e tela; #382), nina-docs, bia-qa, Theo (ADR 0015, adendo da ADR 0004, a dependência da #418), Angelo (conferência
  local da #431).
- **Fora:** login e contas de verdade, deploy e banco gerenciado; dado de outro aluno real; ficha completa do aluno; rascunho de devolutiva
  e roteiros do manual; revisão de amostra do feedback pelo professor e feedback com o nome dele; semana-padrão por grupo; aviso por
  WhatsApp ou e-mail; painel da coordenação; alerta de recuperação baixa (Meta 10); motivo de falta; celular de verdade (decisão 10).
- **Resultado:** feita (17/11), com quatro itens não verificados. Com fixtures sintéticas, a Bia conferiu o critério com
  `tests/test_e2e_meta11.py` (24 testes, um por item; tirar a condição de consentimento derruba 9) e seguiu o [[produto/meta-11-como-rodar]]
  do zero (#429, PR #450); a única diferença do guia (`CORS_ORIGENS`) foi corrigida no PR #451. A Lia deu design-ok sobre a tela rodando,
  com um ajuste pequeno (PR #453). Conferência local feita (#431, PR #456): dois achados resolvidos na `atencao@2` (#454), um em
  investigação (#455). Fuso do "hoje" corrigido (#458). `uv run pytest` no `main` em `5074d20`: 2819 verdes e 2 pulados; `npm test` com 333.
  **Não verificados:** celular de verdade (amarrado ao ensaio, decisão 10), leitor de tela real, login (o `PROFESSOR_ID` não é
  autenticação) e aluno real. Resultado completo em [[produto/metas/meta-11-caixa-do-dia]].
- **Pendências que seguem:** #455 (respondida em 17/11; vira a `linha_base@3` na #462, Meta 12); #402 (paralela da Meta 12);
  `atencao@1` ainda em `apps/mobile/__fixtures__/caixaDoDia.ts` e `apps/mobile/scripts/api-falsa.mjs` (paralela da Meta 12, #471; as notas
  foram corrigidas na #430); comando para carregar os treinos sintéticos da Meta 11 (candidata).
- **Aprendido na Meta 11:** capturas por comando tiraram a conferência visual do fim da meta (a Lia revisou a tela rodando dentro da QA,
  pela primeira vez desde a Meta 8); um consumidor novo de uma métrica antiga mostra os pontos fracos dela (o "fora do normal" da
  `linha_base@2`, visível na caixa, levou à #455), então antes de mostrar uma métrica a um público novo vale conferi-la com o dado real;
  datas "de hoje" são do fuso do atleta e o teste fixa o relógio nas viradas (#458); versão nova de regra procura a string antiga também
  nas fixtures do app e na API falsa; quem escreve o guia roda o passo da tela (#449); "A confirmar" com padrões funcionou pela sexta meta.

### Meta 12: o treino inteiro na tela do atleta (feita)
> **Feita em 17/11, com cinco itens não verificados** (celular de verdade, leitor de tela real, login, aluno real e o feedback dos treinos
> reais ainda não refeito com a `@3`). Resultado completo em [[produto/metas/meta-12-treino-inteiro]]. As quatro perguntas do meio
> da meta (A a D) foram respondidas em 17/11 ("ok para as quatro", todas com a recomendação); a C virou a #510, paralela da Meta 13.
>
> Aberta em 17/11. Proposta do Paulo na #430; o Angelo respondeu **"ok para as seis"** em 17/11, todas com a recomendação, e
> respondeu às perguntas da #455 (respostas só no relatório local em `entregas/`). Issues #462 a #472 e #237; roteiro na #461. Nada na meta
> precisa de conta, serviço pago ou dado de outro aluno real.

- **Decisões do Angelo (17/11, "ok para as seis"):**
  1. abrir as issues e começar a Meta 12 (P1 a P10; paralelas `atencao@2` no app, #402 e a comparação para a Meta 13);
  2. **`linha_base@3` antes de o atleta ver o "fora do normal"** (respostas da #455): piso de dispersão por métrica (FC média 4 bpm, pace
     3%, carga por hora 5%), mínimo de 8 amostras do tipo, oráculo e testes com exemplo **sintético**; conferência local só em `entregas/`.
     A seção do normal usa a `@3`;
  3. **carga do treino e forma do dia** (condicionamento, fadiga e forma: CTL, ATL e TSB) **em números**, sempre como estimativa, com
     "aprendendo" quando faltar histórico; **sem gráfico** da série;
  4. **rótulo de transição corrigível pelo atleta** na tela, com a rota que já existe; a correção dele vence a sugestão (decisão de 06/11);
     o professor continua vendo o tipo pela caixa;
  5. **login e deploy do piloto = Meta 13**; durante a Meta 12, a Duda e o Theo comparam opções de hospedagem, login e custo só com
     documentação e preços públicos, **sem criar conta nem gastar** (#472); provedor, teto de custo, CNPJ e LGPD ficam com o Angelo;
  6. **agente do atleta = Meta 14**.

- **Por que esta e não outra.** O `GET` da atividade já devolve a linha de base (Meta 7), a carga (Meta 6) e os esforços e o rótulo de
  transição (Meta 5), mas a tela de um treino mostra só o check-in, a carga pela PSE e o feedback: o atleta não vê o que o app já calcula.
  O plano põe "o aluno tem que ganhar algo ao preencher" entre os princípios (seção 5.2) e a carga e o normal dele entre o que ele recebe
  (seção 1). É trabalho quase todo de tela, sem conta nem modelo de dados novo, e fecha a #237. As outras candidatas:
  - **Login e deploy do piloto:** é o que falta para o ensaio com professor e atletas (plano, seção 9, semana 11), mas pede conta, serviço
    pago, a consulta de LGPD e o CNPJ, decisões do Angelo. Meta 13 (decisão 5), com a comparação de opções preparada na Meta 12 (#472).
  - **`linha_base@3`** (#455): sozinha é pequena para uma meta; entra como a primeira issue desta (#462, decisão 2). A Meta 11 mostrou que
    mostrar uma métrica a um público novo expõe os pontos fracos dela: o atleta só vê o "fora do normal" depois da revisão.
  - **Agente do atleta:** depende do app no ar para o ensaio valer; Meta 14 (decisão 6).
  - **Resumo semanal:** precisa do planejado; segue candidata.
- **Objetivo:** na tela de um treino, o atleta vê, além do check-in e do feedback, **como o treino ficou em relação ao normal dele** (linha
  de base), **a carga do treino e a forma do dia** (como estimativa) e **os esforços** detectados, com o rótulo de transição que ele pode
  corrigir. O app não calcula nada: lê o que a API já devolve.
- **Entrega visível:** a tela do treino com três seções novas (normal, carga, esforços) no app web e no Expo, em 390 px e no computador,
  claro e escuro, com capturas pelo `npm run capturas`; distância e pace com a mesma aparência (#237).
- **Critério de pronto:**
  - spec da Lia antes da tela: o que cada seção mostra em cada estado (`aprendendo`, sem dado, fora do normal, sem carga, sem esforço),
    palavras sem alarme nem diagnóstico, carga como **estimativa**;
  - `linha_base@3` (piso por métrica e mínimo de 8 amostras) com nota, oráculo e testes sintéticos, e conferência local só em `entregas/`,
    antes de a seção da linha de base mostrar o "fora do normal" (decisão 2);
  - carga do treino e CTL, ATL e TSB em números, sem gráfico (decisão 3);
  - o app não calcula: só textos e números do `GET`; mudança de contrato, se houver, com adendo da ADR 0004 e cliente regerado;
  - cada seção com teste por estado e revisão da Lia sobre as capturas do comando e sobre a tela rodando, dentro da meta;
  - o rótulo de transição corrigido pelo atleta na tela usa a rota que já existe e vence a sugestão (decisão de 06/11);
  - QA com fixtures num clone limpo, seguindo só o guia; testes e CI sem rede.
- **Issues e ordem** (cada uma até 1 dia; abertas em 17/11; o critério curto de cada uma está na própria issue):

  | Proposta | Issue | Título | Dono | Depende de | Situação |
  |---|---|---|---|---|---|
  | P1 | #462 | `linha_base@3` com piso por métrica e mínimo de 8 amostras, nota, oráculo sintético e conferência local (o PR fecha a #455) | caio-ciencia | nenhuma (respostas da #455 dadas) | feita (PR #479; conferência local só em `entregas/`) |
  | P2 | #463 | Desenho da tela do treino com as seções normal, carga e esforços, e a decisão da #237 | lia-design | nenhuma | feita (PR #476) |
  | P3 | #464 | Contrato do `GET` da atividade para as três seções (textos prontos, estados, arredondamento da carga); adendo da ADR 0004 só se mudar | duda-dados (Theo no adendo) | #463 | feita (PR #480, adendo 12) |
  | P4 | #465 | Tela do treino: seção "comparado com o seu normal" | rafa-app (revisão da Lia) | #462, #463, #464 | feita (PR #485) |
  | P5 | #466 | Tela do treino: carga do treino e forma do dia, como estimativa | rafa-app (revisão da Lia) | #463, #464 | feita (PR #483) |
  | P6 | #467 | Tela do treino: esforços e rótulo de transição corrigível pelo atleta | rafa-app (revisão da Lia) | #463, #464 | feita (PR #484) |
  | P7 | #237 | Mesma aparência para distância e pace na tela do treino (issue existente) | rafa-app (revisão da Lia) | #463 (e #464 se o contrato mudar) | feita (PR #477) |
  | P8 | #468 | Documentação, guia `meta-12-como-rodar` e diário (quem escreve roda o passo da tela) | nina-docs | #465, #466, #467, #237 | feita (PR #486) |
  | P9 | #469 | QA de ponta a ponta com fixtures, capturas e revisão da Lia na tela rodando | bia-qa com lia-design | #468 | feita (PR #492) |
  | P10 | #470 | Resultado da meta e roteiro | paulo-planejador | #469 | esta |

  **Ordem:** na largada, em paralelo: #462 (Caio), #463 (Lia), #461 (este roteiro) e as paralelas #471 (Rafa, enquanto a spec não sai) e
  #472 (Duda, enquanto a spec não sai). #464 assim que a spec disser os campos; #237 pode adiantar com a spec. Depois o Rafa em sequência:
  #466, #467 e #465 (a do normal por último, para dar tempo à #462). Caminho crítico: #463 → #464 → #466 → #467 → #468 → #469 → #470;
  a #465 entra no caminho se a #462 atrasar.
- **Paralelas (fora do critério, sem dependência):** #471 (`atencao@2` nas fixtures do app e na API falsa; rafa-app; resto da #454); #402
  (caio-ciencia; só a `mensagem`); #472 (**comparação de opções de hospedagem, login e custo para a Meta 13**; duda-dados com o Theo; só
  leitura de documentação e preços públicos, **sem criar conta nem gastar**; decisão 5).
- **Quem:** lia-design (spec e revisão), rafa-app (telas, #237; #471), duda-dados (contrato; comparação para a Meta 13, #472),
  caio-ciencia (`linha_base@3`; #402), nina-docs, bia-qa, Theo (contrato e adendo, se houver; #472), Angelo (conferência local da #462, se
  ele quiser ver).
- **Fora:** gráfico da série de carga (CTL, ATL e TSB ao longo do tempo); tela da evolução e #213; motivo de falta; resumos; login e deploy
  (Meta 13); agente (Meta 14); alerta de qualquer tipo; celular de verdade (amarrado ao ensaio).
- **Entraram durante a meta, todas feitas:** #487 (textos da FC e de "aprendendo"; PRs #488, #489, #490; a #491 era duplicada); #471 e
  #402 (paralelas; PRs #474, #475 e #482); PRs #478 e #481 (grafo, diário e nota da Meta 11). Em aberto, fora do fechamento: #472.
- **Decisões do Theo na meta:** contrato do `GET` (PRs #476 e #480: textos prontos da carga, 1 casa com vírgula, TSB com U+2212,
  `transicao.editavel` e `forma_do_dia`); `409` no `PUT` e no `DELETE` da transição quando o treino não tem rótulo; `feedback_prompt@9` (só os
  números dos exemplos G02 e G04); pisos da `@3` também em `fc_melhor_tiro` e `melhor_pace`.
- **Resultado:** feita (17/11), com cinco itens não verificados. Com fixtures sintéticas, a Bia conferiu o critério com
  `tests/test_e2e_meta12.py` (16 testes) e seguiu o [[produto/meta-12-como-rodar]] do zero, com a **tela viva contra a API de um banco
  limpo** (#469, PR #492); a única correção do guia foi abrir a tela por `localhost`. A Lia deu design-ok na tela rodando. **Não
  verificados:** celular de verdade, leitor de tela real, login, aluno real e o feedback dos treinos reais refeito com a `@3`. Resultado
  completo em [[produto/metas/meta-12-treino-inteiro]].
- **Pendências que seguem:** #472 (comparação para a Meta 13; passou à meta-13 como entrada da P8, #504); perguntas A a D
  respondidas em 17/11 (A, B e D como já estão no `main`; a C na #510); sugestão da revisão de mostrar
  o esforço de 1000 m como "1 km" em vez de "1 · 1000 m" (a Duda decide); a seção "Não rodado" do guia, que ainda cita a tela viva como
  não rodada (a Nina acerta junto com este fechamento).
- **Aprendido na Meta 12:** spec com a lista de campos antes do contrato evitou retrabalho; a tela viva contra a API na QA pega o que a API
  falsa não pega (CORS, texto do backend) e fica como padrão; versão nova de métrica mexe em textos aprovados de outro módulo (exemplos do
  feedback), então quem sobe a versão procura também ali; texto pronto da API precisa de revisão de português como a tela tem revisão
  visual; perguntas do meio da meta seguem "a confirmar" com a recomendação valendo e não param o time.

### Meta 13: login e deploy do piloto (em curso)
> **Aberta em 17/11.** Proposta do Paulo na #470; o Angelo respondeu **"ok para as nove"** em 17/11, todas com a recomendação, menos a
> pergunta 6 (conta do provedor na pessoa física ou no CNPJ), que não tinha recomendação e **segue em aberto** (o Theo está perguntando).
> Issues #497 a #509 (P1 a P13), paralela #510 (pergunta C da Meta 12), #472 como entrada do provedor; roteiro na #496. Diferente das
> metas anteriores, esta **pede conta nova e gasto mensal**: a conta é criada pelo Angelo, nunca pelo time, e acima do teto o time para.

- **Decisões do Angelo (17/11, "ok para as nove"):**
  1. abrir as issues e começar a Meta 13 com P1 a P13;
  2. provedor **DigitalOcean**, com região e teto de custo mensal pela #472; **a conta é criada pelo Angelo**, nunca pelo time; acima do
     teto, o time para e pergunta;
  3. **e-mail e senha na própria API** (senha com hash, sem serviço novo);
  4. **sem domínio próprio** (endereço do provedor, com HTTPS) e **sem e-mail transacional** no piloto;
  5. CNPJ e consulta de LGPD são condição para o **primeiro aluno real**, não para pôr no ar: no ar só dado sintético e o do Angelo; o texto
     do termo de consentimento fica **provisório e marcado**;
  6. **em aberto:** conta do provedor na pessoa física ou no CNPJ (sem recomendação; o código não muda);
  7. o histórico real do Angelo no servidor **só depois do backup com restauração testada** (P9), na região escolhida, nada no repositório;
  8. **celular de verdade na QA** (Expo Go apontando para o piloto, dado sintético);
  9. o **ensaio com professor e atletas reais** fica para a meta seguinte.
- **Decisões da Meta 12 que entram aqui ("ok para as quatro", 17/11):** B, com o login **só o atleta dono corrige a transição** (P4); C, corrigir
  a transição deixa o feedback `desatualizado` pelo caminho do check-in editado (#510, paralela). A e D já valem no `main`.
- **Por que esta e não outra.** O ensaio com professor e atletas (plano, seção 9, semana 11) precisa do app no ar, com login e cada
  professor vendo só os próprios alunos. Três perguntas abertas (B, quem corrige sem login; o celular de verdade, amarrado ao ensaio; o
  aluno real) só fecham com isso. O agente (Meta 14) vale mais com o app no ar.
- **Objetivo:** o app no ar para o ensaio (1 professor e 10 atletas), com login de atleta e de professor, cada um vendo só o que é seu,
  consentimento registrado pelo próprio atleta, e o Angelo usando o app no celular dele contra o servidor.
- **Entrega visível:** endereço do piloto no provedor, com HTTPS; telas de entrar e sair; o atleta registra o consentimento para um
  professor; o professor vê só os seus alunos; o app no celular (Expo Go) apontando para o servidor; guia de implantação e de restauração
  do backup.
- **Critério de pronto:**
  - ADR 0016 aceita pelo Theo antes de qualquer migração ou conta: identidade e sessão por e-mail e senha, papéis, quem corrige o quê,
    consentimento pelo atleta, o que sai do `ATLETA_ID` e do `PROFESSOR_ID`, redefinição de senha sem e-mail, segredos, logs, backup e
    exclusão; "A confirmar" com padrões;
  - cada rota com teste de acesso: sem sessão = 401; recurso de outro atleta ou de aluno sem consentimento = 404, como na Meta 11; um teste
    que percorre o OpenAPI pega rota nova sem proteção;
  - nenhum dado de saúde em log no servidor; segredos só no provedor, fora do git;
  - deploy reproduzível a partir do repositório, com limite de 10 MB do upload no proxy e backup diário com uma restauração testada;
  - só dado sintético e o do Angelo no servidor (o dele depois da restauração testada); nenhum outro aluno real antes da consulta de LGPD;
  - QA no endereço do piloto seguindo só o guia, **com o celular de verdade** (Expo Go, dado sintético) e um leitor de tela uma vez.
- **Issues e ordem** (cada uma até 1 dia; abertas em 17/11; o critério curto de cada uma está na própria issue):

  | Proposta | Issue | Título | Dono | Depende de | Situação |
  |---|---|---|---|---|---|
  | P1 | #497 | ADR 0016: login, papéis, consentimento pelo atleta e deploy do piloto | duda-dados com caio-ciencia (aprovação do Theo) | nenhuma (região e preço pela #472, sem esperar) | aberta |
  | P2 | #498 | Desenho das telas de entrar, sair, consentimento e erro de sessão, com a lista de campos | lia-design | #497 (adianta) | aberta |
  | P3 | #499 | Contas e sessão na API, migração, no lugar do `ATLETA_ID` e do `PROFESSOR_ID`; comando do operador para conta e senha | duda-dados | #497 | aberta |
  | P4 | #500 | Controle de acesso em todas as rotas (401 e 404); transição só pelo atleta dono | duda-dados | #499 | aberta |
  | P5 | #501 | Consentimento registrado pelo atleta (termo provisório marcado) | duda-dados | #499 | aberta |
  | P6 | #502 | App: telas de entrar e sair, sessão guardada | rafa-app (revisão da Lia) | #498, #499 | aberta |
  | P7 | #503 | App: tela do consentimento | rafa-app (revisão da Lia) | #498, #501 | aberta |
  | P8 | #504 | Deploy reproduzível na DigitalOcean: imagens, banco gerenciado, HTTPS, segredos, upload de 10 MB, logs sem dado de saúde | duda-dados com o Theo | #497, #472; a subida, da conta criada pelo Angelo | aberta |
  | P9 | #505 | Backup diário com restauração testada; exclusão de conta | duda-dados | #504 (script e restauração local adiantam com a #499) | aberta |
  | P10 | #506 | Professor e atletas sintéticos no piloto; histórico do Angelo só depois da #505 | duda-dados | #504, #500 (e #505 para o dado real) | aberta |
  | P11 | #507 | Documentação: guia de implantação, `meta-13-como-rodar`, diário | nina-docs | #502, #503, #505 | aberta |
  | P12 | #508 | QA no endereço do piloto, com celular de verdade e leitor de tela | bia-qa com lia-design | #507, #506 | aberta |
  | P13 | #509 | Resultado da meta e roteiro | paulo-planejador | #508 | aberta |

  **Ordem:** na largada, em paralelo: #497 (Duda com o Caio), #498 (Lia, adianta com a ADR em revisão), #472 (Duda, região e preço para o
  teto do Angelo), #496 (este roteiro) e a paralela #510 (Duda, enquanto o Theo revisa a ADR; o Caio revisa o pacote de fatos). Depois da
  ADR: #499; em seguida #500 e #501; a preparação local da #504 (imagens, proxy, ensaio no Docker) e o script da #505 adiantam sem conta.
  O Rafa entra na #502 com a spec e a #499, depois a #503. **Caminho crítico:** #497 → #499 → #500 → #506 → #508 → #509, e pelo lado do
  servidor #497 → #504 → #505 → #506. **Risco:** a subida da #504 depende da conta criada pelo Angelo (e da pergunta 6, se ele quiser
  decidir o titular antes de criar). Se a conta não vier, P1 a P7 e a preparação da P8 e da P9 entram mesmo assim, e a meta fecha com
  "login local", sem o endereço, registrado como não verificado.
  **Carga da Duda:** ela é dona de P1, P3, P4, P5, P8, P9, P10, #472 e #510; é o gargalo da meta. Se atrasar, a #510 sai primeiro (é
  paralela) e o Theo pode assumir a preparação da P8.
- **Paralelas (fora do critério):** #510 (pergunta C da Meta 12; duda-dados, revisão do Caio no pacote de fatos); "1 km" no rótulo do
  esforço de 1000 m, se a Duda decidir mudar (sem issue).
- **Quem:** duda-dados (ADR, API, deploy, backup; #472, #510), caio-ciencia (ADR; revisão da #510), lia-design (spec e revisão),
  rafa-app (telas), nina-docs, bia-qa, Theo (ADR, deploy, segredos, `.github/`), Angelo (conta, teto, pergunta 6, celular na QA).
- **Fora:** aluno real além do Angelo e o ensaio com professor e atletas reais (decisão 9, meta seguinte); domínio próprio e e-mail
  transacional (decisão 4), portanto sem "esqueci a senha" por e-mail; link mágico e login social; API oficial da Garmin (depende do
  CNPJ); painel da coordenação; agente (Meta 14).

### Meta 14: agente do atleta, primeiras perguntas (depois da Meta 13; decisão 6 do Angelo em 17/11; era a Meta 12)
- **Objetivo:** atalhos para as perguntas mais comuns ("minha evolução nos tiros de 1 km"), respondidos por consultas estruturadas.
- **Quem:** caio-ciencia, duda-dados, rafa-app.
- **Fora:** pergunta livre sem catálogo.

### Candidatas sem número
- **Tela dos esforços e dos treinos de transição no app** (rafa-app, com a Lia): na Meta 12 (#467). A Meta 5 entregou só a API. A tela de
  um treino (#159, feita) já existe e é onde os esforços entram; depois ela recebe o check-in (Meta 8) e o feedback (Meta 9).
  As pendências do app (#213 e #237) podem vir junto.
- **Tela da carga no app** (rafa-app, com a Lia): a carga do treino e a forma do dia em números estão na Meta 12 (#466); o gráfico da série
  fica aqui (decisão 3 da Meta 12). A Meta 6 entregou a carga só na API e no gráfico em `entregas/`. Spec da Lia
  antes (CTL, ATL e TSB como estimativa, o aviso "aprendendo" e os dias sem carga), depois a tela; a API já devolve a série sem
  arredondar e a proposta é 1 casa na tela (Theo, #142).
- **Tela da linha de base no app** (rafa-app, com a Lia): na Meta 12 (#465). A Meta 7 entregou a `linha_base` só na API; o lugar natural é a tela
  de um treino, junto do tipo e da divergência.
- **Revisar o limite de "fora do normal" ou a métrica por tipo** (caio-ciencia): se a taxa de sessões "fora" ficar acima do
  esperado para um limite de `|z| >= 2,5`, rever o limite, o piso ou a métrica de cada tipo (`linha_base@3`). Achado da conferência
  local da Meta 11: com poucas amostras do tipo ou dispersão muito pequena, o `z` pode sair grande; o limite não mede relevância esportiva; investigação na #455; vira a `linha_base@3` na Meta 12 (#462, decisão 2).
- **Janela maior para tipo raro** (caio-ciencia): tipo feito a cada duas semanas ou menos segue em "aprendendo" com 12
  semanas e mínimo de 8; uma janela por tipo resolveria.
- **Esforço curto no `intervalado` sem série de 1 km** (caio-ciencia): hoje o treino compara só pela FC média e pela carga por
  hora; falta uma métrica do melhor esforço curto (depende da detecção, ADR 0008).
- **Motivo de falta** (depois da Meta 8): com a semana-padrão já dá para saber qual treino planejado não aconteceu.
- **Hífen sem quebra no estado vazio da tela da semana-padrão** (rafa-app): feita na #303 (PR #304), paralela da Meta 8.
- **App em celular:** nenhuma tela foi aberta num iOS ou Android até a Meta 9; estava no critério das Metas 8 (#301) e 9 (#332)
  e não foi feito. Em 12/11 o Angelo decidiu não fazer a sessão agora: **pendência conhecida, sem data**. No lugar, a simulação no
  Chrome em tamanho de celular (#369), que não substitui o aparelho (Expo Go, iOS, Android, leitor de tela). Desde 16/11 (decisão 10 da
  Meta 11), amarrado ao ensaio com professor e atletas; sai da lista de cada meta.
- **Cartão de feedback na tela rodando** (bia-qa, com a Lia): ninguém viu o cartão fora dos testes e das capturas na Meta 9. Feita na
  #369 da Meta 10 (PR #416), no Chrome em 390 px.
- **`--reconferir`** (caio-ciencia, com a Duda): reconferir os textos prontos com as checagens atuais sem chamar o provedor; ficou fora da
  #407 ([[diario/2026-11-16]]). Sem issue.
- **Feedback anterior à migração 0015 na fila pelo clima** (duda-dados): hoje só com `--refazer` (#409). Sem issue.
- **Comando para carregar os treinos sintéticos da Meta 11** (duda-dados): o guia usa um script próprio no passo 4 (achado do guia). Sem
  issue.
- **Capturas do check-in no tema escuro e nos estados de erro:** feita na Meta 9 (#334, PR #351).
- **Sono, VFC e FC de repouso do Garmin Connect:** viraram a Meta 10 (feita). **Estado de treino, prontidão, estágios do sono e
  estresse** (métricas proprietárias do Garmin) ficam aqui, sem issue. **Treinos planejados do Garmin Connect** (duda-dados, com o
  Caio): podem alimentar a semana-padrão e o motivo de falta; modelo de dados novo, sem issue.
- **Feedback: gatilho depois do `PUT` do check-in** (duda-dados): hoje o feedback fica `pendente` até alguém rodar o worker (aceito
  no piloto local, item 9 de "A confirmar" da ADR 0013).
- **Feedback: teto de tentativas para texto que sempre reprova** (Theo): hoje sem teto, contido só pelo limite por execução (item 4
  da ADR 0013).
- **Checagem de forma menos heurística** (caio-ciencia): a regra do verbo da `checagens_feedback@2` reprova verbo fora da lista e não
  pega a mesma conclusão com outras palavras.
- **Resumos semanal, quinzenal e mensal** (plano, seção 4.6): o semanal precisa do planejado; candidata depois da caixa do professor.
- **Login, contas e deploy** (duda-dados, com o Theo): virou a Meta 13 (decisão 5 da Meta 12).
- **`carga_pse@2` pelo tempo total** (caio-ciencia, com a Duda): a `carga_pse@1` usa o cronômetro; pediria gravar o tempo
  corrido na importação.
- **Série diária da carga pela PSE e comparação com a `carga@2`** (caio-ciencia): fora da Meta 8 por decisão do Angelo.
- **Lembrete do check-in** (WhatsApp ou e-mail) e **check-in semanal**: conta ou serviço novo, "PRECISA DO ANGELO" quando
  chegar a vez.
- **Abrir as fontes das ADRs 0008, 0011 e 0012** (caio-ciencia): Borg e Foster na 0012, ainda citadas sem conferir no texto.
- **#213** (rafa-app, revisão da Lia): acessibilidade e visual da tela de evolução. **#237** (rafa-app, com a Lia): mesma
  aparência para distância e pace na tela de um treino; pode tocar o contrato (ADR 0004). A #237 está na Meta 12 (P7); a
  #213 (tela da evolução) fica aqui.
- **#74** (vault do Graphify, `docs/_grafo/`): quando o Theo pedir o grafo de novo.
- **Calibração da detecção de esforços pelos recordes pessoais** (caio-ciencia): os recordes já estão no banco (#174, Meta 6);
  falta mapear a categoria da fonte para as faixas (`d1000`, `t20`...) e decidir a regra (`esforcos@2`).

---

## PRECISA DO ANGELO

Bloqueios e decisões que o time não toma sozinho. O time segue planejando em volta deles.

Resolvidos na Meta 1: exportação da Garmin em `dados-teste/garmin/`, Docker instalado, conferência do resultado
real, esteira fora do gráfico (#51) e as decisões da Meta 2 (sem deploy, atleta fixo por configuração, 5 bpm na FC,
stack Expo). A chave do provedor de LLM foi entregue e está no `.env` (fora do git).
- **Histórico público:** resolvido (Angelo, 03/11).
- **Atividades do resumo sem arquivo FIT: resolvido (Angelo, 03/11).** Não faltam arquivos. Ver [[modulos/ingestao-garmin]].
- **Open-Meteo:** o Angelo indicou a API gratuita para o desenvolvimento; o plano comercial continua em aberto para produção.
- **Meta 3: resolvido (Angelo, 03/11).** Guardar o FIT localmente; sem login, só local; 10 MB; qualquer
  modalidade, só corrida na série. Registrado na [[decisoes/0006-upload-de-fit]].
- **Meta 4: resolvido (Angelo, 03/11).** Posição de início arredondada a ~1 km, sem trajeto; ao Open-Meteo só posição
  arredondada e horário; passado relendo os arquivos locais; investigação da série de tiros em paralelo; "pode criar" para
  as issues da Meta 4 e para as propostas da Meta 3 (#118, #119, #120). Registrado na [[decisoes/0007-clima-da-atividade]].

- **Decisões de 04/11: resolvidas.**
  - **Clima do histórico real:** sim, nesta ordem: primeiro o `importar_garmin` sem rede por padrão (#132, feita: clima só com `--com-clima`), depois
    `--so-posicao` (local) e então uma rodada pequena de clima. A execução é local; os números ficam só em `entregas/`.
  - **Série de tiros:** sessões com 2 tiros entram; num treino misto, os tiros de 1 km do bloco principal contam; o valor
    principal é o melhor pace de tiro e o painel de FC mostra a FC do melhor tiro; treino de transição vira um rótulo
    sugerido e corrigível (Meta 5).
  - **Detecção de esforços** antes da carga, com a renumeração das metas; corrida por distância e ciclismo por tempo.
  - **Carga (Meta 6):** o limiar vem dos dados de saúde da exportação Garmin, sem estimar; atleta sem esses dados fica
    "sem carga" com motivo; pode guardar todos os dados de saúde (só no banco local); conferir a carga com o histórico real
    localmente, com os números só em `entregas/`.
  - **"Pode criar"** para as issues das Metas 5 e 6 e para as propostas da Meta 4.

- **Decisões de 06/11: resolvidas.** Parada de 15 s ou mais na corrida (30 s no ciclismo) corta a sequência do
  treino-chave (#165, ADR 0008 item 6); "ok para todas" as recomendações do treino de transição (ADR 0009). Ver
  [[diario/2026-11-06]].

- **Decisões de 07/11 e 08/11: resolvidas.** "Sim" às sete propostas da ADR 0010; `tiros_1km@6`, mínimo de 2 tiros mantido e
  velocidade habitual do ciclismo confirmada (#243); `carga@2` (#255). Ver [[diario/2026-11-07]], [[diario/2026-11-08]] e
  [[produto/metas/meta-6-carga-treino]].
- **Decisões da conferência local da Meta 5 (#169): todas respondidas em 07/11** (#243 e o multiesporte). Nenhuma pendente.

- **Meta 7: respondida em 09/11.** As cinco perguntas da #147:
  1. abrir as issues e começar: ok (abertas #260 a #273);
  2. início frio só com "ainda aprendendo", sem valores da literatura: ok;
  3. janela de 8 semanas, mínimo de 8 treinos do mesmo tipo: ok (no adendo 2 a janela virou 12 semanas, `linha_base@2`);
  4. **mudou:** "tudo bem o app sugerir", mas o tipo de treino vem do atleta ou do treinador, apontando os tipos por dia da
     semana (ex. genérico do plano: "terça intervalado, quinta fartlek, sábado longo", natação sem tipo). Virou a
     semana-padrão da Meta 7, com a regra (`leve`/`longo` na corrida) só como reserva para dia sem plano;
  5. limite "fora do normal" proposto na ADR 0011 e trazido para aprovação: ok.

- **Meta 7, seção "A confirmar" e adendo 2 da ADR 0011: resolvidos em 09/11.** "Ok para as sete" e "ok para as quatro"
  (`linha_base@2`); a semana-padrão do Angelo foi cadastrada no banco local para a conferência (#269). Ver
  [[diario/2026-11-09]].

- **Meta 8: respondida em 09/11 ("ok para as cinco").** Abrir e começar (issues #293 a #303); 3 toques com CR-10, sensação
  em 5 níveis, atalhos com texto livre e "nada a relatar"; `carga_pse@1` por atividade, sem série diária; o Angelo abre a
  tela de check-in no celular uma vez no fim da meta (#301); a observação segue a regra dos dados de saúde da Meta 6.

- **Meta 8, "A confirmar" da ADR 0012: resolvido em 10/11 ("ok para as cinco").** Prazo de 7 dias para registrar, editar e
  apagar sem prazo; toda atividade pede check-in, menos o pai e as trocas do multiesporte, um por parte; PSE, sensação e
  observação obrigatórias; "Carga pela PSE" em UA; sem login no piloto local. ADR aceita (PR #305). Ver
  [[diario/2026-11-10]] e [[produto/metas/meta-8-check-in]].

- **Meta 9 (feedback automático por treino): respondida em 10/11.** "Ok" aos oito padrões abaixo, sem mudança; no item 6 o
  Angelo esclareceu que o feedback é **por texto**, sem áudio (o título antigo do item dava a entender áudio; o item virou "Tom do texto").
  Issues #322 a #335. Os padrões aceitos:
   1. **Abrir as issues e começar a Meta 9** com a lista P1 a P13 acima (mais a P14, pedido dele). Feito: #322 a #335.
   2. **O que vai ao provedor de LLM** (serviço externo; a chave já está no `.env`). *Padrão:* só o pacote de fatos
      (números, unidades, estados e rótulos do tipo, do clima e da carga; PSE, sensação e os atalhos marcados); **nunca** o
      texto livre da observação, nome, data real, posição ou qualquer identificador; nada disso em log.
   3. **Dado real no provedor.** *Padrão:* na Meta 9, só fixtures sintéticas vão ao provedor de verdade, numa rodada pequena e
      local; gerar o feedback dos treinos reais do Angelo fica para um "sim" explícito dele, rodado localmente, sem nada no
      repositório. **O "sim" veio em 10/11** (item abaixo, com os limites).
   4. **Custo.** *Padrão:* só o plano gratuito do provedor atual (Groq), sem cartão, com limite de chamadas por execução do
      `worker.gerar_feedback`; qualquer plano pago ou provedor novo volta para ele.
   5. **Quando o feedback aparece.** *Padrão:* só depois do check-in (o feedback usa PSE e sensação, e isso dá motivo para
      fazer o check-in); treino sem check-in mostra "Faça o check-in para ver o feedback"; editar o check-in marca o feedback
      como desatualizado e ele é refeito.
   6. **Tom do texto.** O feedback é texto escrito, sem áudio (esclarecimento do Angelo em 10/11). *Padrão:* quem fala no
      texto é o app, sem o nome do professor até existir professor de verdade (Meta 10); frases curtas, em segunda pessoa, sem
      diagnóstico, culpa, promessa nem causa afirmada; o Angelo lê os 5 exemplos sintéticos da ADR 0013 antes do código.
   7. **Atalho "dor" no feedback.** *Padrão:* o feedback automático não comenta dor além de uma frase neutra ("Você registrou
      dor neste treino."), sem conselho; alerta sensível é do professor (plano, seção 4.4) e fica para a Meta 10.
   8. **Texto reprovado nas checagens.** *Padrão:* sem feedback naquele treino, com o motivo na API ("ainda não foi possível
      gerar o feedback"), e uma nova tentativa no próximo `worker.gerar_feedback`; nenhum texto de reserva escrito por regra
      nesta meta.
- **Meta 8, o celular (#301): decidido em 10/11.** O Angelo abre a tela de check-in no celular dele (Expo Go, rede de casa,
  dado sintético) na QA da Meta 9 (#332), junto com o cartão de feedback, numa só sessão. Informação, sem decisão: o caminho
  mínimo do check-in fecha em 3 toques; com atalho ou texto são 4 (Theo, 09/11).
- **Meta 9, os dois itens novos: respondidos em 10/11 ("sim para as duas").**
  1. **P14 (#335), buscar a atividade do dia no Garmin Connect: sim.** Paralela da Meta 9, fora do critério de pronto, **só no
     piloto local e só na conta dele**; credenciais e token só no `.env` ou em pasta local fora do git; biblioteca não oficial
     (`garminconnect`), aceita como limitação do piloto; a API oficial continua sendo o caminho de produção (depende do CNPJ,
     item 1 de "Em aberto"). Nada da conta dele entra no repositório.
  2. **Feedback dos treinos reais dele no provedor de LLM: sim, explícito** (responde à decisão 3 para os treinos reais). Os
     limites continuam valendo: rodado **só localmente**, por ele ou pelo Theo; ao provedor vai só o pacote de fatos (nunca o
     texto livre da observação, nome, data real, posição ou identificador); **nada do pacote, do texto gerado ou do resultado**
     entra no repositório, em issue, PR ou log; só o plano gratuito do Groq, com limite de chamadas por execução. A QA da meta
     (#332) não muda: fixtures sintéticas e provedor falso, mais a rodada pequena com fixtures no provedor de verdade.
- **Meta 10: respondida em 12/11 ("ok para as nove").** As nove perguntas da #333 valeram com as recomendações, menos a 6: o Angelo
  não fará a sessão do celular agora e pediu a simulação no Chrome pelo Theo (#369). Lista completa em "Meta 10", "Decisões do
  Angelo". Issues #368 a #380; paralela #367, aberta a pedido dele. "A confirmar" da ADR 0014: "ok para as cinco" (12/11); recuperação
  em duas linhas (13/11, #394).

- **Meta 11 (caixa do dia do professor): respondida em 16/11 ("ok para as 10").** As dez perguntas da #380 valeram com as recomendações,
  sem mudança; na 5 (sim) entrou a P14 (#431). Issues #417 a #431. Resumo em "Meta 11", "Decisões do Angelo"; as perguntas, como foram
  feitas:
   1. **Abrir as issues e começar a Meta 11** com a lista P1 a P13 da seção "Meta 11" (paralelas #382 e #402). *Recomendação:* sim. Alternativa: uma
      meta de telas do atleta (carga, linha de base, esforços, com #213 e #237).
   2. **Login.** *Recomendação:* sem login nesta meta; o professor do piloto local é fixo por configuração, como o atleta fixo da Meta 2.
      Login, contas e controle de acesso de verdade vêm com a meta de deploy, que pede conta e serviço novos e volta para você.
   3. **Dado de outros alunos.** *Recomendação:* na Meta 11, só atletas sintéticos (fictícios, escritos à mão). Nenhum dado de outro aluno
      real até existirem o termo de consentimento, o contrato com a assessoria e a consulta de LGPD (plano, seção 8).
   4. **Consentimento no código.** *Recomendação:* atleta sem vínculo com o professor, ou com vínculo sem consentimento registrado, nunca
      aparece na caixa nem nos treinos dele (o campo já existe no banco). O texto do termo fica para a consulta jurídica.
   5. **Você na caixa, só no banco local.** *Recomendação:* sim: vincular a sua conta a um professor de teste só no banco local, para
      conferir os motivos com treinos reais, com nada no repositório (como a #379). Se "não", a meta usa só os atletas sintéticos.
   6. **Motivos de "precisa de atenção" (`atencao@1`).** *Recomendação:* quatro, todos com o que o código já calcula: treino que diverge
      da semana-padrão; treino fora do normal na linha de base; atalho "dor" marcado no check-in; treino sem check-in perto do fim do prazo
      de 7 dias. **Fora:** recuperação abaixo do normal (não é alerta, Meta 10) e treino planejado que não aconteceu (motivo de falta,
      candidata).
   7. **O que o professor vê de cada treino.** *Recomendação:* o tipo, a PSE, a sensação, os atalhos, o feedback e a observação livre do
      check-in (o aluno escreve para o professor; enquanto só houver atletas sintéticos e você, não há terceiro exposto). A observação
      continua nunca indo ao provedor de LLM. Rever na consulta de LGPD, antes do primeiro aluno real.
   8. **Confirmação em lote.** *Recomendação:* a correção do professor vence a sugestão e a semana-padrão e não é desfeita pela
      reimportação nem por versão nova da regra; confirmar sem mudar só marca o tipo como confirmado.
   9. **Fora da Meta 11.** *Recomendação:* rascunho de devolutiva, revisão de amostra do feedback, feedback com o nome do professor,
      semana-padrão por grupo e ficha completa do aluno ficam para depois (a semana-padrão por aluno basta com poucos atletas).
   10. **Celular de verdade.** Três metas seguidas com o item aberto. *Recomendação:* tirar da lista de cada meta e amarrar ao ensaio com
       professor e atletas (plano, seção 9, semana 11), que precisa do app no aparelho; até lá vale a conferência no Chrome em tamanho de
       celular e as capturas da P1. Alternativa: marcar 15 minutos (Expo Go, rede de casa, dado sintético) numa data dentro da Meta 11.

- **Meta 11, "A confirmar" da ADR 0015: resolvido em 16/11 ("ok para as 7").**

- **Meta 12 (o treino inteiro na tela do atleta): respondida em 17/11 ("ok para as seis").** As seis perguntas da #430 valeram com as
  recomendações, sem mudança; a #455 também foi respondida ("sim para as quatro"; respostas só no relatório local, vira a #462). Issues #461
  a #472 e #237. Resumo em "Meta 12", "Decisões do Angelo"; as perguntas, como foram feitas:
   1. **Abrir as issues e começar a Meta 12** com a lista P1 a P10 da seção "Meta 12" (paralelas: `atencao@2` no app, #402 e a comparação
      para a Meta 13). *Recomendação:* sim. Alternativas: login e deploy agora (pede as decisões da pergunta 5 antes) ou o agente do atleta.
   2. **`linha_base@3` antes de o atleta ver o "fora do normal".** As perguntas da #455. *Recomendação:* responder na largada; com o "sim", a P1 entra e a seção do normal usa a
      `@3`; sem resposta, a P1 e a P4 saem da meta e o atleta não vê o "fora do normal" ainda (melhor do que mostrar uma leitura que a
      conferência local já mostrou frágil).
   3. **Carga na tela do atleta.** *Recomendação:* a carga do treino e a forma do dia (condicionamento, fadiga e forma, os nomes em
      português de CTL, ATL e TSB) em números, sempre como **estimativa**, com "aprendendo" quando faltar histórico; sem gráfico da série
      nesta meta. Alternativa: só a carga do treino.
   4. **Rótulo de transição corrigível pelo atleta na tela.** *Recomendação:* sim, com a rota que já existe; a correção do atleta vence a
      sugestão (decisão de 06/11); o professor continua vendo o tipo pela caixa.
   5. **Login e deploy como Meta 13.** *Recomendação:* sim; durante a Meta 12, a Duda e o Theo preparam uma comparação de opções de
      hospedagem, login e custo mensal só com documentação e preços públicos, **sem criar conta nem gastar**. Antes de planejar a Meta 13
      ficam com você: o provedor, o teto de custo mensal, o CNPJ e a consulta de LGPD (termo de consentimento e contrato com a assessoria).
   6. **Agente do atleta passa a Meta 14.** *Recomendação:* sim: o ensaio precisa do app no ar antes de o agente valer para mais alguém.

- **Meta 12, quatro perguntas do meio da meta: respondidas em 17/11 ("ok para as quatro").** Todas com a recomendação: A, B e D como já
  estão no `main` (B até o login; com o login, só o atleta dono corrige, #500); a C virou a #510, paralela da Meta 13. Detalhes em [[produto/metas/meta-12-treino-inteiro]].
   - **A. Forma do dia em "aprendendo".** *Recomendação:* esconder CTL, ATL e TSB e mostrar só o aviso. Alternativa: os números com o selo
     "ainda aprendendo".
   - **B. Quem corrige a transição sem login.** *Recomendação:* aceitar até a Meta 13; com o login, só o atleta dono do treino corrige.
   - **C. Feedback depois de corrigir a transição.** *Recomendação:* o feedback já gerado fica `desatualizado` e é refeito, como no
     check-in editado. Não implementado; com o "sim", issue pequena (paralela da Meta 13).
   - **D. Manter a `linha_base@3` ou buscar uma regra nova.** A conferência local mostrou redução pequena do "fora do normal" (números só
     em `entregas/`). *Recomendação:* manter até haver uso real para calibrar e rever depois do ensaio. Alternativa: investigar agora.

- **Meta 13 (login e deploy do piloto): respondida em 17/11 ("ok para as nove"), menos a 6, que segue em aberto.** As perguntas 1 a 5
  e 7 a 9 valeram com a recomendação; issues #496 a #510, #472 como entrada do provedor. Resumo em "Meta 13", "Decisões do Angelo". As
  perguntas, como foram feitas (nada criado nem contratado pelo time). A comparação da #472 é a entrada das perguntas 2 a 4. "Ok para todas" vale como "sim" a cada uma.
   1. **Abrir as issues e começar a Meta 13** com a lista P1 a P13 da seção "Meta 13". *Recomendação:* sim. Alternativa: uma meta curta
      sem conta (tela da evolução com a #213, ou a série da carga) enquanto as perguntas 2 a 5 amadurecem.
   2. **Provedor e teto de custo mensal.** Você cria a conta e cadastra o pagamento; o time nunca cria. *Recomendação:* a DigitalOcean
      (já é a produção prevista no AGENTS.md), com região e preço confirmados pela #472, e um teto mensal que você define; acima do teto, o
      time para e pergunta.
   3. **Como o atleta e o professor entram.** *Recomendação:* e-mail e senha na própria API (senha com hash, sem serviço novo). Link mágico
      ou login social pedem serviço de e-mail ou conta de terceiro, e voltam para você.
   4. **Domínio e e-mail.** *Recomendação:* sem domínio próprio no piloto (o endereço do provedor basta) e sem e-mail transacional; se
      quiser domínio, é custo anual seu.
   5. **CNPJ e LGPD antes do ar.** *Recomendação:* pôr no ar só com dado sintético e o seu; a consulta de LGPD (termo de consentimento,
      contrato com a assessoria, onde ficam os dados) e o CNPJ ficam como condição para o **primeiro aluno real**, não para o deploy. O
      texto do termo no app fica provisório e marcado até a consulta.
   6. **Conta no nome de quem.** A conta do provedor na pessoa física ou no CNPJ, quando houver. *Recomendação:* decisão sua; o código não
      muda.
   7. **O seu histórico real no servidor.** *Recomendação:* sim, só depois do backup testado (P9), na região escolhida, com nada no
      repositório; se "não", o servidor tem só dado sintético e você usa o celular com eles.
   8. **Celular de verdade na QA da Meta 13.** *Recomendação:* sim: 15 minutos com o Expo Go apontando para o piloto, dado sintético
      (fecha o item amarrado ao ensaio desde a Meta 11).
   9. **Ensaio com professor e atletas reais.** *Recomendação:* fica fora da Meta 13; vira a meta seguinte, depois do "sim" da pergunta 5
      (consulta de LGPD feita).

Pendentes com o Angelo (o time segue em volta delas):
1. **Celular de verdade** (Expo Go, iOS ou Android): na QA da Meta 13 (#508, decisão 8), cerca de 15 minutos com o Expo Go apontando
   para o piloto, dado sintético, quando a QA chegar.
2. **Antes de gerar o feedback dos treinos reais dele:** ler os termos do provedor sobre o uso dos dados para treinar modelos (item 10
   de "A confirmar" da ADR 0013). Segue não conferido por nós.
3. **Meta 13, pergunta 6 (em aberto):** a conta do provedor na pessoa física ou no CNPJ. Sem recomendação do time; o código não muda.
   O time segue com P1 a P7 e a preparação local da P8 e da P9.
4. **Meta 13, criar a conta na DigitalOcean e definir o teto mensal:** depois da #472 (região e preço). Só você cria a conta e cadastra
   o pagamento; é o que libera a subida da P8 (#504). Sem a conta, a meta fecha com "login local", sem o endereço.
5. **Feedback dos treinos reais com a `linha_base@3`:** refazer localmente quando você quiser (nada no repositório).
6. **Antes do primeiro aluno real:** termo de consentimento (o do app fica provisório e marcado até lá), contrato com a assessoria,
   consulta de LGPD e CNPJ (decisões 3, 4 e 7 da Meta 11; decisão 5 da Meta 13); login e deploy na Meta 13.

Em aberto:
1. **Próximas metas, sem pressa:** CNPJ e pedido da API da Garmin; pedido da API do TrainingPeaks com a assessoria;
   plano comercial do Open-Meteo para produção; limite de tamanho do upload no proxy, obrigatório na meta de deploy.
