---
source_file: "docs/decisoes/0013-feedback-automatico.md"
type: "document"
community: "Glossário e ADRs 12 e 13"
tags:
  - graphify/document
  - graphify/EXTRACTED
  - community/Glossrio_e_ADRs_12_e_13
---

# ADR: 0013 Feedback automático por treino (pacote de fatos, guarda, camada de LLM, checagens)

## Connections
- [[ADR 0004 Contrato da tela de evolução dos tiros (Meta 2)]] - `links_to` [EXTRACTED]
- [[ADR 0007 Clima da atividade (Meta 4)]] - `links_to` [EXTRACTED]
- [[ADR 0008 Detecção de esforços (corrida por distância, ciclismo por duração)]] - `links_to` [EXTRACTED]
- [[ADR 0010 Carga de treino (rTSS, hrTSS, CTL, ATL e TSB)]] - `links_to` [EXTRACTED]
- [[ADR 0011 Linha de base pessoal, semana-padrão e tipo de treino]] - `links_to` [EXTRACTED]
- [[ADR 0012 Check-in pós-treino (PSE, sensação, observação) e `carga_pse@1`]] - `links_to` [EXTRACTED]
- [[ADR 0014 Recuperação diária (sono, VFC e FC de repouso) no contexto do treino]] - `links_to` [EXTRACTED]
- [[ADR 0015 Caixa do dia do professor no piloto local (identidade, vínculo, `atencao@1` e correção do tipo)]] - `links_to` [EXTRACTED]
- [[ADR 0016 Login, papéis, consentimento pelo atleta e deploy do piloto]] - `links_to` [EXTRACTED]
- [[ADR 0017 Chat do atleta com ferramentas de consulta]] - `links_to` [EXTRACTED]
- [[Caio (papel)]] - `owned_by` [EXTRACTED]
- [[Camada de LLM do feedback]] - `defines` [EXTRACTED]
- [[Cartão Feedback texto do pendente e do botão]] - `references` [EXTRACTED]
- [[Checagens do feedback automatico]] - `defines` [EXTRACTED]
- [[Meta 10 sono, VFC e FC de repouso no contexto do treino]] - `links_to` [EXTRACTED]
- [[Meta 12 como rodar o treino inteiro na tela do atleta]] - `references` [EXTRACTED]
- [[Meta 12 o treino inteiro na tela do atleta]] - `links_to` [EXTRACTED]
- [[Pacote de fatos `fatos_treino@2` fixtures e oráculo]] - `references` [EXTRACTED]
- [[designtelasfeedback]] - `aligned_with` [EXTRACTED]
- [[glossario]] - `links_to` [EXTRACTED]
- [[meta-9-feedback-automatico]] - `links_to` [EXTRACTED]
- [[metricascarga-pse]] - `links_to` [EXTRACTED]
- [[metricascarga-treino]] - `links_to` [EXTRACTED]
- [[metricasesforcos]] - `links_to` [EXTRACTED]
- [[metricasfatos-treino]] - `references` [EXTRACTED]
- [[metricaslinha-base]] - `links_to` [EXTRACTED]
- [[modulosapi]] - `references` [EXTRACTED]
- [[modulosapi-client]] - `references` [EXTRACTED]
- [[modulosbanco]] - `references` [EXTRACTED]
- [[moduloscamada-llm]] - `references` [EXTRACTED]
- [[modulosmobile]] - `references` [EXTRACTED]
- [[modulosworker]] - `references` [EXTRACTED]
- [[produtometa-10-como-rodar]] - `references` [EXTRACTED]
- [[produtometa-9-como-rodar]] - `links_to` [EXTRACTED]
- [[produtoplano-mvp-execucao]] - `links_to` [EXTRACTED]
- [[produtoroadmap]] - `links_to` [EXTRACTED]

#graphify/document #graphify/EXTRACTED #community/Glossrio_e_ADRs_12_e_13