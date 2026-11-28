---
tipo: design
status: proposto
dono: lia
atualizado: 2026-11-28
links: [[design/identidade-visual-v3]], [[design/telas/inicio-v4]], [[design/telas/inicio-atleta-v3]], [[design/telas/checkin]], [[design/telas/semana-padrao]], [[design/tokens]], [[modulos/mobile]]
---
# Início v5: spec final (mistura) e direções descartadas

Pedido do Theo (28/11, issue #589). O Angelo achou o [[design/telas/inicio-v4]] melhor e quer **mais opções**. Aqui estão **3 hierarquias**
diferentes para o mesmo conteúdo. **Nada aqui muda o app.** Depois da escolha, esta nota vira a especificação completa (estados, textos e acessibilidade).
Atleta (Ana) e números **sintéticos**. Identidade v3: volt, Barlow Condensed, cantos discretos ([[design/identidade-visual-v3]]); cores de [[design/tokens]].

## Spec final: a mistura escolhida pelo Angelo (28/11)
O Angelo escolheu uma **mistura das três** com o **chat em tamanho médio**. Montagem proposta pela Lia, em 3 linhas:
1. **Panorama da semana (C)** é a base: "Esta semana" com os 7 dias dá o contexto em 3 segundos. Com pendência ele encolhe para uma linha; sem pendência ele é o herói.
2. **Check-in grande (A) só com pendência:** o cartão volt abre a tela quando há treino sem check-in e **some** quando está em dia (o produto pede a ação só quando ela existe; sem cartão vazio).
3. **Chat médio (nem B nem C):** título, caixa de 48 e uma fileira de perguntas prontas que rola de lado (a terceira aparece cortada, para mostrar que há mais), logo abaixo do check-in ou da semana.

### Com check-in pendente
![[design/telas/inicio-v5/inicio-v5-final-pendente-claro.svg]]
![[design/telas/inicio-v5/inicio-v5-final-pendente-escuro.svg]]

### Sem pendência (check-ins em dia)
![[design/telas/inicio-v5/inicio-v5-final-em-dia-claro.svg]]
![[design/telas/inicio-v5/inicio-v5-final-em-dia-escuro.svg]]

### Ordem, regras e textos
| # | bloco | aparece quando | texto (pronto da API, exceto rótulos fixos) |
|---|---|---|---|
| 1 | saudação | sempre | "Olá, Ana" e a data |
| 2 | cartão de check-in grande | há treino com `checkin_aberto` e sem check-in | "Como foi a natação de ontem?"; "3 perguntas, uns 30 segundos. Você recebe o feedback deste treino."; botão "Responder o check-in"; "+ N treino(s) sem check-in" se houver mais |
| 3 | esta semana | tem ao menos 1 treino na semana | pendente: linha com "3 treinos · 2 h 37 min" e os 7 dias; em dia: número grande, "semana passada: 4" e os 7 dias |
| 4 | Pergunte ao seu treino | sempre (depende do chat da Meta 14) | título com "Conversas ›" (lista de conversas); caixa "Ex.: como foi minha semana?"; perguntas prontas **fixas no app** (as 3 primeiras da lista de spec do chat (PR #621)); botão "Enviar pergunta". Toque numa pergunta pronta abre o chat e envia; toque na caixa abre o chat com o teclado |
| 5 | hoje e último treino (par) | só **sem pendência** (com pendência o último treino já está no cartão de check-in); "Hoje" só com semana-padrão | "Corrida leve · da sua rotina"; "0:45:12 · Natação · qui 20/03" |
| 6 | check-ins em dia | só sem pendência e com ao menos 1 check-in | "✓ Check-ins em dia" e "Ver feedback ›" |
| 7 | seu professor | sempre | conectado: "Carlos vê seus treinos e check-ins" (toque abre a conexão); sem conexão: "Tem um código do seu professor?" e "Digitar ›" |
| 8 | abaixo da dobra | como na [[design/telas/inicio-v4]] | quinzena, "Seus números" e treinos recentes |

- **Dia da semana:** ✓ com a cor da modalidade (ter corrida, qua ciclismo, qui natação); hoje tem anel; dia sem treino fica cinza. O ✓ e o anel dizem o estado sem a cor.
- **Perguntas prontas:** alvo de 44 de altura; o texto é fixo no app (sem rota; ver spec do chat (PR #621)); a fileira tem rolagem horizontal e cada botão é focável.
- **Estados do chat:** carregando = esqueleto da fileira; erro = a fileira some e a caixa fica ("Não deu para carregar as perguntas prontas. Você ainda pode escrever.").
- **O convite do professor** e a linha do professor dividem o mesmo lugar; um atleta nunca vê os dois.
- O app não calcula nada: "3 treinos", "2 h 37 min" e as frases vêm prontas.

## Direções descartadas (28/11)
As três direções abaixo **foram descartadas** em favor da mistura acima. Ficam como registro.

## O que entrava em qualquer direção
- **Chat "Pergunte ao seu treino":** caixa aberta e botões com perguntas prontas. O chat responde qualquer pergunta sobre os treinos.
- **Check-in:** é o produto. O professor passa o treino em outra plataforma; aqui o atleta só faz o check-in ([[design/telas/checkin]]).
- **Seu professor:** com conexão, uma linha com o nome; sem conexão, o convite "Tem um código do seu professor?" (código de convite, Meta 15).
- **Regra do app:** ele não calcula. Os textos das perguntas prontas, "3 treinos", "2 h 37 min" e "Em movimento" vêm prontos da API.
- Os esboços mostram a **primeira tela** (390 por 844), sem rolar. O que não cabe fica abaixo, na ordem da v4 ([[design/telas/inicio-atleta-v3]]).

### (descartada) Direção A: o check-in à frente
Claro e escuro:
![[design/telas/inicio-v5/inicio-v5-a-checkin-claro.svg]]
![[design/telas/inicio-v5/inicio-v5-a-checkin-escuro.svg]]

- **Prioriza:** o check-in. Um cartão volt grande com a pergunta ("Como foi a natação de ontem?"), os 3 passos e o botão. É a ação que vira o produto.
- **Sacrifica:** o último treino perde o cartão próprio (vira cabeçalho do check-in) e a quinzena desce. O chat fica numa linha com 2 botões.
- **Quando o check-in está em dia:** o cartão volt some e o chat sobe para o lugar dele; a tela fica como a direção B, mais leve.

### (descartada) Direção B: o chat à frente
Claro e escuro:
![[design/telas/inicio-v5/inicio-v5-b-chat-claro.svg]]
![[design/telas/inicio-v5/inicio-v5-b-chat-escuro.svg]]

- **Prioriza:** perguntar. Um painel com a caixa aberta e 4 perguntas prontas. É o caminho mais curto para "o que quero saber agora" e mostra a novidade do produto.
- **Sacrifica:** o check-in vira faixa fina e a quinzena e "Seus números" saem da primeira tela (um rolar). Depende de o chat ser bom: se a resposta decepcionar, o topo decepciona.
- **Professor:** aqui aparece o convite pontilhado (atleta ainda sem conexão), que some quando conecta e vira a linha "Seu professor".

### (descartada) Direção C: a semana e os números à frente
Claro e escuro:
![[design/telas/inicio-v5/inicio-v5-c-semana-claro.svg]]
![[design/telas/inicio-v5/inicio-v5-c-semana-escuro.svg]]

- **Prioriza:** o panorama. "Esta semana" em número grande com os 7 dias (✓ em cada treino feito, cor da modalidade, hoje com anel), mais hoje, último treino e "Em movimento". Lê-se em 3 segundos.
- **Sacrifica:** o check-in vira faixa de uma linha e o chat vira uma **barra fixa** acima das abas (menos destaque, sempre à mão). O contexto do produto ("o check-in é o produto") fica menos visível.
- **Professor:** linha "Seu professor" leve; sem conexão, o convite entra no lugar dela.

### Comparação das descartadas
| | A: check-in | B: chat | C: semana e números |
|---|---|---|---|
| primeira ação | responder o check-in | fazer uma pergunta | olhar a semana |
| melhor para | atleta que treina e responde todo dia | atleta curioso, que consulta | atleta que quer ver o conjunto |
| risco | repetitivo quando não há check-in pendente | o topo depende da qualidade do chat | o check-in pode ser esquecido |
| cartão grande | check-in | chat | semana |

### Para a escolha (respondida)
Não precisa ser uma só: dá para **mesclar** (por exemplo, C com a faixa de check-in grande da A quando há pendência). Pergunta ao Angelo: qual das três
é o ponto de partida, e o chat deve ser caixa grande (B), caixa média (A) ou barra fixa (C)?

## Acessibilidade (valem nas três)
- Alvos de toque de 44 ou mais (botões e perguntas prontas com altura 44 a 48; a caixa do chat com 48 a 56).
- Pares de cor da tabela de contraste de [[design/tokens]]: texto sobre volt é `cor.sobre-marca`; link no claro é `cor.link`.
- Nada só por cor: cada dia da semana tem o ✓ e o anel de hoje; cada modalidade tem glifo e nome.
- A caixa do chat tem rótulo falado "Pergunte ao seu treino" e o botão de enviar se chama "Enviar pergunta".
