---
tipo: meta
status: em-uso
dono: paulo
atualizado: 2026-11-09
links: [[produto/roadmap]], [[produto/meta-7-como-rodar]], [[decisoes/0011-linha-de-base-e-semana-padrao]], [[decisoes/0004-contrato-tela-evolucao]], [[metricas/tipo-treino]], [[metricas/linha-base]], [[metricas/tipo-linha-base-oraculo]], [[design/telas/semana-padrao]], [[design/tokens]], [[modulos/banco]], [[modulos/api]], [[modulos/api-client]], [[modulos/mobile]], [[produto/metas/meta-6-carga-treino]], [[diario/2026-11-09]], [[glossario]]
---
# Meta 7: linha de base pessoal e semana-padrão

> **Situação: feita.** Código, documentação e QA no main (PRs #275 a #291, todos em 09/11). A Bia conferiu o critério de
> pronto com `tests/test_e2e_meta7.py` (42 testes, só dado sintético, sem rede) e seguiu o [[produto/meta-7-como-rodar]] do
> zero, num clone limpo com Postgres próprio: passos 1 a 10 iguais ao guia, nenhum bug (#271, PR #291). A conferência com o
> histórico real foi feita localmente (#269), com os números só em `entregas/`. Fechamento: #272. Ficam como não verificados
> o app em celular e o que depende do dado real.

## Objetivo
Comparar cada treino com o **normal do próprio atleta**, só na mesma modalidade e no mesmo tipo de treino: uma linha de base
móvel (mediana da janela) e uma medida robusta de quanto a sessão fugiu do normal. O tipo de treino vem da **semana-padrão**
que o atleta ou o treinador definem (um tipo por dia da semana e modalidade); a regra automática só entra como reserva para
dia sem plano. A linha de base compara com o histórico; não diz se o treino foi bom ou ruim. Regras na
[[decisoes/0011-linha-de-base-e-semana-padrao]].

## Entrega visível
- `GET` e `PUT /atletas/{id}/semana-padrao` e a **tela da semana-padrão** no app (web): vigência, "Quem definiu", treinos de
  cada dia e histórico de vigências.
- O tipo de cada atividade com a origem (`professor`, `trainingpeaks`, `semana_padrao`, `sugestao`) e a divergência quando o
  formato contradiz o plano, em `GET /atletas/{id}/atividades/{id}`.
- O objeto `linha_base` nesse mesmo `GET` (`linha_base@2`): por métrica, valor, mediana, desvio, `z`, quantos treinos
  entraram, estado (`dentro`, `fora`, `aprendendo`, `sem_valor`) e texto pronto.
- Passo a passo, com as saídas esperadas, em [[produto/meta-7-como-rodar]].

## Critério de pronto
Resultado de cada item conforme a QA da Bia na #271 (PR #291), contra o main em `d4ec053`, só com fixtures sintéticas.

| Item | Onde | Resultado |
|---|---|---|
| ADR 0011 aprovada antes da migração, com a seção "A confirmar" respondida | #260 | **ok**. Modelo aprovado pelo Theo no PR #277; "ok para as sete" e "ok para as quatro" (adendo 2); status "implementada" |
| Notas em `docs/metricas/` com oráculo sobre fixtures de 12 semanas e uma vigência que muda | #261, #262, #263 | **ok** ([[metricas/tipo-treino]], [[metricas/linha-base]], [[metricas/tipo-linha-base-oraculo]]) |
| Semana-padrão gravada e lida pela API e pela tela; mudar o plano não reescreve o passado | #264, #265, #268 | **ok**. `atividades_reaplicadas` 46, 8 e 0 no guia; tela na web com três vigências |
| Tipo nunca sobrescreve o confirmado, `professor` ou `trainingpeaks`; plano vence a regra; dia sem plano cai na regra; divergência só como dado; idempotente e versionado | #262, #265 | **ok**. Os 81 tipos das fixtures iguais ao oráculo |
| Série de tiros igual (regressão) | #265 | **ok** (`tiros_1km@6`) |
| "Ainda aprendendo" abaixo de 8 treinos do tipo em 12 semanas; tipos e modalidades não se misturam; sem tipo sem linha de base, com motivo; a sessão fora da própria base | #263, #266, #288 | **ok** |
| Endpoints no OpenAPI, adendos 6 e 7 da ADR 0004, cliente regerado | #264, #266, #288 | **ok** |
| Tela com teste e revisão da Lia | #267, #268 | **ok**. `npm test` com 154 testes; design-ok da Lia no PR #285 |
| QA com fixtures num clone limpo, seguindo só o guia | #271 | **ok**. Passos 1 a 10 iguais ao guia |
| Conferência local com o histórico real | #269 | feita localmente; não conferida pela Bia (dado fora do repo) |
| Testes | todos | `uv run pytest` com 1476 testes verdes e 1 pulado no QA (42 novos em `tests/test_e2e_meta7.py`); `npm test` com 154 |

## O que foi entregue
| Issue | Entrega | PR |
|---|---|---|
| #274 | Roteiro com a Meta 7 replanejada em torno da semana-padrão | #275 |
| #260 | ADR 0011 ([[decisoes/0011-linha-de-base-e-semana-padrao]]) | #277 |
| #261 | Fixtures de 12 semanas e oráculo ([[metricas/tipo-linha-base-oraculo]]) | #278 |
| #267 | Desenho da tela ([[design/telas/semana-padrao]]) | #279 |
| #262 | `tipo_treino@1` ([[metricas/tipo-treino]]) | #280 |
| #263 | `linha_base@1` ([[metricas/linha-base]]) | #281 |
| #264 | Migração 0011, `GET` e `PUT` da semana-padrão, cliente regerado | #282 |
| #265 | Tipo pela semana-padrão em `classificar_atividades` e no `PUT` | #284 |
| #268 | Tela da semana-padrão no app ([[modulos/mobile]]) | #285 |
| #266 | `linha_base`, tipo e divergência no `GET` da atividade | #286 |
| #288 | `linha_base@2` (adendo 2 da ADR 0011, adendo 7 da ADR 0004) | #289 |
| #269 | Conferência local com o histórico real | sem PR (relatório em `entregas/`, fora do git) |
| #270 | Guia [[produto/meta-7-como-rodar]], diário [[diario/2026-11-09]] e o retrato desta nota | #290 |
| #271 | QA de ponta a ponta e `tests/test_e2e_meta7.py` | #291 |
| #272 | Resultado da meta e roteiro | este |

Paralelas, fora do critério de pronto: #273 (guia da Meta 6, PR #276), termos novos no [[glossario]] (PR #283) e ícones da
tela conferidos em [[design/tokens]] (PR #287).

## Decisões (regra de produto)
**Do Angelo (09/11):**
- **As cinco perguntas da #147:** abrir as issues; início frio só com "ainda aprendendo", sem valores da literatura; janela de
  8 semanas com mínimo de 8 (depois 12 semanas, abaixo); limite "fora do normal" proposto na ADR. **Mudou o rumo:** o tipo de
  treino vem do atleta ou do treinador, por dia da semana (semana-padrão), com a regra só como reserva.
- **"Ok para as sete" da ADR 0011:** a tela pergunta "Quem definiu" (atleta já marcado, rótulo sem login); o plano vence quando
  o formato o contradiz, e o treino fica marcado como divergente; limite `|z| >= 2,5` com textos sem juízo de valor; tipo raro
  segue a regra por ora; o plano vale para o treino de maior duração do dia; `PUT` sem login aceito no piloto local; a parte de
  transição fora da linha de base (substituída pelo adendo 2).
- **"Ok para as quatro" do adendo 2 (`linha_base@2`):** janela de 12 semanas com mínimo de 8 (com 8 semanas, um treino perdido
  mandava o tipo semanal de volta a "ainda aprendendo"); a parte de treino de transição com base própria; carga por hora no
  lugar da carga absoluta (a absoluta cresce com a duração e acaba medindo volume); no `intervalado` sem série de 1 km, FC média
  e carga por hora, com o melhor esforço curto de fora.

**Do Theo:** modelo de dados da ADR 0011 (semana-padrão por atleta com vigência; `tipo_versao` e `tipo_divergencia` em
`atividade`); o `PUT` reaplica o tipo só de `vigente_desde` em diante; linha de base calculada na leitura e nunca gravada;
textos prontos na API (a API formata, o app mostra).

## O que não foi verificado
- **Conferência com o histórico real (#269):** feita no banco local, com a semana-padrão do Angelo; não conferida pela Bia,
  porque depende do dado real, fora do git.
- **App em celular:** a tela foi vista só na web, com a API real e com a API falsa, e com testes de componente. Nenhuma tela do
  app foi aberta num iOS ou Android até aqui.

## O que ficou de fora
Como planejado: semana-padrão por grupo; login de professor e vínculo (a `definido_por` é só rótulo declarado); confirmação em
lote e a caixa das divergências (Meta 10); treino planejado com duração, zona ou equipamento; TrainingPeaks; motor de
explicação; valores da literatura no início frio; **tela da linha de base no app**; `moderado` e `fartlek` pela regra; ciclismo
sem velocidade média e natação sem pace por 100 m na linha de base; linha de base de CTL/ATL/TSB e da semana.

**Pendências que viram candidatas** (sem prioridade sobre a Meta 8; ver [[produto/roadmap]], "Candidatas sem número"):
- **Limite de "fora do normal" ou métrica por tipo** (caio-ciencia): rever se a taxa de sessões "fora" ficar acima do esperado.
- **Janela maior para tipo raro** (caio-ciencia): tipo quinzenal ou mais raro segue em "aprendendo".
- **Esforço curto no `intervalado` sem série de 1 km** (caio-ciencia).
- **Hífen sem quebra** em "semana-padrão" no estado vazio da tela (rafa-app): hoje quebra em "semana-" e "padrão". Virou
  a paralela da Meta 8 (#303).
- **App em celular:** entrou no critério da Meta 8 (#301).
- **Tela da linha de base no app**, **#213**, **#237** (rafa-app, com a Lia) e **#74** (vault do Graphify).

## Limitações conhecidas
Detalhes em [[metricas/tipo-treino]], [[metricas/linha-base]] e na ADR 0011, seção "Limitações". Todas em texto genérico.
- **Um item por modalidade por dia:** dois treinos da mesma modalidade com tipos diferentes no mesmo dia não cabem no plano; o
  plano vale para o de maior duração.
- **Divergência só na corrida:** `intervalado` sem esforço e `leve`/`longo` com tiros.
- **Constantes únicas para todos os atletas** (`LEVE_MIN_S`, `LONGO_MIN_S`, `PISO_REL`), ainda sem calibração.
- **Tipo raro em "aprendendo"** e **esforço curto do `intervalado` fora**, como acima.
- **`definido_por` não é verificado:** é o que a pessoa declara na tela.
- **Validado com um atleta.**

## Achados
- **O rumo mudou antes da largada.** A quarta resposta do Angelo trocou o tipo sugerido pela semana-padrão; o roteiro foi
  refeito no mesmo dia, antes de qualquer issue de código, e a meta entrou com tela, API e banco que não estavam no plano de 08/11.
- **Um adendo depois do código.** A `linha_base@2` saiu depois da `linha_base@1` já no main, sem migração, porque a linha de
  base é calculada na leitura.
- **O roteiro ficou para trás do adendo.** A QA achou o critério de pronto do roteiro ainda com 8 semanas e `linha_base@1`
  (corrigido nesta #272).
- **`worker.reclassificar` com fixtures sem voltas** apaga os blocos e as sugestões, porque refaz os blocos pelas voltas. O guia
  roda esse passo num segundo atleta, com FIT sintéticos.

## O que se aprendeu
- **Refazer o roteiro logo que a resposta muda o rumo** custa pouco; as issues abertas no mesmo dia foram feitas no mesmo dia.
- **A seção "A confirmar"** funcionou pela segunda meta seguida: sete respostas de uma vez e mais quatro no adendo.
- **Métrica calculada na leitura** (como a `serie_carga@1` e agora a `linha_base`) deixa mudar a regra sem migração nem
  recálculo em lote.
- **Adendo que muda um número do critério de pronto atualiza também o roteiro**, no mesmo PR.
- **Tela com spec da Lia antes** (#267 antes da #268) deu à revisão visual um texto para comparar: uma rodada de ajustes e o
  design-ok no mesmo PR.
- **Fixtures precisam do mesmo formato que o comando que as lê:** sem voltas, o `reclassificar` não serve; documentar no guia.

## PRECISA DO ANGELO
- Nenhuma decisão da Meta 7 em aberto: as cinco perguntas, as sete do "A confirmar" e as quatro do adendo 2 foram respondidas
  em 09/11, e a semana-padrão dele foi cadastrada no banco local.
- Para a Meta 8 (check-in pós-treino), as cinco perguntas foram respondidas em 09/11 ("ok para as cinco"); issues #293 a #303.
  Ver [[produto/roadmap]], "PRECISA DO ANGELO".

## Resultado
**Meta 7 feita.** Com fixtures sintéticas, o atleta ou o treinador definem a semana-padrão pela tela ou pela API, cada atividade
recebe o tipo do plano (ou o da regra, no dia sem plano) com a origem e a divergência, e o `GET` da atividade devolve a linha de
base pessoal (`linha_base@2`) de cada métrica do tipo, com o aviso "ainda aprendendo" e textos prontos, tudo idempotente e
versionado. Não verificados: o app em celular e o que depende do dado real; a linha de base ainda não tem tela.

Próxima: Meta 8, check-in pós-treino ([[produto/roadmap]]).
