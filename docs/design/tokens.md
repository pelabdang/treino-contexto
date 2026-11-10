---
tipo: design
status: rascunho
dono: lia
atualizado: 2026-11-09
links: [[design/guia-visual]], [[design/telas/evolucao-tiros]], [[modulos/mobile]]
---
# Design: tokens do tema

Tabela de nomes e valores para o Rafa transformar em tema no código ([[modulos/mobile]]). O porquê de cada
escolha está em [[design/guia-visual]]. Valores em dp (no app) e px (na web), que no Expo são a mesma unidade.

Esta nota é a **fonte única** das cores: o script `docs/design/contraste.py` lê a tabela "Cores" e escreve a
tabela "Contraste" abaixo. Mudou uma cor? Rode `python docs/design/contraste.py --escrever`. O teste
`tests/test_design_contraste.py` falha se algum par ficar abaixo do mínimo AA ou se a tabela estiver velha.

## Cores
Tema claro e escuro. O app segue o tema do sistema.

| token | claro | escuro | uso |
|---|---|---|---|
| `cor.fundo` | `#F6F5F1` | `#121517` | fundo da tela ("papel") |
| `cor.superficie` | `#FFFFFF` | `#1C2023` | cartão, cabeçalho, área do gráfico |
| `cor.superficie-2` | `#ECEAE4` | `#262B2F` | realce dentro do cartão: detalhe da sessão, esqueleto do carregando |
| `cor.borda` | `#DEDBD3` | `#33393E` | divisória e contorno do cartão (decorativa, sem mínimo) |
| `cor.borda-forte` | `#7D7A72` | `#80878D` | contorno do botão secundário e de campo (mínimo 3:1) |
| `cor.texto` | `#1A1D1F` | `#ECEEEF` | texto principal e números |
| `cor.texto-2` | `#4C5257` | `#B4BBC0` | texto secundário, rótulo, eixo, rodapé |
| `cor.texto-desligado` | `#9A9890` | `#5E656A` | texto de botão desligado (a WCAG não exige contraste de item desligado) |
| `cor.destaque` | `#0B6A6E` | `#5CC8C4` | botão primário, link, item selecionado |
| `cor.destaque-pressionado` | `#08514F` | `#86DAD6` | botão primário pressionado |
| `cor.sobre-destaque` | `#FFFFFF` | `#0B1A1B` | texto e ícone sobre o destaque |
| `cor.destaque-suave` | `#DCEFEE` | `#163536` | fundo de item selecionado |
| `cor.foco` | `#0B6A6E` | `#5CC8C4` | anel de foco (teclado na web) |
| `cor.sucesso` | `#1B6E3A` | `#6FD08E` | texto e ícone de sucesso |
| `cor.sucesso-suave` | `#E3F2E8` | `#17301F` | fundo do aviso de sucesso |
| `cor.alerta` | `#8A5300` | `#F2B851` | texto e ícone de alerta |
| `cor.alerta-suave` | `#FCEFD6` | `#3A2C12` | fundo do aviso de alerta |
| `cor.erro` | `#B3261E` | `#FF8A80` | texto e ícone de erro |
| `cor.erro-suave` | `#FBE6E4` | `#3D1C1A` | fundo do aviso de erro |
| `cor.corrida` | `#B4470F` | `#FF9A5C` | modalidade corrida: ícone, chip, marca |
| `cor.ciclismo` | `#6B3FB0` | `#BFA2F2` | modalidade ciclismo |
| `cor.natacao` | `#1A5FA8` | `#7DB7F0` | modalidade natação |
| `cor.grafico.pace` | `#3340B0` | `#9AA4F5` | série de pace (melhor tiro): linha e ponto |
| `cor.grafico.fc` | `#A3205F` | `#F48FBF` | série de FC (FC do melhor tiro): linha e ponto |
| `cor.grafico.media` | `#6B7176` | `#8E969C` | série secundária (média dos tiros), tracejada |
| `cor.grafico.grade` | `#E3E1DA` | `#2C3236` | linhas de grade (decorativas, sem mínimo) |
| `cor.bloco.esforco` | `#1A1D1F` | `#ECEEEF` | bloco `esforco` na faixa do treino (ADR 0008) |
| `cor.bloco.recuperacao` | `#8C8981` | `#7A8186` | bloco `recuperacao` |
| `cor.bloco.aquecimento` | `#8C8981` | `#7A8186` | blocos `aquecimento` e `desaquecimento` (com hachura) |
| `cor.bloco.leve` | `#8C8981` | `#7A8186` | bloco `leve` |

Os três tokens de bloco que não são esforço têm o mesmo valor de propósito: a categoria se lê pela altura, pela
posição, pela hachura e pelo rótulo, não pela cor (ver "Faixa do treino" em [[design/guia-visual]]). Ficam
separados para poderem mudar sem renomear.

## Contraste
Razão WCAG 2.2 calculada pelo script. Mínimo AA: **texto** 4,5; **texto grande** 3,0; **gráfico** (linha, ponto,
contorno, ícone sem texto) 3,0. Todo par de texto do guia usa o mínimo de texto normal, mesmo quando o texto é grande.

<!-- contraste:inicio -->
| primeiro plano | fundo | tipo | mínimo AA | claro | escuro | passa |
|---|---|---|---|---|---|---|
| `cor.texto` | `cor.fundo` | texto | 4,50 | 15,53 | 15,75 | sim |
| `cor.texto` | `cor.superficie` | texto | 4,50 | 16,94 | 14,09 | sim |
| `cor.texto` | `cor.superficie-2` | texto | 4,50 | 14,08 | 12,28 | sim |
| `cor.texto-2` | `cor.fundo` | texto | 4,50 | 7,26 | 9,44 | sim |
| `cor.texto-2` | `cor.superficie` | texto | 4,50 | 7,92 | 8,44 | sim |
| `cor.texto-2` | `cor.superficie-2` | texto | 4,50 | 6,58 | 7,36 | sim |
| `cor.destaque` | `cor.fundo` | texto | 4,50 | 5,83 | 9,18 | sim |
| `cor.destaque` | `cor.superficie` | texto | 4,50 | 6,36 | 8,21 | sim |
| `cor.destaque` | `cor.destaque-suave` | texto | 4,50 | 5,34 | 6,59 | sim |
| `cor.texto` | `cor.destaque-suave` | texto | 4,50 | 14,22 | 11,30 | sim |
| `cor.sobre-destaque` | `cor.destaque` | texto | 4,50 | 6,36 | 8,93 | sim |
| `cor.sobre-destaque` | `cor.destaque-pressionado` | texto | 4,50 | 9,13 | 11,05 | sim |
| `cor.sucesso` | `cor.superficie` | texto | 4,50 | 6,29 | 8,66 | sim |
| `cor.sucesso` | `cor.sucesso-suave` | texto | 4,50 | 5,43 | 7,50 | sim |
| `cor.texto` | `cor.sucesso-suave` | texto | 4,50 | 14,63 | 12,20 | sim |
| `cor.alerta` | `cor.superficie` | texto | 4,50 | 6,33 | 9,18 | sim |
| `cor.alerta` | `cor.alerta-suave` | texto | 4,50 | 5,56 | 7,59 | sim |
| `cor.texto` | `cor.alerta-suave` | texto | 4,50 | 14,89 | 11,65 | sim |
| `cor.erro` | `cor.superficie` | texto | 4,50 | 6,54 | 7,19 | sim |
| `cor.erro` | `cor.erro-suave` | texto | 4,50 | 5,46 | 6,67 | sim |
| `cor.texto` | `cor.erro-suave` | texto | 4,50 | 14,15 | 13,08 | sim |
| `cor.corrida` | `cor.superficie` | texto | 4,50 | 5,46 | 7,83 | sim |
| `cor.corrida` | `cor.fundo` | texto | 4,50 | 5,00 | 8,76 | sim |
| `cor.ciclismo` | `cor.superficie` | texto | 4,50 | 7,09 | 7,55 | sim |
| `cor.ciclismo` | `cor.fundo` | texto | 4,50 | 6,50 | 8,44 | sim |
| `cor.natacao` | `cor.superficie` | texto | 4,50 | 6,47 | 7,74 | sim |
| `cor.natacao` | `cor.fundo` | texto | 4,50 | 5,93 | 8,65 | sim |
| `cor.grafico.pace` | `cor.superficie` | texto | 4,50 | 8,40 | 7,03 | sim |
| `cor.grafico.fc` | `cor.superficie` | texto | 4,50 | 7,17 | 7,44 | sim |
| `cor.grafico.media` | `cor.superficie` | grafico | 3,00 | 4,94 | 5,46 | sim |
| `cor.grafico.pace` | `cor.superficie-2` | grafico | 3,00 | 6,98 | 6,13 | sim |
| `cor.grafico.fc` | `cor.superficie-2` | grafico | 3,00 | 5,96 | 6,49 | sim |
| `cor.bloco.esforco` | `cor.superficie` | grafico | 3,00 | 16,94 | 14,09 | sim |
| `cor.bloco.recuperacao` | `cor.superficie` | grafico | 3,00 | 3,49 | 4,15 | sim |
| `cor.bloco.aquecimento` | `cor.superficie` | grafico | 3,00 | 3,49 | 4,15 | sim |
| `cor.bloco.leve` | `cor.superficie` | grafico | 3,00 | 3,49 | 4,15 | sim |
| `cor.borda-forte` | `cor.superficie` | grafico | 3,00 | 4,29 | 4,51 | sim |
| `cor.borda-forte` | `cor.fundo` | grafico | 3,00 | 3,93 | 5,04 | sim |
| `cor.foco` | `cor.fundo` | grafico | 3,00 | 5,83 | 9,18 | sim |
| `cor.foco` | `cor.superficie` | grafico | 3,00 | 6,36 | 8,21 | sim |
<!-- contraste:fim -->

## Tipografia
Fonte: **Inter** (SIL Open Font License 1.1), pelo pacote `@expo-google-fonts/inter` (MIT). Reserva: fonte do
sistema. Todo número (pace, FC, distância, data, eixo) usa algarismos tabulares: `fontVariant: ["tabular-nums"]`.

| token | peso | tamanho / altura da linha | uso |
|---|---|---|---|
| `fonte.numero-destaque` | 700 (Inter_700Bold) | 40 / 44, tabular | valor principal: melhor pace da sessão |
| `fonte.titulo-tela` | 700 | 24 / 30 | título da tela |
| `fonte.titulo-secao` | 600 (Inter_600SemiBold) | 18 / 24 | título de cartão e de painel |
| `fonte.corpo` | 400 (Inter_400Regular) | 16 / 24 | texto corrido, mensagens |
| `fonte.corpo-forte` | 600 | 16 / 24 | valor na lista, ênfase |
| `fonte.botao` | 600 | 16 / 20 | texto de botão |
| `fonte.rotulo` | 500 (Inter_500Medium) | 14 / 20 | rótulo de valor, chip, legenda do gráfico |
| `fonte.legenda` | 400 | 13 / 18 | rodapé, nota pequena |
| `fonte.eixo` | 500 | 12 / 16, tabular | só rótulos de eixo e datas do gráfico |

Nada abaixo de 12. O texto acompanha o tamanho de fonte do sistema (`allowFontScaling` ligado);
`fonte.numero-destaque` e `fonte.titulo-tela` limitam a escala com `maxFontSizeMultiplier: 1.5` para não quebrar a linha.

## Espaçamento
Base 4.

| token | valor | uso típico |
|---|---|---|
| `espaco.1` | 4 | entre ícone e texto pequeno |
| `espaco.2` | 8 | entre ícone e texto; entre linhas de um grupo |
| `espaco.3` | 12 | entre rótulo e valor; padding de chip |
| `espaco.4` | 16 | padding de cartão; margem da tela no celular |
| `espaco.5` | 24 | entre cartões; margem da tela a partir de 600 de largura |
| `espaco.6` | 32 | entre seções |
| `espaco.7` | 48 | respiro dos estados vazio e erro |
| `largura.conteudo-max` | 720 | largura máxima do conteúdo na web (professor no computador) |

## Raios, bordas e sombras
| token | valor | uso |
|---|---|---|
| `raio.pequeno` | 4 | barra da faixa do treino, esqueleto de texto |
| `raio.medio` | 8 | botão, campo, aviso, detalhe da sessão |
| `raio.grande` | 12 | cartão |
| `raio.pilula` | 999 | chip de modalidade |
| `borda.fina` | 1 | contorno de cartão, divisória |
| `borda.foco` | 2, afastada 2 | anel de foco |
| `sombra.nenhuma` | sem sombra | padrão de cartão: separa por `cor.borda` e `cor.superficie` |
| `sombra.flutuante` | iOS: cor `#000000`, opacidade 0,12, raio 8, deslocamento (0, 2); Android: `elevation` 3; web: `0 2px 8px rgba(0,0,0,0.12)` | só o que flutua sobre o conteúdo (detalhe aberto sobre o gráfico, aviso temporário). No tema escuro: sem sombra, com `cor.borda` |

## Tamanhos
| token | valor | uso |
|---|---|---|
| `alvo.minimo` | 44 | altura e largura mínimas de tudo que se toca (inclui ponto do gráfico) |
| `botao.altura` | 48 | botão primário e secundário |
| `lista.linha-altura` | 56 | altura mínima da linha tocável de lista (acima do `alvo.minimo` de 44, para caber duas linhas de texto) |
| `icone.pequeno` | 16 | ícone dentro de chip e legenda |
| `icone.medio` | 20 | ícone de botão e de aviso |
| `icone.grande` | 24 | ícone de cabeçalho |
| `icone.estado` | 40 | ícone dos estados vazio e erro |
| `grafico.linha-principal` | 2 | linha da série principal |
| `grafico.linha-media` | 1,5, tracejado 4 e 4 | linha da média, quando houver |
| `grafico.ponto` | raio 5; selecionado raio 7 com anel de 2 em `cor.texto` | ponto da sessão |
| `grafico.painel-altura` | 160 | altura de cada painel (pace e FC) |

## Movimento
| token | valor | uso |
|---|---|---|
| `movimento.rapido` | 150 ms | pressionar botão, abrir detalhe |
| `movimento.esqueleto` | 1200 ms, pulso de opacidade 1 → 0,6 | esqueleto do carregando |

Com "reduzir movimento" ligado no sistema, o esqueleto fica parado e nada anima.

## Ícones
**Material Icons** (Apache License 2.0, Google) pelo pacote `@expo/vector-icons` (MIT), componente `MaterialIcons`.
Os nomes abaixo foram conferidos no mapa de glifos do pacote (versão 15.1.1).

| uso | nome |
|---|---|
| corrida | `directions-run` |
| ciclismo | `directions-bike` |
| natação | `pool` |
| pace | `timer` |
| FC | `favorite` |
| melhor tiro (marca na lista) | `star` |
| enviar arquivo FIT | `upload-file` |
| sucesso | `check-circle-outline` |
| alerta | `warning-amber` |
| erro | `error-outline` |
| sem conexão | `wifi-off` |
| tentar de novo | `refresh` |
| informação (cálculo em atualização) | `info-outline` |
| vazio (sem treinos) | `insert-chart-outlined` |
| clima (Meta 4) | `thermostat`, `wb-sunny` |
| voltar | `arrow-back` |
| abrir item | `chevron-right` |
| fechar | `close` |
| semana-padrão: entrada e data (Meta 7, [[design/telas/semana-padrao]]) | `event` |
| semana-padrão: estado vazio | `event-note` |
| adicionar treino | `add` |
| remover treino | `delete-outline` |
| abrir seletor de tipo | `expand-more` |
| opção de rádio marcada, desmarcada | `radio-button-checked`, `radio-button-unchecked` |
| check-in: entrada, pendentes (Meta 8, [[design/telas/checkin]]) | `assignment` |
| check-in: editar | `edit` |
| check-in: escolhido | `check` |
| sensação 1 a 5 | `sentiment-very-dissatisfied`, `sentiment-dissatisfied`, `sentiment-neutral`, `sentiment-satisfied`, `sentiment-very-satisfied` |

Os nomes da semana-padrão foram conferidos no mapa de glifos do `@expo/vector-icons` pelo Rafa (#268, ver [[modulos/mobile]]). Os do
check-in são do conjunto padrão do Material Icons e ainda precisam ser conferidos pelo Rafa na #299.
