---
tipo: design
status: rascunho
dono: lia
atualizado: 2026-11-09
links: [[design/guia-visual]], [[design/tokens]], [[design/telas/treino]], [[design/telas/semana-padrao]], [[design/telas/evolucao-tiros]], [[decisoes/0012-check-in-pos-treino]], [[decisoes/0010-carga-de-treino]], [[modulos/mobile]], [[glossario]]
---
# Tela: check-in pós-treino e lista de pendentes

Spec da issue #295, antes da implementação (#299, do Rafa). Contrato em [[decisoes/0012-check-in-pos-treino]]
(itens 2, 3, 4 e 7; a ADR está em proposta no PR #305). Os campos `checkin_aberto` e `pse_sugerida` que esta nota pediu
já estão na API (#298, PR #311, adendo 9 da ADR). As dúvidas de desenho foram respondidas pelo Theo em 09/11 (seção final).
Todos os dados são **sintéticos**. Nada em `apps/mobile/` muda nesta nota.

Esboço do tema claro, em celular pequeno (360 por 640): ![[design/telas/checkin-claro.svg]]
(arquivo `docs/design/telas/checkin-claro.svg`; mostra a pergunta 1 e a pergunta 3, cada uma **sem rolar**). O tema
escuro usa a coluna "escuro" de [[design/tokens]] com o mesmo layout. Nenhuma cor nova: os pares usados já estão na
tabela de contraste.

## Objetivo
Logo depois do treino, o atleta diz **como foi** em três toques: o esforço (PSE), a sensação e uma observação.
Com isso o app calcula a "Carga pela PSE" do treino. A tela responde: "como foi esse treino para mim?". Quem não fez
o check-in no dia acha os treinos pendentes numa lista e faz de lá.

Este é **dado de saúde** (dor, sono, estresse). O desenho trata isso: nada de rascunho guardado, nada de check-in
em captura, link ou lista ([[decisoes/0012-check-in-pos-treino]], item 5).

## Onde fica e como se chega
| rota | tela | entrada |
|---|---|---|
| `/checkin/<atividade_id>` | check-in (criar, editar) | botão "Fazer check-in" ou "Editar" no cartão "Check-in" da tela de um treino ([[design/telas/treino]]); linha da lista de pendentes |
| `/checkins-pendentes` | lista de pendentes | linha "Check-ins pendentes" na evolução dos tiros |

- **Tela do treino**: ganha o cartão "Check-in" e, com check-in feito, o cartão "Carga pela PSE" (ver "Cartões na tela
  do treino").
- **Evolução**: abaixo de "Semana-padrão", uma linha de texto com `assignment` e `chevron-right`, alvo 48:
  "Check-ins pendentes" e, se houver, "· 2" (o `total` da API). Se a busca falhar, a linha aparece sem número.
- "Voltar" usa `router.back()`. O endereço `/checkin/<id>` abre direto na web.
- Em multiesporte, cada **parte** é uma atividade com a sua tela de treino e o seu check-in. O treino inteiro
  (`multiesporte_pai`) e a troca não têm check-in.

## Dados
Pelo cliente gerado (a ser regerado na #296 e #298):
- `GET /atletas/{id}/atividades/{id}`: traz `checkin` (ou `null`), `carga_pse` (ou `null`), `checkin_aberto` (booleano) e
  `pse_sugerida` (inteiro ou `null`).
- `PUT .../checkin` com `pse`, `sensacao`, `nada_a_relatar`, `atalhos` e `texto`; `200` com o `CheckinOut`.
- `DELETE .../checkin`: `204`.
- `GET /atletas/{id}/checkins/pendentes?dias=7`: `pendentes[]` com `atividade_id`, `modalidade`, `data_local`,
  `hora_local`, `duracao` e `titulo`; mais `total` e `dias`. **Sem nenhum campo do check-in.**

| campo | valores | na tela |
|---|---|---|
| `pse` | 0 a 10 | botão numerado; âncora vem do app só como rótulo fixo da escala (tabela abaixo) |
| `pse_texto` | âncora ou o número | texto ao lado do número, mostrado como veio (sem repetir o número) |
| `sensacao`, `sensacao_texto` | 1 a 5; "muito mal" a "muito bem" | linha com ícone e texto da API |
| `atalhos[].chave`, `.texto` | `dor`, `cansaco`, `sono_ruim`, `calor`, `trabalho_estresse` | chips; o texto vem da API no resumo |
| `nada_a_relatar`, `texto` | booleano; até 500 caracteres | botão e campo |
| `carga_pse.texto`, `valor_texto`, `estado` | "270 UA", `calculada`, `sem_checkin`, `sem_duracao` | cartão "Carga pela PSE" |
| `checkin_aberto` | `true` quando dá para criar (ou já existe check-in, pois editar não tem prazo); `false` em `multiesporte_pai`, `troca` e com o prazo de criação vencido | decide se o cartão "Check-in" oferece "Fazer check-in" (ver "Cartões na tela do treino") |
| `pse_sugerida` | 0 a 10 ou `null`; numa parte de multiesporte, a PSE do check-in da parte anterior | aviso "Na parte anterior você marcou N (âncora)." e botão "Usar N" na pergunta 1 |
| `pendentes[].titulo`, `data_local`, `hora_local` | texto pronto | linha da lista |

O app não calcula carga, não escolhe âncora de PSE fora da escala fixa da ADR e não decide quem é pendente nem se o prazo
está aberto (`checkin_aberto` vem pronto). Só a data curta `dd/mm/aa` é convertida, como nas outras telas.

### Escala da PSE (CR-10) e da sensação
Os rótulos dos botões são os da ADR 0012 (item 2), conferidos nas fontes pelo Caio. Se uma âncora mudar na ADR, muda aqui.
| PSE | rótulo no botão | PSE | rótulo no botão |
|---|---|---|---|
| 0 | repouso | 6 | (só o número) |
| 1 | muito leve | 7 | muito difícil |
| 2 | leve | 8 | (só o número) |
| 3 | moderado | 9 | (só o número) |
| 4 | um pouco difícil | 10 | máximo |
| 5 | difícil | | |

Sensação: 1 "Muito mal", 2 "Mal", 3 "Normal", 4 "Bem", 5 "Muito bem".

## Hierarquia da informação
**Check-in (uma pergunta por vez):**
1. A pergunta atual, grande, e "Pergunta N de 3".
2. As opções, todas visíveis sem rolar em 360 por 640.
3. O treino a que o check-in se refere (modalidade, duração e data), em linha pequena no alto.

**Tela do treino:** o check-in (feito ou por fazer) vem **depois** dos dados do treino e antes do clima; a carga pela PSE
fica logo abaixo do check-in.

**Pendentes:** o treino mais recente no alto, com o que o treino foi (modalidade, tempo, data) e a ação (fazer check-in).

## Os 3 toques
| toque | pergunta | o que acontece |
|---|---|---|
| 1 | "Qual foi o esforço do treino?" | tocar um número escolhe e **vai para a pergunta 2** |
| 2 | "Como você se sentiu no treino?" | tocar uma opção escolhe e **vai para a pergunta 3** |
| 3 | "Quer registrar mais alguma coisa?" | tocar **"Nada a relatar" salva na hora**; ou marcar atalhos e/ou digitar e tocar "Salvar check-in" |

- O caminho mais curto (nada a relatar) é de **3 toques e nenhum "Próximo" nem "Salvar"**.
- Com atalho ou texto, o terceiro toque é o atalho e o "Salvar check-in" é um toque a mais (marcar vários atalhos
  e digitar não pode salvar sozinho). O texto livre nunca conta como toque ([[decisoes/0012-check-in-pos-treino]], item 2).
- O `PUT` sai **uma vez**, no fim, com as três respostas. Nada é enviado antes.
- Voltar de uma pergunta para a anterior: "Voltar" no alto (volta à pergunta, não sai da tela) e o gesto de voltar do sistema.
  As respostas já dadas ficam marcadas. Sair da tela de verdade: "Voltar" na pergunta 1.

## Layout do check-in (celular de 360 por 640, margem 16)

### Pergunta 1: PSE
```
┌──────────────────────────────────┐
│ ← Voltar                         │  botão de texto, alvo 44
│ Check-in do treino               │  fonte.titulo-tela
│ (🏃) Corrida, 45 min · 09/11/25  │  chip + fonte.rotulo, cor.texto-2
│ Pergunta 1 de 3  ▬▬ ▭▭ ▭▭        │  texto + 3 segmentos (o texto é quem informa)
│ Qual foi o esforço do treino?    │  fonte.titulo-secao
│ 0 é repouso e 10 é o máximo...   │  fonte.legenda
│ ┌────────────┐ ┌────────────┐    │  grade de 2 colunas, botões de 52
│ │0 repouso   │ │6           │    │  coluna da esquerda: 0 a 5
│ │1 muito leve│ │7 muito difí│    │  coluna da direita: 6 a 10
│ │2 leve      │ │8           │    │
│ │3 moderado  │ │9           │    │
│ │4 um pouco d│ │10 máximo   │    │
│ │5 difícil  ✓│ │            │    │
│ └────────────┘ └────────────┘    │
│ A PSE é só sua: não se compara...│  fonte.legenda
└──────────────────────────────────┘
```
- Botão: número em `fonte.titulo-secao` (18, 700) e, ao lado, a âncora em `fonte.rotulo` (14); altura 52, `raio.medio`,
  contorno de 1 em `cor.borda-forte`. Escolhido: fundo `cor.destaque-suave`, contorno de 2 em `cor.destaque` e `check`.
  Sem cor de "gravidade": a escala é a mesma cor, para o número não parecer "bom" ou "ruim".
- "um pouco difícil" e "muito difícil" podem quebrar em duas linhas a 160 de largura: o botão cresce, sem cortar.
- Lido de cima para baixo na coluna da esquerda e depois na da direita (0 a 10 em ordem para o leitor de tela).
- Em 320 de largura ou com fonte grande, a grade vira **uma coluna** de botões de 48 e a tela rola (cabe em 3 telas de rolagem).

### Pergunta 2: sensação
```
│ Pergunta 2 de 3  ▬▬ ▬▬ ▭▭
│ Como você se sentiu no treino?
│ ┌──────────────────────────────┐
│ │ (☹☹) Muito mal            ✓ │  ícone + texto, linhas de 56
│ │ (☹)  Mal                     │
│ │ (😐) Normal                  │
│ │ (☺)  Bem                     │
│ │ (☺☺) Muito bem               │
│ └──────────────────────────────┘
```
- Cinco linhas de 56 (`lista.linha-altura`), ícones `sentiment-very-dissatisfied`, `sentiment-dissatisfied`,
  `sentiment-neutral`, `sentiment-satisfied`, `sentiment-very-satisfied`, todos em `cor.texto-2` (nunca vermelho a
  verde). O texto diz o que o ícone diz. Escolhido: fundo `cor.destaque-suave`, contorno 2 e `check`.
- Ordem de cima para baixo: do pior ao melhor, como a escala (1 a 5).

### Pergunta 3: observação
```
│ Pergunta 3 de 3  ▬▬ ▬▬ ▬▬
│ Quer registrar mais alguma coisa?
│ Toque no que combina. Pode marcar mais de um.
│ [Dor] [✓ Cansaço] [Sono ruim]
│ [Calor] [✓ Trabalho ou estresse]
│ Quer acrescentar algo? (opcional)
│ ┌──────────────────────────────┐
│ │ Semana puxada no trabalho.   │  campo de texto, 3 linhas
│ └──────────────────────────────┘
│                        26 de 500   fonte.legenda
│ [        Salvar check-in       ]   primário, 48
│ [        Nada a relatar        ]   secundário, 48
│ "Nada a relatar" salva na hora.
```
- **Atalhos** (chips tocáveis, altura 48, vários ao mesmo tempo): "Dor", "Cansaço", "Sono ruim", "Calor", "Trabalho ou
  estresse". Marcado: fundo `cor.destaque-suave`, contorno 2 e `check` (nunca só cor). Desmarcado: contorno 1 em `cor.borda-forte`.
- **Texto livre**: campo multilinha de 3 linhas, `maxLength` 500, rótulo "Quer acrescentar algo? (opcional)", contador
  "N de 500" em `fonte.legenda`. Sem preenchimento automático (`autoComplete="off"` na web). Acima de 450, o contador passa a `cor.alerta` com ícone `warning-amber`.
- **"Salvar check-in"** (primário, único primário): desligado até haver **um atalho ou texto**; o motivo vem em texto:
  "Marque um atalho, escreva algo ou toque em Nada a relatar."
- **"Nada a relatar"** (secundário): salva na hora com `nada_a_relatar: true`, sem atalhos e sem texto. Se houver
  atalho marcado ou texto escrito, o toque abre o diálogo "Descartar o que você marcou?" ("Nada a relatar apaga os
  atalhos e o texto desta pergunta." botões "Cancelar" e "Nada a relatar"), para não apagar texto sem querer.
- Teclado aberto: o campo e os botões sobem com o teclado (o botão "Salvar check-in" fica visível).

### Editar um check-in existente
Mesma rota. Em vez do passo a passo, **uma só tela** com os três blocos juntos (já preenchidos), porque quem edita sabe o
que quer mudar:
```
│ ← Voltar
│ Editar check-in
│ (🏃) Corrida, 45 min · 09/11/25
│ ┌ Esforço (PSE) ────────────────┐
│ │ 5 · difícil          [Mudar] │   toca em Mudar: abre a grade de PSE na própria tela
│ └───────────────────────────────┘
│ ┌ Sensação ─────────────────────┐
│ │ (☺) Bem              [Mudar]  │
│ └───────────────────────────────┘
│ ┌ Observação ───────────────────┐
│ │ [✓ Cansaço] [✓ Trabalho ou e…]│
│ │ campo de texto                │
│ │ ( ) Nada a relatar            │   opção que limpa atalhos e texto
│ └───────────────────────────────┘
│ [          Salvar alterações     ]   primário, desligado até mudar
│ [          Apagar check-in       ]   texto, cor.erro, alvo 48
```
- "Mudar" abre a mesma folha de opções (PSE em grade, sensação em lista) com o valor atual marcado; tocar escolhe e
  fecha. O resumo do bloco mostra o novo valor.
- "Nada a relatar" é uma opção marcável (rádio com ícone), **não** salva sozinha aqui. Marcar limpa atalhos e texto
  (com o diálogo de descarte se houver conteúdo); marcar um atalho ou digitar desmarca "Nada a relatar".
- Editar não tem prazo. O `PUT` substitui o registro inteiro.

### Sugerir a PSE da parte anterior (multiesporte)
Na **pergunta 1**, se o `GET` da atividade trouxer `pse_sugerida` (inteiro, a PSE do check-in da parte anterior do mesmo
multiesporte), aparece acima da grade um aviso neutro com `info-outline`: **"Na parte anterior você marcou 5 (difícil)."** e o
botão de texto **"Usar 5"**. O botão tem o mesmo efeito de tocar o 5 (escolhe e vai para a pergunta 2). A grade continua toda
tocável; a sugestão **não vem marcada**, para não virar resposta sem o atleta ver. Com `null`, nada aparece.
- A API manda **só o número**: o app não recebe a modalidade da parte anterior, por isso o aviso não a cita. A âncora entre
  parênteses vem da tabela fixa da escala (acima), a mesma dos botões. Para 6, 8 e 9, que não têm âncora, o aviso é só
  "Na parte anterior você marcou 6.".
- Leitor de tela: o aviso é lido antes da grade, e o botão como "Usar 5, botão".

## Cartões na tela do treino ([[design/telas/treino]])
**Sem check-in.**
```
┌ Check-in ────────────────────────┐
│ (assignment) Você ainda não fez  │
│ o check-in deste treino.         │
│ Sem check-in: a carga pela PSE   │  texto da API (carga_pse.texto, estado sem_checkin)
│ precisa da PSE do treino.        │
│ [        Fazer check-in        ] │  primário, 48
└──────────────────────────────────┘
```
**Com check-in.**
```
┌ Check-in ────────────────────────┐
│ Esforço (PSE)        5 · difícil │  linhas de 44
│ Sensação                     Bem │
│ Observação  Cansaço, Trabalho ou │
│             estresse             │
│ Semana puxada no trabalho.       │  texto livre, se houver
│ [ Editar ]  [ Apagar check-in ]  │  secundário e texto cor.erro, 48
└──────────────────────────────────┘
┌ Carga pela PSE ──────────────────┐
│ 270 UA                           │  fonte.numero-destaque (valor_texto)
│ Carga pela PSE: 6 x 45 min = 270 │  texto da API, fonte.corpo, cor.texto-2
│ UA.                              │
│ Não se compara com a carga do    │  fonte.legenda
│ relógio (pontos): são escalas... │
└──────────────────────────────────┘
```
- "Observação": "Nada a relatar" quando `nada_a_relatar`; senão os atalhos separados por vírgula e, abaixo, o texto livre.
- Carga pela PSE: valor em `fonte.numero-destaque` e a unidade "UA" dentro de `valor_texto`, mostrado como veio. `estado =
  sem_duracao`: só o `texto` da API (sem número). `pse = 0`: "0 UA" vale. Sem `carga_pse` (atividade sem check-in
  elegível), o cartão não aparece.
- **Quando o cartão aparece** (regra pelo `checkin_aberto` e pelo `checkin` do `GET`, decidida em 09/11):
  | `checkin` | `checkin_aberto` | cartão "Check-in" |
  |---|---|---|
  | existe | `true` (sempre, pois editar não tem prazo) | "Com check-in", com "Editar" e "Apagar check-in" |
  | `null` | `true` | "Sem check-in", com "Fazer check-in" |
  | `null` | `false` e a atividade é `multiesporte_pai` ou `troca` | **não aparece** (o treino inteiro e a troca não têm check-in; as partes têm) |
  | `null` | `false` nos demais casos (prazo de criação vencido) | "Sem check-in" **sem o botão**, com o aviso de prazo: ícone `info-outline` e "O prazo para fazer o check-in deste treino acabou (7 dias depois do treino)." |
- O app não calcula prazo: só lê `checkin_aberto`. O `422` `fora_do_prazo` e o `422` `atividade_sem_checkin` (ver Estados)
  ficam como rede de segurança, para quando a tela estava aberta e o prazo venceu no meio, ou para o endereço `/checkin/<id>`
  digitado direto na web.
- **Apagar** abre o diálogo: título "Apagar este check-in?", texto "A PSE, a sensação e a observação deste treino serão
  apagadas. Isso não pode ser desfeito.", botões "Cancelar" (primário) e "Apagar" (secundário, texto `cor.erro`).

## Lista de pendentes (`/checkins-pendentes`)
```
┌──────────────────────────────────┐
│ ← Voltar                         │
│ Check-ins pendentes              │  fonte.titulo-tela
│ Treinos dos últimos 7 dias sem   │  fonte.corpo, cor.texto-2 (usa `dias` da API)
│ check-in                         │
│ ┌──────────────────────────────┐ │  cartão com linhas tocáveis (altura 72)
│ │ (🏃) Corrida, 45 min       > │ │  chip + titulo (corpo-forte)
│ │ 09/11/25 às 07:10            │ │  fonte.corpo, cor.texto-2
│ │ ──────────────────────────── │ │
│ │ (🏊) Natação, 40 min       > │ │
│ │ 08/11/25 às 06:30            │ │
│ └──────────────────────────────┘ │
│ 2 treinos sem check-in           │  fonte.legenda (do total)
└──────────────────────────────────┘
```
- Mais recente no alto (ordem da API). Cada linha é `accessibilityRole="button"` e abre `/checkin/<atividade_id>` direto na pergunta 1.
- Linha com ícone da modalidade **e** o nome no título ("Corrida, 45 min"); a cor não é a informação.
- **Nada do check-in** aparece na lista, nem "pendente de quê". Só o treino.
- Depois de salvar na tela de check-in, o botão da tela "Salvo" é "Voltar aos pendentes", e a lista recarrega sem o treino feito.
- Web larga (a partir de 600): a mesma coluna, até 720, margem 24.

## Estados
Segue [[design/guia-visual]], "Estados". O conteúdo na tela não some quando uma nova ação começa.

### Check-in
| estado | o que aparece | texto |
|---|---|---|
| carregando (abre editando, ou carrega o treino) | esqueleto do cabeçalho e dos blocos; o texto fica para o leitor de tela | "Carregando o check-in..." |
| respondendo | a pergunta atual (1, 2 ou 3) | ver acima |
| salvando | o botão da ação vira "Salvando..." com indicador e fica desligado; opções desligadas; nada é perdido | "Salvando..." |
| salvo | ícone `check-circle-outline` de 40 em `cor.sucesso`, título, resumo curto (PSE, sensação, observação) e o botão primário | "Check-in salvo" / "Voltar ao treino" (ou "Voltar aos pendentes") |
| erro ao carregar (rede) | `wifi-off` de 40, frase e "Tentar de novo" | "Não foi possível falar com o servidor" |
| erro ao carregar `404` | `error-outline` e frase | "Treino não encontrado" (ou "Atleta não encontrado") |
| erro ao salvar (rede) | aviso de erro (`alert`) acima do botão; **as respostas ficam**; o botão volta a ligar | "Não foi possível falar com o servidor. Suas respostas continuam aqui. Tente salvar de novo." |
| erro ao salvar `422` genérico | aviso de erro; respostas ficam | "Algum dado do check-in não foi aceito. Confira as respostas e tente de novo." |
| `422` `fora_do_prazo` | tela de aviso (sem "Tentar de novo"): ícone `error-outline`, frase e botão "Voltar ao treino" | "O prazo para fazer o check-in deste treino acabou (7 dias depois do treino). Check-ins que já existem ainda podem ser editados." |
| `422` `atividade_sem_checkin` | tela de aviso e "Voltar ao treino" | "Este treino não pede check-in." |
| erro ao salvar `404` | aviso de erro | "Treino não encontrado." |
| erro ao salvar (outro) | aviso de erro; respostas ficam | "Não foi possível salvar. Tente de novo mais tarde." |
| apagando | "Apagando..." no botão; desligado | "Apagando..." |
| apagado | volta ao treino com o cartão "sem check-in"; aviso curto (live region) | "Check-in apagado." |
| erro ao apagar | aviso de erro; o check-in continua | "Não foi possível apagar. Tente de novo." |

O texto "7 dias" vem do contrato (padrão ainda a confirmar com o Angelo, A confirmar 1 da ADR). Se o prazo mudar, muda
essa frase. O app **não** mostra o texto técnico do `detail` da API (que não repete a entrada) e **não** escreve respostas em log.

### Pendentes
| estado | o que aparece | texto |
|---|---|---|
| carregando | esqueleto de três linhas | "Carregando seus treinos..." |
| vazio | `check-circle-outline` de 40 em `cor.texto-2`, título e frase; sem botão primário | "Nenhum check-in pendente" / "Você fez o check-in de todos os treinos dos últimos 7 dias." |
| lista | as linhas e o total | "2 treinos sem check-in" (1: "1 treino sem check-in") |
| erro (rede) | `wifi-off`, frase e "Tentar de novo" | "Não foi possível falar com o servidor" |
| erro (outro) | `error-outline` e frase | "Não foi possível carregar os pendentes. Tente de novo mais tarde." |

### Sair com respostas
Só pede confirmação quando já há **conteúdo sensível** digitado ou marcado na pergunta 3 (atalho ou texto) e o atleta
sai da tela: "Sair sem salvar?" / "O que você escreveu aqui será perdido." / "Continuar" e "Sair". PSE e sensação sozinhas
não pedem: são dois toques e voltam a ser feitos. **Nenhum rascunho é guardado** (nem em memória do aparelho, nem no
navegador): o check-in é dado de saúde ([[decisoes/0012-check-in-pos-treino]], item 5).

## Textos (resumo)
Perguntas: "Qual foi o esforço do treino?", "Como você se sentiu no treino?", "Quer registrar mais alguma coisa?".
Apoios: "0 é repouso e 10 é o máximo. É a sua percepção.", "A PSE é só sua: não se compara com a de outros atletas.",
"Toque no que combina. Pode marcar mais de um.", "Nada a relatar salva na hora.".
Botões: "Fazer check-in", "Editar", "Apagar check-in", "Salvar check-in", "Salvar alterações", "Nada a relatar", "Voltar".
Cartão: "Check-in", "Carga pela PSE" (UA, nunca "pontos").

## Acessibilidade
- Contraste AA em todos os pares (nenhuma cor nova); nada abaixo de 12 ([[design/tokens]]).
- Alvos: botão de PSE 52, opção de sensação 56, chip 48, botões 48, linha da lista 72. A grade de PSE tem 8 de espaço entre botões.
- Nada só pela cor: escolhido = `check` + contorno mais grosso; a sensação tem ícone **e** texto; os segmentos de progresso
  têm o texto "Pergunta N de 3"; o contador de caracteres tem ícone de alerta.
- Ordem de leitura (pergunta 1): Voltar, título, treino, "Pergunta 1 de 3", pergunta, apoio, botões 0 a 10, nota. Cada botão
  é lido como "PSE 5, difícil, botão" (e "PSE 6, botão"; escolhido: "selecionado"); a sensação: "Sensação, bem, botão".
  Os botões são um grupo de rádio (`accessibilityRole="radiogroup"` e `radio`, com `checked`).
- **Mudança de pergunta**: o app anuncia "Escolhido: PSE 5, difícil. Pergunta 2 de 3: como você se sentiu no treino?" e leva o
  foco ao título da pergunta nova. A transição não anima com "reduzir movimento" ligado.
- Atalhos: `accessibilityRole="checkbox"` e `checked`; o campo de texto tem rótulo e o contador anunciado ao passar de 450.
- Anel de foco de 2 em `cor.foco` na web; teclado: setas movem entre as opções, Enter escolhe; Esc fecha folhas e diálogos.
- Fonte grande: a grade de PSE vira uma coluna; nada é cortado; a barra de botões da pergunta 3 rola junto.
- Ao ar livre (sol): texto principal e botões em contraste alto, sem cinza claro; pergunta em 18.
- Lista: cada linha é lida como "Corrida, 45 minutos, 09/11/25 às 07:10, botão".

## Privacidade no desenho
- Nenhuma captura, esboço ou exemplo com check-in real. Os desta nota são sintéticos.
- O app não escreve respostas em log, URL, parâmetro de rota nem armazenamento local; a rota leva só o `atividade_id`.
- A lista de pendentes e a evolução não mostram PSE, sensação nem observação.
- Teste e captura do Rafa: só com a API falsa e texto marcador sintético.

## Como gerar capturas sintéticas
Como em [[modulos/mobile]] (`npm run api-falsa`): a API falsa precisa dos cinco endpoints, com atividades sintéticas
com e sem check-in, uma natação, uma fora do prazo e uma parte de multiesporte; e estados forçados pelo `EXPO_PUBLIC_ATLETA_ID`,
como na semana-padrão. Um estado por captura, 390 de largura, claro e escuro.

## O que muda em relação ao app de hoje
| hoje | proposta | issue |
|---|---|---|
| a tela do treino não fala de esforço | cartões "Check-in" e "Carga pela PSE" | #299 |
| sem rota de check-in | `/checkin/<id>` e `/checkins-pendentes` | #299 |
| evolução sem lembrete | linha "Check-ins pendentes" | #299 |
| sem ícones de sensação | cinco ícones `sentiment-*`, `assignment`, `edit` e `check` em [[design/tokens]] | #299 |

## Dúvidas de desenho
Todas respondidas pelo Theo em 09/11 (comentário no PR #309). O que decidiu já está no corpo da nota; a lista fica como registro.
1. **Quarto toque.** Com atalho ou texto o caminho é PSE, sensação, atalho, "Salvar check-in" (4 toques). Só "Nada a relatar"
   fecha em 3. Está bom, ou o Theo prefere atalho de um toque único (um atalho só, salvando na hora)? Perde o "vários atalhos".
   **Respondida (Theo, 09/11):** aceito. "Nada a relatar" fecha em 3 toques; com atalho ou texto são 4, para permitir vários
   atalhos. O Theo leva ao Angelo como informação.
2. **Treino que não pede check-in.** O app só recebe `checkin: null` e `carga_pse: null`, igual para "sem check-in" e para
   `multiesporte_pai`/`troca`. Peço um campo na #298 que diga se o treino aceita check-in (e, idealmente, se o prazo ainda está
   aberto, `checkin_aberto`), para o cartão não oferecer "Fazer check-in" onde só virá `422`. Sem isso, o app trata o `422`.
   **Respondida (Theo, 09/11):** sim. A #298 entregou `checkin_aberto` (booleano) no `GET` da atividade. Regra em "Cartões
   na tela do treino".
3. **PSE da parte anterior.** A ADR deixa para a #299. O app não sabe qual é a parte anterior. Peço à #298 um campo no `GET` da
   atividade, por exemplo `pse_sugerida: {modalidade, pse, pse_texto}`, só quando a parte anterior tem check-in. Sem esse campo,
   a sugestão não aparece.
   **Respondida (Theo, 09/11):** sim, mas como **inteiro ou `null`** (sem modalidade nem texto). O app resolve a âncora pela
   tabela fixa da escala. Texto em "Sugerir a PSE da parte anterior".
4. **Entrada na evolução.** A linha "Check-ins pendentes" busca o `total` ao abrir a evolução (uma chamada a mais). Aceitável? A
   alternativa é sem número, só o link.
   **Respondida (Theo, 09/11):** pode buscar o `total` ao abrir a evolução.
5. **"Mudar" na edição** abre a mesma folha da criação. Prefere que a edição reaproveite o passo a passo, com as respostas marcadas?
   **Respondida (Theo, 09/11):** fica a tela única com "Mudar".
6. **Prazo de 7 dias** ainda depende da resposta do Angelo (A confirmar 1 da ADR). A frase do `fora_do_prazo` está escrita com "7 dias".
   **Respondida (Theo, 09/11):** 7 dias segue como padrão até o Angelo responder. Se mudar, só o texto do `fora_do_prazo`
   (e o do aviso de prazo no cartão) muda.
