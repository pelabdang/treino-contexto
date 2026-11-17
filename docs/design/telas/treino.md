---
tipo: design
status: rascunho
dono: lia
atualizado: 2026-11-17
links: [[design/guia-visual]], [[design/tokens]], [[design/telas/evolucao-tiros]], [[design/telas/checkin]], [[design/telas/feedback]], [[modulos/mobile]], [[decisoes/0004-contrato-tela-evolucao]], [[decisoes/0007-clima-da-atividade]], [[decisoes/0008-deteccao-de-esforcos]], [[decisoes/0009-treino-de-transicao]], [[decisoes/0010-carga-de-treino]], [[decisoes/0011-linha-de-base-e-semana-padrao]], [[metricas/linha-base]], [[metricas/serie-carga]], [[metricas/transicao]], [[produto/roadmap]]
---
# Tela: um treino, com o clima e (Meta 12) o treino inteiro

Spec escrita depois da implementação (`TelaTreino`, rota `/treino/<atividade_id>`, #159, PR #215). Fixa o que
foi aprovado e o que muda. Todos os números são **sintéticos**.

## Objetivo
O atleta (ou o professor) abre um treino e vê, de uma vez, quanto durou, a distância, o pace e a FC, e em que
condição de tempo foi feito. Responde: "como foi esse dia?".

## Dados
`GET /atletas/{id}/atividades/{id}`, pelo cliente (`buscarAtividade`). Campos: `modalidade`, `data_local`,
`hora_local`, `duracao`, `distancia_m`, `pace_medio`, `fc_media` e `clima`. O app só mostra o que a API manda
([[decisoes/0004-contrato-tela-evolucao]], Adendo 2): não calcula nem reformata pace e duração.
A API manda a distância como texto pronto (`distancia`, #216, adendo 3 da [[decisoes/0004-contrato-tela-evolucao]]) e o app a mostra como veio, sem converter (#233).

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

Meta 8 (#299): entre o cartão dos dados e o "Clima" entram os cartões **"Check-in"** e **"Carga pela PSE"**, especificados em
[[design/telas/checkin]] ("Cartões na tela do treino"), com a regra de quando aparecem pelo `checkin_aberto`.

Meta 9 (#329, #330): logo abaixo do "Check-in" entra o cartão **"Feedback"**, especificado em [[design/telas/feedback]].

## Distância
- Corrida e ciclismo: km com duas casas e vírgula ("10,00 km").
- **Natação: metros**, com separador de milhar ("1.800 m"). Piscina e águas abertas se medem em metros.
- Quem formata é a API (#216, feito); a regra acima foi o pedido de design para ela. Sem distância, a linha some.

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

## Meta 12: o treino inteiro na tela (#463)
Spec escrita **antes** das telas #465, #466, #467 e #237. Decisões do Angelo de 17/11 ([[produto/roadmap]], Meta 12): carga e
forma do dia **em números, sem gráfico, como estimativa**; rótulo de transição **corrigível pelo atleta**; seção "comparado com o
seu normal" pela `linha_base@3` (#462). Todos os números abaixo são **sintéticos**. Esboço do tema claro, em 360 de largura:
![[design/telas/treino/meta-12-claro.svg]]
(arquivo `docs/design/telas/treino/meta-12-claro.svg`). O tema escuro usa a coluna "escuro" de [[design/tokens]]; nenhuma cor nova.

### Ordem dos cartões
1. Dados do treino (duração, distância, pace, FC; ver "Distância e pace com a mesma aparência").
2. Check-in e Carga pela PSE (inalterados, [[design/telas/checkin]]).
3. Feedback (inalterado, [[design/telas/feedback]]).
4. **Esforços** (novo).
5. **Comparado com o seu normal** (novo).
6. **Carga e forma do dia** (novo).
7. **Treino de transição** (novo, curto).
8. Clima (inalterado).

Por quê: quem abre o treino acabou de treinar e a primeira coisa a resolver é o check-in; por isso ele **não desce** (uma lista longa
de tiros na frente empurraria o botão para fora da tela). O feedback resume tudo em texto; os cartões 4 a 6 são o detalhe que o
sustenta: o que o atleta **fez** (esforços), como isso **se compara** (normal) e o que **custou** (carga). A transição fica
perto do fim: é uma correção rara, não leitura. O clima continua por último, como já é.

Computador (a partir de 600): a mesma coluna, até 720, margem 24 (como as outras telas). Nada de duas colunas: a ordem de leitura
é a mesma do celular. Cada cartão novo é um grupo único para o leitor de tela, com o título como `accessibilityRole="header"`.

### Regras dos quatro cartões
- **O app não calcula.** Só mostra textos e números do `GET` ([[decisoes/0004-contrato-tela-evolucao]], adendo 2). O que a tela
  precisa e a API ainda não manda está em "Campos que a tela precisa", para a #464.
- **Cada cartão vem do próprio campo do `GET`.** Campo ausente ou `null` = cartão **não aparece** (nunca um cartão vazio).
- **Palavras sem alarme nem diagnóstico.** Proibidos: "alerta", "risco", "perigo", "excesso", "queda", "melhorou", "piorou",
  "bom", "ruim", "ideal" e "descansado" ou "cansado" como veredito. Nenhum cartão usa `cor.erro` ou `cor.alerta` para dizer que
  algo está "fora": o que difere do normal é **informação**, não aviso. `cor.alerta` só aparece onde já aparece (falha de clima).
- **Cor nunca é a única informação**: cada estado tem ícone **e** palavra.

### Cartão "Esforços"
Responde: "o que eu fiz de forte neste treino?". Vem do objeto `esforcos` ([[decisoes/0008-deteccao-de-esforcos]]).

```
┌ Esforços ────────────────────────┐   fonte.titulo-secao
│ Aquecimento 0:12:10              │   fonte.rotulo, cor.texto-2
│ Esforço      Pace      FC        │   cabeçalho: fonte.rotulo, cor.texto-2
│              min/km    bpm       │
│ 1 · 1 km     4:05      172       │   linhas de 44; fonte.corpo-forte, tabulares
│ 2 · 1 km     4:03      175       │
│ 3 · 1 km     4:06      176       │
│ Desaquecimento 0:08:40           │   fonte.rotulo, cor.texto-2
└──────────────────────────────────┘
```
- **Uma linha por esforço**, na ordem (`ordem`). Primeira coluna: o número do esforço e o `faixa_rotulo` ("400 m", "4 min"); se a
  faixa for `null`, a `distancia` pronta; sem distância, a `duracao`. Segunda: `pace` (`m:ss`; a unidade fica no cabeçalho, uma
  vez). Terceira: `fc_media`, **como a API manda** (o app não arredonda). Valor `null` vira "sem dado" em `cor.texto-2`.
- **Ciclismo e natação:** a coluna "Pace" vira "Velocidade" (km/h, campo `velocidade`) no ciclismo; na natação, sem pace, a coluna
  some e ficam distância e FC. Quem decide é a presença de `pace` ou `velocidade` na resposta, não a modalidade.
- **Aquecimento e desaquecimento:** uma linha de texto cada, com a `duracao`. As recuperações entre esforços não têm linha; a
  pausa aparece em `parada_apos` dentro da linha do esforço, quando existir ("pausa 1:00", `fonte.legenda`).
- **Mais de 8 esforços:** mostra os 8 primeiros e o botão de texto "Ver todos os 12 esforços" (48 de alto, `expand-more`). Aberto,
  vira "Ver menos". Não é uma tela nova.
- **`referencia_da_atividade = true`:** aviso `info-outline` em linha: "Sem treinos anteriores parecidos: os esforços foram
  detectados só com este treino." (texto fixo do app; a regra está na ADR 0008).
- **`treino_chave`:** sem selo nem destaque (é conceito interno).

| estado | o que aparece | texto |
|---|---|---|
| `esforcos` ausente ou `null` | cartão não aparece | |
| `blocos` só com `leve` (rodagem) | cartão não aparece | |
| `blocos` sem nenhum `esforco`, mas com outras categorias | aviso neutro `info-outline` | "Nenhum esforço detectado neste treino." |
| com esforços | a tabela acima | |

A **faixa do treino** ([[design/guia-visual]]) fica **fora desta meta**: a lista em texto já é a leitura principal e a alternativa
em texto da faixa. Ela pode entrar depois sem mudar o cartão.

### Cartão "Comparado com o seu normal"
Responde: "este treino foi diferente do que eu costumo fazer?". Vem de `linha_base` (`linha_base@3`, [[metricas/linha-base]]).
É sempre **comparação com o histórico do próprio atleta, nunca julgamento**.

```
┌ Comparado com o seu normal ──────┐
│ FC média                         │   fonte.rotulo, cor.texto-2
│ 148 bpm   (adjust) Dentro do     │   valor: corpo-forte; estado: ícone + palavra
│           seu normal             │
│ Mediana de 150 bpm, em 12        │   texto da API, fonte.corpo, cor.texto-2
│ treinos.                         │
│ ──────────────────────────────── │
│ Carga por hora                   │
│ 61,0 pontos/h (unfold-more)     │
│           Fora do seu normal     │
│ 9,0 pontos/h maior que a         │
│ mediana de 52,0 pontos/h...      │
│ ──────────────────────────────── │
│ Compara com o seu histórico no   │   fonte.legenda (fixo)
│ mesmo tipo de treino. Não diz se │
│ o treino foi bom ou ruim.        │
└──────────────────────────────────┘
```
- **Uma linha por métrica** de `linha_base.metricas`, na ordem da API: rótulo (`rotulo`), valor, **estado com ícone e palavra** e o
  `texto` da API logo abaixo, em `cor.texto-2`. O app não monta frase: o `texto` pronto é a explicação (traz mediana, diferença e
  número de treinos).
- **Estados da métrica** (`metricas[].estado`; a palavra de cada um é fixa no app):

| estado | ícone | palavra | tom |
|---|---|---|---|
| `dentro` | `adjust` | "Dentro do seu normal" | `cor.texto-2` |
| `fora` | `unfold-more` | "Fora do seu normal" | `cor.texto`, chip em `cor.superficie-2`; **sem** `cor.alerta` nem `cor.erro` |
| `aprendendo` | `hourglass-empty` | "Aprendendo o seu normal" | `cor.texto-2` |
| `sem_valor` | `info-outline` | "Sem dado neste treino" | `cor.texto-2` |

  Por que `fora` não é vermelho nem âmbar: fora do normal não é problema (um teste, um dia de prova, uma rodagem mais forte). O
  chip mais firme chama o olho sem acusar. `unfold-more` (duas setas opostas) não diz se sobe ou desce: a direção está nas palavras
  do `texto` ("mais rápido", "acima"). `check` fica de fora de propósito, porque diria "certo".
- **Valor** (`valor_texto`, a pedir à API): "148 bpm", "4:05 min/km", "61,0 pontos/h". Sem `valor_texto` (`aprendendo`,
  `sem_valor`), a linha mostra só o estado e o `texto`.
- **`aprendendo`:** o `texto` da API diz quantos treinos faltam ("5 de 8 treinos nas últimas 12 semanas"). Mesmo com todas as
  métricas em `aprendendo` ou `sem_valor`, o cartão mostra uma linha por métrica (sem juntar), para o atleta ver o que cada uma precisa.
- **Palavra "normal":** é a do projeto (ADR 0011). Nunca "ótimo", "regular" ou "dentro da meta".

| estado do cartão (`linha_base.estado`) | o que aparece | texto |
|---|---|---|
| ausente ou `null` | cartão não aparece | |
| `ok` | uma linha por métrica e a nota fixa | "Compara com o seu histórico no mesmo tipo de treino. Não diz se o treino foi bom ou ruim." |
| `sem_linha_base`, motivo `sem_tipo`, `divergente` ou `modalidade_sem_metricas` | aviso neutro `info-outline` com o `texto` da API | "Sem linha de base: o treino não tem tipo." |
| `sem_linha_base`, motivo `multiesporte` | cartão **não aparece** (é o treino inteiro ou a troca; o texto não ajuda o atleta) | |

Quando o atleta corrige o rótulo de transição, a linha de base muda de grupo (`linha_base@2`: transição compara só com transição).
Depois da correção a tela busca o treino de novo e este cartão passa pelo esqueleto antes de mostrar o novo resultado.

### Cartão "Carga e forma do dia"
Responde: "quanto este treino pesou e como estou hoje?". Dois blocos: a **carga do treino** (`carga`, `carga@2`) e a **forma do
dia** (CTL, ATL e TSB, `serie_carga@1`). **Só números.** Nada de gráfico, barra, medidor, cor por faixa ou seta de tendência.
Tudo como **estimativa**, dito no cartão (chip no alto e nota no fim).

```
┌ Carga e forma do dia ────────────┐
│ (estimativa)                     │   chip: fonte.rotulo, cor.superficie-2
│ Carga deste treino               │   fonte.rotulo, cor.texto-2
│ 87,4 pontos                      │   fonte.numero-destaque + unidade em fonte.rotulo
│ Estimada pela FC.                │   fonte.corpo, cor.texto-2
│ ──────────────────────────────── │
│ No fim do dia 18/03/25           │   fonte.rotulo, cor.texto-2
│ Condicionamento (CTL)       41,2 │   linhas de 44; corpo e corpo-forte
│ Fadiga (ATL)                52,8 │
│ Forma (TSB)                −11,6 │
│ ──────────────────────────────── │
│ Estimativas a partir dos seus    │   fonte.legenda
│ treinos. Não são medidas e não   │
│ são diagnóstico.                 │
└──────────────────────────────────┘
```
- **Carga do treino:** número em `fonte.numero-destaque` e a unidade "pontos" em `fonte.rotulo` ao lado (regra do guia: número
  grande, unidade pequena). Abaixo, uma frase com o método ("Estimada pelo pace." para `rtss`, "Estimada pela FC." para `hrtss`).
  **Não é a "Carga pela PSE"** (UA): os dois cartões convivem e a nota fixa do cartão da PSE já diz que são escalas diferentes. Aqui a
  unidade é sempre "pontos", para não misturar.
- **Forma do dia:** três linhas de 44, nesta ordem: Condicionamento (CTL), Fadiga (ATL), Forma (TSB). A palavra vem primeiro e a
  sigla vai entre parênteses, para quem a conhece. O valor é o do **fim do dia local do treino** (glossário: o TSB aqui é CTL menos
  ATL do mesmo dia), por isso o rótulo "No fim do dia dd/mm/aa".
- **Explicação sob demanda:** cada linha é um botão (alvo 44) que abre uma nota curta no próprio cartão (`expand-more`), com a
  definição do glossário: "Condicionamento: média da sua carga nos últimos 42 dias." "Fadiga: média da sua carga nos últimos 7
  dias." "Forma: condicionamento menos fadiga; negativa quer dizer que a carga recente está acima da média de 42 dias." Texto fixo
  do app, sem adjetivo de valor.
- **Sinal do TSB:** sempre explícito: "−11,6" (sinal de menos U+2212) e "+3,2". Zero é "0,0". Sem cor por sinal: negativo não é erro.
- **Arredondamento:** 1 casa, com vírgula, para carga, CTL, ATL e TSB (proposta do Caio e do Theo na #142). **Quem arredonda é a
  API** (texto pronto): o app não formata (decidido pelo Theo em 17/11).
- **Dia com treino sem carga:** se o dia tem treino sem carga (`sem_carga > 0` na série), uma linha `info-outline` abaixo das três:
  "Há 1 treino deste dia sem carga calculada; a forma pode estar subestimada." (texto pronto da API; evita um número limpo demais
  sobre dado incompleto).

| estado | o que aparece | texto |
|---|---|---|
| `carga` e `forma_do_dia` ausentes | cartão não aparece | |
| carga `calculada` e forma `calculada` | carga, três linhas e nota fixa | |
| forma `aprendendo` (menos de 42 dias de histórico) | a carga do treino e, no lugar das três linhas, um aviso `hourglass-empty`; **não mostra CTL, ATL nem TSB** | "Ainda aprendendo a sua forma: faltam 23 dias de histórico para estimar." (texto da API) |
| carga `sem_carga` | no lugar do número, aviso `info-outline` com o texto do motivo (tabela abaixo); a forma continua se a série cobrir o dia | |
| carga `pendente` | aviso `info-outline` | "A carga deste treino ainda não foi calculada." |
| forma `sem_serie` (nenhum dia com carga até aqui) | só a carga, se houver; sem as três linhas e sem aviso | |
| carregando | esqueleto: um bloco grande e três linhas | |

Por que **não** mostrar CTL, ATL e TSB enquanto "aprendendo": nas primeiras semanas o condicionamento sai baixo por construção
(a série parte de zero) e o TSB sai muito negativo sem que o atleta tenha feito algo demais. Mostrar "−28,0" a quem acabou de
chegar é um falso alarme, o oposto do tom da meta. Esconder (**decidido: Angelo, 17/11**, pergunta A).

Textos dos motivos de `sem_carga` (a API manda pronto; esta é a redação pedida): frases curtas, sem culpar.
| `motivo` | texto |
|---|---|
| `sem_dados_saude` | "Sem a FC de repouso e a máxima no seu perfil, não dá para estimar a carga deste treino." |
| `sem_limiar_na_data` | "Sem o limiar cadastrado para esta data, não dá para estimar a carga." |
| `sem_fc` | "Este treino não tem frequência cardíaca, então não dá para estimar a carga pela FC." |
| `sem_pace` | "Este treino não tem pace, então não dá para estimar a carga pelo pace." |
| `cobertura_insuficiente` | "A frequência cardíaca cobre pouco do treino, então a carga não foi estimada." |
| `modalidade_sem_carga` | "Este tipo de treino não tem carga estimada." |

### Cartão "Treino de transição" e a correção pelo atleta
Responde: "o app entendeu direito que isto foi um treino de transição (brick)?". Vem de `transicao` (`valor` e `origem`,
[[decisoes/0009-treino-de-transicao]]). A correção usa as rotas que já existem: `PUT .../transicao` com `{ "transicao": true }` ou
`false` (`corrigirTransicao`) e `DELETE .../transicao` (`desfazerCorrecaoDeTransicao`). **A correção do atleta vence a sugestão**
(decisão de 06/11).

```
┌ Treino de transição ─────────────┐
│ (swap-horiz) Este treino faz     │
│ parte de um treino de transição. │   fonte.corpo
│ O app sugeriu isso porque outro  │   fonte.corpo, cor.texto-2
│ treino começou logo depois.      │
│ [      Não é transição      ]    │   secundário, 48
│ Isso muda com quais treinos este │   fonte.legenda
│ é comparado.                     │
└──────────────────────────────────┘
```
| `valor` | `origem` | o que o cartão diz | botão | botão de texto |
|---|---|---|---|---|
| `true` | `sugerido` | "Este treino faz parte de um treino de transição. O app sugeriu isso porque outro treino começou logo depois." | "Não é transição" (PUT `false`) | |
| `true` | `atleta` | "Este treino faz parte de um treino de transição. Você marcou assim." | | "Voltar à sugestão do app" (DELETE) |
| `false` | `atleta` | "Você marcou que este treino não é de transição." | "Marcar como transição" (PUT `true`) | "Voltar à sugestão do app" (DELETE) |
| `false` | `null` | "Este treino não está marcado como de transição." | "Marcar como transição" (PUT `true`) | |

- "O app sugeriu isso porque outro treino começou logo depois" é texto fixo e descreve a regra `transicao@1` (modalidades
  diferentes, até 30 minutos entre uma e outra). Se a regra mudar, muda aqui.
- Em `true` com `origem = atleta` não há botão principal: o atleta já disse que sim; para voltar atrás ele usa "Voltar à sugestão
  do app". Em `true` com `sugerido` não há "Voltar": ainda não corrigiu nada.
- **Sem diálogo de confirmação**: a ação se desfaz com um toque, sem perda. Depois do toque, o botão mostra "Salvando..." e fica
  desligado; ao receber o `200`, o app **busca o treino de novo** (o normal, a carga e o feedback podem mudar) e o cartão mostra o
  novo estado. Anúncio para leitor de tela (`accessibilityLiveRegion="polite"`): "Marcado como treino de transição.", "Marcado como
  não sendo treino de transição." ou "Voltou à sugestão do app."
- **Erros:** de rede, texto `cor.erro` com `error-outline` abaixo do botão: "Não foi possível salvar. Tente de novo." O estado
  anterior fica e o botão volta a ficar ativo. `404`: "Treino não encontrado." `422`: o mesmo texto genérico.
- **Quem vê:** a decisão de 17/11 é que o atleta corrige e o professor continua vendo o tipo pela caixa. A tela é a mesma para os
  dois e, **antes do login, o app não sabe quem está olhando**; sem login, o cartão aparece a quem abrir a tela (**decidido: Angelo, 17/11**, pergunta B; com o login, na Meta 13, só o atleta dono corrige).
- **Quando o cartão não aparece:** quando `transicao.editavel = false`. **A API decide** (decisão do Theo, 17/11); o app não olha a
  modalidade nem o subtipo. Hoje isso cobre `outra`, `multiesporte_pai` e `troca`, mas a regra é da API.
- Acessibilidade: o botão tem alvo 48, `accessibilityRole="button"` e rótulo completo ("Marcar este treino como treino de
  transição"). O estado atual é lido antes do botão.

### Distância e pace com a mesma aparência (#237)
**Decisão:** o tom secundário da unidade **sai das duas linhas**. Distância, pace e FC viram o **mesmo tipo de linha**: rótulo à
esquerda (`fonte.corpo`, `cor.texto-2`), valor à direita (`fonte.corpo-forte`, `cor.texto`), inteiro num tom só, alvo de 44, do
jeito que o cartão do clima já faz.

```
┌──────────────────────────────────┐
│ Duração                          │  fonte.rotulo
│ 0:52:05                          │  fonte.numero-destaque
│ Distância               10,00 km │  corpo / corpo-forte
│ Pace médio           5:12 min/km │
│ FC média                 152 bpm │
└──────────────────────────────────┘
```
Por quê: a unidade em tom secundário ajuda no número **grande** ("4:08" com "min/km" ao lado, regra do guia), onde o olho vai
primeiro ao número. Numa linha de tabela, valor e unidade se leem juntos; separar o tom pesa a leitura ao ar livre (o cinza da
unidade perde contraste ao sol), e a API já manda a distância como **texto pronto com a unidade** ("10,00 km", "1.800 m"). Pedir
valor e unidade separados mudaria o contrato (adendo da ADR 0004) por um ganho que nenhuma linha usa. Os campos ficam como estão:
`distancia` (texto pronto) e `pace_medio` (`m:ss`). **O app só acrescenta " min/km" ao pace**, como sufixo fixo no mesmo tom do
valor. "Sem FC" e "sem dado" continuam em `cor.texto-2`. Nenhuma mudança de contrato.

Se a natação passar a ter pace (por 100 m), a unidade deixa de ser fixa; aí vale a API mandar o texto do pace com a unidade
("1:45 min/100 m"). Não é desta meta.

### Campos que a tela precisa (entrada da #464)
"Hoje" é o `GET /atletas/{id}/atividades/{id}` no `main`; "decidido" é o que a tela pede e o Theo decidiu em 17/11 que a API passa a mandar (#464).

| cartão | campo | hoje | para a tela |
|---|---|---|---|
| Dados | `distancia` (texto), `pace_medio` (`m:ss`), `fc_media` | existe | nada muda (#237) |
| Esforços | `esforcos.blocos[]`: `ordem`, `categoria`, `faixa_rotulo`, `distancia`, `duracao`, `pace`, `velocidade`, `fc_media`, `parada_apos` | existe | ler; confirmar que `fc_media` e `parada_apos` saem no texto que a tela mostra |
| Esforços | `esforcos.referencia_da_atividade` | existe | ler |
| Normal | `linha_base.estado`, `motivo`, `texto` (só sem base) | existe | ler |
| Normal | `linha_base.metricas[]`: `chave`, `rotulo`, `estado`, `texto`, `diferenca_texto`, `mediana_texto`, `n`, `unidade` | existe | ler |
| Normal | **`metricas[].valor_texto`** | existe na camada de serviço, não sai no `MetricaBaseOut` | **decidido (Theo, 17/11):** expor |
| Normal | `linha_base.versao` (`linha_base@3`) | existe | a tela não usa; a QA confere |
| Carga | `carga.estado`, `carga` (número), `metodo`, `motivo` | existe, **número sem arredondar** e motivo só em código | **decidido (Theo, 17/11):** `carga.valor_texto` (1 casa, vírgula, "87,4") e `carga.texto` (redação da tabela de motivos) |
| Carga | `carga.metodo` | existe (código) | **decidido (Theo, 17/11):** `carga.metodo_texto` ("Estimada pela FC.") |
| Forma do dia | CTL, ATL e TSB do dia local do treino | só em `GET /atletas/{id}/carga`, que devolve a série inteira | **decidido (Theo, 17/11):** bloco novo `forma_do_dia` no `GET` da atividade, calculado na leitura |
| Forma do dia | `estado` (`calculada`, `aprendendo`, `sem_serie`), `data_local`, `ctl_texto`, `atl_texto`, `tsb_texto` (1 casa, sinal U+2212), `texto_aprendendo` | falta | **decidido**, idem |
| Forma do dia | `sem_carga_no_dia` (inteiro) e `texto_sem_carga` | falta | **decidido**, idem |
| Transição | `transicao.valor`, `transicao.origem` | existe | ler; recarregar o `GET` após `PUT` e `DELETE` |
| Transição | `transicao.editavel` (booleano) | falta | **decidido (Theo, 17/11):** a API manda; o app só segue |

O que **o app guarda** como texto fixo (não vem da API): as quatro palavras do estado da métrica e a nota do cartão do normal;
os títulos e a nota "Estimativas a partir dos seus treinos..." do cartão de carga; as definições de CTL, ATL e TSB (vêm do
glossário); os textos do cartão de transição por combinação de `valor` e `origem`; o aviso "Sem treinos anteriores parecidos...".

### Estados da tela inteira
Sem mudança nos estados de carregando e de erro (seção "Estados"). Como o `GET` é único, **os cartões novos aparecem juntos**, sem
um surgir depois do outro; o esqueleto da tela ganha os mesmos cartões. A QA (#469) captura, para cada cartão novo, claro e escuro,
em 390 e em 1280.

### Acessibilidade dos cartões novos
- Ordem de leitura: Esforços, Normal, Carga e forma do dia, Transição, Clima.
- Cada linha de métrica, de esforço ou de CTL, ATL e TSB é **um item**: "FC média, 148 bpm, dentro do seu normal. Mediana de 150
  bpm, em 12 treinos." / "Esforço 1, 1 km, pace 4:05 por quilômetro, FC 172 bpm." / "Forma, menos 11,6."
- O sinal de menos do TSB é lido como "menos": o `accessibilityLabel` troca o U+2212 pela palavra (leitores de tela costumam
  ignorar o símbolo).
- `fonte.legenda` (13) só em nota; o resto, de 14 para cima. Com fonte grande do sistema (até 1,5), as linhas de valor quebram em
  duas (rótulo em cima, valor embaixo) em vez de cortar.
- Alvos de 44 nas linhas que abrem explicação e 48 nos botões. Contraste: pares já em [[design/tokens]]; o chip de estado usa
  `cor.texto` sobre `cor.superficie-2` (14,08 no claro, 12,28 no escuro) e o resto `cor.texto-2` sobre `cor.superficie` (7,92 e 8,44).

### Decisões de contrato (Theo, 17/11)
Para a #464. Todas como a Lia recomendou.
1. `valor_texto` entra no `MetricaBaseOut` (linha de base).
2. A carga manda `valor_texto`, `texto` do motivo e `metodo_texto` prontos (redação dos seis motivos nesta spec).
3. Arredondamento de 1 casa com vírgula, feito pela API; o TSB com o sinal de menos U+2212.
4. `transicao.editavel` vem da API; o app não decide pela modalidade.
5. Bloco novo `forma_do_dia` no `GET` da atividade, calculado na leitura pela mesma `calcular_serie`, só para o dia local do treino,
   com textos prontos e `sem_carga_no_dia`.

### Perguntas ao Angelo (decididas em 17/11)
O Angelo respondeu **"ok para as quatro"** (A a D da Meta 12) em 17/11, todas com a recomendação. Cada cartão abaixo vale como está.
- **A. Forma do dia em "aprendendo" (decidido, Angelo 17/11).** **Esconder** CTL, ATL e TSB e mostrar só o aviso. Se ele preferir mostrar, entra o
  selo "ainda aprendendo" junto dos números.
- **B. Quem corrige a transição sem login (decidido, Angelo 17/11).** Sem login, professor e atleta veem a mesma tela. **Aceito na Meta 12**; fecha
  na Meta 13, com o login; o rótulo é reversível (DELETE).
- **C. Efeito da correção no feedback (decidido, Angelo 17/11; ainda não implementado).** Corrigir a transição muda a linha de base, que entra no pacote de fatos do feedback.
  O feedback já gerado deve ficar `desatualizado`, pelo mesmo caminho do check-in editado. **Hoje a tela não faz isso**: vira issue paralela da Meta 13 (o Paulo abre).

## O que muda em relação ao app de hoje
| hoje | proposta | issue |
|---|---|---|
| (feito no #216 e #233) distância em km para todos, convertida no app | API manda o texto pronto; natação em metros | #216 |
| carregando com spinner | esqueleto dos cartões | #219 |
| erro só em faixa | ícone de 40, `alert` e "Tentar de novo" na rede | #219 |
| rótulo e valor do clima lidos separados | um item por linha | #219 |
| (feito no #217) tela só abre pela URL | botão "Ver treino" na evolução e volta com a seleção | #217 |
| capturas antigas repetem a modalidade no título | regerar com o título "Treino" | #219 |
| (Meta 12, #463) tela só com dados, check-in, PSE, feedback e clima | cartões Esforços, Comparado com o seu normal, Carga e forma do dia e Treino de transição | #465, #466, #467 |
| (Meta 12, #237) "Distância" sem tom secundário e "Pace" com | linhas de dados com a mesma aparência, unidade no tom do valor | #237 |
| (Meta 12) CTL, ATL e TSB só na série `GET /carga` | bloco `forma_do_dia` no `GET` da atividade | #464 |
