---
tipo: design
status: rascunho
dono: lia
atualizado: 2026-11-04
links: [[design/guia-visual]], [[design/tokens]], [[modulos/mobile]], [[decisoes/0004-contrato-tela-evolucao]], [[metricas/tiros-1km]], [[decisoes/0006-upload-de-fit]]
---
# Tela: evolução dos tiros de 1 km (exemplo do guia)

Aplicação do [[design/guia-visual]] à tela que já existe (`TelaEvolucao`, `GraficoTiros` e `BotaoEnviarFit`, em
[[modulos/mobile]]). É um esboço para a issue do tema, do Rafa: nada em `apps/mobile/` muda nesta nota.
Todos os números são **sintéticos**.

Esboço do tema claro, em largura de celular pequeno (360): ![[design/telas/evolucao-tiros-claro.svg]]
(arquivo `docs/design/telas/evolucao-tiros-claro.svg`). O tema escuro usa a coluna "escuro" de [[design/tokens]]
com o mesmo layout.

## Objetivo
Depois do treino de tiros, o atleta abre o app e vê, em poucos segundos, o melhor tiro de hoje e se ele está
melhorando. O professor vê a mesma série com calma, toca nos treinos e compara a média.

## Dados
`GET /atletas/{id}/evolucao/tiros-1km`, pelo cliente gerado ([[decisoes/0004-contrato-tela-evolucao]], com o
Adendo 1). Valor principal: `pace_melhor` (texto `m:ss` da API) e `fc_melhor_tiro`. Secundário: `pace_medio`,
`fc_media`, `n_tiros`. Eixos e rótulos: bloco `eixos`. O app não formata pace e não escolhe escala.
"Último treino" é a última sessão da lista (a API manda em ordem de data crescente).

## Hierarquia da informação
1. Melhor tiro do último treino, em número grande (`fonte.numero-destaque`).
2. A tendência: gráfico do melhor pace e da FC do melhor tiro.
3. Detalhe de uma sessão, ao tocar no ponto.
4. A lista dos treinos, que também é a alternativa em texto ao gráfico.
5. Ação de apoio: enviar arquivo FIT.
6. Rodapé técnico: versão do cálculo.

## Layout
```
┌──────────────────────────────────┐  fundo (papel), margem 16
│ Tiros de 1 km                    │  fonte.titulo-tela
│ (● Corrida)                      │  chip de modalidade
│ Evolução do melhor tiro de cada  │  fonte.corpo, cor.texto-2
│ treino                           │
│ ┌──────────────────────────────┐ │
│ │   ⇪  Enviar arquivo FIT      │ │  botão secundário, altura 48
│ └──────────────────────────────┘ │
│ ┌ Último treino · 25/03/25 ────┐ │  cartão
│ │ Melhor tiro                  │ │  fonte.rotulo
│ │ 4:02 min/km                  │ │  fonte.numero-destaque + unidade
│ │ FC do melhor tiro 173 bpm    │ │
│ │ Média dos tiros 4:06 min/km ·│ │  secundário, cor.texto-2
│ │ 6 tiros                      │ │
│ └──────────────────────────────┘ │
│ ┌ Evolução ────────────────────┐ │  cartão
│ │ Melhor pace (min/km)  mais   │ │
│ │                    rápido ↑  │ │
│ │ 4:00 ┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄●    │ │  cor.grafico.pace
│ │ 4:10 ┄●──────●──────◉┄┄┄┄    │ │  ◉ = selecionado
│ │ FC do melhor tiro (bpm)      │ │
│ │ 176  ┄┄┄┄┄┄┄┄┄┄┄┄◉┄┄┄┄┄┄     │ │  cor.grafico.fc
│ │ 174  ┄●──────●┄┄┄┄┄┄┄┄┄●     │ │
│ │  04/03  11/03  18/03  25/03  │ │  fonte.eixo
│ │ ┌ 18/03/25 · 5 tiros ──────┐ │ │  detalhe, cor.superficie-2
│ │ │ Melhor tiro 4:05 · FC 176│ │ │
│ │ │ Média 4:09 · FC média 171│ │ │
│ │ └──────────────────────────┘ │ │
│ └──────────────────────────────┘ │
│ ┌ Treinos ─────────────────────┐ │  cartão, mais recente no alto
│ │ 25/03/25  4:02 min/km 173 bpm│ │  linha de 56, tocável
│ │          média 4:06 · 6 tiros│ │
│ │ 18/03/25  4:05 min/km 176 bpm│ │
│ │ ...                          │ │
│ └──────────────────────────────┘ │
│ cálculo: tiros_1km@4             │  fonte.legenda
└──────────────────────────────────┘
```
O desenho em ASCII é aproximado; as posições exatas estão no SVG.

### Gráfico
- Dois painéis (pace e FC), como hoje, com título e unidade. Pace com eixo invertido e o aviso "mais rápido ↑".
- Só a série principal (melhor tiro). **A média não entra no gráfico desta tela**: os `eixos` são calculados pelo
  valor principal e a média pode sair da faixa (Adendo 1 da ADR 0004). A média fica no detalhe e na lista. Por isso
  não há legenda: com uma série só, o título do painel basta. Se um dia a média entrar (eixos que cubram as duas),
  ela usa `cor.grafico.media` tracejada e a legenda do guia.
- Ponto de raio 5; o selecionado tem raio 7 e anel de 2 em `cor.texto`, e a data dele fica em negrito.
- Área de toque de 44 por 44 em cada ponto.

### Na web (professor)
Conteúdo centralizado com largura máxima de 720 e margem de 24. Os dois painéis ficam um embaixo do outro, mais
largos; a lista ganha uma coluna para a média ("Média dos tiros") em vez da segunda linha.

## Estados
| estado | o que aparece | texto |
|---|---|---|
| carregando | cabeçalho e botão normais; esqueleto dos três cartões | "Carregando seus tiros..." |
| vazio (`sessoes: []`) | ícone `insert-chart-outlined`, título, frase e o botão **primário** "Enviar arquivo FIT" no lugar do secundário | título "Ainda não há treinos de tiros de 1 km"; frase "Envie o arquivo FIT de um treino com tiros para ver a evolução aqui." |
| erro de rede | ícone `wifi-off`, frase e botão "Tentar de novo" | "Não foi possível falar com o servidor" |
| erro `404` | ícone `error-outline` e frase | "Atleta não encontrado" |
| outro erro | ícone `error-outline` e frase | "Não foi possível carregar os tiros. Tente de novo mais tarde." |
| sem FC em nenhuma sessão | painel de FC troca por texto em `cor.texto-2` | "Nenhuma sessão deste período tem frequência cardíaca." |
| melhor tiro sem FC | no cartão e na lista | "FC do melhor tiro: sem FC" |
| `reclassificacao_pendente` | no rodapé, ícone `info-outline` e texto em `cor.texto-2` | "cálculo em atualização" |

### Envio de FIT (`BotaoEnviarFit`)
| estado | o que aparece | texto |
|---|---|---|
| parado | botão secundário com ícone `upload-file` | "Enviar arquivo FIT" |
| enviando | botão desligado com indicador no lugar do ícone | "Enviando..." |
| sucesso, atividade nova | aviso de sucesso abaixo do botão | "Atividade adicionada" |
| sucesso, já existia | aviso de sucesso | "Essa atividade já estava aqui" |
| erro | aviso de erro com a mensagem de hoje (rede, 404, mensagem da API) | textos de `mensagemErroEnvio`, sem mudança |

Os textos de erro e de sucesso são os de hoje ([[decisoes/0006-upload-de-fit]]). O aviso é anunciado ao leitor de tela.

## Acessibilidade
- Ordem de leitura: título, modalidade, subtítulo, botão, último treino, gráfico, lista, rodapé.
- Ponto do gráfico: `accessibilityLabel` "Sessão de 18/03/25, melhor tiro 4:05 min/km" (pace) e "Sessão de
  18/03/25, FC do melhor tiro 176 bpm" (FC), com os textos da API.
- A lista de treinos repete todos os valores do gráfico em texto.
- Linha da lista com 56 de altura (tocar abre o mesmo detalhe do ponto).

## O que muda em relação ao app de hoje
Para a issue do tema (Rafa). Nada aqui muda comportamento da API.
| hoje | proposta |
|---|---|
| fundo `#fff`, cores soltas no código (`#1b6ca8`, `#c0392b`, `#b00020`...) | tokens de [[design/tokens]], tema claro e escuro pelo sistema |
| margem 24 | 16 no celular, 24 a partir de 600 de largura |
| painéis com a média (`pace_medio_s_km`, `fc_media`) e títulos "Pace médio" e "FC média" | melhor tiro (`pace_melhor_s_km`, `fc_melhor_tiro`), títulos "Melhor pace (min/km)" e "FC do melhor tiro (bpm)"; essa troca é da #154 |
| sem cartão de resumo | cartão "Último treino" com o melhor tiro em destaque |
| lista em ordem crescente, uma linha | mais recente no alto, duas linhas (principal e média) |
| alvo de toque do ponto 32 | 44 |
| botão primário azul no topo | botão secundário no topo; primário só no estado vazio |
| mensagens só em texto colorido | aviso com ícone, fundo suave e anúncio ao leitor de tela |
| rótulos de eixo 11 | 12 (`fonte.eixo`) |
