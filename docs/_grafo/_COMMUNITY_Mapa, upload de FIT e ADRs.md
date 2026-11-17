---
type: community
cohesion: 0.09
members: 42
---

# Mapa, upload de FIT e ADRs

**Cohesion:** 0.09 - loosely connected
**Members:** 42 nodes

## Members
- [[ADR 0006 Upload de arquivo FIT (Meta 3)]] - document - docs/decisoes/0006-upload-de-fit.md
- [[ADR 0007 Clima da atividade (Meta 4)]] - document - docs/decisoes/0007-clima-da-atividade.md
- [[Botão Enviar arquivo FIT]] - concept - docs/produto/meta-3-como-rodar.md
- [[Clima da atividade fixtures e oráculo]] - document - docs/metricas/clima-oraculo.md
- [[Clima do treino]] - concept - docs/design/telas/treino.md
- [[Diário 2026-10-31 Ciclo da Meta 1 tiros de 1 km]] - document - docs/diario/2026-10-31.md
- [[Diário 2026-11-01 Meta 1 fechada e conferência privada]] - document - docs/diario/2026-11-01.md
- [[Diário 2026-11-03 Ciclos das Metas 2, 3 e 4]] - document - docs/diario/2026-11-03.md
- [[Endpoint upload de FIT]] - concept - docs/modulos/api.md
- [[Estados do clima (ok, indoor, sem_posicao, pendente, falha)]] - concept - docs/produto/metas/meta-4-clima-atividade.md
- [[FIT_DIR (pasta de guarda dos FIT)]] - concept - docs/produto/meta-3-como-rodar.md
- [[Meta 1 (tiros de 1 km)]] - concept - docs/diario/2026-10-31.md
- [[Meta 1 como reproduzir]] - document - docs/produto/meta-1-como-reproduzir.md
- [[Meta 1 tiros de 1 km]] - document - docs/produto_metas_meta_1_tiros_1km.md
- [[Meta 2 (evolução no app)]] - concept - docs/diario/2026-11-03.md
- [[Meta 2 como rodar a API e o app]] - document - docs/produto/meta-2-como-rodar.md
- [[Meta 2 evolução dos tiros no app]] - document - docs/produto/metas/meta-2-evolucao-tiros-app.md
- [[Meta 3 (upload de FIT)]] - concept - docs/diario/2026-11-03.md
- [[Meta 3 como rodar o upload de FIT]] - document - docs/produto/meta-3-como-rodar.md
- [[Meta 3 upload de arquivo FIT]] - document - docs/produto/metas/meta-3-upload-fit.md
- [[Meta 4 (clima completo)]] - concept - docs/diario/2026-11-03.md
- [[Meta 4 clima da atividade]] - document - docs/produto_metas_meta_4_clima_atividade.md
- [[Meta 5 detecção de esforços]] - document - docs/produto/metas/meta-5-deteccao-esforcos.md
- [[Módulo API]] - document - docs/modulos_api.md
- [[Módulo api-client]] - document - docs/modulos/api-client.md
- [[Módulo gráfico dos tiros de 1 km]] - document - docs/modulos/grafico-tiros.md
- [[Módulo infra]] - document - docs/modulos/infra.md
- [[Open-Meteo]] - concept - docs/decisoes/0007-clima-da-atividade.md
- [[Regra tiros_1km (versões @1 a @4)]] - concept - docs/produto/metas/meta-1-tiros-1km.md
- [[Repositório público sem dado real]] - concept - docs/diario/2026-11-01.md
- [[Treino Contexto mapa do projeto]] - document - docs/00-inicio.md
- [[Treino-chave contínuo]] - concept - docs/produto/metas/meta-5-deteccao-esforcos.md
- [[clima]] - document - docs/glossario.md
- [[clima da atividade]] - concept - docs/decisoes/0007-clima-da-atividade.md
- [[mapa do projeto]] - concept - docs/00-inicio.md
- [[meta 4 como rodar]] - document - docs/glossario.md
- [[regra dos 60 s de identidade da atividade]] - concept - docs/decisoes/0006-upload-de-fit.md
- [[tabela clima_atividade]] - concept - docs/decisoes/0007-clima-da-atividade.md
- [[termos]] - concept - docs/00-inicio.md
- [[upload de arquivo FIT]] - concept - docs/decisoes/0006-upload-de-fit.md
- [[worker.preencher_clima]] - concept - docs/produto/meta-4-como-rodar.md
- [[Índice de módulos]] - document - docs/modulos.md

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Mapa_upload_de_FIT_e_ADRs
SORT file.name ASC
```

## Connections to other communities
- 83 edges to [[_COMMUNITY_Modelo de dados e ADRs iniciais]]
- 41 edges to [[_COMMUNITY_Contrato da tela e métricas]]
- 37 edges to [[_COMMUNITY_Check-in e feedback automático]]
- 5 edges to [[_COMMUNITY_Guias das metas e caixa do dia]]
- 1 edge to [[_COMMUNITY_Time e papéis]]

## Top bridge nodes
- [[Treino Contexto mapa do projeto]] - degree 88, connects to 5 communities
- [[Módulo API]] - degree 34, connects to 3 communities
- [[ADR 0007 Clima da atividade (Meta 4)]] - degree 25, connects to 3 communities
- [[ADR 0006 Upload de arquivo FIT (Meta 3)]] - degree 23, connects to 3 communities
- [[Diário 2026-11-03 Ciclos das Metas 2, 3 e 4]] - degree 13, connects to 3 communities