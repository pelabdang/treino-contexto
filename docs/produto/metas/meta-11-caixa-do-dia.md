---
tipo: meta
status: em-uso
dono: paulo
atualizado: 2026-11-17
links: [[produto/roadmap]], [[produto/meta-11-como-rodar]], [[decisoes/0015-caixa-do-dia-do-professor]], [[decisoes/0004-contrato-tela-evolucao]], [[decisoes/0011-linha-de-base-e-semana-padrao]], [[metricas/atencao]], [[metricas/atencao-oraculo]], [[metricas/linha-base]], [[design/telas/caixa-do-dia]], [[modulos/api]], [[modulos/api-client]], [[modulos/banco]], [[modulos/worker]], [[modulos/mobile]], [[produto/metas/meta-10-recuperacao]], [[diario/2026-11-16]], [[glossario]]
---
# Meta 11: caixa do dia do professor

> **Situação: feita, com quatro itens não verificados** (celular de verdade, leitor de tela real, login e aluno real; todos fora por decisão
> do Angelo de 16/11). Código, documentação, QA e conferência local no `main` (PRs #433 a #459, entre 16/11 e 17/11). A Bia conferiu o
> critério de pronto com `tests/test_e2e_meta11.py` (24 testes, um por item, só dado sintético, sem rede) e seguiu o
> [[produto/meta-11-como-rodar]] do zero com um Postgres descartável (#429, PR #450). A Lia deu **design-ok sobre a tela rodando** (na QA,
> com um ajuste pequeno feito no PR #453). A [[decisoes/0015-caixa-do-dia-do-professor]] foi **aceita em 16/11** (PR #435), antes da
> migração 0016 (PR #436). Fechamento: #430.

## Objetivo
O professor abre a **caixa do dia** e vê os seus alunos ordenados por "precisa de atenção", com o motivo em uma linha, e os treinos novos
com o tipo sugerido, que ele **confirma ou corrige em lote**. No piloto local: sem login (professor fixo por configuração), só atletas
fictícios com vínculo e consentimento registrados.

## Entrega visível
- A tela "Caixa do dia" no app web (Expo web), só por endereço direto: lista de atenção, detalhe do treino, seleção e folha de tipo,
  salvar em lote ([[design/telas/caixa-do-dia]], [[modulos/mobile]]).
- `GET /professores/{id}/caixa-do-dia` e `PUT /professores/{id}/tipos-de-treino`, no OpenAPI, com o cliente regerado (adendo 11 da
  [[decisoes/0004-contrato-tela-evolucao]], [[modulos/api]]).
- `PROFESSOR_ID` no ambiente, `worker.carregar_professor --fixtures` e a migração 0016 ([[modulos/worker]], [[modulos/banco]]).
- `npm run capturas`: capturas da web por comando, num navegador sem janela, sem a extensão (390x844 e 1280, claro e escuro).
- Passo a passo em [[produto/meta-11-como-rodar]].

## Critério de pronto
Resultado de cada item conforme a QA da Bia na #429 (PR #450), só com fixtures sintéticas, mais o que entrou depois (#453, #457, #459). Os
números entre parênteses são os testes de `tests/test_e2e_meta11.py`.

| Item | Onde | Resultado |
|---|---|---|
| ADR 0015 aprovada pelo Theo antes de qualquer migração; "A confirmar" com padrões; tabela "o que muda a caixa e quando" | #419 | **ok**. Modelo aprovado e ADR no `main` (PR #435) antes da migração 0016 (PR #436); o Angelo respondeu "ok para as 7" de "A confirmar" (e2e 01 e 02) |
| Regra de atenção como função pura, nota em `docs/metricas/` e oráculo sobre fixtures sintéticas à mão; só o que o código já calcula; sem causa | #421, #422 | **ok** ([[metricas/atencao]], [[metricas/atencao-oraculo]]; PRs #438 e #441). Hoje em `atencao@2` (#454, PR #457), depois da conferência local |
| Atleta sem vínculo, ou com vínculo sem consentimento, nunca aparece na caixa nem nos treinos dele | #423 | **ok** (e2e 06 a 09: consentimento nulo, no futuro, retirado, de outro professor, sem vínculo; no `GET` e no `PUT`). Mutação: tirar a condição de consentimento derruba 9 dos 24 |
| A correção do professor vence a sugestão e a semana-padrão e não é desfeita pela reimportação nem por versão nova da regra | #425 | **ok** (PR #440; e2e 16 a 23) |
| Endpoints no OpenAPI, adendo da ADR 0004 e cliente regerado | #424, #425 | **ok** (PRs #442, #440 e #445; e2e 10 a 15) |
| Tela com teste e revisão da Lia sobre as capturas do comando e sobre a tela rodando | #418, #420, #426, #427 | **ok**. Capturas por comando (PR #434), telas (PRs #444 e #447), design-ok da Lia sobre a tela rodando na QA, com um ajuste pequeno (folga da barra de lote, foco do fundo da folha, frase do feedback pendente; #452, PR #453) |
| Testes e CI sem rede; nada de dado de saúde em log | todos | **ok** (guarda de socket no e2e; o log da caixa leva só `professor_id` e contagens; a rota não chama o modelo de linguagem, e2e 13) |
| QA com fixtures num clone limpo, seguindo só o guia; registrado que nada disso é login nem celular de verdade | #428, #429 | **ok**. Passos 1 a 8 com os números do guia; a única diferença (passo 7 sem `CORS_ORIGENS`) virou a #449, corrigida no PR #451 |
| Conferência local com a conta do Angelo, com nada no repositório | #431 | **ok** (PR #456). Limitações genéricas no guia e em [[metricas/atencao]]; dois achados resolvidos na `atencao@2`; um virou a #455 (em aberto) |
| Testes | todos | `uv run pytest` no `main` em `5074d20`: 2819 verdes e 2 pulados (SQLite local, rodado no fechamento; 24 em `tests/test_e2e_meta11.py`); `npm test` com 333 (PR #453) |

## O que foi entregue
| Issue | Entrega | PR |
|---|---|---|
| #417 | Roteiro com a Meta 11 em curso e as decisões do Angelo de 16/11 | #433 |
| #418 | `npm run capturas` (Playwright só em `devDependencies`, fora do CI obrigatório) | #434 |
| #419 | ADR 0015 ([[decisoes/0015-caixa-do-dia-do-professor]]), aceita em 16/11 | #435 |
| #423 | `PROFESSOR_ID`, filtro de vínculo e consentimento, migração 0016, `carregar_professor` | #436 |
| #420 | Spec da caixa do dia ([[design/telas/caixa-do-dia]]); só por endereço direto; ícones da folha em tokens | #437, #443, #446 |
| #421 | Fixtures sintéticas (professor e 8 atletas fictícios) e oráculo | #438 |
| #425 | `PUT` em lote do tipo de treino pelo professor | #440 |
| #422 | `atencao@1` como função pura | #441 |
| #424 | `GET` da caixa do dia; data do adendo 11 da ADR 0004 | #442, #445 |
| #426 | Tela: lista de atenção | #444 |
| #427 | Tela: confirmar e corrigir em lote | #447 |
| #428 | Guia [[produto/meta-11-como-rodar]], glossário, [[00-inicio]], diário | #448 |
| #429 | QA de ponta a ponta e `tests/test_e2e_meta11.py` | #450 |
| #449 | `CORS_ORIGENS` no passo 7 do guia | #451 |
| #452 | Ajustes da revisão da Lia na tela rodando | #453 |
| #431 | Conferência local; limitações genéricas | #456 |
| #454 | `atencao@2`: aviso de check-in numa linha por aluno, sem a modalidade `outra` | #457 |
| #458 | O "hoje" e o prazo do check-in pela data local, com teste nas viradas do dia | #459 |
| (sem issue) | Diário e [[00-inicio]] de 16/11 | #439 |
| #430 | Resultado da meta e roteiro | este |

Paralela, fora do critério: #382 (botões do check-in fixos ao marcar atalho, PR #432). Em aberto, fora do fechamento: #455 e #402.

## Decisões (regra de produto)
**Do Angelo (16/11, "ok para as 10"):** sem login, professor fixo por configuração; só atletas fictícios; sem vínculo ou consentimento,
nunca aparece; a conta dele ligada a um professor de teste só no banco local; quatro motivos de atenção (divergência da semana-padrão, fora
do normal, dor no check-in, check-in perto do fim do prazo); o professor vê tipo, PSE, sensação, atalhos, feedback e a observação livre, que
nunca vai ao provedor de LLM; a correção do professor vence e não é desfeita; devolutiva, revisão de amostra, nome do professor, grupo e
ficha completa ficam fora; celular de verdade amarrado ao ensaio. Dependência só de desenvolvimento para as capturas. **Na ADR 0015
(16/11):** "ok para as 7" de "A confirmar".

**Do Theo:** modelo de dados da ADR 0015 (quem confirmou e quando, `feedback_treino.tipo_visto`); 404 uniforme para professor e atleta fora
do filtro; `PUT` tudo ou nada; escopo da `atencao@2` (adendo 1 da ADR 0015: só o aviso da caixa muda).

## O que não foi verificado
- **Celular de verdade** (Expo Go, iOS, Android, toque): fora por decisão do Angelo (decisão 10), amarrado ao ensaio com professor e atletas.
  As capturas e a revisão da Lia foram no navegador de computador, em 390 px.
- **Leitor de tela real** (VoiceOver, TalkBack): o foco e os rótulos foram conferidos nos testes e na revisão da Lia, não com leitor de tela.
- **Login:** não existe. O `PROFESSOR_ID` não é autenticação; serve só à máquina local.
- **Aluno real:** nenhum além da conferência local na máquina do Angelo, com nada no repositório.

## O que ficou de fora
Como planejado: login e contas de verdade, deploy e banco gerenciado; dado de outro aluno real; ficha completa do aluno; rascunho de
devolutiva e roteiros do manual; revisão de amostra do feedback pelo professor e feedback com o nome dele; semana-padrão por grupo; aviso por
WhatsApp ou e-mail; painel da coordenação; alerta de recuperação baixa; motivo de falta; celular de verdade.

## Limitações conhecidas
Detalhes na [[decisoes/0015-caixa-do-dia-do-professor]], em [[metricas/atencao]] e no guia. Todas em texto genérico.
- **"Fora do normal" herda a `linha_base@2`:** com poucas amostras do tipo, ou com dispersão muito pequena, o `z` sai grande e o limite não
  mede relevância esportiva (#455, em aberto).
- **A regra só enxerga o que foi ingerido:** sem treinos novos, a lista fica parada.
- **"Dor" e "divergência" só têm teste sintético:** a conferência local não os exercitou; a regra da divergência fica como está até 4 semanas
  de uso.
- **Sem comando para carregar os treinos sintéticos da Meta 11:** o guia usa um script próprio no passo 4.
- **Sem login:** o professor é o da configuração; qualquer outro número devolve o mesmo 404.

## Achados
Todos genéricos; nada do dado real.
- **A conferência local achou ruído no aviso de check-in:** um aviso por treino e a modalidade `outra` entrando na conta. Virou a
  `atencao@2` (#454): uma linha por aluno, sem `outra`.
- **A caixa expôs um ponto fraco de uma métrica antiga:** o "fora do normal" vem da `linha_base@2`; com poucas amostras do tipo ou dispersão muito pequena, o `z` pode sair grande; o limite não mede relevância esportiva; investigação na #455 (em aberto,
  com perguntas ao Angelo antes de qualquer versão nova).
- **O "hoje" dependia do relógio do teste:** entre 21h e meia-noite de Brasília o dia UTC já virou; o e2e montava as datas em UTC e
  falhava nessa janela, e a frase de prazo do detalhe usava o relógio, não o "hoje" da requisição (#458). Hoje o fuso é sempre
  `America/Sao_Paulo`, com teste às 20h, 23h e 01h.
- **O passo da tela no guia não tinha sido rodado por quem escreveu:** faltava `CORS_ORIGENS` (#449), achado pela QA.
- **Versão nova da regra deixou a string antiga em fixtures do app:** `apps/mobile/__fixtures__/caixaDoDia.ts` e
  `apps/mobile/scripts/api-falsa.mjs` ainda dizem `atencao@1` (pendência do Rafa); as notas foram corrigidas neste PR.
- **As capturas por comando funcionaram:** 76 capturas no padrão (19 rotas, 2 tamanhos, 2 temas) em cerca de 80 s, e a tela foi vista
  durante a meta, não no fim.

## O que se aprendeu
- **Capturas por comando tiraram a conferência visual do fim da meta.** Pela primeira vez desde a Meta 8, a Lia revisou a tela rodando dentro
  da QA, e o ajuste dela entrou antes do fechamento. Fica como passo padrão de toda tela nova.
- **Um consumidor novo de uma métrica antiga mostra os pontos fracos dela.** A `linha_base@2` era só da API; na caixa, o "fora do normal"
  virou motivo de atenção e ficou visível. Antes de mostrar uma métrica a um público novo (o atleta, na próxima meta de telas), conferir a
  métrica com o dado real.
- **Datas "de hoje" são do fuso do atleta, e o teste fixa o relógio nas viradas.** Teste que depende da hora em que roda é teste frágil.
- **Versão nova de regra procura a string antiga também no app** (fixtures e API falsa), não só no backend e nas notas.
- **Quem escreve o guia roda o passo da tela**, agora que as capturas dispensam a extensão.
- **"A confirmar" com padrões funcionou pela sexta meta seguida** ("ok para as 7" na ADR 0015).

## PRECISA DO ANGELO
- **#455:** as perguntas sobre uma `linha_base@3`. Até a resposta, o "fora do normal" segue na `@2`.
- **Meta 12:** proposta e perguntas no [[produto/roadmap]] ("Meta 12, proposta"). Nenhuma issue da Meta 12 foi aberta.
- **Termos do provedor sobre o uso dos dados para treinar modelos** (item 10 de "A confirmar" da ADR 0013): segue não conferido por nós.

## Resultado
**Meta 11 feita, com quatro itens não verificados** (celular de verdade, leitor de tela real, login e aluno real, todos fora por decisão).
Com fixtures sintéticas, o professor do piloto (`PROFESSOR_ID`) vê só os atletas com vínculo e consentimento, ordenados pela `atencao@2`
com o motivo em uma linha, abre o detalhe do treino (com a observação, que nunca vai ao provedor), e confirma ou corrige o tipo em lote; a
correção vence a sugestão e a semana-padrão e não é desfeita. A tela tem teste, capturas por comando e design-ok da Lia sobre a tela rodando.
Versões no fechamento: `atencao@2`; migrações até 0016.

Próxima: Meta 12, **proposta**, esperando o "ok" do Angelo ([[produto/roadmap]]).
