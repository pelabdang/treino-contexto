---
type: community
cohesion: 0.17
members: 19
---

# Linha de base e fuso

**Cohesion:** 0.17 - loosely connected
**Members:** 19 nodes

## Members
- [[ADR 0003 Fuso da atividade e data local da sessão]] - document - docs/decisoes/0003-fuso-da-atividade.md
- [[ADR 0011 Linha de base pessoal, semana-padrão e tipo de treino]] - document - docs/decisoes/0011-linha-de-base-e-semana-padrao.md
- [[ADR 0015 Caixa do dia do professor no piloto local (identidade, vínculo, `atencao@1` e correção do tipo)]] - document - docs/decisoes/0015-caixa-do-dia-do-professor.md
- [[Caio (papel)]] - document - docs/decisoes/0008-deteccao-de-esforcos.md
- [[Coluna atividade.fuso_min]] - document - docs/decisoes/0003-fuso-da-atividade.md
- [[Data local da sessão]] - document - docs/decisoes/0003-fuso-da-atividade.md
- [[Migração 0003]] - document - docs/decisoes/0003-fuso-da-atividade.md
- [[Selo normal por treino (`normal_treino@1`)]] - document - docs/metricas/normal-treino.md
- [[Semana-padrão]] - document - docs/decisoes/0011-linha-de-base-e-semana-padrao.md
- [[Versão carga@2_2]] - document - docs/metricas/linha-base.md
- [[Versão linha_base@3_3]] - document - docs/metricas/linha-base.md
- [[Versão linha_base@3_4]] - document - docs/metricas/normal-treino.md
- [[Versão normal_treino@1]] - document - docs/metricas/normal-treino.md
- [[Versão tipo_treino@1_1]] - document - docs/metricas/tipo-treino.md
- [[atencao@2 (caixa do dia)]] - document - docs/decisoes/0015-caixa-do-dia-do-professor.md
- [[linha_base@3]] - document - docs/decisoes/0011-linha-de-base-e-semana-padrao.md
- [[metricaslinha-base]] - document - docs/metricas/linha-base.md
- [[metricastipo-treino]] - document - docs/diario/2026-11-09.md
- [[tipo_treino@1]] - document - docs/decisoes/0011-linha-de-base-e-semana-padrao.md

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Linha_de_base_e_fuso
SORT file.name ASC
```

## Connections to other communities
- 23 edges to [[_COMMUNITY_Roadmap e esforços]]
- 19 edges to [[_COMMUNITY_Banco e guias das metas 7 a 8]]
- 17 edges to [[_COMMUNITY_Glossário e ADRs 12 e 13]]
- 15 edges to [[_COMMUNITY_App, telas e design]]
- 14 edges to [[_COMMUNITY_Worker, carga e Meta 12]]
- 11 edges to [[_COMMUNITY_Recuperação e Meta 10]]
- 8 edges to [[_COMMUNITY_Contrato da tela e api-client]]
- 6 edges to [[_COMMUNITY_Ingestão Garmin e Meta 1]]
- 6 edges to [[_COMMUNITY_API e versões de métricas]]
- 5 edges to [[_COMMUNITY_Evolução e ferramentas do chat]]
- 4 edges to [[_COMMUNITY_Meta 11 caixa do dia]]
- 3 edges to [[_COMMUNITY_Modelo de dados e tabelas]]
- 3 edges to [[_COMMUNITY_Fatos do treino e feedback]]
- 2 edges to [[_COMMUNITY_Deploy da Meta 13 e plano do MVP]]
- 2 edges to [[_COMMUNITY_Fatos do treino e versões]]

## Top bridge nodes
- [[ADR 0011 Linha de base pessoal, semana-padrão e tipo de treino]] - degree 39, connects to 11 communities
- [[metricaslinha-base]] - degree 36, connects to 11 communities
- [[ADR 0015 Caixa do dia do professor no piloto local (identidade, vínculo, `atencao@1` e correção do tipo)]] - degree 23, connects to 11 communities
- [[ADR 0003 Fuso da atividade e data local da sessão]] - degree 32, connects to 10 communities
- [[Caio (papel)]] - degree 24, connects to 8 communities