---
tipo: meta
status: em-uso
dono: paulo
atualizado: 2026-11-04
links: [[produto/roadmap]], [[produto/meta-4-como-rodar]], [[decisoes/0007-clima-da-atividade]], [[modulos/clima]], [[metricas/clima-oraculo]], [[modulos/ingestao-garmin]], [[modulos/worker]], [[modulos/banco]], [[modulos/api]], [[modulos/api-client]], [[decisoes/0006-upload-de-fit]], [[decisoes/0005-serie-de-tiros-o-que-entra]], [[metricas/tiros-1km]], [[produto/metas/meta-3-upload-fit]], [[diario/2026-11-03]]
---
# Meta 4: clima de cada atividade

> **Situação: feita.** Código e QA no main (#109 a #116). A Bia rodou o guia de novo com fixtures sintéticas
> ("Parque do Exemplo", lugar inventado), conferiu cada estado do clima no banco e na API e rodou também o upload de
> FIT seguido do clima (#116, PR #130). Fechamento: #117. Ficam registrados como não verificados a chamada real ao
> Open-Meteo pelo comando, o `worker.importar_garmin` com as fixtures de clima e a tela (o clima ainda não aparece no app).

## Objetivo
Cada atividade ao ar livre ganha temperatura, sensação térmica, umidade e vento na hora e no local do treino. Esteira,
piscina e pedal virtual ficam como `indoor`, sem clima. Regras na [[decisoes/0007-clima-da-atividade]].

## Entrega visível
- O objeto `clima` em `GET /atletas/{atleta_id}/atividades/{atividade_id}`, com `estado` (`ok`, `indoor`, `sem_posicao`,
  `pendente`, `falha`) e, só em `ok`, os quatro valores. A posição nunca sai pela API nem pelo OpenAPI.
- O comando `uv run python -m worker.preencher_clima`, que relê a posição de início dos arquivos locais (`--so-posicao`,
  sem rede) e preenche o clima das atividades já gravadas, sem repetir o que já está feito.
- Passo a passo, com um jeito de forçar cada estado, em [[produto/meta-4-como-rodar]].

## Critério de pronto
Resultado de cada item conforme o relatório da Bia na #116 (PR #130), com as fixtures de `tests/fixtures/clima/` e a
resposta gravada do Open-Meteo, sem rede.

| Item | Onde | Resultado |
|---|---|---|
| ADR do clima aprovada pelo Theo (tabela, posição, indoor, API, falhas) | #109 | **ok**. [[decisoes/0007-clima-da-atividade]], aceita em 03/11 e marcada como implementada |
| O leitor guarda a posição de início, arredondada a 2 casas, do FIT (exportação e upload) e do JSON | #110, #116 | **ok**. Migração 0004; no QA, `12.35 / -45.68` só nas quatro atividades ao ar livre com coordenada; esteira e pedal virtual sem posição mesmo com coordenada no arquivo; `(0, 0)` e valor inválido descartados |
| Cliente Open-Meteo testado só com resposta gravada; clima de uma atividade sintética bate com o oráculo | #111, #112, #116 | **ok**. Valores no banco e no `GET` iguais aos de [[metricas/clima-oraculo]] (média ponderada pelas horas do treino); guarda de socket nos testes |
| Preencher o clima é idempotente | #113, #116 | **ok**. Segunda rodada com `chamadas=0`; `--so-posicao` só preenche `NULL` |
| Indoor e sem posição nunca ganham clima inventado | #113, #114, #116 | **ok**. `indoor` e `sem_posicao` calculados na leitura, sem chamada e sem linha em `clima_atividade` |
| Funciona para atividade da exportação e do upload | #116 | **ok**. Upload pelo `POST .../atividades/fit` (`201`) ficou `pendente` e virou `ok` na rodada seguinte, com os mesmos valores da atividade da exportação |
| Estados `pendente` e `falha` | #113, #116 | **ok**. Dentro dos 7 dias, `null` na janela, 503 até 5 rodadas, 400 como `falha` na hora e `--refazer-falhas` |
| Clima na API e cliente regerado | #114 | **ok** ([[modulos/api]], [[modulos/api-client]]) |
| Testes | todos | `uv run pytest -q` com 651 testes verdes no QA; `tests/test_e2e_meta4.py` (15 testes) no CI |

## O que foi entregue
| Issue | Entrega | PR |
|---|---|---|
| #109 | ADR 0007, clima da atividade ([[decisoes/0007-clima-da-atividade]]) | #123 |
| #110 | Leitor guarda a posição de início arredondada, migração 0004 ([[modulos/ingestao-garmin]], [[modulos/banco]]) | #124 |
| #111 | Fixtures sintéticas com posição e o oráculo do clima ([[metricas/clima-oraculo]]) | #125 |
| #112 | Cliente Open-Meteo com resposta gravada ([[modulos/clima]]) | #126 |
| #113 | Tabela `clima_atividade` (migração 0005) e `worker.preencher_clima` ([[modulos/worker]]) | #127 |
| #114 | `GET /atletas/{atleta_id}/atividades/{atividade_id}` com `clima` e cliente regerado | #128 |
| #115 | Guia [[produto/meta-4-como-rodar]], notas conferidas, ADR 0007 com status e o esclarecimento das tentativas | #129 |
| #116 | QA de ponta a ponta com fixtures com posição e `tests/test_e2e_meta4.py` | #130 |
| #117 | Resultado da meta e roteiro | este |

Fora da sequência, na mesma meta (propostas da Meta 3 aprovadas pelo Angelo):

| Issue | Entrega | PR |
|---|---|---|
| #118 | Investigação da série de tiros com o histórico real. Relatório só em `entregas/`, fora do git; conclusão genérica abaixo | sem PR (só relatório privado) |
| #119 | App web em `pt-BR`: o Chrome não oferece mais tradução nem troca as mensagens ([[modulos/mobile]]) | #122 |
| #120 | Regra do docs-ok registrada no `AGENTS.md`: label só depois do CI do commit da Nina | #121 |

## O que não foi verificado
- **Chamada real ao Open-Meteo pelo código.** Houve uma única chamada manual, na #112, com a posição inventada do "Parque do
  Exemplo" ([[modulos/clima]], "O que a chamada real mostrou"). O `preencher_clima` e o cliente só rodaram com a resposta
  gravada. A primeira chamada do código de verdade será a do histórico real, que espera o Angelo (abaixo).
- **`worker.importar_garmin` na linha de comando com as fixtures de clima.** O comando busca o clima no fim e usaria a rede;
  por isso o guia e o QA importam essas fixtures pela função `importar`. A linha `clima: chamadas=0` do comando só foi vista
  com as fixtures da Meta 1 (sem posição), na #115.
- **Tela.** O clima não aparece no app: web, iOS e Android ficam como "não se aplica".

## O que ficou de fora
Como planejado: previsão do tempo (o clima da semana corrente fica `pendente`); ajuste de pace por calor ou vento;
clima na tela do app; trajeto completo, fim e nome do lugar; plano comercial do Open-Meteo; deploy.

## Investigação da série de tiros (#118): conclusão genérica
O relatório, com a lista de sessões e os números, fica só em `entregas/`, fora do git. Aqui vai só o que pode ser público:
parte do que o atleta esperava ver não está na série por causa da **regra** do que entra
([[decisoes/0005-serie-de-tiros-o-que-entra]]). Outra parte tem a ver
com **como a sessão é resumida**: a série mostra a média dos tiros, e a média esconde o melhor tiro. O Caio deixou
recomendações, e ambas esperam as respostas do Angelo a perguntas sobre o que ele quer ver na série:
- **R1:** mostrar o melhor tiro da sessão junto da média. Muda o contrato da API e o gráfico, não a regra
  ([[metricas/tiros-1km]], [[decisoes/0004-contrato-tela-evolucao]]).
- **R2:** uma regra `tiros_1km@5` que amplia o que entra na série. Muda a série do atleta; entra com teste
  sintético e nova versão da regra.

## Achados depois da meta
Não estão no critério de pronto, então não são pendências da Meta 4. Viram propostas; nenhuma issue foi criada, porque
isso depende do "pode criar" do Angelo.

- **O `worker.importar_garmin` chama o Open-Meteo por padrão.** No fim da importação ele busca o clima das atividades que
  entraram ou mudaram. Com as fixtures de clima isso mandaria a posição inventada para fora; com o histórico real,
  **reimportar a exportação mandaria as posições arredondadas na hora**, sem a decisão que o Angelo ainda não tomou.
  Hoje só o aviso no guia e em [[modulos/worker]] impede isso.
- **Duplicação ao importar um FIT avulso depois do JSON.** Na #115, os FIT de clima importados depois do JSON entraram como
  atividades novas. Causa: a regra de que "a exportação não casa com outra linha da exportação" (detalhe da #94, na
  [[decisoes/0006-upload-de-fit]]) supõe que as duas linhas têm `activityId`. Um FIT sem JSON tem `fonte_id` `fit-…`, que não
  é `activityId`, mas é da mesma fonte e cai na exclusão. Caso estreito: a exportação completa (JSON e FIT juntos) não
  duplica, e o upload pelo app também não.
- **Clima só no banco e na API.** O valor para o atleta aparece quando o clima chegar à tela ou ao feedback do treino.

## Propostas (aguardando "pode criar")
1. **`--sem-clima` no `worker.importar_garmin`** (duda-dados, menos de 1 dia). Opção para importar sem buscar o clima, ou
   inverter o padrão (só busca com `--com-clima`). Proposta do time: **inverter o padrão**, porque nada que manda dado do
   atleta a terceiro deve acontecer sem pedido explícito. Critério de pronto: o comando sem a opção não abre conexão (teste
   com guarda de socket); com a opção, chama `preencher_clima` só para o que mudou; guia da Meta 4 e
   [[modulos/worker]] atualizados, sem o script de contorno do passo 3. Deve vir **antes** de qualquer reimportação do
   histórico real.
2. **Identidade de FIT avulso** (duda-dados, menos de 1 dia). A exclusão "exportação não casa com exportação" passa a valer
   só quando os **dois** lados têm `activityId`; um FIT com `fonte_id` `fit-…` casa pela regra dos 60 s como o upload.
   Critério de pronto: teste com JSON e depois FIT avulso do mesmo treino (uma linha só) e teste com dois `activityId`
   próximos (continuam duas); nota da ADR 0006 com o ajuste. É mudança de regra de identidade: aprovação do Theo.
3. **R1 e R2 da série de tiros** (caio-ciencia, com duda-dados e rafa-app no R1). Só depois das respostas do Angelo; ver
   "PRECISA DO ANGELO".
4. **Clima na tela do app** (rafa-app, com duda-dados). Fora da Meta 4; candidata a meta futura, junto da tela de um treino
   (a mesma tela vai receber o check-in da Meta 8 e o feedback da Meta 9, na numeração revista em 04/11). Exige a atribuição "Weather data by
   Open-Meteo.com" na tela (ADR 0007, item 4).

## O que se aprendeu
- **ADR com fontes e "a confirmar" funcionou.** A ADR 0007 citou a documentação do Open-Meteo e listou o que só a chamada
  real diria. A #112 confirmou tudo com uma chamada: sensação térmica sem `models` e custo 1 por chamada.
- **Efeito colateral de rede precisa ser opt-in.** O fim da importação chamar um terceiro obrigou o guia e o QA a contornar
  o comando, e é o maior risco antes do histórico real (proposta 1).
- **Toda exceção à regra de identidade precisa de teste com as duas fontes.** A exclusão da #94 era certa para o JSON e
  errada para o FIT avulso (proposta 2). Mesma lição da Meta 3, num canto que o QA não cobriu.
- **Número sem unidade confunde.** "3 tentativas" virou "1 chamada mais até 3 repetições" (Theo, na #112), e `chamadas`
  conta atividades, não chamadas HTTP. Escrever limites como "no máximo N chamadas" e nomear contadores pelo que contam.
- **Investigação com dado real em paralelo deu certo.** O Caio trabalhou com o histórico real sem tocar a meta da Duda, e o
  repositório recebeu só a conclusão genérica.
- **Meta sem tela tem QA mais curto e valor menos visível.** Tudo verificável foi verificado; o atleta ainda não vê nada.

## PRECISA DO ANGELO
- **Rodar o `preencher_clima` no histórico real.** É a primeira vez que dado real vai a um terceiro: só a posição de início
  arredondada (~1 km) e o horário, sem identificador; o Open-Meteo guarda coordenadas em log por 90 dias e vê o IP da
  máquina (ADR 0007, "Consequências"). Proposta do time: primeiro a proposta 1 (`importar_garmin` sem rede por padrão),
  depois `--so-posicao` (local) e, com o ok do Angelo, uma rodada de clima com `--limite` baixo. Os números ficam só em
  `entregas/`.
- **Série de tiros:** as perguntas do relatório da #118 (em `entregas/`, fora do git) sobre o que o atleta quer ver
  na série. Delas dependem a R1 (melhor tiro junto da média) e a R2 (`tiros_1km@5`, que amplia o que entra). A R2 muda a série
  do atleta.
- **"Pode criar"** para as propostas 1, 2 e 4 e, depois das respostas acima, a 3.
- As decisões da Meta 6 (carga; era a Meta 5 até 04/11) que envolvem dado de aluno estão em [[produto/roadmap]].

## Resultado
**Meta 4 feita.** Com fixtures sintéticas e a resposta gravada, cada atividade ao ar livre com posição ganha o clima da hora
do treino, sem repetir chamadas; indoor e sem posição nunca ganham clima; o estado aparece na API, sem a posição; e
atividades da exportação e do upload funcionam. Não verificados: a chamada real pelo código, o `worker.importar_garmin` com
as fixtures de clima e a tela (o clima não tem tela).

Próxima (na época): Meta 5, carga de treino. Desde 04/11 a Meta 5 é a detecção de esforços e a carga é a Meta 6 ([[produto/roadmap]]).
