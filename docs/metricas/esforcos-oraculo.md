---
tipo: metrica
status: rascunho
dono: caio
atualizado: 2026-11-04
links: [[decisoes/0008-deteccao-de-esforcos]], [[metricas/tiros-1km]], [[modulos/ingestao-garmin]], [[produto/roadmap]], [[glossario]]
---
# Detecção de esforços: fixtures e oráculo

## O que mede
Os **blocos** esperados de sete atividades sintéticas (cinco corridas e dois pedais), com a conta feita à mão: categoria
(`aquecimento`, `esforco`, `recuperacao`, `desaquecimento`, `leve`), voltas juntadas, distância, duração em movimento,
pace (corrida) ou velocidade (ciclismo), FC, faixa, tempo parado e treino-chave. É o **oráculo** que a função de
blocos (#162), a corrida (#163), o ciclismo (#164 e #165), o comando e o worker (#166) e a API reaproveitam. Nenhum
número vem de IA nem de dado real. As regras são as da [[decisoes/0008-deteccao-de-esforcos]].

## Fórmula
Bloco = uma ou mais voltas consecutivas juntadas (ADR 0008, item 2):
- pace do bloco (s/km) = soma(duração) / soma(distância) x 1000, nunca a média dos paces das voltas;
- velocidade (km/h) = soma(distância) / soma(duração) x 3,6;
- FC do bloco (bpm) = soma(FC x duração) / soma(duração);
- tempo parado da volta `i` = (início de `i+1` - início de `i`) - duração de `i`; `parada_apos_s` do bloco é o da
  última volta dele;
- esforço: corrida, pace <= ritmo habitual x 0,90; ciclismo, velocidade >= velocidade habitual x 1,15;
- juntar: parada menor que 15 s (corrida) ou 30 s (ciclismo) e ritmo a menos de 5% do bloco acumulado.

Os limites são decisão do projeto, não de artigo (ADR 0008, "Consequências"). Os valores de referência de cada
atividade (330 s/km, 22 km/h, 20 km/h) são inventados e entram no teste, não no FIT.

## Dados de entrada
Fixtures em `tests/fixtures/garmin/esforcos/` (FIT inventados, sem GPS, sem nome nem id real), geradas por
`tests/fixtures/garmin/gerar_fixtures.py` (tabelas `VOLTAS_E1` a `VOLTAS_E7`). Voltas numeradas a partir de 0
(`segmento.ordem`). As durações e paradas são em segundos inteiros, porque o `start_time` do FIT tem resolução de 1 s.
No FIT, a parada aparece como diferença entre os `start_time` das voltas; `total_timer_time` é só o tempo em movimento
(ADR 0008, item 3).

| Arquivo | Atividade | Exemplo da ADR | Ref. | Blocos |
|---|---|---|---|---|
| `esforcos_corrida_400_com_pausa.fit` | aquecimento, 10 x 400 m com 90 s parado, desaquecimento | 2 | 330 s/km | 12 |
| `esforcos_corrida_1500_lap_automatico.fit` | aquecimento em 2 laps, 3 x 1500 m cortados em 1000 + 500 m, desaquecimento | 1 | 330 s/km | 5 |
| `esforcos_corrida_continuo_forte.fit` | 8 km contínuos fortes, 8 laps de 1 km | 3 | 330 s/km | 1 |
| `esforcos_corrida_rodagem_leve.fit` | rodagem de 6 km, 6 laps de 1 km | regra geral | 330 s/km | 1 |
| `esforcos_corrida_misto.fit` | 5 x 1 km e 8 x 400 m, com recuperações | item 8, caso 4 | 330 s/km | 27 |
| `esforcos_ciclismo_blocos_4min.fit` | 15 min, 5 x (4 min + 2 min), 10 min | 4 | 22 km/h | 12 |
| `esforcos_ciclismo_lap_automatico.fit` | 10 min, bloco de 20 min cortado em 5 km + 3 km, 10 min | 5 | 20 km/h | 3 |

Oráculo no código: constante `ESPERADO` em `services/api/tests/metricas/test_esforcos_oraculo.py`.

## Contas à mão

Limiar de esforço da corrida com ref 330 s/km: 330 x 0,90 = **297 s/km**. Ciclismo com ref 22 km/h:
22 x 1,15 = **25,3 km/h**; com ref 20 km/h: 20 x 1,15 = **23,0 km/h**.

### 1. Corrida, 10 x 400 m com 90 s parado
Voltas: 0 aquecimento 2000 m em 660 s; 1 a 10 esforços de 400 m em 88 s; 11 desaquecimento 1000 m em 340 s; 90 s
parados depois das voltas 1 a 9.
- Aquecimento: 660 / 2000 x 1000 = 330 s/km (FC 130). Não é esforço (330 > 297).
- Cada 400 m: 88 / 400 x 1000 = **220 s/km** <= 297: esforço, faixa `d400` (370 a 430 m). FC por esforço: 160, 164, 167,
  169, 171, 172, 173, 174, 175, 176.
- Nada se junta: 90 s >= 15 s (e 220 vs 330 passa de 5% de qualquer jeito). Tempo de recuperação: 9 x 90 = **810 s**.
- Desaquecimento: 340 / 1000 x 1000 = 340 s/km (FC 140).
- Os 10 esforços somam 4000 m em 880 s. Total: 12 blocos (1 + 10 + 1).

### 2. Corrida, 3 x 1500 m cortados pelo lap automático
Os números diferem um pouco do exemplo 1 da ADR 0008 (240 s e 241 s/km): aqui cada repetição tem laps diferentes, para
cobrir três casos de junção. A regra é a mesma.
Voltas: 0 e 1 aquecimento (1000 m em 330 s e 1000 m em 332 s); 2 e 3 (1000 m em 240 s + 500 m em 121 s, parada
de 120 s); 4 e 5 (1000 m em 242 s + 500 m em 121 s, parada de 120 s); 6 e 7 (1000 m em 243 s + 500 m em 122 s);
8 desaquecimento 1000 m em 340 s.
- Aquecimento: 332 vs 330 = +0,6%, menor que 5%, sem parada: **juntam**. 2000 m, 662 s, pace 662 / 2000 x 1000 =
  **331,0 s/km**; FC = (128 x 330 + 131 x 332) / 662 = (42240 + 43492) / 662 = 85732 / 662 = 129,5045.
- Repetição 1: pace do 500 m = 121 / 500 x 1000 = 242 s/km contra 240 s/km do bloco: +0,83%, **junta**. 1500 m,
  361 s, pace = 361 / 1500 x 1000 = **240,6667 s/km**; FC = (165 x 240 + 168 x 121) / 361 = (39600 + 20328) / 361 =
  59928 / 361 = 166,0055. Faixa `d1500` (1425 a 1575 m). Parada 120 s >= 15 s: separa da repetição 2.
- Repetição 2: 242 + 121 = 363 s, pace 363 / 1500 x 1000 = **242,0 s/km**; FC = (167 x 242 + 170 x 121) / 363 =
  (40414 + 20570) / 363 = 60984 / 363 = **168,0**.
- Repetição 3: 243 + 122 = 365 s, pace 365 / 1500 x 1000 = **243,3333 s/km** (500 m a 244 s/km, +0,4%); FC =
  (168 x 243 + 171 x 122) / 365 = (40824 + 20862) / 365 = 61686 / 365 = 169,0027.
- Esforço: 240,67, 242,0 e 243,33 são todos <= 297. Desaquecimento: 340 s/km, não junta com 243,33.
- Sem a junção, nenhum lap de 1000 m ou de 500 m seria o esforço de 1500 m: a junção é o que cria o `d1500`.
  Total: 5 blocos. Recuperação entre esforços: 2 x 120 s.

### 3. Corrida, treino contínuo forte
8 voltas de 1000 m em 268, 271, 270, 272, 269, 270, 271 e 269 s.
- Soma das durações: 268 + 271 = 539; + 270 = 809; + 272 = 1081; + 269 = 1350; + 270 = 1620; + 271 = 1891;
  + 269 = **2160 s**.
- Todas as voltas ficam a menos de 5% do bloco acumulado (a maior diferença é de 1,1%, 271 s contra 268 s): **um bloco** de 8000 m, pace 2160 / 8000 x 1000 = **270,0 s/km**.
- 270 <= 297: esforço. Margem sobre o habitual: 1 - 270 / 330 = **18,18%**.
- FC x duração: 150 x 268 + 160 x 271 + 164 x 270 + 166 x 272 + 168 x 269 + 169 x 270 + 170 x 271 + 171 x 269 =
  40200 + 43360 + 44280 + 45152 + 45192 + 45630 + 46070 + 45999 = 355883; FC = 355883 / 2160 = **164,7606**.
- 2160 s >= 1200 s (20 min): **treino-chave contínuo**. 8000 m passa da `d5000` (4750 a 5250 m): sem faixa.
  Sem aquecimento nem desaquecimento (não há bloco antes ou depois do esforço).

### 4. Corrida, rodagem leve
6 voltas de 1000 m em 355, 352, 350, 351, 349 e 348 s.
- Soma: 355 + 352 + 350 + 351 + 349 + 348 = **2105 s**; pace 2105 / 6000 x 1000 = **350,8333 s/km** > 297: nenhum esforço.
- Juntam (todas a menos de 2% do bloco): **um bloco `leve`** de 6000 m. Sem esforço não há aquecimento nem
  desaquecimento.
- FC x duração: 140 x 355 + 142 x 352 + 143 x 350 + 144 x 351 + 145 x 349 + 146 x 348 = 49700 + 49984 + 50050 +
  50544 + 50605 + 50808 = 301691; FC = 301691 / 2105 = **143,3211**.

### 5. Corrida, treino misto (1 km e curtos)
Voltas: 0 aquecimento 2000 m em 660 s; 5 vezes (1000 m em 250 s + 400 m em 168 s); 8 esforços de 400 m em 92 s com
200 m em 90 s entre eles (7 vezes); desaquecimento 1000 m em 340 s. Sem parada.
- Paces: 1000 m em 250 s = **250 s/km** (esforço, `d1000`); 400 m em 168 s = **420 s/km** (recuperação, 420 > 297);
  400 m em 92 s = **230 s/km** (esforço, `d400`); 200 m em 90 s = **450 s/km** (recuperação).
- Nenhum vizinho está a menos de 5% (250 vs 420, 420 vs 230, 230 vs 450): cada volta é um bloco. Blocos:
  1 + (5 x 2) + (8 + 7) + 1 = **27**. Categorias: 1 aquecimento, 13 esforços, 12 recuperações (5 + 7), 1 desaquecimento.
- A recuperação de 400 m depois do 5o tiro de 1 km fica **entre** esforços (antes do primeiro `d400`): é recuperação,
  não desaquecimento.
- Regressão da visão de tiros de 1 km (ADR, item 8, caso 4): 5 esforços `d1000`; pace da sessão = 5 x 250 / 5000 x
  1000 = **250 s/km** (os `d400` não contam). FC dos `d1000`: 160, 163, 165, 167, 168.

### 6. Ciclismo, 5 x 4 min
Voltas: 0 aquecimento 6250 m em 900 s; 1, 3, 5, 7, 9 esforços de 2400 m em 240 s; 2, 4, 6, 8, 10 de 733,33 m em
120 s; 11 de 4000 m em 600 s. Ref 22 km/h, limiar 25,3 km/h.
- Aquecimento: 6250 / 900 x 3,6 = **25,0 km/h** < 25,3: não é esforço.
- Esforço: 2400 / 240 x 3,6 = **36,0 km/h** >= 25,3 (36 / 22 = 1,64), 4 min: faixa `t4` (221 a 259 s). Cada um tem
  36 x 4 / 60 = 2,4 km.
- Recuperação: 733,33 / 120 x 3,6 = **21,9999 km/h** (22 km/h, com a distância arredondada ao centímetro do FIT).
- Última volta: 4000 / 600 x 3,6 = **24,0 km/h**. Não junta com a recuperação anterior: 24 vs 22 = +9,1% > 5%.
- Posição: antes do 1o esforço, aquecimento; entre os esforços, 4 recuperações; a 5a recuperação e os 10 min vêm depois
  do último esforço: **2 blocos de desaquecimento** (120 + 600 = 720 s = 12 min). Total: 1 + 5 + 4 + 2 = 12 blocos.

### 7. Ciclismo, lap automático cortando um bloco
Voltas: 0 aquecimento 3000 m em 600 s; 1 (5000 m em 750 s) e 2 (3000 m em 450 s); 3 desaquecimento 3000 m em 600 s.
Ref 20 km/h, limiar 23,0 km/h.
- Aquecimento e desaquecimento: 3000 / 600 x 3,6 = **18,0 km/h** < 23.
- Voltas 1 e 2: 5000 / 750 x 3,6 = 24,0 e 3000 / 450 x 3,6 = 24,0 km/h, mesma velocidade, sem parada: **juntam**.
  8000 m, 1200 s, 8000 / 1200 x 3,6 = **24,0 km/h** >= 23: esforço, 20 min, faixa `t20` (1104 a 1296 s).
- FC = (150 x 750 + 156 x 450) / 1200 = (112500 + 70200) / 1200 = 182700 / 1200 = **152,25**.
- Total: 3 blocos (aquecimento, esforço, desaquecimento).
- Treino-chave contínuo (#165, ADR 0008, item 6): 1200 s >= 1200 s e 24,0 >= 23,0 km/h durante os 20 min (os dois limites
  são inclusivos): **é treino-chave**, margem 24 / 20 - 1 = 20%. Corrigido na #165: antes o oráculo o marcava `False`.

## Referência
- [[decisoes/0008-deteccao-de-esforcos]], itens 1 a 6 e 8, e os exemplos 1 a 5. Todos os limites são regra própria do
  projeto, sem artigo (a ADR lista as referências bibliográficas como apoio, ainda não conferidas).
- Garmin FIT SDK, mensagem `lap`: `total_timer_time` (tempo de cronômetro) e `start_time`. Ver [[modulos/ingestao-garmin]].

## Código e teste
- Gerador: `tests/fixtures/garmin/gerar_fixtures.py` (`uv run python tests/fixtures/garmin/gerar_fixtures.py`).
  Determinístico (mesmos bytes a cada execução); o teste falha se os arquivos versionados estiverem desatualizados.
- Teste: `services/api/tests/metricas/test_esforcos_oraculo.py` (valor esperado calculado à mão: as contas acima).
  Confere que cada bloco do `ESPERADO` bate com a soma das voltas da tabela do gerador (distância, duração,
  pace ou velocidade, FC, parada), que o limiar da ADR separa esforço de não esforço, que a posição define aquecimento
  e desaquecimento, que a faixa contém a medida do bloco, e que o leitor de FIT lê as voltas e as paradas esperadas.
- Quem usa: #162 (blocos, parte das voltas e categorias), #163 (corrida: faixas, treino-chave), #164 e #165
  (ciclismo), #166 (banco e worker), #168 (tiros de 1 km sobre os blocos), #172.

## Limitações e quando não usar
- Os FIT têm só voltas (sem `record`, sem GPS, sem altimetria): não exercitam relevo, vento nem pausa automática real.
  A premissa de que `total_timer_time` e `start_time` do lap são coerentes com a pausa automática é sintética aqui; a
  conferência com dado real fica fora do git (ADR 0008, "A confirmar", item 5).
- O oráculo não tem caso de atleta sem histórico (referência por atividade) nem de FIT sem `start_time` do lap
  (`inicio_offset_s` zero, volta de pausa pelo pace ou pela velocidade).
- Não há caso de limite exato (parada de 14 s e de 15 s, diferença de 5,0% entre voltas): ficam para os testes
  unitários das funções (#162).
- Valores de referência (330 s/km, 22 e 20 km/h) são inventados; um atleta real pode ter outro limiar.
