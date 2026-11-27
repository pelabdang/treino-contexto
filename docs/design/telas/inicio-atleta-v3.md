---
tipo: design
status: rascunho
dono: lia
atualizado: 2026-11-27
links: [[design/identidade-visual-v3]], [[design/telas/inicio-atleta]], [[design/auditoria-ux-e-inicio-do-atleta]], [[design/telas/treino]], [[design/telas/checkin]], [[design/telas/feedback]], [[metricas/serie-carga]], [[metricas/linha-base]], [[modulos/mobile]]
---
# Telas v3 do atleta: início, treino, lista de treinos e quinzena (especificação)

Aplica as decisões do Angelo de 18/11 à [[design/telas/inicio-atleta]] (v2). Tokens, fontes, cantos e logo estão em
[[design/identidade-visual-v3]]. **Nada aqui muda o app** até o Angelo aprovar; depois, o Rafa implementa por partes.
O nome **Pulso** é de trabalho e não está confirmado. Atleta (Ana), treinos e números **sintéticos**.

**Linha do tempo dos esboços (vale para todos):** hoje é **sexta, 21/03/25**. Treinos: natação qui 20/03 07:00 (0:45:12, 1.800 m),
ciclismo qua 19/03 06:30 (0:52:10, 24,1 km), corrida intervalada ter 18/03 06:30 (10,00 km, melhor tiro 4:11), corrida longa sáb 15/03,
corrida leve qui 13/03. A quinzena vai de **07/03 a 20/03** (14 dias, "até ontem"). Check-in tem **3 perguntas**
([[design/telas/checkin]]) e prazo de **7 dias** depois do treino, que só a API conhece (campo `checkin_aberto`).

## O que mudou em relação à v2
| ponto | v2 | v3 |
|---|---|---|
| ordem do início | "Agora" (check-in) no topo | **último treino primeiro**; o convite do check-in desce e vira faixa |
| cantos | 24, 20 e 14 | 14, 12 e 8 |
| fonte dos números | Barlow Condensed (proposta) | Barlow Condensed (decidida) |
| cor de marca | volt (proposta) | volt `#C6F432` (decidida) |
| gráfico dos 14 dias | duas linhas (proposta) | duas linhas e frase de análise (decidido) |
| ordem do treino | proposta | **aprovada** |
| lista de treinos | não existia | aba Treinos (esta nota) |

## 1. Início v3
Dois cenários, os dois no celular claro e escuro; o computador mostra o cenário 2.

**Cenário 1: o último treino ainda não tem check-in** (`inicio-v3-celular-junto-*`).
![[design/telas/inicio-atleta/inicio-v3-celular-junto-claro.svg]]
![[design/telas/inicio-atleta/inicio-v3-celular-junto-escuro.svg]]

**Cenário 2: o último treino tem feedback** (`inicio-v3-celular-*` e `inicio-v3-computador-*`).
![[design/telas/inicio-atleta/inicio-v3-celular-claro.svg]]
![[design/telas/inicio-atleta/inicio-v3-celular-escuro.svg]]
![[design/telas/inicio-atleta/inicio-v3-computador-claro.svg]]
![[design/telas/inicio-atleta/inicio-v3-computador-escuro.svg]]

### Objetivo
Em cinco segundos: "como foi o último treino, o que falta responder e como estou na quinzena".

### Hierarquia (de cima para baixo)
1. **Saudação:** símbolo, "Olá, Ana" e a data de hoje.
2. **Cartão "Último treino"** (o mais recente de **qualquer** modalidade): ícone, modalidade, dia e hora, tipo; o **número do treino**
   (tabela abaixo); a linha de apoio; o selo de normal; e o fecho, que depende do cenário:
   - **cenário 1, sem check-in:** faixa **volt** dentro do cartão: "Responda o check-in e receba o feedback deste treino." e o botão
     "Responder o check-in (3 perguntas)"; abaixo, "+ N treino(s) sem check-in" quando há outros;
   - **cenário 2, com feedback:** as três primeiras linhas do feedback, "Texto de exemplo." (no app, o aviso da [[design/telas/feedback]]
     de que o texto é automático) e "Ler feedback completo". Se **outro** treino ainda não tem check-in, uma **faixa volt** logo abaixo
     do cartão: "Como foi o ciclismo?", a data do treino e o botão "Responder".
3. **Seus últimos 14 dias:** o cartão da quinzena (seção 4).
4. **Treinos recentes:** quatro cartões de treino (seção 3) e "Ver todos", que abre a aba Treinos.
5. **Abas** na base (celular) ou menu à esquerda (computador 1280: menu de 232 e duas colunas): Início, Treinos (selo com o número de
   pendentes), Evolução, Conta.

No computador, o último treino fica na coluna da esquerda e a quinzena e os recentes, na da direita.

### Número do treino (não inventamos métrica)
| treino | número grande | origem |
|---|---|---|
| corrida intervalada | melhor tiro de 1 km, `m:ss` e "/km" | `pace_melhor` ([[metricas/tiros-1km]]; ver [[design/telas/evolucao-tiros]]) |
| corrida leve, longa, moderada | pace médio, `m:ss` e "/km" | `pace_medio` |
| natação e ciclismo | duração, `h:mm:ss` | `duracao` |
O app **mostra o texto pronto da API**; não formata pace nem calcula. Natação não tem pace por 100 m nos esboços porque o contrato de hoje
não o entrega.

### Selo de normal (linha de base)
Vem de `linha_base` ([[metricas/linha-base]]), só da mesma modalidade e tipo. "Dentro do seu normal para natação" (confere, `marca-suave`);
"Fora do seu normal: <frase da API>" (triângulo, `alerta`); `aprendendo` mostra o `texto` da API (ampulheta); sem `linha_base`, não aparece.
Nunca "bom" ou "ruim".

### Estados do início
| estado | o que aparece | texto |
|---|---|---|
| carregando | esqueleto de quatro cartões | "Carregando" (só para leitor de tela) |
| sem treinos | linha de pulso e botão "Enviar arquivo FIT" | "Nenhum treino ainda. Envie o arquivo do seu relógio e a análise aparece aqui." |
| último treino sem feedback | cenário 1 | ver acima |
| feedback pendente, indisponível ou prazo vencido | linha de estado da [[design/telas/feedback]] no lugar das linhas do feedback | texto da API |
| erro de rede | cada cartão falha sozinho | "Não foi possível carregar. Tentar de novo" |
| acesso expirado | como em [[design/telas/entrar]] | |

### Dados
`GET /atletas/{id}/atividades` (lista, [[modulos/mobile]]) para o último treino e os recentes; `GET /atletas/{id}/carga` para a
quinzena; `GET /atletas/{id}/checkins/pendentes?dias=7` para as faixas. **Prazo do check-in:** o app só lê `checkin_aberto`; por isso os
esboços **não** mostram "faltam N dias". Se o Angelo quiser a contagem, a API precisa entregar o prazo (pergunta 5).

## 2. Treino v3 (ordem aprovada)
![[design/telas/inicio-atleta/treino-v3-celular-claro.svg]]
![[design/telas/inicio-atleta/treino-v3-celular-escuro.svg]]
![[design/telas/inicio-atleta/treino-v3-computador-claro.svg]]
![[design/telas/inicio-atleta/treino-v3-computador-escuro.svg]]

### Hierarquia
1. **Como foi:** o número do treino, a linha de apoio (distância, duração, FC média) e o feedback.
2. **Comparado ao seu normal:** selo, barra com a faixa normal e o ponto de hoje, FC média e a frase da faixa ("Normal: 4:08 a 4:24 /km
   (12 semanas, só intervalados)").
3. **O que você respondeu:** esforço, sensação, observação, com "Editar" e "Apagar check-in".
4. **Os tiros:** uma barra por tiro (mais alta = mais rápido), com o tempo escrito em cada uma.
5. **Contexto:** duração, distância, pace médio, FC média, carga do treino (estimativa) e clima, numa lista só.

Variações: **sem check-in**, o bloco 1 mostra o número e, no lugar do feedback, a faixa volt "Responda o check-in para receber o
feedback"; os blocos 2 e 3 trocam por "Sem check-in". **Sem pace** (natação, ciclismo): o número é a duração e o bloco 2 omite a barra.
**Linha de base aprendendo:** o bloco 2 mostra o texto de aprendendo. Os estados do feedback seguem a [[design/telas/feedback]].
Os detalhes de cada bloco (tiros, clima, apagar) seguem a [[design/telas/treino]], só reordenados.

### Acessibilidade
- Cada bloco é um título numerado para navegar por títulos ("1 Como foi", "2 Comparado ao seu normal"...).
- Número com rótulo completo: "Melhor tiro, 4 minutos e 11 segundos por quilômetro".
- Barra do normal com texto na mesma linha ("hoje 4:11, seu normal 4:08 a 4:24"); gráfico de tiros com a lista dos tempos.

## 3. Aba Treinos e o cartão de treino
![[design/telas/inicio-atleta/treinos-lista-celular-claro.svg]]
![[design/telas/inicio-atleta/treinos-lista-celular-escuro.svg]]
![[design/telas/inicio-atleta/treinos-lista-computador-claro.svg]]
![[design/telas/inicio-atleta/treinos-lista-computador-escuro.svg]]

A lista real já existe no app (PR #540, `GET /atletas/{id}/atividades`, rolagem pelo cursor `proximo`). Esta spec acrescenta o que a v3 pede:
**valor principal** em número grande e **um selo de estado**.

### Hierarquia
1. Título "Treinos" e o botão secundário "Enviar FIT" (sai daqui se o Angelo preferir só na Conta; pergunta 6).
2. **Filtros:** Todos, Corrida, Natação, Ciclismo e "Sem check-in · N". Alvo de toque de **44**; o esboço mostra o desenho de 36 e o
   alvo é maior que o desenho. No celular a fileira **rola na horizontal** e o último filtro aparece cortado para sinalizar que há mais.
   O rótulo "Todos" pode confundir com "sem filtro" quando "Sem check-in" está ligado (visto no PR #540); ver pergunta 7.
3. **Grupos por semana:** "ESTA SEMANA", "SEMANA PASSADA", depois "SEMANA DE 03/03" (data da segunda-feira).
4. **Cartões de treino**, do mais recente ao mais antigo.
5. "Carregar treinos mais antigos" no fim da lista (rolagem infinita; o botão aparece se o carregamento falhar).

### Anatomia do cartão de treino
![[design/telas/inicio-atleta/cartao-treino-anatomia-claro.svg]]
![[design/telas/inicio-atleta/cartao-treino-anatomia-escuro.svg]]

| parte | token | regra |
|---|---|---|
| 1 ícone da modalidade | quadrado 40, `raio.bloco`, `superficie-2`; cor da modalidade | sempre com o nome ao lado |
| 2 título | `fonte.titulo-cartao` | "modalidade · tipo"; o tipo só aparece se existir (natação e ciclismo não têm) |
| 3 data curta | `fonte.rotulo`, `texto-2` | "ter 18/03" (dia da semana e dia/mês) |
| 4 linha de meta | `fonte.rotulo`, `texto-2` | "hora · duração · distância"; omite o que não existe |
| 5 valor principal | `fonte.numero-destaque` (30) e unidade em `fonte.rotulo` | a mesma tabela "Número do treino" do início |
| 6 selo de estado | `raio.pilula`, altura 28, ícone e texto | **um só**, o primeiro que valer: sem check-in, fora do normal, no normal, aprendendo |
Cartão: altura mínima 96, `raio.cartao` (12), padding 16. O cartão **todo** é o alvo de toque e abre o treino; o rótulo falado junta
tudo: "Corrida, intervalado, terça 18 de março, 6 e 30, 52 minutos, 10 quilômetros, melhor tiro 4 minutos e 11 por quilômetro, dentro do seu normal".

**Por que um selo só:** o PR #540 mostra até quatro selos (check-in, feedback). Na lista o atleta precisa de **uma** pista de ação; o
detalhe fica no treino. Prioridade: "Sem check-in" é a ação, vem primeiro.
| selo | ícone | cor | texto |
|---|---|---|---|
| sem check-in | relógio | `alerta` | "Sem check-in" |
| check-in vencido | calendário riscado | `texto-2` | "Check-in vencido" |
| fora do normal | triângulo | `alerta` | "Fora do normal" |
| no normal | confere | `marca-suave` | "No normal" |
| aprendendo | ampulheta | `texto-2` | "Aprendendo" |

### Estados da lista
| estado | o que aparece | texto |
|---|---|---|
| carregando | cinco esqueletos de cartão | "Carregando" (leitor de tela) |
| vazio | linha de pulso | "Nenhum treino ainda. Envie o arquivo do seu relógio pela aba Conta e a análise aparece aqui." |
| vazio com filtro | texto e "Limpar filtros" | "Nenhum treino com esses filtros." |
| erro | ícone, mensagem, botão | "Não foi possível falar com o servidor" ou "Não foi possível carregar os treinos. Tente de novo mais tarde." e "Tentar de novo" |
| erro ao carregar mais | o botão no fim, a lista continua | "Não foi possível carregar mais treinos." e "Tentar de novo" |
| fim | texto discreto | "Esses são todos os seus treinos." |

## 4. Quinzena: gráfico de duas linhas e frase de análise
Cartão "Seus últimos 14 dias" do início (ver as duas telas acima) e o estado em aprendizado:
![[design/telas/inicio-atleta/quinzena-aprendendo-claro.svg]]
![[design/telas/inicio-atleta/quinzena-aprendendo-escuro.svg]]

- **Dados:** os últimos 14 itens de `dias` de `GET /atletas/{id}/carga` ([[metricas/serie-carga]]): `ctl` e `atl`. A série termina no
  **último dia com atividade** e o eixo mostra as datas reais (07/03 a 20/03 no exemplo, "até ontem, 20/03").
- **Nomes na tela:** "Condicionamento" (linha cheia, azul) e "Fadiga" (tracejada, magenta), com o valor final em `fonte.numero-grande`
  ao lado (44 e 58, sintéticos). **Nada de CTL, ATL ou TSB.** Selo "estimativa" sempre. Tocar no nome mostra a definição do glossário.
- **Frase de análise** (descreve, não recomenda; sem adjetivo de valor):
| situação | frase |
|---|---|
| fadiga > condicionamento | "Sua fadiga (58) está acima do condicionamento (44): a carga dos últimos dias passou da média das últimas 6 semanas." |
| fadiga < condicionamento | "Sua fadiga (N) está abaixo do condicionamento (N): a carga dos últimos dias ficou abaixo da média das últimas 6 semanas." |
| iguais | "Sua fadiga e o seu condicionamento estão iguais (N)." |
| aprendendo | o `texto_aprendendo` da API; o esboço mostra "Ainda estamos aprendendo o seu condicionamento: a estimativa melhora depois de 6 semanas de treinos." como exemplo, **sem números nos pontos** |
| sem carga calculada | o `texto` da API, sem gráfico |
  **Pendência para o Caio e a Duda:** a frase deve ser **texto fixo aprovado pelo Caio e entregue pela API** (como `ctl_texto` e
  `texto_aprendendo`), para o app não decidir o que dizer. Os valores 44 e 58 são sintéticos.
- **Sem cor como única pista:** traço cheio e tracejado, rótulo direto e valor.
- **Alternativa em texto do gráfico:** "Condicionamento 44 e fadiga 58 em 20 de março. A fadiga ficou acima do condicionamento nos últimos
  dias." (montada a partir da frase da API).
- "Ver evolução completa" abre a aba Evolução.

## Acessibilidade geral
- Contraste, alvos de 44 e foco: conforme [[design/identidade-visual-v3]].
- Ordem de leitura = ordem visual; cada cartão é um grupo com título.
- Nenhuma informação só por cor: todo selo tem ícone e texto.
- Textos até 2x de escala sem cortar; números limitam a 1,3x e a linha do número pode quebrar a unidade para baixo.
- Respeita "reduzir movimento".

## Perguntas ao Angelo
1. **Nome:** "Pulso" fica? Ainda não confirmado, e não foi pesquisado no INPI nem nas lojas. Se trocar, mudo só a palavra do logo.
2. **Logo e ícone:** a linha de pulso em quadrado volt (`docs/design/marca/`) serve, ou prefere outro símbolo?
3. **Início:** no cenário 1, o convite do check-in **dentro** do cartão do último treino (faixa volt) é o que você quer, ou prefere o
   convite como cartão separado logo abaixo, como no cenário 2?
4. **Lista:** **um** selo por treino (sem check-in, fora do normal, no normal, aprendendo), nessa prioridade, está bom?
5. **Prazo do check-in:** quer ver "faltam N dias" no convite? Isso pede um campo novo na API (decisão do Theo e da Duda); sem ele, o
   convite não mostra prazo.
6. **Enviar FIT:** fica na aba Treinos ou só na Conta?
7. **Filtro:** trocar "Todos" por "Todas as modalidades" para não confundir com "sem filtro"?
8. **Fonte nova:** pode entrar o pacote gratuito `@expo-google-fonts/barlow-condensed` (OFL, sem conta)? Se não, o plano B é Inter 800.
