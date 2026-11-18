---
tipo: design
status: rascunho
dono: lia
atualizado: 2026-11-18
links: [[design/guia-visual]], [[design/tokens]], [[design/telas/evolucao-tiros]], [[design/telas/treino]], [[design/telas/checkin]], [[design/telas/semana-padrao]], [[design/telas/consentimento]], [[design/telas/entrar]], [[design/telas/caixa-do-dia]], [[modulos/mobile]], [[produto/roadmap]]
---
# Auditoria de UX, navegação e tela inicial do atleta

Pedido do Theo (issue #530): o Angelo acha o app **cru** e quer desenvolver o front e a UX **junto com ele**, antes de qualquer
deploy. Esta nota é a primeira entrega, **sem código**, para o Angelo reagir. Tudo é rascunho: o que ele não gostar, muda.
Atletas, nomes e números dos esboços são **sintéticos**.

Base da auditoria: as capturas em `docs/design/telas/` (Chromium, tema claro e escuro) e o código de `apps/mobile`. Não vi o app
num aparelho real.

## 1. Auditoria do app como está

### Diagnóstico em uma frase
O app foi construído **por métrica** (uma tela para cada cálculo que a ciência e a API entregaram), não **por momento do atleta**
("acabei de treinar, o que eu preciso saber agora?"). Cada tela está correta e acessível; o conjunto não tem uma porta de entrada, uma
hierarquia entre as telas nem uma identidade.

### Achados que valem para o app todo
1. **A entrada é uma métrica de uma modalidade.** A tela inicial é "Evolução dos tiros de 1 km". O app atende atleta multiesporte
   (corrida, natação, ciclismo): quem treinou natação ontem abre o app e vê tiros de corrida. A entrada deveria ser "meu último treino",
   qualquer que seja.
2. **Navegação é uma pilha de links de texto.** "Semana-padrão", "Check-ins pendentes", "Enviar arquivo FIT" e o menu "Conta" têm o mesmo
   peso visual, em lista, no alto de uma tela de gráfico. Não há barra de navegação nem lugar fixo para nada. O atleta não sabe o que
   existe sem rolar.
3. **O que é urgente não aparece.** O check-in pendente (que gera o feedback, o maior valor do app) é um link com número, abaixo do
   título e acima do gráfico, sem prazo à vista.
4. **O feedback fica escondido.** Só aparece dentro da tela do treino, como terceiro cartão, depois de duração/pace e do check-in. É o
   que o atleta mais quer ler e é o que ele encontra depois de dois toques e uma rolagem.
5. **Não há histórico de treinos.** A lista "Treinos" da evolução só traz sessões de tiros de 1 km. Não existe tela com todos os treinos
   (e a API **não tem** uma rota que liste as atividades do atleta; ver "O que falta na API").
6. **Linguagem técnica na cara do atleta.** "cálculo: tiros_1km@..." no rodapé, "FC", "PSE", "UA", "CTL/ATL/TSB", "rTSS". Duas
   cargas em escalas diferentes (UA e pontos) na mesma tela, com a ressalva "não se compara". Honesto, mas é conversa de cientista.
7. **Sem identidade.** Tokens e acessibilidade estão sólidos, mas não há nome do app na tela, saudação ("Olá, Ana"), logotipo, ícone,
   ilustração nem personalidade nos estados vazios (o guia deixou "logo e ícone" fora). O app parece uma ferramenta interna.
8. **Densidade uniforme.** Quase todo cartão tem o mesmo peso (título, linhas de rótulo e valor). Falta o contraste entre "o número que
   importa" (grande) e o apoio (pequeno). Só o "melhor tiro" tem número grande.
9. **Computador é o celular esticado.** A 1280 o conteúdo fica numa coluna de até 720 com laterais vazias. Para o professor, que
   provavelmente usa computador, isso desperdiça o espaço.
10. **Texto desatualizado.** A semana-padrão ainda diz "O app ainda não tem login" (tem desde a Meta 13). A corrigir já, independente do
    redesenho.

### Tela a tela
| tela | o que funciona | o que está cru | o que falta |
|---|---|---|---|
| **Evolução dos tiros de 1 km** (entrada) | Número grande do melhor tiro; gráfico em dois painéis com alternativa em texto; lista de treinos tocável; estados e acessibilidade completos | É uma tela de uma métrica, não um início; links de ação empilhados no alto; rótulo de data do último ponto do gráfico encostando na borda direita; rodapé técnico; dois gráficos pequenos para ler no celular | Saudação, último treino de qualquer modalidade, feedback, check-in em destaque, carga e forma, acesso a todos os treinos |
| **Treino** | Dados completos (duração, pace, FC, clima); check-in editável; estados de feedback bem pensados (pronto, pendente, indisponível, prazo) | Ordem errada: o feedback é o 3º cartão; muitos cartões do mesmo tamanho (7 ou 8 em sequência); rótulos e unidades técnicas | Gráfico do treino (pace e FC ao longo do tempo), voltas, comparação com o normal à vista, ação "responder check-in" no topo, compartilhar |
| **Check-in** (4 perguntas) | Uma pergunta por tela, alvos grandes, sugestão de esforço (PSE) | Sensação de formulário; pouco retorno ao terminar (o que acontece depois?) | Tela de fechamento ("Pronto, o feedback chega em instantes") e um caminho direto para o feedback |
| **Check-ins pendentes** | Lista simples, ícone por modalidade, clara | Não diz **quanto tempo falta** para cada um; é uma tela inteira para uma lista curta; vazio sem personalidade | Prazo por item, permitir responder direto da lista, virar um bloco do Início |
| **Semana-padrão** | Cobre o caso real (vários treinos no dia, multiesporte); barra de salvar fixa; estados de erro | Formulário denso que começa por "Vale a partir de" e "Quem definiu" (metadado antes do conteúdo); é uma configuração tratada como tela principal; texto "sem login" desatualizado | Uma versão de leitura bonita ("sua semana") com um botão "Editar"; explicar para que serve (alimenta o tipo sugerido do treino) |
| **Consentimento** (PR #526) | Texto da API inteiro, estado em ícone e palavra, confirmação visível | Tela de estado de saúde/LGPD no mesmo tom de tudo; o aviso de pedido na evolução é só uma faixa | Entrada pela Conta com selo "1 pedido"; nada além disso por enquanto |
| **Entrar / trocar senha** | Rótulos visíveis, erros claros, sem jargão de segurança | Sem marca, sem boas-vindas; parece um formulário genérico | Nome do app e uma frase de apresentação; primeiro acesso que explique "por que trocar a senha" |
| **Caixa do dia** (professor) | Ordem certa (quem olhar primeiro), motivo em frase, lote de tipos | Mistura **triagem** (olhar alunos) e **tarefa administrativa** (confirmar tipos) na mesma rolagem; "Nada a destacar" repetido ocupa espaço; cartões iguais para dor e para "sem check-in" | Distinguir gravidade (dor vs. prazo), entrar na visão de um aluno, layout em duas colunas no computador, resumo no topo como número |

### O que falta na API para a experiência pedida
Sem invenção de métrica; só o que o front precisa e hoje não tem:
- **Lista de atividades do atleta** (data, modalidade, duração, se tem check-in, se tem feedback). Hoje só existe `GET .../atividades/{id}`
  e a lista de tiros. É a base do "Treinos" e do "último treino" de qualquer modalidade.
- **"Resumo do início"** em uma chamada (último treino, pendentes, carga e forma de hoje), para a tela inicial não fazer 4 chamadas.
  Opcional; dá para compor no app no começo.
- Para o professor: **visão de um aluno** (hoje só existe a caixa do dia).

## 2. Arquitetura de informação

Proposta, celular primeiro. Esboço: ![[design/telas/inicio-atleta/navegacao.svg]]

**Atleta: quatro abas na base** (no computador, menu à esquerda com os mesmos quatro itens).
| aba | o que tem | por quê |
|---|---|---|
| **Início** | o último treino com o feedback, check-in pendente em destaque, carga e forma de hoje, os 3 últimos treinos | responde "acabei de treinar, e agora?" |
| **Treinos** | todos os treinos, mais novos primeiro, filtro por modalidade, os sem check-in marcados | o histórico que não existe; absorve "Check-ins pendentes" como filtro |
| **Evolução** | tiros de 1 km, série de carga e forma, o normal (linha de base) | as análises ficam num lugar só, para quem quer estudar |
| **Conta** | Semana-padrão ("Minha semana"), Consentimento (selo se há pedido), Trocar senha, Sair, enviar arquivo FIT | tudo o que é ajuste e manutenção sai da frente do atleta |

Regras: no máximo quatro abas; **ação urgente** (check-in) aparece no Início **e** como selo na aba Treinos; o treino individual abre
por cima das abas (com "Voltar"); "Enviar arquivo FIT" vira um botão na aba Treinos (é uma ação de treino, não de conta) com a opção de
ficar também no Início quando a lista estiver vazia.

**Professor:** hoje uma tela. Proposta: **Caixa do dia** (inicial), **Alunos** (depois: lista e a visão de cada aluno, quando houver
API) e **Conta**. A caixa separa "Para olhar hoje" (alerta) de "Treinos novos" (tarefa: confirmar tipos), podendo virar duas abas
internas. No computador: duas colunas (lista à esquerda, detalhe do aluno à direita).

Decisão em aberto: a aba "Evolução" mantém o nome "tiros de 1 km" enquanto for só isso; cresce com o app (ver pergunta 5).

## 3. Tela inicial do atleta: três direções

Todas partem da mesma pilha de dados (já existentes na API: atividade, feedback, linha de base, carga e forma, check-ins
pendentes) e diferem no **que ocupa o topo**. Todos os números são sintéticos e "estimativa" continua rotulado.

### Direção A, "Hoje": o último treino manda
![[design/telas/inicio-atleta/direcao-a-hoje.svg]]
- Ordem: saudação, **faixa de check-in pendente** (só quando há), **cartão do último treino** (número grande, "dentro do seu normal", e as
  duas primeiras linhas do feedback), **carga da semana e forma** lado a lado, treinos recentes.
- Prós: responde direto à pergunta "como foi meu treino?"; o feedback (o maior valor do app) aparece sem toque extra; serve a qualquer
  modalidade; é a menor mudança em relação ao que já temos (o cartão "Último treino" já existe).
- Contras: no dia sem treino novo, o topo repete o mesmo treino de dias atrás; mostra pouco do "quadro maior" da semana.

### Direção B, "Semana": o quadro maior manda
![[design/telas/inicio-atleta/direcao-b-semana.svg]]
- Ordem: faixa da semana (dias treinados), **carga e forma em gráfico**, faixa de check-in, último treino resumido, treinos recentes.
- Prós: bom para o multiesporte que pensa em semana e em carga acumulada (estilo TrainingPeaks); incentiva a rotina.
- Contras: o gráfico de carga e forma precisa de explicação para quem não é técnico; o feedback fica menor e mais embaixo; precisa de
  decisão sobre o que a faixa mostra (só o feito, ou o previsto da semana-padrão, que é hábito e não plano).

### Direção C, "Agora": uma coisa por vez
![[design/telas/inicio-atleta/direcao-c-agora.svg]]
- Ordem: um **único cartão grande** com a próxima ação (responder o check-in); quando tudo está em dia, o cartão vira o último treino com
  feedback; abaixo, resumo curto e o último treino.
- Prós: empurra o hábito que gera o feedback; mínima carga cognitiva; ótimo no celular pequeno e ao sol.
- Contras: esconde as análises (carga, normal) para quem as quer logo; o topo muda de forma (mais difícil de aprender); para o atleta
  que sempre responde na hora, vira o A com um passo a mais.

### Recomendação
**A como base, pegando emprestado o melhor do C**: a faixa de check-in pendente já é o "agora" (aparece só quando há e some quando
não); o resto é o último treino com o feedback. A **faixa da semana do B** fica para uma segunda rodada, depois de a lista de treinos
e a API de resumo existirem e de o Angelo dizer se quer ver "semana" na entrada. Motivos: é o que o atleta mais olha ao sair do
treino (a confirmar com o Angelo, pergunta 3), é a que menos arrisca, e a que exige menos API nova.

## 4. Perguntas para o Angelo
**Referências e gosto**
1. **Quais apps você gosta** de olhar, de qualquer área (Strava, TrainingPeaks, Garmin Connect, Runna, Whoop, Apple Fitness, Nike
   Run Club, outro)? O que você gosta em cada um, e **o que detesta**? Um print ou uma frase por app já basta.
2. **Tom e cara:** mais **esportivo** (energia, cor forte, números enormes) ou mais **calmo e técnico** (papel, sóbrio, como hoje)?
   O app deve ter **nome e logotipo**? Já tem um nome em mente?

**Uso**
3. **Depois de um treino, o que você mais olha**, nessa ordem? (o número do treino, o feedback, a comparação com o seu normal, a carga
   da semana, o mapa, as voltas...) E **quanto tempo** você passa nessa tela?
4. **Celular primeiro mesmo?** Você abre no celular logo depois do treino e no computador em outro momento? E o **professor**: usa no
   celular ou no computador?
5. **Tiros de 1 km** continua sendo a análise principal ou é só a primeira que existe? O que mais você quer ver crescer em
   "Evolução" (natação, ciclismo, comparar com o ano passado)?
6. **Carga e forma** (CTL/ATL/TSB): você lê isso? Prefere ver o número, um gráfico ou uma frase ("você está carregado")? (o app
   hoje evita adjetivo de valor; me diga se quer mudar.)
7. **Check-in:** você responde logo depois do treino ou à noite? Um lembrete (notificação) ajudaria? Hoje não há notificação.

**Escopo**
8. **Histórico de treinos** com todas as modalidades é prioridade? (exige uma rota nova na API.)
9. Para o **professor**: o que ele precisa ver **em 10 segundos** de manhã? A caixa de hoje é isso, ou falta algo?
10. Quanto você quer **mudar já** (tela inicial e navegação) e quanto deixar para **depois do piloto**?

## 5. Próximos passos sugeridos
1. Angelo reage a esta nota (direções, tom, perguntas).
2. Lia refina a direção escolhida em **mais fidelidade** (tema claro e escuro, estados vazio, carregando e erro) e escreve a spec em
   `docs/design/telas/inicio-atleta.md`.
3. Theo decide a API (lista de atividades; resumo do início) com a Duda.
4. Rafa implementa a navegação por abas primeiro (sem mudar o conteúdo das telas), depois o Início.
5. Correção imediata, independente: o texto "sem login" da semana-padrão.
