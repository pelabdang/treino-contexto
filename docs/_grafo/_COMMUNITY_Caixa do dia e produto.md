---
type: community
cohesion: 0.16
members: 15
---

# Caixa do dia e produto

**Cohesion:** 0.16 - loosely connected
**Members:** 15 nodes

## Members
- [[Caixa do dia (quem precisa de atenção)]] - document - docs/produto/plano-mvp-execucao.md
- [[Cancelamento  desconexão do aluno]] - document - docs/produto/plano-mvp-execucao.md
- [[Checagem automática de números]] - document - docs/produto/plano-mvp-execucao.md
- [[Classificação do tipo de treino pelo professor]] - document - docs/produto/plano-mvp-execucao.md
- [[Consulta estruturada do agente]] - document - docs/produto/plano-mvp-execucao.md
- [[Hipótese do MVP (contexto pronto reduz cancelamento)]] - document - docs/produto/plano-mvp-execucao.md
- [[Medição da inteligência (precisão, utilidade, alertas)]] - document - docs/produto/plano-mvp-execucao.md
- [[Modelo de dados (núcleo)]] - document - docs/produto/plano-mvp-execucao.md
- [[Princípio guardar dado bruto e versionar métricas]] - document - docs/produto/plano-mvp-execucao.md
- [[Segmento (zona e equipamento)]] - document - docs/produto/plano-mvp-execucao.md
- [[Semana-padrão]] - document - docs/produto/plano-mvp-execucao.md
- [[Sinal  alerta de atenção]] - document - docs/produto/plano-mvp-execucao.md
- [[Storage de objetos (S3, Parquet)]] - document - docs/produto/plano-mvp-execucao.md
- [[metrica_derivada (versionada)]] - document - docs/produto/plano-mvp-execucao.md
- [[serie_atividade (séries por segundo)]] - document - docs/produto/plano-mvp-execucao.md

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Caixa_do_dia_e_produto
SORT file.name ASC
```

## Connections to other communities
- 3 edges to [[_COMMUNITY_Pessoas, parceiros e decisões]]
- 3 edges to [[_COMMUNITY_Agente do atleta]]
- 3 edges to [[_COMMUNITY_Cronograma e validação]]
- 2 edges to [[_COMMUNITY_Fundação de dados e fontes]]
- 2 edges to [[_COMMUNITY_Arquitetura e plano do MVP]]
- 2 edges to [[_COMMUNITY_Camadas de métricas]]

## Top bridge nodes
- [[Modelo de dados (núcleo)]] - degree 8, connects to 2 communities
- [[Hipótese do MVP (contexto pronto reduz cancelamento)]] - degree 4, connects to 2 communities
- [[Checagem automática de números]] - degree 3, connects to 2 communities
- [[Sinal  alerta de atenção]] - degree 5, connects to 1 community
- [[serie_atividade (séries por segundo)]] - degree 4, connects to 1 community