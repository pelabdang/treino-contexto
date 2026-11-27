---
tipo: design
status: rascunho
dono: lia
atualizado: 2026-11-27
links: [[design/identidade-visual-v2]], [[design/tokens]], [[design/guia-visual]], [[design/telas/inicio-atleta-v3]], [[design/auditoria-ux-e-inicio-do-atleta]], [[modulos/mobile]]
---
# Identidade visual v3: tokens, tipografia, cantos e logo (proposta final)

Fecha a [[design/identidade-visual-v2]] com as decisões do Angelo de 18/11. Esta nota traz a **tabela de tokens v3**, que o Rafa
transforma em tema depois do aval do Angelo à spec. Enquanto isso, [[design/tokens]] continua sendo a tabela oficial e o app não muda.
As telas que usam estes tokens estão em [[design/telas/inicio-atleta-v3]]. Atleta (Ana), treinos e números **sintéticos**.

## O que o Angelo decidiu (18/11)
| decisão | como aparece aqui |
|---|---|
| cor de marca **volt `#C6F432`** | tabela de cores; usada como preenchimento, nunca como texto sobre fundo claro |
| fonte **Barlow Condensed** nos números e títulos curtos | tabela de tipografia; o resto continua em Inter |
| **cantos mais discretos** | cartão 12, bloco 8, botão 10 (eram 20, 14 e 24 na v2) |
| **ordem do treino aprovada** | como foi, comparado ao normal, o que você respondeu, os tiros, contexto |
| **último treino primeiro** no início | o convite do check-in ("Agora") desce e vira faixa dentro ou abaixo do cartão do último treino |
| gráfico **quinzenal, 2 linhas e frase de análise** | cartão "Seus últimos 14 dias" |
| **Pulso** é nome de **trabalho** | aparece nos esboços e no logo; **sem confirmação**, ver "Nome e logo" |

## Cores
Claro e escuro. O app segue o tema do sistema. Valores vistos nos esboços `inicio-v3-*`, `treino-v3-*` e `treinos-lista-*`.

| token | claro | escuro | uso |
|---|---|---|---|
| `cor.marca` | `#C6F432` | `#D2FF3C` | ícone do app, aba ativa, faixa de check-in, símbolo do logo |
| `cor.sobre-marca` | `#12200A` | `#121A05` | texto e ícone sobre a marca |
| `cor.botao` | `#12200A` | `#D2FF3C` | botão primário (claro: tinta com rótulo volt; escuro: volt com rótulo escuro) |
| `cor.sobre-botao` | `#C6F432` | `#121A05` | rótulo do botão primário |
| `cor.link` | `#2F6600` | `#D2FF3C` | link, ação em texto, anel de foco; substitui `cor.destaque` (teal) |
| `cor.marca-suave` | `#EEF9C9` | `#232B10` | selo "No normal", faixa de análise |
| `cor.fundo` | `#F6F5F1` | `#0F1214` | fundo da tela |
| `cor.superficie` | `#FFFFFF` | `#181C1F` | cartão |
| `cor.superficie-2` | `#ECEAE4` | `#232A2E` | quadrado do ícone de modalidade, esqueleto |
| `cor.borda` | `#DEDBD3` | `#2C3236` | contorno de cartão (decorativa) |
| `cor.borda-forte` | `#7D7A72` | `#80878D` | contorno de botão secundário e filtro |
| `cor.texto` / `cor.texto-2` | `#1A1D1F` / `#4C5257` | `#ECEEEF` / `#B4BBC0` | texto principal e secundário |
| `cor.alerta` / `cor.alerta-suave` | `#8A5300` / `#FCEFD6` | `#F2B851` / `#3A2C12` | selo "Sem check-in" e "Fora do normal" |
| `cor.erro` / `cor.sobre-erro` | `#B3261E` / `#FFFFFF` | `#FF8A80` / `#3D1C1A` | selo numérico da aba Treinos, mensagens de erro |
| modalidade: corrida / natação / ciclismo | `#B4470F` / `#1A5FA8` / `#6B3FB0` | `#FF9A5C` / `#7DB7F0` / `#BFA2F2` | ícone da modalidade (sempre com ícone e nome) |
| gráfico: condicionamento / fadiga | `#1A5FA8` / magenta do guia | `#7DB7F0` / `#F48FBF` | duas linhas (cheia e tracejada); valores iguais a [[design/tokens]] |

Na v2 o `cor.destaque` virava `cor.link`, `cor.botao` e `cor.marca`. Aqui isso fica fechado. **Pendência técnica:** ao aprovar, o Rafa
move estes valores para a tabela "Cores" de [[design/tokens]], e eu rodo `python docs/design/contraste.py --escrever`. Hoje o script
só conhece os tokens antigos.

### Contraste (razão WCAG; mínimo AA: texto 4,5; componente e gráfico 3,0)
Calculado com a mesma fórmula de `docs/design/contraste.py`.
| par | claro | escuro |
|---|---|---|
| `texto` sobre `superficie` | 16,94 | 14,73 |
| `texto-2` sobre `superficie` | 7,92 | 8,83 |
| `texto-2` sobre `superficie-2` | 6,58 | 7,50 |
| `link` sobre `superficie` | 6,95 | 14,79 |
| `link` sobre `fundo` | 6,37 | 16,21 |
| `link` sobre `marca-suave` ("No normal") | 6,30 | 12,71 |
| `alerta` sobre `alerta-suave` ("Sem check-in") | 5,56 | 7,59 |
| `sobre-marca` sobre `marca` | 13,25 | 15,40 |
| `borda-forte` sobre `superficie` | 4,29 | 4,71 |
| corrida, natação, ciclismo sobre `superficie` | 5,46 / 6,47 / 7,09 | 8,19 / 8,09 / 7,89 |

O volt `#C6F432` **nunca** é texto sobre o papel claro (1,2:1). Sobre o volt, só tinta. Nada depende só da cor: cada selo tem ícone e
texto; a modalidade tem ícone e nome; as duas linhas do gráfico diferem por traço e rótulo.

## Tipografia
| token | fonte e peso | tamanho | uso |
|---|---|---|---|
| `fonte.numero-heroi` | Barlow Condensed 800, tabular | 76 (cartão do último treino) e 88 (quando o número é curto, como `4:11`) | número do treino |
| `fonte.numero-destaque` | Barlow Condensed 800, tabular | 30 | valor principal do cartão de treino da lista |
| `fonte.numero-grande` | Barlow Condensed 800, tabular | 24 | valores finais da quinzena (44 e 58 no exemplo) |
| `fonte.titulo-tela` | Inter 800 | 26 | "Olá, Ana", "Treinos" |
| `fonte.titulo-secao` | Inter 800 | 18 | título de cartão e de grupo |
| `fonte.titulo-cartao` | Inter 800 | 15,5 | modalidade e tipo no cartão |
| `fonte.corpo` | Inter 400 | 14 (texto do feedback) e 16 (telas de formulário) | texto corrido |
| `fonte.rotulo` | Inter 600 a 700 | 12,5 a 13 | meta, selo, data |
| `fonte.sobretitulo` | Inter 800, letras espaçadas 1 | 12 | "ÚLTIMO TREINO", "FEEDBACK" |
| `fonte.eixo` | Inter 500 | 11,5 | eixo e legenda do gráfico |

- **Por quê Barlow Condensed:** é o rosto de relógio e placar; o número ocupa pouco de largura e cabe grande em celular de 360 de
  largura (`0:45:12` a 76 cabe com folga). Tabular, para as colunas alinharem.
- Pacote novo: `@expo-google-fonts/barlow-condensed` (OFL, gratuito, sem conta). Plano B: Inter 800 tabular.
- **Texto mínimo:** 11,5 só em eixo e nota; o resto parte de 12,5. O texto corrido escala até 2x; os números grandes limitam a 1,3x
  (`maxFontSizeMultiplier`) para não quebrar a linha.
- Os esboços usam Barlow se estiver instalada e, senão, uma condensada do sistema; a largura real varia um pouco.

## Cantos, espaço e movimento
| token | valor | uso |
|---|---|---|
| `raio.cartao-destaque` | 14 | cartão do último treino |
| `raio.cartao` | 12 | cartão de lista, de gráfico, de treino |
| `raio.bloco` | 8 | ícone de modalidade (quadrado), faixa de análise, faixa de check-in |
| `raio.botao` | 10 | botão (altura 48) |
| `raio.pilula` | metade da altura | selo (28 de altura), filtro (alvo 44), selo numérico da aba |
| `raio.pequeno` | 4 | barra de tiro, esqueleto de texto |
| espaçamento | múltiplos de 4; respiro entre cartões 12; margem lateral 16; padding do cartão 16 | |
| movimento | transição de 150 a 200 ms e fade; nada de animação de número | respeita "reduzir movimento" |

**Por quê mais discretos:** foi o pedido do Angelo. Cantos de 12 mantêm a simpatia sem o ar de brinquedo, e deixam mais área para o
número.

## Ícones, vazio e carregando
- Ícones Material já no app e os pictogramas de modalidade num quadrado `superficie-2` de 36 a 40, com raio 8.
- Sem ilustração. O único motivo gráfico é a **linha de pulso** (a do logo) nos estados vazio e carregando.
- Estados: carregando (esqueleto com `superficie-2`; leitor de tela ouve "Carregando"), vazio (linha de pulso e frase com ação),
  erro (mensagem curta, causa e "Tentar de novo"). Detalhe por tela em [[design/telas/inicio-atleta-v3]].

## Nome e logo
**"Pulso" é nome de trabalho e não está confirmado.** Nada foi pesquisado no INPI nem nas lojas. Se o Angelo trocar o nome, só muda a
palavra; o símbolo (linha de pulso em quadrado volt) serve a qualquer um.

| arquivo | o que é |
|---|---|
| `docs/design/marca/logo-pulso-simbolo.svg` | símbolo: quadrado volt, raio 28 em 128 (cerca de 22%), linha de pulso em tinta |
| `docs/design/marca/logo-pulso-horizontal-claro.svg` | símbolo e palavra PULSO em Barlow Condensed 800, letras espaçadas, tinta sobre papel |
| `docs/design/marca/logo-pulso-horizontal-escuro.svg` | o mesmo sobre `#0F1214`, símbolo `#D2FF3C`, palavra `#ECEEEF` |
| `docs/design/marca/icone-app-1024.svg` | ícone do app: fundo volt **sem cantos** (iOS e Android arredondam sozinhos), linha de pulso em tinta |
| `docs/design/marca/icone-android-frente.svg` | camada da frente do ícone adaptativo: só a linha, dentro dos 66% centrais, fundo transparente |
| `docs/design/marca/icone-android-monocromatico.svg` | a mesma linha em preto, para o ícone temático do Android 13 |

Regras de uso: área de respiro ao redor do símbolo igual a 1/4 da sua largura; tamanho mínimo do símbolo 24; palavra nunca sobre volt
sem ser em tinta; não girar nem esticar. O ícone de fundo do Android adaptativo é a cor `#C6F432` chapada (o Rafa define no `app.json`).

## Impacto no código (para o Rafa, depois do aval)
1. Tema: cores e raios acima; `fonte.numero-*` em Barlow Condensed 800.
2. Pacote `@expo-google-fonts/barlow-condensed`; trocar o ícone e o splash pelos arquivos de `docs/design/marca/` (exportar PNG 1024).
3. Componentes: `CartaoUltimoTreino`, `FaixaCheckin`, `CartaoQuinzena`, `CartaoTreino` (lista e início), `SeloEstado`, `Abas`.
4. Sem conta nova e sem serviço pago.

## Perguntas ao Angelo
Estão no fim de [[design/telas/inicio-atleta-v3]], junto com as das telas.
