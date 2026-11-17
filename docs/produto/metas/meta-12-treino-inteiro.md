---
tipo: meta
status: em-uso
dono: paulo
atualizado: 2026-11-17
links: [[produto/roadmap]], [[produto/meta-12-como-rodar]], [[design/telas/treino]], [[decisoes/0004-contrato-tela-evolucao]], [[decisoes/0011-linha-de-base-e-semana-padrao]], [[decisoes/0009-treino-de-transicao]], [[decisoes/0013-feedback-automatico]], [[metricas/linha-base]], [[metricas/tipo-linha-base-oraculo]], [[metricas/carga-treino]], [[metricas/serie-carga]], [[metricas/esforcos]], [[metricas/transicao]], [[modulos/camada-llm]], [[modulos/mobile]], [[modulos/api]], [[produto/metas/meta-11-caixa-do-dia]], [[diario/2026-11-17]], [[glossario]]
---
# Meta 12: o treino inteiro na tela do atleta

> **Situação: feita, com cinco itens não verificados** (celular de verdade, leitor de tela real, login, aluno real e o feedback dos treinos
> reais ainda não refeito com a `linha_base@3`). Código, documentação e QA no `main` (PRs #473 a #492, em 17/11). A Bia conferiu o critério
> de pronto com `tests/test_e2e_meta12.py` (16 testes, só dado sintético, sem rede) e seguiu o [[produto/meta-12-como-rodar]] do zero num
> projeto Docker próprio, com a **tela viva contra a API de um banco limpo** (#469, PR #492). A Lia deu **design-ok sobre a tela rodando**.
> As quatro perguntas ao Angelo (A a D) foram respondidas em 17/11 (**"ok para as quatro"**, todas com a recomendação); a C ainda não está implementada. Fechamento: #470.

## Objetivo
Na tela de um treino, o atleta vê, além do check-in e do feedback, como o treino ficou em relação ao normal dele (linha de base), a carga
do treino e a forma do dia (como estimativa) e os esforços, com o rótulo de transição que ele pode corrigir. O app não calcula nada: lê o
que o `GET` da atividade devolve.

## Entrega visível
- A tela do treino com quatro cartões novos: **Esforços**, **Comparado com o seu normal**, **Carga e forma do dia** e **Treino de
  transição**, e distância, pace e FC em linhas iguais (#237) ([[design/telas/treino]], [[modulos/mobile]]).
- `linha_base@3`: piso de dispersão por métrica ([[metricas/linha-base]], adendo 3 da [[decisoes/0011-linha-de-base-e-semana-padrao]]).
- `GET` da atividade com os textos prontos da carga, o bloco `forma_do_dia` e `transicao.editavel` (adendo 12 da
  [[decisoes/0004-contrato-tela-evolucao]]), cliente regerado.
- Capturas por `npm run capturas` e capturas da tela viva em `docs/design/telas/treino/qa-viva/`.
- Passo a passo em [[produto/meta-12-como-rodar]].

## Critério de pronto
Resultado de cada item conforme a QA da Bia na #469 (PR #492), só com fixtures sintéticas.

| Item | Onde | Resultado |
|---|---|---|
| Spec da Lia antes da tela: cada seção em cada estado, palavras sem alarme nem diagnóstico, carga como estimativa | #463 | **ok** (PR #476; [[design/telas/treino]], seção "Meta 12"), antes das telas |
| `linha_base@3` com nota, oráculo e testes sintéticos, e conferência local só em `entregas/`, antes de a seção do normal mostrar o "fora do normal" | #462 | **ok** (PR #479; fecha também a #455). Conferência local feita na máquina do Angelo, com os números só em `entregas/`; aqui, só o achado genérico (pergunta D) |
| Carga do treino e CTL, ATL e TSB em números, sem gráfico | #464, #466 | **ok** (PRs #480 e #483). Em "aprendendo" os três números não aparecem (pergunta A, decidida pelo Angelo em 17/11) |
| O app não calcula: só textos e números do `GET`; adendo da ADR 0004 e cliente regerado | #464 | **ok** (PR #480, adendo 12) |
| Rótulo de transição corrigido pelo atleta com a rota que já existe; a correção vence a sugestão | #467 | **ok** (PR #484; `PUT` e `DELETE` existentes; `409` quando o treino não tem rótulo) |
| Cada seção com teste por estado e revisão da Lia sobre as capturas do comando e sobre a tela rodando | #465, #466, #467, #237 | **ok**. Telas nos PRs #483, #484, #485 e #477; design-ok da Lia na tela viva (390 px) dentro da QA |
| QA com fixtures num clone limpo, seguindo só o guia; testes e CI sem rede | #468, #469 | **ok**. Passos 1 a 7 e 9 como o guia diz; a única correção (abrir a tela por `localhost`, CORS) entrou no PR #492. Um achado de texto (#487, corrigido no PR #488; a #491 era duplicada) |
| Testes | todos | `tests/test_e2e_meta12.py`: 16 verdes; `jest TelaTreino`: 54 (PR #492). `uv run pytest` no `main` em `bdc57a9`: 2856 verdes e 2 pulados (SQLite local, rodado no fechamento) |

## O que foi entregue
| Issue | Entrega | PR |
|---|---|---|
| #461 | Roteiro com a Meta 12 em curso e as decisões do Angelo de 17/11 | #473 |
| #471 | `atencao@2` nas fixtures do app e na API falsa (paralela) | #474, #475 |
| #463 | Spec da tela do treino e decisão da #237 | #476 |
| #237 | Distância, pace e FC em linhas iguais, unidade no tom do valor | #477 |
| (sem issue) | Grafo de `docs/` refeito, módulo da caixa do dia, diário | #478 |
| #462, #455 | `linha_base@3` com piso por métrica | #479 |
| #464 | Contrato do `GET` da atividade (textos da carga, `forma_do_dia`, `transicao.editavel`) | #480 |
| (sem issue) | Nota da Meta 11 e [[00-inicio]] | #481 |
| #402 | Feedback desatualizado só pela versão diz só "O feedback será refeito." (paralela) | #482 |
| #466 | Cartão "Carga e forma do dia" | #483 |
| #467 | Cartões "Esforços" e "Treino de transição" | #484 |
| #465 | Cartão "Comparado com o seu normal" | #485 |
| #468 | Guia [[produto/meta-12-como-rodar]], glossário, [[00-inicio]], diário | #486 |
| #487 | Textos da FC ("acima/abaixo da mediana") e de "aprendendo" | #488, #489, #490 |
| #469 | QA de ponta a ponta, `tests/test_e2e_meta12.py`, tela viva | #492 |
| #470 | Resultado da meta e roteiro | este |

Em aberto, fora do fechamento: #472 (comparação de hospedagem, login e custo para a Meta 13; segue com o Angelo).

## Decisões (regra de produto)
**Do Angelo (17/11, "ok para as seis" e "sim para as quatro" da #455):** `linha_base@3` antes de o atleta ver o "fora do normal"; carga e
CTL, ATL e TSB em números, sem gráfico; rótulo de transição corrigível pelo atleta; login e deploy = Meta 13; agente = Meta 14.

**Do Theo (17/11):**
- **Contrato** (PRs #476 e #480): `valor_texto` no `MetricaBaseOut`; a carga manda `valor_texto`, `metodo_texto` e o `texto` do motivo
  prontos; 1 casa com vírgula, feita pela API, e o TSB com o sinal de menos U+2212; `transicao.editavel` vem da API (o app não decide pela
  modalidade); bloco novo `forma_do_dia`, calculado na leitura pela mesma `calcular_serie`, só para o dia local do treino.
- **`409` da transição:** com `editavel = false` (`outra`, `multiesporte_pai`, `troca`), o `PUT` e o `DELETE` respondem `409` e não gravam.
- **`feedback_prompt@9`:** só os números dos exemplos G02 e G04 mudaram, por causa da `@3`; regras e tom iguais à `@8`
  ([[modulos/camada-llm]]).
- **Pisos também em melhor tiro e melhor pace:** o piso de 4 bpm vale para `fc_media` e `fc_melhor_tiro`; o de 3% para `pace_medio` e
  `melhor_pace`; o de 5% para `carga_hora`.
- **QA:** aceitas as capturas de `qa-viva/` e o design-ok da Lia feitos sobre o clone anterior ao #488 (a única diferença é a frase da FC,
  coberta por testes).

## O que não foi verificado
- **Celular de verdade** (Expo Go, iOS, Android, toque): amarrado ao ensaio (decisão 10 da Meta 11). Tela vista no navegador em 390 px.
- **Leitor de tela real:** rótulos e ordem conferidos nos testes e na revisão da Lia, não com VoiceOver ou TalkBack.
- **Login:** não existe; qualquer um que abra a tela corrige o rótulo de transição (pergunta B, aceito pelo Angelo até a Meta 13).
- **Aluno real:** nenhum, além da conferência local na máquina do Angelo, com nada no repositório.
- **Feedback dos treinos reais com a `@3`:** os textos já gerados localmente para os treinos do Angelo ainda usam a `@2`; não foram
  refeitos. O `@9` do prompt vale para os próximos.

## O que ficou de fora
Como planejado: gráfico da série de carga; tela da evolução e #213; motivo de falta; resumos; login e deploy (Meta 13); agente (Meta 14);
alerta de qualquer tipo; celular de verdade. **Decidido (pergunta C, Angelo 17/11) e ainda não implementado; vira issue paralela da Meta 13:** a correção da transição deixar o feedback
`desatualizado`.

## Limitações conhecidas
Detalhes em [[design/telas/treino]], [[metricas/linha-base]] e no guia. Todas em texto genérico.
- **Sem login, a correção da transição é de quem abrir a tela** (pergunta B); o rótulo é reversível (`DELETE`).
- **A correção da transição não marca o feedback como desatualizado** (pergunta C): o feedback já gerado pode citar a linha de base de
  antes da correção.
- **A `@3` corta o "fora" causado só por dispersão pequena,** não por poucas amostras acima do mínimo nem por relevância esportiva
  (pergunta D).
- **`sem_carga` com motivo e carga `pendente` pelo banco** não aparecem com as fixtures da Meta 7; estão só nos testes (guia, "Não rodado").

## Achados
Todos genéricos; nada do dado real.
- **Conferência local da `@3`:** a redução do "fora do normal" foi pequena; os números ficam só em `entregas/`. Virou a pergunta D.
- **Texto pronto com concordância errada** ("abaixo que a mediana"), achado ao escrever o guia e de novo na QA: #487, corrigido no #488.
- **O guia abria a tela por `127.0.0.1`,** que o CORS recusa; a QA trocou para `localhost` (PR #492).
- **A versão nova da linha de base mudou exemplos em cadeia:** oráculos das Metas 7 e 9, exemplos do prompt (`@9`) e da ADR 0013; o
  aprendizado da Meta 11 (procurar a string antiga no app) foi seguido (#489).
- **Sugestão em aberto da revisão:** o esforço de 1000 m sai como "1 · 1000 m"; a spec desenha "1 · 1 km". A Duda decide se o texto muda
  na API.

## O que se aprendeu
- **Spec com a lista de campos antes do contrato funcionou:** a Lia escreveu o que cada cartão precisa; a Duda conferiu campo a campo e o
  Theo decidiu o contrato num comentário só. As telas saíram em sequência, sem retrabalho de contrato.
- **Tela viva contra a API de verdade dentro da QA** pegou o que as capturas da API falsa não pegam (CORS, texto vindo do backend). Fica
  como padrão de toda tela nova, junto das capturas por comando.
- **Versão nova de métrica mexe em textos aprovados de outro módulo** (exemplos do feedback). Quem sobe a versão procura também nos
  exemplos do LLM e nas ADRs.
- **Perguntas que aparecem no meio da meta seguem com a recomendação valendo** ("a confirmar" na spec e no guia, depois respondidas pelo Angelo com "ok para as quatro") e não pararam o time.
- **Texto pronto da API precisa de revisão de português** como a tela tem revisão visual: a Lia revisou as frases do app, não as da API.

## PRECISA DO ANGELO
**Respondidas em 17/11:** o Angelo disse **"ok para as quatro"** (A a D), todas com a recomendação. Ficam aqui como registro; a C ainda não está implementada e vira issue paralela da Meta 13 (o Paulo abre).
- **A. Forma do dia em "aprendendo".** *Recomendação:* esconder CTL, ATL e TSB e mostrar só o aviso (é o que está no `main`).
  Alternativa: mostrar os números com o selo "ainda aprendendo".
- **B. Quem corrige a transição sem login.** *Recomendação:* aceitar na Meta 12 que qualquer um que abra a tela corrija, e fechar na
  Meta 13 com o login (só o atleta dono do treino corrige; o professor segue pela caixa).
- **C. Feedback depois de corrigir a transição.** *Recomendação:* o feedback já gerado fica `desatualizado` e é refeito, pelo mesmo
  caminho do check-in editado. **Não implementado**; com o "sim", vira uma issue pequena da Meta 13 (ou paralela).
- **D. Manter a `linha_base@3` ou buscar uma regra nova.** A conferência local mostrou redução pequena do "fora do normal" (números só em
  `entregas/`). *Recomendação:* manter a `@3` até haver uso real para calibrar; investigar uma regra nova (piso ou limite maior, ou mínimo
  por tipo) depois do ensaio. Alternativa: investigar agora, como paralela.
- **Termos do provedor sobre o uso dos dados para treinar modelos** (item 10 de "A confirmar" da ADR 0013): segue não conferido por nós.

## Resultado
**Meta 12 feita, com cinco itens não verificados** (celular de verdade, leitor de tela real, login, aluno real e o feedback dos treinos
reais com a `@3`). Com fixtures sintéticas, o atleta abre um treino e vê os esforços, o comparado com o normal dele pela `linha_base@3`, a
carga e a forma do dia em números como estimativa, e o rótulo de transição, que ele corrige ou desfaz; o app só mostra o que a API manda. A
tela tem teste por estado, capturas por comando, capturas da tela viva e design-ok da Lia sobre a tela rodando. Versões no fechamento:
`linha_base@3`, `feedback_prompt@9`, `atencao@2`; migrações até 0016 (nenhuma nova nesta meta).

Próxima: Meta 13, login e deploy do piloto, **proposta** ([[produto/roadmap]], seção "Meta 13"), esperando as decisões do Angelo.
