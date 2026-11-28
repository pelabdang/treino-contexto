---
type: community
cohesion: 0.27
members: 12
---

# Glossário e ADRs 12 e 13

**Cohesion:** 0.27 - loosely connected
**Members:** 12 nodes

## Members
- [[ADR 0012 Check-in pós-treino (PSE, sensação, observação) e `carga_pse@1`]] - document - docs/decisoes/0012-check-in-pos-treino.md
- [[ADR 0013 Feedback automático por treino (pacote de fatos, guarda, camada de LLM, checagens)]] - document - docs/decisoes/0013-feedback-automatico.md
- [[ADR 0016 Login, papéis, consentimento pelo atleta e deploy do piloto]] - document - docs/decisoes/0016-login-e-deploy-do-piloto.md
- [[ADR 0017 Chat do atleta com ferramentas de consulta]] - document - docs/decisoes/0017-chat-do-atleta.md
- [[Camada de LLM do feedback]] - document - docs/decisoes/0013-feedback-automatico.md
- [[Carga de treino rTSS, hrTSS, CTL, ATL, TSB]] - document - docs/decisoes/0010-carga-de-treino.md
- [[Checagens do feedback automatico]] - document - docs/decisoes/0013-feedback-automatico.md
- [[Groq no chat do atleta]] - document - docs/decisoes/0017-chat-do-atleta.md
- [[Oraculo das fixtures]] - document - docs/glossario.md
- [[PSE (percepcao de esforco)]] - document - docs/decisoes/0012-check-in-pos-treino.md
- [[carga_pse@1 (carga por PSE)]] - document - docs/decisoes/0012-check-in-pos-treino.md
- [[glossario]] - document - docs/glossario.md

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Glossrio_e_ADRs_12_e_13
SORT file.name ASC
```

## Connections to other communities
- 19 edges to [[_COMMUNITY_Roadmap e esforços]]
- 18 edges to [[_COMMUNITY_App, telas e design]]
- 17 edges to [[_COMMUNITY_Linha de base e fuso]]
- 15 edges to [[_COMMUNITY_Worker, carga e Meta 12]]
- 14 edges to [[_COMMUNITY_Banco e guias das metas 7 a 8]]
- 10 edges to [[_COMMUNITY_Recuperação e Meta 10]]
- 10 edges to [[_COMMUNITY_Fatos do treino e feedback]]
- 9 edges to [[_COMMUNITY_Contrato da tela e api-client]]
- 8 edges to [[_COMMUNITY_Roadmap, atenção e diário 1711]]
- 5 edges to [[_COMMUNITY_Mapa e diários de novembro]]
- 4 edges to [[_COMMUNITY_API e versões de métricas]]
- 4 edges to [[_COMMUNITY_Deploy da Meta 13 e plano do MVP]]
- 4 edges to [[_COMMUNITY_Diário de 2811 e chat]]
- 4 edges to [[_COMMUNITY_Evolução e ferramentas do chat]]
- 3 edges to [[_COMMUNITY_Fatos do treino e versões]]
- 3 edges to [[_COMMUNITY_Meta 11 caixa do dia]]
- 3 edges to [[_COMMUNITY_Carga de treino e conferência]]
- 2 edges to [[_COMMUNITY_Diário de 1011 e decisões]]
- 1 edge to [[_COMMUNITY_Modelo de dados e tabelas]]
- 1 edge to [[_COMMUNITY_Diários de 18 e 2711 e clima]]
- 1 edge to [[_COMMUNITY_Camada de LLM]]

## Top bridge nodes
- [[glossario]] - degree 73, connects to 16 communities
- [[ADR 0013 Feedback automático por treino (pacote de fatos, guarda, camada de LLM, checagens)]] - degree 36, connects to 12 communities
- [[ADR 0012 Check-in pós-treino (PSE, sensação, observação) e `carga_pse@1`]] - degree 33, connects to 11 communities
- [[ADR 0017 Chat do atleta com ferramentas de consulta]] - degree 20, connects to 11 communities
- [[ADR 0016 Login, papéis, consentimento pelo atleta e deploy do piloto]] - degree 18, connects to 9 communities