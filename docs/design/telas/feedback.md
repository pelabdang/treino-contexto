---
tipo: design
status: rascunho
dono: lia
atualizado: 2026-11-10
links: [[design/guia-visual]], [[design/tokens]], [[design/telas/treino]], [[design/telas/checkin]], [[produto/plano-mvp-execucao]], [[produto/roadmap]], [[decisoes/0012-check-in-pos-treino]], [[modulos/mobile]], [[glossario]]
---
# Tela: cartão "Feedback" na tela de um treino

Spec da issue #329 (Meta 9), antes da implementação (#330, do Rafa). **Rascunho pelo roteiro e pelo plano**
([[produto/plano-mvp-execucao]], seção 4.4): a ADR 0013 (#322, do Caio) ainda está sendo escrita. O que depende dela
vem marcado com **(ADR 0013)** e a lista está em "Dúvidas de desenho". Todos os dados e textos de exemplo são
**sintéticos**. Nada em `apps/mobile/` muda nesta nota.

Esboço dos dois temas, em celular de 360 por 640: ![[design/telas/feedback-pronto.svg]]
(arquivo `docs/design/telas/feedback-pronto.svg`; o estado "pronto" em claro e escuro). Os outros estados usam
o mesmo cartão e só trocam o miolo. Nenhuma cor nova e nenhum ícone novo: tudo vem de [[design/tokens]].

## Objetivo
Depois do check-in, o atleta lê **3 a 5 linhas** sobre o treino que acabou de fazer: como foi em relação ao normal
dele para aquele tipo de treino, o que o check-in e o contexto (clima, carga) dizem, e uma observação positiva. O texto é
**escrito pelo app**, em texto (sem áudio), e o cartão deixa claro que foi gerado automaticamente. A tela responde:
"o que esse treino quer dizer para mim?".

Quem calcula é o código; o texto só redige o que o código já calculou. O cartão **não mostra número novo**, não
dá nota e não afirma causa. O professor também pode abrir a tela (Meta 10), então o cartão não fala em nome de ninguém.

O texto tem um **tom** (frases curtas, segunda pessoa, sem diagnóstico, culpa nem promessa). O tom é
da ADR 0013 e do Angelo; esta nota só desenha o cartão.

## Onde fica
Na tela de um treino ([[design/telas/treino]], rota `/treino/<atividade_id>`), **logo abaixo do cartão "Check-in"**, e
antes de "Carga pela PSE" e de "Clima":

```
dados do treino  >  Check-in  >  Feedback  >  Carga pela PSE  >  Clima
```

O feedback nasce do check-in; por isso fica colado nele. A carga pela PSE é um dado e fica depois do texto.
Sem rota nova, sem tela nova, sem entrada na evolução.

**Quando o cartão aparece** (regra pelo que o `GET` da atividade manda; **(ADR 0013)** para os nomes dos campos):
| situação | cartão "Feedback" |
|---|---|
| a atividade não aceita check-in (`multiesporte_pai`, `troca`) | **não aparece**, como o cartão "Check-in" |
| a API não manda o campo `feedback` (versão antiga) | **não aparece** |
| todos os outros casos | aparece, num dos estados abaixo |

## Dados
Do `GET /atletas/{id}/atividades/{id}`, pelo cliente gerado, campo `feedback` (adendo da ADR 0004, #328). **Proposta
de forma, a confirmar com o Theo e com a ADR 0013:**

| campo | valores | na tela |
|---|---|---|
| `feedback.estado` | `pronto`, `sem_checkin`, `pendente`, `desatualizado`, `reprovado`, `sem_provedor`, `sem_fatos` | escolhe o miolo do cartão |
| `feedback.texto` | texto de 3 a 5 linhas, só com `estado = pronto` | corpo do cartão, **como veio** |
| `feedback.mensagem` | frase pronta em português para os estados sem texto | miolo dos estados sem feedback |
| `feedback.origem` | por exemplo `automatico` | linha discreta "Gerado automaticamente" |

O app **não** gera, não corta, não reformata e não confere o texto: as checagens (número no pacote, linguagem proibida)
são do backend. O app mostra `texto` como veio, preservando parágrafos. Não calcula `desatualizado` nem `sem_checkin`:
lê o `estado`. As frases fixas desta nota são o **texto de reserva do app** para o caso de a `mensagem` não vir; se a API
mandar a frase pronta (como faz com `carga_pse.texto`), vale a da API. **(ADR 0013)** Quem escreve a frase de cada estado?

O app **não** mostra: motivo técnico da reprovação, nome do provedor ou do modelo, versão do pacote, nada do pacote de
fatos. O app **não guarda** o texto: nem em log, nem em armazenamento local, nem em URL, nem em cache do navegador além
do da própria requisição (é dado de saúde, [[decisoes/0012-check-in-pos-treino]], item 5).

## Hierarquia da informação
1. O texto do feedback (quando existe), em `fonte.corpo`, `cor.texto`: é o que o atleta veio ler.
2. A situação (quando não há texto): uma frase curta e, se houver, a **ação** (fazer o check-in, atualizar).
3. A origem: "Gerado automaticamente...", em `fonte.legenda`, `cor.texto-2`, no pé do cartão. Discreta, mas sempre
   presente quando há texto.

O título do cartão é só "Feedback" (`fonte.titulo-secao`). Sem selo, sem chip, sem ícone de "inteligência" no título.

## Layout
Celular de 360, margem 16. Cartão como em [[design/guia-visual]] ("Cartão"): `cor.superficie`, borda 1 em `cor.borda`,
`raio.grande`, padding `espaco.4`, espaço de `espaco.5` entre cartões.

### Pronto
```
┌ Feedback ────────────────────────┐  fonte.titulo-secao
│ Você correu 10,00 km em 5:12     │  fonte.corpo, cor.texto
│ min/km, perto do seu normal para │  (3 a 5 linhas de texto; no
│ um treino deste tipo. Você       │  celular de 360 pode passar
│ marcou esforço 5 (difícil) e     │  de 5 linhas visuais; o cartão
│ sensação boa. Fez 24,3 °C.       │  cresce, sem cortar)
│ Bom treino.                      │
│ ──────────────────────────────── │  divisória 1, cor.borda
│ Gerado automaticamente a partir  │  fonte.legenda, cor.texto-2
│ dos dados deste treino e do seu  │
│ check-in.                        │
└──────────────────────────────────┘
```
- Exemplo **sintético e ilustrativo**: o tom final é o da ADR 0013. Os números do exemplo são os dos outros esboços
  ([[design/telas/treino]], [[design/telas/checkin]]).
- Texto alinhado à esquerda, sem justificar, sem negrito dentro do texto e sem destaque de palavra por cor. Nenhuma
  palavra é "marcada" por ser boa, ruim ou preocupante.
- Largura de leitura: no celular, a do cartão; na web larga (a partir de 600), a coluna de até 720 do resto da tela, com o
  texto limitado a 640 para a linha não passar de uns 80 caracteres.
- O texto é selecionável (`selectable`; na web, o padrão), para o atleta poder copiar se quiser. Sem botão de compartilhar
  nem de copiar nesta meta.
- Sem "joinha", sem botão "gostei" e sem pedido de nota (fora da meta).

### Os estados sem texto
Mesma moldura do cartão. O miolo é **uma frase** (`fonte.corpo`, `cor.texto`) com um ícone de `icone.medio` ao lado,
em `cor.texto-2`, e a ação, se houver, num botão **secundário ou de texto** (nunca primário: o primário da tela é o
"Fazer check-in" do cartão de cima, ou nenhum). O fundo do cartão **não muda**: nada de fundo de alerta, de erro ou de sucesso.
```
┌ Feedback ────────────────────────┐
│ (assignment) Faça o check-in     │  ícone cor.texto-2 + fonte.corpo
│ para ver o feedback.             │
│ [       Fazer check-in         ] │  secundário, 48
└──────────────────────────────────┘
```
Os ícones são do grupo neutro (`assignment`, `info-outline`, `refresh`): nunca `warning-amber` nem `error-outline`,
porque nenhuma destas situações é problema do atleta nem aviso de saúde.

## Estados
Segue [[design/guia-visual]], "Estados". O feedback chega **dentro** do `GET` da atividade: não há busca própria. Por isso o
cartão não tem carregando nem erro de rede (quem carrega e falha é a tela inteira, [[design/telas/treino]]), e o conteúdo que
já está na tela não some quando "Atualizar" busca de novo.

| estado (`feedback.estado`) | o que aparece | texto |
|---|---|---|
| **pronto** (`pronto`) | o texto e a linha de origem | texto da API (3 a 5 linhas) e "Gerado automaticamente a partir dos dados deste treino e do seu check-in." |
| **sem check-in** (`sem_checkin`) | ícone `assignment`, frase e o botão secundário "Fazer check-in" (abre `/checkin/<id>`) | "Faça o check-in para ver o feedback." |
| **sem check-in, prazo vencido** (`sem_checkin` com `checkin_aberto` falso) | ícone `info-outline` e a frase, **sem botão** | "O prazo do check-in deste treino acabou, então ele fica sem feedback." |
| **gerando ou pendente** (`pendente`) | ícone `info-outline`, frase e o botão de texto "Atualizar" (`refresh`) | "O feedback deste treino ainda está sendo preparado. Volte daqui a pouco ou toque em Atualizar." |
| **desatualizado** (`desatualizado`) | ícone `info-outline` e a frase; **o texto antigo não aparece**; botão de texto "Atualizar" | "Você editou o check-in. O feedback será refeito." |
| **não foi possível gerar** (`reprovado`: texto reprovado nas checagens ou provedor fora) | ícone `info-outline` e a frase; **nunca** o texto reprovado, nem o motivo técnico | "Ainda não foi possível gerar o feedback deste treino. Uma nova tentativa será feita mais tarde." |
| **sem provedor** (`sem_provedor`) | ícone `info-outline` e a frase, sem botão | "O feedback automático não está ligado neste app." |
| **sem feedback possível** (`sem_fatos`) **(ADR 0013)** | ícone `info-outline` e a frase, sem botão | "Ainda não há dados para escrever o feedback deste treino." |
| sem o campo `feedback` | o cartão não aparece | |

Detalhes de cada estado:
- **Pendente.** É o caso de quem acabou de salvar o check-in e o feedback ainda não foi escrito (**(ADR 0013)** quando é gerado:
  no `PUT` do check-in ou só pelo `worker.gerar_feedback`). Como o app **não sabe** quanto falta, o estado **não usa
  esqueleto nem indicador girando** (isso prometeria que o texto está para aparecer). "Atualizar" busca a atividade de novo
  e o leitor de tela fala o resultado. Sem busca automática repetida nesta versão (**(ADR 0013)** se o Theo quiser).
- **Desatualizado.** Editar o check-in marca o feedback e ele é refeito (decisão 5 do Angelo, 10/11). Esconder o texto
  antigo evita mostrar uma frase que contradiz o check-in novo (por exemplo, o esforço de antes). **A decidir com o Theo**
  se a API devolve o texto antigo; se devolver, o app ainda assim não o mostra.
- **Não foi possível gerar.** Decisão 8 do Angelo: sem texto de reserva escrito por regra; a nova tentativa é do
  `worker.gerar_feedback`. A frase é a mesma para texto reprovado e para provedor fora: o atleta não precisa do motivo, e
  o texto reprovado **nunca** chega ao app. Sem "Tentar de novo": o app não gera.
- **Sem provedor.** Quem pode resolver é quem cuida do app, não o atleta. Por isso a frase não pede ação.
- **Sem feedback possível.** Só existe se a ADR separar esse caso do `reprovado` (por exemplo, atividade sem tipo e sem
  linha de base). Se a ADR disser que o pacote sempre existe com check-in, o estado some (o "aprendendo" da linha de base
  entra no texto, não impede o feedback).
- **Treino com dor no check-in.** O cartão **não muda** por causa disso: sem destaque, sem ícone, sem cor e sem botão
  diferente. Se o texto da API tiver a frase neutra da decisão 7 ("Você registrou dor neste treino."), ela aparece no meio do
  texto, igual às outras frases. O alerta sensível é do professor (Meta 10).

## Sem juízo de valor visual
- O cartão tem **uma só aparência** para qualquer texto: ritmo acima ou abaixo do normal, esforço alto ou baixo, "fora do
  normal" na linha de base. Nada de verde, vermelho, seta para cima ou para baixo, medalha, estrela ou termômetro.
- `cor.sucesso`, `cor.alerta` e `cor.erro` **não são usadas** neste cartão. Os estados sem texto são neutros porque
  ausência de feedback não é erro do atleta.
- Nenhum número do texto ganha destaque tipográfico (nem `fonte.numero-destaque`): o número do treino já está no cartão de
  dados, e aqui ele é parte da frase.

## Textos (resumo)
Título: "Feedback".
Origem (só com texto): "Gerado automaticamente a partir dos dados deste treino e do seu check-in."
Botões: "Fazer check-in", "Atualizar".
Frases dos estados: ver a tabela acima. Em todas, frases curtas, sem "erro", sem "falha", sem código, sem culpar o
atleta, sem nome de provedor e sem a palavra "inteligência". A expressão para o texto automático é **"gerado
automaticamente"**.
Rótulo de acessibilidade do cartão: "Feedback do treino".

## Acessibilidade
- **Contraste AA em todos os pares, nos dois temas**, sem cor nova ([[design/tokens]], tabela "Contraste"):
  | uso no cartão | par | claro | escuro |
  |---|---|---|---|
  | texto do feedback | `cor.texto` sobre `cor.superficie` | 16,94 | 14,09 |
  | origem, ícones, frases sem texto | `cor.texto-2` sobre `cor.superficie` | 7,92 | 8,44 |
  | botão secundário e de texto | `cor.destaque` sobre `cor.superficie` | 6,36 | 8,21 |
  | contorno do botão secundário | `cor.borda-forte` sobre `cor.superficie` | 4,29 | 4,51 |
  | anel de foco (web) | `cor.foco` sobre `cor.superficie` | 6,36 | 8,21 |
- **Nada só pela cor.** Os estados se distinguem pelo **texto** (a frase) e pelo ícone; a cor é a mesma em todos.
- **Alvos.** Botões de 48 (`botao.altura`); "Atualizar", de texto, também com alvo de 48 de altura.
- **Tamanho de fonte.** `allowFontScaling` ligado, **sem** `maxFontSizeMultiplier` no texto do feedback nem na origem: o cartão
  cresce com a fonte do sistema e a tela rola. Com fonte no máximo, os botões ficam abaixo do texto, em largura total.
  Texto de 16; a origem é `fonte.legenda` (13/18), nada abaixo disso.
- **Ao ar livre.** Texto principal em `cor.texto` (contraste acima de 14); a origem em `cor.texto-2`, nunca em cinza claro;
  nada de texto sobre imagem ou sobre cor de estado.
- **Leitor de tela.**
  - O título é cabeçalho (`accessibilityRole="header"`; na web, `h2`). O cartão é lido na ordem: "Feedback", o texto **inteiro
    como um item só** (não por linha), a origem. Ícone decorativo fora da leitura (`accessible={false}`), porque a frase já
    diz tudo.
  - Estados sem texto: a frase é lida e depois o botão. Como o cartão "Check-in" logo acima também tem "Fazer check-in",
    o botão do feedback leva o rótulo "Fazer check-in para ver o feedback".
  - Depois de "Atualizar", o app anuncia o novo estado (`accessibilityLiveRegion="polite"` no Android; anúncio no iOS e na
    web): "Feedback pronto." ou "O feedback ainda não está pronto." O foco não pula.
  - Ao salvar o check-in e voltar ao treino, o foco vai ao título da tela, como hoje; o cartão não rouba o foco.
- **Teclado (web).** Tab chega nos botões do cartão, com anel de foco de 2 em `cor.foco`; Enter ativa.
- **Movimento.** O cartão não anima e não tem esqueleto próprio: "reduzir movimento" não muda nada nele.

## Privacidade no desenho
O feedback é **dado de saúde derivado** (usa PSE, sensação e atalhos do check-in).
- Nenhuma captura, esboço ou exemplo com texto real. O texto desta nota é sintético e ilustrativo.
- O app não escreve o texto em log, URL, parâmetro de rota nem armazenamento local; não há rascunho nem cache próprio.
- Capturas e testes do Rafa: só com a API falsa e **texto marcador sintético** (por exemplo "Texto de exemplo do feedback.").
- Apagar o check-in apaga o feedback (roteiro, #327): ao voltar ao treino, o cartão vira "sem check-in".

## Como gerar capturas sintéticas
Como em [[modulos/mobile]] (`npm run api-falsa`): a API falsa precisa devolver o campo `feedback` em atividades sintéticas
nos oito casos da tabela de estados (um por atividade), mais uma sem o campo; e estados forçados pelo
`EXPO_PUBLIC_ATLETA_ID`, como na semana-padrão. Uma captura por estado, 390 de largura, **claro e escuro**; na web larga
(900), o estado pronto e o sem check-in. Revisão da Lia no PR do Rafa com essas capturas.

## O que muda em relação ao app de hoje
| hoje | proposta | issue |
|---|---|---|
| a tela do treino acaba no check-in e na carga pela PSE | cartão "Feedback" logo abaixo do check-in, com 8 estados | #330 |
| nenhum texto escrito pelo app | texto gerado automaticamente, com a origem dita no cartão | #330 |
| `feedback` não existe no `GET` da atividade | campo `feedback` com `estado`, `texto` e `mensagem` | #328 |

## Dúvidas de desenho
Para o Theo, antes da tela (#330). As marcadas **(ADR 0013)** dependem da ADR em escrita pelo Caio.
1. **Nomes e forma do campo `feedback`.** Proponho `estado` (sete valores), `texto`, `mensagem` e `origem`. Está bom, ou a
   #328 define outro desenho? **(ADR 0013)**
2. **Quem escreve a frase dos estados sem texto?** Proponho a API mandar `mensagem` pronta (como `carga_pse.texto`) e o app
   ter as frases desta nota só como reserva. Ou o app escreve todas?
3. **Quando o feedback é gerado.** No `PUT` do check-in (a tela volta ao treino e já o encontra, ou em "pendente") ou só pelo
   `worker.gerar_feedback`? No piloto local, "pendente" pode durar até alguém rodar o worker. Isso decide se "Atualizar"
   basta ou se precisamos de busca automática. **(ADR 0013)**
4. **Desatualizado: a API devolve o texto antigo?** Eu escondo mesmo assim (pode contradizer o check-in novo). Se o Theo
   preferir mostrá-lo com o aviso, volta para mim.
5. **`reprovado`: um estado ou dois?** Texto reprovado e provedor fora têm a mesma frase para o atleta. Se a API separar em dois
   estados, o app trata os dois como o mesmo cartão; só confirmo que **nenhum motivo técnico** vai ao app.
6. **Sem linha de base.** O roteiro lista fixtures com linha de base "aprendendo" e "fora", o que indica que o feedback sai
   mesmo assim, e o `sem_fatos` seria raro. A ADR prevê treino **sem feedback possível**? Se não, tiro esse estado.
   **(ADR 0013)**
7. **Ordem dos cartões.** Coloquei o feedback **logo abaixo do check-in** (e a carga pela PSE depois). Se o Theo preferir a
   carga pela PSE colada no check-in, o feedback desce um lugar; é só a ordem.
8. **De onde vem o texto.** A origem diz só "Gerado automaticamente a partir dos dados deste treino e do seu check-in." Sem nome
   do provedor nem do modelo. Concorda? Quando o professor existir (Meta 10), a frase pode ganhar uma variante, mas
   hoje o texto não tem o nome dele (decisão 6).
9. **Sem provedor numa instalação de atleta.** A frase "não está ligado neste app" faz sentido no piloto local. Quando houver
   atletas de verdade, vale esconder o cartão nesse caso? Hoje mostro, para quem cuida do app saber por que está vazio.
10. **Ícone de origem.** Não usei ícone de "inteligência" (como `auto-awesome`) para não dar peso ao selo nem criar
    ícone novo; a origem é texto. Se o Theo quiser um ícone, a Lia propõe um e atualiza [[design/tokens]].
11. **Sem "gostei" e sem botão de copiar.** Confirmo que ficam fora da Meta 9.
