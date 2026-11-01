---
tipo: metrica
status: em-uso
dono: caio
atualizado: 2026-11-01
links: [[modulos/grafico-tiros]], [[produto/meta-1-como-reproduzir]], [[produto/roadmap]], [[decisoes/0001-modelo-de-dados-minimo]], [[decisoes/0002-segmento-intensidade-e-versao]], [[glossario]]
---
# Tiros de 1 km

## O que mede
Quais voltas de uma corrida são tiros de 1 km e se a atividade é um treino intervalado. É a base da série
"pace e FC médios dos tiros por sessão" da Meta 1. Cálculo determinístico, em código, sem banco e sem IA.

## Fórmula
Versão do cálculo: `tiros_1km@2` (a `@1` foi substituída, ver "Histórico" abaixo). Constantes em
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
6. `eh_intervalado` = **pelo menos 3 tiros**.

### Por que a estrutura e não a intensidade
Um treino de tiros é uma alternância de esforço e pausa; uma rodagem com auto-lap de 1 km é uma sequência de
voltas parecidas, sem pausa entre elas. A regra pede o que distingue os dois. A intensidade gravada pelo relógio
não distingue: numa rodagem real quase todas as voltas vêm `active` e a última, parcial, vem `rest`, `recovery` ou
`cooldown`, o que parecia "contraste" e fazia a `@1` marcar todas as voltas de 1 km como tiro.

### Por que 8%
Numa rodagem leve com auto-lap, as voltas variam cerca de 3% a 4% de uma para a outra (relevo, vento, parada
em semáforo); 8% fica com folga acima desse ruído. Um tiro de verdade costuma ser 15% a 30% mais rápido que a
recuperação, então 8% não perde tiros. O valor é decisão do projeto, não vem de artigo.

### Exemplos à mão
- 6 x 1000 m a 240 s/km com recuperação de 400 m a 450 s/km: `240 <= 450 x 0,92 = 414`, os 6 são tiros.
- 8 voltas de 1000 m (328 a 340 s) e uma parcial de 350 m: a razão mais baixa entre voltas vizinhas é
  `328 / 340 = 0,965`, acima de 0,92: nenhuma é tiro, mesmo que a parcial seja `rest`.
- 4 blocos de 3 x 1000 m a 280 s/km com parada de 7 m: as voltas do meio têm vizinha de 1 km no mesmo ritmo,
  e as das pontas, de um dos lados: nenhuma tiro.

## Agregação por sessão (issue #12)
Um ponto por atividade com `eh_intervalado` verdadeiro; série ordenada por data (empate: id da atividade).
Rodagem leve e natação não entram.

- **Pace da sessão (s/km)** = soma das durações dos tiros / soma das distâncias dos tiros x 1000. É a média
  ponderada pela distância, não a média simples dos paces.
- **FC da sessão (bpm)** = soma(FC x duração) / soma(duração), média ponderada pela duração. Tiros sem FC ficam
  fora (inclusive do peso); se nenhum tem FC, `None`.
- Também saem `n_tiros`, `data` (data local do início) e `atividade_id`.
- `versao`: versão da regra de detecção (`tiros_1km@2`), vinda da detecção e levada até o ponto da série
  (`SessaoTiros.versao`, `PontoSessao.versao`). É o valor a gravar em `segmento.versao_deteccao` ([[decisoes/0002-segmento-intensidade-e-versao]]).
  Mudou regra ou constante: sobe `VERSAO`.
- Arredondamento só na apresentação, 1 casa decimal (`para_apresentacao`); o cálculo usa o valor cheio.

Exemplo à mão: tiros 1000 m/240 s/160 bpm, 1000 m/236 s/165 bpm, 990 m/238 s sem FC:
pace = 714 / 2990 x 1000 = 238,8 s/km; FC = (160x240 + 165x236) / 476 = 162,5 bpm.

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

| Atividade | Tiros | Pace (s/km) | FC (bpm) | Conta |
|---|---|---|---|---|
| 1000000001 (6 x 1 km) | 6 | 250,83 (4:10,8) | 170,30 | 1505 s / 6000 m; 256309 / 1505 |
| 1000000002 (5 x 1 km) | 5 | 237,0 (3:57,0) | 171,77 | 1185 s / 5000 m; 203546 / 1185 |

Ficam fora da série: 1000000003 (corrida leve, sem tiros), 1000000004 (natação) e 1000000005 (sem FIT).

## Dados de entrada
Por volta: `ordem`, `distancia_m`, `duracao_s`, `fc_media` (opcional) e `intensidade` (opcional; campo
`segmento.intensidade` proposto na ADR da issue #9). Mais a modalidade da atividade.

## Referência
Regra própria do projeto; não há artigo.

## Histórico
- `tiros_1km@1` (#11): tiro por intensidade quando havia 2 ou mais valores diferentes; senão, pace 8% abaixo da
  mediana. Em dado real marcava rodagens leves como intervalado (a volta final parcial criava o "contraste").
- `tiros_1km@2` (#48): a regra acima. Os segmentos já gravados com `@1` precisam ser reclassificados.

## Código e teste
- Código: `services/api/app/metricas/tiros_1km.py` (`detectar_tiros`, `agregar_sessao`, `serie_por_sessao`)
- Testes: `services/api/tests/metricas/test_agregacao_sessao.py` (exemplo acima) e
  `services/api/tests/metricas/test_tiros_1km.py` (valor esperado calculado à mão em cada caso, ex.:
  6 x 1 km com recuperação de 400 m: tiros a 240 s/km contra 450 s/km, limite 414 s/km).

## Limitações e quando não usar
- Só detecta tiros de 1 km; 400 m, 2 km e outras distâncias ficam fora da Meta 1. Num treino misto (tiros de
  1 km e curtos), só os de 1 km entram na série.
- Tiros de 1 km seguidos, sem volta de recuperação entre eles (o relógio não marcou a pausa), não são detectados:
  a regra não distingue esse caso de um bloco contínuo de vários km. É o preço de não marcar rodagens.
- Um tiro precisa ter volta de recuperação (ou pausa) dos dois lados, ou ser a primeira/última volta. Treino com
  voltas de 1 km sem `lap` manual (só auto-lap) não é visto como intervalado.
- Corrida de prova ou longão com variação grande de ritmo e voltas de 1 km alternadas com pausas pode passar na
  regra; é o comportamento esperado, não um erro.
- Esteira sem GPS: a distância vem do sensor do aparelho e pode se afastar da faixa de ± 50 m.
