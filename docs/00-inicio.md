---
tipo: mapa
status: em-uso
dono: nina
atualizado: 2026-11-03
---
# Treino Contexto: mapa do projeto

App de análise de treinos com contexto (corrida, natação, ciclismo) para atletas e assessorias.

## Onde estamos
- Meta 1 feita: tiros de 1 km a partir da exportação Garmin, com fixtures e dado real ([[produto/metas/meta-1-tiros-1km]])
- Próxima: Meta 2, evolução dos tiros no app (ver [[produto/roadmap]])
- Como reproduzir: [[produto/meta-1-como-reproduzir]]
- Último diário: [[diario/2026-11-03]]

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
  - [[decisoes/0005-serie-de-tiros-o-que-entra]]: o que entra na série de tiros e como a regra muda (0004 reservada ao contrato da Meta 2)

## Ciência e especialistas
- Artigos: pasta [[ciencia/artigos/]]
- Regras da base de conhecimento: pasta [[ciencia/regras/]]
- Entrevistas com treinadores: pasta [[entrevistas/]]

## Termos
- [[glossario]]

## Mapa automático do código
- Pasta `_grafo/` (gerada pelo Graphify; não editar)
