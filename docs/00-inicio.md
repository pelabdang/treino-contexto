---
tipo: mapa
status: em-uso
dono: nina
atualizado: 2026-11-13
---
# Treino Contexto: mapa do projeto

App de análise de treinos com contexto (corrida, natação, ciclismo) para atletas e assessorias.

## Onde estamos
- Meta 1 feita: tiros de 1 km a partir da exportação Garmin, com fixtures e dado real ([[produto/metas/meta-1-tiros-1km]])
- Meta 2 feita: evolução dos tiros no app, vista na web com as fixtures ([[produto/metas/meta-2-evolucao-tiros-app]])
- Meta 3 feita: upload de arquivo FIT pelo botão no app, vista na web com FIT sintéticos ([[produto/metas/meta-3-upload-fit]]).
- Meta 4 feita: clima de cada atividade na API, visto com fixtures e a resposta gravada, sem rede ([[produto/metas/meta-4-clima-atividade]])
- Meta 5 feita: detecção de esforços na API e série de tiros pelos esforços, vistas com fixtures num clone limpo ([[produto/metas/meta-5-deteccao-esforcos]]). Parte técnica no `main` desde 06/11: esforços ([[metricas/esforcos]]) no banco, no worker e na API, série `tiros_1km@5` ([[metricas/tiros-1km]]), treino de transição ([[metricas/transicao]], [[decisoes/0009-treino-de-transicao]]), multiesporte e a tela de um treino no app. QA (#172) e resultado (#173) feitos
- Meta 6 feita: carga de treino (rTSS, hrTSS, CTL, ATL e TSB) na API, no gráfico e na conferência com o Garmin, vista com fixtures num clone limpo ([[produto/metas/meta-6-carga-treino]]). Parte técnica no `main` desde 08/11: rTSS e hrTSS por volta (`carga@2`), CTL, ATL e TSB (`serie_carga@1`), dados de saúde da exportação no banco e `GET /atletas/{id}/carga` ([[decisoes/0010-carga-de-treino]], [[metricas/carga-treino]], [[metricas/serie-carga]], [[metricas/conferencia-carga]], [[modulos/grafico-carga]]). QA (#146) e resultado (#147) feitos
- Como reproduzir: [[produto/meta-1-como-reproduzir]] (Meta 1) e [[produto/meta-2-como-rodar]] (API e app), [[produto/meta-3-como-rodar]] (upload de FIT), [[produto/meta-4-como-rodar]] (clima), [[produto/meta-5-como-rodar]] (esforços, transição e multiesporte), [[produto/meta-6-como-rodar]] (carga de treino), [[produto/meta-7-como-rodar]] (semana-padrão, tipo de treino e linha de base), [[produto/meta-8-como-rodar]] (check-in e carga pela PSE), [[produto/meta-9-como-rodar]] (feedback automático), [[produto/meta-10-como-rodar]] (recuperação da noite)
- Meta 7 feita (09/11): semana-padrão na API e na tela, tipo de treino pelo plano e pela regra de reserva, e linha de base pessoal (`linha_base@2`) no `GET` da atividade, vistas com fixtures num clone limpo ([[decisoes/0011-linha-de-base-e-semana-padrao]], [[metricas/tipo-treino]], [[metricas/linha-base]], [[metricas/tipo-linha-base-oraculo]], [[design/telas/semana-padrao]], [[produto/metas/meta-7-linha-de-base-semana-padrao]])
- Meta 8 feita (10/11): check-in pós-treino em 3 toques (PSE de 0 a 10, sensação, atalhos e "nada a relatar"), carga pela PSE (`carga_pse@1`, em UA), pendentes e a tela no app, vistos com fixtures num clone limpo ([[metricas/carga-pse]], [[metricas/carga-pse-oraculo]], [[design/telas/checkin]], [[produto/metas/meta-8-check-in]]). A [[decisoes/0012-check-in-pos-treino]] foi **aceita** em 10/11. Não verificado: a tela num celular de verdade. Ver [[produto/roadmap]]
- **Meta 9 feita (12/11): feedback automático por treino** ([[produto/metas/meta-9-feedback-automatico]]). Não verificados: o cartão em tela, o celular de verdade e a revisão da Lia. A conferência visual do cartão no Chrome virou a #369 da Meta 10; o celular segue com o Angelo. No `main`, com o provedor falso e fixtures: o pacote de fatos (`fatos_treino@1`), as checagens do texto (`checagens_feedback@3`), a camada de LLM trocável, a migração 0013 e o `worker.gerar_feedback`, o campo `feedback` no `GET` da atividade (cinco estados) e o cartão "Feedback" na tela do treino ([[decisoes/0013-feedback-automatico]], aceita em 10/11; [[metricas/fatos-treino]], [[metricas/fatos-treino-oraculo]], [[metricas/checagens-feedback]], [[modulos/camada-llm]], [[design/telas/feedback]], [[produto/meta-9-como-rodar]]). O feedback é **texto escrito**, gerado só pelo worker; texto reprovado nas checagens nunca chega ao app. Também entraram o `worker.buscar_garmin` (piloto local, biblioteca não oficial; [[modulos/ingestao-garmin]]), o prompt `feedback_prompt@3` (#356 e #367), a pausa entre chamadas e a parada no limite do provedor (#358), o `.env` lido sempre da raiz (#359) e o texto fixo do provedor falso que passa nas checagens (#363, bug #361). QA com fixtures feita (#332, PR #362: `tests/test_e2e_meta9.py`, 23 testes). Resultado da meta feito (#333, PR #366). Ver [[produto/roadmap]]
- **Meta 10 (atual, em curso desde 12/11): sono, VFC e FC de repouso no contexto do treino.** A [[decisoes/0014-recuperacao-diaria]] foi aceita em 12/11 (o Angelo disse "ok para as nove" e "ok para as cinco"). **Feito, no `main` (13/11):** a `recuperacao@1` (a noite anterior ao treino comparada com o normal do atleta; função pura, #373; [[metricas/recuperacao]], [[metricas/recuperacao-oraculo]]); a migração `0014` com a tabela `recuperacao_dia`, o `worker.buscar_recuperacao`, o `worker.apagar_recuperacao` e o 429 das rotas de dados tratado como limite (#372 e #386; [[modulos/banco]], [[modulos/worker]]); o `fatos_treino@2` com o bloco `recuperacao` e o adaptador do banco (#374; [[metricas/fatos-treino]]); o `feedback_prompt@5` e as `checagens_feedback@4` (#375; [[metricas/checagens-feedback]], [[modulos/camada-llm]]); o guia [[produto/meta-10-como-rodar]] e os diários (#377). O feedback é refeito quando a noite chega e a recuperação se apaga com um comando. **Falta:** a rodada com o provedor de verdade (#376), a QA (#378), a conferência local (#379) e o resultado da meta (#380). O formato das respostas do Garmin está em [[modulos/ingestao-garmin]]. A conferência visual no Chrome em tamanho de celular (#369) entrou na meta; o celular de verdade segue pendente, sem data. Nenhum texto com linha de recuperação foi visto ainda (o provedor falso não fala de sono). Issues #368 a #380 em [[produto/roadmap]]
- Time e papéis: [[time]]. A Lia (design) é dona de `docs/design/`; o guia visual, o tema do app e a tela com o melhor tiro estão no main (#192, #195 e #154)
- Último diário: [[diario/2026-11-13]] (anteriores: [[diario/2026-11-12]] e [[diario/2026-11-11]])

## Produto
- [[produto/plano-mvp-execucao]]: plano completo do MVP
- [[produto/roadmap]]: metas em ordem (mantido pelo Paulo)
- [[produto/metas/meta-1-tiros-1km]]: nota da Meta 1 (tiros de 1 km)
- [[produto/meta-1-como-reproduzir]]: passo a passo da Meta 1 com as fixtures
- [[produto/meta-2-como-rodar]]: passo a passo de ponta a ponta da API e do app web com as fixtures
- [[produto/meta-3-como-rodar]]: upload de FIT com os FIT sintéticos, como forçar cada status (201, 200, 400, 404, 413, rede) e apagar os FIT
- [[produto/meta-4-como-rodar]]: clima da atividade com a resposta gravada, sem rede, e como forçar cada estado (ok, indoor, sem_posicao, pendente, falha)
- [[produto/meta-5-como-rodar]]: esforços, série `tiros_1km@5`, treino de transição e multiesporte com as fixtures, e o app com a API falsa
- [[produto/meta-6-como-rodar]]: carga de treino com as fixtures: saúde da exportação, `calcular_carga`, API, gráfico e conferência com o Garmin
- [[produto/meta-7-como-rodar]]: semana-padrão, tipo de treino e linha de base com as fixtures: Postgres próprio, API, tela, `reclassificar` e a `linha_base` no `GET` da atividade
- [[produto/meta-8-como-rodar]]: check-in pós-treino e carga pela PSE com as fixtures: Postgres próprio, API, tela de 3 toques, pendentes e `worker.apagar_checkin` (nota da meta: [[produto/metas/meta-8-check-in]])
- [[produto/meta-9-como-rodar]]: feedback automático com as fixtures: Postgres próprio, migração 0013, `worker.gerar_feedback` com o provedor falso, os estados do `feedback` no `GET`, o cartão no app, `worker.apagar_checkin`, o provedor de verdade e o `worker.buscar_garmin` (opcionais)
- [[produto/meta-10-como-rodar]]: recuperação da noite com as fixtures: Postgres próprio, migração 0014, noites sintéticas, o bloco `recuperacao` do pacote, o feedback refeito quando a noite chega, a busca com o cliente Garmin falso e `worker.apagar_recuperacao`; a busca com conta real é opcional
- [[produto/metas/meta-2-evolucao-tiros-app]]: nota da Meta 2
- [[produto/metas/meta-3-upload-fit]]: nota da Meta 3 (upload de FIT): resultado, não verificados, achados e propostas
- [[produto/metas/meta-4-clima-atividade]]: nota da Meta 4 (clima da atividade): resultado, não verificados, conclusão genérica da série de tiros, achados e propostas
- [[produto/metas/meta-5-deteccao-esforcos]]: nota da Meta 5 (detecção de esforços): resultado, não verificados, limitações, achados e pendências
- [[produto/metas/meta-6-carga-treino]]: nota da Meta 6 (carga de treino): resultado, decisões, não verificados, limitações, achados e pendências
- [[produto/metas/meta-7-linha-de-base-semana-padrao]]: nota da Meta 7 (linha de base e semana-padrão): resultado, decisões, não verificados, limitações, achados e pendências
- [[produto/metas/meta-8-check-in]]: nota da Meta 8 (check-in pós-treino): resultado, decisões, não verificados, limitações, achados e pendências
- [[produto/metas/meta-9-feedback-automatico]]: nota da Meta 9 (feedback automático): resultado, não verificados, decisões e pendências

## Como o sistema funciona
- Módulos: [[modulos/api]], [[modulos/api-client]], [[modulos/banco]], [[modulos/worker]], [[modulos/mobile]], [[modulos/infra]], [[modulos/grafico-tiros]], [[modulos/ingestao-garmin]], [[modulos/camada-llm]], [[modulos/clima]], [[modulos/grafico-carga]] (índice em [[modulos]])
- Métricas: pasta [[metricas/]]; [[metricas/tiros-1km]]; [[metricas/clima-oraculo]]; [[metricas/esforcos]]; [[metricas/esforcos-oraculo]]; [[metricas/transicao]]; [[metricas/carga-treino]]; [[metricas/serie-carga]]; [[metricas/conferencia-carga]]; [[metricas/carga-oraculo]]; [[metricas/tipo-treino]]; [[metricas/linha-base]]; [[metricas/tipo-linha-base-oraculo]]; [[metricas/carga-pse]]; [[metricas/carga-pse-oraculo]]; [[metricas/fatos-treino]]; [[metricas/fatos-treino-oraculo]]; [[metricas/checagens-feedback]]
- Design (Lia): [[design/guia-visual]] (identidade, princípios e componentes), [[design/tokens]] (tokens do tema e contraste WCAG) e telas em [[design/telas/]] ([[design/telas/evolucao-tiros]], [[design/telas/treino]], [[design/telas/semana-padrao]], [[design/telas/checkin]], [[design/telas/feedback]])
- Decisões de arquitetura: pasta [[decisoes/]] (a 0004 tem os adendos 1 a 4: melhor tiro, campos prontos, distância e CORS; a 0006 tem o ajuste da #133)
  - [[decisoes/0001-modelo-de-dados-minimo]]: modelo de dados mínimo e monorepo
  - [[decisoes/0002-segmento-intensidade-e-versao]]: intensidade da volta e versão da detecção no segmento
  - [[decisoes/0003-fuso-da-atividade]]: fuso da atividade (`fuso_min`) e data local da sessão
  - [[decisoes/0004-contrato-tela-evolucao]]: contrato da tela de evolução dos tiros (Meta 2): pace só pela API, eixos, versão, erros e cliente gerado
  - [[decisoes/0005-serie-de-tiros-o-que-entra]]: o que entra na série de tiros e como a regra muda
  - [[decisoes/0006-upload-de-fit]]: upload de arquivo FIT (Meta 3): onde fica o leitor, identidade da atividade, guarda do arquivo, limites e erros
  - [[decisoes/0007-clima-da-atividade]]: clima de cada atividade (Meta 4): posição de início arredondada, tabela clima_atividade, API do Open-Meteo, falhas e idempotência
  - [[decisoes/0008-deteccao-de-esforcos]]: detecção de esforços (Meta 5): blocos, junção de laps, faixas, treino-chave e tabela `bloco_atividade`
  - [[decisoes/0009-treino-de-transicao]]: treino de transição (Meta 5): rótulo sugerido e corrigível, tabela `rotulo_transicao`, grupos e rotas
  - [[decisoes/0010-carga-de-treino]]: carga de treino (Meta 6): rTSS, hrTSS, CTL, ATL e TSB
  - [[decisoes/0011-linha-de-base-e-semana-padrao]]: linha de base pessoal, semana-padrão e tipo de treino (Meta 7)
  - [[decisoes/0012-check-in-pos-treino]]: check-in pós-treino e `carga_pse@1` (Meta 8), aceita em 10/11
  - [[decisoes/0013-feedback-automatico]]: feedback automático por treino (Meta 9): pacote de fatos, banco, camada de LLM, checagens e dado de saúde; aceita em 10/11
  - [[decisoes/0014-recuperacao-diaria]]: recuperação diária (Meta 10): tabela `recuperacao_dia`, `recuperacao@1`, `fatos_treino@2` e regras de linguagem; aceita em 12/11

## Ciência e especialistas
- Artigos: pasta [[ciencia/artigos/]]
- Regras da base de conhecimento: pasta [[ciencia/regras/]]
- Entrevistas com treinadores: pasta [[entrevistas/]]

## Termos
- [[glossario]]
- [[time]]: quem faz o quê

## Mapa automático do código
- Pasta `_grafo/` (gerada pelo Graphify; não editar)
