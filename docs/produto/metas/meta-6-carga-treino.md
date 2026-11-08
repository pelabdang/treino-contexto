---
tipo: meta
status: em-uso
dono: paulo
atualizado: 2026-11-08
links: [[produto/roadmap]], [[produto/meta-6-como-rodar]], [[decisoes/0010-carga-de-treino]], [[decisoes/0008-deteccao-de-esforcos]], [[metricas/carga-treino]], [[metricas/serie-carga]], [[metricas/carga-oraculo]], [[metricas/conferencia-carga]], [[metricas/tiros-1km]], [[modulos/grafico-carga]], [[modulos/banco]], [[modulos/worker]], [[modulos/api]], [[modulos/api-client]], [[modulos/ingestao-garmin]], [[produto/metas/meta-5-deteccao-esforcos]], [[diario/2026-11-07]], [[diario/2026-11-08]]
---
# Meta 6: carga de treino

> **Situação: feita.** Código, documentação e QA no main (PRs #241 a #258). A Bia conferiu o critério de pronto com
> `tests/test_e2e_meta6.py` (20 testes, só dado sintético) e depois seguiu o [[produto/meta-6-como-rodar]] de ponta a ponta,
> com Postgres próprio e só fixtures: passos 1 a 9 iguais ao guia, nenhum bug (#146, PR #258). A conferência com o histórico
> real foi feita localmente (#144), com os números só em `entregas/`. Fechamento: #147. Ficam registrados como não
> verificados o que depende do dado real e qualquer tela (a carga não tem tela).

## Objetivo
A primeira métrica derivada de carga: a carga de cada atividade (rTSS pelo pace, hrTSS pela FC) e, dia a dia,
condicionamento (CTL), fadiga (ATL) e forma (TSB), sempre mostrados como **estimativa**. O limiar vem dos dados de saúde da
exportação Garmin e nunca é estimado. Regras na [[decisoes/0010-carga-de-treino]].

## Entrega visível
- `GET /atletas/{atleta_id}/carga`: a série diária de CTL, ATL e TSB (`serie_carga@1`), com a carga de cada dia, o aviso
  `aprendendo` e quantas atividades ficaram sem carga, por motivo.
- O objeto `carga` em `GET /atletas/{atleta_id}/atividades/{atividade_id}`: `calculada`, `sem_carga` (com o motivo) ou
  `pendente`. A API nunca devolve limiar, zonas, recordes nem a carga do Garmin.
- Os comandos `worker.importar_saude` (também chamado no fim do `importar_garmin`), `worker.calcular_carga` (idempotente,
  `carga@2`), `worker.grafico_carga` (PNG e CSV em `entregas/`), `worker.conferir_carga` (conferência com a carga do Garmin,
  só descritiva) e `worker.apagar_saude` (LGPD).
- Passo a passo, com as saídas esperadas, em [[produto/meta-6-como-rodar]].

## Critério de pronto
Resultado de cada item conforme a QA da Bia na #146 (PR #258), com a exportação sintética das fixtures da carga, sem rede.

| Item | Onde | Resultado |
|---|---|---|
| ADR 0010 aprovada pelo Theo (tabelas, fórmula por modalidade, versão, o que fazer sem FC, pace ou limiar) | #134 | **ok**. Aceita em 07/11; status "implementada" em 08/11 (#145) |
| Dados de saúde lidos e guardados, idempotentes e com vigência (limiar, zonas, FC máxima e de repouso, recordes, carga do Garmin) | #135, #136, #140, #174 | **ok**. Reimportar dá `inseridas=0` em toda a saúde |
| rTSS, hrTSS e CTL/ATL/TSB com nota em `docs/metricas/` e teste com valor à mão (oráculo) | #137, #138, #139 | **ok**. 13 atividades calculadas e 7 sem carga, iguais ao [[metricas/carga-oraculo]]; série de 43 dias igual ao oráculo |
| Cálculo idempotente e versionado; mudar a versão ou o limiar recalcula | #141, #255 | **ok**. Segunda rodada sem mudança; atividade em `carga@1` volta para `carga@2` |
| Sem dado suficiente fica "sem carga" com o motivo; atleta sem saúde fica "sem carga", sem estimar limiar; a série diz quantas ficaram de fora | #141, #142 | **ok**. Seis motivos; atleta sem saúde dá `sem_dados_saude` e série vazia com `sem_carga_calculada` |
| `multiesporte_pai` e `troca` fora da carga, sem contar em dobro | #141 | **ok** |
| Conferência com a carga do Garmin com fixtures e, localmente, com o histórico real | #144 | **ok** com fixtures (CSV e resumo); a do histórico real foi local, com os números só em `entregas/` |
| Endpoint no OpenAPI e cliente regerado | #142 | **ok** (`cargaDoAtleta`, [[modulos/api]], [[modulos/api-client]]) |
| QA com fixtures num clone limpo, seguindo só o guia | #146 | **ok**. Passos 1 a 9 iguais ao guia; nenhuma divergência de conteúdo |
| Testes | todos | `uv run pytest -q` com 1302 testes verdes no QA (20 novos em `tests/test_e2e_meta6.py`); o app não mudou |

## O que foi entregue
| Issue | Entrega | PR |
|---|---|---|
| #134 | ADR 0010, carga de treino ([[decisoes/0010-carga-de-treino]]) | #241 |
| #135 | Formato dos dados de saúde da exportação Garmin e fixtures sintéticas ([[modulos/ingestao-garmin]]) | #242 |
| #136 | Leitor dos dados de saúde, função pura | #244 |
| #137 | Fixtures de algumas semanas e oráculo da carga ([[metricas/carga-oraculo]]) | #245 |
| #138 | rTSS e hrTSS por volta (`carga@1`, [[metricas/carga-treino]]) | #249 |
| #139 | CTL, ATL e TSB diários (`serie_carga@1`, [[metricas/serie-carga]]) | #248 |
| #140 | `limiar_atleta` e `zona_fc_atleta` (migração 0008) e `worker.importar_saude` ([[modulos/banco]], [[modulos/worker]]) | #246 |
| #174 | `recorde_pessoal` e `carga_garmin_dia` (migração 0009) e `worker.apagar_saude` | #247 |
| #141 | `carga_atividade` (migração 0010) e `worker.calcular_carga` | #251 |
| #142 | `GET /atletas/{id}/carga`, `carga` na atividade e cliente regerado | #253 |
| #143 | Gráfico e CSV da carga, `worker.grafico_carga` ([[modulos/grafico-carga]]) | #252 |
| #144 | Conferência com a carga do Garmin, `worker.conferir_carga` ([[metricas/conferencia-carga]]) | #254 |
| #255 | `carga@2`: FC média da atividade quando nenhuma volta tem FC | #256 |
| #145 | Guia [[produto/meta-6-como-rodar]], ADR 0010 "implementada", diários [[diario/2026-11-07]] e [[diario/2026-11-08]] | #257 |
| #146 | QA de ponta a ponta e `tests/test_e2e_meta6.py` | #258 |
| #147 | Resultado da meta e roteiro | este |

Paralela, na mesma meta (fora do critério de pronto):

| Issue | Entrega | PR |
|---|---|---|
| #243 | `tiros_1km@6`: vizinho de 950 m ou mais separado por parada de 15 s ou mais deixa de cortar o tiro ([[metricas/tiros-1km]], adendo da [[decisoes/0008-deteccao-de-esforcos]]) | #250 |

## Decisões (regra de produto)
**Do Angelo:**
- **04/11:** o limiar vem dos dados de saúde da exportação Garmin, sem estimar; atleta sem esses dados fica "sem carga"; pode
  guardar todos os dados de saúde, só no banco local; conferir a carga com o histórico real localmente.
- **07/11, as sete propostas da ADR 0010 ("sim" para todas):** esteira e ciclismo só por hrTSS; rTSS preferido ao hrTSS
  quando os dois valem; cobertura mínima de 95% das voltas; "aprendendo" com menos de 42 dias e série sem semente; a série
  termina na última atividade importada; natação sem carga mesmo com FC; conferência com o Garmin só descritiva, sem faixa
  de aprovação.
- **07/11, tiros de 1 km (#243):** o vizinho de 950 m ou mais separado por parada de 15 s ou mais não corta o tiro
  (`tiros_1km@6`); mínimo de 2 tiros mantido; velocidade habitual do ciclismo como está (12 semanas, pedais de 30 min ou
  mais, mínimo de 10).
- **08/11, `carga@2` (#255):** no hrTSS, quando nenhuma volta tem FC e a atividade tem FC média, a atividade entra como volta
  única. FC em parte das voltas segue a cobertura de 95%.

**Do Theo:**
- **ADR 0010 (07/11):** cinco tabelas de saúde e carga; tabela própria no lugar de uma `metrica_derivada` genérica; CTL, ATL
  e TSB calculados na leitura; `importar_garmin` chama a saúde e a carga no fim (erro vira aviso); `multiesporte_pai` e
  `troca` sem linha; `worker.apagar_saude` para a LGPD.
- **Leitor de saúde (#136):** FC igual a 0 não vira registro; valor igual ao vigente não abre vigência nova; faixas de
  plausibilidade (FC de 30 a 250 bpm, velocidade de 0,5 a 10 m/s).
- **Recordes (#174):** unidade `s`, `m`, `W`, `passos` ou nula; o vigente de cada tipo é o de data mais recente, sem flag.
- **Carga por atividade (#141):** o casamento JSON x FIT pega o par mais próximo primeiro (corrige a troca de um
  multiesporte que tomava o FIT da parte seguinte).
- **API (#142):** a série sai sem arredondar (a tela decide as casas); `pendente` para atividade elegível sem linha ou com
  versão antiga; nenhum dado de saúde pela API.
- **Conferência (#144):** só lê o banco, sem rede; o terminal mostra só contagens; duas leituras dos dias, a da ADR (descarta
  dia com atividade sem carga) e a complementar (todos os dias).

## O que não foi verificado
- **Conferência com o histórico real (#144)** não foi conferida pela Bia: depende do dado real, fora do git.
- **Tela:** a carga não tem tela no app; só a API e o gráfico em `entregas/`. Nada a abrir no navegador nem nos aparelhos.
- **Zonas de FC e recordes** estão guardados, mas nenhuma métrica os usa ainda; a leitura deles foi conferida só com as
  fixtures.

## O que ficou de fora
Como planejado: linha de base pessoal (Meta 7); estimar o limiar do histórico; NGP e ajuste de subida; leitura da série por
segundo; TSS por potência; sTSS e carga por PSE na natação (o check-in é a Meta 8); ajuste por calor com o clima da Meta 4;
**tela da carga no app**; motor de explicação; hrTSS por zonas e `segmento.zona`.

**Pendências fora da meta** (abertas ou a abrir, sem prioridade sobre a Meta 7; ver [[produto/roadmap]], "Candidatas"):
- **Tela da carga no app** (rafa-app, com a Lia): sem issue.
- **Duas observações da Bia sobre o guia** (nina-docs, opcionais, sem issue): o passo 9 cria um segundo atleta na importação de
  saúde, e o texto não diz que o `--atleta-id 1` continua sendo o primeiro; o `export DATABASE_URL` pode virar prefixo
  `env DATABASE_URL=...` para quem não quer exportar.
- **#213** e **#237** (rafa-app, com a Lia): visual e acessibilidade da tela de evolução e da tela de um treino.
- **#74** (vault do Graphify, `docs/_grafo/`): quando o Theo pedir o grafo.

## Limitações conhecidas
Detalhes em [[metricas/carga-treino]], [[metricas/serie-carga]] e [[metricas/conferencia-carga]], seção "Limitações". Todas
em texto genérico, sem nada do histórico.
- **Por volta, sem ajuste de subida nem de calor:** a subida deixa o pace lento e subestima a carga; a descida faz o
  contrário. `IF²` por volta subestima treinos com variação dentro da volta.
- **Volta única da `carga@2`:** quando a carga vem da FC média da atividade, treinos variáveis ficam subestimados.
- **hrTSS pela razão direta** ignora FC de repouso e deriva cardíaca; a FC de limiar da fonte pode ser a da corrida e
  subestimar o ciclismo.
- **Esteira só por FC; natação e `outra` sem carga:** a série subestima a carga dos dias com essas atividades, e por isso eles
  ficam marcados.
- **"Aprendendo" nos primeiros 42 dias:** o CTL ainda está subindo da semente zero; os números saem mesmo assim.
- **A conferência com o Garmin não prova que a carga está certa:** escalas diferentes, correlação alta esperada por
  construção, dias descartados não aleatórios e possível diferença de um dia entre o dia UTC do Garmin e o nosso dia local.
- **Mudar um limiar regrava** também as atividades que tentaram o rTSS e caíram no hrTSS ou em `sem_pace`, com o mesmo
  resultado (a entrada da conta mudou). Inofensivo; documentado no teste 13 do e2e (observação da Bia).
- **Validado com um atleta.**

## Achados
- **Um caso de origem que o oráculo não tinha.** Arquivos em que a volta não traz FC, mas a atividade traz a FC média, davam
  `sem_fc` na `carga@1`. Virou a `carga@2` (#255) no dia seguinte, sem migração: a versão na linha e o `calcular_carga`
  recalculando por versão deixaram a mudança barata.
- **Testes presos à versão quebraram o CI.** No PR da `carga@2` três testes ainda esperavam o texto `carga@1`; o docs-ok
  esperou a correção. Teste de comportamento compara com a constante `VERSAO`; só o teste da versão fixa o texto.
- **O QA começou antes do guia.** A Bia escreveu o e2e contra o main enquanto a #145 estava aberta e depois seguiu o guia
  publicado. Funcionou e encurtou a meta, mas o fechamento só valeu com o guia seguido.

## O que se aprendeu
- **ADR com as propostas de produto numa lista "A confirmar"** deixou o Angelo responder as sete de uma vez, e as issues de
  código seguiram sem esperar.
- **Dado fisiológico tem regra própria desde a ADR:** só no banco local, nunca em log nem pela API, com um comando para apagar.
  Escrever isso na ADR evitou discussão em cada PR.
- **Duas trilhas que só se encontram num ponto** (saúde e banco com a Duda; fórmulas e oráculo com o Caio; encontro na #141)
  fecharam a meta em três dias.
- **Versão na linha gravada** (`carga@N`, como `esforcos@N`) segue sendo o jeito barato de mudar uma regra depois da entrega.
- **O roteiro com "aberta" e "feita" só no fechamento** funcionou: não houve tabela defasada durante a meta.
- **A conferência com o dado real em paralelo, com só o genérico no repositório,** funcionou pela terceira vez.

## PRECISA DO ANGELO
- Nenhuma decisão da Meta 6 em aberto.
- Para a Meta 7 (linha de base), três decisões de produto entram como propostas na ADR, como na Meta 6; ver
  [[produto/roadmap]], "PRECISA DO ANGELO".

## Resultado
**Meta 6 feita.** Com fixtures sintéticas, os dados de saúde da exportação Garmin entram no banco com vigência, cada atividade
ganha a sua carga (rTSS ou hrTSS) ou um motivo para não ter, e a série diária de CTL, ATL e TSB sai pela API, num gráfico e
numa conferência com a carga do Garmin, tudo idempotente e versionado. Não verificados: o que depende do dado real; a carga
ainda não tem tela.

Próxima: Meta 7, linha de base pessoal ([[produto/roadmap]]).
