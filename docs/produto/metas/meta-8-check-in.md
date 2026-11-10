---
tipo: meta
status: em-uso
dono: paulo
atualizado: 2026-11-10
links: [[produto/roadmap]], [[produto/meta-8-como-rodar]], [[decisoes/0012-check-in-pos-treino]], [[decisoes/0010-carga-de-treino]], [[decisoes/0004-contrato-tela-evolucao]], [[metricas/carga-pse]], [[metricas/carga-pse-oraculo]], [[design/telas/checkin]], [[design/telas/treino]], [[modulos/banco]], [[modulos/api]], [[modulos/api-client]], [[modulos/mobile]], [[modulos/worker]], [[produto/metas/meta-7-linha-de-base-semana-padrao]], [[diario/2026-11-09]], [[diario/2026-11-10]], [[glossario]]
---
# Meta 8: check-in pós-treino

> **Situação: feita.** Código, documentação e QA no `main` (PRs #304 a #318, entre 09/11 e 10/11). A Bia conferiu o critério de
> pronto com `tests/test_e2e_meta8.py` (15 testes, só dado sintético, sem rede) e seguiu o [[produto/meta-8-como-rodar]] do zero,
> num clone limpo com Postgres próprio: passos 1 a 14 iguais ao guia, nenhum bug no código (#301, PR #317). A
> [[decisoes/0012-check-in-pos-treino]] foi **aceita em 10/11** (PR #305): modelo aprovado pelo Theo e "ok para as cinco" do Angelo
> no "A confirmar". Fechamento: #302. Fica como **não verificado** abrir a tela num celular de verdade (Expo Go), que depende do Angelo.

## Objetivo
Registrar o **check-in depois de cada treino em 3 toques**: esforço percebido (PSE de 0 a 10), sensação em 5 níveis e observação (atalhos ou texto, com
"nada a relatar" como resposta válida). Com a PSE, uma carga pela PSE (`carga_pse@1`, PSE x minutos, em UA), separada da carga do relógio, que dá carga também à natação.
O check-in é dado de saúde: só no banco local, nunca em log, e com comando para apagar.

## Entrega visível
- `PUT`, `GET` e `DELETE /atletas/{id}/atividades/{id}/checkin`; prazo de 7 dias para criar, edição e apagar sem prazo ([[modulos/api]]).
- `checkin`, `checkin_aberto`, `pse_sugerida` e `carga_pse` no `GET` da atividade, e `GET /atletas/{id}/checkins/pendentes`.
- A tela de check-in (criar em 3 toques, editar, apagar), a lista de pendentes e os cartões na tela do treino ([[design/telas/checkin]], [[modulos/mobile]]).
- `worker.apagar_checkin` ([[modulos/worker]]).
- Passo a passo, com as saídas esperadas, em [[produto/meta-8-como-rodar]].

## Critério de pronto
Resultado de cada item conforme a QA da Bia na #301 (PR #317), contra o `main` em `b8f7cf2`, só com fixtures sintéticas, mais o que
mudou depois (ADR aceita, #318).

| Item | Onde | Resultado |
|---|---|---|
| ADR 0012 aprovada pelo Theo antes da migração, com propostas de produto em "A confirmar" | #293 | **ok**. Modelo de dados aprovado pelo Theo no PR #305 antes da migração 0012 (#310); "ok para as cinco" do Angelo no "A confirmar" em 10/11; status **aceita** (PR #305). Na QA, ainda "parcial": o arquivo da ADR só entra no `main` com o #305 |
| Check-in completo em 3 toques; "nada a relatar" válido; editar e apagar; uma atividade nunca tem dois check-ins | #296, #299 | **ok**. Teste de componente que conta os toques (`TelaCheckin.test.tsx`), tela na web com um só `PUT`, índice único por atividade; e2e 01, 06 e 12 |
| Observação como dado de saúde: só no banco local, nunca em log, só ao próprio atleta, comando para apagar | #296, #298, #299 | **ok**. `422` sem eco da entrada, texto marcador fora do log, outro atleta dá `404`, `worker.apagar_checkin` (e2e 05, 07, 13 e 14); no app, nada em log, URL ou armazenamento |
| Nota em `docs/metricas/` e teste de valor à mão da `carga_pse@1` | #294, #297 | **ok** ([[metricas/carga-pse]], [[metricas/carga-pse-oraculo]]; e2e 09 e 10) |
| Endpoints no OpenAPI, adendo da ADR 0004, cliente regerado | #296, #298 | **ok** (adendo 8 da [[decisoes/0004-contrato-tela-evolucao]]; e2e 15) |
| Tela com teste e revisão da Lia | #295, #299 | **ok**. `npm test` com 225 testes; design-ok da Lia no PR #313 (sem bloqueantes) |
| Aberta pelo menos uma vez num celular pelo Angelo, no fim da meta | #301 | **não verificado** (depende do Angelo; ver abaixo) |
| QA com fixtures num clone limpo, seguindo só o guia | #301 | **ok**. Passos 1 a 14 iguais ao guia, inclusive os 12 estados forçados da API falsa abertos na tela |
| Testes | todos | `uv run pytest` com 1705 testes verdes e 2 pulados no QA (15 novos em `tests/test_e2e_meta8.py`); `npm test` com 225 |

## O que foi entregue
| Issue | Entrega | PR |
|---|---|---|
| #293 | ADR 0012 ([[decisoes/0012-check-in-pos-treino]]), aceita em 10/11 | #305 |
| #294 | Fixtures sintéticas de check-in e oráculo ([[metricas/carga-pse-oraculo]]) | #307 |
| #297 | `carga_pse@1` como função pura ([[metricas/carga-pse]]) | #308 |
| #295 | Desenho da tela de check-in e da lista de pendentes ([[design/telas/checkin]]) | #309 |
| #296 | Migração 0012 (`checkin_treino`), `PUT`/`GET`/`DELETE`, `worker.apagar_checkin`, cliente regerado | #310 |
| #298 | `checkin`, `carga_pse`, `checkin_aberto` e `pse_sugerida` no `GET` da atividade; lista de pendentes | #311 |
| #306 | Fixture de atividades do app com os campos novos do cliente regerado | #312 |
| #299 | Tela de check-in, pendentes e cartões na tela do treino ([[modulos/mobile]]) | #313 |
| #300 | Guia [[produto/meta-8-como-rodar]], diário [[diario/2026-11-09]] e o retrato desta nota | #315 |
| #301 | QA de ponta a ponta e `tests/test_e2e_meta8.py` | #317 |
| #316 | Texto da carga pela PSE em minutos e segundos quando a duração não é inteira (achado do guia) | #318 |
| #302 | Resultado da meta e roteiro | este |

Paralelas, fora do critério de pronto: #303 (hífen sem quebra em "semana-padrão" no estado vazio, PR #304) e termos novos no
[[glossario]] com a Meta 8 no [[00-inicio]] (PR #314).

## Decisões (regra de produto)
**Do Angelo (09/11, "ok para as cinco"):** abrir as issues e começar; 3 toques com PSE de 0 a 10 (CR-10), sensação em 5 níveis e
observação por atalhos (dor, cansaço, sono ruim, calor, trabalho ou estresse) com texto livre e "nada a relatar"; `carga_pse@1` = PSE x
minutos, por atividade, separada da `carga@2` e sem série diária; ele abre a tela no celular uma vez no fim da meta; a observação segue a
regra dos dados de saúde da Meta 6.

**Do Angelo (10/11, "ok para as cinco" do "A confirmar" da ADR 0012):**
1. prazo de **7 dias** para registrar; editar e apagar sem prazo;
2. toda atividade pede check-in, menos o registro geral ("pai") do multiesporte e as trocas; no multiesporte, **um check-in por parte**,
   com a PSE da parte anterior oferecida como ponto de partida;
3. PSE, sensação e observação **obrigatórias** (inclusive "nada a relatar");
4. nome na tela **"Carga pela PSE"**, em **UA**, nunca "pontos";
5. check-in **sem login** enquanto é piloto local; identidade na Meta 10.

**Do Theo:** modelo de dados da ADR 0012 (`checkin_treino` com um check-in por atividade, `CHECK` nas escalas e na coerência de "nada a
relatar", atalhos em colunas, sem coluna nova em `atividade`); `carga_pse@1` calculada na leitura e nunca gravada; `checkin_aberto` e
`pse_sugerida` no `GET` da atividade (respostas às dúvidas de desenho da #295); o caminho mínimo fecha em 3 toques e, com atalho ou texto,
são 4 (para permitir vários atalhos); a edição em tela única com "Mudar".

## O que não foi verificado
- **Tela de check-in num celular de verdade:** o critério pedia que o Angelo abrisse a tela uma vez pelo Expo Go, na rede de casa, com dado
  sintético. **Ainda não foi feito.** A tela foi vista só na web (API real e API falsa) e com testes de componente; nenhuma tela do app foi
  aberta num iOS ou Android até aqui. Segue em "PRECISA DO ANGELO".
- **Leitor de tela real:** a acessibilidade foi conferida no código e nos testes (papéis, rótulos, anúncio da pergunta seguinte), não com
  VoiceOver ou TalkBack.
- **Fontes da ADR 0012** (Borg, Foster): citadas, ainda não abertas nos textos (mesma pendência das ADRs 0008 e 0011).

## O que ficou de fora
Como planejado: lembrete por WhatsApp ou e-mail; check-in semanal; motivo de falta do treino planejado que não aconteceu; equipamento e
zona no check-in; série diária e CTL/ATL pela PSE; o check-in no motor de explicação e no feedback (Meta 9); o professor vendo o check-in e
a identidade de quem grava (Meta 10).

**Pendências que viram candidatas** (ver [[produto/roadmap]], "Candidatas sem número"):
- **Capturas do check-in no tema escuro e nos estados de erro** (rafa-app, com a Lia): item 4, não bloqueante, da revisão da Lia no #313.
  Aberta como paralela da Meta 9 (#334).
- **"Salvar alterações" desligado sem dizer por quê** na edição (item 5 da revisão da Lia; aceito como está).
- **`carga_pse@2` pelo tempo total** (caio-ciencia): a `carga_pse@1` usa o cronômetro; o tempo corrido não é gravado na importação.
- **Série diária da carga pela PSE e comparação com a `carga@2`** (caio-ciencia).
- **Motivo de falta**, **lembrete** (conta ou serviço novo: "PRECISA DO ANGELO" quando chegar a vez) e **check-in semanal**.

## Limitações conhecidas
Detalhes na [[decisoes/0012-check-in-pos-treino]], seção "Limitações", e em [[metricas/carga-pse]]. Todas em texto genérico.
- **Sem login:** "só ao próprio atleta" é o `atleta_id` da rota; quem conhece o id lê, grava e apaga. Aceito no piloto local.
- **A carga pela PSE usa o cronômetro**, não o tempo total.
- **Sem histórico de edições** e sem check-in do multiesporte inteiro (só por parte).
- **O relógio é o real:** os pendentes e o prazo dependem de "hoje"; as fixtures valem para o dia em que foram carregadas (o `carregar.py`
  do guia desloca as datas).
- **Validado com fixtures sintéticas.** Não há conferência com o histórico real: o check-in é dado novo.

## Achados
- **A ADR só foi aceita depois de todo o código.** O modelo de dados foi aprovado pelo Theo no comentário do PR #305 e a migração
  seguiu; o "A confirmar" ficou aberto até 10/11. O time trabalhou com os cinco padrões, e eles valeram sem mudança. Custo: o arquivo
  da ADR ficou fora do `main` a meta inteira, então os links `[[decisoes/0012-check-in-pos-treino]]` não resolviam, e o guia, a nota do
  módulo do app e esta nota diziam "proposta".
- **O texto da carga pela PSE não fechava à mão.** Rodando o guia, a Nina viu "6 x 45,4 min = 272,5 UA" (minutos arredondados, valor
  pelos segundos). A #316 entrou no mesmo dia (PR #318): "6 x 45 min 25 s = 272,5 UA". Fórmula e versão não mudaram.
- **Um ajuste do app fora do plano.** O cliente regerado pelo #311 trouxe campos novos e a fixture do app parou no `tsc` (#306, PR #312).
- **A conferência visual dependeu do navegador.** A extensão caiu no meio do guia; a Nina conferiu os estados forçados só por `curl`, e
  a Bia os abriu na tela depois com um navegador local por script.
- **Revisão da Lia com um ajuste visual dentro do próprio PR** (#313): cabeçalho com "52 min", tela "Check-in salvo" e o cartão com prazo
  vencido; a Nina pediu as capturas refeitas antes do docs-ok.

## O que se aprendeu
- **Modelo de dados aprovado e ADR aceita são duas etapas.** Separar as duas deixou o código andar; da próxima vez, entrar com a ADR no
  `main` como `proposta` logo depois da aprovação do modelo, para os links resolverem, e trocar o status quando o Angelo responder.
- **A seção "A confirmar" com padrões funcionou pela terceira meta seguida:** cinco respostas de uma vez, nenhuma mudou o código, porque
  os padrões ficaram em um só lugar no app (`src/checkin/escala.ts`) e na API.
- **Rodar o guia acha o que o teste não acha:** a conta da carga pela PSE estava certa nos testes e errada para quem lê.
- **Dúvidas de desenho respondidas pelo Theo antes da tela** (#295 antes da #299) viraram campos da API (`checkin_aberto`, `pse_sugerida`):
  o app não precisou calcular prazo nem elegibilidade.
- **Métrica calculada na leitura** (como a `linha_base` e agora a `carga_pse`) segue sem migração nem recálculo quando o check-in muda.
- **Passo que depende do Angelo fica para o fim e fica pendente.** O celular estava no critério desde o começo e é o único item aberto;
  na próxima meta, marcar a sessão com ele junto da QA, e não depois.

## PRECISA DO ANGELO
- **Abrir a tela de check-in no celular** (Expo Go, rede de casa, dado sintético), uma vez. Pendente da Meta 8; decidido pelo Angelo em
  10/11: junto com o cartão de feedback, na QA da Meta 9 (#332), numa só sessão.
- **Informação, sem decisão:** o caminho mínimo do check-in ("Nada a relatar") fecha em 3 toques; com atalho ou texto são 4, para permitir
  marcar vários atalhos (Theo, 09/11).
- **Meta 9 (feedback automático por treino):** respondida em 10/11 ("ok" às oito decisões; o feedback é texto, sem áudio). Issues #322 a
  #335; ver [[produto/roadmap]].

## Resultado
**Meta 8 feita.** Com fixtures sintéticas, o atleta registra o check-in de um treino em 3 toques (PSE, sensação e observação, com "nada a
relatar"), edita e apaga; a API devolve o check-in, a carga pela PSE (`carga_pse@1`, em UA, também na natação), se o check-in ainda está
aberto e a lista de pendentes dos últimos 7 dias; o check-in segue a regra do dado de saúde e tem comando para apagar. Não verificado: a
tela num celular de verdade.

Próxima: Meta 9, feedback automático por treino (em curso desde 10/11; [[produto/roadmap]]).
