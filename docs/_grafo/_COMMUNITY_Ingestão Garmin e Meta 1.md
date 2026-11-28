---
type: community
cohesion: 0.11
members: 25
---

# Ingestão Garmin e Meta 1

**Cohesion:** 0.11 - loosely connected
**Members:** 25 nodes

## Members
- [[ADR 0002 Segmento com intensidade da volta e versão da detecção]] - document - docs/decisoes/0002-segmento-intensidade-e-versao.md
- [[Antes de começar]] - document - docs/produto/meta-1-como-reproduzir.md
- [[Arquivos principais_5]] - document - docs/modulos/ingestao-garmin.md
- [[Buscar no Garmin Connect (piloto local, 335)]] - document - docs/modulos/ingestao-garmin.md
- [[Com Postgres]] - document - docs/produto/meta-1-como-reproduzir.md
- [[Como importar a exportação real]] - document - docs/modulos/ingestao-garmin.md
- [[Como testar_4]] - document - docs/modulos/ingestao-garmin.md
- [[Conferência com a exportação real (19)]] - document - docs/modulos/ingestao-garmin.md
- [[Depende de_4]] - document - docs/modulos/ingestao-garmin.md
- [[Diário 2026-10-31]] - document - docs/diario/2026-10-31.md
- [[Diário 2026-11-01]] - document - docs/diario/2026-11-01.md
- [[Entradas e saídas_5]] - document - docs/modulos/ingestao-garmin.md
- [[Importação no banco (`appingestaoimportacao.py`, CLI em `workerimportar_garmi]] - document - docs/modulos/ingestao-garmin.md
- [[Migração 0002]] - document - docs/decisoes/0002-segmento-intensidade-e-versao.md
- [[Notas da Meta 1]] - document - docs/produto/meta-1-como-reproduzir.md
- [[Para que serve_5]] - document - docs/modulos/ingestao-garmin.md
- [[Parser (`servicesapiappingestaogarmin`)]] - document - docs/modulos/ingestao-garmin.md
- [[Passo a passo (SQLite)]] - document - docs/produto/meta-1-como-reproduzir.md
- [[Sono, VFC e FC de repouso formato das respostas (Meta 10, 371)]] - document - docs/modulos/ingestao-garmin.md
- [[Testes]] - document - docs/produto/meta-1-como-reproduzir.md
- [[Upload de FIT (Meta 3, 94)]] - document - docs/modulos/ingestao-garmin.md
- [[Valores esperados]] - document - docs/produto/meta-1-como-reproduzir.md
- [[modulosingestao-garmin]] - document - docs/modulos/ingestao-garmin.md
- [[produtometa-1-como-reproduzir]] - document - docs/diario/2026-10-31.md
- [[produtometasmeta-1-tiros-1km]] - document - docs/diario/2026-11-01.md

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Ingesto_Garmin_e_Meta_1
SORT file.name ASC
```

## Connections to other communities
- 23 edges to [[_COMMUNITY_Roadmap e esforços]]
- 13 edges to [[_COMMUNITY_Contrato da tela e api-client]]
- 9 edges to [[_COMMUNITY_Worker, carga e Meta 12]]
- 6 edges to [[_COMMUNITY_Linha de base e fuso]]
- 6 edges to [[_COMMUNITY_Guias das metas 2 a 4]]
- 5 edges to [[_COMMUNITY_Modelo de dados e tabelas]]
- 5 edges to [[_COMMUNITY_API e versões de métricas]]
- 4 edges to [[_COMMUNITY_Banco e guias das metas 7 a 8]]
- 3 edges to [[_COMMUNITY_Recuperação e Meta 10]]
- 3 edges to [[_COMMUNITY_Gráfico dos tiros]]
- 2 edges to [[_COMMUNITY_Infra e papéis]]
- 2 edges to [[_COMMUNITY_Fatos do treino e feedback]]
- 2 edges to [[_COMMUNITY_Mapa e diários de novembro]]
- 1 edge to [[_COMMUNITY_Módulo clima]]
- 1 edge to [[_COMMUNITY_App, telas e design]]

## Top bridge nodes
- [[modulosingestao-garmin]] - degree 54, connects to 12 communities
- [[produtometa-1-como-reproduzir]] - degree 24, connects to 8 communities
- [[Diário 2026-10-31]] - degree 13, connects to 7 communities
- [[ADR 0002 Segmento com intensidade da volta e versão da detecção]] - degree 17, connects to 6 communities
- [[produtometasmeta-1-tiros-1km]] - degree 15, connects to 6 communities