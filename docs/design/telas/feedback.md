---
tipo: design
status: rascunho
dono: lia
atualizado: 2026-11-14
links: [[design/guia-visual]], [[design/tokens]], [[design/telas/treino]], [[design/telas/checkin]], [[produto/plano-mvp-execucao]], [[produto/roadmap]], [[decisoes/0012-check-in-pos-treino]], [[modulos/mobile]], [[glossario]]
---
# Tela: cartão "Feedback" na tela de um treino

Spec da issue #329 (Meta 9), antes da implementação (#330, do Rafa). Alinhada à ADR 0013 (#322, PR #340, modelo aprovado pelo Theo em 10/11), seção "Forma do campo `feedback`", e ao plano
([[produto/plano-mvp-execucao]], seção 4.4). O contrato fino sai na #328. Todos os dados e textos de exemplo são
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

**Quando o cartão aparece** (regra pelo que o `GET` da atividade manda):
| situação | cartão "Feedback" |
|---|---|
| `feedback: null` (atividade não elegível: `multiesporte_pai`, `troca`) | **não aparece**, como o cartão "Check-in" |
| a API não manda o campo `feedback` (versão antiga) | **não aparece** |
| todos os outros casos | aparece, num dos estados abaixo |

## Dados
Do `GET /atletas/{id}/atividades/{id}`, pelo cliente gerado, campo `feedback` (adendo da ADR 0004, #328). Forma fixada na ADR 0013:
`null` para atividade não elegível; senão, cinco estados.

| campo | valores | na tela |
|---|---|---|
| `feedback.estado` | `pronto`, `sem_checkin`, `pendente`, `desatualizado`, `indisponivel` | escolhe o miolo do cartão |
| `feedback.texto` | texto de 3 a 5 linhas, só em `pronto` | corpo do cartão, **como veio** |
| `feedback.origem` | só em `pronto`: `automatico` ou `teste` (provedor falso) | linha de origem; `teste` ganha o selo "Texto de teste" |
| `feedback.mensagem` | frase pronta, escrita pela API, em `sem_checkin`, `pendente`, `desatualizado` e `indisponivel` | miolo dos estados sem texto, **como veio** |
| `feedback.checkin_aberto` | só em `sem_checkin`; falso = prazo vencido | com botão ou sem botão |
| `feedback.motivo` | só em `indisponivel`; código fechado | **o app não mostra** nem usa para escolher o desenho |

O app **não** gera, não corta, não reformata e não confere o texto: as checagens (número no pacote, linguagem proibida)
são do backend. O app mostra `texto` como veio, preservando parágrafos. Não calcula `desatualizado` nem `sem_checkin`:
lê o `estado`. A frase vem pronta da API (como `carga_pse.texto`) e o cartão a mostra como veio; as frases desta nota
são só o **texto de reserva do app**, para o caso de a `mensagem` faltar. A API pode variar a frase por `motivo` sem criar
estado (por exemplo, "sem provedor", ou a noite que chegou em `desatualizado`, #396); o cartão só mostra a `mensagem`. O texto de reserva do app segue sendo o do check-in.

O app **não** mostra: o `motivo`, o motivo técnico da reprovação, nome do provedor ou do modelo, versão do pacote, nada do pacote de
fatos. O app **não guarda** o texto: nem em log, nem em armazenamento local, nem em URL, nem em cache do navegador além
do da própria requisição (é dado de saúde, [[decisoes/0012-check-in-pos-treino]], item 5).

## Hierarquia da informação
1. O texto do feedback (quando existe), em `fonte.corpo`, `cor.texto`: é o que o atleta veio ler.
2. A situação (quando não há texto): uma frase curta e, se houver, a **ação** (fazer o check-in, atualizar).
3. A origem: "Gerado automaticamente..." (ou, com `origem = teste`, o selo "Texto de teste" e a frase de teste), em `fonte.legenda`, `cor.texto-2`, no pé do cartão. Discreta, mas sempre
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
- **Selo de teste (`origem = teste`).** Texto do provedor falso, nunca deve parecer um feedback de verdade. Ao lado do
  título entra um selo **só de texto**, "Texto de teste", em `fonte.rotulo`, `cor.texto`, fundo `cor.superficie-2`, `raio.pilula`,
  padding `espaco.1` por `espaco.3`, sem ícone e sem cor de estado (par `cor.texto` sobre `cor.superficie-2`: 14,08 claro e
  12,28 escuro). A linha de origem vira "Texto de teste, gerado sem o provedor de verdade. Não é um feedback de verdade."
  O leitor de tela lê o selo logo depois do título ("Feedback, texto de teste"). Só aparece em ambiente de teste; o atleta
  de verdade nunca o vê.
```
┌ Feedback ──────── [Texto de teste]┐
│ (texto)                          │
│ Texto de teste, gerado sem o     │
│ provedor de verdade. Não é um    │
│ feedback de verdade.             │
└──────────────────────────────────┘
```

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
| **pronto** (`pronto`, `origem = automatico`) | o texto e a linha de origem | texto da API (3 a 5 linhas) e "Gerado automaticamente a partir dos dados deste treino e do seu check-in." |
| **pronto de teste** (`pronto`, `origem = teste`) | o mesmo, mais o selo de texto "Texto de teste" ao lado do título e a origem trocada | selo "Texto de teste" e "Texto de teste, gerado sem o provedor de verdade. Não é um feedback de verdade." |
| **sem check-in** (`sem_checkin`, `checkin_aberto` verdadeiro) | ícone `assignment`, a `mensagem` e o botão secundário "Fazer check-in" (abre `/checkin/<id>`) | "Faça o check-in para ver o feedback." |
| **sem check-in, prazo vencido** (`sem_checkin`, `checkin_aberto` falso) | ícone `info-outline` e a `mensagem`, **sem botão** | "O prazo do check-in deste treino acabou, então ele fica sem feedback." (reserva; a ADR 0013 só fixa a frase do caso com prazo aberto) |
| **pendente** (`pendente`) | ícone `info-outline`, a `mensagem` e o botão de texto "Atualizar" (`refresh`) | "O feedback deste treino ainda não foi gerado. Toque em Atualizar para ver se já está pronto." |
| **desatualizado** (`desatualizado`) | ícone `info-outline` e a `mensagem`; a API **não devolve** o texto antigo; botão de texto "Atualizar" | "Você editou o check-in. O feedback será refeito." (check-in editado, versão do pacote nova, ou os dois com a noite) ou, só quando a noite do treino chegou ou mudou, "Os dados da noite anterior foram atualizados. O feedback será refeito." (#396, frase da Lia; cobre a noite nova e a corrigida pelo Garmin) |
| **indisponível** (`indisponivel`, para texto reprovado, provedor fora ou limite de chamadas) | ícone `info-outline` e a `mensagem`; **nunca** o texto reprovado nem o `motivo` | "Ainda não foi possível gerar o feedback deste treino. Uma nova tentativa será feita mais tarde." |
| **indisponível, sem provedor** (`indisponivel`, `motivo = provedor_nao_configurado`) | o mesmo cartão, só a `mensagem` (a ADR 0013 permite uma frase própria para esse motivo); o app **não** olha o `motivo` | "O feedback automático não está ligado neste app." |
| `feedback: null` ou sem o campo | o cartão não aparece | |

Detalhes de cada estado:
- **Pendente.** Tem check-in e o `worker.gerar_feedback` ainda não rodou. **O feedback nunca é gerado no `PUT` do check-in**
  (ADR 0013, item 2): no piloto local o `pendente` **dura até alguém rodar o comando**. Por isso a frase não promete
  ("daqui a pouco") nem diz que está "sendo preparado": diz só que ainda não foi gerado. Sem esqueleto nem indicador
  girando (prometeriam que o texto está para aparecer). "Atualizar" busca a atividade de novo e o leitor de tela fala o
  resultado. Sem busca automática.
- **Desatualizado.** Editar o check-in (ou subir a versão dos fatos) marca o feedback, e a noite do treino que chega ou muda (#396) também; o worker o refaz. A `mensagem` diz qual foi o motivo: a do check-in vale quando ele mudou (sozinho ou junto com a noite), a da noite só quando foi a noite. A API não devolve o
  texto antigo, que poderia contradizer o check-in novo. O app não tem o que esconder.
- **Indisponível.** Sem texto de reserva escrito por regra (decisão 8 do Angelo); a nova tentativa é do `worker.gerar_feedback`.
  Texto reprovado e provedor fora têm a mesma frase: o atleta não precisa do motivo e o texto reprovado **nunca** chega ao app.
  O `motivo` é um código para quem cuida do app: o app não o mostra nem escolhe ícone ou botão por ele. Sem "Tentar de novo":
  o app não gera.
- **Sem provedor.** É um `motivo` de `indisponivel`, não um estado. Se a API mandar uma `mensagem` própria, o cartão só mostra a
  mensagem. A frase não pede ação ao atleta: quem resolve é quem cuida do app.
- **Linha de base "aprendendo", treino sem tipo, sem carga.** Não há estado para isso: o feedback sai, e o texto traz a frase
  ("Ainda aprendendo o seu normal...", "Sem comparação..."). O cartão não muda.
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
nos casos da tabela de estados (um por atividade, incluindo `origem = teste` e `indisponivel` com e sem a frase de provedor desligado), mais uma com `feedback: null`; e estados forçados pelo
`EXPO_PUBLIC_ATLETA_ID`, como na semana-padrão. Uma captura por estado, 390 de largura, **claro e escuro**; na web larga
(900), o estado pronto e o sem check-in. Revisão da Lia no PR do Rafa com essas capturas.

## O que muda em relação ao app de hoje
| hoje | proposta | issue |
|---|---|---|
| a tela do treino acaba no check-in e na carga pela PSE | cartão "Feedback" logo abaixo do check-in, com 5 estados da API e 9 variantes | #330 |
| nenhum texto escrito pelo app | texto gerado automaticamente, com a origem dita no cartão | #330 |
| `feedback` não existe no `GET` da atividade | campo `feedback` (ADR 0013): `null` ou cinco estados | #328 |

## Dúvidas de desenho
As dúvidas 1 a 6 da primeira versão foram **respondidas pela ADR 0013** (modelo aprovado pelo Theo em 10/11): forma do campo
`feedback`, frase pronta na API, geração só pelo worker, texto antigo não devolvido, `indisponivel` único, sem estado
"sem feedback possível". O que continua em aberto, para o Theo:
1. **Frase do prazo vencido.** A ADR 0013 fixa a `mensagem` de `sem_checkin` só com prazo aberto. A API manda uma frase própria
   quando `checkin_aberto` é falso? Se não, vale a de reserva desta nota ("O prazo do check-in deste treino acabou, então ele
   fica sem feedback.").
2. **Frase do `pendente`.** A ADR não fixa a frase. Proponho "O feedback deste treino ainda não foi gerado. Toque em Atualizar
   para ver se já está pronto." Se o `pendente` longo incomodar o Angelo no piloto local (ADR, item 9), a alternativa é o
   gatilho de fundo, não texto.
3. **Selo de teste.** "Texto de teste" no título e frase de origem trocada, como acima. Concorda?
4. **Ordem dos cartões.** Feedback logo abaixo do check-in e a carga pela PSE depois. Se preferir a carga colada no check-in, é
   só a ordem.
5. **Sem provedor com atletas reais.** Hoje o cartão mostra a frase. Quando houver atletas de verdade, esconder? Hoje mostro,
   para quem cuida do app saber por que está vazio.
6. **Selo de origem sem ícone.** Sem ícone de "inteligência"; a origem é texto. Se quiser ícone, eu proponho e atualizo
   [[design/tokens]].
7. **Sem "gostei" e sem botão de copiar.** Confirmo que ficam fora da Meta 9.
