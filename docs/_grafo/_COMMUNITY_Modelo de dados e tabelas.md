---
type: community
cohesion: 0.18
members: 13
---

# Modelo de dados e tabelas

**Cohesion:** 0.18 - loosely connected
**Members:** 13 nodes

## Members
- [[ADR 0001 Modelo de dados mínimo e estrutura do monorepo]] - document - docs/decisoes/0001-modelo-de-dados-minimo.md
- [[Coluna segmento.intensidade]] - document - docs/decisoes/0002-segmento-intensidade-e-versao.md
- [[Coluna segmento.versao_deteccao]] - document - docs/decisoes/0002-segmento-intensidade-e-versao.md
- [[Migrações Alembic]] - document - docs/decisoes/0001-modelo-de-dados-minimo.md
- [[Modelo completo do plano (alternativa rejeitada)]] - document - docs/decisoes/0001-modelo-de-dados-minimo.md
- [[Monorepo (appsmobile, servicesapi, servicesworker)]] - document - docs/decisoes/0001-modelo-de-dados-minimo.md
- [[Postgres 16]] - document - docs/decisoes/0001-modelo-de-dados-minimo.md
- [[Princípio guardar o dado bruto]] - document - docs/decisoes/0001-modelo-de-dados-minimo.md
- [[Princípio versionar cada métrica derivada]] - document - docs/decisoes/0002-segmento-intensidade-e-versao.md
- [[Regra tiros_1km (versões @1 a @4)]] - document - docs/decisoes/0005-serie-de-tiros-o-que-entra.md
- [[Tabela atividade]] - document - docs/decisoes/0001-modelo-de-dados-minimo.md
- [[Tabela segmento]] - document - docs/decisoes/0001-modelo-de-dados-minimo.md
- [[Theo (tech lead)]] - document - docs/decisoes/0001-modelo-de-dados-minimo.md

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Modelo_de_dados_e_tabelas
SORT file.name ASC
```

## Connections to other communities
- 5 edges to [[_COMMUNITY_Ingestão Garmin e Meta 1]]
- 5 edges to [[_COMMUNITY_Roadmap e esforços]]
- 3 edges to [[_COMMUNITY_Linha de base e fuso]]
- 3 edges to [[_COMMUNITY_Contrato da tela e api-client]]
- 1 edge to [[_COMMUNITY_Worker, carga e Meta 12]]
- 1 edge to [[_COMMUNITY_Glossário e ADRs 12 e 13]]
- 1 edge to [[_COMMUNITY_API e versões de métricas]]
- 1 edge to [[_COMMUNITY_Banco e guias das metas 7 a 8]]
- 1 edge to [[_COMMUNITY_Mapa, metas e templates]]

## Top bridge nodes
- [[ADR 0001 Modelo de dados mínimo e estrutura do monorepo]] - degree 24, connects to 9 communities
- [[Tabela atividade]] - degree 4, connects to 1 community
- [[Coluna segmento.versao_deteccao]] - degree 4, connects to 1 community
- [[Coluna segmento.intensidade]] - degree 2, connects to 1 community
- [[Princípio versionar cada métrica derivada]] - degree 2, connects to 1 community