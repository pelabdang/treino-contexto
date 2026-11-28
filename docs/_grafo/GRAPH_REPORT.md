# Graph Report - docs  (2026-11-28)

## Corpus Check
- 142 files · ~304,251 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 549 nodes · 1810 edges · 36 communities (30 shown, 6 thin omitted)
- Extraction: 98% EXTRACTED · 2% INFERRED · 0% AMBIGUOUS · INFERRED: 45 edges (avg confidence: 0.76)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- App, telas e design
- Mapa, metas e templates
- Worker, carga e Meta 12
- Banco e guias das metas 7 a 8
- Roadmap e esforços
- Ingestão Garmin e Meta 1
- Contrato da tela e api-client
- Guias das metas 2 a 4
- Linha de base e fuso
- Mapa e diários de novembro
- Diários de 18 e 27/11 e clima
- Roadmap, atenção e diário 17/11
- Evolução e ferramentas do chat
- API e versões de métricas
- Diário de 28/11 e chat
- Fatos do treino e feedback
- Carga de treino e conferência
- Modelo de dados e tabelas
- Recuperação e Meta 10
- Módulo clima
- Glossário e ADRs 12 e 13
- Infra e papéis
- Camada de LLM
- Script de contraste
- Meta 11: caixa do dia
- Diário de 10/11 e decisões
- Fatos do treino e versões
- Deploy da Meta 13 e plano do MVP
- Gráfico dos tiros
- Papéis e pontas 29
- Papéis e pontas 30
- Papéis e pontas 31
- Papéis e pontas 32
- Papéis e pontas 33
- Papéis e pontas 34

## God Nodes (most connected - your core abstractions)
1. `modulos/api` - 92 edges
2. `produto/roadmap` - 92 edges
3. `glossario` - 73 edges
4. `modulos/mobile` - 72 edges
5. `modulos/worker` - 61 edges
6. `modulos/banco` - 59 edges
7. `modulos/ingestao-garmin` - 54 edges
8. `ADR 0004 Contrato da tela de evolução dos tiros (Meta 2)` - 52 edges
9. `ADR: 0011 Linha de base pessoal, semana-padrão e tipo de treino` - 39 edges
10. `modulos/api-client` - 36 edges

## Surprising Connections (you probably didn't know these)
- `Template decisao` --template_for--> `ADR 0001 Modelo de dados mínimo e estrutura do monorepo`  [INFERRED]
  docs/_templates/decisao.md → docs/decisoes/0001-modelo-de-dados-minimo.md
- `modulos/api` --references--> `atencao`  [EXTRACTED]
  docs/modulos/api.md → docs/metricas/atencao.md
- `meta-13-backup-e-restauracao` --references--> `modulos/worker`  [EXTRACTED]
  docs/produto/meta-13-backup-e-restauracao.md → docs/modulos/worker.md
- `meta-13-backup-e-restauracao` --references--> `produto/roadmap`  [EXTRACTED]
  docs/produto/meta-13-backup-e-restauracao.md → docs/produto/roadmap.md
- `produto/roadmap` --links_to--> `2026-11-13`  [EXTRACTED]
  docs/produto/roadmap.md → docs/diario/2026-11-13.md

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **ADRs do modelo de dados da Meta 1** — 0001_modelo_de_dados_minimo, 0002_segmento_intensidade_e_versao, 0003_fuso_da_atividade [EXTRACTED 0.90]
- **Cadeia de ADRs de carga, check-in, feedback e recuperacao** — 0010_carga_de_treino, 0012_check_in_pos_treino, 0013_feedback_automatico, 0014_recuperacao_diaria [INFERRED 0.80]
- **Evolucao da identidade visual** — guia_visual, identidade_visual_v2, identidade_visual_v3 [EXTRACTED 0.90]
- **Telas v3-v5 do atleta (identidade v3)** — inicio_atleta_v3, inicio_v4, inicio_v5_direcoes, evolucao_v1 [INFERRED 0.80]
- **Metrica + oraculo de fixtures** — metricas_atencao, metricas_atencao_oraculo, metricas_carga_pse, metricas_carga_pse_oraculo, metricas_carga_treino, metricas_carga_oraculo, metricas_checagens_chat, metricas_chat_oraculo [INFERRED 0.80]

## Communities (36 total, 6 thin omitted)

### Community 0 - "App, telas e design"
Cohesion: 0.15
Nodes (45): Auditoria de UX, navegação e tela inicial do atleta, Regra: o app nao calcula, a API entrega pronto, Tipografia Barlow Condensed, Ideia: prancheta do treinador, Cor volt #C6F432, design/telas/caixa-do-dia, Versão atencao@2, Versão linha_base@3 (+37 more)

### Community 1 - "Mapa, metas e templates"
Cohesion: 0.08
Nodes (41): Meta 2 evolução dos tiros no app, ADR 0006 Upload de FIT, ADR 0007 Clima da atividade, ADR 0008 Detecção de esforços, ADR 0009 Treino de transição, ADR 0010 Carga de treino, ADR 0011 Linha de base e semana-padrão, ADR 0012 Check-in pós-treino (+33 more)

### Community 2 - "Worker, carga e Meta 12"
Cohesion: 0.11
Nodes (38): ADR: 0010 Carga de treino (rTSS, hrTSS, CTL, ATL e TSB), Diário 2026-11-07, Diário 2026-11-08, metricas/carga-oraculo, metricas/carga-treino, metricas/conferencia-carga, metricas/frase-forma, Versão frase_forma@1 (+30 more)

### Community 3 - "Banco e guias das metas 7 a 8"
Cohesion: 0.08
Nodes (36): Diário 2026-11-09, modulos/banco, Versão carga@2, Versão checkin@1, Versão esforcos@1, Versão recuperacao_leitura@1, Versão saude_garmin@1, Versão tipo_treino@1 (+28 more)

### Community 4 - "Roadmap e esforços"
Cohesion: 0.21
Nodes (27): ADR: 0008 Detecção de esforços (corrida por distância, ciclismo por duração), ADR: 0009 Treino de transição (rótulo sugerido e corrigível), Diário 2026-11-04, Diário 2026-11-06, 2026-11-12, 2026-11-17, Rotulo sugerido e corrigivel de treino de transicao, metricas/esforcos (+19 more)

### Community 5 - "Ingestão Garmin e Meta 1"
Cohesion: 0.11
Nodes (25): Migração 0002, ADR 0002 Segmento com intensidade da volta e versão da detecção, Diário 2026-10-31, Diário 2026-11-01, modulos/ingestao-garmin, Arquivos principais, Buscar no Garmin Connect (piloto local, #335), Como importar a exportação real (+17 more)

### Community 6 - "Contrato da tela e api-client"
Cohesion: 0.22
Nodes (21): Princípio: app não formata pace nem escolhe eixos, ADR 0004 Contrato da tela de evolução dos tiros (Meta 2), GET /atletas/{atleta_id}/evolucao/tiros-1km, Angelo (decisão #51), Esteira fora da série de tiros, Regra geral, sem critério por atleta, ADR 0005 Série de tiros: o que entra e como a regra muda, ADR: 0006 Upload de arquivo FIT (Meta 3) (+13 more)

### Community 7 - "Guias das metas 2 a 4"
Cohesion: 0.11
Nodes (20): produto/meta-2-como-rodar, Antes de começar, Atenção com o banco (leia antes do passo 1), Encerrar e limpar, Passo a passo, Problemas comuns, Testes, produto/meta-3-como-rodar (+12 more)

### Community 8 - "Linha de base e fuso"
Cohesion: 0.17
Nodes (19): Data local da sessão, ADR 0003 Fuso da atividade e data local da sessão, Coluna atividade.fuso_min, Migração 0003, ADR: 0011 Linha de base pessoal, semana-padrão e tipo de treino, ADR: 0015 Caixa do dia do professor no piloto local (identidade, vínculo, `atencao@1` e correção do tipo), atencao@2 (caixa do dia), linha_base@3 (+11 more)

### Community 9 - "Mapa e diários de novembro"
Cohesion: 0.26
Nodes (19): 00-inicio, decisoes/0013-feedback-automatico, decisoes/0014-recuperacao-diaria, design/telas/feedback, diario/2026-11-11, diario/2026-11-12, diario/2026-11-13, diario/2026-11-16 (+11 more)

### Community 10 - "Diários de 18 e 27/11 e clima"
Cohesion: 0.12
Nodes (19): decisoes/0007-clima-da-atividade, design/auditoria-ux-e-inicio-do-atleta, design/identidade-visual-v2, design/identidade-visual-v3, design/telas/evolucao-v1, design/telas/inicio-atleta-v3, design/telas/inicio-v4, design/tokens (+11 more)

### Community 11 - "Roadmap, atenção e diário 17/11"
Cohesion: 0.20
Nodes (18): atencao@2 (caixa do dia), carga_pse@1, decisoes/0011-linha-de-base-e-semana-padrao, decisoes/0012-check-in-pos-treino, decisoes/0015-caixa-do-dia-do-professor, design/telas/treino, diario/2026-11-17, Caixa do dia (do professor) (+10 more)

### Community 12 - "Evolução e ferramentas do chat"
Cohesion: 0.11
Nodes (18): metricas/evolucao-series, Versão carga@2, Versão eficiencia@1, Versão esforcos@1, Versão frase_evolucao@1, Versão frase_evolucao@2, Versão frase_forma@1, Versão linha_base@3 (+10 more)

### Community 13 - "API e versões de métricas"
Cohesion: 0.12
Nodes (17): modulos/api, Versão atencao@2, Versão carga@1, Versão carga@2, Versão carga_pse@1, Versão checagens_chat@1, Versão checkin@1, Versão esforcos@1 (+9 more)

### Community 14 - "Diário de 28/11 e chat"
Cohesion: 0.21
Nodes (17): modulos/chat, checagens_chat@1, prompt_chat@3, checagens_feedback@6, decisoes/0004-contrato-tela-evolucao, decisoes/0016-login-e-deploy-do-piloto, decisoes/0017-chat-do-atleta, design/telas/chat (+9 more)

### Community 15 - "Fatos do treino e feedback"
Cohesion: 0.19
Nodes (14): 2026-11-10, 2026-11-11, metricas/checagens-feedback, Label docs-ok, Pacote de fatos `fatos_treino@2`: fixtures e oráculo, Versão carga_pse@1, Versão checagens_feedback@2, Versão checagens_feedback@3 (+6 more)

### Community 16 - "Carga de treino e conferência"
Cohesion: 0.22
Nodes (14): carga@2 (rTSS e hrTSS por volta), Serie diaria CTL/ATL/TSB, conferencia_carga@1 (carga vs Garmin), decisoes/0002-segmento-intensidade-e-versao, decisoes/0003-fuso-da-atividade, decisoes/0009-treino-de-transicao, decisoes/0010-carga-de-treino, metricas/carga-oraculo (+6 more)

### Community 17 - "Modelo de dados e tabelas"
Cohesion: 0.18
Nodes (13): Migrações Alembic, Modelo completo do plano (alternativa rejeitada), ADR 0001 Modelo de dados mínimo e estrutura do monorepo, Monorepo (apps/mobile, services/api, services/worker), Postgres 16, Princípio: guardar o dado bruto, Tabela atividade, Tabela segmento (+5 more)

### Community 18 - "Recuperação e Meta 10"
Cohesion: 0.24
Nodes (13): ADR: 0014 Recuperação diária (sono, VFC e FC de repouso) no contexto do treino, Recuperacao diaria: sono, VFC, FC de repouso, 2026-11-13, produto/meta-10-como-rodar, Achados do guia, Antes de começar, Derrubar tudo, Passo a passo (+5 more)

### Community 19 - "Módulo clima"
Cohesion: 0.15
Nodes (13): modulos/clima, A chamada, Arquivos principais, Como testar, Decisões do Theo (03/11), Depende de, Entradas e saídas, Falhas e tentativas (+5 more)

### Community 20 - "Glossário e ADRs 12 e 13"
Cohesion: 0.27
Nodes (12): ADR: 0012 Check-in pós-treino (PSE, sensação, observação) e `carga_pse@1`, ADR: 0013 Feedback automático por treino (pacote de fatos, guarda, camada de LLM, checagens), ADR: 0016 Login, papéis, consentimento pelo atleta e deploy do piloto, ADR: 0017 Chat do atleta com ferramentas de consulta, Camada de LLM do feedback, carga_pse@1 (carga por PSE), Checagens do feedback automatico, Groq no chat do atleta (+4 more)

### Community 21 - "Infra e papéis"
Cohesion: 0.17
Nodes (12): modulos/infra, Arquivos principais, Como testar, Depende de, Entradas e saídas, Para que serve, Pendências, Porta do Postgres ocupada (+4 more)

### Community 22 - "Camada de LLM"
Cohesion: 0.18
Nodes (11): modulos/camada-llm, Arquivos principais, Entradas e saídas, Limitações, Para que serve, Prompt `feedback_prompt@9` (`app/llm/prompt_feedback.py`), Quem usa: `app/servicos/feedback.py` e `worker.gerar_feedback` (#327), Regras (+3 more)

### Community 23 - "Script de contraste"
Cohesion: 0.38
Nodes (10): calcular(), documento_atualizado(), ler_cores(), luminancia(), main(), num(), Contraste WCAG 2.x dos pares de cor do guia visual (issue #192).  Lê as cores da, Luminância relativa sRGB (WCAG 2.2). (+2 more)

### Community 24 - "Meta 11: caixa do dia"
Cohesion: 0.28
Nodes (9): 2026-11-16, atencao, atencao-oraculo, Meta 11: caixa do dia do professor, Meta 11: como rodar a caixa do dia do professor, Achados do guia, Antes de começar, Limitações da conferência local (#431) (+1 more)

### Community 25 - "Diário de 10/11 e decisões"
Cohesion: 0.22
Nodes (9): design/telas/checkin, diario/2026-11-09, diario/2026-11-10, Angelo aprova as cinco decisoes do check-in (ADR 0012), Check-in pos-treino, modulos/mobile, produto/meta-8-como-rodar, produto/metas/meta-8-check-in (+1 more)

### Community 26 - "Fatos do treino e versões"
Cohesion: 0.22
Nodes (9): metricas/fatos-treino, Versão carga@2, Versão carga_pse@1, Versão checagens_feedback@6, Versão esforcos@1, Versão fatos_treino@2, Versão feedback_prompt@9, Versão linha_base@2 (+1 more)

### Community 27 - "Deploy da Meta 13 e plano do MVP"
Cohesion: 0.22
Nodes (9): produto/meta-13-opcoes-deploy, Fora, Hospedagem na DigitalOcean (fontes: [App Platform](https://www.digitalocean.com/, Login (o que cada opção pede), O que muda no código e no repositório (para a #504), O que o piloto precisa, PRECISA DO ANGELO, Região: não há no Brasil (+1 more)

### Community 28 - "Gráfico dos tiros"
Cohesion: 0.25
Nodes (8): modulos/grafico-tiros, Arquivos principais, Como testar, Depende de, Entradas e saídas, Escala mínima dos eixos (issue #63), Para que serve, Pendências

## Knowledge Gaps
- **293 isolated node(s):** `App de análise de treinos com contexto`, `Monorepo (apps/mobile, services/api, services/worker)`, `Migrações Alembic`, `Postgres 16`, `Theo (tech lead)` (+288 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **6 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `glossario` connect `Glossário e ADRs 12 e 13` to `App, telas e design`, `Worker, carga e Meta 12`, `Banco e guias das metas 7 a 8`, `Roadmap e esforços`, `Linha de base e fuso`, `Mapa e diários de novembro`, `Diários de 18 e 27/11 e clima`, `Roadmap, atenção e diário 17/11`, `Evolução e ferramentas do chat`, `Diário de 28/11 e chat`, `Fatos do treino e feedback`, `Carga de treino e conferência`, `Recuperação e Meta 10`, `Meta 11: caixa do dia`, `Diário de 10/11 e decisões`, `Fatos do treino e versões`?**
  _High betweenness centrality (0.209) - this node is a cross-community bridge._
- **Why does `modulos/api` connect `API e versões de métricas` to `App, telas e design`, `Worker, carga e Meta 12`, `Banco e guias das metas 7 a 8`, `Roadmap e esforços`, `Ingestão Garmin e Meta 1`, `Contrato da tela e api-client`, `Guias das metas 2 a 4`, `Linha de base e fuso`, `Evolução e ferramentas do chat`, `Diário de 28/11 e chat`, `Fatos do treino e feedback`, `Modelo de dados e tabelas`, `Recuperação e Meta 10`, `Módulo clima`, `Glossário e ADRs 12 e 13`, `Infra e papéis`, `Camada de LLM`, `Meta 11: caixa do dia`, `Fatos do treino e versões`, `Deploy da Meta 13 e plano do MVP`, `Gráfico dos tiros`?**
  _High betweenness centrality (0.128) - this node is a cross-community bridge._
- **Why does `ADR 0004 Contrato da tela de evolução dos tiros (Meta 2)` connect `Contrato da tela e api-client` to `App, telas e design`, `Mapa, metas e templates`, `Worker, carga e Meta 12`, `Banco e guias das metas 7 a 8`, `Roadmap e esforços`, `Ingestão Garmin e Meta 1`, `Guias das metas 2 a 4`, `Linha de base e fuso`, `API e versões de métricas`, `Fatos do treino e feedback`, `Recuperação e Meta 10`, `Módulo clima`, `Glossário e ADRs 12 e 13`, `Infra e papéis`, `Meta 11: caixa do dia`, `Gráfico dos tiros`?**
  _High betweenness centrality (0.127) - this node is a cross-community bridge._
- **What connects `App de análise de treinos com contexto`, `Monorepo (apps/mobile, services/api, services/worker)`, `Migrações Alembic` to the rest of the system?**
  _293 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `App, telas e design` be split into smaller, more focused modules?**
  _Cohesion score 0.14747474747474748 - nodes in this community are weakly interconnected._
- **Should `Mapa, metas e templates` be split into smaller, more focused modules?**
  _Cohesion score 0.08292682926829269 - nodes in this community are weakly interconnected._
- **Should `Worker, carga e Meta 12` be split into smaller, more focused modules?**
  _Cohesion score 0.11379800853485064 - nodes in this community are weakly interconnected._