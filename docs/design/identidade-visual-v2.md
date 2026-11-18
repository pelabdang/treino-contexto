---
tipo: design
status: rascunho
dono: lia
atualizado: 2026-11-18
links: [[design/guia-visual]], [[design/tokens]], [[design/auditoria-ux-e-inicio-do-atleta]], [[design/telas/inicio-atleta]], [[modulos/mobile]]
---
# Identidade visual v2: esportiva e amigável (proposta)

Segunda rodada, depois das respostas do Angelo à [[design/auditoria-ux-e-inicio-do-atleta]]: tom **esportivo e amigável**,
referências Strava e Garmin "mas pode propor coisas". Isto é **proposta para ele reagir**. Nada aqui muda o app nem o
[[design/tokens]] até o Angelo aprovar; depois disso a tabela de tokens v2 vira a tabela oficial e o Rafa a transforma em tema.

Quadro de estilo (claro e escuro lado a lado, com os três logotipos): ![[design/telas/inicio-atleta/quadro-de-estilo.svg]]

**Nenhum nome, logotipo, cor ou fonte está decidido**: Pulso, Cadência e Contexto são **propostas** que o Angelo ainda não escolheu. Os esboços usam o nome provisório **Pulso** só para ter algo na tela, com atletas e números **sintéticos**. A fonte nos SVGs aparece com uma reserva (a
condensada pesada real é a Barlow Condensed; o SVG a usa se ela estiver instalada).

## Ideia em uma frase
**Preto-tinta e verde volt, números enormes e condensados, cartões bem arredondados.** É a energia de um relógio esportivo com a
simpatia de um app de amigos, sem copiar o laranja do Strava nem o azul do Garmin.

## Paleta
Uma cor de marca forte, **volt** (verde-limão), usada como **preenchimento**, nunca como texto sobre fundo claro (limão sobre papel
não passa de 1,2:1). O texto sempre vai em tinta escura sobre o volt, ou o volt vai sobre o escuro. Assim a marca fica vibrante e o AA
fica garantido nos dois temas.

| papel | claro | escuro | nota |
|---|---|---|---|
| `cor.marca` | `#C6F432` | `#D2FF3C` | fundo do cartão "Agora", aba ativa, logotipo |
| `cor.sobre-marca` | `#12200A` | `#121A05` | texto e ícone sobre a marca |
| `cor.botao` (primário) | `#12200A` (tinta) | `#D2FF3C` | botão primário: tinta com rótulo volt no claro, volt com rótulo escuro no escuro |
| `cor.sobre-botao` | `#C6F432` | `#121A05` | rótulo do botão primário |
| `cor.link` | `#2F6600` | `#D2FF3C` | link, ícone de ação, anel de foco (substitui o teal `cor.destaque`) |
| `cor.marca-suave` | `#EEF9C9` | `#232B10` | chip "dentro do seu normal", faixa de análise |
| `cor.fundo` | `#F6F5F1` | `#0F1214` | papel (claro igual ao de hoje; escuro um pouco mais fundo) |
| `cor.superficie` | `#FFFFFF` | `#181C1F` | cartão |
| `cor.texto` / `cor.texto-2` | `#14181A` / `#4C5257` | `#ECEEEF` / `#B4BBC0` | como hoje |

**Fica como está:** cores de modalidade (corrida laranja, natação azul, ciclismo roxo), cores dos gráficos (azul `cor.grafico.pace`,
magenta `cor.grafico.fc`), sucesso, alerta e erro. Motivo: já têm contraste conferido e dão leitura imediata de modalidade; a
marca não disputa com elas porque só aparece em "agora", ação e aba ativa.

### Contraste (razão WCAG, mínimo AA: texto 4,5; gráfico e componente 3,0)
| par | claro | escuro |
|---|---|---|
| `sobre-marca` sobre `marca` | 13,25 | 15,40 |
| rótulo do botão sobre o botão | 13,25 | 15,40 |
| `link` sobre `fundo` | 6,37 | 16,21 |
| `link` sobre `superficie` | 6,95 | 14,79 |
| `link` sobre `marca-suave` | 6,30 | 12,71 |
| `texto` sobre `marca-suave` | 16,19 | 12,67 |
| `texto` sobre `fundo` | 16,38 | conforme tokens |
| `texto-2` sobre `superficie` | 7,92 | 8,83 |
| azul do gráfico sobre `superficie` | 8,40 | 7,35 |
| magenta do gráfico sobre `superficie` | 7,17 | 7,78 |
| corrida / natação / ciclismo sobre `superficie` | 5,46 / 6,47 / 7,09 | 8,19 / 8,09 / 7,89 |
Números calculados por mim com a mesma fórmula do `docs/design/contraste.py`; ao aprovar, entram no script e na tabela oficial.

Nada depende só da cor: modalidade tem ícone e nome; "dentro do normal" tem ícone de confere e texto; as duas linhas do gráfico
diferem por traço (cheio e tracejado) e por rótulo direto.

## Tipografia
- **Números de impacto e títulos curtos:** **Barlow Condensed ExtraBold (800)**, em números tabulares. É o rosto esportivo (relógio,
  placar). Tamanhos: `numero-heroi` 84 a 100 (o melhor tiro), `numero-grande` 28 a 40 (pace, carga), `numero-tiro` 22 (barras).
- **Todo o resto:** **Inter** como hoje (400 texto, 700 e 800 título e botão). Corpo 16/24 e legenda 13/18 não mudam.
- Custo: um pacote novo, `@expo-google-fonts/barlow-condensed` (licença OFL, gratuito, sem conta). Plano B sem pacote novo: Inter 800 em
  números tabulares (menos esportivo, mesma legibilidade).
- Escala do sistema: números grandes limitam em 1,3x (`maxFontSizeMultiplier`) para não quebrar a linha; o texto corrido escala até 2x.

## Formas, espaço e movimento
| elemento | valor | porquê |
|---|---|---|
| cartão destaque ("Agora") | raio 24 | amigável e "de aplicativo", chama o olhar |
| cartão | raio 20 | mais macio que os 16 de hoje |
| bloco interno (chip largo, faixa de análise) | raio 14 | |
| botão e chip | pílula (altura/2), botão 48 | alvo grande e simpático |
| borda | 1 em `cor.borda`; destaque 0 (sem borda, só cor) | |
| espaçamento | escala de hoje (múltiplos de 4); respiro entre cartões 16 | |
| movimento | só transição curta (150 a 200 ms) e fade; sem confete nem animação de número | respeita "reduzir movimento" |

## Ícones e ilustração
- **Ícones:** continuam os Material já no app (rápido e acessível), mais os **pictogramas de modalidade** (corrida, natação,
  ciclismo) num círculo suave. Futuro: um conjunto próprio e consistente.
- **Ilustração:** **não** no começo. O que dá personalidade é a cor, o número grande e o texto. Um único motivo gráfico: a **linha de
  pulso** (a mesma do logotipo) como fio de estados vazios e de carregamento ("Nenhum treino ainda").
- **Fotos e mapa:** nenhum por enquanto (ver Strava e Garmin, abaixo).

## Tom das palavras (esportivo e amigável)
- Fala com "você", frases curtas, verbo no começo da ação: "Como foi a natação de ontem?", "Responder o check-in".
- Celebra **fatos**, não adjetivos: "Melhor tiro da série: 4:11", e não "Arrasou!". O app já evita adjetivo de valor em métrica
  (carga, forma, normal) e o feedback tem checagens; a simpatia vem do tom e da forma, não de promessas.
- Sem culpa: não há sequência (streak) nem "você perdeu"; o check-in pendente é um convite com prazo, não uma cobrança.
- Estimativa sempre rotulada ("estimativa").

## Nomes e logotipos (a escolher; nada pesquisado em registro de marca)
| nome | ideia | logotipo simples |
|---|---|---|
| **Pulso** (minha preferência) | batida do coração e impulso; curto, fácil de falar e de achar | quadrado volt com uma linha de pulso em tinta |
| **Cadência** | o ritmo do treino; serve a corrida, bike e nado | três barras que crescem, como passos |
| **Contexto** | é o que o app faz (o treino lido no seu contexto) e já é o nome do projeto | anel com ponto no centro (foco) |

Os três usam o mesmo contêiner (quadrado com cantos grandes, volt, forma em tinta) e a palavra em Barlow Condensed 800 com letras
espaçadas. Antes de adotar qualquer um: checar o registro (INPI) e o nome na loja de aplicativos. Isso não foi feito e depende do
Angelo.

## O que pegar do Strava e do Garmin, e o que fazer diferente
**Do Strava (pegar):**
- O **cartão de atividade** como unidade de tudo: ícone de modalidade, título, e uma **fileira de três números** com unidade
  pequena ao lado do número grande. Usamos nos treinos recentes e no último treino.
- **Uma cor de ação só** e muito branco em volta: a ação principal é óbvia. Nossa marca volt faz isso.
- **Resumo da semana** em uma faixa (para a segunda rodada; ver a Direção B).
- **Fazer diferente:** sem feed social, sem "kudos", sem segmentos e ranking, sem medalhas e sem sequência (pressão de comparação não
  combina com um atleta que treina com professor). O Strava mostra o que **os outros** fizeram; aqui o ponto é **o seu normal**.

**Do Garmin (pegar):**
- **Números condensados e pesados** com a unidade ao lado, como no mostrador de um relógio.
- **Cor por modalidade/zona** e o **medidor com faixa** (aqui, a barra "seu normal" com a faixa e o ponto de hoje).
- A **frase curta de estado** ("seu status de treino"): uma linha de texto que explica o gráfico. Usamos como a frase da quinzena.
- **Fazer diferente:** o Garmin Connect é denso e configurável (painéis, widgets); aqui a ordem é **fixa e curta**, com uma pergunta
  por cartão. Sem siglas na cara do atleta (nada de CTL, ATL, TSB na tela; o app diz "condicionamento", "fadiga").

**Mapa:** **não agora.** Mapa com base de ruas manda a localização do treino a um provedor de mapas (privacidade e, em geral,
custo). Alternativa de uma etapa futura: **desenhar o trajeto como uma linha**, sem mapa de fundo, só com os dados que já temos
(quando o treino tem posição). Se um dia quisermos mapa de verdade, é decisão do Angelo (custo e privacidade): **PRECISA DO ANGELO**.

**Não copiar:** laranja do Strava, azul/preto do Garmin, as fontes deles, os formatos exatos de cartão e os ícones.

## Impacto no código (para o Rafa, depois da aprovação)
1. Tokens: trocar `cor.destaque` (teal) por `cor.link`, `cor.botao` e `cor.marca` (tabela acima); novo `raio.cartao-destaque`, `raio.pilula`.
2. Fonte: `fonte.numero-heroi`, `fonte.numero-grande` em Barlow Condensed 800 (ou Inter 800 se for o plano B).
3. Componentes: `CartaoAgora`, `CartaoUltimoTreino`, `CartaoQuinzena`, `ItemTreino`, `ChipNormal`, `Abas`.
4. Sem conta nova, sem serviço pago.

## Perguntas ao Angelo
1. A direção **preto-tinta + volt** te agrada? Prefere mais sóbria (a atual, teal) ou outra cor forte (laranja, azul-elétrico, magenta)?
2. **Nome:** Pulso, Cadência, Contexto ou outro? Ele tem algum que já usa?
3. **Números condensados e pesados** (Barlow Condensed) ou só uma versão mais pesada da fonte atual?
4. Cantos **bem arredondados** assim, ou mais discretos?
5. **Sem ilustração** no começo está bom?
