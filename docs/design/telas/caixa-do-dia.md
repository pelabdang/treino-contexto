---
tipo: design
status: rascunho
dono: lia
atualizado: 2026-11-16
links: [[design/guia-visual]], [[design/tokens]], [[design/telas/checkin]], [[design/telas/feedback]], [[design/telas/semana-padrao]], [[design/telas/treino]], [[decisoes/0015-caixa-do-dia-do-professor]], [[decisoes/0011-linha-de-base-e-semana-padrao]], [[decisoes/0012-check-in-pos-treino]], [[produto/roadmap]], [[modulos/mobile]], [[glossario]]
---
# Tela: caixa do dia do professor

Spec da issue #420 (Meta 11), antes da implementação (o Rafa, depois que a #424 entregar a API). Contrato em
[[decisoes/0015-caixa-do-dia-do-professor]] (aceita com o "ok para as 7" do Angelo) e decisões do Angelo de 16/11
em [[produto/roadmap]], "Meta 11". Todos os nomes, datas e textos são **sintéticos** (alunos fictícios, escritos à
mão). Nada em `apps/mobile/` muda nesta nota.

Esboços do estado principal, em 390 por 844: tema claro ![[design/telas/caixa-do-dia-claro.svg]] e tema escuro
![[design/telas/caixa-do-dia-escuro.svg]] (arquivos `docs/design/telas/caixa-do-dia-claro.svg` e
`caixa-do-dia-escuro.svg`). Os outros estados estão em ASCII, na seção "Estados"; o tema escuro usa a coluna
"escuro" de [[design/tokens]] com o mesmo layout. **Nenhuma cor nova**: só pares que já passam na tabela de contraste.

## Objetivo
O professor abre a tela de manhã e, em um minuto, responde duas perguntas:
1. **Quem eu devo olhar hoje, e por quê?** Os alunos ordenados por "precisa de atenção", cada motivo em **uma linha**.
2. **Quais treinos novos eu confirmo?** Os treinos com tipo sugerido (semana-padrão ou regra), que ele confirma ou
   corrige **em lote**.

A hipótese do produto é que o professor gasta menos tempo por aluno com o contexto pronto
([[produto/plano-mvp-execucao]], seção 5.1). A tela serve para **olhar e decidir rápido**, não para vigiar:

- Sem "alerta", "risco", "problema", "atenção!" nem cor de perigo. O título é "Para olhar hoje".
- O motivo diz **o quê**, nunca **por quê** (sem causa, sem conselho, sem diagnóstico, sem juízo). As frases vêm
  prontas da API ([[decisoes/0015-caixa-do-dia-do-professor]], item 4); o app só as mostra.
- A lista é uma ajuda para decidir onde olhar primeiro, não um veredito. Quem não tem motivo não "está bem": a frase é
  "Nada a destacar nos últimos 7 dias." e só isso.
- O professor fala de "alunos"; o atleta fala de "treinos meus". Aqui é sempre "aluno" e "aluna" no texto de apoio
  (os rótulos de dado seguem o da API).

Quem usa: o professor de uma assessoria, **no computador** (mais provável) e **no celular** (390 de largura).
O professor do piloto é fixo por configuração: não há login nem tela de escolha de professor.

## Onde fica e como se chega
| rota | tela | entrada |
|---|---|---|
| `/caixa-do-dia` | caixa do dia | endereço direto e página inicial quando o professor estiver configurado (o Rafa decide o redirecionamento; ver "Dados") |

- Uma tela só, com rolagem. **Sem rota de detalhe do treino:** o detalhe abre dentro da própria lista (ver "Detalhe
  do treino"). Menos telas, e a observação livre nunca vai parar em endereço, histórico ou parâmetro de rota.
- O cabeçalho tem o título, a data de hoje e o botão "Atualizar" (`refresh`). A caixa é **calculada a cada leitura**
  ([[decisoes/0015-caixa-do-dia-do-professor]], item 1): o professor toca para ver o que mudou.
- Sem "Voltar": é a tela de entrada do professor.

## Dados
Contrato do `GET /professores/{professor_id}/caixa-do-dia` (#424) e do `PUT` em lote do tipo (#425). **Este quadro é
a lista de campos que a tela precisa, para o adendo da ADR 0004 na #424.** O app **não calcula nada**: não escolhe
motivo, não ordena, não decide janela, não monta frase, não decide quem é "novo". Só a data curta `dd/mm/aa` e o nome do dia
quando precisar são formatados no app, como nas outras telas.

**Resposta do `GET`:**
| campo | valores | na tela |
|---|---|---|
| `versao` | `atencao@1` | não aparece (só em teste e em log sem dado de saúde) |
| `hoje` | data local (`America/Sao_Paulo`) | "Quinta, 13/11/25" no cabeçalho; mesma data que a API usou para as janelas |
| `janela_atencao_dias`, `janela_novos_dias` | 7 e 14 | frases de apoio das seções ("últimos 7 dias", "últimos 14 dias"): o app **não** escreve o número no código |
| `alunos[]` | ordenados pela API (item 4 da ADR); **o app não reordena** | seção "Para olhar hoje" |
| `alunos[].atleta_id`, `.nome` | inteiro; texto do cadastro fictício | nome do aluno |
| `alunos[].sem_motivo` | booleano | linha compacta "Nada a destacar nos últimos 7 dias." (a frase vem em `alunos[].texto_sem_motivo`) |
| `alunos[].treinos[]` | só os treinos **com motivo**, do mais recente ao mais antigo | linhas de treino do cartão do aluno |
| `treinos[].atividade_id`, `.modalidade`, `.data_local`, `.hora_local`, `.duracao_texto` | `corrida`, `ciclismo`, `natacao`; "45 min" pronto | linha pequena do treino (chip, duração, data) |
| `treinos[].motivos[]` | `{codigo, texto}` na ordem fixa `dor`, `fora_do_normal`, `divergencia`, `checkin_vencendo` | uma linha por motivo; `codigo` escolhe o **ícone**, `texto` é mostrado **como veio** |
| `novos[]` | treinos com tipo sugerido para confirmar (item 4 da ADR, 14 dias), **na ordem que a API der** | seção "Treinos novos" |
| `novos[].atividade_id`, `.atleta_id`, `.atleta_nome`, `.modalidade`, `.data_local`, `.hora_local`, `.duracao_texto` | como acima | linha do treino novo |
| `novos[].tipo_sugerido`, `.tipo_sugerido_texto`, `.origem_texto` | `leve`, `moderado`, `longo`, `intervalado`, `fartlek`; "Intervalado"; "sugerido pela semana-padrão" ou "sugerido pela regra" | chip do tipo e legenda de origem |
| `detalhe` (em cada treino de `alunos[].treinos[]` **e** de `novos[]`) | objeto, ver abaixo | bloco aberto ao expandir |
| `detalhe.tipo_texto`, `.tipo_origem_texto`, `.tipo_confirmado` | "Intervalado"; "sugerido pela regra"; booleano | linha "Tipo" |
| `detalhe.checkin` | `null` quando não há check-in | se `null`: linha "Sem check-in ainda." |
| `detalhe.checkin.pse_texto`, `.sensacao`, `.sensacao_texto`, `.atalhos[].chave`, `.atalhos[].texto`, `.nada_a_relatar`, `.observacao` | PSE como no check-in ("8", "5 · difícil"); 1 a 5; texto pronto; chaves da ADR 0012; booleano; texto ou `null` | linhas "Esforço", "Sensação", "Atalhos", "Observação" |
| `detalhe.feedback.estado`, `.texto`, `.mensagem` | os estados de [[design/telas/feedback]] (`pronto`, `sem_checkin`, `pendente`, `desatualizado`, `indisponivel`) | linha "Feedback", com a frase do estado como o cartão do atleta mostra |

**Corpo do `PUT` em lote** (#425): lista de `{atividade_id, tipo_treino}`, no máximo 200, todos de alunos do filtro de
vínculo e consentimento. `tipo_treino` é um dos cinco, **igual ao `tipo_sugerido`** para "confirmar sem mudar" (a API
trata como confirmação) ou diferente para "corrigir". Tudo ou nada.
Resposta que a tela quer: `{confirmados: N, corrigidos: N}`, para o anúncio do resultado não depender de o app
adivinhar o que o servidor decidiu (se a #425 não devolver, o app calcula pela comparação com `tipo_sugerido`).

**Erros que a tela trata:**
| resposta | origem | na tela |
|---|---|---|
| `404` com `type` `professor_inexistente` (**uniforme**: id sem linha, id diferente do configurado e `PROFESSOR_ID` vazio têm o mesmo corpo) | `GET` | estado de erro "Caixa do dia não encontrada" (ver "Estados"). O app **não** tenta dizer qual foi a causa, porque a API também não diz |
| `404` `atividade_nao_encontrada` | `PUT` | lote inteiro não salvo; texto abaixo |
| `422` `atividade_sem_tipo` | `PUT` | lote inteiro não salvo |
| `422` de validação (tipo fora dos cinco, lote vazio, id repetido, mais de 200) | `PUT` | **não deve acontecer** se a tela cumprir as regras; se vier, aviso genérico |
| rede, `5xx` | os dois | estados de erro |

**O app não faz:** guardar nome, PSE, sensação, atalho, observação ou feedback em armazenamento local, URL, parâmetro
de rota, log ou mensagem de erro. A observação livre só existe na memória da tela e some quando ela é fechada
([[decisoes/0015-caixa-do-dia-do-professor]], item 7).

**Professor configurado:** o app lê o `professor_id` de uma variável de ambiente pública do Expo (como o atleta fixo
da Meta 2, por exemplo `EXPO_PUBLIC_PROFESSOR_ID`; o nome fica com o Rafa). Sem a variável, a tela mostra o estado
"Caixa do dia não encontrada" **sem chamar a API**, com o mesmo texto do `404`.

## Hierarquia da informação
**Tela inteira, de cima para baixo:**
1. Título "Caixa do dia" e a data de hoje (de onde estamos olhando).
2. **Resumo em uma linha**: "2 alunos para olhar · 4 treinos novos". Responde "tenho trabalho hoje?" antes de rolar.
3. **"Para olhar hoje"**: os alunos na ordem da API, cada um com o nome e o motivo em uma linha.
4. **"Treinos novos"**: o tipo sugerido, a seleção e a barra de ação do lote.

**Dentro do cartão de um aluno** (o que se lê primeiro, nesta ordem):
1. O **nome** do aluno (`fonte.titulo-secao`).
2. A linha pequena do treino: modalidade, duração e data (`fonte.rotulo`, `cor.texto-2`).
3. O **motivo**: uma linha de texto por motivo, com ícone (`fonte.corpo`, `cor.texto`). É o que o professor veio ler.
4. A seta de expandir. O resto (tipo, esforço, sensação, atalhos, feedback e observação) fica **fechado**.

**O que o professor vê de cada treino (decisão 7), e onde:**
| dado | na lista (fechado) | ao abrir o treino |
|---|---|---|
| motivo (uma linha por motivo) | sim | sim (repetido como título do bloco) |
| tipo e de onde veio | só nos **treinos novos** (chip) | sim |
| PSE e sensação | não | sim |
| atalhos (dor, cansaço, sono ruim, calor, trabalho ou estresse) | **não**, só o motivo "dor" aparece como frase | sim |
| feedback | não | sim |
| observação livre | **nunca** | sim, e só ali |

Por que assim: a lista serve para decidir onde olhar e precisa caber em poucas telas; o dado de saúde (PSE,
sensação, atalho, observação) fica atrás de um toque, **uma exposição intencional por treino**, e não numa tela
aberta numa mesa de assessoria. Se o ensaio mostrar que o professor sempre abre, reabrimos a decisão 1 (ver "Perguntas de produto").

## Layout

### Celular (390 por 844, margem `espaco.4` = 16)
```
┌──────────────────────────────────────┐
│ Caixa do dia                    (↻) │  fonte.titulo-tela; ↻ = Atualizar, alvo 44
│ Quinta, 13/11/25                     │  fonte.rotulo, cor.texto-2
│ 3 alunos para olhar · 4 treinos novos│  fonte.corpo-forte
│                                      │
│ Para olhar hoje                      │  fonte.titulo-secao
│ Últimos 7 dias. Primeiro quem tem    │  fonte.legenda, cor.texto-2
│ dor marcada, depois fora do normal,  │
│ diferença da semana-padrão e         │
│ check-in perto do prazo.             │
│ ┌──────────────────────────────────┐ │  cartão (superficie, raio.grande, borda.fina)
│ │ Ana Exemplo                      │ │  fonte.titulo-secao
│ │ ┌──────────────────────────────┐ │ │  linha de treino tocável (alvo >= 72)
│ │ │ (🏃) Corrida · 45 min · 11/11│ │ │  chip + fonte.rotulo
│ │ │ (♡) Treino de terça com dor  │ │ │  ícone + fonte.corpo, cor.texto
│ │ │     marcada no check-in.     │ │ │
│ │ │ (~) Treino de terça fora do  │ │ │  uma linha por motivo
│ │ │     normal: FC média acima   │ │ │
│ │ │     do habitual.          (v)│ │ │  expandir: `expand-more`
│ │ └──────────────────────────────┘ │ │
│ └──────────────────────────────────┘ │
│ ┌──────────────────────────────────┐ │
│ │ Bruno Exemplo                    │ │
│ │ (🏃) Corrida · 50 min · 12/11    │ │
│ │ (▦) Treino de quarta diferente da│ │
│ │     semana-padrão: previsto      │ │
│ │     intervalado, sem esforço     │ │
│ │     detectado.                (v)│ │
│ └──────────────────────────────────┘ │
│ ┌──────────────────────────────────┐ │
│ │ Carla Exemplo                    │ │
│ │ (🚴) Ciclismo · 1 h 10 · 08/11   │ │
│ │ (◷) Treino de sábado sem check-in│ │
│ │     ; o prazo termina em 2 dias. │ │
│ └──────────────────────────────────┘ │
│ Diego Exemplo                        │  linha compacta, sem cartão: nome em fonte.corpo-forte
│ Nada a destacar nos últimos 7 dias.  │  fonte.corpo, cor.texto-2
│ ──────────────────────────────────── │
│ Elisa Exemplo                        │
│ Nada a destacar nos últimos 7 dias.  │
│                                      │
│ Treinos novos                        │  fonte.titulo-secao
│ Últimos 14 dias, com tipo sugerido.  │  fonte.legenda
│ Confirme como está ou mude o tipo.   │
│ [ ] Selecionar todos (4)             │  alvo 44, linha inteira tocável
│ ┌──────────────────────────────────┐ │
│ │[ ] Ana Exemplo                   │ │  caixa de seleção (alvo 48 x 72)
│ │    (🏃) Corrida · 45 min · 11/11 │ │
│ │    Intervalado (sugerido pela    │ │  chip do tipo + legenda
│ │    regra)     [Mudar tipo]   (v) │ │
│ └──────────────────────────────────┘ │
│ ...                                  │
├──────────────────────────────────────┤
│ 2 selecionados · 1 corrigido         │  barra fixa embaixo, só com seleção
│ [Limpar]          [ Salvar 2 tipos ] │  secundário 48 + primário 48
└──────────────────────────────────────┘
```
- Margem lateral 16; entre cartões `espaco.3` (12); entre seções `espaco.6` (32). Cartão: `cor.superficie`, `raio.grande`,
  `borda.fina` em `cor.borda`, sem sombra (padrão do guia).
- Os ícones de motivo (todos `cor.texto-2`, nunca de alerta) estão em "Motivos e ícones".
- Linha de treino com motivo: **uma área tocável** (alvo 72 ou mais) que expande o detalhe. A seta `expand-more`/`expand-less` em
  `cor.texto-2` fica à direita, alinhada ao topo.
- Aluno **sem motivo**: sem cartão e sem seta (não há o que abrir). Nome e frase em duas linhas, divisória `cor.borda`.
  Mais de cinco alunos assim ficam todos visíveis; o professor com 40 alunos rola, e a lista de motivos vem antes.
- **Barra de lote**: `cor.superficie`, borda superior `borda.fina` e `sombra.flutuante` (no escuro, sem sombra e com `cor.borda`).
  Fica fixa no rodapé **só com pelo menos um treino selecionado**. Altura 72 (padding `espaco.3` e botão de 48). O conteúdo ganha 88 de
  espaço no fim para a barra não cobrir a última linha.

### Treino novo, aberto, com a escolha de tipo
```
│ ┌──────────────────────────────────┐ │
│ │[✓] Ana Exemplo                   │ │  selecionado: fundo destaque-suave, contorno 2 em destaque e `check-box`
│ │    (🏃) Corrida · 45 min · 11/11 │ │
│ │    (✎) Corrigido para Longo      │ │  muda ao escolher outro tipo (não salvo)
│ │    [Mudar tipo] [Voltar à sugestão]│ │  dois botões de texto, alvo 44
│ │ ┌──────────────────────────────┐ │ │
│ │ │ Tipo       Intervalado, sugerido│ │ │  detalhe, fundo superficie-2, raio.medio
│ │ │            pela regra          │ │ │
│ │ │ Esforço    8                   │ │ │
│ │ │ Sensação   (☹) Mal             │ │ │
│ │ │ Atalhos    Dor, Cansaço        │ │ │
│ │ │ Feedback   O treino ficou perto│ │ │
│ │ │            do esforço dos ...  │ │ │
│ │ │ Observação (texto do aluno)    │ │ │
│ │ └──────────────────────────────┘ │ │
│ └──────────────────────────────────┘ │
```

### Folha "Tipo do treino"
Abre com "Mudar tipo". No celular, folha de baixo para cima (`sombra.flutuante`, `raio.grande` no alto); no computador, caixa
centrada de 400 de largura. Fecha com "Fechar" (`close`), com Esc e com toque fora.
```
┌──────────────────────────────────────┐
│ Tipo do treino                  (x) │  fonte.titulo-secao
│ Ana Exemplo · Corrida de terça 11/11 │  fonte.rotulo, cor.texto-2
│ ( ) Leve                             │  cinco linhas de 56, grupo de rádio
│ ( ) Moderado                         │
│ (•) Longo                  ✓         │  escolhido: destaque-suave, contorno 2 e `check`
│ ( ) Intervalado   Sugerido           │  etiqueta "Sugerido" na opção que veio da API
│ ( ) Fartlek                          │
└──────────────────────────────────────┘
```
- **Escolher fecha a folha na hora** (um toque). A linha fica selecionada e mostra "Corrigido para Longo". Escolher o tipo
  sugerido equivale a confirmar sem mudar ("Voltar à sugestão" faz o mesmo).
- Os cinco tipos valem para **qualquer modalidade elegível** (ciclismo e natação também), como a ADR 0015 decidiu.
- A etiqueta "Sugerido" é texto (nada só pela cor).

### Computador (largura 900 ou mais)
- **Uma coluna** com `largura.conteudo-max` (720), centrada, margem `espaco.5` (24). Mesmo layout do celular, com mais
  respiro. Não criamos tamanho novo: o professor usa a tela para ler e dar poucos toques.
- Barra de lote: fixa no rodapé com a mesma largura de 720, botões à direita, texto à esquerda numa linha só.
- Hover: linha tocável ganha fundo `cor.superficie-2`; foco por teclado: anel de `borda.foco` em `cor.foco`.
- Folha de tipo vira caixa centrada (400) com sombra flutuante e fundo escurecido (sem animação com "reduzir movimento").

### 360 por 640 e fonte grande
- A 360, nada muda no layout. Os botões da barra de lote ficam lado a lado até 360; abaixo disso (ou fonte a 200%), empilham:
  texto, depois "Salvar N tipos", depois "Limpar seleção" (a ação principal em cima do secundário).
- O chip de tipo e a legenda de origem quebram em duas linhas, sem cortar. Nenhum texto fica abaixo de 12 e o resumo e o
  título limitam a escala em 1,5 como em [[design/tokens]].

## Motivos e ícones
Cada motivo é uma linha de texto da API, precedida de um ícone de `icone.medio` (20) em `cor.texto-2`. O ícone **repete** o
que a frase diz; ele não é o único sinal e **não usa cor de estado** (nada de vermelho ou âmbar: é uma lista de "onde olhar",
não de perigo; as cores `alerta` e `erro` ficam só para falha da tela).

| `codigo` | ícone (Material Icons) | ordem do motivo dentro do treino |
|---|---|---|
| `dor` | `healing` | 1 |
| `fora_do_normal` | `show-chart` | 2 |
| `divergencia` | `event` | 3 |
| `checkin_vencendo` | `schedule` | 4 |

- Treino com dois motivos: **duas linhas** no mesmo bloco, na ordem da API (a ordem fixa da ADR). Nunca uma frase colada.
- Mais de um treino do mesmo aluno: um bloco de treino por vez, do mais recente ao mais antigo, separados por divisória
  `cor.borda`. O nome do aluno aparece **uma vez**, no alto do cartão.
- Vocabulário **proibido** em qualquer texto desta tela, igual à ADR: causa ("por causa do calor"), diagnóstico ("lesão"),
  conselho ("descanse", "converse com ele"), juízo ("bom", "ruim", "preocupante"), comparação entre alunos, número de saúde.

## Detalhe do treino (abrir e fechar)
Tocar na linha do treino **abre o detalhe logo abaixo** (acordeão), no mesmo lugar, sem trocar de tela. Tocar de novo fecha.
Mais de um aberto ao mesmo tempo é permitido (o professor compara). O estado aberto **não é guardado**: ao atualizar ou
sair, tudo volta fechado.

Bloco de detalhe (`cor.superficie-2`, `raio.medio`, padding `espaco.3`; rótulo à esquerda em `fonte.rotulo` e
`cor.texto-2`, valor à direita em `fonte.corpo`; em tela estreita, rótulo em cima e valor embaixo):
| linha | conteúdo | se faltar |
|---|---|---|
| Tipo | "Intervalado" e, em `fonte.legenda`, de onde veio ("sugerido pela regra", "da semana-padrão", "confirmado por você") | nunca falta (o treino novo tem tipo); no treino com motivo sem tipo, "Sem tipo" |
| Esforço | PSE como no check-in ("8"; com âncora, "5 · difícil"), texto da API | "Sem check-in ainda." (ocupa as três linhas seguintes) |
| Sensação | ícone `sentiment-*` e texto ("Mal"), os mesmos do check-in | idem |
| Atalhos | texto separado por vírgula ("Dor, Cansaço"); **não** são chips tocáveis | "Nenhum" (com `nada_a_relatar`: "Nada a relatar") |
| Feedback | a frase como o cartão do atleta mostra; nos estados sem texto, a `mensagem` ("O feedback será refeito.") | `feedback: null`: linha omitida |
| Observação | o texto do aluno **como foi escrito**, em bloco com borda esquerda de 2 em `cor.borda-forte`, preservando parágrafos | linha omitida |

- O rótulo da observação é "Observação do aluno" e, logo abaixo, em `fonte.legenda`: "Só você vê. Não vai ao provedor de IA."
  (a decisão 7 e a ADR 0015, item 7, garantem; o texto diz o que o professor precisa saber, sem jargão).
- **Os atalhos não são tocáveis** e não têm contorno, para ninguém achar que dá para marcar.
- O app **não** destaca palavras da observação, não tira conclusão dela e não a repete em nenhum outro ponto da tela
  (nem no título do cartão, nem no anúncio de acessibilidade do lote).
- O professor **não vê** recuperação (sono, VFC, FC de repouso), clima, posição, carga numérica, arquivo FIT, semana-padrão
  do aluno nem recordes (ADR 0015, item 7). O feedback pode citar recuperação **em frase**; isso vem do texto aprovado e a
  tela não separa nada (pergunta 5 da ADR 0015, do Angelo).
- Quando o treino tem motivo `divergencia` ou está em "Treinos novos", o detalhe ganha, no fim, o botão de texto "Confirmar ou
  corrigir em Treinos novos" (`chevron-right`, alvo 44). Ele rola até a linha do treino e leva o foco a ela. É só atalho de
  navegação: a ação em si fica **num lugar só**, em "Treinos novos".

## Confirmar e corrigir em lote

### O modelo de interação
Cada linha de "Treinos novos" tem um **estado local** (só na tela, nada guardado):
| estado da linha | como se vê | o que o `PUT` leva |
|---|---|---|
| **não selecionada** | caixa vazia (`check-box-outline-blank`), tipo sugerido | nada |
| **selecionada, sem mudança** | caixa marcada (`check-box`), fundo `cor.destaque-suave`, contorno 2 em `cor.destaque` | `tipo_treino` = o sugerido (**confirmar**) |
| **selecionada, corrigida** | igual, mais "Corrigido para Longo" com `edit` | `tipo_treino` = o escolhido (**corrigir**) |

- Escolher outro tipo na folha **seleciona a linha sozinha** (quem corrige quer salvar). "Voltar à sugestão" tira a correção
  e **mantém a linha selecionada**; a caixa desmarca com um toque.
- **Nenhuma linha vem selecionada** ao abrir (decisão 2). "Selecionar todos (N)" marca todas, **no máximo 200**; com mais de
  200 novos, marca os 200 primeiros da lista e mostra o aviso "Foram selecionados os 200 primeiros. Salve e selecione os próximos."
- A **barra de lote** diz o que vai acontecer **antes** de salvar: "2 selecionados · 1 corrigido" (o número de confirmados é o
  resto). Botão "Salvar 2 tipos" (1: "Salvar 1 tipo"). Só aparece com seleção.

### Desfazer: antes e depois de salvar
- **Antes de salvar, tudo se desfaz**: desmarcar a linha, "Voltar à sugestão", "Limpar seleção" (zera seleção e correções) e
  sair da tela. Sair com seleção ou correção pendente **não pede confirmação** (não há dado de saúde na ação, e o que
  se perde são poucos toques).
- **Depois de salvar, não há desfazer** ([[decisoes/0015-caixa-do-dia-do-professor]], itens 6 e 7 de "A confirmar": a correção não
  é desfeita; sem "voltar ao automático"). A tela diz isso **antes**, em texto fixo sob a barra: "Depois de salvar, para mudar de novo
  é só corrigir o tipo outra vez." (decisão 4: sem diálogo de confirmação).

### Salvar
1. Toque em "Salvar N tipos": a barra vira "Salvando..." com indicador; botões e linhas ficam desligados; **nada some** da tela.
2. Sucesso (`200`): a tela **busca a caixa de novo** (a lista é calculada a cada leitura). As linhas salvas **saem** de "Treinos novos"
   e, se tinham `divergencia`, o motivo some do cartão. Aviso de sucesso no topo da seção ("Aviso" do guia, `cor.sucesso-suave`,
   `check-circle-outline`) e anúncio para o leitor de tela: **"3 treinos salvos: 2 confirmados e 1 corrigido."**
3. O foco vai ao **título "Treinos novos"** (as linhas onde estava saíram). Sem treino que sobre: o título e o estado vazio da seção.
4. Se a nova busca falhar depois de um `PUT` bem-sucedido: o aviso de sucesso fica e a seção mostra "Não foi possível atualizar a
   lista. O que você salvou está salvo." com "Atualizar".

### Erros do lote
Em todos: **nada foi gravado** (tudo ou nada), **a seleção e as correções ficam** e o botão volta a ligar.
| situação | texto do aviso de erro (`alert`, acima da barra) |
|---|---|
| sem rede ou `5xx` | "Não foi possível falar com o servidor. Nada foi salvo. Tente de novo." |
| `404` `atividade_nao_encontrada` | "Algum treino não está mais disponível para você. Nada foi salvo. Atualize a lista e escolha de novo." com botão "Atualizar" (atualiza e **limpa a seleção**) |
| `422` `atividade_sem_tipo` | "Algum treino não aceita tipo. Nada foi salvo. Atualize a lista." com "Atualizar" |
| `422` de validação (não deve ocorrer) | "Algum dado do lote não foi aceito. Nada foi salvo. Tente de novo mais tarde." |

A API **não diz quais** ids foram recusados (só o código), então o texto não aponta uma linha.

### O que o professor corrige e confirma
Só o **tipo**. Nada mais é editável nesta tela (PSE, sensação, atalho e observação são do aluno; a semana-padrão é dele).
Confirmar e corrigir viram as gravações da ADR 0015, item 5; a tela não explica isso, só mostra o resultado: "confirmado" ou
"corrigido" no detalhe ("confirmado por você") na próxima leitura **fora** de "Treinos novos".

## Estados
Segue [[design/guia-visual]], "Estados". O conteúdo que já está na tela **não some** quando uma nova ação começa.

### Tela
| estado | o que aparece | texto |
|---|---|---|
| carregando (primeira busca) | título e data reais; esqueleto de dois cartões de aluno e três linhas de treino novo (`cor.superficie-2`, `raio.pequeno`, `movimento.esqueleto`; parado com "reduzir movimento"). O texto fica para o leitor de tela | "Carregando a caixa do dia..." |
| atualizando (botão ↻) | o conteúdo **continua**; o ícone vira indicador pequeno e o botão fica desligado | anúncio: "Atualizando..." depois "Caixa do dia atualizada." |
| com conteúdo | as duas seções | ver acima |
| sem alunos (nenhum com vínculo e consentimento) | `group` de `icone.estado` em `cor.texto-2`, título e frase; **sem botão primário** (não há ação do professor aqui) | "Nenhum aluno na caixa do dia" / "Aparecem aqui os alunos com vínculo e consentimento registrados." |
| alunos, **nenhum com motivo** | seção "Para olhar hoje" com a mensagem e os alunos em linhas compactas | "Nenhum aluno com algo a destacar nos últimos 7 dias." |
| **sem treinos novos** | `check-circle-outline` pequeno em `cor.texto-2` e frase, no lugar das linhas | "Nenhum treino novo para confirmar." (legenda: "Treinos com tipo sugerido, dos últimos 14 dias, aparecem aqui.") |
| erro (rede) | `wifi-off` de 40, frase e "Tentar de novo" | "Não foi possível falar com o servidor" / "Sua caixa do dia continua como estava. Tente de novo." |
| erro `404` uniforme, ou sem `professor_id` configurado | `error-outline` de 40, título e frase; **sem "Tentar de novo"** (repetir não muda) | "Caixa do dia não encontrada" / "Confira o professor configurado neste computador." |
| erro (outro, `5xx`) | `error-outline` e frase, "Tentar de novo" | "Não foi possível carregar a caixa do dia. Tente de novo mais tarde." |
| erro ao atualizar (já havia conteúdo) | o conteúdo antigo fica; aviso de erro no topo | "Não foi possível atualizar. Você está vendo a caixa de antes." |

- O estado de erro `404` **não diz** se o professor não existe, se o id está errado ou se a variável está vazia: a API também não diz
  (corpo uniforme, ADR 0015 item 2), e o app não adivinha. O "como configurar" fica no guia da #428, não na tela.
- Tema claro e escuro: todos os estados têm a mesma estrutura nos dois; `wifi-off`, `error-outline`, `group` e
  `check-circle-outline` seguem as cores dos tokens, sem sombra.

### Esboço por estado (390, mesmas cores nos dois temas pela tabela de tokens)

**Carregando**
```
│ Caixa do dia                    (↻) │
│ Quinta, 13/11/25                     │
│ ░░░░░░░░░░░░░░░░░░░░                │  resumo (esqueleto)
│ Para olhar hoje                      │
│ ┌──────────────────────────────────┐ │
│ │ ░░░░░░░░░░                       │ │
│ │ ░░░░░░░░░░░░░░░░░░░░░░           │ │
│ │ ░░░░░░░░░░░░░░░░░░░░░░░░░░░░     │ │
│ └──────────────────────────────────┘ │
│ ┌──────────────────────────────────┐ │
│ │ ░░░░░░░░░░                       │ │
│ │ ░░░░░░░░░░░░░░░░░░░░░░░░         │ │
│ └──────────────────────────────────┘ │
│ Carregando a caixa do dia...         │  fonte.legenda, cor.texto-2
```

**Sem alunos**
```
│ Caixa do dia                    (↻) │
│ Quinta, 13/11/25                     │
│                                      │
│              (👥)                    │  `group`, 40, cor.texto-2
│    Nenhum aluno na caixa do dia      │  fonte.titulo-secao
│    Aparecem aqui os alunos com       │
│    vínculo e consentimento           │
│    registrados.                      │  fonte.corpo, cor.texto-2
```

**Tudo sem motivo, sem treinos novos**
```
│ Caixa do dia                    (↻) │
│ 0 alunos para olhar · 0 treinos novos│
│ Para olhar hoje                      │
│ Nenhum aluno com algo a destacar nos │
│ últimos 7 dias.                      │
│ Diego Exemplo                        │
│ Nada a destacar nos últimos 7 dias.  │
│ ...                                  │
│ Treinos novos                        │
│ (✓) Nenhum treino novo para          │
│     confirmar.                       │
```

**Erro de rede, erro 404 uniforme**
```
│ Caixa do dia                         │          │ Caixa do dia                         │
│              (wifi-off)              │          │              (error-outline)         │
│ Não foi possível falar com o servidor│          │ Caixa do dia não encontrada          │
│ Sua caixa do dia continua como       │          │ Confira o professor configurado      │
│ estava. Tente de novo.               │          │ neste computador.                    │
│        [ Tentar de novo ]            │          │ (sem botão)                          │
```

**Lote: com seleção, salvando, erro, salvo**
```
 seleção                          salvando                       erro (404 do lote)               salvo
├─────────────────────────┤     ├─────────────────────────┤   ├───────────────────────────┤   ├────────────────────────┤
│ 2 selecionados          │     │ (◌) Salvando...         │   │ (!) Algum treino não está │   │ (✓) 3 treinos salvos:  │
│ · 1 corrigido           │     │ botões desligados       │   │ mais disponível para você.│   │ 2 confirmados e 1      │
│ [Limpar] [Salvar 2 tipos]│    │ linhas desligadas       │   │ Nada foi salvo. [Atualizar]│  │ corrigido.             │
```
(O `(!)` do erro é `error-outline`; o do aviso de sucesso é `check-circle-outline`. A barra some depois de salvo.)

## Textos
Todos em português, frases curtas, sem "alerta", sem "erro" nem "falha" na tela, sem código, sem culpar o professor.

| onde | texto |
|---|---|
| título | "Caixa do dia" |
| data | "Quinta, 13/11/25" |
| resumo | "3 alunos para olhar · 4 treinos novos" (1: "1 aluno para olhar"; 1: "1 treino novo"; 0: "0 alunos para olhar") |
| seção 1 | "Para olhar hoje" |
| apoio da seção 1 | "Últimos 7 dias. Primeiro quem tem dor marcada, depois fora do normal, diferença da semana-padrão e check-in perto do prazo." |
| sem motivo | "Nada a destacar nos últimos 7 dias." (vem da API) |
| seção 2 | "Treinos novos" |
| apoio da seção 2 | "Últimos 14 dias, com tipo sugerido. Confirme como está ou mude o tipo." |
| selecionar | "Selecionar todos (4)" / "Limpar seleção" |
| origem do tipo | "sugerido pela semana-padrão", "sugerido pela regra" (da API) |
| botões | "Mudar tipo", "Voltar à sugestão", "Salvar 2 tipos" ("Salvar 1 tipo"), "Limpar seleção", "Atualizar", "Tentar de novo", "Confirmar ou corrigir em Treinos novos" |
| correção local | "Corrigido para Longo" |
| folha | "Tipo do treino", "Sugerido" |
| aviso fixo | "Depois de salvar, para mudar de novo é só corrigir o tipo outra vez." |
| detalhe | "Tipo", "Esforço", "Sensação", "Atalhos", "Feedback", "Observação do aluno" |
| observação | "Só você vê. Não vai ao provedor de IA." |
| sem check-in | "Sem check-in ainda." |
| atalhos | "Dor", "Cansaço", "Sono ruim", "Calor", "Trabalho ou estresse"; sem nenhum: "Nenhum"; "Nada a relatar" |
| sucesso | "3 treinos salvos: 2 confirmados e 1 corrigido." |

**Motivos** (vêm da API; estes são os da ADR 0015, só para o esboço e a captura): "Treino de terça com dor marcada no check-in.",
"Treino de terça fora do normal: FC média acima do habitual.", "Treino de quarta diferente da semana-padrão: previsto intervalado,
sem esforço detectado.", "Treino de sábado sem check-in; o prazo termina em 2 dias.".

## Acessibilidade
- **Contraste AA em todos os pares**; nenhuma cor nova ([[design/tokens]], seção "Contraste"). Os pares usados: `cor.texto` e
  `cor.texto-2` sobre `cor.superficie`, `cor.fundo` e `cor.superficie-2`; `cor.destaque` sobre `cor.destaque-suave`;
  `cor.sobre-destaque` sobre `cor.destaque`; `cor.borda-forte` (3:1) nos contornos de caixa de seleção e botão secundário.
- **Alvos de toque de pelo menos 44**: linha de treino 72 ou mais; caixa de seleção com área tocável 48 por 72 (o desenho da caixa
  tem 24); "Mudar tipo" e "Voltar à sugestão" 44; botões da barra 48; opção da folha 56; "Atualizar" 44 por 44.
- **Nada só pela cor**: seleção = `check-box` marcado **e** contorno mais grosso **e** o texto "N selecionados"; correção =
  `edit` **e** o texto "Corrigido para..."; cada motivo = ícone **e** frase; erro = ícone **e** texto.
- **Texto legível ao ar livre e em celular pequeno**: texto principal em `cor.texto` (15:1 ou mais), nada em cinza claro,
  nada abaixo de 12, motivo em 16. A 360 por 640 a primeira dobra mostra o título, o resumo e o primeiro cartão.
- **Estrutura e ordem de foco** (a ordem de leitura é a visual): "Atualizar"; título (cabeçalho nível 1); resumo; título "Para olhar
  hoje" (nível 2); para cada aluno, nome (nível 3) e depois as linhas de treino; título "Treinos novos" (nível 2); "Selecionar
  todos"; para cada treino novo, caixa de seleção, o detalhe, "Mudar tipo"; barra de lote (por último, **mas** em `region` com rótulo
  "Ações do lote", para o leitor de tela pular até ela). As seções são `region` rotuladas pelo título.
- **Rótulos**: linha de treino é lida como "Treino de terça com dor marcada no check-in. Treino de terça fora do normal: FC média
  acima do habitual. Corrida, 45 minutos, 11 de novembro. Botão, fechado." (`accessibilityRole="button"` e `expanded`; na web,
  `aria-expanded`). Caixa de seleção: `checkbox` com `checked` e rótulo "Selecionar o treino de Ana Exemplo, corrida de 11 de novembro,
  tipo sugerido intervalado". O nome é lido; o **conteúdo da observação nunca entra em rótulo ou anúncio**.
- **Anúncios** (`accessibilityLiveRegion="polite"` no Android; anúncio no iOS e na web; só texto, **sem dado de saúde**): ao salvar,
  "3 treinos salvos: 2 confirmados e 1 corrigido."; ao selecionar, "2 selecionados"; ao atualizar, "Caixa do dia atualizada."; no erro,
  o texto do aviso (`alert`). Ao abrir um detalhe, o foco **fica** no botão (o conteúdo aberto é o próximo na ordem); ao fechar, idem.
- **Folha "Tipo do treino"**: `dialog` modal, foco no título ao abrir, **foco preso** dentro, Esc fecha, e ao fechar o foco volta para o
  botão "Mudar tipo" da mesma linha. Opções num grupo de rádio ("Leve, botão de opção, 1 de 5"); escolhida: "selecionado".
- **Teclado na web**: Tab percorre na ordem acima; Enter e Espaço abrem a linha, marcam a caixa e escolhem a opção; Esc fecha a folha;
  setas movem entre as opções da folha. Anel de foco de `borda.foco` em `cor.foco`, sempre visível.
- **Fonte grande e zoom**: nada é cortado; os cartões crescem; a barra de lote empilha os botões; a página rola.
  Sem rolagem horizontal em 390, em 320 e com zoom de 200% na web.
- **Reduzir movimento**: sem esqueleto pulsando, sem transição ao abrir o detalhe e a folha.
- **Leitor de tela e "Atualizar"**: o botão tem rótulo "Atualizar a caixa do dia", não só o ícone.

## Privacidade no desenho
- Esta é a primeira tela que mostra **dado de saúde de outra pessoa**. O desenho a trata com o mesmo rigor do check-in:
  nada guardado, nada em URL, nada em log, nada em captura.
- A lista (fechada) **nunca** mostra PSE, sensação, atalho nem observação; só o motivo (que já é uma frase pronta, sem número de saúde).
  O dado fica atrás de um toque, e o estado aberto não é guardado.
- A observação livre só aparece no detalhe, com a frase "Só você vê. Não vai ao provedor de IA.", e nunca em título, rótulo
  de acessibilidade, anúncio, mensagem de erro, parâmetro de rota ou armazenamento local.
- **Aluno sem vínculo ou sem consentimento não existe para a tela** (a API não manda; o app não tem como pedir): a tela não tem
  busca de aluno, filtro por nome, nem acesso por id na barra de endereço.
- **Só atletas fictícios** em esboço, teste e captura: nomes "Ana Exemplo" e semelhantes, datas e textos escritos à mão. A observação
  dos exemplos é um texto marcador ("Texto de exemplo escrito à mão"). A conta do Angelo, se ligada a um professor de teste (#431),
  **nunca** vai para captura ou esboço do repositório.
- Impressão e captura de tela feitas pelo professor estão **fora do controle** do app; o termo do consentimento (consulta
  jurídica) é quem cobre isso.

## Como gerar capturas sintéticas
Pelo comando `npm run capturas` (em `apps/mobile`, #418): a API falsa serve a caixa do dia com **fixtures escritas à mão** (ADR 0015,
#421), e cada estado é forçado por uma variável (`EXPO_PUBLIC_PROFESSOR_ID` e fixtures próprias), como na semana-padrão. Uma captura por
estado, em 390 por 844 **e** em 900 de largura (computador), **claro e escuro**. Os estados: com conteúdo e um detalhe aberto
(a observação com o texto marcador), com seleção e correção na barra, folha de tipo aberta, carregando, sem alunos, sem motivo e sem
novos, erro de rede, erro `404`, lote salvo, lote com erro. As capturas ficam em `docs/design/telas/caixa-do-dia/`
(`caixa-do-dia-<estado>-<tema>.png`).

## O que muda em relação ao app de hoje
| hoje | proposta | issue |
|---|---|---|
| o app só tem telas do atleta (evolução, treino, semana-padrão, check-in) | rota `/caixa-do-dia` do professor, lista de atenção | #426 |
| sem noção de professor | `professor_id` da configuração, sem login | #423 |
| sem lista de atenção nem de treinos novos | duas seções, com motivos prontos da API | #424 (API), #426 (tela) |
| o tipo do treino só muda pela semana-padrão e pela regra | confirmar e corrigir em lote | #425 (API), #427 (tela) |
| ícones de motivo e de seleção | `healing`, `show-chart`, `schedule`, `check-box`, `check-box-outline-blank`, `expand-more`, `expand-less` e `group` em [[design/tokens]] | #426 e #427 |

## Decisões de produto
As sete perguntas desta spec foram respondidas em 16/11 e **todas seguiram a recomendação**. O Angelo respondeu "ok para as 4"
(perguntas 2, 4, 5 e 7); o Theo decidiu as perguntas 1, 3 e 6 (comentário no PR #437). O corpo da nota já está de acordo.

| # | pergunta | decisão | quem |
|---|---|---|---|
| 1 | Onde abre o detalhe do treino | **Dentro da lista** (acordeão), fechado por padrão; sem rota com id de treino | Theo |
| 2 | Seleção inicial dos treinos novos | **Nenhum selecionado**; "Selecionar todos (N)" marca (máx. 200) | Angelo |
| 3 | Ordem dos treinos novos | **Mais recente primeiro** (data local, depois início), nome do aluno em cada linha; quem ordena é a API (#424) | Theo |
| 4 | Diálogo ao salvar o lote | **Sem diálogo**: a barra diz "N selecionados · N corrigido" antes; corrigir de novo desfaz depois | Angelo |
| 5 | Treino sem motivo e já confirmado não aparece | **Aceito** na Meta 11 (ficha completa fora); medir no ensaio com professor se faz falta | Angelo |
| 6 | Computador | **Uma coluna de 720** (`largura.conteudo-max`); duas colunas só se o ensaio pedir | Theo |
| 7 | Frase sob a observação | **Mantida**: "Só você vê. Não vai ao provedor de IA."; troca pelo texto do termo quando ele existir (consulta de LGPD) | Angelo |

## Referências ao contrato para quem implementa
- Nada de motivo, janela, ordem ou "novo" calculado no app. Tudo vem pronto no `GET` (#424).
- O `PUT` leva só `atividade_id` e `tipo_treino`. Nada de PSE, observação ou nome sai do app.
- Os testes do Rafa usam a API falsa com as fixtures da #421 e **texto marcador sintético**; nenhum teste, captura ou log com
  observação real. Revisão da Lia no PR do Rafa **com as capturas do comando** e com a tela rodando (critério de pronto da Meta 11).
