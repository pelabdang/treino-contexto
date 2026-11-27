---
tipo: design
status: rascunho
dono: lia
atualizado: 2026-11-27
links: [[design/identidade-visual-v3]], [[design/telas/inicio-atleta-v3]], [[design/telas/evolucao-v1]], [[design/referencias-evolucao-inicio]], [[metricas/evolucao-series]], [[metricas/frase-forma]], [[metricas/recuperacao]], [[design/telas/semana-padrao]], [[modulos/mobile]]
---
# Tela: Início v4 (mais cartões, com regra de aparecer e sumir)

Pedido do Angelo (27/11): o início com mais "gadgets" (cartões). Parte do [[design/telas/inicio-atleta-v3]] (aprovado) e acrescenta uma seção,
**"Seus números"**, entre a quinzena e os treinos recentes. Candidatos e custos: inventário do Caio ([[metricas/evolucao-series]], "Cartões candidatos do início").
**Nada aqui muda o app** até o Rafa implementar. Identidade v3. Atleta (Ana) e números **sintéticos**.

## Objetivo
O atleta abre o app e, além do último treino e da quinzena, vê em segundos **o que mudou e o que vem hoje**, sem rolar muito e sem cartão vazio.

## Princípios dos cartões
1. **Sem dado, não aparece.** Nada de "sem dados", cartão cinza ou zero. A seção some inteira se nenhum cartão tiver dado.
2. **Cada cartão responde uma pergunta** e leva a um detalhe (a Evolução com a série já escolhida, ou a semana-padrão).
3. **Texto pronto da API.** O app não calcula soma, mediana nem frase. Os cartões 1 e 3 pedem rota de volume (Duda); sem ela, não entram.
4. **Descreve, não julga.** Nada de "bom", "ruim", "meta", "sequência" nem conselho.
5. **Um cartão é lido em 3 segundos:** rótulo, número, uma ou duas linhas de apoio.

## Esboços
Celular (cenário: último treino é natação em piscina) e computador, claro e escuro:
![[design/telas/inicio-v4/inicio-v4-celular-claro.svg]]
![[design/telas/inicio-v4/inicio-v4-celular-escuro.svg]]
![[design/telas/inicio-v4/inicio-v4-computador-claro.svg]]
![[design/telas/inicio-v4/inicio-v4-computador-escuro.svg]]

Anatomia do cartão pequeno, pouco dado e quando somem:
![[design/telas/inicio-v4/inicio-v4-cartoes-claro.svg]]
![[design/telas/inicio-v4/inicio-v4-cartoes-escuro.svg]]

## Ordem do início
1. Saudação, **último treino** (com a faixa do check-in, como na v3).
2. **Seus últimos 14 dias** (quinzena, como na v3).
3. **Seus números** (novo): os cartões da tabela abaixo, na ordem dela.
4. **Treinos recentes** e "Ver todos".
No computador: coluna da esquerda = último treino e "Seus números"; direita = quinzena e recentes.
**Por que "Seus números" depois da quinzena:** o último treino e a forma são o que o atleta veio ver; os números são o contexto de semanas e de rotina.

## Os cartões, a ordem e a regra de aparecer
Ordem fixa. A coluna "dado" diz o que a API precisa devolver; a coluna "aparece quando" é a regra. Origem e custo: [[metricas/evolucao-series]].
| # | cartão | formato | pergunta que responde | aparece quando | toque leva a | texto de exemplo |
|---|---|---|---|---|---|---|
| 1 | **Esta semana** | pequeno | "quanto treinei esta semana?" | há ao menos 1 treino desde a segunda (fuso do atleta) | Evolução, série "Volume por semana" | "3 treinos" e "2 h 37 min · semana passada: 4" |
| 2 | **Hoje, sexta** | pequeno | "o que a minha rotina prevê hoje?" | o atleta tem semana-padrão cadastrada ([[design/telas/semana-padrao]]) e hoje tem treino previsto | tela da semana-padrão | "Corrida leve" e "da sua rotina" |
| 3 | **Volume das 4 semanas** | largo, 4 barras | "estou treinando mais ou menos?" | 4 semanas completas com ao menos 3 de volume > 0 | Evolução, série "Volume por semana" | "30 km por semana, 10 km a menos que nas 4 anteriores" |
| 4 | **Em movimento** | largo, só texto | "o que mudou mais nas últimas 4 semanas?" | a API escolhe a série de maior mudança (mínimo 1,0 do limiar) e traz o título e a frase | Evolução, essa série | "Pace dos seus treinos leves nas últimas 4 semanas: 5:42/km (mediana de 3 treinos), 12 s/km mais rápido que nas 4 anteriores (5:54/km)." |
| 5 | **Melhor marca** | pequeno | "bati um recorde?" | há recorde do relógio nos **últimos 30 dias** (proposta minha; o Caio confirma) | Evolução, série "Marcas" | "21:10 · 5 km" e "novo recorde · 12/03" |
| (6) | Noite | pequeno | "como dormi?" | **depois**: precisa da rota "última noite" e de importação de saúde | | "6 h 40" e "sono dentro do seu normal" |
Ficam **fora do v4**: Mistura de tipos, CTL em 6 meses, Limiar (valor baixo), **Regularidade** (pergunta ao Angelo), Clima (pertence ao treino, não ao dia).

### Layout
- **Pequenos ficam em pares** (2 colunas, 12 de espaço, altura 112). Um pequeno sozinho ocupa a **largura inteira**.
- **Largos** ocupam a linha toda. Mantém a ordem da tabela; um largo entre dois pequenos quebra o par (veja o esboço: 1 e 2 em par; 3 e 4 largos; 5 sozinho).
- Máximo de **5 cartões** no início, na prioridade da tabela. Quando a "Noite" entrar (v4.1), ela concorre pelas mesmas 5 vagas.
- Título da seção "Seus números" em `fonte.titulo-secao`; some junto com os cartões.
- Cartão pequeno: `raio.cartao` 12, padding 14, rótulo em maiúsculas (`fonte.sobretitulo`), número em Barlow Condensed 800 (32; 27 quando o texto passa de 8 caracteres), apoio `fonte.rotulo` até 2 linhas, "›" no canto.
- **Alvo de toque:** o cartão todo (mínimo 112 por 175).
- Barras do volume: 4 barras, cada uma com o valor escrito em cima e a data da segunda-feira embaixo; a **semana mais recente** em azul, as demais em `superficie-2`. Sem a cor: o valor está escrito.

## Estados
| situação | o que aparece | texto |
|---|---|---|
| carregando | esqueletos dos cartões (mesmo tamanho) para o leitor de tela ouvir "Carregando" | |
| cartão sem dado | **nada** | |
| pouco dado | o número fica e o apoio explica | "1 treino" e "45 min · sem semana anterior"; "21:10 · 5 km" e "1 marca no período" |
| erro num cartão | o cartão **some em silêncio** (são extras; o erro do último treino e da quinzena continuam visíveis) | |
| nenhum cartão | a seção e o título somem | |
| sem treinos no app | o início vazio da v3; nenhum cartão | |
| atualização | o cartão "Em movimento" só muda quando o dia muda (a API calcula por dia), para não trocar a cada abertura | |

## Personalização (pergunta ao Angelo, não decisão)
O atleta poderia **esconder** ou **reordenar** os cartões. Recomendo **não no v4**: ordem fixa e regra "sem dado, não aparece". Esconder entra depois
do piloto, se o atleta pedir. Reordenar fica para o fim (o Garmin Connect deixa reordenar, mas muita gente não usa e a tela vira configuração; ver [[design/referencias-evolucao-inicio]]).
Se o Angelo quiser personalizar: começar por **esconder** (um menu "Ocultar" em cada cartão, desfeito em Conta > "Cartões do início").

## Acessibilidade
- Cada cartão é um grupo com título; rótulo falado junta tudo: "Esta semana, 3 treinos, 2 horas e 37 minutos, semana passada 4 treinos. Abre a evolução do volume."
- Barras do volume: lista de 4 itens ("Semana de 3 de fevereiro, 40 quilômetros").
- Alvo de 44 em tudo; texto até 2x (o número limita a 1,3x e o apoio quebra linha, o cartão cresce).
- Nenhuma informação só por cor.

## O que muda em relação à v3
| v3 | v4 |
|---|---|
| último treino, quinzena, recentes | + seção "Seus números" com até 5 cartões |
| toque no cartão da quinzena abre a Evolução | cada cartão leva à Evolução com a série escolhida ([[design/telas/evolucao-v1]]) |
