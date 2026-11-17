# Graph Report - docs  (2026-11-17)

## Corpus Check
- 111 files · ~234,768 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 346 nodes · 1044 edges · 20 communities (16 shown, 4 thin omitted)
- Extraction: 95% EXTRACTED · 5% INFERRED · 0% AMBIGUOUS · INFERRED: 53 edges (avg confidence: 0.83)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- Contrato da tela e métricas
- Modelo de dados e ADRs iniciais
- Mapa, upload de FIT e ADRs
- Check-in e feedback automático
- Arquitetura e plano do MVP
- Caixa do dia e produto
- Guias das metas e caixa do dia
- Pessoas, parceiros e decisões
- Agente do atleta
- Cronograma e validação
- Time e papéis
- Script de contraste
- Camadas de métricas
- Descoberta e conhecimento
- Fundação de dados e fontes
- Templates de regra e texto
- Template de decisão
- Template de diário
- Template de meta
- Template de módulo

## God Nodes (most connected - your core abstractions)
1. `Treino Contexto: mapa do projeto` - 88 edges
2. `Roadmap` - 66 edges
3. `Glossário` - 53 edges
4. `ADR: 0011 Linha de base pessoal, semana-padrão e tipo de treino` - 37 edges
5. `ADR: 0013 Feedback automático por treino (pacote de fatos, guarda, camada de LLM, checagen` - 36 edges
6. `Módulo API` - 34 edges
7. `ADR: 0004 Contrato da tela de evolução dos tiros (Meta 2)` - 33 edges
8. `ADR: 0012 Check-in pós-treino (PSE, sensação, observação) e `carga_pse@1`` - 33 edges
9. `ADR: 0010 Carga de treino (rTSS, hrTSS, CTL, ATL e TSB)` - 32 edges
10. `ADR: 0014 Recuperação diária (sono, VFC e FC de repouso) no contexto do treino` - 29 edges

## Surprising Connections (you probably didn't know these)
- `Componente GraficoTiros` --semantically_similar_to--> `Módulo gráfico dos tiros de 1 km`  [INFERRED] [semantically similar]
  docs/modulos/mobile.md → docs/modulos/grafico-tiros.md
- `Escala PSE (CR-10)` --conceptually_related_to--> `Carga por PSE`  [INFERRED]
  docs/design/telas/checkin.md → docs/metricas_carga_pse.md
- `grafico carga` --semantically_similar_to--> `Módulo gráfico dos tiros de 1 km`  [INFERRED] [semantically similar]
  docs/metricas/conferencia-carga.md → docs/modulos/grafico-tiros.md
- `Meta 6 (carga de treino)` --implements--> `ADR: 0010 Carga de treino (rTSS, hrTSS, CTL, ATL e TSB)`  [INFERRED]
  docs/diario/2026-11-07.md → docs/decisoes/0010-carga-de-treino.md
- `Semana-padrão` --implements--> `ADR: 0011 Linha de base pessoal, semana-padrão e tipo de treino`  [EXTRACTED]
  docs/design/telas/semana-padrao.md → docs/decisoes/0011-linha-de-base-e-semana-padrao.md

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Base de conhecimento: artigos e entrevistas → regras/métricas → motor de explicação** — docs_templates_artigo_template, docs_templates_entrevista_template, docs_templates_regra_template, docs_templates_metrica_template [INFERRED 0.75]
- **Pipeline de inteligência em quatro camadas (só a última usa LLM)** — docs_produto_plano_mvp_execucao_camada1_metricas, docs_produto_plano_mvp_execucao_camada2_linha_base, docs_produto_plano_mvp_execucao_camada3_motor_explicacao, docs_produto_plano_mvp_execucao_pacote_fatos, docs_produto_plano_mvp_execucao_camada4_redacao_ia [EXTRACTED 1.00]
- **Três barreiras contra erro do texto de IA** — docs_produto_plano_mvp_execucao_checagem_numeros, docs_produto_plano_mvp_execucao_linguagem_proibida, docs_produto_plano_mvp_execucao_regras_envio, docs_produto_plano_mvp_execucao_camada4_redacao_ia [EXTRACTED 1.00]
- **Fluxo de ingestão (Garmin, FIT, check-in -> fila -> workers -> banco)** — docs_produto_plano_mvp_execucao_garmin, docs_produto_plano_mvp_execucao_upload_fit, docs_produto_plano_mvp_execucao_checkin, docs_produto_plano_mvp_execucao_fila_workers, docs_produto_plano_mvp_execucao_open_meteo, docs_produto_plano_mvp_execucao_postgres_supabase, docs_produto_plano_mvp_execucao_storage_parquet [EXTRACTED 1.00]
- **Cadeia do feedback por treino** — docs_decisoes_0012_check_in_pos_treino_check_in_pos_treino, docs_decisoes_0013_feedback_automatico_feedback_automatico_por_treino, docs_decisoes_0014_recuperacao_diaria_recuperacao_diaria_sono_vfc_fc_de_repouso [INFERRED 0.85]
- **Caixa do dia: ADR, spec e linha de base** — docs_decisoes_0015_caixa_do_dia_do_professor_caixa_do_dia_do_professor, docs_design_telas_caixa_do_dia_tela_caixa_do_dia, docs_decisoes_0011_linha_de_base_e_semana_padrao_linha_de_base_pessoal [INFERRED 0.85]
- **Telas do app seguindo o guia visual** — docs_design_telas_checkin, docs_design_telas_feedback, docs_design_telas_treino, docs_design_telas_semana_padrao, docs_design_telas_evolucao_tiros [EXTRACTED 1.00]
- **Meta 8: check-in pós-treino** — docs_decisoes_0012_check_in_pos_treino, docs_design_telas_checkin, docs_diario_2026_11_10_meta8_fechada, docs_metricas_carga_pse [INFERRED 0.85]
- **Meta 9: feedback automático** — docs_decisoes_0013_feedback_automatico, docs_design_telas_feedback, docs_metricas_fatos_treino, docs_metricas_checagens_feedback, docs_modulos_camada_llm [INFERRED 0.85]
- **Fatos, recuperação, carga pela PSE e checagens do feedback** — docs_metricas_fatos_treino, docs_metricas_recuperacao, docs_metricas_checagens_feedback, docs_metricas_carga_pse [INFERRED 0.85]
- **Família de métricas de carga** — docs_metricas_carga_treino, docs_metricas_serie_carga, docs_metricas_conferencia_carga, docs_metricas_carga_pse [INFERRED 0.85]
- **Pipeline de dados: ingestão Garmin, banco, worker e API** — docs_modulos_ingestao_garmin, docs_modulos_banco, docs_modulos_worker, docs_modulos_api [INFERRED 0.85]
- **Fluxo da caixa do dia: API, tela mobile e roteiro da Meta 11** — docs_modulos_api_caixa_do_dia, docs_modulos_mobile_tela_caixa_do_dia, docs_produto_meta_11_como_rodar [INFERRED 0.85]
- **Guias como-rodar das Metas 3 a 9 (mesma base de Postgres próprio e fixtures sintéticas)** — docs_produto_meta_3_como_rodar, docs_produto_meta_4_como_rodar, docs_produto_meta_5_como_rodar, docs_produto_meta_6_como_rodar, docs_produto_meta_7_como_rodar, docs_produto_meta_8_como_rodar, docs_produto_meta_9_como_rodar [EXTRACTED 1.00]
- **Notas de resultado das Metas 1 a 11** — docs_produto_metas_meta_1_tiros_1km, docs_produto_metas_meta_2_evolucao_tiros_app, docs_produto_metas_meta_3_upload_fit, docs_produto_metas_meta_4_clima_atividade, docs_produto_metas_meta_5_deteccao_esforcos, docs_produto_metas_meta_6_carga_treino, docs_produto_metas_meta_7_linha_de_base_semana_padrao, docs_produto_metas_meta_8_check_in, docs_produto_metas_meta_9_feedback_automatico, docs_produto_metas_meta_10_recuperacao, docs_produto_metas_meta_11_caixa_do_dia [EXTRACTED 1.00]

## Communities (20 total, 4 thin omitted)

### Community 0 - "Contrato da tela e métricas"
Cohesion: 0.06
Nodes (70): ADR: 0004 Contrato da tela de evolução dos tiros (Meta 2), a API formata, o app mostra, contrato da tela de evolução, melhor tiro como valor principal, carga de treino (rTSS, hrTSS), linha de base pessoal, ADR: 0012 Check-in pós-treino (PSE, sensação, observação) e `carga_pse@1`, carga_pse@1 (+62 more)

### Community 1 - "Modelo de dados e ADRs iniciais"
Cohesion: 0.10
Nodes (59): ADR: 0001 Modelo de dados mínimo e estrutura do monorepo, estrutura do monorepo, modelo de dados mínimo, ADR: 0002 Segmento com intensidade da volta e versão da detecção, intensidade da volta, versão da detecção, ADR: 0003 Fuso da atividade e data local da sessão, data local da sessão (+51 more)

### Community 2 - "Mapa, upload de FIT e ADRs"
Cohesion: 0.09
Nodes (42): Treino Contexto: mapa do projeto, mapa do projeto, termos, ADR: 0006 Upload de arquivo FIT (Meta 3), regra dos 60 s de identidade da atividade, upload de arquivo FIT, ADR: 0007 Clima da atividade (Meta 4), clima da atividade (+34 more)

### Community 3 - "Check-in e feedback automático"
Cohesion: 0.13
Nodes (42): check-in pós-treino, ADR: 0013 Feedback automático por treino (pacote de fatos, guarda, camada de LLM, checagen, camada de LLM, checagens do feedback, feedback automático por treino, pacote de fatos fatos_treino@1, ADR: 0014 Recuperação diária (sono, VFC e FC de repouso) no contexto do treino, fatos_treino@2 (+34 more)

### Community 4 - "Arquitetura e plano do MVP"
Cohesion: 0.15
Nodes (17): Arquitetura (ingestão, fila, workers, web), Camada 3: motor de explicação, Check-in pós-treino (3 toques), Check-in semanal (3 perguntas), API do Claude, Custo estimado do piloto, Fase: Inteligência e fluxo (sem. 7-10), Python FastAPI (backend) (+9 more)

### Community 5 - "Caixa do dia e produto"
Cohesion: 0.16
Nodes (15): Caixa do dia (quem precisa de atenção), Cancelamento / desconexão do aluno, Checagem automática de números, Classificação do tipo de treino pelo professor, Consulta estruturada do agente, Hipótese do MVP (contexto pronto reduz cancelamento), metrica_derivada (versionada), Modelo de dados (núcleo) (+7 more)

### Community 6 - "Guias das metas e caixa do dia"
Cohesion: 0.19
Nodes (13): Meta 6: como rodar a carga de treino, worker.calcular_carga, Meta 7: como rodar semana-padrão, tipo de treino e linha de base, Meta 11: caixa do dia do professor, Regra de atenção (atencao@2), Vínculo e consentimento do atleta com o professor, Meta 6: carga de treino, CTL, ATL e TSB (condicionamento, fadiga, forma) (+5 more)

### Community 7 - "Pessoas, parceiros e decisões"
Cohesion: 0.19
Nodes (13): Angelo (produto e relação com a assessoria), Apple Health / Health Connect, Assessoria (cliente B2B), Claude Code (agentes do projeto), CNPJ, Decisões que precisam de você, Plano de MVP e execução, Fora do MVP (prescrição, app nativo, venda direta) (+5 more)

### Community 8 - "Agente do atleta"
Cohesion: 0.24
Nodes (12): Agente do atleta, Atleta, Cadência do feedback (treino, semanal, quinzenal, mensal), Camada 4: redação com IA, Devolutiva do professor, Limites de escopo do agente (não prescreve), Fase: Agente do atleta (sem. 9-11), Feedback automático (+4 more)

### Community 9 - "Cronograma e validação"
Cohesion: 0.25
Nodes (11): Coordenação, Critério de decisão (seguir, ajustar, repensar), Cronograma (~16 semanas), Fase: Avaliação (sem. 16), Fase: Ensaio (sem. 11), Grupo de comparação, Manual da assessoria, Métricas de sucesso do piloto (+3 more)

### Community 10 - "Time e papéis"
Cohesion: 0.22
Nodes (11): Time e papéis, Angelo (dono do produto), Bia (QA), Caio (ciência do esporte), Duda (dados e backend), Lia (design e UX), Nina (documentação), Paulo (planejador) (+3 more)

### Community 11 - "Script de contraste"
Cohesion: 0.38
Nodes (10): calcular(), documento_atualizado(), ler_cores(), luminancia(), main(), num(), Contraste WCAG 2.x dos pares de cor do guia visual (issue #192).  Lê as cores da, Luminância relativa sRGB (WCAG 2.2). (+2 more)

### Community 12 - "Camadas de métricas"
Cohesion: 0.25
Nodes (8): Altimetria, Camada 1: métricas determinísticas, Camada 2: linha de base pessoal, Carga (TSS, rTSS, hrTSS, CTL/ATL/TSB), Eficiência (EF) e desacoplamento Pa:HR, Início frio (valor populacional ponderado), Métricas de engajamento, Pace ajustado (GAP, calor, vento)

### Community 13 - "Descoberta e conhecimento"
Cohesion: 0.29
Nodes (7): Aprendizado contínuo com edições do professor, Base de conhecimento (regras com fonte), Consultor de ciência do esporte, Ely 2007 (calor e desempenho na corrida), Entrevistas com 8 a 12 treinadores, Fase: Descoberta (sem. 1-2), Propriedade intelectual (regras e textos)

### Community 14 - "Fundação de dados e fontes"
Cohesion: 0.33
Nodes (7): bem_estar_diario (sono, HRV, FC repouso), Fase: Fundação de dados (sem. 3-6), Ficha do aluno, Garmin Connect Developer Program, COROS, Polar, Suunto, Wahoo, Upload de arquivo FIT/GPX/TCX, WHOOP, Oura

### Community 15 - "Templates de regra e texto"
Cohesion: 0.50
Nodes (4): Template: artigo, Template: entrevista, Template: métrica, Template: regra

## Ambiguous Edges - Review These
- `Início frio (valor populacional ponderado)` → `Ely 2007 (calor e desempenho na corrida)`  [AMBIGUOUS]
  docs/produto/plano-mvp-execucao.md · relation: conceptually_related_to

## Knowledge Gaps
- **112 isolated node(s):** `Template: decisão (ADR)`, `Template: diário`, `Template: entrevista`, `Template: meta`, `Template: métrica` (+107 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **4 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `Início frio (valor populacional ponderado)` and `Ely 2007 (calor e desempenho na corrida)`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **Why does `Treino Contexto: mapa do projeto` connect `Mapa, upload de FIT e ADRs` to `Contrato da tela e métricas`, `Modelo de dados e ADRs iniciais`, `Check-in e feedback automático`, `Guias das metas e caixa do dia`, `Time e papéis`?**
  _High betweenness centrality (0.152) - this node is a cross-community bridge._
- **Why does `Roadmap` connect `Check-in e feedback automático` to `Contrato da tela e métricas`, `Modelo de dados e ADRs iniciais`, `Mapa, upload de FIT e ADRs`, `Guias das metas e caixa do dia`, `Time e papéis`?**
  _High betweenness centrality (0.086) - this node is a cross-community bridge._
- **Why does `Time e papéis` connect `Time e papéis` to `Mapa, upload de FIT e ADRs`, `Check-in e feedback automático`?**
  _High betweenness centrality (0.035) - this node is a cross-community bridge._
- **What connects `Template: decisão (ADR)`, `Template: diário`, `Template: entrevista` to the rest of the system?**
  _112 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Contrato da tela e métricas` be split into smaller, more focused modules?**
  _Cohesion score 0.0567287784679089 - nodes in this community are weakly interconnected._
- **Should `Modelo de dados e ADRs iniciais` be split into smaller, more focused modules?**
  _Cohesion score 0.1005260081823495 - nodes in this community are weakly interconnected._