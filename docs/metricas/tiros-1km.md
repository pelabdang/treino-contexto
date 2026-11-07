---
tipo: metrica
status: em-uso
dono: caio
atualizado: 2026-11-07
links: [[modulos/grafico-tiros]], [[metricas/esforcos]], [[decisoes/0008-deteccao-de-esforcos]], [[produto/meta-1-como-reproduzir]], [[produto/roadmap]], [[decisoes/0001-modelo-de-dados-minimo]], [[decisoes/0002-segmento-intensidade-e-versao]], [[glossario]]
---
# Tiros de 1 km

## O que mede
Quais blocos de uma corrida são tiros de 1 km e se a atividade é um treino intervalado. É a base da série
"pace e FC médios dos tiros por sessão" da Meta 1. Cálculo determinístico, em código, sem banco e sem IA.

## Fórmula
Versão do cálculo: `tiros_1km@6` (#243; as anteriores foram substituídas, ver "Histórico"). Constantes e funções em
`services/api/app/metricas/tiros_1km.py` (`tiros_de_blocos`). Desde a `@5` a série **não lê mais voltas**: é uma
**visão dos esforços** ([[metricas/esforcos]], ADR [[decisoes/0008-deteccao-de-esforcos]], item 8), lida de
`bloco_atividade` (`esforcos@1`, gravado pelo `worker.detectar_esforcos`).

1. Só `modalidade == "corrida"`, fora a esteira (ADR 0005, item 1). Outra modalidade devolve 0 tiros.
2. **Candidato** = bloco de categoria `esforco` e faixa `d1000` (950 a 1050 m, inclusive). Quem junta os laps
   automáticos e separa aquecimento, recuperação e desaquecimento é a detecção de esforços: um tiro de 1000 m que o
   relógio cortou em 500 + 500 já chega como um bloco. Um esforço de **1500 m** (`d1500`), de 2000 m ou de 400 m
   **não é** tiro de 1 km. Aquecimento, desaquecimento, recuperação e rodagem (`leve`) saem pela própria categoria.
   A intensidade do FIT não é lida (é dica, ADR 0002).
3. **Ritmo parecido** (igual à `@4`): com 3 ou mais candidatos, sai o que é **mais de 20% mais lento** que a mediana
   deles (`pace > mediana x 1,20`; o limite entra).
4. **Bloco contínuo** (a regra de 15% da `@4`, agora sobre blocos): sai o candidato que é **menos de 15% mais rápido**
   que um **bloco vizinho** (anterior ou seguinte) de corrida, isto é, `pace do tiro > pace do vizinho x 0,85`. Conta
   como vizinho o bloco de **950 m ou mais** que não seja aquecimento nem desaquecimento (o km moderado de um
   fartlek, a rodagem de 2 km de um progressivo). **Exceção (`@6`, #243)**: o vizinho separado
   do tiro por uma **parada de 15 s ou mais** (`PAUSA_SEPARA_S`) **não conta**, seja ou não candidato a tiro (na `@5`
   só valia para o vizinho candidato): com descanso parado entre eles não há corrida contínua. Parada menor que 15 s
   continua cortando. Assim, em séries de distâncias misturadas (1500 m e 1000 m) e em pirâmides (1-3-2-1 km) com
   descanso parado, os blocos de 1 km contam como tiros. Exemplo: 1 km, 3 km, 2 km, 1 km, todos a 250 s/km com 90 s
   parados entre eles: os dois km são tiros (`250 > 250 x 0,85 = 212,5` os cortaria sem a exceção); com 10 s
   parados e o vizinho de 2 km a 275 s/km, `250 > 275 x 0,85 = 233,75`, o tiro sai. Dois km colados (parada menor que 15 s) em ritmos até 5% diferentes já viram um só esforço
   (`d2000`); entre 5% e 15% ficam como dois blocos e o item cobra a diferença.
5. **Recuperações**: blocos que não são tiro entre o primeiro e o último tiro (com 2 ou mais).
6. **Sessão** (`eh_intervalado`) = **pelo menos 2 tiros** (era 3 na `@4`; decisão do Angelo, 04/11). Não há mais a
   regra do volume do bloco principal: os 3-4 x 1 km de um treino misto contam e os tiros curtos simplesmente não são de
   1 km (decisão do Angelo, 04/11).
7. **Dois esforços vizinhos que a regra de 5% não junta** (1000 m a 250 s/km e 500 m a 270 s/km, por exemplo) ficam
   como `d1000` e `d500` (decisão do Angelo, 04/11): o `d1000` vale como tiro.

Ponto de partida de cada tiro na série: `ordem` = `segmento.ordem` da **primeira volta** do bloco; a contagem de
tiros, pace, FC e melhor tiro usam o bloco inteiro (distância e duração somadas).

### Por que a estrutura e não a intensidade
Um treino de tiros é uma alternância de esforço e recuperação; uma rodagem com auto-lap de 1 km é uma sequência de
voltas parecidas e vira um bloco só (`leve`). A intensidade gravada pelo relógio não distingue: numa rodagem real
quase todas as voltas vêm `active`. O pace relativo ao ritmo habitual e a posição no treino decidem.

### Dependência do ritmo habitual (e do histórico)
O limiar de esforço da detecção é `pace <= ritmo habitual x 0,90` (ADR 0008, item 5), o mesmo 10% do filtro da série
abaixo. Por isso o filtro da série ficou **redundante com a detecção** (cada tiro já é pelo menos 10% mais rápido, logo a
média também); ele continua aplicado como proteção quando o histórico muda depois da detecção. Consequência nova da `@5`:
**sem histórico** (atleta novo, primeira corrida) a referência é a mediana ponderada da própria atividade
(`ref_origem = atividade`), e uma sessão em que os tiros dominam o volume pode não ter nenhum esforço detectado. Na `@4`
a série não dependia disso. Ver "Limitações".

### Regressão da `@4` (issue #168)
Os casos de `test_tiros_1km.py` da `@4` foram refeitos pelo caminho voltas -> `montar_blocos` -> `tiros_de_blocos`
(ritmo habitual de 330 s/km, limiar 297). **Mesmo resultado**: seis tiros com aquecimento e desaquecimento; trote de 1 km a
330 s/km (tiros ficam); fartlek 1 km forte / 1 km moderado a 270 s/km (nenhum tiro); limite de 15% (trote a 282 fora, a
283 dentro); progressivo com paradas (fora) e km forte depois de rodagem lenta (3 tiros); bloco contínuo de 3 km (fora);
desaquecimento de 1 km a 290 s/km (sai pelo ritmo parecido; a 288 fica); autolap progressivo inteiro (fora); voltas de
949 e 1051 m (fora), 950 e 1050 m (dentro); rodagem de 8 x 1 km (fora).

**Mudou, com justificativa:**
- 3 x 1 km + 8 x 400 m: era fora (volume 3000 m < 3200 m); agora **3 tiros** (treinos mistos contam, Angelo 04/11).
- 2 x 1 km (com ou sem 8 x 400 m, com ou sem aquecimento) e 2 tiros + desaquecimento: era fora (mínimo 3); agora **entra**
  (mínimo 2, Angelo 04/11).
- 3 x 1 km + 10 x 300 m (e + 150 m): era dentro/fora pela fronteira do volume; agora **3 tiros nos dois**, sem regra de volume.
- Desaquecimento de 1 km a 300 s/km: era tiro cortado pelo ritmo parecido só com 3 ou mais; agora é `desaquecimento` por
  categoria (300 > 297, não é esforço).

Exemplos à mão da `@5`: 2 x 1000 m a 250 s/km com 400 m a 420 s/km: `250 <= 297`, 2 tiros, pace 250 s/km, entra.
5 x (1000 m a 250 + 400 m a 420) e depois 8 x (400 m a 230 + 200 m a 450): só os 5 blocos `d1000` são tiro, pace
`1250 s / 5000 m x 1000 = 250 s/km`; os `d400` não contam. Tiros curtos com 1 km lento antes e depois: nenhum `d1000`
`esforco`, fora. Fartlek: 240 contra 270 s/km colados, `240 > 270 x 0,85 = 229,5`, fora; contra 330 s/km, `240 <= 280,5`, dentro.

### Ritmo habitual do atleta (`@3`, issue #53; limite de 10% desde a `@4`, issue #58)
A estrutura (itens 1 a 9) diz se o treino tem repetições de 1 km separadas por recuperação. Falta saber se elas são
**treino de ritmo** e não rodagem: numa rodagem lenta com paradas curtas (sinal, pausa manual) ou com o ritmo
oscilando de uma volta para a outra, as voltas de 1 km também ficam "separadas" e passam. O que as separa de um
treino de tiros é o ritmo: os tiros precisam ser mais rápidos que o ritmo de rodagem **do próprio atleta**.

- **Ritmo habitual** (`pace_habitual`, função pura em `app/metricas/`): mediana do pace (s/km) das corridas do atleta
  com **mais de 3 km**, **sem esteira**, com data **anterior** à da sessão, nas **12 semanas (84 dias)** antes dela.
  Com **menos de 10 corridas** nessa janela, usa **todo o histórico anterior**; sem nenhuma corrida anterior, não há
  ritmo habitual (`None`) e a sessão não é filtrada. É a mediana, e não a média, para não ser puxada pelas poucas
  sessões de tiros nem por uma corrida atípica. A janela é móvel para acompanhar o atleta que evolui.
- **Filtro** (`mais_rapido_que_o_habitual`, aplicado na série em `serie_tiros_1km`/`sessoes_tiros_1km`, num lugar
  só): a sessão entra se `pace médio dos tiros <= ritmo habitual x 0,90`, sem arredondar; o limite exato entra.
- **Por que 10% (era 5% na `@3`).** O 8% da regra vale **por volta**: um tiro contra a volta ao lado, no mesmo dia, em
  que o ruído de uma volta para outra (relevo, vento) é pequeno. Contra o ritmo habitual, que mistura dias e
  condições, a comparação é mais ruidosa, então pede-se uma margem própria. Com 5%, séries de 1 km em ritmo moderado
  ainda passavam, porque ficam perto do ritmo habitual; tiros de verdade ficam bem abaixo dele. Subiu para 10%, um valor
  redondo que mantém folga para tiros de verdade e tira essas séries. Decisão do projeto, não vem de artigo.
- A comparação é entre o pace dos tiros **da sessão** e o histórico do atleta, por isso o filtro mora na série
  (precisa do histórico), e não em `tiros_de_blocos`, que olha uma atividade só.

Exemplo à mão: histórico com mediana de 330 s/km (5:30). Limite = 330 x 0,90 = 297 s/km (4:57). Tiros a 270 s/km:
entram. "Tiros" a 330 s/km (rodagem com paradas): 330 > 297, ficam fora. Tiros a 297: entram (o limite entra).

## Agregação por sessão (issue #12)
Um ponto por atividade com `eh_intervalado` verdadeiro; série ordenada por data (empate: id da atividade).
Rodagem leve e natação não entram.

- **Pace da sessão (s/km)** = soma das durações dos tiros / soma das distâncias dos tiros x 1000. É a média
  ponderada pela distância, não a média simples dos paces.
- **FC da sessão (bpm)** = soma(FC x duração) / soma(duração), média ponderada pela duração. Tiros sem FC ficam
  fora (inclusive do peso); se nenhum tem FC, `None`.
- **Melhor tiro da sessão** (issue #151): o tiro de **menor pace** (duração / distância x 1000, por tiro), com a **FC
  dele** (`melhor_pace_s_km`, `melhor_fc_media`, `melhor_ordem`). Empate de pace: **o primeiro** na ordem da
  atividade. Decisão de produto (04/11): o valor principal do gráfico é o melhor tiro e a média (pace e FC acima)
  fica como valor secundário; o painel de FC mostra a FC do melhor tiro. Esta nota só define a métrica; contrato,
  PNG/CSV e app vêm em #152, #153 e #154.
- **Melhor tiro sem FC**: `melhor_fc_media` é `None`. Não se troca por outro tiro nem por a FC média: o ponto fica
  sem FC no painel. A FC média da sessão (só tiros com FC) continua existindo à parte.
- Tiro sem distância (0 m) não tem pace e não concorre a melhor tiro.
- Também saem `n_tiros`, `data` (data local do início) e `atividade_id`.
- `versao`: versão da regra de detecção (`tiros_1km@5`), vinda da detecção e levada até o ponto da série
  (`SessaoTiros.versao`, `PontoSessao.versao`). É o valor a gravar em `segmento.versao_deteccao` ([[decisoes/0002-segmento-intensidade-e-versao]]).
  Mudou regra ou constante: sobe `VERSAO`.
- Arredondamento só na apresentação, 1 casa decimal (`para_apresentacao`); o cálculo usa o valor cheio.

Exemplo à mão: tiros 1000 m/240 s/160 bpm, 1000 m/236 s/165 bpm, 990 m/238 s sem FC:
pace = 714 / 2990 x 1000 = 238,8 s/km; FC = (160x240 + 165x236) / 476 = 162,5 bpm.

Exemplo à mão do melhor tiro (#151): tiros 1000 m/250 s/165 bpm, 1000 m/244 s/170 bpm, 990 m/247 s sem FC. Paces:
250,0; 244,0; 247 / 990 x 1000 = 249,5 s/km. Melhor: 244,0 s/km (4:04), FC 170 bpm. Média: 741 / 2990 x 1000 =
247,8 s/km (a média aparece como secundária). Empate: 1000 m/240 s/160 bpm e 1000 m/240 s/170 bpm têm o mesmo pace;
vale o primeiro (FC 160). Se o melhor fosse o de 990 m, a FC do melhor tiro seria `None`, sem emprestar a de outro.

**Versão: não subiu por causa do melhor tiro** (a `@4` seguia; a `@5` vem da #168, e é ela que pede reclassificação). O melhor tiro é só uma agregação a mais sobre os
tiros que a detecção já devolvia.

### Formato do pace em `m:ss` (issue #39)
`formatar_pace(s_km)` arredonda ao segundo **com meio para cima** (piso de `s_km + 0,5`) e só depois separa
minutos e segundos; por isso nunca sai "3:60". Não usa `round()` do Python (arredonda para o par). É a regra única
do eixo do gráfico, do CSV e do JSON ([[modulos/grafico-tiros]]).

| Pace (s/km) | `m:ss` |
|---|---|
| 238,8 | 3:59 |
| 239,5 | 4:00 |
| 238,49 | 3:58 |
| 250,83 | 4:11 |
| 237,0 | 3:57 |
| 59,5 | 1:00 |

### Valores esperados das fixtures (oráculo, issue #30)
Calculados à mão a partir de `tests/fixtures/garmin/gerar_fixtures.py`; o teste
`services/api/tests/metricas/test_oraculo_fixtures.py` os guarda em `ESPERADO` para a #14 e a #18 reutilizarem.

| Atividade | Tiros | Pace (s/km) | FC (bpm) | Melhor tiro (s/km, FC) | Conta |
|---|---|---|---|---|---|
| 1000000001 (6 x 1 km) | 6 | 250,83 (4:10,8) | 170,30 | 248,0 (4:08), 175 bpm | 1505 s / 6000 m; 256309 / 1505; paces 255, 252, 250, 251, 249, 248: o menor é o 6o, 248 s em 1000 m, FC 175 |
| 1000000002 (5 x 1 km) | 5 | 237,0 (3:57,0) | 171,77 | 234,0 (3:54), 177 bpm | 1185 s / 5000 m; 203546 / 1185; paces 240, 238, 237, 236, 234: o menor é o 5o, 234 s em 1000 m, FC 177 |

Ficam fora da série: 1000000003 (corrida leve, sem tiros), 1000000004 (natação) e 1000000005 (sem FIT).

### Escala dos eixos do gráfico (issue #63)
O pace e a FC médios por sessão são desenhados com escala mínima: faixa de 30 s/km no pace e de 5 bpm na FC (regra e
conta à mão em [[modulos/grafico-tiros]]). Os rótulos das marcas de pace vêm de `formatar_pace`. A escala não altera
nenhum valor da métrica, só o desenho, e não muda a versão.

## Dados de entrada
Por volta: `ordem`, `distancia_m`, `duracao_s`, `fc_media` (opcional) e `intensidade` (opcional; campo
`segmento.intensidade`, ver [[decisoes/0002-segmento-intensidade-e-versao]]). Mais a modalidade da atividade.

## Referência
Regra própria do projeto; não há artigo.

## Histórico
- `tiros_1km@1` (#11): tiro por intensidade quando havia 2 ou mais valores diferentes; senão, pace 8% abaixo da
  mediana. Em dado real marcava rodagens leves como intervalado (a volta final parcial criava o "contraste").
- `tiros_1km@2` (#48): a regra acima, com o bloco principal. Os segmentos já gravados com `@1` precisam ser reclassificados: reimportar a exportação ou chamar `classificar_atividades` (`app.servicos.evolucao_tiros`) para o atleta, que regrava `tipo` e `versao_deteccao`.
- `tiros_1km@3` (#53): o filtro do ritmo habitual acima, na série. A detecção por atividade (`detectar_tiros`) não muda
  em relação à `@2`; mudam a versão e a série. Reclassificar (como acima) regrava a versão nos segmentos.
- `tiros_1km@4` (#58): itens 7 (ritmo parecido) e 8 (bloco contínuo) na detecção e ritmo habitual de 5% para 10% na
  série. Mudou a detecção: é preciso **reclassificar** (`classificar_atividades`) para regravar `tipo` e `versao_deteccao`.
- `tiros_1km@5` (#168): a série passa a ler `bloco_atividade` (visão dos esforços, ADR 0008, item 8) no lugar das voltas;
  mínimo de 2 tiros; sem a regra do volume do bloco principal; ritmo parecido, bloco contínuo e ritmo habitual mantidos.
  Mudou a detecção: **reclassificar** (`python -m worker.reclassificar --atleta-id <id>` ou `classificar_atividades`),
  que agora também recria os blocos (`detectar_esforcos`) e regrava `tipo` e `versao_deteccao` dos segmentos. A API traz
  `reclassificacao_pendente: true` até lá. O contrato (campos) não mudou; só `versao_calculo` passa a `tiros_1km@5`.

- `tiros_1km@6` (#243): o vizinho de 950 m ou mais separado do tiro por parada de 15 s ou mais deixa de cortá-lo, seja ou
  não candidato (item 4). Mínimo de 2 tiros mantido e velocidade habitual do ciclismo (12 semanas, pedais de 30 min ou
  mais, mínimo de 10) confirmada (ADR 0008, adendo). Os blocos (`esforcos@1`) não mudam; **reclassificar**
  (`python -m worker.reclassificar --atleta-id <id>`) recalcula as linhas `@5` e regrava `tipo` e `versao_deteccao`.

## Código e teste
- Melhor tiro (#151): sem mudança de versão, ver "Agregação por sessão".
- Código: `services/api/app/metricas/tiros_1km.py` (`tiros_de_blocos`, `agregar_sessao`, `serie_por_sessao`); `services/api/app/servicos/evolucao_tiros.py` (leitura dos blocos); escala dos eixos em `services/api/app/graficos/escala.py`
- Testes: `services/api/tests/metricas/test_agregacao_sessao.py` (exemplo acima) e
  `services/api/tests/metricas/test_tiros_1km.py` (visão sobre os blocos, regressão da `@4` e o que mudou, conta à mão em cada caso) e `services/api/tests/servicos/test_serie_pace_habitual.py` (exemplos da #168 no banco).

## Limitações e quando não usar
- **Sem histórico a referência é a da própria atividade** (ADR 0008): primeira corrida do atleta, ou treino em que os tiros dominam o volume, pode ficar sem esforços e fora da série. Na `@4` não havia essa dependência.
- Tiro de 1 km cortado em dois ritmos pelo relógio (1000 m + 500 m com mais de 5% de diferença) vale como `d1000` + `d500`; um esforço de 1500 m não é tiro de 1 km.
- Para as listas abaixo, o que a `@4` descrevia por voltas vale agora por blocos.
- **Validado com um atleta.** Os limites da `@4` (15% de bloco contínuo, 20% de ritmo parecido, 10% do ritmo habitual)
  foram calibrados com uma amostra pequena e ainda não foram testados com outros perfis. Atleta que faz progressivo com km final bem mais rápido que os anteriores (mais de 15%) ou que treina tiros
  em ritmo próximo ao de rodagem pode ser classificado diferente do que espera.
- Ficam como limitação, sem critério geral encontrado (a `@6` aceitou o caso (c)): (a) progressivo ou série moderada em que o km forte é mais de
  15% mais rápido que o km vizinho e há recuperação curta (parece tiro de verdade); (b) fartlek de 1 km forte e 500 m
  moderados, que não se distingue estruturalmente de tiros com trote de 500 m; (c) séries de 1 km em ritmo moderado com
  paradas de cerca de 1 min, que têm a mesma estrutura de tiros. A regra não usa dia da semana nem nada específico do atleta.
- Efeito colateral aceito da `@4`: uma série de 3 tiros em que um é desaquecimento lento perde o terceiro e deixa de
  valer; e uma sessão com um km de aquecimento mais rápido que 85% do tiro, colado por pausa curta, perde esse tiro.
- O filtro do ritmo habitual (agora 10%) e a janela de 12 semanas também só foram vistos com **um atleta**. Atleta novo, sem corridas anteriores, não é filtrado na série (mas a detecção usa a referência da atividade, ver acima; e com menos de 10 corridas na janela o
  histórico todo é a referência, que é menos preciso). Um treino de tiros leve, mais lento que 10% abaixo do ritmo
  habitual (por exemplo, volta à corrida depois de lesão), não entra na série de tiros.
- **Série moderada com paradas** (`@6`): como a parada de 15 s ou mais tira o vizinho da conta, um km no ritmo de
  tiro entre blocos de rodagem separados por paradas passa a valer como tiro (caso (c) acima, agora aceito como regra).
  O limite de ritmo habitual (10%) e o ritmo parecido continuam filtrando.
- **Pausa dentro do tiro não é tratada**: um tiro de 1 km parado no meio por 15 s ou mais chega como dois pedaços de
  esforço e não conta (proposta futura no adendo da ADR 0008).
- Só detecta tiros de 1 km; 400 m, 2 km e outras distâncias ficam fora da Meta 1. Num treino misto, os
  tiros de 1 km contam e os curtos não (`@5`).
- Uma volta solta de ~1 km, sem rótulo, no fim do treino (por exemplo, um desaquecimento de 1 km) vale como tiro se
  for até 20% mais lenta que a mediana dos tiros (item 7 da `@4`); mais lenta que isso, sai.
- Tiros de 1 km seguidos, sem pausa nem recuperação entre eles e no mesmo ritmo, viram um esforço só (`d2000`, `d3000`...) e
  não são tiros: a regra não distingue esse caso de um bloco contínuo. Com parada de 15 s ou mais entre eles, são tiros.
- Treino com voltas de 1 km sem `lap` manual (só auto-lap) vira um bloco só e não é visto como intervalado.
- Corrida de prova ou longão com variação grande de ritmo e voltas de 1 km alternadas com pausas pode passar na
  regra; é o comportamento esperado, não um erro.
- Esteira sem GPS: a distância vem do sensor do aparelho e pode se afastar da faixa `d1000`.
- **Esteira fica fora da série** (decisão do Angelo, #51): a detecção classifica uma esteira como qualquer corrida,
  mas `serie_tiros_1km`/`sessoes_tiros_1km` descartam `subtipo = "esteira"`. A atividade segue guardada.
