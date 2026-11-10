---
tipo: mapa
status: em-uso
dono: nina
atualizado: 2026-11-10
---
# Treino Contexto: mapa do projeto

App de análise de treinos com contexto (corrida, natação, ciclismo) para atletas e assessorias.

## Onde estamos
- Meta 1 feita: tiros de 1 km a partir da exportação Garmin, com fixtures e dado real ([[produto/metas/meta-1-tiros-1km]])
- Meta 2 feita: evolução dos tiros no app, vista na web com as fixtures ([[produto/metas/meta-2-evolucao-tiros-app]])
- Meta 3 feita: upload de arquivo FIT pelo botão no app, vista na web com FIT sintéticos ([[produto/metas/meta-3-upload-fit]]). 
- Meta 4 feita: clima de cada atividade na API, visto com fixtures e a resposta gravada, sem rede ([[produto/metas/meta-4-clima-atividade]])
- Meta 5 feita: detecção de esforços na API e série de tiros pelos esforços, vistas com fixtures num clone limpo ([[produto/metas/meta-5-deteccao-esforcos]])
- Meta 6 feita: carga de treino (rTSS, hrTSS, CTL, ATL e TSB) na API, no gráfico e na conferência com o Garmin, vista com fixtures num clone limpo ([[produto/metas/meta-6-carga-treino]]). Próxima: Meta 7, linha de base pessoal e semana-padrão. Ver [[produto/roadmap]]
- Como reproduzir: [[produto/meta-1-como-reproduzir]] (Meta 1) e [[produto/meta-2-como-rodar]] (API e app), [[produto/meta-3-como-rodar]] (upload de FIT), [[produto/meta-4-como-rodar]] (clima), [[produto/meta-5-como-rodar]] (esforços, transição e multiesporte), [[produto/meta-6-como-rodar]] (carga de treino), [[produto/meta-7-como-rodar]] (semana-padrão, tipo de treino e linha de base)
- Meta 5, parte técnica no `main` (06/11): detecção de esforços ([[metricas/esforcos]]) no banco, no worker e na API, série de tiros pelos esforços (`tiros_1km@5`, [[metricas/tiros-1km]]), treino de transição ([[metricas/transicao]], [[decisoes/0009-treino-de-transicao]]), multiesporte e a tela de um treino no app. QA (#172) e resultado da meta (#173) feitos
- Time e papéis: [[time]]. A Lia (design) é dona de `docs/design/`; o guia visual, o tema do app e a tela com o melhor tiro estão no main (#192, #195 e #154)
- Meta 6, parte técnica no `main` (08/11): carga de treino (rTSS e hrTSS por volta, `carga@2`; CTL, ATL e TSB, `serie_carga@1`), dados de saúde da exportação Garmin no banco, `GET /atletas/{id}/carga`, gráfico e conferência com o Garmin ([[decisoes/0010-carga-de-treino]], [[metricas/carga-treino]], [[metricas/serie-carga]], [[metricas/conferencia-carga]], [[modulos/grafico-carga]]). QA (#146) e resultado da meta (#147) feitos
- Meta 7, em andamento (09/11): semana-padrão na API e na tela, tipo de treino pelo plano e pela regra de reserva, e linha de base pessoal (`linha_base@2`) no `GET` da atividade ([[decisoes/0011-linha-de-base-e-semana-padrao]], [[metricas/tipo-treino]], [[metricas/linha-base]], [[metricas/tipo-linha-base-oraculo]], [[design/telas/semana-padrao]]). Faltam a conferência local (#269), a QA (#271) e o resultado (#272) ([[produto/metas/meta-7-linha-de-base-semana-padrao]])
- Meta 8, em andamento (09/11): check-in pós-treino (PSE de 0 a 10, sensação, atalhos e "nada a relatar") e carga pela PSE (`carga_pse@1`, em UA). No `main`: API do check-in, `carga_pse`, `checkin_aberto` e `pse_sugerida` no `GET` da atividade, pendentes, fixtures e o desenho da tela ([[metricas/carga-pse]], [[metricas/carga-pse-oraculo]], [[design/telas/checkin]]). A tela no app está em revisão (#313). A [[decisoes/0012-check-in-pos-treino]] segue **proposta** (espera o Angelo)
- Último diário: [[diario/2026-11-09]] (anteriores: [[diario/2026-11-08]] e [[diario/2026-11-07]])

## Produto
- [[produto/plano-mvp-execucao]]: plano completo do MVP
- [[produto/roadmap]]: metas em ordem (mantido pelo Paulo)
- [[produto/meta-1-como-reproduzir]]: passo a passo da Meta 1 com as fixtures
- [[produto/meta-2-como-rodar]]: passo a passo de ponta a ponta da API e do app web com as fixtures
- [[produto/meta-3-como-rodar]]: upload de FIT com os FIT sintéticos, como forçar cada status (201, 200, 400, 404, 413, rede) e apagar os FIT
- [[produto/meta-4-como-rodar]]: clima da atividade com a resposta gravada, sem rede, e como forçar cada estado (ok, indoor, sem_posicao, pendente, falha)
- [[produto/meta-5-como-rodar]]: esforços, série `tiros_1km@5`, treino de transição e multiesporte com as fixtures, e o app com a API falsa
- [[produto/meta-6-como-rodar]]: carga de treino com as fixtures: saúde da exportação, `calcular_carga`, API, gráfico e conferência com o Garmin
- [[produto/meta-7-como-rodar]]: semana-padrão, tipo de treino e linha de base com as fixtures: Postgres próprio, API, tela, `reclassificar` e a `linha_base` no `GET` da atividade
- [[produto/meta-8-como-rodar]]: check-in pós-treino e carga pela PSE com as fixtures: Postgres próprio, API, tela de 3 toques, pendentes e `worker.apagar_checkin` (nota da meta: [[produto/metas/meta-8-check-in]]; ADR 0012 ainda proposta)
- [[produto/metas/meta-2-evolucao-tiros-app]]: nota da Meta 2
- [[produto/metas/meta-3-upload-fit]]: nota da Meta 3 (upload de FIT): resultado, não verificados, achados e propostas
- [[produto/metas/meta-4-clima-atividade]]: nota da Meta 4 (clima da atividade): resultado, não verificados, conclusão genérica da série de tiros, achados e propostas
- [[produto/metas/meta-5-deteccao-esforcos]]: nota da Meta 5 (detecção de esforços): resultado, não verificados, limitações, achados e pendências
- [[produto/metas/meta-6-carga-treino]]: nota da Meta 6 (carga de treino): resultado, decisões, não verificados, limitações, achados e pendências
- [[produto/metas/meta-7-linha-de-base-semana-padrao]]: nota da Meta 7 (linha de base e semana-padrão), em andamento

## Como o sistema funciona
- Módulos: [[modulos/api]], [[modulos/api-client]], [[modulos/banco]], [[modulos/worker]], [[modulos/mobile]], [[modulos/infra]], [[modulos/grafico-tiros]], [[modulos/ingestao-garmin]] (índice em [[modulos]])
- Métricas: pasta [[metricas/]]; [[metricas/tiros-1km]]; [[metricas/clima-oraculo]]; [[metricas/esforcos]]; [[metricas/esforcos-oraculo]]; [[metricas/transicao]]; [[metricas/carga-pse]]; [[metricas/carga-pse-oraculo]]
- Design (Lia): [[design/guia-visual]] (identidade, princípios e componentes), [[design/tokens]] (tokens do tema e contraste WCAG) e telas em [[design/telas/]] ([[design/telas/evolucao-tiros]], [[design/telas/treino]], [[design/telas/semana-padrao]], [[design/telas/checkin]])
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
  - [[decisoes/0012-check-in-pos-treino]]: check-in pós-treino e `carga_pse@1` (Meta 8), proposta; no PR #305

## Ciência e especialistas
- Artigos: pasta [[ciencia/artigos/]]
- Regras da base de conhecimento: pasta [[ciencia/regras/]]
- Entrevistas com treinadores: pasta [[entrevistas/]]

## Termos
- [[glossario]]
- [[time]]: quem faz o quê

## Mapa automático do código
- Pasta `_grafo/` (gerada pelo Graphify; não editar)
