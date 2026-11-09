---
tipo: meta
status: em-uso
dono: paulo
atualizado: 2026-11-09
links: [[produto/roadmap]], [[produto/meta-7-como-rodar]], [[decisoes/0011-linha-de-base-e-semana-padrao]], [[decisoes/0004-contrato-tela-evolucao]], [[metricas/tipo-treino]], [[metricas/linha-base]], [[metricas/tipo-linha-base-oraculo]], [[design/telas/semana-padrao]], [[modulos/banco]], [[modulos/api]], [[modulos/api-client]], [[modulos/mobile]], [[produto/metas/meta-6-carga-treino]], [[diario/2026-11-09]]
---
# Meta 7: linha de base pessoal e semana-padrão

> **Situação: em andamento.** O código e a documentação principais estão no main (PRs #275 a #289, em 09/11). Faltam a conferência local com o
> histórico real (#269), a QA de ponta a ponta (#271) e o resultado da meta (#272). Esta nota é um retrato de 09/11, escrito junto do guia; o Paulo a
> completa no fechamento.

## Objetivo
Comparar cada treino com o **normal do próprio atleta**, só na mesma modalidade e no mesmo tipo de treino: uma linha de base móvel (mediana da janela) e uma medida
robusta de quanto a sessão fugiu do normal. O tipo de treino vem da **semana-padrão** que o atleta ou o treinador definem (um tipo por dia da semana e modalidade); a
regra automática só entra como reserva para dia sem plano. A linha de base compara com o histórico; não diz se o treino foi bom ou ruim. Regras na [[decisoes/0011-linha-de-base-e-semana-padrao]].

## Entrega visível
- `GET` e `PUT /atletas/{id}/semana-padrao` e a **tela da semana-padrão** no app (web): vigência, "Quem definiu", treinos de cada dia e histórico de vigências.
- O tipo de cada atividade com a origem (`professor`, `trainingpeaks`, `semana_padrao`, `sugestao`) e a divergência quando o formato contradiz o plano, em `GET /atletas/{id}/atividades/{id}`.
- O objeto `linha_base` nesse mesmo `GET` (`linha_base@2`): por métrica, valor, mediana, desvio, `z`, quantos treinos entraram, estado (`dentro`, `fora`, `aprendendo`, `sem_valor`) e texto pronto.
- Passo a passo, com as saídas esperadas, em [[produto/meta-7-como-rodar]].

## Decisões (regra de produto)
**Do Angelo (09/11):** início frio só com "ainda aprendendo"; o tipo vem do atleta ou do treinador por dia da semana (semana-padrão); "ok para as sete" da ADR 0011;
"ok para as quatro" do adendo 2 (`linha_base@2`: janela de 12 semanas com mínimo de 8, transição com base própria, carga por hora, intervalado sem série de 1 km pela FC média
e carga por hora, com o esforço curto de fora). Detalhes em [[diario/2026-11-09]].
**Do Theo:** modelo de dados da ADR 0011; o `PUT` reaplica o tipo só de `vigente_desde` em diante; linha de base calculada na leitura e nunca gravada.

## O que foi entregue
| Issue | Entrega | PR |
|---|---|---|
| #274 | Roteiro com a Meta 7 replanejada | #275 |
| #260 | ADR 0011 ([[decisoes/0011-linha-de-base-e-semana-padrao]]) | #277 |
| #261 | Fixtures de 12 semanas e oráculo ([[metricas/tipo-linha-base-oraculo]]) | #278 |
| #267 | Desenho da tela ([[design/telas/semana-padrao]]) | #279 |
| #262 | `tipo_treino@1` ([[metricas/tipo-treino]]) | #280 |
| #263 | `linha_base@1` ([[metricas/linha-base]]) | #281 |
| #264 | Migração 0011, `GET` e `PUT` da semana-padrão, cliente regerado | #282 |
| #265 | Tipo pela semana-padrão em `classificar_atividades` e no `PUT` | #284 |
| #268 | Tela da semana-padrão no app ([[modulos/mobile]]) | #285 |
| #266 | `linha_base`, tipo e divergência no `GET` da atividade | #286 |
| #288 | `linha_base@2` | #289 |
| #270 | Guia [[produto/meta-7-como-rodar]], diário e esta nota | este |

## O que não foi verificado
- **Conferência com o histórico real (#269):** depende do dado real, fora do git, e da semana-padrão do Angelo no banco local.
- **App em celular:** a tela foi vista só na web, com a API real e com a API falsa (os estados forçados), com testes de componente.
- **QA de ponta a ponta (#271):** é da Bia.

## O que ficou de fora
Como decidido: valores da literatura no início frio; professor com login e vínculo (a `definido_por` é só rótulo declarado); ciclismo sem velocidade média e natação sem pace por 100 m na linha de base;
o melhor esforço curto do `intervalado` sem série de 1 km; janela maior para o tipo raro; hífen sem quebra no estado vazio da tela; taxa de "fora do normal" a revisar (#269).
