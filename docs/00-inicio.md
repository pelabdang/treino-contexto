---
tipo: mapa
status: em-uso
dono: nina
atualizado: 2026-11-04
---
# Treino Contexto: mapa do projeto

App de análise de treinos com contexto (corrida, natação, ciclismo) para atletas e assessorias.

## Onde estamos
- Meta 1 feita: tiros de 1 km a partir da exportação Garmin, com fixtures e dado real ([[produto/metas/meta-1-tiros-1km]])
- Meta 2 feita: evolução dos tiros no app, vista na web com as fixtures ([[produto/metas/meta-2-evolucao-tiros-app]])
- Meta 3 feita: upload de arquivo FIT pelo botão no app, vista na web com FIT sintéticos ([[produto/metas/meta-3-upload-fit]]). 
- Meta 4 feita: clima de cada atividade na API, visto com fixtures e a resposta gravada, sem rede ([[produto/metas/meta-4-clima-atividade]]). Atual: Meta 5, detecção de esforços (desde 04/11); depois a Meta 6, carga de treino. Ver [[produto/roadmap]]
- Como reproduzir: [[produto/meta-1-como-reproduzir]] (Meta 1) e [[produto/meta-2-como-rodar]] (API e app), [[produto/meta-3-como-rodar]] (upload de FIT), [[produto/meta-4-como-rodar]] (clima)
- Meta 5 em andamento (04/11): ADR 0008 aceita; oráculo ([[metricas/esforcos-oraculo]]), blocos, esforços de corrida e de ciclismo ([[metricas/esforcos]]) prontos; faltam o treino-chave contínuo (#165), o banco e o worker (#166) e a visão de tiros
- Time e papéis: [[time]]. A Lia (design) é dona de `docs/design/`; o guia visual, o tema do app e a tela com o melhor tiro estão no main (#192, #195 e #154)
- Último diário: [[diario/2026-11-04]]

## Produto
- [[produto/plano-mvp-execucao]]: plano completo do MVP
- [[produto/roadmap]]: metas em ordem (mantido pelo Paulo)
- [[produto/meta-1-como-reproduzir]]: passo a passo da Meta 1 com as fixtures
- [[produto/meta-2-como-rodar]]: passo a passo de ponta a ponta da API e do app web com as fixtures
- [[produto/meta-3-como-rodar]]: upload de FIT com os FIT sintéticos, como forçar cada status (201, 200, 400, 404, 413, rede) e apagar os FIT
- [[produto/meta-4-como-rodar]]: clima da atividade com a resposta gravada, sem rede, e como forçar cada estado (ok, indoor, sem_posicao, pendente, falha)
- [[produto/metas/meta-2-evolucao-tiros-app]]: nota da Meta 2
- [[produto/metas/meta-3-upload-fit]]: nota da Meta 3 (upload de FIT): resultado, não verificados, achados e propostas
- [[produto/metas/meta-4-clima-atividade]]: nota da Meta 4 (clima da atividade): resultado, não verificados, conclusão genérica da série de tiros, achados e propostas

## Como o sistema funciona
- Módulos: [[modulos/api]], [[modulos/api-client]], [[modulos/banco]], [[modulos/worker]], [[modulos/mobile]], [[modulos/infra]], [[modulos/grafico-tiros]], [[modulos/ingestao-garmin]] (índice em [[modulos]])
- Métricas: pasta [[metricas/]]; [[metricas/tiros-1km]]; [[metricas/clima-oraculo]]; [[metricas/esforcos]]; [[metricas/esforcos-oraculo]]
- Design (Lia): [[design/guia-visual]] (identidade, princípios e componentes), [[design/tokens]] (tokens do tema e contraste WCAG) e telas em [[design/telas/]] ([[design/telas/evolucao-tiros]])
- Decisões de arquitetura: pasta [[decisoes/]] (a 0004 tem o adendo 1, melhor tiro; a 0006 tem o ajuste da #133)
  - [[decisoes/0001-modelo-de-dados-minimo]]: modelo de dados mínimo e monorepo
  - [[decisoes/0002-segmento-intensidade-e-versao]]: intensidade da volta e versão da detecção no segmento
  - [[decisoes/0003-fuso-da-atividade]]: fuso da atividade (`fuso_min`) e data local da sessão
  - [[decisoes/0004-contrato-tela-evolucao]]: contrato da tela de evolução dos tiros (Meta 2): pace só pela API, eixos, versão, erros e cliente gerado
  - [[decisoes/0005-serie-de-tiros-o-que-entra]]: o que entra na série de tiros e como a regra muda
  - [[decisoes/0006-upload-de-fit]]: upload de arquivo FIT (Meta 3): onde fica o leitor, identidade da atividade, guarda do arquivo, limites e erros
  - [[decisoes/0007-clima-da-atividade]]: clima de cada atividade (Meta 4): posição de início arredondada, tabela clima_atividade, API do Open-Meteo, falhas e idempotência
  - [[decisoes/0008-deteccao-de-esforcos]]: detecção de esforços (Meta 5): blocos, junção de laps, faixas, treino-chave e tabela `bloco_atividade`

## Ciência e especialistas
- Artigos: pasta [[ciencia/artigos/]]
- Regras da base de conhecimento: pasta [[ciencia/regras/]]
- Entrevistas com treinadores: pasta [[entrevistas/]]

## Termos
- [[glossario]]
- [[time]]: quem faz o quê

## Mapa automático do código
- Pasta `_grafo/` (gerada pelo Graphify; não editar)
