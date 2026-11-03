---
tipo: roteiro
status: em-uso
dono: paulo
atualizado: 2026-11-03
links: [[produto/plano-mvp-execucao]], [[decisoes/0001-modelo-de-dados-minimo]], [[decisoes/0005-serie-de-tiros-o-que-entra]], [[produto/metas/meta-1-tiros-1km]], [[produto/metas/meta-2-evolucao-tiros-app]], [[produto/metas/meta-3-upload-fit]], [[decisoes/0004-contrato-tela-evolucao]], [[decisoes/0006-upload-de-fit]], [[decisoes/0003-fuso-da-atividade]], [[diario/2026-11-03]], [[00-inicio]]
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
| **4** | **Clima de cada atividade** | **próxima** (revisada; issues propostas, aguardando as decisões do Angelo) |
| 5 | Carga e linha de base pessoal | esboço |
| 6 | Check-in pós-treino | esboço |
| 7 | Feedback automático por treino | esboço |
| 8 | Caixa do dia do professor | esboço |
| 9 | Agente do atleta (primeiras perguntas) | esboço |

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

### Meta 4: clima de cada atividade (próxima, revisada em 03/11)
- **Objetivo:** cada atividade ao ar livre ganha temperatura, umidade, vento e sensação térmica na hora e no local do
  treino; esteira e piscina ficam marcadas "indoor", sem clima.
- **Entrega visível:** o clima de cada atividade na resposta da API (com a marca "indoor" ou o motivo de não ter
  clima) e um comando que preenche o clima das atividades já gravadas.
- **Critério de pronto (proposta):**
  - ADR do clima aprovada pelo Theo: tabela `clima_atividade` (plano MVP), de onde vem a posição, o que é indoor,
    qual API do Open-Meteo e o que fazer quando falta dado;
  - o leitor guarda a posição de início da atividade, vinda do FIT (exportação e upload) e do JSON da exportação,
    no formato que o Angelo decidir (ver "PRECISA DO ANGELO");
  - cliente Open-Meteo testado só com resposta gravada (nenhum teste chama a rede); clima de uma atividade sintética
    batendo com a resposta gravada na hora do treino;
  - preencher o clima é idempotente: rodar de novo não duplica nem chama a API para o que já tem clima;
  - esteira, piscina e atividade sem posição saem como "indoor" ou "sem posição", nunca com clima inventado;
  - funciona para atividade da exportação e do upload; QA com fixtures sintéticas com posição fictícia.
- **Conferido no código antes das issues (03/11):**
  - **Nenhuma atividade guarda posição hoje.** O modelo `atividade` não tem latitude nem longitude, e o leitor FIT
    (`services/api/app/ingestao/garmin/fit.py`) só lê `file_id`, `session` e `lap`; a posição de início do FIT
    (`session.start_position_lat/long`) e a do JSON da exportação não são lidas. Vale para os dois caminhos, não só
    para o upload.
  - **As fixtures sintéticas não têm posição:** `tests/test_fixtures_garmin.py` e `tests/test_fixtures_fit_upload.py`
    conferem que `position_lat/long` estão vazios. A Meta 4 precisa de fixtures com posição fictícia.
  - **O FIT do upload não traz horário local:** `fuso_min` fica vazio e a data cai no fallback `America/Sao_Paulo`
    ([[decisoes/0003-fuso-da-atividade]]). Para buscar o clima basta o `inicio` em UTC; o fuso só importa para
    exibir a hora local. Ler o horário local do FIT (mensagem `activity`) é melhoria possível, fora do critério.
  - **Dá para preencher o passado:** os FIT do upload estão guardados em `FIT_DIR` e a exportação segue em
    `dados-teste/`, então as atividades já gravadas podem ganhar posição reimportando ou relendo o arquivo, sem
    pedir nada ao atleta.
  - **"Indoor" já tem base:** o `subtipo` `esteira` vem do JSON e do FIT (`sub_sport`), e `piscina` também.
- **Ordem e donos** (proposta; as issues saem com o "pode criar" do Angelo e depois das decisões dele):
  1. ADR 0007, clima da atividade: tabela, posição, indoor, API do Open-Meteo (histórico ou previsão com dias
     passados, a conferir), falhas e limites de chamada (duda-dados, aprovação do Theo).
  2. Em paralelo: leitor guarda a posição de início (FIT e JSON), com migração (duda-dados); fixtures sintéticas com
     posição fictícia e o oráculo do clima a partir de uma resposta gravada (caio-ciencia).
  3. Cliente Open-Meteo com resposta gravada (duda-dados).
  4. Comando idempotente que preenche o clima e chamada no fim da importação e do upload (duda-dados).
  5. Clima na resposta da API e cliente regerado (duda-dados).
  6. Documentação e diário (nina-docs).
  7. QA de ponta a ponta com fixtures (bia-qa).
  8. Resultado da meta e roteiro (paulo-planejador).
  Em paralelo, se o Angelo escolher "junto": investigação da série de tiros com o dado real (caio-ciencia).
- **Quem:** duda-dados, caio-ciencia (oráculo; ajuste de pace por calor só como estimativa, fora do critério),
  nina-docs, bia-qa, Theo (ADR). rafa-app só se a proposta do `pt-BR` for aprovada.
- **Fora:** previsão do tempo; ajuste por vento; clima na tela do app; trajeto completo (só a posição de início);
  plano comercial do Open-Meteo (no desenvolvimento, a API gratuita, indicação do Angelo); deploy.

### Meta 5: carga e linha de base pessoal
- **Objetivo:** primeiras métricas derivadas versionadas (rTSS/hrTSS, CTL, ATL, TSB) e a linha de base por tipo de treino.
- **Entrega visível:** gráfico de carga em `entregas/` e endpoint.
- **Critério de pronto:** cada métrica com nota em `docs/metricas/` e teste calculado à mão; aviso "ainda aprendendo" com menos de 8 treinos do tipo.
- **Quem:** caio-ciencia, duda-dados, nina-docs.
- **Fora:** motor de explicação.

### Meta 6: check-in pós-treino
- **Objetivo:** o atleta registra PSE, sensação e observação em 3 toques.
- **Entrega visível:** tela de check-in no app e dado gravado.
- **Critério de pronto:** 3 toques; "nada a relatar" válido; ADR das tabelas de check-in.
- **Quem:** rafa-app, duda-dados, bia-qa.
- **Fora:** lembrete por WhatsApp, check-in semanal.

### Meta 7: feedback automático por treino
- **Objetivo:** 3 a 5 linhas por treino, a partir de um pacote de fatos calculado.
- **Entrega visível:** feedback na tela do treino.
- **Critério de pronto:** LLM só pela camada trocável (LiteLLM, `.env`); checagem automática de que todo número do texto está no pacote de fatos; lista de linguagem proibida.
- **Quem:** caio-ciencia (pacote de fatos), duda-dados, rafa-app.
- **Fora:** resumos semanal e mensal, envio em nome do professor.

### Meta 8: caixa do dia do professor
- **Objetivo:** o professor vê quem precisa de atenção e confirma o tipo de treino sugerido em lote.
- **Entrega visível:** tela web do professor com semana-padrão e confirmação em lote.
- **Quem:** rafa-app, duda-dados, caio-ciencia.
- **Fora:** rascunho de devolutiva, painel da coordenação.

### Meta 9: agente do atleta, primeiras perguntas
- **Objetivo:** atalhos para as perguntas mais comuns ("minha evolução nos tiros de 1 km"), respondidos por consultas estruturadas.
- **Quem:** caio-ciencia, duda-dados, rafa-app.
- **Fora:** pergunta livre sem catálogo.

---

## PRECISA DO ANGELO

Bloqueios e decisões que o time não toma sozinho. O time segue planejando em volta deles.

Resolvidos na Meta 1: exportação da Garmin em `dados-teste/garmin/`, Docker instalado, conferência do resultado
real, esteira fora do gráfico (#51) e as decisões da Meta 2 (sem deploy, atleta fixo por configuração, 5 bpm na FC,
stack Expo). A chave do provedor de LLM foi entregue e está no `.env` (fora do git).
- **Histórico público:** resolvido (Angelo, 03/11).
- **Atividades do resumo sem arquivo FIT: resolvido (Angelo, 03/11).** Não faltam arquivos. Ver [[modulos/ingestao-garmin]].
- **Open-Meteo:** o Angelo indicou a API gratuita para o desenvolvimento; o plano comercial continua em aberto para produção (Meta 4).
- **Meta 3: resolvido (Angelo, 03/11).** Guardar o FIT localmente; sem login, só local; 10 MB; qualquer
  modalidade, só corrida na série. Registrado na [[decisoes/0006-upload-de-fit]].

Em aberto:
1. **Ordem da investigação da série de tiros com o dado real:** antes da Meta 4 (meta curta só para isso) ou junto
   com ela (issue paralela do Caio). Proposta do time: junto, porque a Meta 4 é quase toda da Duda. Os dados reais
   ficam só em `entregas/`. Se a regra mudar, a série do atleta muda. Ver [[produto/metas/meta-3-upload-fit]].
2. **Meta 4, antes das issues (dado de aluno):**
   - guardar a posição de início das atividades? É dado pessoal: mostra onde o aluno treina e, muitas vezes, onde
     mora. Proposta do time: guardar só a posição de início **arredondada** (por exemplo 2 casas decimais, cerca de
     1 km), que basta para o clima, e nunca o trajeto;
   - enviar essa posição e o horário ao Open-Meteo (serviço de terceiro). Proposta: sim, arredondada, sem nenhum
     identificador do aluno na chamada;
   - preencher o clima das atividades antigas (relendo os FIT guardados e a exportação). Proposta: sim, pelo
     comando, só local.
3. **"Pode criar"** para as propostas da Meta 3 (app web em `pt-BR` e a investigação da série) e para as issues da
   Meta 4, depois do item 2.
4. **Próximas metas, sem pressa:** CNPJ e pedido da API da Garmin; pedido da API do TrainingPeaks com a assessoria;
   plano comercial do Open-Meteo para produção; limite de tamanho do upload no proxy, obrigatório na meta de deploy.
