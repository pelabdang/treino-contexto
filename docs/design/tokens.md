---
tipo: design
status: aprovado
dono: lia
atualizado: 2026-11-27
links: [[design/identidade-visual-v3]], [[design/guia-visual]], [[design/telas/evolucao-tiros]], [[modulos/mobile]]
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
| `cor.fundo` | `#F6F5F1` | `#0F1214` | fundo da tela ("papel") |
| `cor.superficie` | `#FFFFFF` | `#181C1F` | cartão, cabeçalho, área do gráfico |
| `cor.superficie-2` | `#ECEAE4` | `#232A2E` | realce dentro do cartão: detalhe da sessão, esqueleto do carregando |
| `cor.borda` | `#DEDBD3` | `#2C3236` | divisória e contorno do cartão (decorativa, sem mínimo) |
| `cor.borda-forte` | `#7D7A72` | `#80878D` | contorno do botão secundário e de campo (mínimo 3:1) |
| `cor.texto` | `#1A1D1F` | `#ECEEEF` | texto principal e números |
| `cor.texto-2` | `#4C5257` | `#B4BBC0` | texto secundário, rótulo, eixo, rodapé |
| `cor.texto-desligado` | `#9A9890` | `#5E656A` | texto de botão desligado (a WCAG não exige contraste de item desligado) |
| `cor.marca` | `#C6F432` | `#D2FF3C` | volt: ícone do app, aba ativa, faixa de check-in, símbolo do logo. Nunca texto sobre fundo claro |
| `cor.sobre-marca` | `#12200A` | `#121A05` | texto e ícone sobre `cor.marca` |
| `cor.botao` | `#12200A` | `#D2FF3C` | botão primário (claro: tinta; escuro: volt) |
| `cor.botao-pressionado` | `#2C4416` | `#B5DE2B` | botão primário pressionado (proposta do Rafa, aprovada pela Lia) |
| `cor.sobre-botao` | `#C6F432` | `#121A05` | rótulo e ícone sobre `cor.botao` |
| `cor.link` | `#2F6600` | `#D2FF3C` | link, ação em texto, ícone de ação, item selecionado; substitui o teal `destaque` da v2 |
| `cor.marca-suave` | `#EEF9C9` | `#232B10` | fundo de item selecionado, selo "No normal", faixa de análise |
| `cor.foco` | `#2F6600` | `#D2FF3C` | anel de foco (teclado na web); igual a `cor.link` |
| `cor.sucesso` | `#1B6E3A` | `#6FD08E` | texto e ícone de sucesso |
| `cor.sucesso-suave` | `#E3F2E8` | `#17301F` | fundo do aviso de sucesso |
| `cor.alerta` | `#8A5300` | `#F2B851` | texto e ícone de alerta |
| `cor.alerta-suave` | `#FCEFD6` | `#3A2C12` | fundo do aviso de alerta |
| `cor.erro` | `#B3261E` | `#FF8A80` | texto e ícone de erro |
| `cor.erro-suave` | `#FBE6E4` | `#3D1C1A` | fundo do aviso de erro |
| `cor.sobre-erro` | `#FFFFFF` | `#3D1C1A` | texto sobre `cor.erro` (selo numérico da aba Treinos) |
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
| `cor.texto` | `cor.fundo` | texto | 4,50 | 15,53 | 16,15 | sim |
| `cor.texto` | `cor.superficie` | texto | 4,50 | 16,94 | 14,73 | sim |
| `cor.texto` | `cor.superficie-2` | texto | 4,50 | 14,08 | 12,51 | sim |
| `cor.texto-2` | `cor.fundo` | texto | 4,50 | 7,26 | 9,68 | sim |
| `cor.texto-2` | `cor.superficie` | texto | 4,50 | 7,92 | 8,83 | sim |
| `cor.texto-2` | `cor.superficie-2` | texto | 4,50 | 6,58 | 7,50 | sim |
| `cor.link` | `cor.fundo` | texto | 4,50 | 6,37 | 16,21 | sim |
| `cor.link` | `cor.superficie` | texto | 4,50 | 6,95 | 14,79 | sim |
| `cor.link` | `cor.marca-suave` | texto | 4,50 | 6,30 | 12,71 | sim |
| `cor.texto` | `cor.marca-suave` | texto | 4,50 | 15,35 | 12,67 | sim |
| `cor.sobre-botao` | `cor.botao` | texto | 4,50 | 13,25 | 15,40 | sim |
| `cor.sobre-botao` | `cor.botao-pressionado` | texto | 4,50 | 8,42 | 11,44 | sim |
| `cor.sobre-marca` | `cor.marca` | texto | 4,50 | 13,25 | 15,40 | sim |
| `cor.botao` | `cor.fundo` | grafico | 3,00 | 15,57 | 16,21 | sim |
| `cor.botao` | `cor.superficie` | grafico | 3,00 | 16,98 | 14,79 | sim |
| `cor.sobre-erro` | `cor.erro` | texto | 4,50 | 6,54 | 6,67 | sim |
| `cor.sucesso` | `cor.superficie` | texto | 4,50 | 6,29 | 9,05 | sim |
| `cor.sucesso` | `cor.sucesso-suave` | texto | 4,50 | 5,43 | 7,50 | sim |
| `cor.texto` | `cor.sucesso-suave` | texto | 4,50 | 14,63 | 12,20 | sim |
| `cor.alerta` | `cor.superficie` | texto | 4,50 | 6,33 | 9,59 | sim |
| `cor.alerta` | `cor.alerta-suave` | texto | 4,50 | 5,56 | 7,59 | sim |
| `cor.texto` | `cor.alerta-suave` | texto | 4,50 | 14,89 | 11,65 | sim |
| `cor.erro` | `cor.superficie` | texto | 4,50 | 6,54 | 7,51 | sim |
| `cor.erro` | `cor.erro-suave` | texto | 4,50 | 5,46 | 6,67 | sim |
| `cor.texto` | `cor.erro-suave` | texto | 4,50 | 14,15 | 13,08 | sim |
| `cor.corrida` | `cor.superficie` | texto | 4,50 | 5,46 | 8,19 | sim |
| `cor.corrida` | `cor.fundo` | texto | 4,50 | 5,00 | 8,98 | sim |
| `cor.ciclismo` | `cor.superficie` | texto | 4,50 | 7,09 | 7,89 | sim |
| `cor.ciclismo` | `cor.fundo` | texto | 4,50 | 6,50 | 8,65 | sim |
| `cor.natacao` | `cor.superficie` | texto | 4,50 | 6,47 | 8,09 | sim |
| `cor.natacao` | `cor.fundo` | texto | 4,50 | 5,93 | 8,87 | sim |
| `cor.grafico.pace` | `cor.superficie` | texto | 4,50 | 8,40 | 7,35 | sim |
| `cor.grafico.fc` | `cor.superficie` | texto | 4,50 | 7,17 | 7,78 | sim |
| `cor.grafico.media` | `cor.superficie` | grafico | 3,00 | 4,94 | 5,71 | sim |
| `cor.grafico.pace` | `cor.superficie-2` | grafico | 3,00 | 6,98 | 6,24 | sim |
| `cor.grafico.fc` | `cor.superficie-2` | grafico | 3,00 | 5,96 | 6,61 | sim |
| `cor.bloco.esforco` | `cor.superficie` | grafico | 3,00 | 16,94 | 14,73 | sim |
| `cor.bloco.recuperacao` | `cor.superficie` | grafico | 3,00 | 3,49 | 4,34 | sim |
| `cor.bloco.aquecimento` | `cor.superficie` | grafico | 3,00 | 3,49 | 4,34 | sim |
| `cor.bloco.leve` | `cor.superficie` | grafico | 3,00 | 3,49 | 4,34 | sim |
| `cor.borda-forte` | `cor.superficie` | grafico | 3,00 | 4,29 | 4,71 | sim |
| `cor.borda-forte` | `cor.fundo` | grafico | 3,00 | 3,93 | 5,16 | sim |
| `cor.foco` | `cor.fundo` | grafico | 3,00 | 6,37 | 16,21 | sim |
| `cor.foco` | `cor.superficie` | grafico | 3,00 | 6,95 | 14,79 | sim |
<!-- contraste:fim -->

## Tipografia
Fontes: **Inter** (SIL OFL 1.1, `@expo-google-fonts/inter`) no texto e **Barlow Condensed** (SIL OFL 1.1, `@expo-google-fonts/barlow-condensed`)
nos números e títulos curtos, como decidiu o Angelo ([[design/identidade-visual-v3]]). Reserva: fonte do sistema. Todo número usa algarismos
tabulares: `fontVariant: ["tabular-nums"]`.

| token | fonte e peso | tamanho / altura da linha | uso |
|---|---|---|---|
| `fonte.numero-heroi` | Barlow Condensed 800 (BarlowCondensed_800ExtraBold), tabular | 76 / 80 | número do treino no cartão do último treino |
| `fonte.numero-destaque` | Barlow Condensed 800, tabular | 30 / 34 | valor principal (melhor pace da sessão, cartão da lista) |
| `fonte.numero-grande` | Barlow Condensed 800, tabular | 24 / 28 | valores finais da quinzena |
| `fonte.titulo-tela` | Inter 800 (Inter_800ExtraBold) | 26 / 32 | título da tela |
| `fonte.titulo-secao` | Inter 800 | 18 / 24 | título de cartão e de grupo |
| `fonte.titulo-cartao` | Inter 800 | 15,5 / 22 | modalidade e tipo no cartão |
| `fonte.corpo` | Inter 400 (Inter_400Regular) | 16 / 24 | texto corrido, mensagens |
| `fonte.corpo-forte` | Inter 600 (Inter_600SemiBold) | 16 / 24 | valor na lista, ênfase |
| `fonte.botao` | Inter 600 | 16 / 20 | texto de botão |
| `fonte.rotulo` | Inter 500 (Inter_500Medium) | 14 / 20 | rótulo de valor, chip, legenda do gráfico |
| `fonte.legenda` | Inter 400 | 13 / 18 | rodapé, nota pequena |
| `fonte.sobretitulo` | Inter 800, letras espaçadas 1 | 12 / 16 | "ÚLTIMO TREINO", "FEEDBACK" |
| `fonte.eixo` | Inter 500, tabular | 12 / 16 | só rótulos de eixo e datas do gráfico |

Nada abaixo de 12. O texto acompanha o tamanho de fonte do sistema (`allowFontScaling` ligado); os números e `fonte.titulo-tela`
limitam a escala com `maxFontSizeMultiplier: 1.3` (números) e 1,5 (título) para não quebrar a linha.

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
Cantos mais discretos (v3, decisão do Angelo).

| token | valor | uso |
|---|---|---|
| `raio.pequeno` | 4 | barra de tiro, esqueleto de texto |
| `raio.bloco` | 8 | quadrado do ícone de modalidade, aviso, faixa de análise, detalhe da sessão |
| `raio.botao` | 10 | botão e campo (altura 48) |
| `raio.cartao` | 12 | cartão |
| `raio.cartao-destaque` | 14 | cartão do último treino |
| `raio.pilula` | 999 | selo, filtro, chip |
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
| caixa do dia: motivo `dor` (Meta 11, [[design/telas/caixa-do-dia]]) | `healing` |
| caixa do dia: motivo `fora_do_normal` | `show-chart` |
| caixa do dia: motivo `divergencia` | `event` (o mesmo da semana-padrão) |
| caixa do dia: motivo `checkin_vencendo` | `schedule` |
| caixa do dia: seleção de treino novo | `check-box`, `check-box-outline-blank` |
| caixa do dia: abrir e fechar o detalhe | `expand-more`, `expand-less` |
| caixa do dia: correção ainda não salva | `edit` |
| caixa do dia: estado sem alunos | `group` |
| caixa do dia: opção da folha "Tipo do treino" (#427) | `radio-button-checked`, `radio-button-unchecked`, `close` |

Os nomes da semana-padrão foram conferidos no mapa de glifos do `@expo/vector-icons` pelo Rafa (#268, ver [[modulos/mobile]]). Os do
check-in são do conjunto padrão do Material Icons e ainda precisam ser conferidos pelo Rafa na #299.
Os da caixa do dia foram conferidos no mapa de glifos do `@expo/vector-icons` (Lia, 16/11); o Rafa reconfere na #426.
