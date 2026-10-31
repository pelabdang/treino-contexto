---
tipo: roteiro
status: em-uso
dono: paulo
atualizado: 2026-10-31
links: [[produto/plano-mvp-execucao]], [[decisoes/0001-modelo-de-dados-minimo]], [[00-inicio]]
---
# Roteiro de metas

Metas em ordem, cada uma com no máximo 1 semana de trabalho. Só se trabalha em issues da **meta atual**.
Ao fechar uma meta, o Paulo registra o resultado em `docs/produto/metas/` e revisa este roteiro.

| Meta | Tema | Situação |
|---|---|---|
| 0 | Fundação: monorepo, modelo mínimo, CI, base de docs | feita (#1, #3) |
| **1** | **Tiros de 1 km a partir da exportação Garmin** | **atual** |
| 2 | Evolução dos tiros no app | esboço |
| 3 | Upload de arquivo FIT | esboço |
| 4 | Clima de cada atividade | esboço |
| 5 | Carga e linha de base pessoal | esboço |
| 6 | Check-in pós-treino | esboço |
| 7 | Feedback automático por treino | esboço |
| 8 | Caixa do dia do professor | esboço |
| 9 | Agente do atleta (primeiras perguntas) | esboço |

---

## Meta 1: tiros de 1 km a partir da exportação Garmin (atual)

### Objetivo
Provar o caminho completo do dado: exportação da Garmin, banco, métrica determinística, gráfico e API.
Definida pelo Angelo: ler a exportação em `dados-teste/garmin/`, guardar as atividades no Postgres local e
mostrar a evolução dos tiros de 1 km dos intervalados de corrida (pace e FC médios por sessão).

### Entrega visível
- `entregas/meta-1/tiros-1km-atleta-<id>.png`: dois painéis com o mesmo eixo X (data do treino, `dd/mm/aa`).
  Em cima, "Pace médio dos tiros (min/km)", eixo invertido (mais rápido para cima); embaixo,
  "FC média dos tiros (bpm)". Um ponto por sessão. Junto vai um `.csv` com a mesma série.
- `GET /atletas/{atleta_id}/evolucao/tiros-1km` (JSON) e `GET /atletas/{atleta_id}/evolucao/tiros-1km.png`.
  O formato exato está em #15 (gráfico) e #16 (JSON).
- `entregas/` e `dados-teste/` ficam fora do git: o gráfico com dado real é dado pessoal.

### Critério de pronto
- [ ] Com as fixtures sintéticas (`tests/fixtures/garmin/`), num clone limpo e seguindo só a documentação:
      importar, gerar o PNG e o CSV e chamar os dois endpoints (Bia, #18).
- [ ] Pace e FC de cada sessão batem com o cálculo à mão a partir da tabela das fixtures.
      Pace da sessão = soma das durações dos tiros / soma das distâncias x 1000; FC = média ponderada pela duração.
- [ ] Reimportar a mesma exportação não duplica atividades nem segmentos.
- [ ] Rodagem leve com auto-lap de 1 km, natação e intervalado sem arquivo FIT ficam fora da série.
- [ ] Check `testes` verde (SQLite local e Postgres no CI) e "docs ok" da Nina em todos os PRs.
- [ ] Notas: [[modulos/ingestao-garmin]], [[metricas/tiros-1km]], ADR 0002 e o passo a passo de reprodução.
- [ ] **Com dado real (quando o Angelo desbloquear, #19):** a exportação do Angelo importada no Postgres local,
      PNG gerado e conferido com 2 ou 3 treinos de que ele se lembra.

### Issues e ordem
| # | Issue | Dono | Depende de | Situação |
|---|---|---|---|---|
| #8 | Formato da exportação Garmin e fixtures sintéticas | duda-dados | (#1, feita) | feita |
| #9 | ADR 0002: intensidade da volta e versão do cálculo no `segmento` | duda-dados (aprovação do Theo) | (#1, feita) | feita |
| #10 | Parser da exportação Garmin (JSON e FIT) | duda-dados | #8 | feita |
| #11 | Detecção dos tiros de 1 km numa corrida | caio-ciencia | (#1, feita) | feita |
| #12 | Agregação por sessão (pace e FC médios) | caio-ciencia | #11 | feita |
| #29 | `versao_deteccao` (`tiros_1km@1`) em `SessaoTiros`/`PontoSessao` | caio-ciencia | (#12, feita) | feita |
| #30 | Oráculo das fixtures: pace e FC por sessão calculados à mão | caio-ciencia | (#8, #12, feitas) | feita |
| #13 | Importar no banco (idempotente) | duda-dados | #9, #10 | feita |
| #14 | Classificar tiros no banco e montar a série (data local da sessão, ADR do fuso) | duda-dados | #12, #13, #29 (referência: #30) | em andamento (ADR 0003, fuso) |
| #15 | Gráfico em `entregas/` | duda-dados | #14 | a fazer |
| #16 | Endpoint da API (JSON e PNG) | duda-dados | #14, #15 | a fazer |
| #17 | Documentação da Meta 1 e diário do ciclo | nina-docs | #16 | a fazer |
| #18 | QA de ponta a ponta com fixtures | bia-qa | #16, #17 (oráculo #30) | a fazer |
| #19 | Validar com a exportação real e o Postgres local | duda-dados (com bia-qa) | #18 e itens do Angelo | bloqueada (itens do Angelo) |

Caminhos paralelos: a Duda começa por #8 e #9; o Caio faz #11 e #12 ao mesmo tempo, com voltas montadas à mão.
Os dois se encontram em #14. Depois de #12, o Caio faz #29 e #30, que servem de referência para #14 e #18.
Manutenção do roteiro (paulo-planejador): #27 (feita), #36.

### Quem participa
- **duda-dados:** ingestão, banco, gráfico e API.
- **caio-ciencia:** regra dos tiros de 1 km e agregação por sessão, com testes calculados à mão.
- **nina-docs:** revisa as notas a cada PR ("docs ok"), fecha a documentação e escreve o diário (#17).
- **bia-qa:** entra em #18 para conferir o critério de pronto de ponta a ponta, e repete com o dado real em #19.
- **Theo:** aprova a ADR 0002 (#9) e faz os merges.
- **rafa-app:** não participa da Meta 1; entra na Meta 2.

### Fora desta meta
Tela no app; upload de FIT pela API; outras distâncias de tiro (400 m, 2 km) e outras modalidades;
clima, sono, check-in; tipo de treino confirmado pelo professor (o tipo `intervalado` entra só como sugestão
automática); séries por segundo em Parquet; webhook da Garmin; login e várias assessorias.

---

## Metas seguintes (esboço)

Revisadas ao fim de cada meta com o que se aprendeu. Ordem tirada da "Fundação de dados" do
[[produto/plano-mvp-execucao]] (seção 9), começando pelo que já dá para mostrar.

### Meta 2: evolução dos tiros no app
- **Objetivo:** o atleta vê no app (web, iOS e Android) o gráfico da Meta 1.
- **Entrega visível:** tela "Evolução dos tiros de 1 km" no Expo, com dados do endpoint da Meta 1.
- **Critério de pronto:** cliente TypeScript gerado do OpenAPI em `packages/api-client/`; tela com estado
  vazio, carregando e erro; `npm test` cobrindo os três estados.
- **Quem:** rafa-app, duda-dados (cliente gerado), bia-qa.
- **Fora:** login, outras métricas, edição de dados.

### Meta 3: upload de arquivo FIT
- **Objetivo:** plano B enquanto a API da Garmin não é aprovada: o atleta envia um `.fit`.
- **Entrega visível:** `POST` de upload na API e botão no app; a atividade aparece na série.
- **Critério de pronto:** reaproveita o parser da Meta 1; envio repetido não duplica; arquivo inválido dá erro claro.
- **Quem:** duda-dados, rafa-app, bia-qa.
- **Fora:** GPX/TCX, webhook da Garmin, storage em nuvem.

### Meta 4: clima de cada atividade
- **Objetivo:** cada atividade ao ar livre ganha temperatura, umidade, vento e sensação térmica.
- **Entrega visível:** clima na resposta da API e marca "indoor" em esteira.
- **Critério de pronto:** nova tabela com ADR; cliente Open-Meteo com teste usando resposta gravada.
- **Quem:** duda-dados, caio-ciencia (ajuste de pace por calor só como estimativa), Theo (ADR).
- **Fora:** previsão do tempo; ajuste por vento. Uso comercial do Open-Meteo: ver "PRECISA DO ANGELO".

### Meta 5: carga e linha de base pessoal
- **Objetivo:** primeiras métricas derivadas versionadas (rTSS/hrTSS, CTL, ATL, TSB) e a linha de base por tipo de treino.
- **Entrega visível:** gráfico de carga em `entregas/` e endpoint.
- **Critério de pronto:** cada métrica com nota em `docs/metricas/` e teste calculado à mão; aviso "ainda aprendendo" com menos de 8 treinos do tipo.
- **Quem:** caio-ciencia, duda-dados, nina-docs.
- **Fora:** motor de explicação.

### Meta 6: check-in pós-treino
- **Objetivo:** o atleta registra PSE, sensação e observação em 3 toques.
- **Entrega visível:** tela de check-in no app e dado gravado.
- **Critério de pronto:** 3 toques; "nada a relatar" válido; ADR das tabelas de check-in.
- **Quem:** rafa-app, duda-dados, bia-qa.
- **Fora:** lembrete por WhatsApp, check-in semanal.

### Meta 7: feedback automático por treino
- **Objetivo:** 3 a 5 linhas por treino, a partir de um pacote de fatos calculado.
- **Entrega visível:** feedback na tela do treino.
- **Critério de pronto:** LLM só pela camada trocável (LiteLLM, `.env`); checagem automática de que todo número do texto está no pacote de fatos; lista de linguagem proibida.
- **Quem:** caio-ciencia (pacote de fatos), duda-dados, rafa-app.
- **Fora:** resumos semanal e mensal, envio em nome do professor.

### Meta 8: caixa do dia do professor
- **Objetivo:** o professor vê quem precisa de atenção e confirma o tipo de treino sugerido em lote.
- **Entrega visível:** tela web do professor com semana-padrão e confirmação em lote.
- **Quem:** rafa-app, duda-dados, caio-ciencia.
- **Fora:** rascunho de devolutiva, painel da coordenação.

### Meta 9: agente do atleta, primeiras perguntas
- **Objetivo:** atalhos para as perguntas mais comuns ("minha evolução nos tiros de 1 km"), respondidos por consultas estruturadas.
- **Quem:** caio-ciencia, duda-dados, rafa-app.
- **Fora:** pergunta livre sem catálogo.

---

## PRECISA DO ANGELO

Bloqueios e decisões que o time não toma sozinho. O time segue planejando em volta deles.

1. **Exportação da Garmin em `dados-teste/garmin/`.** Bloqueia só a validação com dado real (#19); o resto
   da Meta 1 usa fixtures sintéticas. Há uma pasta `~/Documents/Projects/garmin` (com `your_data/`) que pode
   ser a exportação: o time **não** leu nem copiou nada de lá. Se for ela, o Angelo copia o zip (ou a pasta)
   para `dados-teste/garmin/`, que fica fora do git.
2. **Docker (ou Postgres 16) instalado na máquina.** Sem isso o Postgres local não sobe; os testes rodam em
   SQLite e no Postgres do CI. Bloqueia #19.
3. **Conferência do resultado real.** Dizer 2 ou 3 treinos de 1 km de que se lembra (data e mais ou menos o
   pace) para conferir o gráfico em #19. Dizer também se treinos em esteira e pista devem entrar no mesmo gráfico
   (padrão até lá: entram todos, com o `subtipo` guardado).
4. **Próximas metas (sem pressa para a Meta 1):** CNPJ e pedido da API da Garmin (o plano pede na primeira
   semana; a aprovação pode demorar); pedido da API do TrainingPeaks com a assessoria; plano comercial do
   Open-Meteo (Meta 4); chave do provedor de LLM, padrão Groq (Meta 7).
