---
source_file: "docs/produto/plano-mvp-execucao.md"
type: "document"
community: "Caixa do dia e produto"
location: "§3.2"
tags:
  - graphify/document
  - graphify/EXTRACTED
  - community/Caixa_do_dia_e_produto
---

# Modelo de dados (núcleo)

## Connections
- [[PostgreSQL  Supabase]] - `references` [EXTRACTED]
- [[Princípio guardar dado bruto e versionar métricas]] - `references` [EXTRACTED]
- [[Segmento (zona e equipamento)]] - `references` [EXTRACTED]
- [[Semana-padrão]] - `references` [EXTRACTED]
- [[Sinal  alerta de atenção]] - `references` [EXTRACTED]
- [[bem_estar_diario (sono, HRV, FC repouso)]] - `references` [EXTRACTED]
- [[metrica_derivada (versionada)]] - `references` [EXTRACTED]
- [[serie_atividade (séries por segundo)]] - `references` [EXTRACTED]

#graphify/document #graphify/EXTRACTED #community/Caixa_do_dia_e_produto