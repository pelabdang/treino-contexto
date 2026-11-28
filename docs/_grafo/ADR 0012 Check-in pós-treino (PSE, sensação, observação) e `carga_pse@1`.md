---
source_file: "docs/decisoes/0012-check-in-pos-treino.md"
type: "document"
community: "Glossário e ADRs 12 e 13"
tags:
  - graphify/document
  - graphify/EXTRACTED
  - community/Glossrio_e_ADRs_12_e_13
---

# ADR: 0012 Check-in pós-treino (PSE, sensação, observação) e `carga_pse@1`

## Connections
- [[ADR 0003 Fuso da atividade e data local da sessão]] - `links_to` [EXTRACTED]
- [[ADR 0004 Contrato da tela de evolução dos tiros (Meta 2)]] - `links_to` [EXTRACTED]
- [[ADR 0009 Treino de transição (rótulo sugerido e corrigível)]] - `links_to` [EXTRACTED]
- [[ADR 0010 Carga de treino (rTSS, hrTSS, CTL, ATL e TSB)]] - `links_to` [EXTRACTED]
- [[ADR 0011 Linha de base pessoal, semana-padrão e tipo de treino]] - `links_to` [EXTRACTED]
- [[ADR 0013 Feedback automático por treino (pacote de fatos, guarda, camada de LLM, checagens)]] - `links_to` [EXTRACTED]
- [[ADR 0014 Recuperação diária (sono, VFC e FC de repouso) no contexto do treino]] - `links_to` [EXTRACTED]
- [[ADR 0015 Caixa do dia do professor no piloto local (identidade, vínculo, `atencao@1` e correção do tipo)]] - `links_to` [EXTRACTED]
- [[ADR 0016 Login, papéis, consentimento pelo atleta e deploy do piloto]] - `links_to` [EXTRACTED]
- [[ADR 0017 Chat do atleta com ferramentas de consulta]] - `links_to` [EXTRACTED]
- [[Caio (papel)]] - `owned_by` [EXTRACTED]
- [[Diário 2026-11-09]] - `references` [EXTRACTED]
- [[PSE (percepcao de esforco)]] - `defines` [EXTRACTED]
- [[Pacote de fatos `fatos_treino@2` fixtures e oráculo]] - `references` [EXTRACTED]
- [[carga_pse@1 (carga por PSE)]] - `defines` [EXTRACTED]
- [[designtelascaixa-do-dia]] - `references` [EXTRACTED]
- [[designtelascheckin]] - `specifies` [EXTRACTED]
- [[designtelasconsentimento]] - `references` [EXTRACTED]
- [[designtelasfeedback]] - `references` [EXTRACTED]
- [[glossario]] - `links_to` [EXTRACTED]
- [[meta-9-feedback-automatico]] - `links_to` [EXTRACTED]
- [[metricascarga-treino]] - `links_to` [EXTRACTED]
- [[metricasfatos-treino]] - `references` [EXTRACTED]
- [[modulosapi]] - `references` [EXTRACTED]
- [[modulosapi-client]] - `references` [EXTRACTED]
- [[modulosbanco]] - `references` [EXTRACTED]
- [[modulosmobile]] - `references` [EXTRACTED]
- [[modulosworker]] - `references` [EXTRACTED]
- [[produtometa-8-como-rodar]] - `references` [EXTRACTED]
- [[produtometa-9-como-rodar]] - `links_to` [EXTRACTED]
- [[produtometasmeta-8-check-in]] - `links_to` [EXTRACTED]
- [[produtoplano-mvp-execucao]] - `links_to` [EXTRACTED]
- [[produtoroadmap]] - `links_to` [EXTRACTED]

#graphify/document #graphify/EXTRACTED #community/Glossrio_e_ADRs_12_e_13