---
tipo: design
status: rascunho
dono: lia
atualizado: 2026-11-17
links: [[design/guia-visual]], [[design/tokens]], [[design/telas/entrar]], [[design/telas/caixa-do-dia]], [[design/telas/checkin]], [[decisoes/0015-caixa-do-dia-do-professor]], [[decisoes/0012-check-in-pos-treino]], [[produto/roadmap]], [[modulos/mobile]]
---
# Tela: consentimento do atleta para o professor

Spec da issue #498 (Meta 13), antes da tela (P7 da Meta 13, do Rafa) e junto da ADR 0016 (#497), que ainda não foi aceita. Hoje o
consentimento é uma coluna no banco (`vinculo_professor_atleta.consentimento_em`, [[decisoes/0015-caixa-do-dia-do-professor]]); aqui
**o próprio atleta** o registra e o retira. Decisão do Angelo de 17/11: o **texto do termo é provisório e marcado como provisório**
até a consulta de LGPD, o CNPJ e o contrato com a assessoria (primeiro aluno real). Nomes e textos abaixo são **sintéticos**. Nada em
`apps/mobile/` muda nesta nota.

## Objetivo
O atleta decide, com calma e sabendo o quê, **quais professores podem ver os treinos dele**. A tela responde: "quem está pedindo para ver os meus
dados, o que essa pessoa vai ver e como eu volto atrás?". O consentimento é **dado de saúde**: o texto é direto, sem pressão, e retirar é
tão fácil quanto dar.

Quem consente é **só o atleta**, dentro da própria conta. O professor não vê esta tela e não consegue consentir por ele.

## Onde fica
Rota `/consentimento`, só para o papel atleta ([[design/telas/entrar]]). Entrada: "Conta" no cabeçalho da evolução, "Consentimento".
Se houver **pedido aguardando resposta**, a evolução mostra uma linha de aviso acima do conteúdo, com `info-outline`, o texto
"Há um professor pedindo para ver seus treinos." e o botão de texto "Ver", alvo 48. Sem pedido, não há aviso.

## O que a tela mostra
Uma lista de **professores com vínculo** com o atleta (o vínculo é criado por quem opera o piloto; a tela não cria vínculo). Cada
professor está em um de dois estados: **aguardando** o consentimento ou **consentido**.

```
┌──────────────────────────────────┐
│ ← Voltar                         │
│ Consentimento                    │  fonte.titulo-tela
│ Quem pode ver os seus treinos.   │  fonte.corpo, cor.texto-2
│ ┌──────────────────────────────┐ │  cartão por professor
│ │ Carlos Exemplo               │ │  fonte.titulo-secao
│ │ Assessoria Modelo            │ │  fonte.corpo, cor.texto-2
│ │ (hourglass) Aguardando você  │ │  estado: ícone + palavra
│ │ [  Ler e dar consentimento ] │ │  primário, 48
│ └──────────────────────────────┘ │
│ ┌──────────────────────────────┐ │
│ │ Marina Exemplo               │ │
│ │ Assessoria Modelo            │ │
│ │ (check) Consentido em        │ │
│ │ 10/11/26                     │ │
│ │ [  Retirar consentimento  ]  │ │  secundário, 48, texto cor.texto
│ └──────────────────────────────┘ │
└──────────────────────────────────┘
```
- **Estado em palavra e ícone**, nunca só cor: "Aguardando você" (`hourglass-empty`) e "Consentido em dd/mm/aa"
  (`check-circle-outline`). "Consentido" não é verde de sucesso: `cor.texto-2` com o ícone, para não parecer pressão a aceitar.
- Ordem: **aguardando primeiro**, depois consentidos, cada grupo por nome.
- Computador (a partir de 600): a mesma coluna, até 720, margem 24.

## Ler e dar consentimento
Tocar em "Ler e dar consentimento" abre a tela do termo (uma tela, não um diálogo: o texto é longo).
```
┌──────────────────────────────────┐
│ ← Voltar                         │
│ Termo de consentimento           │  fonte.titulo-tela
│ ┌ (warning-amber) TEXTO PROVISÓRIO ┐│  faixa de alerta, cor.alerta sobre cor.alerta-suave
│ │ Este texto ainda não foi revisto ││  fica no topo do termo
│ │ por quem entende de lei. Ele vale││
│ │ só para o piloto.                ││
│ └──────────────────────────────────┘│
│ Você está dando permissão a:     │  fonte.corpo
│ Carlos Exemplo, da Assessoria    │  fonte.corpo-forte
│ Modelo.                          │
│ O professor vai ver:             │  fonte.titulo-secao
│  - os seus treinos e a análise   │
│  - o que você responde no        │
│    check-in: esforço, sensação,  │
│    dor e a observação que você   │
│    escrever                      │
│  - o feedback de cada treino     │
│ O professor não vê:              │
│  - a sua senha                   │
│  - treinos de outros atletas     │
│ Você pode retirar quando quiser. │
│ O professor deixa de ver seus    │
│ treinos na hora. O que ele já    │
│ gravou, como o tipo corrigido de │
│ um treino, fica.                 │
│ [ ] Li e concordo                │  caixa de seleção, alvo 48, rótulo clicável
│ [   Dar consentimento   ]        │  primário, 48, desligado até marcar
└──────────────────────────────────┘
```
- **Faixa "Texto provisório"** acima de tudo, `warning-amber` e a palavra "provisório", fixa no texto do termo (e repetida numa linha
  curta no cartão da lista, "Termo provisório"). Redação: "Este texto é provisório. Ainda não foi revisto por quem entende de lei e
  vale só para o piloto." O texto real do termo **substitui** o provisório quando vier da consulta de LGPD; a faixa **some sozinha**
  quando a API disser que o termo não é mais provisório (campo `provisorio`).
- **O texto do termo vem da API** (versão e texto), não fica fixo no app: trocar o termo não exige novo aplicativo, e o app **registra
  qual versão** o atleta leu ([[decisoes/0015-caixa-do-dia-do-professor]]: "o texto do termo fica para a consulta jurídica").
- O corpo do termo acima é a **proposta de redação da Lia** para o texto provisório, em palavras simples, para a Duda e o Angelo
  ajustarem. A lista "o professor vai ver" **tem de bater com o que a API entrega ao professor** (ADR 0015, item 7: tipo, PSE, sensação,
  atalhos, feedback e **observação livre**). Se a API mudar o que o professor vê, o termo muda junto.
- **"Li e concordo"** liga o botão. Não vem marcado. O botão diz "Dar consentimento" (a ação), não "Aceitar".
- Sem "aceitar tudo", sem nada pré-marcado, sem botão de cor chamativa: a decisão é do atleta.
- "Voltar" sem consentir não muda nada e **não** pergunta nada.

### Estados da tela do termo
| estado | o que aparece | texto |
|---|---|---|
| carregando o termo | esqueleto de quatro linhas e o texto | "Carregando o termo..." |
| pronto | o termo, a faixa provisória, a caixa e o botão | |
| salvando | botão desligado, "Salvando..." | "Salvando..." |
| salvo | volta à lista, com o cartão do professor já em "Consentido em dd/mm/aa" e o anúncio "Consentimento registrado." | |
| erro de rede ao salvar | faixa de erro acima do botão; a caixa continua marcada | "Não foi possível salvar. Tente de novo." |
| termo mudou enquanto lia (`409`) | faixa neutra e o termo recarregado, caixa desmarcada | "O texto do termo mudou. Leia de novo antes de dar o consentimento." |
| professor não está mais na lista (`404`) | volta à lista com a frase | "Este pedido não existe mais." |
| erro ao carregar o termo | ícone `error-outline`, frase e "Tentar de novo" | "Não foi possível carregar o termo. Tente de novo." |

## Retirar o consentimento
Tocar em "Retirar consentimento" abre um diálogo:
```
┌ Retirar o consentimento? ────────┐
│ Carlos Exemplo deixa de ver os   │
│ seus treinos a partir de agora.  │
│ O que ele já gravou, como o tipo │
│ corrigido de um treino, fica.    │
│ Você pode dar o consentimento de │
│ novo depois.                     │
│ [   Cancelar   ] [  Retirar  ]   │  "Cancelar" primário; "Retirar" secundário
└──────────────────────────────────┘
```
- Depois de retirar, o vínculo **continua** (a linha não se apaga, ADR 0015) e o cartão
  volta a "Aguardando você", com o botão "Ler e dar consentimento" (dar de novo é um caminho curto). Para tirar o vínculo de vez, quem
  opera o piloto remove (decisão 3 abaixo).
- "Retirar" é um passo só, sem pedir senha (é uma proteção do atleta, tem de ser fácil).
- Erro de rede: "Não foi possível retirar. Tente de novo." e o estado fica como estava. Anúncio ao concluir: "Consentimento retirado."

## Estados da lista
| estado | o que aparece | texto |
|---|---|---|
| carregando | esqueleto de dois cartões e o texto | "Carregando..." |
| vazio (nenhum vínculo) | ícone `info-outline` em `cor.texto-2` e frase | "Nenhum professor pediu para ver os seus treinos. Quando pedir, o pedido aparece aqui." |
| com cartões | a lista acima | |
| erro de rede | ícone `wifi-off` de 40, frase e "Tentar de novo" | "Não foi possível falar com o servidor" |
| `401` | leva a `/entrar` com "Seu acesso expirou. Entre de novo." | |
| outro erro | `error-outline` e frase | "Não foi possível carregar. Tente de novo mais tarde." |

## O que o professor vê quando o atleta retira
Na caixa do dia, o atleta **some na leitura seguinte**, com os treinos e os dados ([[design/telas/caixa-do-dia]] e a matriz da
ADR 0015). Sem aviso ao professor no app (o piloto não tem notificação): se ele perguntar, quem opera explica. Fica na ADR a decisão de
avisar ou não.

## Acessibilidade
- Cada cartão de professor é um grupo único lido como "Carlos Exemplo, Assessoria Modelo, aguardando você" com o botão logo depois.
- A faixa provisória é lida **antes** do texto do termo (`accessibilityRole="alert"` ao abrir a tela do termo, uma vez).
- A caixa "Li e concordo" tem estado marcado/desmarcado, alvo de 48 e o rótulo inteiro é tocável.
- Diálogo de retirar: foco em "Cancelar", Esc fecha; texto lido na abertura.
- Contraste: `cor.alerta` sobre `cor.alerta-suave` (5,56 claro, 7,59 escuro), `cor.texto-2` sobre `cor.superficie` (7,92 e 8,44),
  conforme [[design/tokens]]. Nada de cor como única informação: estado em ícone e palavra.
- Texto do termo em `fonte.corpo` (16), nunca abaixo de 14; rolagem simples, sem expandir/recolher.

## Lista de campos que a tela precisa da API (entrada da ADR 0016, #497, e da issue do consentimento, P5)
Nomes são proposta; a ADR 0016 decide.

| tela | rota | pede | recebe |
|---|---|---|---|
| Lista | `GET /eu/professores` | acesso (papel atleta) | `professores[]`: `professor_id`, `nome`, `assessoria_nome`, `estado` (`aguardando` ou `consentido`), `consentimento_em` (data, só se consentido), `termo_versao` (a versão que o atleta aceitou, só se consentido) |
| Aviso na evolução | a mesma rota | | `total_aguardando` (inteiro) para a linha de aviso, ou o app conta `estado = aguardando` na lista |
| Termo | `GET /termo` | acesso | `versao`, `texto` (blocos de texto pronto, em português), `provisorio` (booleano), `aviso_provisorio` (a frase da faixa, para ficar na mão de quem muda o termo) |
| Dar consentimento | `PUT /eu/professores/{professor_id}/consentimento` | `termo_versao` | `200` com o item da lista; `409` `termo_mudou` se a versão enviada não é a atual; `404` se o vínculo não existe; `401` |
| Retirar | `DELETE /eu/professores/{professor_id}/consentimento` | | `200` com o item da lista (volta a `aguardando`) ou `204`; `404` |
Regras que a tela **espera** da API (o app não decide nada disto):
- o atleta só consente **para ele mesmo**: `atleta_id` vem do acesso, nunca do corpo;
- o `consentimento_em` é gravado pela API com a hora dela, não pelo app;
- o log do servidor **não grava** nome, `termo_versao` nem o fato de ter consentido junto do atleta (dado de saúde);
- consentir e retirar são idempotentes (tocar duas vezes não dá erro).

## Decisões de contrato (Theo, 17/11)
Comentário do Theo no PR #512; entram na ADR 0016 (#497). Todas como a Lia recomendou.
1. **Vínculo:** criado por **quem opera o piloto**, sem convite por e-mail; o atleta vê o pedido na lista e no aviso da evolução.
2. **Versão do termo:** `termo_versao` é gravada junto de `consentimento_em` (registrado na ADR 0016).
3. **Retirar:** só o consentimento; o **vínculo fica** e o cartão volta a "Aguardando você". Tirar o vínculo é por quem opera.
4. **Aviso ao professor ao retirar:** **não** no piloto.
5. **Texto do termo:** segue **provisório e marcado**; o texto definitivo vem antes do primeiro aluno real (decisão do Angelo). A redação
   desta tela é proposta da Lia, em palavras simples, para o Angelo ler e ajustar.
