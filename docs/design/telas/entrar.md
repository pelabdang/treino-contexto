---
tipo: design
status: rascunho
dono: lia
atualizado: 2026-11-17
links: [[design/guia-visual]], [[design/tokens]], [[design/telas/consentimento]], [[design/telas/caixa-do-dia]], [[design/telas/treino]], [[produto/roadmap]], [[modulos/mobile]]
---
# Telas: entrar, sair, acesso expirado e trocar a senha

Spec da issue #498 (Meta 13), antes das telas (P6 da Meta 13, do Rafa) e junto da ADR 0016 (#497, da Duda), que ainda não foi
aceita: a lista de campos no fim ajusta ao texto final da ADR. Decisões do Angelo de 17/11 ([[produto/roadmap]], "Meta 13"):
**e-mail e senha na própria API**, **sem e-mail transacional** (a senha esquecida é refeita por quem opera o piloto) e **sem login a
tela do atleta e a caixa do professor não abrem**. Todos os nomes, e-mails e textos abaixo são **sintéticos**. Nada em
`apps/mobile/` muda nesta nota.

## Objetivo
Quem abre o app diz quem é, com e-mail e senha, e cai na tela certa: o **atleta** na evolução dos tiros e o **professor** na caixa
do dia. Sem entrar, nenhuma outra tela abre. A tela responde: "sou eu mesmo, posso ver os meus treinos?". Depois de entrar,
sair e voltar têm um jeito só, simples e previsível.

O tom é calmo e direto. **Palavras simples, sem jargão de segurança**: "entrar", "senha", "seu acesso", nunca "autenticação",
"credencial", "sessão", "token" nem "bloqueado".

## Mapa das telas
| rota | tela | quem vê | entrada |
|---|---|---|---|
| `/entrar` | Entrar | qualquer pessoa sem acesso ativo | abrir o app ou qualquer endereço sem acesso; "Sair" |
| `/trocar-senha` | Trocar a senha | quem já entrou | primeiro acesso (senha provisória) ou "Trocar senha" no menu |
| (diálogo) | Sair | quem já entrou | "Sair" no cabeçalho |
| (faixa e redirecionamento) | Acesso expirado | quem já entrou | qualquer chamada à API que volta `401` |

Regra geral de rotas: **só `/entrar` abre sem acesso.** Qualquer outro endereço (`/`, `/treino/<id>`, `/caixa-do-dia`,
`/semana-padrao`, `/checkin/<id>`, `/consentimento`) sem acesso leva a `/entrar` e **lembra** onde a pessoa queria ir. Depois de
entrar, volta para lá. O endereço lembrado é sempre um caminho **do próprio app** (começa com `/`, sem domínio): endereço de fora é
ignorado, para ninguém mandar o atleta para outro site.

## Entrar
```
┌──────────────────────────────────┐
│                                  │
│ Entrar                           │  fonte.titulo-tela
│ Use o e-mail e a senha do seu    │  fonte.corpo, cor.texto-2
│ cadastro.                        │
│                                  │
│ E-mail                           │  fonte.rotulo (rótulo visível)
│ ┌──────────────────────────────┐ │  campo, alvo 48, raio.medio, cor.borda-forte
│ │ ana@exemplo.com              │ │
│ └──────────────────────────────┘ │
│ Senha                            │
│ ┌────────────────────────┬─────┐ │
│ │ ••••••••••             │ Ver │ │  botão de texto "Ver" / "Esconder", alvo 48
│ └────────────────────────┴─────┘ │
│                                  │
│ [           Entrar             ] │  primário, 48
│                                  │
│ Esqueceu a senha? Fale com quem  │  fonte.corpo, cor.texto-2
│ convidou você para o piloto: ele │
│ cria uma senha nova para você.   │
└──────────────────────────────────┘
```
Computador (a partir de 600): o mesmo formulário num cartão de até 420 de largura, centrado na horizontal, no alto da área (não no
meio vertical: com o teclado e a janela baixa o botão precisa ficar à vista), `cor.superficie` com a borda de 1.

- **Rótulos visíveis acima dos campos**, não só texto de exemplo (o texto de exemplo some ao digitar e perde contraste ao sol).
- **E-mail:** teclado de e-mail, sem maiúscula automática, sem correção automática, `autoComplete="email"`. **Senha:**
  `autoComplete="current-password"`, o gerenciador de senhas do aparelho funciona. "Ver" mostra a senha; volta a esconder ao sair
  da tela.
- **Teclado:** "próximo" no e-mail leva à senha; "ok" na senha envia. O botão "Entrar" fica **desligado enquanto algum campo
  está vazio** (não valida o formato do e-mail no app: a API decide).
- **Sem cadastro.** Não existe "Criar conta" nem "Esqueci a senha" automático: no piloto as contas são criadas por quem opera, e
  a senha esquecida é refeita por ele (decisão 4 da Meta 13, sem e-mail). A frase de rodapé diz isso sem prometer nada que o app não faz.
- **Nada de "Lembrar de mim".** O acesso fica guardado no aparelho até a pessoa tocar em "Sair" ou até a API dizer que expirou
  (ver "Acesso expirado").
- Sem logotipo nem imagem: o app ainda não tem (guia visual, "O que fica fora").

### Estados da tela de entrar
| estado | o que aparece | texto |
|---|---|---|
| inicial | campos vazios, "Entrar" desligado | |
| pronto | "Entrar" ligado | |
| entrando | botão desligado com o texto "Entrando...", campos desligados; o texto fica, para leitor de tela | "Entrando..." |
| e-mail ou senha errados (`401`) | faixa de erro acima do botão, `error-outline`, `cor.erro` sobre `cor.erro-suave`; **a senha é apagada, o e-mail fica**; o foco vai para a senha | "E-mail ou senha incorretos. Confira e tente de novo." |
| muitas tentativas (`429`) | faixa neutra `info-outline` e o botão desligado pelo tempo que a API mandar; depois volta | "Muitas tentativas. Espere 5 minutos e tente de novo." (o número vem da API) |
| sem rede | faixa de erro e o botão "Tentar de novo" volta a ser "Entrar" | "Não foi possível falar com o servidor. Confira a conexão e tente de novo." |
| erro do servidor (`5xx`) | faixa de erro | "Algo deu errado do nosso lado. Tente de novo mais tarde." |
| acesso expirado (veio de outra tela) | faixa neutra no alto, `info-outline` | "Seu acesso expirou. Entre de novo." |
| saiu de propósito | nada: a tela abre limpa | |

**Regra de segurança no texto:** a faixa de `401` é **a mesma** para e-mail que não existe e para senha errada. Nunca "esse e-mail
não está cadastrado" nem "senha errada". Também a mesma para uma conta desativada (decisão 3 abaixo).

## Sair
Onde fica: no cabeçalho das telas principais (evolução dos tiros e caixa do dia), um **botão de texto "Sair"** com o ícone
`logout`, alvo 48, no canto oposto ao "Voltar". Nas telas internas (treino, check-in) não aparece: "Voltar" basta.

```
┌ Sair do app? ────────────────────┐   diálogo, fonte.titulo-secao
│ Você vai precisar entrar de novo │   fonte.corpo
│ com o e-mail e a senha.          │
│ [   Cancelar   ]  [    Sair    ] │   "Cancelar" primário; "Sair" secundário
└──────────────────────────────────┘
```
- **"Cancelar" é o botão principal** (a saída por engano custa digitar a senha de novo; o contrário é raro).
- Ao confirmar: o app **apaga o que guardou no aparelho** (o acesso e o endereço lembrado), avisa a API (para o acesso deixar de
  valer) e vai a `/entrar` com a tela limpa. O aviso à API é feito sem esperar: **se a rede falhar, a pessoa sai mesmo assim** no
  aparelho (o acesso apagado lá já impede o uso). Anúncio para leitor de tela: "Você saiu."
- Quem está no meio de um check-in com texto digitado: o texto não é guardado (regra do [[design/telas/checkin]]), então o
  diálogo diz a verdade e **não** avisa de rascunho.
- Quem quiser trocar a senha acha "Trocar senha" na mesma área do cabeçalho (menu "Conta", com "Trocar senha" e "Sair").

## Acesso expirado
O acesso tem prazo (a API decide qual). Quando qualquer chamada volta `401` com a pessoa usando o app:
1. O app **guarda o endereço atual** (só o caminho) e limpa o acesso do aparelho.
2. Leva a `/entrar` com a faixa "Seu acesso expirou. Entre de novo."
3. Depois de entrar, volta ao endereço guardado. Se a conta agora for de outro papel (o professor entrou onde o atleta estava), vai
   ao início do próprio papel.

Sem diálogo no meio da tela e sem perder nada que o app já tenha salvo: o que estava só digitado (por exemplo uma observação do
check-in não enviada) **se perde**, porque o app não guarda rascunho. O texto da faixa é o mesmo em toda a tela de entrada.

### Erros de acesso depois de entrar (não são "expirado")
| o que a API devolve | o que a tela mostra |
|---|---|
| `401` | Acesso expirado (acima) |
| `404` em recurso do próprio dado | o estado de erro que a tela já tem ("Treino não encontrado") |
| `404` em recurso de outro atleta ou de aluno sem consentimento | **o mesmo** "não encontrado" (a API responde `404` de propósito, para não dizer que existe; ver [[design/telas/caixa-do-dia]]) |
| `403` | não esperado; se vier, "Você não tem acesso a esta tela." com botão "Voltar" |
| rede ou `5xx` | os estados de erro que cada tela já tem |

## Abrir o app (carregando o acesso)
Ao abrir, antes de mostrar qualquer tela, o app olha se há um acesso guardado e pergunta à API quem é a pessoa (`GET /eu`).
Durante isso: tela cheia no fundo `cor.fundo` com o texto "Verificando o seu acesso..." (esqueleto não, é um instante). Resultados:
- **Há acesso e a API confirma:** abre a tela do papel (ou o endereço pedido).
- **Há acesso e a API diz `401`:** "Seu acesso expirou" na entrada.
- **Sem acesso guardado:** vai a `/entrar` limpa, sem faixa.
- **Sem rede:** tela com ícone `wifi-off` de 40, "Não foi possível falar com o servidor" e "Tentar de novo". Não manda para `/entrar` (a
  pessoa pode estar logada, só sem sinal).

## Trocar a senha
Duas ocasiões: **primeiro acesso** (a senha foi criada por quem opera, então a primeira coisa é trocá-la) e voluntária.
```
┌──────────────────────────────────┐
│ ← Voltar                         │  (some no primeiro acesso: não dá para pular)
│ Trocar a senha                   │
│ Escolha uma senha só sua.        │
│ Senha de agora                   │
│ [                            Ver]│
│ Senha nova                       │
│ [                            Ver]│
│ Pelo menos 10 caracteres.        │  fonte.legenda; dica fixa, não bloqueia por cor
│ Repita a senha nova              │
│ [                            Ver]│
│ [      Salvar a senha nova     ] │  primário, 48, desligado até os três campos terem texto
└──────────────────────────────────┘
```
| estado | texto |
|---|---|
| salvando | "Salvando..." |
| senha de agora errada (`401` ou `422`) | "A senha de agora não confere." (aqui não há o que esconder: a pessoa já entrou) |
| nova muito curta ou igual à de agora (`422`) | "A senha nova precisa de pelo menos 10 caracteres e ser diferente da de agora." |
| as duas novas diferentes (checado no app, antes de enviar) | "As duas senhas novas não são iguais." |
| salvo | "Senha trocada." e segue para o início do papel (primeiro acesso) ou volta (voluntária) |
| sem rede | "Não foi possível salvar. Tente de novo." |
- `autoComplete="new-password"` nos dois campos novos (o aparelho oferece gerar uma senha).
- Troca é **da pessoa que está dentro**. A recuperação de senha esquecida **não passa por esta tela**: é um comando de quem opera.
- O mínimo de **10 caracteres** foi aceito pelo Theo (decisão 4 abaixo); a regra final fica na ADR 0016. Sem exigir símbolo nem
  maiúscula (regra que cansa e não protege mais que o tamanho).

## Papéis e destino depois de entrar
| papel | vai para | cabeçalho |
|---|---|---|
| atleta | a evolução dos tiros dele (hoje `/`) | "Conta": Trocar senha, Consentimento ([[design/telas/consentimento]]), Sair |
| professor | a caixa do dia (`/caixa-do-dia`) | "Conta": Trocar senha, Sair |
O app **não escolhe o atleta nem o professor por configuração**: o `EXPO_PUBLIC_ATLETA_ID` e o `EXPO_PUBLIC_PROFESSOR_ID` saem e
o identificador vem da resposta de entrar. O professor **não** vê "Consentimento" (quem consente é o atleta).

## Acessibilidade
- Ordem de leitura: título, instrução, e-mail, senha, "Ver", "Entrar", ajuda para senha esquecida.
- A faixa de erro tem `accessibilityRole="alert"` e a mensagem é lida quando aparece; o foco vai para o primeiro campo com problema
  (a senha, no `401`). Erro nunca depende só da cor: tem ícone e frase.
- "Ver" é um botão com rótulo "Mostrar a senha" ou "Esconder a senha" e estado.
- Alvos de 48 nos campos e botões; contraste conforme [[design/tokens]]; `cor.erro` sobre `cor.erro-suave` já está na tabela (5,46 claro,
  6,67 escuro).
- Fonte do sistema grande (até 1,5): os campos não cortam; o botão fica dentro da rolagem, com o teclado aberto o formulário sobe.
- Foco por teclado na web: ordem natural; anel de foco `cor.foco`; Enter envia.
- Nenhum texto de erro revela se o e-mail existe.

## Lista de campos que a tela precisa da API (entrada da ADR 0016, #497, e das issues da API)
"Pedido" é o que a tela precisa; os nomes são proposta, a ADR 0016 decide. O app **não valida regra de senha nem de e-mail** além de
campo vazio e de "as duas senhas novas iguais".

| tela | quem chama | pede | recebe | observação |
|---|---|---|---|---|
| Entrar | `POST /sessao` (nome a decidir) | `email`, `senha` | `acesso` (o que o app guarda), `expira_em` (instante), `papel` (`atleta` ou `professor`), `atleta_id` ou `professor_id`, `nome` (para saudar), `troca_de_senha_obrigatoria` (booleano) | `401` com o **mesmo corpo** para e-mail inexistente, senha errada e conta desativada; `429` com `espere_s` (segundos) |
| Abrir o app | `GET /eu` | acesso | `papel`, `atleta_id` ou `professor_id`, `nome`, `expira_em`, `troca_de_senha_obrigatoria` | `401` se expirou ou foi revogado |
| Sair | `DELETE /sessao` | acesso | `204` | falha de rede não impede a saída no aparelho |
| Trocar a senha | `PUT /eu/senha` | `senha_atual`, `senha_nova` | `204` | `422` com tipo (`senha_atual_incorreta`, `senha_nova_invalida`) para o app escolher o texto; **sem** devolver a senha nem repetir o enviado |
| todas as rotas | cabeçalho de acesso | | | `401` quando expirou; `404` uniforme para dado de outro atleta ou aluno sem consentimento; nunca `403` com diferença visível |

Nada disso é dado de saúde, mas **o log do servidor não grava e-mail, senha nem acesso** (ADR 0016).

## Decisões de contrato (Theo, 17/11)
Comentário do Theo no PR #512; entram na ADR 0016 (#497). Todas como a Lia recomendou.
1. **Onde guardar o acesso:** no cofre do aparelho (Expo) e em `sessionStorage` na web, enviado em cabeçalho, sem cookie.
2. **Papéis:** um papel por conta no piloto (quem é professor e atleta usa duas contas).
3. **Conta desativada:** responde o **mesmo** `401` do e-mail inexistente e da senha errada.
4. **Senha:** mínimo de 10 caracteres, sem outras regras. A senha provisória do operador **obriga a troca** no primeiro acesso
   (`troca_de_senha_obrigatoria`); a tela "Trocar a senha" **fica no piloto**.
5. **Prazo do acesso:** **30 dias**; **sair e trocar a senha invalidam o acesso no servidor** (o acesso guardado em outro aparelho
   também deixa de valer, e esse aparelho vê "Seu acesso expirou. Entre de novo.").
6. **Limite de tentativas:** `429` com `espere_s`; o texto diz o tempo.
