---
tipo: meta
status: em-uso
dono: paulo
atualizado: 2026-11-06
links: [[produto/roadmap]], [[produto/meta-5-como-rodar]], [[decisoes/0008-deteccao-de-esforcos]], [[decisoes/0009-treino-de-transicao]], [[decisoes/0004-contrato-tela-evolucao]], [[decisoes/0005-serie-de-tiros-o-que-entra]], [[metricas/esforcos]], [[metricas/esforcos-oraculo]], [[metricas/tiros-1km]], [[metricas/transicao]], [[modulos/banco]], [[modulos/worker]], [[modulos/api]], [[modulos/api-client]], [[modulos/ingestao-garmin]], [[modulos/mobile]], [[design/telas/treino]], [[produto/metas/meta-4-clima-atividade]], [[diario/2026-11-06]]
---
# Meta 5: detecção de esforços

> **Situação: feita.** Código, documentação e QA no main (PRs #209 a #239). A Bia rodou o
> [[produto/meta-5-como-rodar]] num clone limpo, com Postgres descartável e só fixtures sintéticas, e o critério de pronto
> bateu (#172, PR #239, com `tests/test_e2e_meta5.py`). A conferência com o histórico real foi feita localmente (#169), com o
> relatório só em `entregas/`. Fechamento: #173. Ficam registrados como não verificados a tela no navegador e nos aparelhos,
> o `downgrade` das migrações e o que depende do dado real.

## Objetivo
Cada treino lido como blocos (aquecimento, esforços, recuperações, desaquecimento, treino leve), com esforços de qualquer
distância na corrida e por duração no ciclismo, laps automáticos do mesmo esforço juntados e a recuperação reconhecida pela
pausa. Treinos contínuos fortes marcados como treinos-chave. A série de tiros de 1 km passa a sair dos esforços e mostra o
melhor tiro de cada sessão. Regras na [[decisoes/0008-deteccao-de-esforcos]].

## Entrega visível
- O objeto `esforcos` em `GET /atletas/{atleta_id}/atividades/{atividade_id}`: versão (`esforcos@1`), treino-chave, se a
  referência foi a da própria atividade e os blocos com textos prontos (duração, distância, pace ou velocidade).
- O comando `uv run python -m worker.detectar_esforcos`, idempotente; a importação e o upload de FIT também detectam
  (pelo `classificar_atividades`, o único ponto).
- A série de tiros `tiros_1km@5`, visão dos esforços (faixa `d1000`, mínimo de 2 tiros, treino misto conta), com o **melhor
  pace** e a **FC do melhor tiro** como valores principais no JSON, no PNG/CSV e na tela de evolução.
- Paralelas entregues na mesma meta: o treino de transição (rótulo sugerido e corrigível, com listar, comparar e corrigir
  pela API; [[decisoes/0009-treino-de-transicao]]), a tela de um treino com o clima no app ([[design/telas/treino]]) e o
  subtipo do multiesporte (pai e troca).
- Passo a passo, com as saídas esperadas, em [[produto/meta-5-como-rodar]].

## Critério de pronto
Resultado de cada item conforme o relatório da Bia na #172 (PR #239), com as fixtures de `tests/fixtures/garmin/esforcos/`
e `tests/fixtures/multiesporte/`, sem rede.

| Item | Onde | Resultado |
|---|---|---|
| ADR 0008 (detecção de esforços) aprovada pelo Theo | #148 | **ok**. Aceita; decisões de implementação da #166 registradas nela |
| Oráculo sintético à mão; blocos, corrida por distância, ciclismo por duração e treino-chave com teste de valor à mão | #161 a #165, #172 | **ok**. Blocos da API iguais ao oráculo nos FIT 1 a 6; o FIT 7 só bate importado sozinho (ver "Achados") |
| Lap cortado no mesmo ritmo vira um esforço; aquecimento e desaquecimento nunca são esforço | #162, #172 | **ok**. Testes no `test_e2e_meta5.py` |
| Detecção idempotente e versionada (`esforcos@1`) | #166, #172 | **ok**. Segunda rodada com `sem mudança` em todas; versão nova detecta de novo |
| Série de tiros pelos esforços (mínimo de 2, treino misto conta, esteira fora) e regressão das regras anteriores | #168, #172 | **ok**. `@4` no banco dá `reclassificacao_pendente: true`; depois do `worker.reclassificar`, as sessões do guia com melhor pace e FC do melhor tiro; regressão da `@4` em [[metricas/tiros-1km]] |
| Melhor pace e FC do melhor tiro no JSON, no PNG/CSV e na tela | #151 a #154, #172 | **ok** no JSON, PNG e CSV; tela pelo `npm test` (ver "Não verificado") |
| OpenAPI declarado e cliente regerado | #167 | **ok** ([[modulos/api]], [[modulos/api-client]]) |
| QA com fixtures num clone limpo, seguindo só o guia | #172 | **ok**. Passos 1 a 9 rodados; três divergências do guia, nenhuma é bug, corrigidas no próprio guia |
| Conferência local com o histórico real, números só em `entregas/` | #169 | **ok**, local. No repositório só as limitações genéricas (abaixo); nenhuma constante nem regra mudou |
| Testes | todos | `uv run pytest -q` com 1023 testes verdes no QA (14 novos em `tests/test_e2e_meta5.py`); `npm test` com 104 testes em 10 suítes |

## O que foi entregue
| Issue | Entrega | PR |
|---|---|---|
| #148 | ADR 0008, detecção de esforços ([[decisoes/0008-deteccao-de-esforcos]]) | #180 |
| #161 | Fixtures sintéticas e oráculo dos esforços ([[metricas/esforcos-oraculo]]) | #187 |
| #162 | Blocos do treino: pausas, laps juntados, aquecimento e desaquecimento ([[metricas/esforcos]]) | #188 |
| #163 | Esforços de corrida por distância (`d200` a `d5000`) | #200 |
| #164 | Esforços de ciclismo por duração (`t1` a `t60`) | #205 |
| #165 | Treino-chave contínuo | #210 |
| #151 | Melhor tiro da sessão na agregação | #178 |
| #152 | Melhor pace e FC do melhor tiro no contrato (ADR 0004) e na API | #185 |
| #153 | Melhor pace no PNG e no CSV | #199 |
| #154 | Melhor pace como valor principal na tela | #201 |
| #166 | `bloco_atividade` (migração 0006) e `worker.detectar_esforcos` ([[modulos/banco]], [[modulos/worker]]) | #222 |
| #167 | Objeto `esforcos` na atividade e cliente regerado | #226 |
| #168 | `tiros_1km@5`, a série como visão dos esforços (absorveu #149 e #150) | #228 |
| #169 | Conferência local com o histórico real; limitações genéricas nas notas | #235 |
| #171 | Guia [[produto/meta-5-como-rodar]], notas conferidas e [[diario/2026-11-06]] | #238 |
| #172 | QA de ponta a ponta e `tests/test_e2e_meta5.py` | #239 |
| #173 | Resultado da meta e roteiro | este |

Paralelas, na mesma meta (fora do critério de pronto):

| Issue | Entrega | PR |
|---|---|---|
| #132 | `importar_garmin` sem rede por padrão; clima só com `--com-clima` | #160 |
| #133 | Identidade do FIT avulso importado depois do JSON | #186 |
| #183 | `worker.reclassificar_subtipo` (subtipo `NULL` ou divergente) | #184 |
| #155 | ADR 0009, treino de transição ([[decisoes/0009-treino-de-transicao]]) | #214 |
| #156 | Regra `transicao@1` ([[metricas/transicao]]) | #223 |
| #157 | `rotulo_transicao` (migração 0007) e `worker.sugerir_transicao` | #229 |
| #170 | Treino de transição: listar, comparar e corrigir pela API (adendo 4 da ADR 0004) | #232 |
| #158 | Campos prontos na atividade: data, hora, duração, pace e atribuição do clima (adendo 2 da ADR 0004) | #212 |
| #216 | `distancia` pronta na atividade, natação em metros (adendo 3 da ADR 0004) | #231 |
| #159, #219, #233 | Tela de um treino com o clima, estados e a distância da API ([[modulos/mobile]]) | #215, #225, #234 |
| #220 | Spec da tela de um treino ([[design/telas/treino]]) | #221 |
| #217 | Botão "Ver treino" na sessão selecionada da evolução | #227 |
| #202 | Tela de evolução com ícones, esqueleto e lista tocável | #211 |
| #218 | HTML do app web volta a trazer o script do bundle; `npm run verificar:web` | #224 |
| #230 | Multiesporte: subtipos `multiesporte_pai` e `troca` e `worker.reclassificar_multiesporte` ([[modulos/ingestao-garmin]]) | #236 |
| #175, #179, #208 | Roteiro renumerado, diário de 04/11 e estado da meta em 04/11 | #176, #181, #209 |

## O que não foi verificado
- **Tela no navegador, no iOS e no Android.** A Bia não abriu o Expo: a tela de um treino, o botão "Ver treino" e a evolução
  com o melhor pace estão cobertos pelo `npm test` (`TelaTreino`, `index`, `html`) e pelas capturas sintéticas em
  `docs/design/telas/treino/`. A conferência visual das #158, #159 e #233 fica pendente.
- **`downgrade` das migrações 0006 e 0007.** Subidas no Postgres e no SQLite; a descida não foi rodada.
- **ADR 0009 (#155) e a conferência com o histórico real (#169)** não foram conferidas pela Bia: a primeira é documento, a
  segunda depende do dado real, fora do git.

## O que ficou de fora
Como planejado: tela dos esforços e dos treinos de transição no app (a meta entrega só a API); evolução por faixa de distância
na tela; esforço por tempo na corrida; potência no ciclismo; esforços na natação; calibração pela lista de recordes pessoais
(os recordes chegam ao banco na Meta 6, #174).

**Pendências fora da meta** (abertas, sem prioridade sobre a Meta 6):
- **#213** (rafa-app, revisão da Lia): ajustes de acessibilidade e visual da tela de evolução, da revisão do #211.
- **#237** (rafa-app, com a Lia): mesma aparência para distância e pace na tela de um treino; pode tocar o contrato (ADR 0004).
- **#74** (manutenção do vault do Graphify, `docs/_grafo/`): fica para quando o Theo pedir o grafo de novo.

## Limitações conhecidas
Detalhes em [[metricas/esforcos]] e [[metricas/tiros-1km]], seção "Limitações". As da conferência local (#169) estão
escritas em texto genérico, sem nada do histórico.
- **Referência sem histórico:** sem corridas anteriores a referência é a mediana da própria atividade; num treino em que o
  esforço domina o volume, ele some (nas fixtures, o 3 x 1500 m vira todo `leve`). Com poucas atividades anteriores a
  referência é ruidosa e pode marcar como esforço o ritmo normal do atleta. Melhora com o histórico; redetectar depois de
  importar muito histórico antigo.
- **`ref_origem` recalculado na leitura**, não gravado: depois de uma importação grande, a leitura pode não bater com a
  referência usada nos blocos. Rodar `worker.detectar_esforcos` de novo.
- **Ciclismo sem potência:** a velocidade sofre com relevo e vento.
- **Dado de origem ruim** (GPS com distância absurda) vira um esforço com ritmo impossível; a detecção não valida.
- **Faixa pela soma:** dois esforços vizinhos que a regra de 5% não junta contam como dois (decisão do Angelo, 04/11).
- **Vizinho separado por pausa corta o tiro:** um vizinho que não é candidato a tiro (um esforço de 1500 m, por exemplo)
  corta o tiro de 1 km mesmo com descanso parado entre os dois; séries mistas e pirâmides perdem tiros de 1 km. Mudar isso
  é nova versão da regra, em issue própria.
- **Validado com um atleta:** os limites da série seguem calibrados com uma amostra pequena.

## Achados
- **O oráculo supõe uma referência.** O pedal de lap cortado (FIT 7) dá o esforço do oráculo só importado sozinho: no banco
  do guia a referência de ciclismo vem do histórico (o pedal de blocos, mais rápido), e o bloco não passa do limiar. Não é
  bug; o guia e o teste agora dizem isso.
- **Discordar de uma parte do brick** deixa a outra parte como grupo `incompleto`. Comportamento intencional (ADR 0009), que
  o guia não dizia.
- **O roteiro ficou defasado durante a meta.** A tabela marcava #166 a #171 como abertas e #165 e #202 em andamento quando
  todas já estavam fechadas (achado da Bia na #172). Corrigido aqui.
- **A meta cresceu pelas paralelas.** Entraram issues novas durante a semana (#216 a #220, #230, #233) e três adendos à ADR
  0004. Todas couberam, mas o fechamento esperou por elas.

## O que se aprendeu
- **Premissa marcada como pendente até a resposta funcionou.** A parada de 15 s / 30 s que corta o treino-chave entrou como
  premissa, a Nina a marcou, e o Angelo decidiu em 06/11 sem retrabalho.
- **Oráculo tem de dizer a referência que supõe.** Num banco com histórico, a mesma atividade pode dar outro resultado; o
  teste do oráculo importa a atividade sozinha, e o guia avisa a diferença.
- **Um único ponto de entrada para a detecção** (`classificar_atividades`) evitou que a importação, o upload e o comando
  divergissem.
- **"A API formata, o app mostra" escala.** A tela de um treino saiu com textos prontos da API (adendos 2 e 3 da ADR 0004),
  e a #237 mostra o custo: o tom secundário da unidade depende do formato que a API manda.
- **O roteiro não acompanha o dia a dia.** A situação de cada issue vive no GitHub; o roteiro registra o plano, a ordem e o
  resultado. Na Meta 6 a tabela leva só "aberta" e "feita" e é revisada no fechamento.
- **Conferência com o dado real em paralelo, com só o genérico no repositório,** funcionou de novo (#169), como na #118.

## PRECISA DO ANGELO
- Há decisões do Angelo pendentes da conferência local (#169). Os detalhes ficam em `entregas/`, fora do repositório.
  Nenhuma bloqueia a Meta 6.
- As decisões da Meta 6 que envolvem dado de aluno já foram tomadas em 04/11 ([[produto/roadmap]]).

## Resultado
**Meta 5 feita.** Com fixtures sintéticas, cada corrida e cada pedal viram blocos com esforços por distância e por duração,
de forma idempotente e versionada; a série de tiros sai dos esforços com o melhor tiro; e tudo aparece na API com textos
prontos. Junto vieram o treino de transição pela API, a tela de um treino com o clima e o subtipo do multiesporte. Não
verificados: a tela no navegador e nos aparelhos, o `downgrade` das migrações novas e o que depende do dado real.

Próxima: Meta 6, carga de treino ([[produto/roadmap]]).
