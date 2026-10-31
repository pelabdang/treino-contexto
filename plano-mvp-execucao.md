# Plano de MVP e execução

*Análise de treinos com contexto · 29/10/2026 · Consolida "app-analise-treinos" e "assessoria-encaixe-proposta".*

## 1. A aposta do MVP

**Mudança principal em relação ao plano anterior:** o MVP é vendido e distribuído pela **assessoria, com o professor no meio**, mas o atleta continua tendo o seu próprio analista automático. A assessoria é quem paga, quem distribui o app para centenas de alunos e quem já tem o problema medido: os alunos param de comentar, depois faltam e por fim cancelam.

**Dois canais de feedback, complementares:**

- **Feedback automático (agente do atleta):** chega direto ao aluno, sem esperar o professor. Inclui o retorno de cada treino, o resumo semanal, quinzenal e mensal, e respostas a perguntas livres sobre a própria evolução. É o que dá ao aluno a sensação de ter um analista pessoal disponível o tempo todo.
- **Feedback do professor:** a devolutiva humana, preparada com rascunhos e contexto prontos, que decide ajustes de plano e mantém a relação.

O agente explica e mostra dados, mas não muda o plano: quando a pergunta envolve mudar treino, ele encaminha ao professor. O professor vê tudo o que o agente disse aos seus alunos.

**Hipótese a validar:** se o professor receber o contexto pronto de cada aluno (treino, sono, rotina, clima), alertas de desconexão e rascunhos de devolutiva, ele (a) gasta muito menos tempo por aluno e (b) o aluno se sente mais acompanhado, o que reduz o cancelamento.

**Posicionamento em relação ao TrainingPeaks:** o TP continua sendo a ferramenta de prescrição da assessoria (o calendário de treinos). O app é a **camada de feedback, contexto e engajamento** que o TP não faz bem. Substitui e melhora a comunicação e o feedback ao aluno, sem disputar a prescrição. Isso reduz a resistência da assessoria e o risco de o TP negar a API.

**Fora do MVP:** prescrição e calendário de treinos (ficam no TP), app nativo iOS e Android, plano de treino gerado por IA, venda direta ao atleta, integração com dezenas de relógios e conversa com IA sobre temas fora de treino, saúde e evolução.

### Usuários e o que cada um recebe

| Usuário | O que usa no MVP |
|---|---|
| Atleta | Check-in pós-treino em 3 toques (PSE, sensação, observação), 3 perguntas semanais, feedback automático por treino, semana, quinzena e mês, agente para perguntas sobre a própria evolução e a devolutiva do professor |
| Professor | Lista diária de "quem precisa de atenção", contexto pronto de cada aluno, rascunho de devolutiva para revisar e enviar |
| Coordenação | Painel com os indicadores do manual da assessoria (comentários, execução, check-in, prazo de resposta, satisfação, retenção em 90 dias) |

## 2. Frentes de execução

O trabalho se divide em seis frentes que andam em paralelo:

1. **Dados:** fontes, como obter, onde guardar e modelo de dados.
2. **Inteligência:** métricas, linha de base, explicações, base de conhecimento e geração de texto.
3. **Produto e experiência:** telas, fluxos e tom das mensagens.
4. **Engenharia e plataforma:** arquitetura, stack, segurança e custos.
5. **Piloto e métricas:** como provar valor com a assessoria.
6. **Negócio e legal:** LGPD, contratos, preço e parcerias de API.

---

## 3. Frente 1: Dados

### 3.1 Fontes, prioridade e como conseguir

| Fonte | Dados | Como conseguir | Prioridade |
|---|---|---|---|
| **Garmin Connect Developer Program** | Atividades completas (arquivo FIT com séries por segundo, voltas, potência, braçadas), sono, HRV, FC de repouso, estresse | Cadastro como empresa (precisa de CNPJ) e aprovação da Garmin. Gratuito. Dados chegam por webhook | **MVP (principal)** |
| **Upload de arquivo FIT/GPX/TCX** | Mesmo conteúdo de atividade, sem sono | Próprio app. Sem dependência | **MVP (plano B enquanto a Garmin não aprova)** |
| **Check-in próprio** | PSE, sensação, observação, motivo de falta, 3 perguntas semanais | Próprio app (web/PWA) com lembrete por WhatsApp ou e-mail | **MVP (essencial)** |
| **Clima** | Temperatura, umidade, vento, sensação térmica por hora e coordenada | Open-Meteo (histórico e previsão). O uso comercial exige plano pago, de baixo custo | **MVP** |
| **Altimetria** | Subida e descida por trecho | Do próprio arquivo, com correção por modelo de elevação se o GPS estiver ruim | **MVP** |
| **TrainingPeaks** | Treino planejado, tipo de treino, comentários dos alunos, histórico | API restrita a parceiros aprovados. Pedir junto com a assessoria, que é cliente grande deles. Quando aprovada, traz o planejado automaticamente | **Fase 2 (pedir já)** |
| **COROS, Polar, Suunto, Wahoo** | Atividades | APIs de parceiros. A da Polar é aberta | Fase 2, conforme os relógios dos alunos |
| **Apple Health / Health Connect** | Sono e atividades de outros aparelhos | Exige app nativo | Fase 3 |
| **WHOOP, Oura** | Sono e recuperação | APIs abertas com OAuth | Fase 3 |
| **Strava** | Atividades | **Evitar como base.** Os termos proíbem o uso dos dados com IA e a exibição para terceiros (o professor) | Não usar |

**Ação imediata:** levantar com a assessoria quais relógios os alunos usam. Se a Garmin cobrir de 60% a 70% dos alunos, ela basta para o piloto.

**Ordem das fontes:** a Garmin é a fonte principal do MVP, porque traz os treinos e também sono, HRV e FC de repouso, que o TP não garante. O TrainingPeaks entra na fase 2, principalmente para trazer o treino planejado e os comentários.

**Tipo de treino e planejado, classificados pelo professor:** como o professor é o administrador da carteira, é ele quem define o tipo de treino, e não o aluno. Funciona assim:

1. O professor cadastra a semana-padrão de cada aluno, ou de um grupo de alunos com o mesmo plano: "terça intervalado, quinta fartlek, sábado longo".
2. Cada treino que chega da Garmin recebe automaticamente o tipo sugerido, pelo dia da semana e pelo formato do treino (tiros, duração, intensidade).
3. O professor confirma ou corrige em lote na caixa do dia, com um clique por treino. Só os casos duvidosos pedem atenção.
4. Quando a API do TP estiver disponível, o tipo e o planejado passam a vir direto do calendário do professor, e essa etapa praticamente desaparece.

Isso tira uma tarefa do aluno, deixa a classificação mais confiável (feita por quem prescreveu) e basta para a "execução ajustada" do piloto.

### 3.2 Modelo de dados (núcleo)

- **assessoria, professor, atleta** e o vínculo professor↔atleta, com o consentimento do atleta.
- **atividade:** modalidade, início, duração, distância, resumo e tipo de treino (leve, moderado, longo, intervalado, fartlek), com origem (sugestão automática, professor ou TP) e confirmação do professor.
- **semana_padrao:** tipo de treino por dia da semana, definido pelo professor por aluno ou por grupo.
- **serie_atividade:** séries temporais por segundo (FC, pace, potência, cadência, altitude, posição), guardadas como arquivo colunar e não como linhas no banco.
- **segmento:** voltas, tiros e repetições detectados, com métricas, e com **zona** (A1, A2, limiar…) e **equipamento** (palmar, pull buoy, nadadeira) quando informados pelo professor, pelo TP ou pelo check-in.
- **bem_estar_diario:** sono (duração, fases, score), HRV, FC de repouso, estresse.
- **checkin_treino** e **checkin_semanal**.
- **clima_atividade:** condições na hora e no local do treino.
- **metrica_derivada:** carga, eficiência, pace ajustado, desacoplamento (com versão do cálculo).
- **linha_base:** a referência pessoal por métrica e por tipo de treino.
- **sinal / alerta:** gatilho, evidência, estado e o que o professor decidiu.
- **feedback:** fatos usados, rascunho gerado, texto final do professor, nota do professor.
- **pergunta_agente:** pergunta do atleta, consulta estruturada gerada, resultado, resposta, avaliação do atleta.
- **regra_conhecimento:** regra, fonte (artigo ou entrevista), versão.

Dois princípios de projeto: **guardar o dado bruto original** (arquivo FIT e JSON da API), para poder recalcular tudo quando as fórmulas mudarem, e **versionar cada métrica derivada**.

### 3.3 Onde construir

- **Banco:** PostgreSQL gerenciado (por exemplo, Supabase ou AWS RDS), de preferência na região de São Paulo. Inclui login e controle de acesso por linha (cada professor só vê os próprios alunos).
- **Arquivos brutos e séries:** armazenamento de objetos (S3 ou o storage do Supabase), com as séries em formato Parquet.
- **Ingestão:** webhooks da Garmin colocam tarefas numa fila, e workers em Python processam (leitura do FIT, clima, métricas).

### 3.4 Qualidade de dados

Esses problemas aparecem na prática e precisam de tratamento desde o início: FC óptica de pulso com picos, GPS ruim em prédios e túneis, natação em piscina sem GPS, esteira e rolo sem clima externo (marcar "indoor"), relógio usado por duas pessoas, treinos duplicados vindos de duas fontes e fuso horário. Cada atividade recebe uma **nota de qualidade**, e as análises ignoram ou avisam quando o dado não é confiável.

---

## 4. Frente 2: Inteligência

A arquitetura tem quatro camadas. **Só a última usa um modelo de linguagem**, e ela nunca calcula nada.

### 4.1 Camada 1: métricas determinísticas

- **Carga:** TSS (potência), rTSS (pace) e hrTSS (FC). Para natação, usar sTSS ou carga por PSE × duração (método de Foster). Condicionamento (CTL), fadiga (ATL) e forma (TSB).
- **Eficiência:** pace ou potência por batimento (Efficiency Factor) e desacoplamento Pa:HR nos longos.
- **Ajustes:** pace ajustado por inclinação (GAP), por calor e umidade e por vento. Mostrados sempre como estimativa.
- **Detecção de estrutura:** tiros e intervalos (a partir das voltas ou por mudança de ritmo), séries de natação.
- **Engajamento:** taxa de comentário, tamanho dos comentários, check-ins feitos, execução contra o planejado e dias sem registro.

### 4.2 Camada 2: linha de base pessoal

Cada métrica é comparada com a referência do próprio atleta, separada por tipo de treino: média móvel de 4 a 8 semanas e uma medida robusta de quanto aquele dia fugiu do normal. **Início frio:** nas primeiras semanas, sem histórico, o sistema usa valores típicos da literatura e vai personalizando aos poucos (combinação ponderada entre o valor populacional e o do próprio atleta). Com menos de 8 a 10 treinos de um tipo, o app avisa que ainda está aprendendo.

### 4.3 Camada 3: motor de explicação

Para cada treino ou semana fora do normal:

1. Detecta o desvio, por exemplo, pace 3% pior que a linha de base do intervalado.
2. Lista os fatores candidatos, cada um com seu próprio desvio: sono, carga das últimas 2 semanas, temperatura, vento, subida, horário, check-in (trabalho e estresse), FC de repouso e HRV.
3. Estima quanto de cada fator explica a diferença. No MVP usa regras com efeitos tirados da literatura, como o calor, e o histórico do atleta. A partir de alguns meses de dados, passa a usar modelos estatísticos por atleta (regressão com efeitos individuais).
4. Gera um **pacote de fatos estruturado**, com números, comparações, grau de certeza e a regra da base de conhecimento usada.

O motor nunca afirma causa: classifica cada fator como "provável", "possível" ou "sem evidência".

### 4.4 Camada 4: redação com IA

O modelo recebe o pacote de fatos, o guia de tom (o manual da assessoria mais os princípios do app) e exemplos de textos aprovados por treinadores, e escreve o feedback. São três barreiras contra erro:

- **Checagem automática:** todo número no texto precisa existir no pacote de fatos, ou o texto é descartado.
- **Linguagem proibida:** diagnóstico médico, culpa ("você falhou") e promessas.
- **Regras de envio por canal:** o feedback automático e as respostas do agente vão direto ao aluno, porque se baseiam só em fatos calculados e passam pelas checagens acima. As mensagens em nome do professor (devolutiva, roteiros do manual, alertas sensíveis como dor ou fadiga incomum) só saem com a aprovação dele. Na primeira semana do piloto, o professor pode revisar também uma amostra do feedback automático antes de liberá-lo.

### 4.5 Agente do atleta: perguntas sobre a própria evolução

O atleta pergunta em linguagem natural, e o agente responde com números, um gráfico e uma explicação. O funcionamento segue a mesma regra do resto do sistema: **a IA entende a pergunta e redige a resposta, mas quem calcula é o código.**

1. **Entender:** a IA traduz a pergunta para uma consulta estruturada: modalidade, tipo de esforço, distância ou duração, zona, equipamento, período e métrica.
2. **Buscar e calcular:** o sistema roda a consulta nos dados (segmentos, séries e métricas) e calcula a tendência, a variação e o grau de confiança.
3. **Responder:** a IA escreve a resposta com os números retornados e anexa o gráfico. Se faltar dado, diz exatamente o que falta.

**Os três exemplos:**

| Pergunta | Consulta | O que precisa existir nos dados |
|---|---|---|
| "Quanto eu melhorei nos 100 m A2 de natação com palmar?" | Natação, repetições de 100 m, zona A2, equipamento palmar, últimos N meses, pace médio por sessão e braçadas | Os comprimentos e repetições vêm do relógio. **Zona A2 e palmar não vêm do relógio**: precisam vir da descrição do treino (TP ou semana-padrão do professor) ou de uma marcação no check-in ("usei palmar"). Por isso o check-in e o cadastro do professor precisam de campos de equipamento e zona |
| "Quanto foi minha melhora em NP durante 20 min de pedal?" | Ciclismo, melhor NP em 20 min por treino (curva de potência), tendência mensal | Só o arquivo com potência. Separar rolo e rua, e treinos de teste e treinos comuns |
| "Por que meu rendimento piorou nesta semana?" | Motor de explicação (4.3) aplicado à semana contra as 4 semanas anteriores | Treinos, sono, check-ins, carga e clima. Responde com os fatores prováveis e o grau de certeza |

**Exemplo de resposta:**

> "Nos últimos 3 meses, seus 100 m A2 com palmar foram de 1:52 para 1:46 em média, uma melhora de 6 s (5%), em 11 treinos. A melhora veio junto com menos braçadas por piscina (de 18 para 16), sinal de que a técnica está ajudando. Ressalva: em 3 desses treinos a piscina era de 50 m, que costuma ser um pouco mais rápida, e eu separei esses casos no gráfico."

**Cuidados do agente:**

- **Comparar só o comparável:** mesma distância, zona, equipamento e tamanho de piscina. Quando não der, avisar.
- **Amostra pequena:** com poucos treinos, dizer "ainda há poucos dados" em vez de inventar uma tendência.
- **Limites de escopo:** não prescreve treino, não faz diagnóstico de saúde e encaminha ao professor quando a pergunta pede mudança no plano ("devo treinar menos?").
- **Perguntas frequentes viram atalhos:** as perguntas mais comuns aparecem como botões ("minha evolução no longo", "por que a semana foi pior"), o que reduz o custo e o erro.
- **Visibilidade do professor:** as perguntas e respostas aparecem na ficha do aluno. Isso também é um ótimo sinal do que preocupa cada aluno.

### 4.6 Cadência do feedback automático

| Quando | Conteúdo |
|---|---|
| Após cada treino | 3 a 5 linhas: como foi em relação ao seu normal para aquele tipo de treino, o que pesou (sono, calor, carga) e uma observação positiva |
| Semanal | Volume e carga contra o planejado, destaques, fatores externos da semana e um ponto de atenção |
| Quinzenal | Tendências dos treinos-chave e evolução por modalidade. Serve também de base para a devolutiva do professor |
| Mensal | Evolução do mês com gráficos (pace, potência, natação), recordes pessoais, consistência e o que mudou na rotina |

### 4.7 Base de conhecimento

- **Artigos:** a lista do documento anterior, conferida, vira um catálogo de regras com fonte. Por exemplo: "calor acima de X °C reduz o desempenho em corrida longa em cerca de Y% (Ely 2007)".
- **Entrevistas:** de 8 a 12 treinadores, começando pelos professores da própria assessoria. Elas viram regras de interpretação e exemplos de linguagem.
- **Aprendizado contínuo:** cada edição que o professor faz no rascunho é guardada. As edições recorrentes viram ajuste de regra ou de tom.

### 4.8 Como medir se a inteligência é boa

- **Precisão factual:** 100% dos números corretos (checagem automática mais amostragem manual).
- **Utilidade:** nota de 1 a 5 do professor em cada rascunho, e o percentual enviado sem edição ou com edição leve.
- **Alertas:** dos alunos sinalizados, quantos o professor considerou pertinentes, e quantos cancelamentos não tinham alerta antes.

---

## 5. Frente 3: Produto e experiência

### 5.1 Telas do MVP

**Atleta (web/PWA no celular):**

- Conectar Garmin ou enviar arquivo.
- Check-in pós-treino em 3 toques, que chega por link no WhatsApp minutos depois do treino sincronizar.
- Check-in semanal com 3 perguntas.
- Ver o feedback automático de cada treino e os resumos semanal, quinzenal e mensal, com gráficos.
- **Perguntar ao agente:** campo de pergunta livre e atalhos com as perguntas mais comuns. A resposta vem com número, gráfico e explicação.
- Ver a devolutiva do professor.

**Professor (web):**

- **Caixa do dia:** alunos ordenados por "precisa de atenção", com o motivo em uma linha, e os treinos novos com o tipo sugerido para confirmar em lote.
- **Semana-padrão:** cadastro do tipo de treino por dia, por aluno ou por grupo.
- **Ficha do aluno:** linha do tempo de treinos, check-ins, sono e clima, mais os gráficos de evolução.
- **Rascunho de devolutiva:** editar, aprovar e enviar. Inclui os roteiros do manual já preenchidos.

**Coordenação (web):** painel com os indicadores do piloto, por professor e por carteira.

### 5.2 Princípios de experiência

- **O check-in é o produto.** Se o aluno não preencher, nada funciona. Por isso: 3 toques, lembrete no momento certo, nunca mais de uma pergunta por vez e "nada a relatar" como resposta válida.
- **O aluno tem que ganhar algo ao preencher:** uma frase de retorno imediato, como "anotado, isso explica o pace de hoje".
- **A voz é do professor.** O feedback chega com o nome dele.
- **Nada de vigilância:** o aluno vê o que é coletado e pode desligar fontes.

### 5.3 Canal de mensagens

O WhatsApp é onde o aluno brasileiro realmente responde. No MVP, a mensagem leva um link para o check-in na web. Numa fase seguinte, o check-in pode ser feito dentro do próprio WhatsApp (API oficial da Meta, que cobra por conversa). O e-mail fica como alternativa barata.

---

## 6. Frente 4: Engenharia e plataforma

### 6.1 Arquitetura

```
Garmin (webhook) ─┐
Upload FIT ───────┼─> API de ingestão ─> Fila ─> Workers Python
Check-in (web) ───┘                               │  ├─ leitura FIT e qualidade
                                                  │  ├─ clima (Open-Meteo)
                                                  │  ├─ métricas e linha de base
                                                  │  ├─ motor de explicação
                                                  │  └─ redação (LLM) + checagem
                                                  v
                    PostgreSQL + Storage (bruto e Parquet)
                                                  │
                          Web app (atleta, professor, coordenação)
                                                  │
                                  WhatsApp / e-mail (lembretes e envio)
```

### 6.2 Stack sugerida

- **Backend e dados:** Python (FastAPI), com bibliotecas para ler FIT, pandas/Polars e um job agendado para os recálculos noturnos.
- **Frontend:** Next.js (React) como PWA, com uma biblioteca de gráficos.
- **Banco e login:** Supabase (Postgres, autenticação e storage) para ir rápido. Dá para migrar para AWS depois.
- **IA:** API do Claude, usando um modelo menor e mais barato para os rascunhos do dia a dia e um modelo maior para o resumo quinzenal.
- **Observabilidade:** logs, alertas de falha de ingestão e um painel de custo de IA por atleta.

### 6.3 Segurança e privacidade desde o início

Controle de acesso por linha (professor só vê os próprios alunos), criptografia, registro de quem acessou o quê, exclusão de dados a pedido e separação entre dados de saúde e dados de cadastro.

### 6.4 Custo estimado do piloto (ordem de grandeza, por mês)

- Hospedagem e banco: US$ 25 a 100.
- Clima (plano comercial): na faixa de dezenas de dólares.
- IA: centavos por atleta por semana, se o volume de texto for controlado. Para 100 atletas, abaixo de US$ 50.
- WhatsApp: se usar a API oficial, cobrança por conversa. No MVP, só com link, o custo é próximo de zero.

São valores estimados que precisam ser confirmados nas tabelas de preço atuais.

### 6.5 Processo de desenvolvimento

Repositório único, testes automatizados das métricas com treinos reais anonimizados (o valor esperado é calculado à mão uma vez), ambiente de homologação com dados de teste e entregas semanais mostradas ao professor-piloto.

---

## 7. Frente 5: Piloto e métricas

### 7.1 Formato

Encaixar no piloto que o próprio manual da assessoria propõe:

- 2 a 3 professores e 40 a 60 atletas, com pelo menos 60% usando Garmin.
- 4 semanas de linha de base antes do piloto, com os dados que eles já têm.
- 30 dias de uso, com avaliação de retenção aos 90 dias.
- Se possível, um **grupo de comparação**: professores ou carteiras parecidos sem o app. O próprio manual reconhece que sem comparação não dá para provar causa.

### 7.2 Métricas de sucesso

| Para quem | Métrica | Meta inicial (a calibrar) |
|---|---|---|
| Assessoria | Taxa de comentários pós-treino | Subir para 80% ou mais (meta do manual) |
| Assessoria | Participação no check-in semanal | 90% ou mais (meta do manual) |
| Assessoria | "Sinto-me acompanhado(a)" (0 a 10) | Subir em relação à linha de base |
| Assessoria | Retenção aos 90 dias | Maior que no grupo de comparação |
| Professor | Minutos por aluno por semana | Reduzir pela metade |
| Professor | Rascunhos enviados com pouca edição | 60% ou mais ao fim do piloto |
| Produto | Atletas ativos no check-in na semana 4 | 70% ou mais |
| Inteligência | Erros factuais nos textos | Zero |
| Agente | Perguntas respondidas com dado correto (amostra revisada) | 90% ou mais |
| Agente | Atletas que fazem pelo menos 1 pergunta por semana | 40% ou mais |
| Agente | Respostas avaliadas como úteis pelo atleta | 80% ou mais |

### 7.3 Critério de decisão ao fim do piloto

- **Seguir e cobrar:** professores pedem para continuar, o tempo por aluno cai de forma clara e o engajamento sobe.
- **Ajustar:** o engajamento sobe mas o professor não economiza tempo, ou o contrário.
- **Repensar:** os alunos não fazem check-in mesmo com 3 toques.

---

## 8. Frente 6: Negócio e legal

- **Empresa:** é preciso ter CNPJ para pedir as APIs (Garmin, TrainingPeaks) e assinar com a assessoria.
- **LGPD:** dados de saúde são dados sensíveis. São necessários consentimento específico do atleta, contrato de tratamento de dados com a assessoria (definindo papéis de controlador e operador), política de privacidade, encarregado de dados e plano de resposta a incidentes. Vale uma consulta com advogado antes do piloto.
- **Contrato do piloto:** gratuito por 30 a 90 dias, com acesso aos resultados anonimizados e às entrevistas com os professores, e opção de preço combinada antecipadamente para depois do piloto.
- **Preço a testar:** por atleta ativo por mês, pago pela assessoria (por exemplo, R$ 5 a 15 por atleta, ou faixas por tamanho de carteira). Validar no piloto quanto vale o tempo economizado do professor.
- **Parcerias:** a candidatura à API do TrainingPeaks fica mais forte com a assessoria apoiando. Pedir a da Garmin na primeira semana, porque a aprovação pode demorar.
- **Propriedade intelectual:** as regras e os textos treinados com os professores são o ativo do produto. Isso precisa estar claro no contrato.

---

## 9. Cronograma (cerca de 16 semanas até o resultado de 90 dias)

| Semanas | Fase | Entregas |
|---|---|---|
| 1 a 2 | **Descoberta** | Reunião com a assessoria, levantamento de relógios, 4 a 6 entrevistas com professores, pedidos de API (Garmin e TrainingPeaks), CNPJ e assessoria jurídica, linha de base dos indicadores |
| 3 a 6 | **Fundação de dados** | Upload FIT e Garmin, clima, métricas e linha de base, ficha do aluno para o professor (só leitura). Testar com dados históricos de 5 a 10 voluntários |
| 7 a 10 | **Inteligência e fluxo** | Check-in pós-treino e semanal, feedback automático por treino e semanal, alertas de atenção precoce, motor de explicação, rascunhos de devolutiva, painel da coordenação |
| 9 a 11 | **Agente do atleta** | Perguntas sobre evolução (com atalhos para as mais comuns) e resumos quinzenal e mensal. Começa com um catálogo de consultas e se amplia conforme as perguntas reais |
| 11 | **Ensaio** | 1 professor e 10 atletas por uma semana. Corrigir atrito |
| 12 a 15 | **Piloto (30 dias)** | 2 a 3 professores, 40 a 60 atletas. Revisão semanal das métricas e das edições dos professores |
| 16 | **Avaliação** | Relatório para a chefia da assessoria e decisão de continuar ou ajustar |
| até ~24 | **Retenção 90 dias** | Medir a coorte. Proposta comercial |

## 10. Time mínimo

- **Produto e relação com a assessoria:** Angelo.
- **Engenharia full-stack e dados:** 1 pessoa sênior, ou Angelo com apoio de Claude Code nos agentes do projeto.
- **Ciência do esporte:** um consultor, que pode ser um dos professores da assessoria, remunerado por horas, para validar regras e textos.
- **Jurídico:** consulta pontual de LGPD.

## 11. Principais riscos e como mitigar

| Risco | Mitigação |
|---|---|
| Aprovação da Garmin demora | Upload de FIT como plano B. Pedir na semana 1 |
| Alunos não fazem check-in | 3 toques, lembrete por WhatsApp, retorno imediato e o próprio professor pedindo |
| Professor não confia no texto da IA | Mostrar a evidência junto, checagem de números, professor sempre aprova |
| Texto errado ou com tom ruim chega ao aluno | Checagem de números, lista de linguagem proibida e aprovação do professor nas mensagens em nome dele. Revisão de amostra do feedback automático no início do piloto |
| Agente contradiz o professor ou prescreve treino | Escopo limitado a explicar dados. Perguntas sobre mudança de plano são encaminhadas ao professor |
| Dados insuficientes para a pergunta (ex.: palmar, zona A2) | Campos de equipamento e zona no check-in e no cadastro do professor. O agente diz claramente o que falta |
| A assessoria vê o app como concorrente do TrainingPeaks | Posicionar como complemento: contexto e comunicação, não prescrição |
| LGPD com dado sensível | Consentimento, contrato e acesso restrito desde o primeiro dia |
| Piloto sem grupo de comparação não prova nada | Pedir carteiras de comparação e medir tempo do professor, que é mais fácil de provar |

## 12. Decisões que precisam de você

1. Confirmar o modelo: venda e distribuição via assessoria (B2B), com feedback automático e agente direto para o atleta mais a devolutiva do professor.
2. Quem constrói: você com Claude Code, um sócio técnico ou um desenvolvedor contratado.
3. Abrir CNPJ e fazer o pedido da API da Garmin já na próxima semana.
4. Quem na assessoria será o patrocinador do piloto e quais professores participam.
