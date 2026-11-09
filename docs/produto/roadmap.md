---
tipo: roteiro
status: em-uso
dono: paulo
atualizado: 2026-11-09
links: [[produto/plano-mvp-execucao]], [[decisoes/0001-modelo-de-dados-minimo]], [[decisoes/0005-serie-de-tiros-o-que-entra]], [[produto/metas/meta-1-tiros-1km]], [[produto/metas/meta-2-evolucao-tiros-app]], [[produto/metas/meta-3-upload-fit]], [[decisoes/0004-contrato-tela-evolucao]], [[decisoes/0006-upload-de-fit]], [[decisoes/0003-fuso-da-atividade]], [[diario/2026-11-03]], [[00-inicio]], [[produto/metas/meta-4-clima-atividade]], [[decisoes/0007-clima-da-atividade]], [[produto/meta-4-como-rodar]], [[metricas/tiros-1km]], [[decisoes/0008-deteccao-de-esforcos]], [[diario/2026-11-04]], [[produto/metas/meta-5-deteccao-esforcos]], [[produto/meta-5-como-rodar]], [[decisoes/0009-treino-de-transicao]], [[metricas/esforcos]], [[metricas/transicao]], [[modulos/ingestao-garmin]], [[diario/2026-11-06]], [[produto/metas/meta-6-carga-treino]], [[produto/meta-6-como-rodar]], [[decisoes/0010-carga-de-treino]], [[metricas/carga-treino]], [[metricas/serie-carga]], [[metricas/conferencia-carga]], [[diario/2026-11-07]], [[diario/2026-11-08]], [[diario/2026-11-09]], [[produto/metas/meta-7-linha-de-base-semana-padrao]], [[produto/meta-7-como-rodar]], [[decisoes/0011-linha-de-base-e-semana-padrao]], [[metricas/linha-base]], [[metricas/tipo-treino]], [[design/tokens]]
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
| **8** | **Check-in pós-treino** | **atual** (issues #293 a #302; paralela #303) |
| 9 | Feedback automático por treino | esboço |
| 10 | Caixa do dia do professor | esboço |
| 11 | Agente do atleta (primeiras perguntas) | esboço |

Numeração: em 03/11 a linha de base virou meta própria e as metas seguintes andaram um número. Em 04/11 (decisão do
Angelo) a detecção de esforços entrou como Meta 5, antes da carga, e as seguintes andaram mais um número: carga = 6,
linha de base = 7, check-in = 8, feedback = 9, caixa do professor = 10, agente = 11. Notas antigas que citam "Meta 5"
para a carga falam da atual Meta 6; "Meta 8" para o feedback com LLM, da atual Meta 9.

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

### Meta 8: check-in pós-treino (atual)
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
- **Issues e ordem:**

  | # | Issue | Dono | Depende de | Situação |
  |---|---|---|---|---|
  | #293 | ADR 0012, check-in pós-treino (modelo, escalas, prazo, dado sensível, `carga_pse@1`) | caio-ciencia com duda-dados (aprovação do Theo) | nenhuma | aberta |
  | #294 | Fixtures sintéticas de check-in e oráculo (inclui `carga_pse@1`) | caio-ciencia | #293 (adianta à mão) | aberta |
  | #295 | Desenho da tela de check-in e da lista de treinos sem check-in | lia-design | #293 (pode rascunhar pelo plano) | aberta |
  | #296 | Check-in no banco (migração 0012), `PUT`/`GET`/`DELETE`, comando para apagar, cliente regerado | duda-dados | #293 | aberta |
  | #297 | `carga_pse@1`, carga pela PSE por atividade | caio-ciencia | #293 (oráculo #294) | aberta |
  | #298 | Check-in no `GET` da atividade e lista de treinos sem check-in | duda-dados | #296 (fixtures #294) | aberta |
  | #299 | Tela de check-in no app | rafa-app (revisão da Lia) | #295, #296, #298 | aberta |
  | #300 | Documentação, guia `meta-8-como-rodar` e diário | nina-docs | #298, #297, #299 | aberta |
  | #301 | QA de ponta a ponta com fixtures e o celular (o Angelo abre a tela uma vez) | bia-qa | #300 | aberta |
  | #302 | Resultado da meta e roteiro | paulo-planejador | #301 | aberta |

  **Ordem:** #293 na largada (Caio, com a Duda no modelo); #294 e #295 adiantam em paralelo. Depois da ADR, #296 (Duda) e
  #297 (Caio) em paralelo; #298 depois da #296; #299 é o encontro (precisa da #295, da #296 e da #298). #300, #301 e #302 no
  fechamento. Caminho crítico: #293 → #296 → #298 → #299 → #300 → #301 → #302. Não há conferência com o histórico real: o
  check-in é dado novo. A coluna "Situação" só muda no fechamento.
- **Paralela pequena (fora do critério de pronto):** #303, hífen sem quebra em "semana-padrão" no estado vazio da tela
  da semana-padrão (rafa-app, sem dependência), já que o Rafa mexe no app nesta meta.
- **Quem:** caio-ciencia (ADR, escalas, carga pela PSE, oráculo), duda-dados (banco, API, cliente, comando para apagar),
  lia-design (desenho), rafa-app (tela), nina-docs, bia-qa, Theo (ADR 0012 e adendo da ADR 0004), Angelo (celular, no fim).
- **Fora:** lembrete por WhatsApp ou e-mail (conta ou serviço novo, "PRECISA DO ANGELO" quando chegar a vez); check-in
  semanal; motivo de falta para o treino planejado que não aconteceu (a semana-padrão já permite saber o que faltou; candidata);
  equipamento e zona no check-in; série diária e CTL/ATL pela PSE; o check-in no motor de explicação e no feedback (Meta 9); o
  professor vendo o check-in (Meta 10).

### Meta 9: feedback automático por treino
- **Objetivo:** 3 a 5 linhas por treino, a partir de um pacote de fatos calculado.
- **Entrega visível:** feedback na tela do treino.
- **Critério de pronto:** LLM só pela camada trocável (LiteLLM, `.env`); checagem automática de que todo número do texto está no pacote de fatos; lista de linguagem proibida.
- **Quem:** caio-ciencia (pacote de fatos), duda-dados, rafa-app.
- **Fora:** resumos semanal e mensal, envio em nome do professor.

### Meta 10: caixa do dia do professor
- **Objetivo:** o professor vê quem precisa de atenção e confirma o tipo de treino sugerido em lote.
- **Entrega visível:** tela web do professor com confirmação em lote e as atividades que divergem da semana-padrão. A
  semana-padrão por atleta entra na Meta 7 (09/11); aqui ela ganha o professor de verdade (login, vínculo) e, se o Angelo
  quiser, o cadastro por grupo de atletas.
- **Quem:** rafa-app, duda-dados, caio-ciencia.
- **Fora:** rascunho de devolutiva, painel da coordenação.

### Meta 11: agente do atleta, primeiras perguntas
- **Objetivo:** atalhos para as perguntas mais comuns ("minha evolução nos tiros de 1 km"), respondidos por consultas estruturadas.
- **Quem:** caio-ciencia, duda-dados, rafa-app.
- **Fora:** pergunta livre sem catálogo.

### Candidatas sem número
- **Tela dos esforços e dos treinos de transição no app** (rafa-app, com a Lia): a Meta 5 entregou só a API. A tela de
  um treino (#159, feita) já existe e é onde os esforços entram; depois ela recebe o check-in (Meta 8) e o feedback (Meta 9).
  As pendências do app (#213 e #237) podem vir junto.
- **Tela da carga no app** (rafa-app, com a Lia): a Meta 6 entregou a carga só na API e no gráfico em `entregas/`. Spec da Lia
  antes (CTL, ATL e TSB como estimativa, o aviso "aprendendo" e os dias sem carga), depois a tela; a API já devolve a série sem
  arredondar e a proposta é 1 casa na tela (Theo, #142).
- **Tela da linha de base no app** (rafa-app, com a Lia): a Meta 7 entregou a `linha_base` só na API; o lugar natural é a tela
  de um treino, junto do tipo e da divergência.
- **Revisar o limite de "fora do normal" ou a métrica por tipo** (caio-ciencia): se a taxa de sessões "fora" ficar acima do
  esperado para um limite de `|z| >= 2,5`, rever o limite, o piso ou a métrica de cada tipo (`linha_base@3`).
- **Janela maior para tipo raro** (caio-ciencia): tipo feito a cada duas semanas ou menos segue em "aprendendo" com 12
  semanas e mínimo de 8; uma janela por tipo resolveria.
- **Esforço curto no `intervalado` sem série de 1 km** (caio-ciencia): hoje o treino compara só pela FC média e pela carga por
  hora; falta uma métrica do melhor esforço curto (depende da detecção, ADR 0008).
- **Motivo de falta** (Meta 8 ou depois): com a semana-padrão já dá para saber qual treino planejado não aconteceu.
- **Hífen sem quebra no estado vazio da tela da semana-padrão** (rafa-app): virou a #303, paralela da Meta 8.
- **App em celular:** nenhuma tela foi aberta num iOS ou Android até a Meta 7; entrou no critério da Meta 8 (#301).
- **#213** (rafa-app, revisão da Lia): acessibilidade e visual da tela de evolução. **#237** (rafa-app, com a Lia): mesma
  aparência para distância e pace na tela de um treino; pode tocar o contrato (ADR 0004). As duas vão com a tela dos esforços,
  da carga ou da linha de base.
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

Em aberto:
1. **Meta 8, o celular (#301):** o Angelo abre a tela de check-in no celular dele (Expo Go, rede local, dado sintético) uma
   vez no fim da meta, como combinado.
2. **Próximas metas, sem pressa:** CNPJ e pedido da API da Garmin; pedido da API do TrainingPeaks com a assessoria;
   plano comercial do Open-Meteo para produção; limite de tamanho do upload no proxy, obrigatório na meta de deploy.
