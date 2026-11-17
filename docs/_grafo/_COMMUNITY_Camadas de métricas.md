---
type: community
cohesion: 0.25
members: 8
---

# Camadas de métricas

**Cohesion:** 0.25 - loosely connected
**Members:** 8 nodes

## Members
- [[Altimetria]] - document - docs/produto/plano-mvp-execucao.md
- [[Camada 1 métricas determinísticas]] - document - docs/produto/plano-mvp-execucao.md
- [[Camada 2 linha de base pessoal]] - document - docs/produto/plano-mvp-execucao.md
- [[Carga (TSS, rTSS, hrTSS, CTLATLTSB)]] - document - docs/produto/plano-mvp-execucao.md
- [[Eficiência (EF) e desacoplamento PaHR]] - document - docs/produto/plano-mvp-execucao.md
- [[Início frio (valor populacional ponderado)]] - document - docs/produto/plano-mvp-execucao.md
- [[Métricas de engajamento]] - document - docs/produto/plano-mvp-execucao.md
- [[Pace ajustado (GAP, calor, vento)]] - document - docs/produto/plano-mvp-execucao.md

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Camadas_de_mtricas
SORT file.name ASC
```

## Connections to other communities
- 3 edges to [[_COMMUNITY_Arquitetura e plano do MVP]]
- 2 edges to [[_COMMUNITY_Caixa do dia e produto]]
- 2 edges to [[_COMMUNITY_Descoberta e conhecimento]]
- 1 edge to [[_COMMUNITY_Fundação de dados e fontes]]

## Top bridge nodes
- [[Camada 1 métricas determinísticas]] - degree 7, connects to 2 communities
- [[Camada 2 linha de base pessoal]] - degree 4, connects to 2 communities
- [[Pace ajustado (GAP, calor, vento)]] - degree 4, connects to 2 communities
- [[Início frio (valor populacional ponderado)]] - degree 2, connects to 1 community
- [[Métricas de engajamento]] - degree 2, connects to 1 community