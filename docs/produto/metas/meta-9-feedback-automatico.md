---
tipo: meta
status: em-uso
dono: paulo
atualizado: 2026-11-12
links: [[produto/roadmap]], [[produto/meta-9-como-rodar]], [[decisoes/0013-feedback-automatico]], [[decisoes/0012-check-in-pos-treino]], [[decisoes/0004-contrato-tela-evolucao]], [[metricas/fatos-treino]], [[metricas/fatos-treino-oraculo]], [[metricas/checagens-feedback]], [[design/telas/feedback]], [[modulos/camada-llm]], [[modulos/banco]], [[modulos/api]], [[modulos/api-client]], [[modulos/mobile]], [[modulos/worker]], [[modulos/ingestao-garmin]], [[produto/metas/meta-8-check-in]], [[diario/2026-11-10]], [[diario/2026-11-11]], [[glossario]]
---
# Meta 9: feedback automático por treino

> **Situação: feita, com três itens não verificados.** Código, documentação e QA no `main` (PRs #337 a #363, entre 10/11 e 12/11). A
> Bia conferiu o critério de pronto com `tests/test_e2e_meta9.py` (23 testes, um por item, só dado sintético, sem rede) e seguiu o
> [[produto/meta-9-como-rodar]] do zero com um Postgres descartável (#332, PR #362). Um bug achado na QA (#361) foi corrigido no PR #363.
> A [[decisoes/0013-feedback-automatico]] foi **aceita em 10/11** (PR #345). **Não verificados:** o cartão na tela do app rodando, o
> celular do Angelo (check-in da Meta 8 e cartão da Meta 9) e a revisão da Lia sobre a tela pronta (ver "O que não foi verificado").
> Fechamento: #333.

## Objetivo
Depois do check-in, o atleta lê **3 a 5 linhas** sobre o treino: como foi em relação ao normal dele naquele tipo de treino, o que o
check-in e o contexto (clima, carga) dizem e, quando um fato sustenta, uma observação positiva. **Quem calcula é o código; a IA só
redige** a partir de um pacote de fatos (`fatos_treino@1`), e o texto passa por checagens automáticas antes de chegar ao app. O
feedback é texto escrito, sem áudio, e quem fala é o app.

## Entrega visível
- O campo `feedback` no `GET` da atividade, com cinco estados (`pronto`, `sem_checkin`, `pendente`, `desatualizado`, `indisponivel`),
  a frase pronta e só a `origem` do texto (adendo 10 da [[decisoes/0004-contrato-tela-evolucao]], [[modulos/api]]).
- `worker.gerar_feedback` (pacote, LLM, checagens, grava), com `--limite`, `--refazer`, pausa entre chamadas e parada no limite do
  provedor; o feedback é apagado com o check-in, também pelo `worker.apagar_checkin` ([[modulos/worker]]).
- O cartão "Feedback" na tela do treino, abaixo do check-in ([[design/telas/feedback]], [[modulos/mobile]]).
- Passo a passo em [[produto/meta-9-como-rodar]].

## Critério de pronto
Resultado de cada item conforme a QA da Bia na #332 (PR #362), contra o `main` em `5325cbe`, só com fixtures sintéticas, mais o que
entrou depois (#363). Os números entre parênteses são os testes de `tests/test_e2e_meta9.py`.

| Item | Onde | Resultado |
|---|---|---|
| ADR 0013 aprovada pelo Theo antes da migração; oito decisões do Angelo registradas; "A confirmar" com padrões; o Angelo lê os exemplos de tom antes do código | #322 | **ok**. ADR no `main` como `proposta` (PR #340) e **aceita** em 10/11 (PR #345), antes da migração 0013 (PR #348, 11/11). O Angelo leu os 6 exemplos sintéticos e respondeu "ok para as quatro" (itens 1, 2, 9 e 10); itens 3, 4 e 6 pelo Theo; 5, 7 e 8 com o padrão (e2e 23) |
| `fatos_treino@1` como função pura, nota e oráculo; só números que o código já calcula; sem causa | #323, #324 | **ok** ([[metricas/fatos-treino]], [[metricas/fatos-treino-oraculo]]; e2e 03 e 04): igual ao oráculo nos 8 casos com pacote; sem identificador, data real, posição nem texto livre |
| Checagens: todo número no pacote; nenhuma linguagem proibida; reprovado descartado e nunca no app; teste com textos ruins | #325, #355 | **ok** ([[metricas/checagens-feedback]]; e2e 09 e 10). Hoje em `checagens_feedback@2` (PR #360), com regras de forma; 13 textos bons e 82 ruins sintéticos |
| LLM só pela camada trocável; provedor falso nos testes e no CI; nada do pacote nem do texto em log | #326 | **ok** ([[modulos/camada-llm]]; e2e 06, 07, 12, 13, 15, 16 e 21) |
| Texto livre da observação nunca vai ao provedor; regra do dado de saúde; feedback apagado com o check-in | #326, #327 | **ok** (e2e 14, 17, 18 e 19) |
| Endpoints no OpenAPI, adendo da ADR 0004, cliente regerado | #328 | **ok** (adendo 10; e2e 05, 08 e 22) |
| Cartão com teste e revisão da Lia | #329, #330 | **ok nos testes e nas capturas**: `CartaoFeedback.test.tsx`, um teste por estado; design-ok da Lia no PR #352 sobre 22 capturas sintéticas, depois de dois ajustes (região viva no Android, capturas em tela inteira). **Não verificado** na tela rodando (abaixo) |
| QA com fixtures num clone limpo, seguindo só o guia, com o provedor falso | #331, #332 | **ok depois do #363**. Na QA, o texto fixo do provedor falso era reprovado pela `checagens_feedback@2` e os passos 8 a 10 e 12 do guia não davam o descrito (bug #361); com o conserto, os números do guia batem (e2e 20) |
| Uma rodada com o provedor de verdade, só com fixtures sintéticas | #332 | **ok**. Pausa de 40 s entre chamadas, banco descartável: 4 gerados, 0 reprovados, 0 recusas por limite |
| O Angelo abre no celular, na mesma sessão, o check-in (Meta 8) e o cartão de feedback | #332 | **não verificado** (a sessão não aconteceu; ver abaixo) |
| Testes | todos | `uv run pytest` no `main` em `17b1c85`: 2374 verdes e 2 pulados (SQLite local, rodado no fechamento; 23 em `tests/test_e2e_meta9.py`); `npm test` com 249 (QA) |

## O que foi entregue
| Issue | Entrega | PR |
|---|---|---|
| #336 | Roteiro com a Meta 9 em curso e a paralela P14 | #337 |
| #322 | ADR 0013 ([[decisoes/0013-feedback-automatico]]), proposta e depois aceita em 10/11 | #340, #345 |
| #323 | Fixtures sintéticas e oráculo do pacote; textos bons e ruins para as checagens | #341, #346 |
| #329 | Spec do cartão Feedback ([[design/telas/feedback]]) | #338 |
| #326 | Camada de LLM trocável (LiteLLM), provedor falso, tempo limite, sem log de conteúdo ([[modulos/camada-llm]]) | #343 |
| #324 | `fatos_treino@1` como função pura ([[metricas/fatos-treino]]) | #347 |
| #325 | Checagens do texto, `checagens_feedback@1` ([[metricas/checagens-feedback]]) | #349 |
| #327 | Migração 0013 (`feedback_treino`), `worker.gerar_feedback`, prompt `feedback_prompt@1` | #348 |
| #328 | `feedback` no `GET` da atividade, adendo 10 da ADR 0004, cliente regerado | #350 |
| #330 | Cartão "Feedback" na tela do treino, com design-ok da Lia | #352 |
| #355 | `feedback_prompt@2` (frases completas, comparação com número) e `checagens_feedback@2` (regras de forma) | #356, #360 |
| #357 | `LLM_INTERVALO_S`, parada da execução no limite do provedor, `--refazer` que mantém o texto pronto se falhar | #358 |
| #354 | O `.env` lido é sempre o da raiz do repositório | #359 |
| #331 | Guia [[produto/meta-9-como-rodar]] e diário [[diario/2026-11-11]] | #353 |
| #332 | QA de ponta a ponta e `tests/test_e2e_meta9.py` | #362 |
| #361 | Texto fixo do provedor falso que passa na `checagens_feedback@2`, com teste que roda a checagem real | #363 |
| #333 | Resultado da meta e roteiro | este |

Paralelas, fora do critério de pronto: #334 (capturas do check-in no tema escuro e nos estados de erro, PR #351), #335
(`worker.buscar_garmin`, buscar a atividade do dia no Garmin Connect, só no piloto local, PR #339) e #342 (o `buscar_garmin` não baixa de
novo o que já importou, PR #344; [[modulos/ingestao-garmin]]). Em aberto, da Nina: #364 (alinhar glossário, [[00-inicio]], guia, notas
e diário depois da QA).

## Decisões (regra de produto)
**Do Angelo (10/11, "ok" às oito decisões, sem mudança):** abrir as issues e começar; ao provedor vai só o pacote de fatos, nunca o
texto livre da observação, nome, data real, posição ou identificador; na meta, só fixtures sintéticas no provedor de verdade; só o plano
gratuito, com limite de chamadas por execução; feedback só depois do check-in, e editar o check-in desatualiza; quem fala é o app, sem o
nome do professor, e o feedback é **texto, sem áudio**; o atalho "dor" vira uma frase neutra, sem conselho; texto reprovado deixa o treino
sem feedback, com o motivo, e uma nova tentativa na execução seguinte. Na ADR: "ok para as quatro" (observação positiva só com fato;
clima e check-in lado a lado, sem "possível"; tom dos 6 exemplos; `pendente` até alguém rodar o worker).

**Do Angelo (10/11, "sim para as duas"):** a P14 (#335) como paralela, só local e só na conta dele; o feedback dos treinos reais dele no
provedor, só localmente, sem nada no repositório. **Do Angelo (11/11):** o ajuste da forma do texto (#355), depois da primeira rodada
com o provedor de verdade sobre fixtures.

**Do Theo:** modelo de dados da ADR 0013 (um feedback por check-in, versões do pacote, das checagens e do prompt na linha, ordem da fila do
worker); tempo limite de 20 s e 20 chamadas por execução; tentar de novo sem teto; o feedback não é refeito sozinho na reimportação, só
com `--refazer`; adendo de 11/11 (#357): `--refazer` que falha mantém o texto pronto, e a recusa por limite para a execução sem gravar
linha.

## O que não foi verificado
- **O cartão na tela do app rodando.** Ninguém viu o cartão "Feedback" numa tela de verdade, nem na web: na QA a extensão do navegador
  não estava conectada, e os passos 10 e 11 do guia ficaram de fora. O cartão foi conferido só pelo `npm test` (249 testes) e pelas 22
  capturas sintéticas do PR #352; a API foi conferida por `curl`.
- **O celular do Angelo.** A sessão em que ele abriria no celular (Expo Go, rede de casa, dado sintético) o check-in, pendente da Meta 8,
  e o cartão de feedback **não aconteceu**. Nenhuma tela do app foi aberta num iOS ou Android até aqui. É a segunda meta seguida com
  esse item aberto.
- **A revisão da Lia sobre a tela pronta.** O design-ok do PR #352 foi dado sobre as capturas; a Lia não revisou o cartão no app em
  execução, com a API real, depois do merge.
- **Leitor de tela real:** o anúncio do "Atualizar" (região viva no Android, anúncio no iOS e na web) foi conferido nos testes, não com
  VoiceOver ou TalkBack.
- **Pontos do provedor ainda não conferidos** (item 10 de "A confirmar" da ADR 0013): uso dos dados para treinar modelos e limites do plano
  gratuito. A autorização do Angelo para os treinos dele segue valendo, com os limites da ADR.

## O que ficou de fora
Como planejado: motor de explicação com o peso de cada fator; resumos semanal, quinzenal e mensal; envio em nome do professor e revisão
de amostra pelo professor (Meta 10 do esboço); aviso por WhatsApp ou e-mail; agente com pergunta livre; feedback sem check-in; feedback
em áudio; gatilho de fundo depois do `PUT`; sono, VFC, estado de treino, prontidão e treinos planejados do Garmin Connect.

## Limitações conhecidas
Detalhes na [[decisoes/0013-feedback-automatico]], seção "Limitações", e nas notas de métrica. Todas em texto genérico.
- **A checagem de forma é heurística** (`checagens_feedback@2`): verbo fora da lista reprova por engano; a conclusão repetida com outras
  palavras passa ([[metricas/checagens-feedback]]).
- **Versão nova do prompt ou das checagens não desatualiza o que já está pronto:** só a versão do pacote e a edição do check-in
  desatualizam; o resto só com `--refazer`.
- **O feedback não acompanha a reimportação** da atividade: segue o texto antigo até o check-in mudar ou o `--refazer`.
- **`pendente` até alguém rodar o worker:** não há gatilho depois do `PUT` (aceito no piloto local).
- **Sem login:** "só ao próprio atleta" é o `atleta_id` da rota, como no check-in.
- **Validado com fixtures sintéticas.** Não há conferência no repositório com o histórico real: o feedback é texto novo, e o que for
  gerado localmente para os treinos do Angelo fica só no banco local.

## Achados
- **O texto do provedor falso não passava na checagem nova (#361).** A `checagens_feedback@2` (PR #360) entrou com regras de forma, e o
  texto fixo do provedor falso, escrito para a `@1`, passou a ser reprovado. Os testes do worker injetavam uma checagem própria e não
  pegaram; o e2e da Bia, que roda o worker de verdade, pegou, e entrou com um `xfail(strict)` ligado ao bug até o conserto (PR #363).
- **A primeira rodada com o provedor de verdade achou o que as fixtures não achavam:** os textos passavam nas checagens, mas saíam
  telegráficos (listas de valores, a mesma conclusão duas vezes, nenhum número na comparação). Virou `feedback_prompt@2` e
  `checagens_feedback@2` (#355), a pedido do Angelo.
- **O plano gratuito do provedor recusa por limite por minuto.** Chamadas seguidas foram recusadas; daí `LLM_INTERVALO_S` (pausa entre
  chamadas), um motivo próprio para a recusa por limite e a parada da execução no primeiro limite (#357). Com 40 s de pausa, a rodada da
  QA não teve recusa.
- **O `.env` era lido da pasta de execução (#354).** Um worker rodado fora da raiz (ou de outra cópia do repositório, como uma worktree)
  tratava o provedor como não configurado, sem erro. Agora o `.env` é sempre o da raiz do repositório.
- **O guia ficou para trás das paralelas:** a contagem de testes e o texto do provedor falso mudaram depois do guia (PRs #356, #358,
  #360 e #363); o alinhamento é a #364, da Nina.
- **Ninguém viu a tela.** A conferência visual dependia da extensão do navegador, que não estava conectada (o mesmo risco já visto na
  Meta 8).

## O que se aprendeu
- **Versão nova de checagem confere também o texto do provedor falso.** Toda mudança em `checagens_feedback` roda a checagem real sobre
  o texto fixo do provedor falso (o teste do #363 faz isso); teste de worker com checagem injetada não substitui a checagem real.
- **O `.env` é da raiz do repositório.** Numa worktree ou em outro clone, a raiz muda e o `.env` também; o guia e as notas dizem de onde
  o comando roda e qual `.env` vale.
- **Limite por minuto do provedor é parte do desenho**, não um erro raro: pausa configurável (`LLM_INTERVALO_S`) e parada no primeiro
  limite, em vez de gastar o resto da execução.
- **Mudar a versão do prompt não desatualiza o que já está pronto.** É uma escolha (o texto descreve o treino na hora em que foi gerado):
  quem quiser o texto novo usa `--refazer`. Vale escrever isso na ADR antes de subir a versão, como foi feito na #355.
- **Rodada pequena com o provedor de verdade antes da QA**, só com fixtures, achou a forma do texto; da próxima vez, fazer essa rodada
  logo depois da camada e do prompt, não no fim.
- **A seção "A confirmar" com padrões funcionou pela quarta meta seguida:** quatro respostas do Angelo de uma vez, e nenhuma mudou o
  código.
- **Passo que depende de pessoa ou de ferramenta não pode ficar para a QA.** O celular ficou pendente pela segunda meta e a tela não foi
  vista porque a extensão do navegador não estava conectada. Na próxima meta, a conferência visual (web e celular) vira issue própria na
  largada, com data marcada com o Angelo, e não um passo da QA.

## PRECISA DO ANGELO
- **A sessão do celular** (Expo Go, rede de casa, dado sintético): abrir o check-in (Meta 8) e o cartão de feedback (Meta 9), uma vez,
  com a Bia. Pendente desde a Meta 8.
- **Antes de gerar o feedback dos treinos reais dele:** ler os termos do provedor sobre treino de modelos (item 10 de "A confirmar" da
  ADR 0013). A retenção zero foi informada por ele em 10/11, não conferida por nós.
- **Meta 10:** a proposta e as perguntas estão no [[produto/roadmap]] ("Meta 10, proposta"). Nenhuma issue da Meta 10 foi aberta.

## Resultado
**Meta 9 feita, com três itens não verificados.** Com fixtures sintéticas e o provedor falso, depois do check-in o
`worker.gerar_feedback` monta o pacote de fatos (`fatos_treino@1`), pede o texto pela camada de LLM, descarta o que reprova nas
checagens (`checagens_feedback@2`) e grava o feedback; a API o devolve em cinco estados, com a frase pronta, e o cartão do app tem teste
por estado e design-ok sobre capturas. O texto livre da observação nunca vai ao provedor, nada do pacote ou do texto vai a log, e o
feedback é apagado com o check-in. Uma rodada com o provedor de verdade, só com fixtures, gerou 4 textos sem reprovação. Não
verificados: o cartão na tela rodando, o celular do Angelo e a revisão da Lia sobre a tela pronta.

Próxima: Meta 10, **proposta**, esperando o "ok" do Angelo ([[produto/roadmap]]).
