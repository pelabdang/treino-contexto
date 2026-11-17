---
type: community
cohesion: 0.10
members: 59
---

# Modelo de dados e ADRs iniciais

**Cohesion:** 0.10 - loosely connected
**Members:** 59 nodes

## Members
- [[ADR 0001 Modelo de dados mínimo e estrutura do monorepo]] - document - docs/decisoes/0001-modelo-de-dados-minimo.md
- [[ADR 0002 Segmento com intensidade da volta e versão da detecção]] - document - docs/decisoes/0002-segmento-intensidade-e-versao.md
- [[ADR 0003 Fuso da atividade e data local da sessão]] - document - docs/decisoes/0003-fuso-da-atividade.md
- [[ADR 0005 Série de tiros o que entra e como a regra muda]] - document - docs/decisoes/0005-serie-de-tiros-o-que-entra.md
- [[ADR 0008 Detecção de esforços (corrida por distância, ciclismo por duração)]] - document - docs/decisoes/0008-deteccao-de-esforcos.md
- [[ADR 0009 Treino de transição (rótulo sugerido e corrigível)]] - document - docs/decisoes/0009-treino-de-transicao.md
- [[ADR 0010 Carga de treino (rTSS, hrTSS, CTL, ATL e TSB)]] - document - docs/decisoes/0010-carga-de-treino.md
- [[ADR 0011 Linha de base pessoal, semana-padrão e tipo de treino]] - document - docs/decisoes/0011-linha-de-base-e-semana-padrao.md
- [[Agregação por sessão]] - concept - docs/metricas/tiros-1km.md
- [[CTL, ATL e TSB]] - concept - docs/decisoes/0010-carga-de-treino.md
- [[Carga de treino]] - document - docs/metricas_carga_treino.md
- [[Carga de treino fixtures de algumas semanas e oráculo]] - document - docs/metricas/carga-oraculo.md
- [[Conferência da nossa carga com a carga do Garmin (`conferencia_carga@1`)]] - document - docs/metricas/conferencia-carga.md
- [[Dados de saúde da exportação (limiar, zonas, recordes)]] - concept - docs/modulos/ingestao-garmin.md
- [[Decisões do Angelo (0411)]] - concept - docs/diario/2026-11-04.md
- [[Detecção de esforços fixtures e oráculo]] - document - docs/metricas/esforcos-oraculo.md
- [[Divergência do plano]] - concept - docs/metricas/tipo-treino.md
- [[Diário 2026-11-04 Decisões do Angelo e detecção de esforços]] - document - docs/diario/2026-11-04.md
- [[Diário 2026-11-06 Meta 5 esforços e treino de transição]] - document - docs/diario/2026-11-06.md
- [[Diário 2026-11-07 Meta 6 carga de treino]] - document - docs/diario/2026-11-07.md
- [[Diário 2026-11-08 Fechamento da Meta 6]] - document - docs/diario/2026-11-08.md
- [[Encaixe na semana-padrão]] - concept - docs/metricas/tipo-treino.md
- [[Endpoint de carga]] - concept - docs/modulos/api.md
- [[Esforços]] - document - docs/metricas_esforcos.md
- [[Glossário]] - document - docs/glossario.md
- [[Gráfico de carga]] - concept - docs/diario/2026-11-08.md
- [[Ingestão Garmin]] - document - docs/modulos_ingestao_garmin.md
- [[Meta 5 (esforços e transição)]] - concept - docs/diario/2026-11-06.md
- [[Meta 5 como rodar a detecção de esforços]] - document - docs/produto/meta-5-como-rodar.md
- [[Meta 6 (carga de treino)]] - concept - docs/diario/2026-11-07.md
- [[Métrica tiros de 1 km]] - document - docs/metricas_tiros_1km.md
- [[Módulo banco]] - document - docs/modulos_banco.md
- [[Módulo worker]] - document - docs/modulos_worker.md
- [[Parser de FIT (fitdecode)]] - concept - docs/modulos/ingestao-garmin.md
- [[Ritmo habitual do atleta]] - concept - docs/metricas/tiros-1km.md
- [[Série de carga]] - document - docs/metricas_serie_carga.md
- [[Tipo de treino]] - document - docs/metricas_tipo_treino.md
- [[Tipo de treino e linha de base fixtures de 12 semanas e oráculo]] - document - docs/metricas/tipo-linha-base-oraculo.md
- [[Treino multiesporte atividade-pai e troca]] - concept - docs/modulos/ingestao-garmin.md
- [[calibração pelos recordes pessoais]] - concept - docs/decisoes/0008-deteccao-de-esforcos.md
- [[carga@1]] - concept - docs/decisoes/0010-carga-de-treino.md
- [[data local da sessão]] - concept - docs/decisoes/0003-fuso-da-atividade.md
- [[detecção de esforços]] - concept - docs/decisoes/0008-deteccao-de-esforcos.md
- [[estrutura do monorepo]] - concept - docs/decisoes/0001-modelo-de-dados-minimo.md
- [[fuso da atividade]] - concept - docs/decisoes/0003-fuso-da-atividade.md
- [[grafico carga]] - document - docs/metricas/conferencia-carga.md
- [[intensidade da volta]] - concept - docs/decisoes/0002-segmento-intensidade-e-versao.md
- [[limiar do atleta]] - concept - docs/decisoes/0010-carga-de-treino.md
- [[modelo de dados mínimo]] - concept - docs/decisoes/0001-modelo-de-dados-minimo.md
- [[recuperação pelo tempo de pausa]] - concept - docs/decisoes/0008-deteccao-de-esforcos.md
- [[regra transicao@1]] - concept - docs/decisoes/0009-treino-de-transicao.md
- [[rótulo corrigível pelo atleta]] - rationale - docs/decisoes/0009-treino-de-transicao.md
- [[semana-padrão_1]] - concept - docs/decisoes/0011-linha-de-base-e-semana-padrao.md
- [[série de tiros]] - concept - docs/decisoes/0005-serie-de-tiros-o-que-entra.md
- [[tipo de treino (tipo_treino@1)]] - concept - docs/decisoes/0011-linha-de-base-e-semana-padrao.md
- [[transicao]] - document - docs/glossario.md
- [[treino de transição]] - concept - docs/decisoes/0009-treino-de-transicao.md
- [[versão da detecção]] - concept - docs/decisoes/0002-segmento-intensidade-e-versao.md
- [[worker.detectar_esforcos]] - concept - docs/produto/meta-5-como-rodar.md

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Modelo_de_dados_e_ADRs_iniciais
SORT file.name ASC
```

## Connections to other communities
- 83 edges to [[_COMMUNITY_Mapa, upload de FIT e ADRs]]
- 71 edges to [[_COMMUNITY_Check-in e feedback automático]]
- 50 edges to [[_COMMUNITY_Contrato da tela e métricas]]
- 4 edges to [[_COMMUNITY_Guias das metas e caixa do dia]]

## Top bridge nodes
- [[ADR 0011 Linha de base pessoal, semana-padrão e tipo de treino]] - degree 37, connects to 4 communities
- [[ADR 0010 Carga de treino (rTSS, hrTSS, CTL, ATL e TSB)]] - degree 32, connects to 4 communities
- [[Glossário]] - degree 53, connects to 3 communities
- [[Módulo banco]] - degree 27, connects to 3 communities
- [[ADR 0003 Fuso da atividade e data local da sessão]] - degree 26, connects to 3 communities