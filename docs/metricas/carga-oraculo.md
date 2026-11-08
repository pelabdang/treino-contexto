---
tipo: metrica
status: rascunho
dono: caio
atualizado: 2026-11-07
links: [[decisoes/0010-carga-de-treino]], [[metricas/esforcos-oraculo]], [[modulos/ingestao-garmin]], [[produto/roadmap]], [[glossario]]
---
# Carga de treino: fixtures de algumas semanas e oráculo

## O que mede
O resultado esperado da **carga** (rTSS e hrTSS por volta, carga da atividade, método e motivo de "sem carga") e da
**série diária** (CTL, ATL e TSB) para 23 atividades sintéticas de 03/03 a 16/04/2025, com o histórico de limiar da
fixture de saúde (#135). É o **oráculo** que a função de carga (#138), a série (#139), o comando (#141), a API (#142)
e o QA reaproveitam. Cada conta está escrita abaixo; nenhum número vem de IA nem de dado real. As regras são as da
[[decisoes/0010-carga-de-treino]] (`carga@1`/`carga@2` e `serie_carga@1`). Sempre estimativa, nunca medida.

## Fórmula
Forma do TSS, `TSS = horas x IF^2 x 100`: uma hora no limiar vale 100 (Coggan & Allen, *Training and Racing with a
Power Meter*; TrainingPeaks, "The Development of the Training Stress Score").

- **rTSS** da volta: `v = distância / duração` (m/s); `IF = v / velocidade_limiar`; `carga = duração / 3600 x IF^2 x 100`.
  Corrida fora da esteira, só com velocidade de limiar na data. Sem ajuste de subida.
- **hrTSS** da volta: `IF = FC_média / FC_limiar`; mesma carga. **Não é o hrTSS por zonas do TrainingPeaks**: é uma
  adaptação própria (ADR, item 4). Corrida, esteira e ciclismo.
- **Atividade** = soma das voltas (todas as voltas). Volta sem o dado do método conta 0. O método só vale com as
  voltas com dado cobrindo **>= 95%** da duração total. Sem FIT, uma volta única com os totais do JSON.
- **Método vencedor:** rTSS, se vale; senão hrTSS. Os dois valores que valem são gravados.
- **Motivo de sem carga** (ADR, item 7): natação e `outra` = `modalidade_sem_carga`; nenhum caminho com limiar na data =
  `sem_limiar_na_data` (ou `sem_dados_saude` se o atleta nunca importou limiar); senão o motivo do **primeiro caminho
  disponível, na ordem rTSS e depois hrTSS**: `sem_pace`/`sem_fc` se nenhuma volta tem o dado, `cobertura_insuficiente`
  se há dado mas abaixo de 95%.
- **Série** (ADR, item 6): `k_ctl = 1 - exp(-1/42) = 0,023528`, `k_atl = 1 - exp(-1/7) = 0,133122`;
  `CTL_d = CTL_(d-1) + (L_d - CTL_(d-1)) x k_ctl`, ATL igual com 7; `TSB_d = CTL_d - ATL_d` (mesmo dia). `L_d` é a soma
  das cargas calculadas do dia local; CTL = ATL = 0 antes do primeiro dia com carga; a série vai até o dia da última
  atividade importada. `aprendendo` = menos de 42 dias desde o primeiro dia.
  Base: Banister, Calvert, Savage e Bach, IEEE Trans. SMC-6(2):94-102, 1976; forma `1 - exp(-1/tau)` das planilhas do Golden Cheetah.
  Duas diferenças conhecidas do TrainingPeaks (ADR, item 6): o TSB aqui é do mesmo dia, e a constante é a forma exata.

**Apresentação.** A ADR não fixa as casas da apresentação (seus exemplos mostram 4 casas de cálculo). O oráculo guarda
**6 casas** (tolerância de teste 1e-6) e a nota mostra 4. Proposta para a #142: 1 casa na tela para carga, CTL, ATL e TSB;
nenhum valor deste oráculo cai em empate de arredondamento nessa casa.

## Dados de entrada
Fixtures geradas por `tests/fixtures/garmin/gerar_fixtures_carga.py` (determinístico; o teste falha se o zip versionado
estiver desatualizado), em `tests/fixtures/garmin/carga/`:
- `exportacao_carga.zip`: as atividades (JSON e FIT por volta) mais os arquivos de saúde de `gerar_fixtures_saude.py`;
- `exportacao_carga_sem_saude.zip`: as mesmas atividades, de um atleta sem nenhum dado de saúde.

Fuso -3 h em todas (a data local pode ser a do dia anterior ao UTC). Voltas numeradas a partir de 0.

**Limiar vigente** (histórico da fixture de saúde, uma linha por grandeza; a velocidade vem do arquivo como m/s dividido por 10):

| a partir de | FC de limiar (bpm) | velocidade de limiar (m/s) | pace de limiar (s/km) |
|---|---|---|---|
| (antes de 05/03) | sem limiar | sem limiar | |
| 05/03 | 158 | 3,70 | 270,27 |
| 08/03 | 159 | 3,70 (o registro é só de FC) | 270,27 |
| 10/03 | 163 | 3,85 | 259,74 |

**Atividades** (dia local):

| id | dia local | atividade | resultado esperado |
|---|---|---|---|
| 4000000001 | 03/03 | corrida, 5 voltas | `sem_limiar_na_data` |
| 4000000002 | 04/03 (05/03 01h UTC) | corrida às 22h locais | `sem_limiar_na_data` (vale o dia local) |
| 4000000003 | 05/03 | corrida com voltas, dia em que o limiar começa | calculada, rTSS (hrTSS também) |
| 4000000004 | 06/03 | natação em piscina | `modalidade_sem_carga` |
| 4000000005 | 07/03 | ciclismo, sem potência | calculada, hrTSS |
| 4000000006 | 08/03 | corrida sem FC | calculada, rTSS |
| 4000000007 | 08/03 | esteira sem FC | `sem_fc` |
| (09/03) | 09/03 | dia sem treino | |
| 4000000008 | 10/03 | corrida, dia em que o limiar muda | calculada, rTSS (limiar novo) |
| 4000000009 | 11/03 (12/03 02h UTC) | ciclismo às 23h locais | calculada, hrTSS |
| 4000000010 | 12/03 | esteira, 10 voltas, uma sem FC | `cobertura_insuficiente` (90%) |
| 4000000011 | 13/03 | esteira, 20 voltas, uma sem FC | calculada, hrTSS (cobertura 95%) |
| 4000000012 | 14/03 | corrida sem distância e sem FC | `sem_pace` |
| 4000000013 a 4000000018 | 15/03 | triatlo: pai (`multiesporte_pai`), natação em águas abertas, troca, ciclismo, troca, corrida | pai e trocas **ignoradas**; natação `modalidade_sem_carga`; ciclismo hrTSS; corrida rTSS |
| 4000000019 | 16/03 | corrida com FC e sem distância | calculada, hrTSS |
| 4000000023 | 20/03 | corrida só no JSON (sem FIT) | calculada, rTSS, granularidade `atividade` |
| 4000000020 | 05/04 | corrida, 4 voltas | calculada, rTSS |
| 4000000021 | 15/04 | corrida, 3 voltas (dia 41 da série) | calculada, rTSS |
| 4000000022 | 16/04 | corrida, 4 voltas (dia 42) | calculada, rTSS |

Oráculo no código: constantes `ESPERADO`, `SEM_SAUDE`, `CARGA_DIA`, `SERIE` e `TOTAIS` em
`services/api/tests/metricas/test_carga_oraculo.py`.

## Contas à mão

### Carga de cada atividade
Cada tabela mostra, por volta, `v`, `IF` e a carga com 4 casas; a soma é feita com os valores sem arredondar (a soma dos
valores de 4 casas pode diferir em 1 no último dígito). Conferência de uma volta: 4000000003, volta 1: 1000 m em 255 s,
v = 1000 / 255 = 3,9216 m/s; IF = 3,9216 / 3,70 = 1,0599; carga = 255 / 3600 x 1,0599^2 x 100 = 0,070833 x 112,34 = 7,9571.
Sanidade: 1 h a 3,70 m/s daria IF = 1 e carga 100.

Quando um método não vale, a tabela dele mostra por quê.

#### 4000000001 (03/03): Corrida 5 km
- `sem_carga`, motivo **sem_limiar_na_data**.

#### 4000000002 (04/03): Corrida noturna 4 km
- `sem_carga`, motivo **sem_limiar_na_data**.

#### 4000000003 (05/03): Intervalado 2 x 1 km
- rTSS, limiar 3,70 m/s (pace de limiar 270,27 s/km). Cobertura: voltas com distância e duração = 100,0%.

  | volta | distância (m) | duração (s) | v (m/s) | IF = v / limiar | carga = dur/3600 x IF² x 100 |
  |---|---|---|---|---|---|
  | 0 | 2000 | 720 | 2,7778 | 0,7508 | 11,2725 |
  | 1 | 1000 | 255 | 3,9216 | 1,0599 | 7,9571 |
  | 2 | 400 | 150 | 2,6667 | 0,7207 | 2,1643 |
  | 3 | 1000 | 252 | 3,9683 | 1,0725 | 8,0518 |
  | 4 | 400 | 150 | 2,6667 | 0,7207 | 2,1643 |
  | 5 | 1000 | 360 | 2,7778 | 0,7508 | 5,6363 |

  Soma: **37,2463**
- hrTSS, limiar 158 bpm. Cobertura: voltas com FC = 100,0%.

  | volta | FC (bpm) | duração (s) | IF = FC / limiar | carga = dur/3600 x IF² x 100 |
  |---|---|---|---|---|
  | 0 | 130 | 720 | 0,8228 | 13,5395 |
  | 1 | 165 | 255 | 1,0443 | 7,7249 |
  | 2 | 150 | 150 | 0,9494 | 3,7554 |
  | 3 | 168 | 252 | 1,0633 | 7,9141 |
  | 4 | 152 | 150 | 0,9620 | 3,8562 |
  | 5 | 140 | 360 | 0,8861 | 7,8513 |

  Soma: **44,6414**
- Resultado: `calculada`, método **rtss**, carga **37,2463**, carga_rtss 37,2463, carga_hrtss 44,6414, cobertura 100,0%, granularidade volta.

#### 4000000004 (06/03): Natacao 400 m
- `sem_carga`, motivo **modalidade_sem_carga**.

#### 4000000005 (07/03): Pedal 35 km
- hrTSS, limiar 158 bpm. Cobertura: voltas com FC = 100,0%.

  | volta | FC (bpm) | duração (s) | IF = FC / limiar | carga = dur/3600 x IF² x 100 |
  |---|---|---|---|---|
  | 0 | 120 | 1500 | 0,7595 | 24,0346 |
  | 1 | 150 | 2400 | 0,9494 | 60,0865 |
  | 2 | 125 | 900 | 0,7911 | 15,6475 |

  Soma: **99,7687**
- Resultado: `calculada`, método **hrtss**, carga **99,7687**, carga_hrtss 99,7687, cobertura 100,0%, granularidade volta.

#### 4000000006 (08/03): Corrida sem FC
- rTSS, limiar 3,70 m/s (pace de limiar 270,27 s/km). Cobertura: voltas com distância e duração = 100,0%.

  | volta | distância (m) | duração (s) | v (m/s) | IF = v / limiar | carga = dur/3600 x IF² x 100 |
  |---|---|---|---|---|---|
  | 0 | 1000 | 300 | 3,3333 | 0,9009 | 6,7635 |
  | 1 | 1000 | 298 | 3,3557 | 0,9069 | 6,8089 |
  | 2 | 1000 | 296 | 3,3784 | 0,9131 | 6,8549 |
  | 3 | 1000 | 294 | 3,4014 | 0,9193 | 6,9016 |
  | 4 | 1000 | 292 | 3,4247 | 0,9256 | 6,9488 |
  | 5 | 1000 | 290 | 3,4483 | 0,9320 | 6,9967 |

  Soma: **41,2745**
- hrTSS, limiar 159 bpm. Cobertura: voltas com FC = 0,0%.
  - nenhuma volta com dado: o método não vale.
- Resultado: `calculada`, método **rtss**, carga **41,2745**, carga_rtss 41,2745, cobertura 100,0%, granularidade volta.

#### 4000000007 (08/03): Esteira sem FC
- hrTSS, limiar 159 bpm. Cobertura: voltas com FC = 0,0%.
  - nenhuma volta com dado: o método não vale.
- Resultado: `sem_carga`, motivo **sem_fc**.

#### 4000000008 (10/03): Intervalado 3 x 1 km
- rTSS, limiar 3,85 m/s (pace de limiar 259,74 s/km). Cobertura: voltas com distância e duração = 100,0%.

  | volta | distância (m) | duração (s) | v (m/s) | IF = v / limiar | carga = dur/3600 x IF² x 100 |
  |---|---|---|---|---|---|
  | 0 | 1500 | 540 | 2,7778 | 0,7215 | 7,8084 |
  | 1 | 1000 | 240 | 4,1667 | 1,0823 | 7,8084 |
  | 2 | 400 | 160 | 2,5000 | 0,6494 | 1,8740 |
  | 3 | 1000 | 238 | 4,2017 | 1,0913 | 7,8741 |
  | 4 | 400 | 160 | 2,5000 | 0,6494 | 1,8740 |
  | 5 | 1000 | 236 | 4,2373 | 1,1006 | 7,9408 |
  | 6 | 1000 | 380 | 2,6316 | 0,6835 | 4,9317 |

  Soma: **40,1115**
- hrTSS, limiar 163 bpm. Cobertura: voltas com FC = 100,0%.

  | volta | FC (bpm) | duração (s) | IF = FC / limiar | carga = dur/3600 x IF² x 100 |
  |---|---|---|---|---|
  | 0 | 135 | 540 | 0,8282 | 10,2892 |
  | 1 | 170 | 240 | 1,0429 | 7,2516 |
  | 2 | 150 | 160 | 0,9202 | 3,7638 |
  | 3 | 172 | 238 | 1,0552 | 7,3613 |
  | 4 | 152 | 160 | 0,9325 | 3,8648 |
  | 5 | 174 | 236 | 1,0675 | 7,4702 |
  | 6 | 138 | 380 | 0,8466 | 7,5660 |

  Soma: **47,5669**
- Resultado: `calculada`, método **rtss**, carga **40,1115**, carga_rtss 40,1115, carga_hrtss 47,5669, cobertura 100,0%, granularidade volta.

#### 4000000009 (11/03): Pedal noturno
- hrTSS, limiar 163 bpm. Cobertura: voltas com FC = 100,0%.

  | volta | FC (bpm) | duração (s) | IF = FC / limiar | carga = dur/3600 x IF² x 100 |
  |---|---|---|---|---|
  | 0 | 125 | 1200 | 0,7669 | 19,6030 |
  | 1 | 148 | 1800 | 0,9080 | 41,2210 |
  | 2 | 120 | 600 | 0,7362 | 9,0331 |

  Soma: **69,8571**
- Resultado: `calculada`, método **hrtss**, carga **69,8571**, carga_hrtss 69,8571, cobertura 100,0%, granularidade volta.

#### 4000000010 (12/03): Esteira 10 voltas
- hrTSS, limiar 163 bpm. Cobertura: voltas com FC = 90,0%.

  | volta | FC (bpm) | duração (s) | IF = FC / limiar | carga = dur/3600 x IF² x 100 |
  |---|---|---|---|---|
  | 0 | 150 | 100 | 0,9202 | 2,3524 |
  | 1 | 151 | 100 | 0,9264 | 2,3838 |
  | 2 | 152 | 100 | 0,9325 | 2,4155 |
  | 3 | 153 | 100 | 0,9387 | 2,4474 |
  | 4 | sem dado | 100 | - | - | 0 |
  | 5 | 155 | 100 | 0,9509 | 2,5118 |
  | 6 | 156 | 100 | 0,9571 | 2,5443 |
  | 7 | 157 | 100 | 0,9632 | 2,5770 |
  | 8 | 158 | 100 | 0,9693 | 2,6100 |
  | 9 | 159 | 100 | 0,9755 | 2,6431 |

  Soma: **22,4854** (cobertura abaixo de 95%: não vale)
- Resultado: `sem_carga`, motivo **cobertura_insuficiente**.

#### 4000000011 (13/03): Esteira 20 voltas
- hrTSS, limiar 163 bpm. Cobertura: voltas com FC = 95,0%.

  | volta | FC (bpm) | duração (s) | IF = FC / limiar | carga = dur/3600 x IF² x 100 |
  |---|---|---|---|---|
  | 0 | 150 | 50 | 0,9202 | 1,1762 |
  | 1 | 151 | 50 | 0,9264 | 1,1919 |
  | 2 | 152 | 50 | 0,9325 | 1,2078 |
  | 3 | 153 | 50 | 0,9387 | 1,2237 |
  | 4 | 154 | 50 | 0,9448 | 1,2397 |
  | 5 | 150 | 50 | 0,9202 | 1,1762 |
  | 6 | 151 | 50 | 0,9264 | 1,1919 |
  | 7 | sem dado | 50 | - | - | 0 |
  | 8 | 153 | 50 | 0,9387 | 1,2237 |
  | 9 | 154 | 50 | 0,9448 | 1,2397 |
  | 10 | 150 | 50 | 0,9202 | 1,1762 |
  | 11 | 151 | 50 | 0,9264 | 1,1919 |
  | 12 | 152 | 50 | 0,9325 | 1,2078 |
  | 13 | 153 | 50 | 0,9387 | 1,2237 |
  | 14 | 154 | 50 | 0,9448 | 1,2397 |
  | 15 | 150 | 50 | 0,9202 | 1,1762 |
  | 16 | 151 | 50 | 0,9264 | 1,1919 |
  | 17 | 152 | 50 | 0,9325 | 1,2078 |
  | 18 | 153 | 50 | 0,9387 | 1,2237 |
  | 19 | 154 | 50 | 0,9448 | 1,2397 |

  Soma: **22,9495**
- Resultado: `calculada`, método **hrtss**, carga **22,9495**, carga_hrtss 22,9495, cobertura 95,0%, granularidade volta.

#### 4000000012 (14/03): Corrida sem GPS e sem FC
- rTSS, limiar 3,85 m/s (pace de limiar 259,74 s/km). Cobertura: voltas com distância e duração = 0,0%.
  - nenhuma volta com dado: o método não vale.
- hrTSS, limiar 163 bpm. Cobertura: voltas com FC = 0,0%.
  - nenhuma volta com dado: o método não vale.
- Resultado: `sem_carga`, motivo **sem_pace**.

#### 4000000014 (15/03): Triatlo: natacao
- `sem_carga`, motivo **modalidade_sem_carga**.

#### 4000000016 (15/03): Triatlo: ciclismo
- hrTSS, limiar 163 bpm. Cobertura: voltas com FC = 100,0%.

  | volta | FC (bpm) | duração (s) | IF = FC / limiar | carga = dur/3600 x IF² x 100 |
  |---|---|---|---|---|
  | 0 | 125 | 900 | 0,7669 | 14,7023 |
  | 1 | 150 | 1500 | 0,9202 | 35,2855 |

  Soma: **49,9878**
- Resultado: `calculada`, método **hrtss**, carga **49,9878**, carga_hrtss 49,9878, cobertura 100,0%, granularidade volta.

#### 4000000018 (15/03): Triatlo: corrida
- rTSS, limiar 3,85 m/s (pace de limiar 259,74 s/km). Cobertura: voltas com distância e duração = 100,0%.

  | volta | distância (m) | duração (s) | v (m/s) | IF = v / limiar | carga = dur/3600 x IF² x 100 |
  |---|---|---|---|---|---|
  | 0 | 1000 | 250 | 4,0000 | 1,0390 | 7,4961 |
  | 1 | 1000 | 248 | 4,0323 | 1,0473 | 7,5566 |
  | 2 | 1000 | 246 | 4,0650 | 1,0559 | 7,6180 |

  Soma: **22,6707**
- hrTSS, limiar 163 bpm. Cobertura: voltas com FC = 100,0%.

  | volta | FC (bpm) | duração (s) | IF = FC / limiar | carga = dur/3600 x IF² x 100 |
  |---|---|---|---|---|
  | 0 | 168 | 250 | 1,0307 | 7,3770 |
  | 1 | 170 | 248 | 1,0429 | 7,4933 |
  | 2 | 172 | 246 | 1,0552 | 7,6088 |

  Soma: **22,4791**
- Resultado: `calculada`, método **rtss**, carga **22,6707**, carga_rtss 22,6707, carga_hrtss 22,4791, cobertura 100,0%, granularidade volta.

#### 4000000019 (16/03): Corrida com FC sem distancia
- rTSS, limiar 3,85 m/s (pace de limiar 259,74 s/km). Cobertura: voltas com distância e duração = 0,0%.
  - nenhuma volta com dado: o método não vale.
- hrTSS, limiar 163 bpm. Cobertura: voltas com FC = 100,0%.

  | volta | FC (bpm) | duração (s) | IF = FC / limiar | carga = dur/3600 x IF² x 100 |
  |---|---|---|---|---|
  | 0 | 140 | 600 | 0,8589 | 12,2950 |
  | 1 | 145 | 600 | 0,8896 | 13,1889 |
  | 2 | 150 | 600 | 0,9202 | 14,1142 |
  | 3 | 155 | 600 | 0,9509 | 15,0708 |

  Soma: **54,6690**
- Resultado: `calculada`, método **hrtss**, carga **54,6690**, carga_hrtss 54,6690, cobertura 100,0%, granularidade volta.

#### 4000000023 (20/03): Corrida so JSON 5 km
- rTSS, limiar 3,85 m/s (pace de limiar 259,74 s/km). Cobertura: voltas com distância e duração = 100,0%.

  | volta | distância (m) | duração (s) | v (m/s) | IF = v / limiar | carga = dur/3600 x IF² x 100 |
  |---|---|---|---|---|---|
  | 0 | 5000 | 1500 | 3,3333 | 0,8658 | 31,2338 |

  Soma: **31,2338**
- hrTSS, limiar 163 bpm. Cobertura: voltas com FC = 100,0%.

  | volta | FC (bpm) | duração (s) | IF = FC / limiar | carga = dur/3600 x IF² x 100 |
  |---|---|---|---|---|
  | 0 | 150 | 1500 | 0,9202 | 35,2855 |

  Soma: **35,2855**
- Resultado: `calculada`, método **rtss**, carga **31,2338**, carga_rtss 31,2338, carga_hrtss 35,2855, cobertura 100,0%, granularidade atividade.

#### 4000000020 (05/04): Rodagem 4 km
- rTSS, limiar 3,85 m/s (pace de limiar 259,74 s/km). Cobertura: voltas com distância e duração = 100,0%.

  | volta | distância (m) | duração (s) | v (m/s) | IF = v / limiar | carga = dur/3600 x IF² x 100 |
  |---|---|---|---|---|---|
  | 0 | 1000 | 360 | 2,7778 | 0,7215 | 5,2056 |
  | 1 | 1000 | 358 | 2,7933 | 0,7255 | 5,2347 |
  | 2 | 1000 | 356 | 2,8090 | 0,7296 | 5,2641 |
  | 3 | 1000 | 354 | 2,8249 | 0,7337 | 5,2939 |

  Soma: **20,9983**
- hrTSS, limiar 163 bpm. Cobertura: voltas com FC = 100,0%.

  | volta | FC (bpm) | duração (s) | IF = FC / limiar | carga = dur/3600 x IF² x 100 |
  |---|---|---|---|---|
  | 0 | 140 | 360 | 0,8589 | 7,3770 |
  | 1 | 141 | 358 | 0,8650 | 7,4412 |
  | 2 | 142 | 356 | 0,8712 | 7,5050 |
  | 3 | 143 | 354 | 0,8773 | 7,5683 |

  Soma: **29,8915**
- Resultado: `calculada`, método **rtss**, carga **20,9983**, carga_rtss 20,9983, carga_hrtss 29,8915, cobertura 100,0%, granularidade volta.

#### 4000000021 (15/04): Rodagem 3 km
- rTSS, limiar 3,85 m/s (pace de limiar 259,74 s/km). Cobertura: voltas com distância e duração = 100,0%.

  | volta | distância (m) | duração (s) | v (m/s) | IF = v / limiar | carga = dur/3600 x IF² x 100 |
  |---|---|---|---|---|---|
  | 0 | 1000 | 350 | 2,8571 | 0,7421 | 5,3544 |
  | 1 | 1000 | 348 | 2,8736 | 0,7464 | 5,3851 |
  | 2 | 1000 | 346 | 2,8902 | 0,7507 | 5,4163 |

  Soma: **16,1558**
- hrTSS, limiar 163 bpm. Cobertura: voltas com FC = 100,0%.

  | volta | FC (bpm) | duração (s) | IF = FC / limiar | carga = dur/3600 x IF² x 100 |
  |---|---|---|---|---|
  | 0 | 142 | 350 | 0,8712 | 7,3785 |
  | 1 | 143 | 348 | 0,8773 | 7,4400 |
  | 2 | 144 | 346 | 0,8834 | 7,5011 |

  Soma: **22,3196**
- Resultado: `calculada`, método **rtss**, carga **16,1558**, carga_rtss 16,1558, carga_hrtss 22,3196, cobertura 100,0%, granularidade volta.

#### 4000000022 (16/04): Rodagem 4 km
- rTSS, limiar 3,85 m/s (pace de limiar 259,74 s/km). Cobertura: voltas com distância e duração = 100,0%.

  | volta | distância (m) | duração (s) | v (m/s) | IF = v / limiar | carga = dur/3600 x IF² x 100 |
  |---|---|---|---|---|---|
  | 0 | 1000 | 345 | 2,8986 | 0,7529 | 5,4320 |
  | 1 | 1000 | 343 | 2,9155 | 0,7573 | 5,4636 |
  | 2 | 1000 | 341 | 2,9326 | 0,7617 | 5,4957 |
  | 3 | 1000 | 339 | 2,9499 | 0,7662 | 5,5281 |

  Soma: **21,9194**
- hrTSS, limiar 163 bpm. Cobertura: voltas com FC = 100,0%.

  | volta | FC (bpm) | duração (s) | IF = FC / limiar | carga = dur/3600 x IF² x 100 |
  |---|---|---|---|---|
  | 0 | 144 | 345 | 0,8834 | 7,4794 |
  | 1 | 145 | 343 | 0,8896 | 7,5397 |
  | 2 | 146 | 341 | 0,8957 | 7,5995 |
  | 3 | 147 | 339 | 0,9018 | 7,6587 |

  Soma: **30,2772**
- Resultado: `calculada`, método **rtss**, carga **21,9194**, carga_rtss 21,9194, carga_hrtss 30,2772, cobertura 100,0%, granularidade volta.


### Atividades ignoradas e atleta sem saúde
- 4000000013 (pai), 4000000015 e 4000000017 (trocas): subtipo `multiesporte_pai` e `troca` (reconhecidos pelo tipo do JSON,
  `multi_sport` e `transition`). **Sem linha de carga** e fora de "sem carga": entram só em `ignoradas_multiesporte` = **3**.
- Natação do triatlo (4000000014, águas abertas) e a de 06/03 (4000000004, piscina): `modalidade_sem_carga` (a regra vem
  antes do limiar, ADR item 7, passo 2).
- **Atleta sem dados de saúde** (`exportacao_carga_sem_saude.zip`): as 20 atividades elegíveis ficam sem carga; as 18 que
  não são natação com `sem_dados_saude` e as 2 natações com `modalidade_sem_carga`. Nenhuma calculada: **série vazia**.

### Totais (atleta com saúde)
23 atividades importadas = 13 calculadas + 7 sem carga + 3 ignoradas. As 7 sem carga: `sem_limiar_na_data` 2
(4000000001 e 4000000002), `sem_fc` 1 (4000000007), `sem_pace` 1 (4000000012), `cobertura_insuficiente` 1 (4000000010),
`modalidade_sem_carga` 2 (4000000004 e 4000000014); `sem_dados_saude` 0 (só o outro atleta). Os 6 motivos aparecem.
O total de sem carga é do atleta inteiro, inclusive as de antes do primeiro dia da série.

**Decisão do oráculo para o 4000000012 (`sem_pace`):** sem distância e sem FC, os dois caminhos estão disponíveis (limiar
de velocidade e de FC) e nenhum vale. O motivo é o do primeiro caminho na ordem da ADR (rTSS, depois hrTSS): `sem_pace`.

### Carga por dia local
Soma das cargas calculadas do dia. 15/03 = 49,9878 (ciclismo hrTSS) + 22,6707 (corrida rTSS) = **72,6585**
(a natação não soma). 08/03 = 41,2745: só a corrida sem FC (a esteira ficou sem carga e marca o dia como incompleto).
12/03 e 14/03 têm carga 0 e uma atividade sem carga, diferentes de 09/03 (sem atividade).

### Série CTL / ATL / TSB
Primeiro dia: **05/03** (a primeira atividade calculada; as de 03/03 e 04/03 são anteriores ao limiar e ficam fora da
série). Último dia: **16/04** (a última atividade importada). 43 dias. A conta à mão dos dias escolhidos usa a **forma
fechada** da recursão:

`CTL_d = k_ctl x soma_j L_j x exp(-(d - j)/42)` e `ATL_d = k_atl x soma_j L_j x exp(-(d - j)/7)`,

somando sobre os dias `j <= d` com carga. (A recursão é `X_d = X_(d-1) x (1 - k) + k x L_d` e `1 - k = exp(-1/tau)`, então
cada carga contribui `k x L_j x exp(-(d - j)/tau)`.) O teste confere a forma fechada contra a recursão nos mesmos dias.

##### 05/03 (dia 0 da série)

| dia da carga | atraso Δ (dias) | carga L | e^(-Δ/42) | e^(-Δ/7) |
|---|---|---|---|---|
| 05/03 | 0 | 37,2463 | 1,000000 | 1,000000 |

CTL = 0,023528 x 37,2463 = **0,8763**; ATL = 0,133122 x 37,2463 = **4,9583**; TSB = 0,8763 - 4,9583 = **-4,0820**.

##### 08/03 (dia 3 da série)

| dia da carga | atraso Δ (dias) | carga L | e^(-Δ/42) | e^(-Δ/7) |
|---|---|---|---|---|
| 05/03 | 3 | 37,2463 | 0,931063 | 0,651439 |
| 07/03 | 1 | 99,7687 | 0,976472 | 0,866878 |
| 08/03 | 0 | 41,2745 | 1,000000 | 1,000000 |

CTL = 0,023528 x 173,3744 = **4,0792**; ATL = 0,133122 x 152,0254 = **20,2379**; TSB = 4,0792 - 20,2379 = **-16,1587**.

##### 09/03 (dia 4 da série)

| dia da carga | atraso Δ (dias) | carga L | e^(-Δ/42) | e^(-Δ/7) |
|---|---|---|---|---|
| 05/03 | 4 | 37,2463 | 0,909156 | 0,564718 |
| 07/03 | 2 | 99,7687 | 0,953497 | 0,751477 |
| 08/03 | 1 | 41,2745 | 0,976472 | 0,866878 |

CTL = 0,023528 x 169,2952 = **3,9832**; ATL = 0,133122 x 131,7875 = **17,5438**; TSB = 3,9832 - 17,5438 = **-13,5606**.

##### 15/03 (dia 10 da série)

| dia da carga | atraso Δ (dias) | carga L | e^(-Δ/42) | e^(-Δ/7) |
|---|---|---|---|---|
| 05/03 | 10 | 37,2463 | 0,788128 | 0,239651 |
| 07/03 | 8 | 99,7687 | 0,826565 | 0,318907 |
| 08/03 | 7 | 41,2745 | 0,846482 | 0,367879 |
| 10/03 | 5 | 40,1115 | 0,887766 | 0,489542 |
| 11/03 | 4 | 69,8571 | 0,909156 | 0,564718 |
| 13/03 | 2 | 22,9495 | 0,953497 | 0,751477 |
| 15/03 | 0 | 72,6584 | 1,000000 | 1,000000 |

CTL = 0,023528 x 340,4196 = **8,0095**; ATL = 0,133122 x 204,9173 = **27,2790**; TSB = 8,0095 - 27,2790 = **-19,2695**.

##### 05/04 (dia 31 da série)

| dia da carga | atraso Δ (dias) | carga L | e^(-Δ/42) | e^(-Δ/7) |
|---|---|---|---|---|
| 05/03 | 31 | 37,2463 | 0,478024 | 0,011932 |
| 07/03 | 29 | 99,7687 | 0,501337 | 0,015877 |
| 08/03 | 28 | 41,2745 | 0,513417 | 0,018316 |
| 10/03 | 26 | 40,1115 | 0,538457 | 0,024373 |
| 11/03 | 25 | 69,8571 | 0,551431 | 0,028116 |
| 13/03 | 23 | 22,9495 | 0,578325 | 0,037414 |
| 15/03 | 21 | 72,6584 | 0,606531 | 0,049787 |
| 16/03 | 20 | 54,6690 | 0,621145 | 0,057433 |
| 20/03 | 16 | 31,2338 | 0,683210 | 0,101701 |
| 05/04 | 0 | 20,9983 | 1,000000 | 1,000000 |

CTL = 0,023528 x 282,7699 = **6,6531**; ATL = 0,133122 x 37,5169 = **4,9943**; TSB = 6,6531 - 4,9943 = **1,6588**.

##### 15/04 (dia 41 da série)

| dia da carga | atraso Δ (dias) | carga L | e^(-Δ/42) | e^(-Δ/7) |
|---|---|---|---|---|
| 05/03 | 41 | 37,2463 | 0,376744 | 0,002859 |
| 07/03 | 39 | 99,7687 | 0,395118 | 0,003805 |
| 08/03 | 38 | 41,2745 | 0,404638 | 0,004389 |
| 10/03 | 36 | 40,1115 | 0,424373 | 0,005841 |
| 11/03 | 35 | 69,8571 | 0,434598 | 0,006738 |
| 13/03 | 33 | 22,9495 | 0,455794 | 0,008966 |
| 15/03 | 31 | 72,6584 | 0,478024 | 0,011932 |
| 16/03 | 30 | 54,6690 | 0,489542 | 0,013764 |
| 20/03 | 26 | 31,2338 | 0,538457 | 0,024373 |
| 05/04 | 10 | 20,9983 | 0,788128 | 0,239651 |
| 15/04 | 0 | 16,1558 | 1,000000 | 1,000000 |

CTL = 0,023528 x 239,0145 = **5,6236**; ATL = 0,133122 x 25,1467 = **3,3476**; TSB = 5,6236 - 3,3476 = **2,2760**.

##### 16/04 (dia 42 da série)

| dia da carga | atraso Δ (dias) | carga L | e^(-Δ/42) | e^(-Δ/7) |
|---|---|---|---|---|
| 05/03 | 42 | 37,2463 | 0,367879 | 0,002479 |
| 07/03 | 40 | 99,7687 | 0,385821 | 0,003299 |
| 08/03 | 39 | 41,2745 | 0,395118 | 0,003805 |
| 10/03 | 37 | 40,1115 | 0,414388 | 0,005063 |
| 11/03 | 36 | 69,8571 | 0,424373 | 0,005841 |
| 13/03 | 34 | 22,9495 | 0,445070 | 0,007773 |
| 15/03 | 32 | 72,6584 | 0,466776 | 0,010343 |
| 16/03 | 31 | 54,6690 | 0,478024 | 0,011932 |
| 20/03 | 27 | 31,2338 | 0,525788 | 0,021128 |
| 05/04 | 11 | 20,9983 | 0,769584 | 0,207748 |
| 15/04 | 1 | 16,1558 | 0,976472 | 0,866878 |
| 16/04 | 0 | 21,9194 | 1,000000 | 1,000000 |

CTL = 0,023528 x 255,3103 = **6,0070**; ATL = 0,133122 x 43,7185 = **5,8199**; TSB = 6,0070 - 5,8199 = **0,1871**.


### Série diária completa
A coluna `n` é o número de dias desde 05/03; `aprendendo` é verdadeiro até `n = 41` (15/04) e falso a partir de `n = 42` (16/04).
A tabela é a recursão inteira, 4 casas; os valores com 6 casas dos dias escolhidos estão em `SERIE`.

| dia | n | carga do dia | CTL | ATL | TSB |
|---|---|---|---|---|---|
| 05/03 | 0 | 37,2463 | 0,8763 | 4,9583 | -4,0820 |
| 06/03 | 1 | 0,0000 | 0,8557 | 4,2983 | -3,4425 |
| 07/03 | 2 | 99,7687 | 3,1830 | 17,0075 | -13,8245 |
| 08/03 | 3 | 41,2745 | 4,0792 | 20,2379 | -16,1587 |
| 09/03 | 4 | 0,0000 | 3,9832 | 17,5438 | -13,5606 |
| 10/03 | 5 | 40,1115 | 4,8333 | 20,5481 | -15,7148 |
| 11/03 | 6 | 69,8571 | 6,3632 | 27,1122 | -20,7490 |
| 12/03 | 7 | 0,0000 | 6,2135 | 23,5030 | -17,2895 |
| 13/03 | 8 | 22,9495 | 6,6072 | 23,4293 | -16,8221 |
| 14/03 | 9 | 0,0000 | 6,4518 | 20,3103 | -13,8586 |
| 15/03 | 10 | 72,6584 | 8,0095 | 27,2790 | -19,2695 |
| 16/03 | 11 | 54,6690 | 9,1073 | 30,9252 | -21,8179 |
| 17/03 | 12 | 0,0000 | 8,8930 | 26,8084 | -17,9154 |
| 18/03 | 13 | 0,0000 | 8,6838 | 23,2396 | -14,5558 |
| 19/03 | 14 | 0,0000 | 8,4795 | 20,1459 | -11,6664 |
| 20/03 | 15 | 31,2338 | 9,0149 | 21,6219 | -12,6071 |
| 21/03 | 16 | 0,0000 | 8,8028 | 18,7436 | -9,9408 |
| 22/03 | 17 | 0,0000 | 8,5956 | 16,2484 | -7,6528 |
| 23/03 | 18 | 0,0000 | 8,3934 | 14,0854 | -5,6920 |
| 24/03 | 19 | 0,0000 | 8,1959 | 12,2103 | -4,0144 |
| 25/03 | 20 | 0,0000 | 8,0031 | 10,5848 | -2,5818 |
| 26/03 | 21 | 0,0000 | 7,8148 | 9,1758 | -1,3610 |
| 27/03 | 22 | 0,0000 | 7,6309 | 7,9543 | -0,3234 |
| 28/03 | 23 | 0,0000 | 7,4514 | 6,8954 | 0,5560 |
| 29/03 | 24 | 0,0000 | 7,2760 | 5,9775 | 1,2986 |
| 30/03 | 25 | 0,0000 | 7,1049 | 5,1817 | 1,9231 |
| 31/03 | 26 | 0,0000 | 6,9377 | 4,4919 | 2,4458 |
| 01/04 | 27 | 0,0000 | 6,7745 | 3,8939 | 2,8805 |
| 02/04 | 28 | 0,0000 | 6,6151 | 3,3756 | 3,2395 |
| 03/04 | 29 | 0,0000 | 6,4594 | 2,9262 | 3,5332 |
| 04/04 | 30 | 0,0000 | 6,3074 | 2,5367 | 3,7708 |
| 05/04 | 31 | 20,9983 | 6,6531 | 4,9943 | 1,6588 |
| 06/04 | 32 | 0,0000 | 6,4966 | 4,3295 | 2,1671 |
| 07/04 | 33 | 0,0000 | 6,3437 | 3,7531 | 2,5906 |
| 08/04 | 34 | 0,0000 | 6,1945 | 3,2535 | 2,9410 |
| 09/04 | 35 | 0,0000 | 6,0487 | 2,8204 | 3,2283 |
| 10/04 | 36 | 0,0000 | 5,9064 | 2,4449 | 3,4615 |
| 11/04 | 37 | 0,0000 | 5,7674 | 2,1195 | 3,6480 |
| 12/04 | 38 | 0,0000 | 5,6317 | 1,8373 | 3,7944 |
| 13/04 | 39 | 0,0000 | 5,4992 | 1,5927 | 3,9065 |
| 14/04 | 40 | 0,0000 | 5,3698 | 1,3807 | 3,9891 |
| 15/04 | 41 | 16,1558 | 5,6236 | 3,3476 | 2,2760 |
| 16/04 | 42 | 21,9194 | 6,0070 | 5,8199 | 0,1871 |

### Contagens por dia (dia incompleto)
`atividades` conta as elegíveis do dia (sem as ignoradas); `calculadas` e `sem_carga` a separam. Em (atividades, calculadas,
sem_carga): 05/03 (1, 1, 0); 06/03 (1, 0, 1: só natação, carga 0); 08/03 (2, 1, 1); 09/03 (0, 0, 0); 12/03 (1, 0, 1);
14/03 (1, 0, 1); 15/03 (3, 2, 1: natação, ciclismo e corrida; o pai e as trocas não contam).

## Referência
- [[decisoes/0010-carga-de-treino]], itens 1, 4, 5, 6 e 7, os exemplos 1 a 4 e a seção "Fontes conferidas".
- Coggan, A. & Allen, H., *Training and Racing with a Power Meter* (VeloPress); TrainingPeaks, *The Development of the
  Training Stress Score* e *Running Training Stress Score (rTSS) Explained*; Banister et al. (1976), IEEE Trans. SMC-6(2):94-102.

## Código e teste
- Gerador: `tests/fixtures/garmin/gerar_fixtures_carga.py` (`uv run python tests/fixtures/garmin/gerar_fixtures_carga.py`).
  Determinístico; o teste falha se os zips versionados estiverem desatualizados. Reusa `gerar_fixtures.py` (FIT e JSON) e
  `gerar_fixtures_saude.py` (arquivos de saúde).
- Teste: `services/api/tests/metricas/test_carga_oraculo.py` (valores esperados calculados à mão: as contas acima). Confere
  que cada atividade do `ESPERADO` bate com uma referência curta e independente das regras da ADR (escrita no próprio teste,
  sem o código de `app/metricas/`), que os exemplos 1 a 4 da ADR dão os números do texto, que a série dos dias escolhidos
  bate com a recursão e com a forma fechada, que `aprendendo` muda entre os dias 41 e 42, que o limiar do teste é o da
  fixture de saúde e que o leitor de FIT lê as voltas da tabela.
- Quem usa: #138 (carga por atividade), #139 (série), #141 (comando), #142 (API), #146 e o QA.

## Limitações e quando não usar
- Os FIT têm só voltas (sem série por segundo, sem GPS, sem altimetria): não exercitam subida nem calor.
- Todas as atividades estão no fuso -3 h; o caso `fuso_min` nulo (America/Sao_Paulo por padrão, ADR 0003) fica para os testes unitários.
- Não há limiar por esporte (a FC de limiar vale para corrida e ciclismo), como na ADR.
- Não há caso de duas origens de limiar no mesmo dia (`informado` e `garmin_export`), de limiar que chega depois da atividade
  (recálculo) nem de reclassificação de subtipo; ficam para a #138 e a #141.
- A forma `1 - exp(-1/tau)` e o TSB do mesmo dia **não batem** com o TrainingPeaks (ADR, item 6): não compare estes números
  com os de lá. O hrTSS aqui é adaptação própria.
- Valores do atleta sintético; um atleta real terá outros limiares.

## Nota da `carga@2` (#255)
O oráculo não muda: nenhuma atividade das fixtures tem voltas sem FC com FC média na atividade (a esteira `4000000007` segue `sem_fc`). O caso novo é coberto por testes sintéticos em `test_carga.py` e `test_calcular_carga.py`.
