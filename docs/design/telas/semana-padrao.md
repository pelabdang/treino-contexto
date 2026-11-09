---
tipo: design
status: rascunho
dono: lia
atualizado: 2026-11-09
links: [[design/guia-visual]], [[design/tokens]], [[design/telas/evolucao-tiros]], [[design/telas/treino]], [[decisoes/0011-linha-de-base-e-semana-padrao]], [[modulos/mobile]], [[glossario]]
---
# Tela: semana-padrão

Spec para a issue #267, antes da implementação (o Rafa implementa depois). Contrato em
[[decisoes/0011-linha-de-base-e-semana-padrao]] (itens 8 e 9; a ADR está em proposta, então a API pode mudar em
detalhe). Todos os dados são **sintéticos**. Nada em `apps/mobile/` muda nesta nota.

Esboço do tema claro, em celular pequeno (360): ![[design/telas/semana-padrao-claro.svg]]
(arquivo `docs/design/telas/semana-padrao-claro.svg`; mostra segunda a quinta e o aviso de "salvo"). O tema
escuro usa a coluna "escuro" de [[design/tokens]] com o mesmo layout. Nenhuma cor nova: o contraste dos pares
usados já está em [[design/tokens]] (script `docs/design/contraste.py`).

## Objetivo
O atleta (ou o treinador, que ainda não tem login) diz **o que se costuma treinar em cada dia**: modalidade e,
se quiser, o tipo do treino. O app usa isso para dar tipo aos treinos e comparar cada um com o normal do próprio
atleta. A tela responde: "qual é a minha semana-padrão, desde quando vale e o que mudou quando eu a alterei?".
Exemplo de uso: "segunda fartlek + natação, terça bike intervalado, quarta corrida intervalado + natação".

## Onde fica e como se chega
- Rota nova: `/semana-padrao` (`src/app/semana-padrao.tsx`). Hoje o app não tem navegação além da evolução e do
  treino; esta é a primeira tela de "configuração".
- Entrada: na **evolução dos tiros**, logo abaixo do subtítulo e acima do botão "Enviar arquivo FIT", um botão de
  texto com ícone `event` à esquerda, "Semana-padrão" e `chevron-right` à direita, alvo 48. Mesmo padrão do
  "Ver treino" ([[design/telas/treino]]). Mais adiante, quando houver menu, a rota muda de lugar sem mudar de endereço.
- "Voltar" (`arrow-back`) usa `router.back()`. Abrir `/semana-padrao` direto na web também vale.
- Web larga (a partir de 600): mesma tela, conteúdo limitado a `largura.conteudo-max` (720), margem 24.

## Dados
Pelo cliente gerado (a ser regerado na #264):
- `GET /atletas/{id}/semana-padrao` (sem `em`: vale hoje) devolve `vigente` (ou `null`) e `vigencias`.
- `GET /atletas/{id}/semana-padrao?em=AAAA-MM-DD`: usado só para **copiar** uma vigência antiga (ver "Histórico").
- `PUT /atletas/{id}/semana-padrao` com `vigente_desde`, `definido_por` e `itens`; a resposta traz
  `atividades_reaplicadas`.

| campo da API | valores | na tela |
|---|---|---|
| `dia_semana` | 1 a 7 (1 = segunda) | uma seção por dia, de segunda a domingo; o nome vem de `dia_semana_texto` |
| `modalidade` | `corrida`, `natacao`, `ciclismo` | chip de modalidade (ícone e nome) |
| `tipo_treino` | `null`, `leve`, `moderado`, `longo`, `intervalado`, `fartlek` | "Sem tipo" para `null`; os outros em português com inicial maiúscula |
| `vigente_desde` | data | "Vale a partir de" |
| `definido_por` | `atleta`, `professor` | "Quem definiu": "Eu" e "Treinador" |
| `atividades_reaplicadas` | inteiro | "N treinos reclassificados" |
| `vigencias[].total_itens` | inteiro | "N treinos por semana" |

O app não conta nem decide nada: o número de treinos reclassificados e o histórico vêm da API. Contar os itens
de cada dia ("2 treinos") é só rótulo da tela e não é métrica. A regra "um item por modalidade por dia" é aplicada
na própria tela (o botão de adicionar só oferece o que falta), e a API a valida de novo com `422`.

## Hierarquia da informação
1. O que se treina em cada dia (o cartão "Treinos de cada dia").
2. Desde quando vale.
3. Quem definiu.
4. O resultado de salvar (quantos treinos mudaram).
5. As semanas anteriores.

A leitura vai do alto para baixo, mas o ponto de ação (Salvar) fica fixo no pé da tela, sempre à mão.

## Layout (celular de 360, margem 16)
```
┌──────────────────────────────────┐
│ ← Voltar                         │  botão de texto, alvo 44
│ Semana-padrão                    │  fonte.titulo-tela
│ O que você costuma treinar em    │  fonte.corpo, cor.texto-2
│ cada dia                         │
│ ┌ Vale a partir de ────────────┐ │  cartão
│ │ [ 02/03/2026              ]  │ │  campo, altura 48
│ │ [Hoje] [Próxima segunda]     │ │  atalhos, alvo 44
│ │ Os treinos antes desta data  │ │  fonte.legenda
│ │ não mudam.                   │ │
│ └──────────────────────────────┘ │
│ ┌ Quem definiu ────────────────┐ │  cartão
│ │ (●) Eu          ( ) Treinador│ │  duas opções, alvo 48
│ └──────────────────────────────┘ │
│ ┌ Treinos de cada dia ─────────┐ │  cartão
│ │ Segunda            2 treinos │ │  fonte.titulo-secao
│ │ (🏃 Corrida) [Fartlek    ▾][🗑]│ │  chip, seletor de tipo, remover
│ │ (🏊 Natação) [Sem tipo   ▾][🗑]│ │
│ │ + Adicionar treino           │ │  botão de texto, alvo 44
│ │ ──────────────────────────── │ │
│ │ Terça              1 treino  │ │
│ │ (🚴 Ciclismo)[Intervalado▾][🗑]│ │
│ │ + Adicionar treino           │ │
│ │ ... quarta a domingo ...     │ │
│ │ Quinta            Sem treino │ │
│ │ + Adicionar treino           │ │
│ └──────────────────────────────┘ │
│ ┌ Semanas anteriores ──────────┐ │  cartão (histórico)
│ │ Desde 02/03/26 · Em vigor    │ │  linha tocável, altura 56
│ │ Eu · 4 treinos por semana  > │ │
│ │ Desde 02/02/26               │ │
│ │ Treinador · 7 treinos...   > │ │
│ └──────────────────────────────┘ │
├──────────────────────────────────┤  barra fixa no pé (superficie, borda no topo)
│ [aviso: salvo / erro]            │  aparece só quando há resultado
│ [        Salvar semana         ] │  botão primário, altura 48
└──────────────────────────────────┘
```
Ícones das modalidades: `directions-run`, `pool`, `directions-bike`, sempre com o nome ao lado
([[design/guia-visual]], "Chip de modalidade"). A barra fixa fica no pé da janela; na web larga ela acompanha a
largura do conteúdo (720) e não a janela inteira.

### Campo "Vale a partir de"
- Campo de texto com máscara `dd/mm/aaaa`, teclado numérico, altura 48, `raio.medio`, contorno `cor.borda-forte`.
  Sem pacote novo de calendário nesta versão (ver "Dúvidas de produto"). Na web, o Rafa pode usar o `<input
  type="date">` do navegador, que já é acessível.
- Valor inicial: **hoje** (data local, como a API faz com `em`). Assim salvar cria uma vigência nova em vez de
  reescrever a vigente, e o passado fica intacto (ADR 0011, item 8).
- Atalhos "Hoje" e "Próxima segunda" (botões de 44 de altura, estilo secundário). A próxima segunda é calculada
  pelo calendário do aparelho: é data, não métrica.
- Texto de apoio fixo: "Os treinos antes desta data não mudam."
- Aviso extra, quando a data for **igual** à de uma vigência do histórico: "Já existe uma semana que vale desde
  esta data. Salvar vai substituí-la." (`cor.alerta`, ícone `warning-amber`).
- Aviso extra, quando a data for **futura**: "Esta semana começa a valer em dd/mm/aa. Até lá, nada muda."
  (informativo, `info-outline`).
- Data no futuro é aceita pela API; data inválida ou vazia não envia (ver "Erros de preenchimento").

### Cartão "Quem definiu"
- Duas opções de rádio lado a lado: "Eu" (`atleta`, **pré-marcada**) e "Treinador" (`professor`). Altura 48 cada.
- Selecionada: fundo `cor.destaque-suave`, contorno de 2 em `cor.destaque`, ícone `radio-button-checked`. Não
  selecionada: contorno de 1 em `cor.borda-forte`, `radio-button-unchecked`. A seleção não depende da cor: muda
  o ícone e a espessura do contorno.
- Texto de apoio: "Só registra de quem é o plano. O app ainda não tem login."
- O campo é obrigatório na API (`422` se faltar). Como "Eu" vem marcada, nunca fica vazio.

### Cartão "Treinos de cada dia"
- Uma seção por dia, de segunda a domingo, separadas por divisória (`cor.borda`). O nome do dia em
  `fonte.titulo-secao` e, à direita, o resumo em `fonte.rotulo` e `cor.texto-2`: "Sem treino", "1 treino",
  "2 treinos".
- **Item** = uma linha de 48: chip da modalidade (não editável), seletor de tipo e botão remover. A
  modalidade não muda depois de criada: para trocar, remove e adiciona outra. Isso evita, por construção, duas
  vezes a mesma modalidade no dia.
- **Seletor de tipo** (botão com contorno `cor.borda-forte`, altura 48, valor atual e `expand-more`): abre a lista
  "Tipo do treino" com seis opções de 56 de altura, em rádio: "Sem tipo", "Leve", "Moderado", "Longo",
  "Intervalado", "Fartlek". No celular é uma folha que sobe do pé; na web larga, um menu junto ao botão. Tocar
  numa opção escolhe e fecha. O padrão de um item novo é "Sem tipo". Texto de apoio no topo da lista: "Sem tipo:
  o app não define o tipo desse treino pela semana."
- **Remover** (`delete-outline`, alvo 44 por 44, `cor.erro`): remove na hora, sem confirmação, porque nada é
  gravado até "Salvar semana" e dá para voltar sem salvar. Não há "desfazer".
- **Adicionar treino** (botão de texto com `add`, alvo 44): abre a folha "Qual modalidade?" com só as modalidades
  que **faltam** naquele dia ("Corrida", "Natação", "Ciclismo", cada uma com ícone e nome, 56 de altura). O novo item
  entra no fim da lista do dia, com o seletor de tipo em foco. Com as três já usadas, o botão some.
- Ordem dos itens no dia: a da API ("ordem de dia e modalidade", ADR 0011, item 9). Itens novos entram no fim e,
  depois de salvar, a tela mostra a ordem que a API devolveu.
- Celular estreito com fonte grande: chip e remover ficam na primeira linha e o seletor desce para a linha de baixo,
  com largura total (sem cortar texto).

### Cartão "Semanas anteriores" (histórico de vigências)
- Lista de `vigencias` na ordem da API (a mais nova no alto). Cada linha (altura mínima 56, `accessibilityRole="button"`):
  - 1ª linha: "Desde 02/03/26" (`fonte.corpo-forte`) e, se for a vigente hoje, um selo "Em vigor" (texto, não só cor);
    se a data ainda não chegou, o selo "Ainda não começou".
  - 2ª linha: "Eu · 4 treinos por semana" ou "Treinador · 7 treinos por semana" (`fonte.corpo`, `cor.texto-2`).
  - `chevron-right` à direita.
- Tocar numa linha **copia** aquela semana para o formulário (chama `GET ?em=<vigente_desde>`) e mostra o aviso:
  "Semana de 02/02/26 copiada. Salvar cria uma semana nova a partir de {data do campo}." A data do campo continua
  a que estava (hoje, por padrão). Nada é gravado até "Salvar semana".
- Só aparece com pelo menos uma vigência. Sem plano nenhum, o estado vazio cobre.
- Carregar uma cópia com o formulário alterado e não salvo pede confirmação (ver "Sair com mudanças").

### Barra fixa de salvar
- Botão primário "Salvar semana" (único primário da tela). **Desligado** (fundo `cor.superficie-2`, texto
  `cor.texto-desligado`) enquanto nada mudou em relação ao que foi carregado, e quando não há plano carregado e a
  semana está sem nenhum treino. Quando desligado, o motivo aparece em texto acima do botão: "Nada mudou ainda." ou
  "Adicione pelo menos um treino."
- Sem treinos em nenhum dos sete dias **com** uma semana vigente carregada: o botão fica ligado, e o aviso
  (`cor.alerta`) diz "Sem nenhum treino, o plano acaba em dd/mm/aa e o app deixa de usá-lo para classificar os
  treinos." Salvar assim envia `itens: []` e encerra o plano.
- Ao salvar, vem a reaplicação do tipo nos treinos a partir da data. A tela só mostra o resultado.

## Estados
Segue o padrão de [[design/guia-visual]], "Estados". O conteúdo que já está na tela não some quando uma nova
ação começa.

| estado | o que aparece | texto |
|---|---|---|
| carregando | esqueleto do cartão de data, do de "quem definiu" e de dois dias (`cor.superficie-2`, `raio.pequeno`, pulso `movimento.esqueleto`); o texto fica para o leitor de tela; botão Salvar desligado | "Carregando a semana-padrão..." |
| vazio (sem plano) | ver "Estado vazio" abaixo | "Você ainda não definiu sua semana-padrão" |
| editando | o formulário completo; Salvar ligado quando há mudança | |
| salvando | o botão vira "Salvando..." com indicador no lugar do ícone e fica desligado; campos e botões do formulário ficam desligados (sem esmaecer o texto abaixo do contraste AA, usa `cor.texto-desligado` só em botão) | "Salvando..." |
| salvo | aviso de sucesso na barra fixa; o formulário passa a mostrar o que a API devolveu; o histórico se atualiza; Salvar volta a ficar desligado ("Nada mudou ainda.") | ver "Textos de salvar" |
| erro ao carregar (rede) | ícone `wifi-off` de 40 em `cor.erro`, frase e botão "Tentar de novo" | "Não foi possível falar com o servidor" |
| erro ao carregar `404` | `error-outline` e frase | "Atleta não encontrado" |
| erro ao carregar (outro) | `error-outline` e frase | "Não foi possível carregar a semana-padrão. Tente de novo mais tarde." |
| erro ao salvar (rede) | aviso de erro na barra fixa, `accessibilityRole="alert"`; **as mudanças ficam na tela**; botão volta a ligar | "Não foi possível falar com o servidor. Suas mudanças continuam aqui. Tente salvar de novo." |
| erro ao salvar `422` | aviso de erro na barra fixa; as mudanças ficam; o campo com problema, se a API o apontar, recebe o aviso em texto | "Algum dado da semana não foi aceito. Confira a data e os treinos de cada dia e tente de novo." |
| erro ao salvar `404` | aviso de erro | "Atleta não encontrado." |
| erro ao salvar (outro) | aviso de erro; as mudanças ficam | "Não foi possível salvar. Tente de novo mais tarde." |

O `422` quase nunca deve aparecer, porque a tela já impede dia fora de 1 a 7, modalidade repetida, tipo fora da
lista e `definido_por` vazio. Fica coberto para o caso de a tela e a API divergirem. O app **não** mostra o texto
técnico do `detail` da API.

### Estado vazio (sem plano)
Quando `vigente` é `null` **e** não há vigências. Se há vigências mas nenhuma vale hoje (a primeira ainda é futura),
a tela mostra o formulário normalmente, com o histórico.
```
┌──────────────────────────────────┐
│ ← Voltar                         │
│ Semana-padrão                    │
│                                  │
│            (ícone event-note 40) │  cor.texto-2
│  Você ainda não definiu sua      │  fonte.titulo-secao
│  semana-padrão                   │
│  Diga que treino você costuma    │  fonte.corpo
│  fazer em cada dia. O app usa    │
│  isso para comparar cada treino  │
│  com os do mesmo tipo.           │
│  [      Montar minha semana    ] │  primário, altura 48
└──────────────────────────────────┘
```
"Montar minha semana" troca o vazio pelo formulário com os sete dias sem treino, "Eu" marcada e a data de hoje.
Fica um só botão primário na tela. Se o treinador for quem monta, ele muda para "Treinador" no formulário.

### Erros de preenchimento (antes de enviar)
Em texto, junto ao campo, com ícone `error-outline` e `cor.erro`; o foco vai ao primeiro campo com erro; o botão
Salvar continua ligado (o erro aparece ao tocar). Nunca só a cor do contorno.
| situação | texto |
|---|---|
| data vazia | "Digite a data em que a semana começa a valer." |
| data impossível (ex.: 31/02/2026) | "Digite uma data que exista, como 02/03/2026." |

### Sair com mudanças
"Voltar" (e o botão voltar do Android) com mudanças não salvas abre um diálogo: título "Sair sem salvar?", texto
"As mudanças desta semana serão perdidas.", botões "Continuar editando" (primário) e "Sair sem salvar".
Na web, o `beforeunload` do navegador cobre fechar a aba. Tocar numa semana do histórico com mudanças não salvas
usa o mesmo diálogo: "Copiar esta semana?", "As mudanças que você fez serão trocadas pela semana de dd/mm/aa.",
"Continuar editando" e "Copiar".

## Textos de salvar
O número vem de `atividades_reaplicadas`. Singular para 1; "Nenhum" para 0.
| resultado | texto |
|---|---|
| 0 | "Semana salva. Nenhum treino mudou de tipo." |
| 1 | "Semana salva. 1 treino reclassificado." |
| N | "Semana salva. N treinos reclassificados." |
| data futura | "Semana salva. Ela passa a valer em dd/mm/aa; nenhum treino muda até lá." |
| plano encerrado (`itens: []`) | "Plano encerrado a partir de dd/mm/aa. N treinos reclassificados." (0: "Nenhum treino mudou de tipo.") |
O aviso fica até a próxima mudança no formulário e é anunciado ao leitor de tela (live region educada). Em "treino
reclassificado" entra só quem teve tipo, origem ou divergência alterados; treino com tipo confirmado ou vindo do
professor ou do TrainingPeaks não muda (ADR 0011, item 8). Uma linha de apoio abaixo do aviso: "Treinos
anteriores a dd/mm/aa não foram alterados." (`fonte.legenda`).

## Fluxos
1. **Primeira vez (sem plano):** evolução > "Semana-padrão" > vazio > "Montar minha semana" > adiciona itens dia a
   dia > mantém "Eu" e a data de hoje > "Salvar semana" > aviso "Semana salva. N treinos reclassificados.".
2. **Mudar o plano:** abre com a semana vigente preenchida > muda um tipo ou adiciona uma natação > a data continua
   hoje > "Salvar semana" > nova vigência; a anterior aparece no histórico.
3. **Treinador monta para o atleta:** muda "Quem definiu" para "Treinador", escolhe a data (por exemplo,
   "Próxima segunda") > salva.
4. **Voltar ao plano antigo:** em "Semanas anteriores" toca "Desde 02/02/26" > semana copiada > escolhe a data >
   salva como nova vigência.
5. **Encerrar o plano:** remove todos os itens > aviso de que o plano acaba > salva com `itens: []`.
6. **Falha ao salvar:** erro na barra > mudanças continuam > "Salvar semana" de novo. Clique duplo não duplica:
   o botão fica desligado enquanto salva.

## Acessibilidade
- Contraste AA em todos os pares (nenhuma cor nova); texto mínimo 13 (legenda), nada abaixo de 12 ([[design/tokens]]).
- Alvos de 44 ou mais em tudo: botão remover 44 por 44, atalhos de data 44, opções de rádio 48, itens de lista 56.
- Informação nunca só pela cor: modalidade = ícone + nome; opção escolhida = ícone de rádio + contorno mais grosso
  (+ cor); "Em vigor" e "Ainda não começou" em texto; erro com ícone e frase.
- Ordem de leitura: Voltar, título, "Vale a partir de" (campo, atalhos, apoio), "Quem definiu", cada dia
  (nome e resumo, depois itens, depois "Adicionar treino"), "Semanas anteriores", aviso, Salvar.
- Nome do dia com `accessibilityRole="header"`. Cada item é lido como um grupo: "Segunda, corrida, tipo fartlek".
- Rótulos de acessibilidade com o contexto, porque "Remover" sozinho repete sete vezes: "Remover corrida de segunda",
  "Tipo do treino de corrida na segunda, fartlek, botão", "Adicionar treino na terça".
- Rádio com `accessibilityRole="radio"` e `accessibilityState.checked`; "Quem definiu" é um grupo com rótulo.
- Foco: ao adicionar, vai para o seletor de tipo do item novo; ao remover, vai para o nome do dia; ao fechar a
  folha, volta ao botão que a abriu; erro de preenchimento leva o foco ao campo.
- Anúncios: "Corrida removida de segunda"; "Natação adicionada em segunda"; o aviso de salvo e de erro como
  `alert`/live region.
- Anel de foco de 2 em `cor.foco` para teclado na web; folha e menu fecham com Esc e prendem o foco.
- Fonte do sistema: a linha do item quebra em duas (ver acima); `fonte.titulo-tela` limita a 1,5.
- Ao ar livre: texto principal em `cor.texto` sobre `cor.superficie`, mais de 14 de contraste no claro.

## Como gerar capturas sintéticas
Como em [[modulos/mobile]] (`npm run api-falsa`): a API falsa precisa dos três endpoints acima, com a semana de
exemplo (segunda fartlek + natação, terça ciclismo intervalado, quarta corrida intervalado + natação) e
duas vigências. Só dado sintético; 390 de largura, claro e escuro, um estado por captura.

## O que muda em relação ao app de hoje
| hoje | proposta | issue |
|---|---|---|
| não existe tela de configuração | rota `/semana-padrao` | a abrir |
| evolução sem nenhum atalho | botão "Semana-padrão" na evolução | a abrir |
| sem ícones de calendário, lixeira e adicionar | novos nomes em [[design/tokens]] (`event`, `event-note`, `add`, `delete-outline`, `expand-more`, `radio-button-checked`, `radio-button-unchecked`) | a abrir |
| API falsa sem semana-padrão | três endpoints sintéticos | a abrir |

## Dúvidas de produto
1. **Data do campo por padrão:** hoje (cria vigência nova e preserva o histórico) ou a data da vigente (edita no
   lugar)? Proponho hoje; a tela avisa quando a data coincide com uma vigência existente.
2. **Calendário:** campo de texto com máscara (sem pacote novo) ou um seletor de data nativo
   (`@react-native-community/datetimepicker`, gratuito, mas mais uma dependência)? Proponho o campo de texto agora.
3. **Tocar numa semana antiga:** só copia (o que está na spec) ou também deve permitir ver sem editar? Copiar é o
   caminho seguro, porque editar a vigência antiga reaplica o tipo a partir daquela data.
4. **"Treinador" sem login:** o campo é só uma declaração, sem verificação. Basta o texto "Só registra de quem é o
   plano" ou o Angelo quer outro aviso?
5. **Remover item sem desfazer:** aceitável porque nada é gravado antes de salvar? Se não, entra um "Desfazer" no aviso.
