---
tipo: metrica
status: rascunho
dono: caio
atualizado: 2026-11-06
links: [[decisoes/0008-deteccao-de-esforcos]], [[metricas/esforcos-oraculo]], [[metricas/tiros-1km]], [[modulos/ingestao-garmin]], [[produto/roadmap]], [[glossario]]
---
# Esforços: blocos do treino

## O que mede
Lê a sequência de voltas de uma atividade como **blocos** e dá a cada bloco uma categoria: `aquecimento`, `esforco`,
`recuperacao`, `desaquecimento` ou `leve`. É o primeiro passo comum da detecção de esforços (corrida por distância,
ciclismo por duração; [[decisoes/0008-deteccao-de-esforcos]]). Esta nota cobre a versão `esforcos@1`: a função de
blocos (#162) e as **faixas de distância dos esforços de corrida** (#163) e as **faixas de duração dos esforços de ciclismo** (#164), nas seções abaixo.
O **treino-chave contínuo** (#165) fecha a nota. Cálculo
determinístico, em código, sem banco e sem IA. Só corrida e ciclismo; outra modalidade devolve zero blocos.

## Fórmula
Entrada: as voltas (`ordem`, `inicio_offset_s`, `duracao_s` em movimento, `distancia_m`, `fc_media`, `intensidade`) e a
**referência** de intensidade. Constantes em `services/api/app/metricas/esforcos.py`; todas são decisão do projeto,
sem artigo, aprovadas em 04/11.

1. **Tempo parado** depois da volta `i`: `(inicio[i+1] - inicio[i]) - duracao[i]`, mínimo 0; a última volta tem 0.
   `inicio_offset_s` é tempo corrido e `duracao_s` é o cronômetro (que a pausa automática para), então a diferença é o
   tempo de pausa.
2. **Volta de pausa** (o atleta parou sem o relógio pausar; não é bloco): corrida, pace maior que
   `PAUSA_PACE_S_KM = 600` s/km ou distância menor que `PAUSA_DIST_MIN_M = 50` m; ciclismo, velocidade menor que
   `PAUSA_VEL_KMH = 5` km/h; qualquer modalidade, distância ou duração zero. Ela sempre separa os blocos, e a
   duração dela mais o tempo parado dela entram no `parada_apos_s` do bloco anterior. Pausa antes do primeiro bloco
   ou depois do último é ignorada.
3. **Junção**: a volta entra no bloco acumulado quando as duas condições valem: tempo parado depois da volta anterior
   **menor que** `PAUSA_SEPARA_S` (15 s na corrida, 30 s no ciclismo) e ritmo a no máximo `JUNTAR_TOLERANCIA = 5%` do
   ritmo do bloco acumulado. Ritmo = pace (s/km) na corrida e velocidade (km/h) no ciclismo, comparados com o do
   **bloco acumulado** (ponderado por distância), não com a volta anterior. Os limites de 5% e de 15 s/30 s são
   inclusivos/exclusivos como na ADR: 5,0% ainda junta; 14 s junta e 15 s separa.
4. **Medidas do bloco**: distância e duração são somas; pace = soma(duração) / soma(distância) x 1000 (nunca a média
   dos paces); velocidade = soma(distância) / soma(duração) x 3,6; FC = soma(FC x duração) / soma(duração), só sobre
   voltas com FC (nula se nenhuma tem). `parada_apos_s` = tempo parado depois do bloco até o seguinte (0 no último).
5. **Referência** (`ref`): o ritmo habitual do atleta em s/km (`pace_habitual`) ou a velocidade habitual em km/h. Sem
   ela, vale a **mediana, ponderada pela duração, dos blocos da própria atividade** (o menor valor cujo tempo
   acumulado chega à metade do total), marcada em `ref_origem = "atividade"`.
6. **Esforço**: corrida, pace do bloco `<= ref x 0,90`; ciclismo, velocidade `>= ref x 1,15`.
7. **Categoria pela posição**: com pelo menos um esforço, os blocos antes do primeiro são `aquecimento`, os depois do
   último são `desaquecimento` e os de permeio que não são esforço são `recuperacao`. Sem nenhum esforço, todos são
   `leve`. A intensidade do FIT (`warmup`, `cooldown`) **não muda a categoria** (só dica; a estrutura vence).

Exemplo: 1000 m em 240 s + 500 m em 120,5 s. Pace das voltas 240 e 241 s/km: diferença 0,42% < 5%, sem parada: um
bloco de 1500 m em 360,5 s, pace = 360,5 / 1500 x 1000 = **240,3333 s/km**. Com ref 330, limiar 297: esforço.

## Esforços de corrida por distância (#163)
`esforcos_corrida(resultado_dos_blocos)` pega os blocos de categoria `esforco` de uma corrida e devolve, para cada um,
a **faixa** pela distância do bloco inteiro (laps já juntados), com pace e FC do bloco. Faixas da ADR 0008, item 5
(aprovadas pelo Angelo em 04/11): tolerância `max(5% do alvo, 30 m)` para cada lado, limites inclusivos.

| faixa | aceita (m) | faixa | aceita (m) |
|---|---|---|---|
| `d200` | 170 a 230 | `d1000` | 950 a 1050 |
| `d300` | 270 a 330 | `d1200` | 1140 a 1260 |
| `d400` | 370 a 430 | `d1500` | 1425 a 1575 |
| `d500` | 470 a 530 | `d2000` | 1900 a 2100 |
| `d600` | 570 a 630 | `d3000` | 2850 a 3150 |
| `d800` | 760 a 840 | `d5000` | 4750 a 5250 |

Conta: `d800` = max(5% x 800 = 40, 30) = 40, logo 760 a 840; `d200` = max(10, 30) = 30, logo 170 a 230; `d1500` =
max(75, 30) = 75, logo 1425 a 1575. As faixas não se sobrepõem (o menor vão é de 40 m, entre `d500` e `d600`).
**Esforço entre faixas ou fora delas** (700 m, 1350 m, 8 km) continua sendo esforço, com `faixa = None` e a distância
real. Não é arredondado para a faixa mais próxima.

Exemplos à mão (sintéticos, referência 330 s/km, limiar 297 s/km):
- 10 x 400 m em 88 s com 90 s parado: pace 88 / 400 x 1000 = 220 s/km, 10 esforços `d400`, recuperação 9 x 90 = 810 s.
- 1000 m em 240 s + 500 m em 120,5 s, sem parada: junta (0,42%), 1500 m, pace 240,3333 s/km, faixa `d1500`.
- 1350 m em 300 s (222,2 s/km): esforço sem faixa (entre 1260 e 1425).
- 8 km contínuos a 270 s/km: esforço sem faixa (passa de 5250 m); o treino-chave contínuo está na seção abaixo (#165).

## Esforços de ciclismo por duração (#164)
`esforcos_ciclismo(resultado_dos_blocos)` pega os blocos de categoria `esforco` de um pedal e devolve, para cada um, a
**faixa** pela duração em movimento do bloco inteiro (laps já juntados), com velocidade média (km/h) e FC. Aquecimento,
recuperação e desaquecimento não entram. A junção (parada menor que 30 s e velocidade a até 5% do bloco acumulado) e o
limiar (velocidade >= habitual x 1,15) são os dos blocos. Não há potência.

Faixas da ADR 0008, item 5 (aprovadas pelo Angelo em 04/11): tolerância `max(8% do alvo, 15 s)` para cada lado,
limites inclusivos, em segundos de tempo em movimento.

| faixa | aceita (s) | faixa | aceita (s) |
|---|---|---|---|
| `t1` | 45 a 75 | `t12` | 662 a 778 |
| `t2` | 105 a 135 | `t15` | 828 a 972 |
| `t3` | 165 a 195 | `t20` | 1104 a 1296 |
| `t4` | 221 a 259 | `t30` | 1656 a 1944 |
| `t5` | 276 a 324 | `t40` | 2208 a 2592 |
| `t8` | 442 a 518 | `t60` | 3312 a 3888 |
| `t10` | 552 a 648 | | |

Conta: `t1` = max(4,8; 15) = 15 s, logo 45 a 75; `t4` = max(19,2; 15) = 19,2, logo 220,8 a 259,2, que a ADR escreve
221 a 259; `t12` = max(57,6; 15) = 57,6, logo 662,4 a 777,6, escrito 662 a 778 (a ADR arredonda ao segundo mais
próximo; o texto dela diz "para dentro", o que daria 663 a 777 só na `t12`; vale a tabela da ADR). Fora de
qualquer faixa (360 s, entre `t5` e `t8`) o esforço continua esforço com `faixa = None` e a duração real.

Exemplos à mão (sintéticos):
- 5 x (240 s a 2400 m + 120 s leve), ref 22 km/h, limiar 25,3: cada esforço 2400 / 240 x 3,6 = 36 km/h, faixa `t4`;
  as recuperações (22 km/h) e o aquecimento (25 km/h) ficam fora.
- 5000 m em 750 s + 3000 m em 450 s, ref 20 km/h (limiar 23): 24 km/h nas duas, sem parada, juntam: 8000 m, 1200 s,
  faixa `t20`; FC = (150 x 750 + 156 x 450) / 1200 = 152,25.

## Treino-chave contínuo (#165)
`treino_chave_continuo(resultado_dos_blocos, modalidade)` marca a atividade que é um treino contínuo forte (ritmo,
limiar, progressivo forte), mesmo sem repetições. Regra da ADR 0008, item 6, aprovada pelo Angelo em 04/11; é regra
própria do projeto, sem artigo (a ADR cita Daniels só como inspiração para os ~20 min, não conferido).

1. **Sequência forte** = blocos `esforco` vizinhos sem `recuperacao` entre eles. "Forte" é o limiar do esforço dos
   blocos: corrida, pace `<= habitual x 0,90` (10% de ganho; `ESFORCO_GANHO_CORRIDA`); ciclismo, velocidade
   `>= habitual x 1,15` (15%; `ESFORCO_GANHO_CICLISMO`). Como cada bloco já passou no limiar, o ritmo é forte durante
   todo o tempo da sequência.
2. **Treino-chave contínuo** quando a maior sequência (a de mais tempo em movimento) soma pelo menos
   `CONTINUO_MIN_S = 1200` s (20 min, nas duas modalidades, limite inclusivo) **e** há menos de
   `CONTINUO_FORA_MAX = 2` esforços fora dela (0 ou 1 passa; 2 ou mais é treino de repetição).
3. Resultado: `treino_chave`, `motivo` (`continuo`, `sem_esforco`, `curto`, `repeticoes`), a sequência (blocos inicial e
   final, duração, distância, pace e velocidade), `margem` (corrida `1 - pace/ref`; ciclismo `velocidade/ref - 1`),
   `esforcos_fora`, `referencia` e `ref_origem`.

**Premissa pendente de confirmação do Angelo (não é decisão; vai além do texto da ADR)**: uma parada de `PAUSA_SEPARA_S` ou mais entre dois esforços (15 s na corrida,
30 s no ciclismo) conta como recuperação e corta a sequência. Sem isso, 5 x 1 km a 240 s/km com 90 s parados somariam
1200 s e seriam "contínuos". Dois esforços vizinhos separados só por diferença de ritmo (mais de 5%, parada menor) seguem
na mesma sequência: é o progressivo forte.
A ADR 0008 aprovou os 15 s e 30 s só para separar blocos na junção de laps (item 2 de "A confirmar"); usá-los para cortar a
sequência do treino-chave ainda precisa do aval do Angelo. Até lá a regra vale como premissa e o resultado pode mudar.

Exemplos à mão (sintéticos, habitual de 330 s/km, limiar 297 s/km):
- **8 km a 270 s/km**: 8 x 1000 m em 270 s, 2160 s >= 1200 s, 270 <= 297, margem 1 - 270/330 = 18,2%, 0 esforços fora:
  **treino-chave** (`continuo`).
- **Rodagem a 330 s/km**: 330 > 297, nenhum esforço: não é (`sem_esforco`).
- **Limite exato de ritmo**: 5000 m em 1485 s = 297 s/km (330 x 0,90) entra; 5000 m em 1486 s = 297,2 s/km não.
- **Limite exato de duração**: 4800 m em 1200 s (250 s/km) entra; 4796 m em 1199 s não (`curto`).
- **Contínuo e um 400 m forte** (recuperação de 400 m em 168 s entre eles): 1 esforço fora, passa. Com dois 400 m fortes
  fora: `repeticoes`, não é.
- **5 x 1000 m a 240 s/km, 90 s parados**: cada sequência tem 240 s, `curto`.
- **Progressivo forte**: 4 x 1000 m a 296 s/km e 4 x 1000 m a 270 s/km, sem parada (296 para 270 é -8,8%, dois blocos):
  uma sequência de 4 x 296 + 4 x 270 = 2264 s, **treino-chave**.
- **Ciclismo, habitual de 20 km/h** (limiar 23): 5000 m em 750 s + 3000 m em 450 s juntam em 8000 m, 1200 s, 24 km/h,
  margem 24/20 - 1 = 20%: **treino-chave** (oráculo 7). 23 km/h exatos entram; 22,5 km/h (+12,5%) não, porque o
  ciclismo exige 15% e não 10%.
- **Ciclismo 5 x 4 min a 36 km/h** (oráculo 6): maior sequência de 240 s, `curto`.

**Limitações**
- **Referência por atividade** (atleta sem histórico): num treino contínuo a mediana é o próprio bloco, que nunca
  bate o limiar; o contínuo não é detectado. `ref_origem = "atividade"` vai no resultado para a tela avisar.
- **Dois blocos longos com recuperação** (por exemplo 2 x 25 min): cada um é uma sequência de 25 min, mas o outro conta
  como 1 esforço fora (passa) ou mais (não passa); com blocos fracionados em 2 ou mais esforços vira repetição.
  A regra não distingue "tempo 2 x 25" de intervalado longo.
- Fartlek moderado e progressivo forte podem cair aqui (ADR, item 6); a visão de tiros de 1 km continua os excluindo.
- Ciclismo sem potência: relevo e vento mexem na velocidade, então uma subida longa pode parecer treino contínuo forte.
- O teto de 20 min é igual nas duas modalidades; ainda sem calibração pelos recordes (ADR, item 7).

## Dados de entrada
Voltas do banco (`segmento`: `ordem`, `inicio_offset_s`, `duracao_s`, `distancia_m`, `fc_media`, `intensidade`) e
`atividade.modalidade`. O FIT sem `start_time` no lap grava `inicio_offset_s = 0` e o tempo parado não é computável: a
conta dá 0 e a parada só aparece como volta de pausa (ADR 0008, "A confirmar", item 5).

## Referência
- [[decisoes/0008-deteccao-de-esforcos]], itens 1 a 5. Regra própria do projeto; os valores de referência
  bibliográfica da ADR (Buchheit e Laursen, Seiler, Daniels) ainda não foram conferidos.
- Oráculo: [[metricas/esforcos-oraculo]] (sete atividades sintéticas, com a conta à mão).

## Código e teste
- Código: `services/api/app/metricas/esforcos.py` (`montar_blocos`, `esforcos_corrida`, `faixa_de_distancia`,
  `FAIXAS_CORRIDA`, `VERSAO = "esforcos@1"`).
- Treino-chave contínuo: `treino_chave_continuo`, `TreinoChaveContinuo`, `CONTINUO_MIN_S`, `CONTINUO_FORA_MAX`; teste
  `services/api/tests/metricas/test_esforcos_treino_chave.py` (8 km a 270, rodagem a 330, limites exatos de ritmo e de
  duração, repetições fora, parada que corta, progressivo, ciclismo a 15% e as sete atividades do oráculo).
- Ciclismo: `esforcos_ciclismo`, `faixa_de_duracao`, `FAIXAS_CICLISMO`; teste
  `services/api/tests/metricas/test_esforcos_ciclismo.py` (fórmula das faixas, limites, 5 x 4 min, 20 min cortados
  por lap, aquecimento fora, sem faixa e os dois pedais do oráculo).
- Teste das faixas: `services/api/tests/metricas/test_esforcos_corrida.py` (fórmula de cada faixa, limites de 760 e
  840 m, entre faixas, 10 x 400 m, 1000 + 500 m, FC ponderada e as cinco corridas do oráculo).
- Teste: `services/api/tests/metricas/test_esforcos_blocos.py` (valor esperado calculado à mão: 1000 m + 500 m viram
  1500 m; pausa de 90 s separa; limites de 14 s/15 s e de 5%; aquecimento e desaquecimento; rodagem leve; FC
  ponderada; mediana da atividade) e os blocos de cada FIT sintético contra `ESPERADO` de
  `test_esforcos_oraculo.py`.

## Limitações e quando não usar
- **Referência por atividade**: sem histórico, quando o esforço domina o volume a mediana sobe e o esforço some.
  Nas fixtures, a de 3 x 1500 m (1089 s de esforço em 2091 s) vira toda `leve`, e o contínuo forte e a rodagem
  (um bloco só) também; as outras quatro mantêm o resultado do oráculo. Por isso `ref_origem` vai no resultado e a
  referência por atividade é só reserva.
- **Ciclismo sem potência**: a velocidade sofre com relevo e vento (sobe-e-desce vira esforço ou some); sem altimetria
  no modelo.
- Sem teto de duração para o aquecimento e o desaquecimento (tudo antes do primeiro e depois do último esforço).
- **Progressivo suave** e fartlek moderado juntam num bloco só ou viram um esforço contínuo; o treino-chave contínuo
  (seção acima) os marca quando passam do limiar de esforço por 20 min.
- Pausa só por pace, distância ou velocidade quando o relógio não grava `start_time`; uma parada curta (menos de
  15 s) dentro do esforço não separa os blocos.
- **Faixa pela soma**: dois esforços vizinhos que a regra de 5% não junta (1000 m a 250 s/km e 500 m a 270 s/km, por
  exemplo) ficam como `d1000` e `d500`, não como um `d1500`. Decidido pelo Angelo em 04/11: contam como dois esforços
  separados (a regra de junção segue como está).
- A tabela `bloco_atividade` (ADR 0008, item 9) é da Duda e da #166; esta função não toca o banco.
