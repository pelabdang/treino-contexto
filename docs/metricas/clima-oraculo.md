---
tipo: metrica
status: rascunho
dono: caio
atualizado: 2026-11-03
links: [[decisoes/0007-clima-da-atividade]], [[modulos/ingestao-garmin]], [[modulos/worker]], [[produto/roadmap]]
---
# Clima da atividade: fixtures e oráculo

## O que mede
O clima esperado de uma atividade ao ar livre (temperatura, sensação térmica, umidade e vento) na hora e no
local do treino, calculado a partir de uma resposta gravada do Open-Meteo. Esta nota descreve o **oráculo**: os
valores certos, feitos à mão, que os testes do leitor de posição (#112) e do cliente e comando do Open-Meteo (#113)
usam para conferir o código. Nenhum número vem de IA nem da rede. A regra é a da
[[decisoes/0007-clima-da-atividade]], item 4.

## Fórmula
Atividade com `inicio` e `duracao_s` (UTC). A janela é `[inicio, inicio + duracao_s]`. Cada hora cheia UTC que a
janela toca tem peso igual ao tempo de sobreposição dividido pela duração:

`valor = soma(peso_h * valor_h)`, com `peso_h = segundos_em_h / duracao_s` e `soma(peso_h) = 1`.

Vale para as quatro variáveis (`temperature_2m`, `apparent_temperature`, `relative_humidity_2m`,
`wind_speed_10m`, em °C, °C, % e km/h). O vento é a média das velocidades, não vetorial. Se **qualquer** hora da
janela tem `null` em **qualquer** variável, o estado é `pendente` e nenhum valor é devolvido (nunca `ok` com média
parcial). Indoor (esteira, piscina, virtual) e sem posição não consultam nada: estados `indoor` e `sem_posicao`.

## Dados de entrada
- Fixtures em `tests/fixtures/clima/` (todas inventadas, lugar "Parque do Exemplo", 12.3456, -45.6789, que o leitor
  guarda como 12.35, -45.68; nenhuma coordenada real; dia 2026-05-10):

| Arquivo | O que testa | Início (UTC), duração | Estado esperado |
|---|---|---|---|
| `fit/corrida_ar_livre.fit` | posição em `session.start_position_lat/long` | 09:20, 50 min | ok |
| `fit/corrida_posicao_na_lap.fit` | `session` sem posição; só a primeira `lap` tem (a segunda tem outra, que não vale) | 10:45, 30 min | ok |
| `fit/corrida_longa_4_horas.fit` | janela de 4 horas | 13:40, 2 h 30 | ok |
| `fit/esteira_com_posicao.fit` | esteira **com** coordenada no arquivo | 17:50, 40 min | indoor, sem posição gravada |
| `fit/corrida_posicao_zero.fit` | posição `(0, 0)` | 12:30, 60 min | sem_posicao |
| `fit/corrida_posicao_invalida.fit` | `0x7FFFFFFF` (inválido do FIT; o `fitdecode` devolve `None`) | 06:40, 40 min | sem_posicao |
| `exportacao_clima.json` | JSON mínimo com `startLatitude`/`startLongitude`: corrida (id 3000000101), esteira com coordenada (…102), ponto zero (…103), pedal virtual com coordenada (…104) e corrida sem coordenada (…105) | mesmos horários | ok, indoor, sem_posicao, indoor, sem_posicao |

  Nos FIT, a posição é guardada em semicírculos: `12.3456 * 2^31 / 180 = 147 288 745` e
  `-45.6789 * 2^31 / 180 = -544 970 504`. As fixtures antigas (`tests/fixtures/garmin/`) seguem sem posição, e um
  teste confere isso.
- **Resposta gravada** `open_meteo_archive_2026-05-10.json`: formato da Historical Weather API (`hourly.time` em
  `yyyy-mm-ddThh:mm` com `timezone=GMT`, as quatro variáveis, vento em km/h). **Foi montada à mão** a partir da
  documentação pública, sem chamar a rede (diz isso na chave `_aviso`, que a resposta real não tem). Os valores
  são inventados. `open_meteo_archive_2026-05-10_com_null.json` é a mesma com `null` na temperatura das 10h e na
  sensação das 11h.
- **Oráculo**: `tests/fixtures/clima/oraculo_clima.json`, escrito à mão (não é gerado). Cada caso traz arquivo,
  início, duração, janela com pesos, estado e valores, e o estado esperado com a resposta com `null`.

Valores da resposta usados nas contas (hora UTC: temperatura, sensação, umidade, vento):
09h 26,8 / 30,1 / 71 / 9,6; 10h 27,9 / 31,6 / 67 / 10,8; 11h 28,7 / 32,8 / 63 / 11,5;
13h 29,9 / 34,7 / 58 / 12,9; 14h 30,1 / 35,0 / 57 / 13,1; 15h 29,8 / 34,4 / 58 / 12,6; 16h 29,2 / 33,5 / 61 / 11,7.

## Contas à mão

**Corrida ao ar livre (FIT e JSON): 09:20 a 10:10, 3000 s.** Hora das 9h: 40 min = 2400 s, peso 4/5. Hora das 10h:
10 min = 600 s, peso 1/5.
- Temperatura: 0,8 x 26,8 + 0,2 x 27,9 = 21,44 + 5,58 = **27,02 °C**
- Sensação: 0,8 x 30,1 + 0,2 x 31,6 = 24,08 + 6,32 = **30,40 °C**
- Umidade: 0,8 x 71 + 0,2 x 67 = 56,8 + 13,4 = **70,2 %**
- Vento: 0,8 x 9,6 + 0,2 x 10,8 = 7,68 + 2,16 = **9,84 km/h**

**Posição na primeira lap: 10:45 a 11:15, 1800 s.** 10h: 15 min = 900 s, peso 1/2; 11h: 900 s, peso 1/2.
- Temperatura: (27,9 + 28,7) / 2 = **28,3 °C**
- Sensação: (31,6 + 32,8) / 2 = **32,2 °C**
- Umidade: (67 + 63) / 2 = **65 %**
- Vento: (10,8 + 11,5) / 2 = **11,15 km/h**

**Corrida longa: 13:40 a 16:10, 9000 s.** 13h: 20 min = 1200 s (2/15); 14h: 3600 s (6/15); 15h: 3600 s (6/15);
16h: 10 min = 600 s (1/15). Soma: 2 + 6 + 6 + 1 = 15, ou seja, peso total 1.
- Temperatura: (2 x 29,9 + 6 x 30,1 + 6 x 29,8 + 29,2) / 15 = (59,8 + 180,6 + 178,8 + 29,2) / 15 = 448,4 / 15 = **29,8933 °C**
- Sensação: (2 x 34,7 + 6 x 35,0 + 6 x 34,4 + 33,5) / 15 = (69,4 + 210 + 206,4 + 33,5) / 15 = 519,3 / 15 = **34,62 °C**
- Umidade: (2 x 58 + 6 x 57 + 6 x 58 + 61) / 15 = (116 + 342 + 348 + 61) / 15 = 867 / 15 = **57,8 %**
- Vento: (2 x 12,9 + 6 x 13,1 + 6 x 12,6 + 11,7) / 15 = (25,8 + 78,6 + 75,6 + 11,7) / 15 = 191,7 / 15 = **12,78 km/h**

**Com a resposta com `null`:** a corrida das 09:20 toca a hora das 10h (temperatura `null`) e a de 10:45 toca as de
10h e 11h (temperatura e sensação `null`): as duas ficam **`pendente`**. A corrida longa só toca 13h a 16h, sem
`null`: continua **ok** com os mesmos valores. Isso mostra que um `null` fora da janela não atrapalha.

**Sem clima:** esteira com coordenada, pedal virtual com coordenada: **indoor**, posição não gravada. Posição
`(0, 0)`, inválida ou ausente: **sem_posicao**. Nenhuma chamada ao Open-Meteo para elas.

## Referência
- ADR [[decisoes/0007-clima-da-atividade]] (posição de início, hora ponderada, estados).
- Documentação pública do Open-Meteo, Historical Weather API: <https://open-meteo.com/en/docs/historical-weather-api>
  (consultada em 03/11/2026). Dado CC BY 4.0: "Weather data by Open-Meteo.com". Peso por tempo de sobreposição: regra
  do produto (ADR 0007), não de artigo.

## Código e teste
- Gerador das fixtures: `tests/fixtures/clima/gerar_fixtures_clima.py` (`uv run python tests/fixtures/clima/gerar_fixtures_clima.py`).
  Determinístico; o teste falha se os arquivos versionados estiverem desatualizados. O oráculo não é gerado.
- Teste: `tests/test_fixtures_clima.py` (valor esperado calculado à mão: as contas acima). Confere a posição nas
  fixtures novas e a ausência nas antigas, o `(0,0)` e o inválido, o formato da resposta gravada, e que o oráculo
  bate com a resposta pela conta dos pesos feita de forma independente (frações exatas).
- Quem usa: testes da #112 (leitor lê `inicio_lat/lon` e o estado `indoor`/`sem_posicao`) e da #113 (cliente e
  comando: valores e `pendente`).

## Limitações e quando não usar
- A resposta é sintética: não prova que a API real devolve `apparent_temperature` preenchida nem o formato exato de
  todos os campos; a #113 confere isso com a resposta real.
- A conta cobre um único dia UTC (`start_date = end_date`). Atividade que cruza a meia-noite UTC pede duas datas ou
  um intervalo na chamada, e ainda não tem caso no oráculo.
- Duração zero ou ausente (usa a hora do início) não tem caso aqui.
