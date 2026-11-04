---
tipo: metrica
status: em-uso
dono: caio
atualizado: 2026-11-04
links: [[modulos/grafico-tiros]], [[produto/meta-1-como-reproduzir]], [[produto/roadmap]], [[decisoes/0001-modelo-de-dados-minimo]], [[decisoes/0002-segmento-intensidade-e-versao]], [[glossario]]
---
# Tiros de 1 km

## O que mede
Quais voltas de uma corrida são tiros de 1 km e se a atividade é um treino intervalado. É a base da série
"pace e FC médios dos tiros por sessão" da Meta 1. Cálculo determinístico, em código, sem banco e sem IA.

## Fórmula
Versão do cálculo: `tiros_1km@4` (as anteriores foram substituídas, ver "Histórico" abaixo). Constantes em
`services/api/app/metricas/tiros_1km.py`.

1. Só `modalidade == "corrida"`. Qualquer outra modalidade devolve 0 tiros e `eh_intervalado = falso`.
2. **Candidata**: volta com distância de **950 a 1050 m**, inclusive (1000 m ± 50 m, tolerância de GPS e de
   auto-lap; ± 5%), cuja intensidade (campo `intensidade` do FIT) não seja `rest`, `recovery`, `warmup` nem
   `cooldown`. Volta de 949 m ou de 1,2 km nunca é tiro. Pace da volta (s/km) = duração / distância x 1000.
3. **Tiro** = candidata cujas **duas vizinhas** (volta anterior e volta seguinte) a separam do resto do treino.
   Uma vizinha separa se:
   - não existe (a volta é a primeira ou a última da atividade); ou
   - é `warmup` ou `cooldown` (fronteira do treino); ou
   - é uma **pausa**: distância menor que 200 m (parado ou andando); ou
   - é uma **recuperação**: o tiro é **pelo menos 8% mais rápido** que ela, isto é,
     `pace do tiro <= pace da vizinha x 0,92`. Vale para qualquer volta vizinha, inclusive outra de ~1 km
     (um trote de 1 km entre tiros) ou de outra distância (400 m de recuperação).
   Uma vizinha de 1 km no mesmo ritmo **não separa**: é o auto-lap de uma rodagem ou de um bloco contínuo.
4. A **intensidade só veta e marca fronteira**: nunca basta para dizer que uma volta é tiro. O pace e a
   estrutura esforço-pausa decidem sempre, com ou sem intensidade.
5. **Recuperações**: voltas que não são tiro entre o primeiro e o último tiro.
6. **Bloco principal**: se há 3 ou mais tiros, a atividade só vale se o **volume** (soma das distâncias) dos tiros
   de 1 km for **maior ou igual** ao das voltas curtas (de 150 a 700 m) que não são tiro de 1 km e não estão
   rotuladas `rest`/`recovery`/`warmup`/`cooldown` (tiros curtos e também recuperações sem rótulo). Num treino misto
   em que os tiros curtos pesam mais, a atividade fica fora: tiros e recuperações saem vazios. As recuperações sem
   rótulo entram na soma, mas somam bem menos que os tiros num treino de 1 km: cada uma pesa no máximo 70% de um
   tiro.
7. **Ritmo parecido** (`@4`): com 3 ou mais tiros, sai o tiro **mais de 20% mais lento** que a **mediana** dos
   tiros da atividade (`pace > mediana x 1,20`; o limite entra). É o desaquecimento de 1 km que o relógio marcou como
   volta, separado do resto por uma pausa.
8. **Bloco contínuo** (`@4`): sai o tiro cuja **primeira volta de corrida** de qualquer lado (**pulando as pausas**,
   isto é, voltas de menos de 200 m) é uma volta de ~1 km (950 a 1050 m), que não é tiro nem `warmup`/`cooldown`, e
   da qual o tiro é **menos de 15% mais rápido** (`pace do tiro > pace da vizinha x 0,85`). É o 1 km forte de um
   progressivo ou de um fartlek (1 km forte, 1 km moderado), em que o "descanso" é outro km de corrida.
9. `eh_intervalado` = **pelo menos 3 tiros** (depois dos itens 6, 7 e 8).

### Por que a estrutura e não a intensidade
Um treino de tiros é uma alternância de esforço e pausa; uma rodagem com auto-lap de 1 km é uma sequência de
voltas parecidas, sem pausa entre elas. A regra pede o que distingue os dois. A intensidade gravada pelo relógio
não distingue: numa rodagem real quase todas as voltas vêm `active` e a última, parcial, vem `rest`, `recovery` ou
`cooldown`, o que parecia "contraste" e fazia a `@1` marcar todas as voltas de 1 km como tiro.

### Por que 8%
Numa rodagem leve com auto-lap, as voltas variam cerca de 3% a 4% de uma para a outra (relevo, vento, parada
em semáforo); 8% fica com folga acima desse ruído. Um tiro de verdade costuma ser 15% a 30% mais rápido que a
recuperação, então 8% não perde tiros. O valor é decisão do projeto, não vem de artigo.

### Progressivo e fartlek não são tiros (`@4`, issue #58)
A `@3` aceitava qualquer volta de 1 km cercada por pausas ou por voltas mais lentas em 8%. Isso inclui treinos com
outra intenção: **progressivo** (km a km cada vez mais rápido, com paradas), **fartlek** (1 km forte, 1 km moderado) e
**séries de 1 km em ritmo moderado**. Como o relógio tem volta automática de 1 km, esses blocos parecem tiros: volta de
1 km, parada curta, volta de 1 km. O que os separa de um treino de tiros é que o "descanso" é **corrida em ritmo
moderado**, não trote ou parada: o km forte é só um pouco mais rápido (menos de 15%) que o km ao lado, mesmo que haja
uma pausa de segundos no meio. Os itens 7 e 8 acima cobrem isso. Os 8% da `@3` continuam valendo para o resto; os 15% valem
só para vizinha de ~1 km, porque aí é a mesma distância e a comparação é direta.

- **Por que 15%.** Um trote de recuperação entre tiros costuma ser 20% ou mais mais lento que o tiro; um km moderado de
  fartlek ou de progressivo fica entre 5% e 14%. 15% separa os dois grupos. Decisão do projeto, não vem de artigo.
- **Por que 20% no ritmo parecido.** Tiros de uma série variam poucos por cento entre si (fadiga, relevo); uma volta
  mais de 20% mais lenta que a mediana não é repetição, é rodagem. A mediana não é puxada pela volta lenta.
- **Ritmo habitual (`@4`)**: o limite subiu de 5% para **10%** (`pace dos tiros <= habitual x 0,90`). Séries de 1 km
  em ritmo moderado ficam perto do ritmo habitual; tiros de verdade ficam bem abaixo dele.

Exemplo à mão (fartlek): 4 x [1000 m a 240 s/km + 1000 m de trote a 270 s/km]. Pela `@3`: `240 <= 270 x 0,92 = 248,4`,
os 4 eram tiros. Pela `@4`: `240 > 270 x 0,85 = 229,5`, o trote é moderado demais: nenhum é tiro. Com trote a 330 s/km:
`240 <= 330 x 0,85 = 280,5`, os 4 seguem tiros. No limite: trote a 282, `282 x 0,85 = 239,7 < 240`, fora; a 283,
`283 x 0,85 = 240,55 >= 240`, dentro.

Exemplo à mão (por cima da parada): 3 x [1000 m a 310, 1000 m a 300, parada de 20 m, 1000 m a 275, parada de 20 m]. O km de
275 está entre paradas, mas a volta de corrida do outro lado da parada é 300: `275 > 300 x 0,85 = 255`, fora. Com 340 e 330:
`275 <= 330 x 0,85 = 280,5`, dentro.

Exemplo à mão (ritmo parecido): 3 x 1000 m a 240 s/km e um 4o km a 290 s/km no fim. Mediana = 240; limite = 240 x 1,20 = 288.
`290 > 288`: sai, sobram os 3 tiros. A 288 o limite entra.

### Em linguagem simples
Um treino de tiros de 1 km é um treino em que o que importa são as repetições de 1 km, com pausa ou trote entre elas.
A regra procura isso em três passos: acha as voltas de 1 km que estão cercadas por recuperação (e não coladas a outras
voltas de 1 km no mesmo ritmo, que é rodagem); exige pelo menos 3; e confere que elas são a parte principal do treino,
isto é, que somam pelo menos tanta distância quanto as voltas curtas (por exemplo, de 400 m) do mesmo treino.
Se os tiros curtos pesam mais, o treino é de tiros curtos e não entra na série de 1 km. Desde a `@4`, dois filtros
tiram o que parece tiro mas não é: o **ritmo parecido** (um km bem mais lento que os outros tiros é desaquecimento, não
repetição) e o **bloco contínuo** (um km forte colado, mesmo por cima de uma pausa curta, a outro km de corrida quase tão
rápido é progressivo ou fartlek, não tiro).

### Exemplos à mão
- 6 x 1000 m com 5 recuperações de 400 m sem rótulo: 6000 m de tiros contra 2000 m de voltas curtas: dentro.
- 3 x 1000 m e 8 x 400 m a 225 s/km: 3000 m de tiros contra 3200 m de curtos: 3000 < 3200, o bloco principal são
  os tiros curtos, fora. Com 2 x 1000 m e 8 x 400 m, fora já pelo mínimo de 3 tiros.
- 3 x 1000 m e 10 x 300 m: 3000 m contra 3000 m. A regra é "maior ou igual": dentro. Com mais 150 m de curtos, fora.
- 6 x 1000 m e 4 x 400 m: 6000 m contra 1600 m: dentro.
- 6 x 1000 m a 240 s/km com recuperação de 400 m a 450 s/km: `240 <= 450 x 0,92 = 414`, os 6 são tiros.
- 8 voltas de 1000 m (328 a 340 s) e uma parcial de 350 m: a razão mais baixa entre voltas vizinhas é
  `328 / 340 = 0,965`, acima de 0,92: nenhuma é tiro, mesmo que a parcial seja `rest`.
- 4 blocos de 3 x 1000 m a 280 s/km com parada de 7 m: as voltas do meio têm vizinha de 1 km no mesmo ritmo,
  e as das pontas, de um dos lados: nenhuma tiro.

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
  (precisa do histórico), e não em `detectar_tiros`, que olha uma atividade só.

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
- `versao`: versão da regra de detecção (`tiros_1km@4`), vinda da detecção e levada até o ponto da série
  (`SessaoTiros.versao`, `PontoSessao.versao`). É o valor a gravar em `segmento.versao_deteccao` ([[decisoes/0002-segmento-intensidade-e-versao]]).
  Mudou regra ou constante: sobe `VERSAO`.
- Arredondamento só na apresentação, 1 casa decimal (`para_apresentacao`); o cálculo usa o valor cheio.

Exemplo à mão: tiros 1000 m/240 s/160 bpm, 1000 m/236 s/165 bpm, 990 m/238 s sem FC:
pace = 714 / 2990 x 1000 = 238,8 s/km; FC = (160x240 + 165x236) / 476 = 162,5 bpm.

Exemplo à mão do melhor tiro (#151): tiros 1000 m/250 s/165 bpm, 1000 m/244 s/170 bpm, 990 m/247 s sem FC. Paces:
250,0; 244,0; 247 / 990 x 1000 = 249,5 s/km. Melhor: 244,0 s/km (4:04), FC 170 bpm. Média: 741 / 2990 x 1000 =
247,8 s/km (a média aparece como secundária). Empate: 1000 m/240 s/160 bpm e 1000 m/240 s/170 bpm têm o mesmo pace;
vale o primeiro (FC 160). Se o melhor fosse o de 990 m, a FC do melhor tiro seria `None`, sem emprestar a de outro.

**Versão: não sobe** (`tiros_1km@4` segue). O melhor tiro é só uma agregação a mais sobre os tiros que a detecção já
devolve; não muda `detectar_tiros`, constantes nem quais voltas são tiro. Por isso **não pede reclassificação**
(`classificar_atividades`); os segmentos já gravados com `@4` continuam válidos.

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
nenhum valor da métrica, só o desenho, e não muda `tiros_1km@4`.

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

## Código e teste
- Melhor tiro (#151): sem mudança de versão, ver "Agregação por sessão".
- Código: `services/api/app/metricas/tiros_1km.py` (`detectar_tiros`, `agregar_sessao`, `serie_por_sessao`); escala dos eixos em `services/api/app/graficos/escala.py`
- Testes: `services/api/tests/metricas/test_agregacao_sessao.py` (exemplo acima) e
  `services/api/tests/metricas/test_tiros_1km.py` (valor esperado calculado à mão em cada caso, ex.:
  6 x 1 km com recuperação de 400 m: tiros a 240 s/km contra 450 s/km, limite 414 s/km).

## Limitações e quando não usar
- **Validado com um atleta.** Os limites da `@4` (15% de bloco contínuo, 20% de ritmo parecido, 10% do ritmo habitual)
  foram calibrados com uma amostra pequena e ainda não foram testados com outros perfis. Atleta que faz progressivo com km final bem mais rápido que os anteriores (mais de 15%) ou que treina tiros
  em ritmo próximo ao de rodagem pode ser classificado diferente do que espera.
- Ficam como limitação, sem critério geral encontrado: (a) progressivo ou série moderada em que o km forte é mais de
  15% mais rápido que o km vizinho e há recuperação curta (parece tiro de verdade); (b) fartlek de 1 km forte e 500 m
  moderados, que não se distingue estruturalmente de tiros com trote de 500 m; (c) séries de 1 km em ritmo moderado com
  paradas de cerca de 1 min, que têm a mesma estrutura de tiros. A regra não usa dia da semana nem nada específico do atleta.
- Efeito colateral aceito da `@4`: uma série de 3 tiros em que um é desaquecimento lento perde o terceiro e deixa de
  valer; e uma sessão com um km de aquecimento mais rápido que 85% do tiro, colado por pausa curta, perde esse tiro.
- O filtro do ritmo habitual (agora 10%) e a janela de 12 semanas também só foram vistos com **um atleta**. Atleta novo, sem corridas anteriores, não é filtrado (e com menos de 10 corridas na janela o
  histórico todo é a referência, que é menos preciso). Um treino de tiros leve, mais lento que 10% abaixo do ritmo
  habitual (por exemplo, volta à corrida depois de lesão), não entra na série de tiros.
- Só detecta tiros de 1 km; 400 m, 2 km e outras distâncias ficam fora da Meta 1. Num treino misto, só entra
  se o volume dos tiros de 1 km for pelo menos o dos curtos (item 6); aí só os de 1 km vão para a série.
- Uma volta solta de ~1 km, sem rótulo, no fim do treino (por exemplo, um desaquecimento de 1 km) vale como tiro se
  for até 20% mais lenta que a mediana dos tiros (item 7 da `@4`); mais lenta que isso, sai.
- Tiros de 1 km seguidos, sem volta de recuperação entre eles (o relógio não marcou a pausa), não são detectados:
  a regra não distingue esse caso de um bloco contínuo de vários km. É o preço de não marcar rodagens.
- Um tiro precisa ter volta de recuperação (ou pausa) dos dois lados, ou ser a primeira/última volta. Treino com
  voltas de 1 km sem `lap` manual (só auto-lap) não é visto como intervalado.
- Corrida de prova ou longão com variação grande de ritmo e voltas de 1 km alternadas com pausas pode passar na
  regra; é o comportamento esperado, não um erro.
- Esteira sem GPS: a distância vem do sensor do aparelho e pode se afastar da faixa de ± 50 m.
- **Esteira fica fora da série** (decisão do Angelo, #51): a detecção classifica uma esteira como qualquer corrida,
  mas `serie_tiros_1km`/`sessoes_tiros_1km` descartam `subtipo = "esteira"`. A atividade segue guardada.
