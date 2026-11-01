---
tipo: mapa
status: em-uso
dono: nina
atualizado: 2026-10-31
---
# Treino Contexto: mapa do projeto

App de análise de treinos com contexto (corrida, natação, ciclismo) para atletas e assessorias.

## Onde estamos
- Meta atual: Meta 1, tiros de 1 km a partir da exportação Garmin (ver [[produto/roadmap]]). Código e docs prontos; faltam QA (#18) e dado real (#19)
- Como reproduzir: [[produto/meta-1-como-reproduzir]]
- Último diário: [[diario/2026-10-31]]

## Produto
- [[produto/plano-mvp-execucao]]: plano completo do MVP
- [[produto/roadmap]]: metas em ordem (mantido pelo Paulo)
- [[produto/meta-1-como-reproduzir]]: passo a passo da Meta 1 com as fixtures

## Como o sistema funciona
- Módulos: [[modulos/api]], [[modulos/banco]], [[modulos/worker]], [[modulos/mobile]], [[modulos/infra]], [[modulos/grafico-tiros]], [[modulos/ingestao-garmin]] (índice em [[modulos]])
- Métricas: pasta [[metricas/]]; [[metricas/tiros-1km]]
- Decisões de arquitetura: pasta [[decisoes/]]
  - [[decisoes/0001-modelo-de-dados-minimo]]: modelo de dados mínimo e monorepo
  - [[decisoes/0002-segmento-intensidade-e-versao]]: intensidade da volta e versão da detecção no segmento
  - [[decisoes/0003-fuso-da-atividade]]: fuso da atividade (`fuso_min`) e data local da sessão

## Ciência e especialistas
- Artigos: pasta [[ciencia/artigos/]]
- Regras da base de conhecimento: pasta [[ciencia/regras/]]
- Entrevistas com treinadores: pasta [[entrevistas/]]

## Termos
- [[glossario]]

## Mapa automático do código
- Pasta `_grafo/` (gerada pelo Graphify; não editar)
