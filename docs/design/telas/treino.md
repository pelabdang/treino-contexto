---
tipo: design
status: rascunho
dono: lia
atualizado: 2026-11-06
links: [[design/guia-visual]], [[design/tokens]], [[design/telas/evolucao-tiros]], [[modulos/mobile]], [[decisoes/0004-contrato-tela-evolucao]], [[decisoes/0007-clima-da-atividade]]
---
# Tela: um treino, com o clima

Spec escrita depois da implementação (`TelaTreino`, rota `/treino/<atividade_id>`, #159, PR #215). Fixa o que
foi aprovado e o que muda. Todos os números são **sintéticos**.

## Objetivo
O atleta (ou o professor) abre um treino e vê, de uma vez, quanto durou, a distância, o pace e a FC, e em que
condição de tempo foi feito. Responde: "como foi esse dia?".

## Dados
`GET /atletas/{id}/atividades/{id}`, pelo cliente (`buscarAtividade`). Campos: `modalidade`, `data_local`,
`hora_local`, `duracao`, `distancia_m`, `pace_medio`, `fc_media` e `clima`. O app só mostra o que a API manda
([[decisoes/0004-contrato-tela-evolucao]], Adendo 2): não calcula nem reformata pace e duração.
A distância hoje é convertida de metros no app; a API passa a mandar o texto pronto (#216) e o app deixa de converter.

## Hierarquia da informação
1. Duração, em `fonte.numero-destaque`.
2. Distância, pace médio e FC média.
3. Clima: temperatura, sensação, umidade e vento.
4. Contexto: modalidade (chip), data e hora locais.
5. Atribuição do dado de clima.

## Layout
Celular de 360, tema claro (a margem é 16; a partir de 600 é 24, largura máxima como na [[design/telas/evolucao-tiros]]).
```
┌──────────────────────────────────┐
│ ← Voltar                         │  botão de texto, alvo 44
│ Treino                           │  fonte.titulo-tela
│ (🏃 Corrida)  18/03/25 às 06:30  │  chip + fonte.corpo, cor.texto-2
│ ┌──────────────────────────────┐ │  cartão
│ │ Duração                      │ │  fonte.rotulo
│ │ 0:52:05                      │ │  fonte.numero-destaque
│ │ Distância: 10,00 km          │ │
│ │ Pace médio: 5:12 min/km      │ │  só se a API mandar
│ │ FC média: 152 bpm            │ │  ou "sem FC"
│ └──────────────────────────────┘ │
│ ┌ Clima ───────────────────────┐ │  cartão
│ │ Temperatura          24,3 °C │ │  linhas de 44
│ │ Sensação térmica     25,1 °C │ │
│ │ Umidade                61 %  │ │
│ │ Vento                8,2 km/h│ │
│ │ Weather data by Open-Meteo…  │ │  fonte.legenda
│ └──────────────────────────────┘ │
└──────────────────────────────────┘
```
O título é sempre "Treino": a modalidade fica só no chip (ícone `directions-run`, `directions-bike` ou `pool`
mais o nome; a cor da modalidade nunca é a única informação).

## Distância
- Corrida e ciclismo: km com duas casas e vírgula ("10,00 km").
- **Natação: metros**, com separador de milhar ("1.800 m"). Piscina e águas abertas se medem em metros.
- Quem formata é a API (#216); a regra acima é o pedido de design para ela. Sem distância, a linha some.

## Estados
Segue o padrão do [[design/guia-visual]] e da [[design/telas/evolucao-tiros]] (#211).
| estado | o que aparece | texto |
|---|---|---|
| carregando | esqueleto dos dois cartões (`cor.superficie-2`, `raio.pequeno`, pulso de `movimento.esqueleto`) e o texto | "Carregando o treino..." |
| erro de rede | ícone `wifi-off` de 40 (`icone.estado`, `cor.erro`), frase e botão "Tentar de novo" | "Não foi possível falar com o servidor" |
| erro `404` | ícone `error-outline` e frase | "Treino não encontrado" (ou "Atleta não encontrado") |
| outro erro | ícone `error-outline` e frase | "Não foi possível carregar este treino. Tente de novo mais tarde." |
| sem pace (natação) | a linha "Pace médio" não aparece | |
| sem FC | a linha mostra | "FC média: sem FC" |

### Cartão "Clima" (`clima.estado`)
| estado | o que aparece | texto |
|---|---|---|
| `ok` | quatro linhas e a atribuição `clima.atribuicao`; valor ausente vira "sem dado" | "Weather data by Open-Meteo.com" |
| `indoor` | aviso neutro com `info-outline` | "Treino em ambiente fechado: não há clima para mostrar." |
| `sem_posicao` | aviso neutro com `info-outline` | "O arquivo não tem posição, então não dá para buscar o clima." |
| `pendente` | aviso neutro com `info-outline` | "O clima deste treino ainda não chegou. Treinos recentes podem levar cerca de uma semana." |
| `falha` | aviso de alerta, `warning-amber`, `cor.alerta` sobre `cor.alerta-suave` | "Não foi possível obter o clima deste treino." |
Sem o campo `clima`, o cartão não aparece. A atribuição é obrigatória com `ok` (CC BY 4.0, [[decisoes/0007-clima-da-atividade]]).

## Entrada pela lista da evolução
Implementado no #217 (antes a tela só abria digitando a URL). Sem quebrar a seleção compartilhada do #211:
- A linha da lista continua selecionando a sessão. Quando ela está **selecionada**, aparece abaixo do detalhe do gráfico o botão de texto "Ver treino" com `chevron-right`, alvo 48.
- "Voltar" na tela do treino devolve à evolução com a sessão ainda selecionada.
- Na web larga, o mesmo botão no detalhe; o endereço `/treino/<id>` continua abrindo direto.

## Acessibilidade
- Ordem de leitura: Voltar, título, modalidade e data, duração, distância, pace, FC, clima, atribuição.
- Cada linha do clima é lida junta: "Temperatura, 24,3 °C" (um item, não dois).
- Faixa de erro com `accessibilityRole="alert"`; o esqueleto fica fora da leitura e o texto "Carregando o treino..." é anunciado.
- Alvos de toque de 44 ou mais; contraste conforme [[design/tokens]]. Ícone nunca sozinho: sempre há texto.

## Como gerar capturas sintéticas
Passo a passo em [[modulos/mobile]]: `npm run api-falsa` e `EXPO_PUBLIC_API_URL`, sem trocar config. Só dado sintético
em captura (repositório público); 390 de largura, tema claro e escuro.

## O que muda em relação ao app de hoje
| hoje | proposta | issue |
|---|---|---|
| distância em km para todos, convertida no app | API manda o texto pronto; natação em metros | #216 |
| carregando com spinner | esqueleto dos cartões | #219 |
| erro só em faixa | ícone de 40, `alert` e "Tentar de novo" na rede | #219 |
| rótulo e valor do clima lidos separados | um item por linha | #219 |
| (feito no #217) tela só abre pela URL | botão "Ver treino" na evolução e volta com a seleção | #217 |
| capturas antigas repetem a modalidade no título | regerar com o título "Treino" | #219 |
