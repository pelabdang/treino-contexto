---
source_file: "docs/decisoes/0002-segmento-intensidade-e-versao.md"
type: "document"
community: "Ingestão Garmin e Meta 1"
tags:
  - graphify/document
  - graphify/EXTRACTED
  - community/Ingesto_Garmin_e_Meta_1
---

# ADR 0002 Segmento com intensidade da volta e versão da detecção

## Connections
- [[ADR 0001 Modelo de dados mínimo e estrutura do monorepo]] - `extends` [EXTRACTED]
- [[ADR 0003 Fuso da atividade e data local da sessão]] - `references` [EXTRACTED]
- [[ADR 0004 Contrato da tela de evolução dos tiros (Meta 2)]] - `references` [EXTRACTED]
- [[ADR 0005 Série de tiros o que entra e como a regra muda]] - `references` [EXTRACTED]
- [[ADR 0008 Detecção de esforços (corrida por distância, ciclismo por duração)]] - `links_to` [EXTRACTED]
- [[ADR 0010 Carga de treino (rTSS, hrTSS, CTL, ATL e TSB)]] - `links_to` [EXTRACTED]
- [[ADR 0011 Linha de base pessoal, semana-padrão e tipo de treino]] - `links_to` [EXTRACTED]
- [[Coluna segmento.intensidade]] - `decides` [EXTRACTED]
- [[Coluna segmento.versao_deteccao]] - `decides` [EXTRACTED]
- [[Diário 2026-10-31]] - `references` [EXTRACTED]
- [[Migração 0002]] - `decides` [EXTRACTED]
- [[Princípio versionar cada métrica derivada]] - `decides` [EXTRACTED]
- [[metricastiros-1km]] - `references` [EXTRACTED]
- [[modulosbanco]] - `references` [EXTRACTED]
- [[modulosingestao-garmin]] - `references` [EXTRACTED]
- [[produtometa-1-como-reproduzir]] - `references` [EXTRACTED]
- [[produtometasmeta-1-tiros-1km]] - `links_to` [EXTRACTED]

#graphify/document #graphify/EXTRACTED #community/Ingesto_Garmin_e_Meta_1