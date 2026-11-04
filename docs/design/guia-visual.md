---
tipo: design
status: rascunho
dono: lia
atualizado: 2026-11-04
links: [[design/tokens]], [[design/telas/evolucao-tiros]], [[modulos/mobile]], [[decisoes/0004-contrato-tela-evolucao]], [[decisoes/0008-deteccao-de-esforcos]], [[metricas/tiros-1km]], [[glossario]]
---
# Design: guia visual do app

Identidade, regras de uso e componentes base do app (iOS, Android e web). Proposta do zero, sem referência
anterior (decisão do Angelo, 04/11; issue #192). Os valores estão em [[design/tokens]]; o exemplo aplicado está em
[[design/telas/evolucao-tiros]]. O tema no código é do Rafa, em outra issue ([[modulos/mobile]]).

## Ideia: a prancheta do treinador
O treinador anota o treino numa prancheta: papel claro, tinta escura, uma caneta de cor para marcar o que importa.
O app faz o mesmo. Fundo de papel, números em tinta, uma cor de destaque só para a ação e a seleção, e cor de dado
só dentro dos gráficos. O nome do produto é "contexto": o número nunca aparece sozinho, sempre com a data, a
unidade e o que ele significa.

## Princípios
1. **O número primeiro.** Depois do treino, o atleta quer um número: o melhor tiro de hoje. Ele vem grande, no
   alto, com a unidade ao lado. Explicação e detalhe vêm abaixo.
2. **Legível ao sol e com a mão suada.** Contraste AA em todo texto (a maioria passa de 6:1), nada abaixo de 12,
   alvo de toque de 44, sem informação em cor clara ou em sombra. Toque largo e perdoador.
3. **Cor nunca sozinha.** Toda cor vem com texto, ícone, forma ou posição. Quem não distingue cores lê tudo.
4. **Dois leitores.** O atleta multisporte olha no celular, rápido, um treino por vez. O professor olha no
   computador, com calma, vários treinos e atletas. A mesma tela serve aos dois: uma coluna estreita no celular e
   conteúdo de até 720 de largura na web, centralizado.
5. **A API manda o texto.** Pace em `m:ss` e rótulos de eixo vêm prontos da API ([[decisoes/0004-contrato-tela-evolucao]]).
   O design nunca pede ao app para formatar pace nem escolher escala.
6. **Calmo.** Sem gradiente, sem animação de enfeite, sem sombra em cartão. O que chama atenção é o dado.

## Cores
Tabela completa, nos dois temas, em [[design/tokens]] (seção "Cores"). Os contrastes estão calculados lá.

### Neutros: papel e tinta
- `cor.fundo` claro `#F6F5F1` é um branco quente de papel; os cartões são brancos puros (`cor.superficie`). A
  diferença leve separa cartão de fundo sem precisar de sombra, que some ao sol.
- `cor.texto` `#1A1D1F` é quase preto, não preto puro: menos vibração em tela OLED clara, contraste de 16,9:1 no cartão.
- `cor.texto-2` `#4C5257` para rótulos e eixos: mais claro que o texto, mas ainda 7,9:1. Não existe um terceiro
  cinza de texto: cinza claro some ao sol.
- Tema escuro: fundo `#121517` e cartão `#1C2023`, sem preto puro (evita o "borrão" de texto claro em OLED).
  O app segue o tema do sistema; sem chave própria por enquanto.

### Destaque: petróleo
`cor.destaque` `#0B6A6E` (claro) e `#5CC8C4` (escuro). É a caneta da prancheta: botão primário, link, item
selecionado e anel de foco. Por que petróleo:
- fica longe das cores que já têm sentido no app: o laranja da corrida, o âmbar do alerta, o vermelho do erro, o
  anil do pace e o magenta da FC;
- é calmo e lê bem nos dois temas (6,4:1 no cartão claro; 8,2:1 no escuro);
- não é verde de "sucesso" nem azul de "natação", então um botão não parece um estado nem uma modalidade.

### Estados
Sucesso `#1B6E3A`, alerta `#8A5300`, erro `#B3261E`, cada um com um fundo suave para o aviso. O alerta é um âmbar
escuro, quase marrom, porque o amarelo não passa 4,5 como texto em fundo claro. Todo aviso tem ícone e texto; a cor
só reforça.

### Modalidades
| modalidade | cor (claro / escuro) | ícone | por quê |
|---|---|---|---|
| corrida | `#B4470F` / `#FF9A5C` | `directions-run` | laranja-tijolo da pista de atletismo |
| ciclismo | `#6B3FB0` / `#BFA2F2` | `directions-bike` | violeta: longe das outras duas e dos estados |
| natação | `#1A5FA8` / `#7DB7F0` | `pool` | azul da água |

A cor da modalidade aparece só no chip, no ícone e na marca da atividade em listas mistas. Nunca pinta o gráfico:
dentro da tela da corrida, o gráfico é da corrida, e a cor do dado é a do dado (pace, FC). Assim as cores de
modalidade e de gráfico não se misturam numa mesma vista. A corrida fica perto do vermelho do erro na roda de cores;
por isso a modalidade vem sempre com ícone e nome, e o erro sempre com ícone de erro e frase.

### Gráficos
| série | token | forma |
|---|---|---|
| pace (valor principal: melhor tiro) | `cor.grafico.pace` anil | linha cheia de 2, ponto cheio |
| FC (valor principal: FC do melhor tiro) | `cor.grafico.fc` magenta | linha cheia de 2, ponto cheio |
| média dos tiros (secundária) | `cor.grafico.media` cinza | linha tracejada de 1,5, ponto vazado |
| grade | `cor.grafico.grade` | linha fina, decorativa |

- Pace e FC ficam em painéis separados, cada um com título e unidade. A cor ajuda, mas o título diz o que é.
- Anil e magenta têm claridade parecida e podem se confundir para quem tem daltonismo. Por isso pace e FC nunca
  dividem o mesmo painel: quem diz qual é qual é o título, não a cor.
- Melhor tiro e média se distinguem pela forma (cheia contra tracejada, ponto cheio contra vazado) e pela cor
  (série contra cinza). A legenda mostra a forma, não só a cor.
- Pace com eixo invertido (mais rápido no alto, ADR 0004): o painel diz "mais rápido ↑" ao lado do título.

### Blocos do treino (previsto para a Meta 5)
A detecção de esforços ([[decisoes/0008-deteccao-de-esforcos]]) divide a atividade em blocos: `aquecimento`,
`esforco`, `recuperacao`, `desaquecimento` e `leve`. Eles vão virar a **faixa do treino** (componente abaixo).
`cor.bloco.esforco` é a tinta (`cor.texto`): o esforço é o que importa e precisa do maior contraste. Os outros
blocos são cinza médio (3,5:1 no claro, 4,2:1 no escuro) e se distinguem pela altura, pela hachura e pelo rótulo.

## Tipografia
**Inter** (SIL Open Font License 1.1), pelo pacote `@expo-google-fonts/inter` (MIT). Por quê:
- algarismos tabulares (`tnum`): `4:08` e `4:11` ocupam a mesma largura, e os números da lista ficam alinhados;
- desenhada para tela, com letras abertas e boa leitura em tamanho pequeno (eixos de 12);
- tem os pesos 400, 500, 600 e 700 com acentos do português;
- é livre e roda igual em iOS, Android e web. Se a fonte não carregar, cai na fonte do sistema, que também tem
  algarismos tabulares.

Escala em [[design/tokens]] (seção "Tipografia"). Regras:
- **Número grande, unidade pequena.** `4:08` em `fonte.numero-destaque` (40) e `min/km` em `fonte.rotulo` ao lado.
- Todo número com `fontVariant: ["tabular-nums"]`.
- Nada abaixo de 12, e 12 só nos eixos. O texto respeita o tamanho de fonte do sistema.
- Pesos só 400, 500, 600 e 700. Sem itálico (lê mal em tela pequena e ao sol).

## Espaçamento, raios e sombras
- Base 4 (`espaco.1` a `espaco.7`). Margem da tela de 16 no celular: num aparelho de 320 de largura sobram 288
  para o gráfico, contra 272 com a margem de 24 de hoje. A partir de 600 de largura, 24.
- Raios: 8 no que se toca (botão, campo, aviso), 12 no cartão, pílula no chip. Raio pequeno e constante: sério,
  sem parecer brinquedo.
- **Sem sombra em cartão.** O cartão se separa do fundo pela cor e por uma borda de 1. Sombra só no que flutua
  (`sombra.flutuante`). Motivo: sombra some ao sol, pesa no Android e não existe no tema escuro.

## Ícones
**Material Icons** (Apache License 2.0), pelo `@expo/vector-icons` (MIT). Por quê: tem as três modalidades
(`directions-run`, `directions-bike`, `pool`), funciona em iOS, Android e web sem desenhar nada, e é um conjunto só,
com traço coerente. Lista de nomes em [[design/tokens]] (seção "Ícones").
Regras: ícone sempre com texto ao lado ou com `accessibilityLabel`; tamanho 16, 20 ou 24; cor do texto vizinho.

## Acessibilidade
- Contraste AA em todos os pares, calculado por script ([[design/tokens]], seção "Contraste").
- Alvo de toque mínimo de 44 por 44, inclusive o ponto do gráfico (hoje é 32: ajuste para o Rafa).
- Todo ponto do gráfico tem `accessibilityLabel` com a data e o valor ("Sessão de 04/03/25, melhor tiro 4:08 min/km").
  A lista de sessões abaixo do gráfico é a alternativa em texto ao gráfico.
- Anel de foco de 2 em `cor.foco` em tudo que se toca, para teclado na web.
- "Reduzir movimento" do sistema desliga as animações.

## Estados
Toda tela que busca dado tem os três estados abaixo, no mesmo lugar onde o conteúdo vai aparecer.

| estado | o que aparece | regra |
|---|---|---|
| carregando | esqueleto dos cartões (`cor.superficie-2`, `raio.pequeno`) e o texto "Carregando seus tiros..." | o texto fica, para leitor de tela; com "reduzir movimento", esqueleto parado |
| vazio | ícone `icone.estado` em `cor.texto-2`, título, uma frase do que fazer e o botão da ação | diz o próximo passo, não só "não há dados" |
| erro | ícone do erro, frase curta do que houve e, se fizer sentido, o botão "Tentar de novo" | frase sem código de erro; sem culpar o usuário |

O conteúdo que já está na tela não some quando uma nova busca começa (como já faz a tela de evolução depois do envio).

## Componentes base

### Botão
| variante | fundo | texto | borda | uso |
|---|---|---|---|---|
| primário | `cor.destaque` | `cor.sobre-destaque` | nenhuma | a ação principal da tela (no máximo um por vista) |
| secundário | `cor.superficie` | `cor.destaque` | 1 em `cor.borda-forte` | ação de apoio ("Enviar arquivo FIT" com dados na tela) |
| texto | transparente | `cor.destaque` | nenhuma | ação pequena ("Tentar de novo" dentro de um aviso) |

Altura 48 (`botao.altura`), padding lateral 16, `raio.medio`, `fonte.botao`, ícone opcional de 20 à esquerda.
Estados: pressionado (`cor.destaque-pressionado`; secundário com fundo `cor.destaque-suave`); desligado (fundo
`cor.superficie-2`, texto `cor.texto-desligado`, sem opacidade sobre a cor original); carregando (indicador no
lugar do ícone, texto muda para o gerúndio: "Enviando...", botão desligado). No celular estreito, o primário ocupa a
largura toda.

### Cartão
`cor.superficie`, borda 1 em `cor.borda`, `raio.grande`, padding `espaco.4`, `sombra.nenhuma`, espaço de `espaco.5`
entre cartões. Título em `fonte.titulo-secao`. Um cartão = um assunto.

### Cabeçalho de tela
Título em `fonte.titulo-tela`, chip da modalidade ao lado ou abaixo, e uma linha de subtítulo em `fonte.corpo`,
`cor.texto-2`. Ações à direita só se forem ícone com rótulo de acessibilidade. Voltar (`arrow-back`) quando houver
tela anterior. Sem barra colorida: o cabeçalho é papel, como o resto.

### Chip de modalidade
Pílula com ícone de 16 na cor da modalidade e o nome em `fonte.rotulo` e `cor.texto`, fundo `cor.superficie-2`.
Altura 28 (não é tocável; se virar filtro, sobe para 44).

### Número em destaque
Valor em `fonte.numero-destaque` e `cor.texto`, unidade em `fonte.rotulo` e `cor.texto-2` na mesma linha base,
rótulo acima em `fonte.rotulo` ("Melhor tiro"). Um por cartão. Logo abaixo, os valores secundários em `fonte.corpo`
e `cor.texto-2` (média, FC, número de tiros).

### Aviso
Faixa com fundo suave do estado (`cor.sucesso-suave`, `cor.alerta-suave`, `cor.erro-suave`), ícone de 20 e texto em
`fonte.corpo` na cor do estado, `raio.medio`, padding `espaco.3`. Usa `accessibilityLiveRegion="polite"` (Android) e
anúncio de acessibilidade, para o leitor de tela falar o resultado do envio.

### Legenda de gráfico
Linha acima do painel, em `fonte.rotulo` e `cor.texto-2`. Cada item mostra a **forma** da série (traço de 16 cheio ou
tracejado, com o ponto cheio ou vazado) na cor da série, e o nome: "Melhor tiro", "Média dos tiros". A legenda só
aparece quando o painel tem mais de uma série; com uma só, o título do painel basta.

### Faixa do treino (previsto, Meta 5)
Barra horizontal com os blocos da atividade, na ordem, largura proporcional à duração. A altura diz a intensidade:
`esforco` 32, `leve` 24, `recuperacao`, `aquecimento` e `desaquecimento` 16. Aquecimento e desaquecimento com
hachura diagonal. Pausa = um vão de 2. Rótulo curto embaixo dos esforços ("1", "2"...). Tocar um bloco abre o detalhe
dele. Alternativa em texto: a lista dos blocos abaixo da faixa, com categoria, distância, duração e pace.
A tela dos blocos ganha especificação própria em `docs/design/telas/` quando a issue for aberta.

## O que fica fora deste guia
- Logo e ícone do app: fora do escopo da #192.
- Tema escolhido pelo usuário: o app segue o sistema.
- Tela dos blocos (Meta 5): só o componente está previsto aqui.

## Pendências
- O Rafa transforma [[design/tokens]] em tema no código (issue seguinte) e adiciona `@expo-google-fonts/inter` e
  `@expo/vector-icons` (pacotes livres; nenhum serviço nem conta).
- Conferir o tema numa tela real ao sol, em celular pequeno, depois da implementação.
