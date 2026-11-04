---
type: community
cohesion: 0.23
members: 21
---

# Comunidade 4

**Cohesion:** 0.23 - loosely connected
**Members:** 21 nodes

## Members
- [[ADR 0003 fuso da atividade e data local]] - document - docs/decisoes/0003-fuso-da-atividade.md
- [[ADR 0006 Upload de arquivo FIT (Meta 3)]] - document - docs/decisoes/0006-upload-de-fit.md
- [[ADR 0007 Clima da atividade (Meta 4)]] - document - docs/decisoes/0007-clima-da-atividade.md
- [[Bia (QA)]] - document - docs/diario/2026-11-03.md
- [[Clima da atividade fixtures e oraculo]] - document - docs/metricas/clima-oraculo.md
- [[Coluna atividade.fuso_min]] - document - docs/decisoes/0003-fuso-da-atividade.md
- [[Comando worker.apagar_fit]] - document - docs/decisoes/0006-upload-de-fit.md
- [[Dado real fora do repositorio publico]] - document - docs/decisoes/0005-serie-de-tiros-o-que-entra.md
- [[Diario 2026-11-03]] - document - docs/diario/2026-11-03.md
- [[Estados do clima (ok, indoor, sem_posicao, pendente, falha)]] - document - docs/decisoes/0007-clima-da-atividade.md
- [[Guarda do FIT (FIT_DIR)]] - document - docs/decisoes/0006-upload-de-fit.md
- [[Modulo clima (Open-Meteo)]] - document - docs/modulos.md
- [[Módulo api-client]] - document - docs/00-inicio.md
- [[Objeto clima na resposta da API]] - document - docs/decisoes/0007-clima-da-atividade.md
- [[Open-Meteo Historical Weather API]] - document - docs/decisoes/0007-clima-da-atividade.md
- [[Paulo (planejador)]] - document - docs/diario/2026-11-03.md
- [[Posicao de inicio arredondada (~1 km)]] - document - docs/decisoes/0007-clima-da-atividade.md
- [[Regra de identidade dos 60 s]] - document - docs/decisoes/0006-upload-de-fit.md
- [[Tabela atividade]] - document - docs/decisoes/0001-modelo-de-dados-minimo.md
- [[Tabela clima_atividade]] - document - docs/decisoes/0007-clima-da-atividade.md
- [[Upload de arquivo FIT]] - document - docs/decisoes/0006-upload-de-fit.md

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Comunidade_4
SORT file.name ASC
```

## Connections to other communities
- 52 edges to [[_COMMUNITY_Comunidade 2]]
- 19 edges to [[_COMMUNITY_Comunidade 0]]
- 5 edges to [[_COMMUNITY_Comunidade 3]]
- 1 edge to [[_COMMUNITY_Comunidade 5]]
- 1 edge to [[_COMMUNITY_Comunidade 1]]

## Top bridge nodes
- [[ADR 0006 Upload de arquivo FIT (Meta 3)]] - degree 30, connects to 3 communities
- [[Diario 2026-11-03]] - degree 23, connects to 3 communities
- [[Módulo api-client]] - degree 11, connects to 3 communities
- [[ADR 0007 Clima da atividade (Meta 4)]] - degree 23, connects to 2 communities
- [[Tabela clima_atividade]] - degree 9, connects to 2 communities