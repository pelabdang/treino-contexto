---
tipo: design
status: rascunho
dono: lia
atualizado: 2026-11-28
links: [[decisoes/0017-chat-do-atleta]], [[decisoes/0004-contrato-tela-evolucao]], [[decisoes/0016-login-e-deploy-do-piloto]], [[design/identidade-visual-v3]], [[design/tokens]], [[design/telas/evolucao-v1]], [[design/telas/treino]], [[design/telas/inicio-v4]], [[modulos/mobile]]
---
# Tela: chat "Pergunte ao seu treino" (spec da #599, Meta 14)

Spec antes da implementação (Rafa). Contrato: [[decisoes/0017-chat-do-atleta]] e o adendo 16 da [[decisoes/0004-contrato-tela-evolucao]] (PR #618, da Duda;
ainda **proposto**). Identidade v3 ([[design/identidade-visual-v3]], cores de [[design/tokens]]). **Nada aqui muda o app** até o Rafa implementar.
Atleta e perguntas **sintéticos**. A regra de sempre: **o app não calcula**; todo número e toda frase de resposta vêm prontos da API.

## Objetivo
O atleta pergunta o que quiser sobre os próprios treinos e recebe uma resposta curta, com os números certos e um atalho para o treino ou a Evolução.
A tela é **um chat simples**: o histórico da conversa, o campo de texto e, no começo, perguntas prontas.

## Onde mora (decisão proposta)
**Sem aba nova.** O chat é uma tela empilhada (voltar com "‹"), aberta pelo bloco "Pergunte ao seu treino" do Início v5 (spec da mistura, PR #601). As abas
continuam 4 (Início, Treinos, Evolução, Conta) e **somem na tela do chat**, para sobrar espaço ao teclado.
| rota | tela | como chega |
|---|---|---|
| `/chat` | conversa **nova** (começo, com perguntas prontas) | toque na caixa do Início (abre com o teclado) ou em "Nova conversa" na lista |
| `/chat/<conversa_id>` | conversa existente | toque numa linha da lista |
| `/chat/conversas` | lista de conversas | "Conversas ›" no cabeçalho do chat e ao lado do título do bloco no Início |
- **Pergunta pronta no Início:** o toque abre `/chat` e **já envia** a pergunta (estado "pensando"). Toque na caixa só abre a tela com o teclado.
- "‹" volta para onde o atleta veio. O endereço `/chat/<id>` abre direto na web.
- Ao enviar a primeira pergunta de uma conversa nova, o app chama `criarConversa`; nas seguintes, `enviarMensagem`.

## Esboços (390 px, claro e escuro)
**Começo da conversa** (perguntas prontas):
![[design/telas/chat/chat-comecar-claro.svg]]
![[design/telas/chat/chat-comecar-escuro.svg]]

**Resposta com links** ("Abrir na Evolução", "Abrir treino"):
![[design/telas/chat/chat-resposta-claro.svg]]
![[design/telas/chat/chat-resposta-escuro.svg]]

**Pensando** (até 10 s) e **espera longa** (a partir de 25 s):
![[design/telas/chat/chat-pensando-claro.svg]]
![[design/telas/chat/chat-pensando-escuro.svg]]
![[design/telas/chat/chat-pensando-longo-claro.svg]]
![[design/telas/chat/chat-pensando-longo-escuro.svg]]

**Recusa (fora do tema e pedido de mudança) e erro**:
![[design/telas/chat/chat-recusa-erro-claro.svg]]
![[design/telas/chat/chat-recusa-erro-escuro.svg]]

**Limite de perguntas** (`429`):
![[design/telas/chat/chat-limite-claro.svg]]
![[design/telas/chat/chat-limite-escuro.svg]]

**Lista de conversas** e **apagar**:
![[design/telas/chat/chat-conversas-claro.svg]]
![[design/telas/chat/chat-conversas-escuro.svg]]
![[design/telas/chat/chat-apagar-claro.svg]]
![[design/telas/chat/chat-apagar-escuro.svg]]

## Hierarquia e layout da conversa
1. **Cabeçalho** (altura 56): "‹", título "Pergunte ao seu treino" (`fonte.titulo-secao`) e "Conversas ›" (`cor.link`, alvo 44).
2. **Histórico** (rola; abre no fim): marcador de dia ("hoje"), balão da **pergunta** à direita (`cor.superficie-2`, `raio` 14) com "Você · 14:32" embaixo; **resposta** à esquerda
   em cartão (`cor.superficie`, contorno `cor.borda`, `raio.cartao` 12) com a hora e o rótulo fixo "Resposta de IA com números do seu histórico".
3. **Compositor** fixo no pé (acima do teclado): campo de 1 a 4 linhas (altura mínima 52, `raio.botao` 10, contorno `cor.borda-forte`), botão de enviar (↑, 38 por 40 visíveis,
   **alvo 44**) e, sob o campo, o aviso fixo **"A sua pergunta vai a um serviço de IA."** (exigência da ADR 0017, item 5; o texto do termo é da Nina).
- Resposta: texto simples (a API não manda Markdown, emoji nem link no texto); até 8 linhas e 900 caracteres. Os **links** vêm abaixo do texto, como botões de contorno de altura 44.
- Fonte `fonte.corpo` 16 nas respostas (o esboço mostra 14,5 só por espaço no desenho; o app usa a escala dos tokens e acompanha o tamanho do sistema).
- Mensagem nova rola o histórico até ela; o leitor de tela ouve a resposta quando chega (região "polida").

## Começo e perguntas prontas
- Título em Barlow Condensed "O que você quer saber sobre os seus treinos?" e a frase "Escreva a sua pergunta ou toque em uma destas."
- **6 perguntas prontas, fixas no app** (rótulo fixo; o texto é enviado como pergunta comum, sem cálculo): "Como foi minha semana?", "Meu pace nos treinos leves melhorou?",
  "Quanto corri neste mês?", "Como estão minha carga e minha forma?", "O que escrevi no check-in de ontem?", "Como foi meu último treino?".
  Cada linha: altura 48, contorno `cor.borda-forte`, "›". O Início v5 mostra as 3 primeiras. **Não há rota de perguntas prontas** no adendo 16, por isso a lista é do app (ver "Decisões").
- Some assim que a conversa tem a primeira pergunta. Atleta **sem treinos**: as perguntas prontas somem e a tela diz "Você ainda não tem treinos aqui. Importe o primeiro para perguntar." (o campo continua).
- Sem histórico ainda: nenhuma lista de conversas ("Nenhuma conversa ainda. Faça a sua primeira pergunta." com o botão "Nova conversa").

## Estados
| situação | `estado` da API | o que aparece | texto |
|---|---|---|---|
| enviando | (pedido em curso) | a pergunta já aparece no histórico; o campo e o ↑ ficam **desligados**; cartão "pensando" | ver "A espera" |
| respondida | `respondida` | cartão com `texto` e `links[]` | o `texto` da API, sem mexer |
| fora do tema | `recusada`, `motivo = fora_do_tema` | cartão **neutro de contorno tracejado** (não é erro) | o `texto` fixo: "Eu respondo perguntas sobre os seus treinos. Pergunte, por exemplo, sobre o seu pace, a sua carga ou como foi a sua semana." |
| pede mudança | `recusada`, `motivo = pedido_de_mudanca` | idem | "Mudar o treino é com o seu professor. Posso mostrar o que os seus treinos dizem, se isso ajudar na conversa com ele." (sem professor: só a primeira frase; **a API decide**) |
| reprovada | `reprovada` | cartão de erro (`cor.erro-suave`) | o `texto` fixo: "Não consegui responder agora. Tente de novo em instantes." e o botão **"Tentar de novo"** |
| erro do provedor | `erro` | igual à reprovada (mesma frase, **sem** o motivo na tela) | idem |
| limite | HTTP `429` | faixa de alerta (`cor.alerta-suave`) acima do compositor; campo e ↑ desligados | "Você fez 20 perguntas na última hora. Espere N min para perguntar de novo." |
| sem rede | falha de conexão | faixa neutra sobre o compositor, a pergunta **fica no campo** | "Sem conexão. Verifique a internet e tente de novo." |
| conversa não encontrada | `404` | tela de erro simples com "Voltar às conversas" | "Não encontramos esta conversa." |
- **Recusa não é erro:** contorno tracejado em cor neutra, sem ícone de alerta, sem "Tentar de novo". Quem lê vê que o chat entendeu e disse o que faz.
- **Tentar de novo** reenvia a **mesma pergunta** como mensagem nova (a pergunta que falhou continua no histórico; a API a guardou). Conta no limite de 20 por hora.
- **Limite:** o tempo "N min" vem da API (como no login, [[design/telas/entrar]] usa `espere_s`); o app **só mostra**. Se faltar `espere_s`, vale "Espere alguns minutos". Quando o tempo acaba, a faixa some e o campo volta sozinho.
- O `422` (pergunta vazia ou maior que 1000) não deve ocorrer: o ↑ fica desligado com campo vazio e o campo para em 1000 caracteres; a partir de 900, um contador "950 de 1000" aparece sob o campo.

## A espera (sem streaming, até uns 45 s)
A resposta só existe **depois das checagens**, então não há texto parcial. O desenho evita dois erros: parecer travado e prometer um progresso que não existe (**sem barra de porcentagem**).
| tempo | o que aparece |
|---|---|
| 0 a 10 s | cartão com o círculo de espera, "Consultando os seus treinos…" e três linhas de esqueleto; embaixo "Pode levar até 45 segundos." |
| 10 a 25 s | a mesma coisa; o texto muda para "Ainda consultando. Perguntas sobre vários treinos levam mais tempo." |
| 25 s em diante | o cartão vira aviso (`cor.alerta-suave`): "Está demorando mais que o normal. A resposta pode levar até 45 segundos." |
| resposta chegou | o cartão vira a resposta (mesma posição, sem pular) |
| passou do tempo | a API devolve `estado = erro` (`tempo_limite`) e vale o estado de erro; o app espera **até 60 s** antes de desistir do pedido (cliente) |
- Os tempos são do app (só trocam o texto); **o app não estima nada**. O 45 s é o limite da ADR 0017 (item 3).
- **Movimento reduzido:** o círculo fica parado e o esqueleto sem brilho; o texto muda do mesmo jeito.
- **Leitor de tela:** "Consultando os seus treinos" é anunciado uma vez; as trocas de texto são anunciadas com educação ("polida"); a resposta é anunciada quando chega. Nada de som.
- **Sair da tela:** a pergunta fica guardada. O que acontece com o pedido em curso depende da API (ver "Decisões"); o esboço da espera longa oferece "Voltar ao Início e esperar lá" só se a Duda confirmar que a resposta fica guardada.

## Links nas respostas
Vêm em `links[]` (montados pelo código; o modelo não escreve link; no máximo 5, só em `respondida`):
| `tipo` | rótulo (da API) | leva a |
|---|---|---|
| `evolucao` | "Abrir na Evolução" | [[design/telas/evolucao-v1]], com a série `serie_id` já escolhida |
| `treino` | "Abrir treino" | [[design/telas/treino]] do `atividade_id` |
- Botão de contorno, altura 44, `cor.link`, "›". Com mais de um link do mesmo tipo, o app **mostra o texto do rótulo da API** e, se vier, a data ("Abrir treino · qui 20/03"; se a API não mandar a data, só "Abrir treino").
- Voltar da Evolução ou do treino devolve à conversa, na mesma posição.
- O pedido do Theo falava em "Ver treino"; o contrato do adendo 16 diz **"Abrir treino"**. A spec segue o contrato.

## Lista de conversas e apagar
- Cabeçalho "‹ Conversas"; botão primário **"+ Nova conversa"** (48); abaixo, uma linha por conversa, da mais recente para a mais antiga (até 50; "Ver mais" não é necessário no piloto).
- Linha: o `titulo` (a primeira pergunta cortada em 80), em até 2 linhas, e a data de `atualizada_em` ("hoje, 14:32", "ontem, 20:10", "qua 19/03, 07:45"); alvo = a linha toda.
- **Apagar:** botão "⋯" em cada linha (alvo 44) abre um menu com "Apagar conversa". Em iOS e Android, **deslizar para a esquerda** é um atalho a mais, nunca o único caminho. Na web, o "⋯" é o caminho.
- **Confirmação** (diálogo): "Apagar esta conversa?" / "As perguntas e as respostas somem do app. O que já foi enviado ao serviço de IA não pode ser apagado por nós." / "Cancelar" e **"Apagar"** (`cor.erro`). Sem "desfazer" (o `DELETE` apaga de verdade). Depois, aviso curto "Conversa apagada".
- Rodapé fixo da lista: "As conversas ficam guardadas até você apagar. O seu professor não vê as suas conversas." (decisões 4 e 7 da ADR 0017).
- Erro ao apagar: aviso "Não deu para apagar. Tente de novo." e a conversa continua na lista. Erro ao carregar a lista: "Não deu para carregar as conversas." com "Tentar de novo".
- Lista vazia: "Nenhuma conversa ainda. Faça a sua primeira pergunta." e o botão "Nova conversa".

## Campos da API que a tela usa
Pelo cliente gerado do adendo 16 (#598); nada é calculado no app.
| chamada | campos usados | para quê |
|---|---|---|
| `criarConversa` (`POST /atletas/{id}/conversas`) | corpo `pergunta`; resposta `ConversaOut` (`id`, `titulo`, `mensagens[]`) | primeira pergunta |
| `enviarMensagem` (`POST .../conversas/{id}/mensagens`) | corpo `pergunta`; resposta `MensagemOut` | perguntas seguintes e "Tentar de novo" |
| `listarConversas` (`GET .../conversas?limite=`) | `conversas[]`: `id`, `titulo`, `criada_em`, `atualizada_em` | lista |
| `buscarConversa` (`GET .../conversas/{id}`) | `mensagens[]` | histórico |
| `apagarConversa` (`DELETE .../conversas/{id}`) | `204` | apagar |
| `MensagemOut` | `id`, `ordem`, `pergunta`, `estado`, `motivo`, `texto`, `links[]`, `criada_em` | balão, cartão de resposta, estado visual |
| `links[]` | `tipo`, `rotulo`, `atividade_id` ou `serie_id` | botões de link |
| `429` | `detail`, `espere_s`, cabeçalho `Retry-After` | faixa do limite |
- O app **mostra `texto` como veio** em qualquer `estado` (inclusive os textos fixos de recusa e erro). O `motivo` **não aparece** para o atleta; serve só para escolher o estilo do cartão (neutro na recusa, erro na reprovada e no erro).
- Horas de `criada_em` já vêm em `America/Sao_Paulo`; o app só as escreve no formato "14:32".

## Acessibilidade
- Alvos de 44 ou mais: ↑, "Conversas ›", linhas, "⋯", links, "Tentar de novo". Pares de cor da tabela de contraste de [[design/tokens]]; texto sobre o volt é `cor.sobre-marca`.
- **Nada só por cor:** a recusa tem contorno tracejado e a frase fixa; o erro tem texto e botão; o limite tem o título "Limite de perguntas".
- Cada mensagem é um grupo falado: "Você, 14:32: …" e "Resposta, 14:32: …, 2 links". Os links se leem como botões.
- Texto até 2x: as respostas quebram linha e o cartão cresce; o compositor cresce até 4 linhas e depois rola por dentro.
- Teclado: Enter envia na web (Shift+Enter quebra linha); no celular, o ↑ envia. Foco volta ao campo depois de uma resposta.

## Privacidade (texto para a Nina no termo)
O aviso sob o campo ("A sua pergunta vai a um serviço de IA.") e o diálogo de apagar dizem o que a ADR 0017 manda. O termo deve dizer também que o **texto livre do check-in**
pode ir ao serviço de IA quando o atleta pergunta sobre ele (decisão do Angelo de 28/11). Tudo no app em português simples; sem a palavra "Groq" na tela.

## Decisões que precisam do Angelo ou do Theo
1. **Sem aba nova para o chat** (entrada pelo Início e tela empilhada). Alternativa: aba "Perguntar" no lugar de outra. Recomendo sem aba.
2. **Perguntas prontas fixas no app** (6 frases acima), porque não há rota para elas. Alternativa: a API manda a lista (permite variar com o dado do atleta, mas exige rota e a regra de quando aparece). Recomendo fixas no piloto.
3. **Texto "Abrir treino"** (do contrato) no lugar de "Ver treino" (do pedido). Recomendo seguir o contrato.
4. **Sair da tela enquanto pensa:** a resposta fica guardada para quando o atleta voltar? Depende da API (o pedido é síncrono; se o app fechar a conexão, o servidor termina e grava?). **Pergunta para a Duda/Theo.** Se não, tiro o botão "Voltar ao Início e esperar lá".
5. **Limite em minutos:** a API manda só `espere_s`; converter em "N min" é formatação do app (como no login). Se preferirem, a API manda a frase pronta em `detail`.
6. **Primeira versão sem "Copiar resposta" e sem avaliar a resposta (👍/👎).** Dá para somar depois; sem pedido ainda.
