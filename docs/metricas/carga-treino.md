---
tipo: metrica
status: rascunho
dono: caio
atualizado: 2026-11-07
links: [[decisoes/0010-carga-de-treino]], [[metricas/carga-oraculo]], [[decisoes/0002-segmento-intensidade-e-versao]], [[decisoes/0003-fuso-da-atividade]], [[decisoes/0009-treino-de-transicao]], [[glossario]], [[produto/roadmap]], [[metricas/serie-carga]], [[modulos/worker]], [[modulos/banco]]
---
# Carga de treino: rTSS e hrTSS por volta (`carga@1`)

## O que mede
Quanto uma atividade custou ao corpo, numa escala única em que **1 hora no limiar vale 100**. É sempre **estimativa**, nunca medida.
Cada volta é comparada com o limiar do atleta **vigente na data** da atividade; a carga da atividade é a soma das voltas. Corrida usa o
pace (rTSS) ou a FC (hrTSS); ciclismo e esteira, só a FC. Natação e `outra` ficam sem carga. Sem dado suficiente, a atividade fica
"sem carga" **com o motivo**, e nunca com um número inventado. Cálculo determinístico, em código, sem banco e sem IA.
Esta nota cobre a carga **por atividade** (#138 e #141). A série diária (CTL, ATL, TSB) tem nota própria: [[metricas/serie-carga]].

## Fórmula
Função pura `calcular_carga` em `services/api/app/metricas/carga.py`; `VERSAO = "carga@1"`. Constantes iguais para todos os atletas.

```
rTSS_i  = (duracao_i / 3600) x IF_i^2 x 100,   IF_i = (distancia_i / duracao_i) / velocidade_limiar   (m/s)
hrTSS_i = (duracao_i / 3600) x IF_i^2 x 100,   IF_i = fc_media_i / fc_limiar                          (bpm)
carga   = soma das voltas (todos os tipos: volta, tiro e recuperação)
```

- **Volta sem o dado** do método (sem FC no hrTSS; sem distância ou duração no rTSS) conta 0. O método só vale se as voltas com dado
  cobrem **pelo menos 95%** da soma das durações (`COBERTURA_MIN = 0,95`).
- **Atividade sem voltas** (JSON sem FIT) é uma volta única (`duracao_s`, `distancia_m`, `fc_media`), com `granularidade = 'atividade'`.
- **Qual método vale:** corrida fora da esteira: rTSS, depois hrTSS (o rTSS vence quando os dois valem; ambos ficam em `carga_rtss` e
  `carga_hrtss`). Corrida em esteira e ciclismo: só hrTSS. Natação e `outra`: `modalidade_sem_carga`. `multiesporte_pai` e `troca`:
  **ignoradas** (a função devolve `None`: não há linha nem motivo).
- **Motivo** (ordem da ADR 0010, item 7): `modalidade_sem_carga`; nenhum caminho com limiar na data: `sem_dados_saude` (o atleta não tem
  nenhuma linha da grandeza) ou `sem_limiar_na_data` (todas começam depois); senão o do **primeiro caminho disponível**:
  `sem_fc`, `sem_pace` ou `cobertura_insuficiente` (`cobertura_pct` só aí).
- **Limiar** entra já resolvido (`Limiares`); quem resolve a vigência por data local é `app/servicos/carga.py` (#141). Limiar nunca é estimado nem tomado de data
  posterior.

## Onde fica e como recalcula (#141)
A carga de cada atividade fica em `carga_atividade` ([[modulos/banco]]), uma linha por atividade elegível. `worker.calcular_carga` ([[modulos/worker]]) resolve o limiar vigente no **dia local** da atividade, calcula e grava a `entrada` (SHA-256 de modalidade, subtipo, voltas e limiares do caminho da modalidade, com a vigência) e a `versao`. Só regrava quando um dos dois mudou: reexecutar não muda nada, subir `VERSAO` recalcula tudo e um limiar novo recalcula só as atividades da nova vigência. Em `calculada`, `limiar_vigente_desde` é a vigência do limiar do método vencedor.

## Dados de entrada
Por atividade: `modalidade`, `subtipo`; por volta: `duracao_s` (tempo em movimento), `distancia_m`, `fc_media`; limiares vigentes
(`fc_bpm`, `velocidade_ms`) e, para cada grandeza, se o atleta tem alguma linha (distingue `sem_dados_saude` de `sem_limiar_na_data`).

## Referência
- Coggan, A. & Allen, H., *Training and Racing with a Power Meter* (VeloPress); TrainingPeaks, "The Development of the Training Stress
  Score": `TSS = horas x IF^2 x 100`.
- TrainingPeaks, *Running Training Stress Score (rTSS) Explained*: ideia do rTSS (aqui **sem** ajuste de subida).
- O hrTSS é **adaptação própria** (mesma forma, IF pela FC); **não** é o hrTSS por zonas do TrainingPeaks e os valores não são comparáveis.
- Detalhes, fontes conferidas e decisões: [[decisoes/0010-carga-de-treino]].

## Código e teste
- Código: `services/api/app/metricas/carga.py`
- Banco: `services/api/app/servicos/carga.py`; comando `services/worker/worker/calcular_carga.py`
- Teste do banco: `services/worker/tests/test_calcular_carga.py` (confere as 20 linhas do oráculo, `TOTAIS` e o atleta sem saúde)
- Teste: `services/api/tests/metricas/test_carga.py` (valores à mão nos comentários; confere todas as atividades do oráculo
  [[metricas/carga-oraculo]], `ESPERADO` e `SEM_SAUDE`)

Exemplos à mão (sintéticos), limiar de 270 s/km (3,7037 m/s) ou FC de limiar 170 bpm:

| Caso | Conta | Resultado |
|---|---|---|
| rTSS, 1000 m em 300 s | IF 0,9; 300/3600 x 0,81 x 100 | 6,75 |
| rTSS, 1000 m em 240 s | IF 1,125; 240/3600 x 1,265625 x 100 | 8,4375 (atividade das duas: 15,1875) |
| hrTSS, 300 s a 153 bpm e 240 s a 187 bpm | 6,75 + 240/3600 x 1,21 x 100 | 14,8167 |
| 1 h no limiar | IF 1 | 100 |
| 20 voltas de 50 s, uma sem FC | cobertura 950/1000 = 95%; 19 x 1,125 | vale, 21,375 |
| 10 voltas de 100 s, uma sem FC | cobertura 90% | `cobertura_insuficiente` |

## Limitações e quando não usar
- **Por volta, sem ajuste de subida nem de calor** (estimativa): a subida deixa o pace lento e subestima a carga; a descida faz o contrário.
- **Voltas, não segundos:** `IF^2` por volta subestima treinos com variação dentro da volta (convexidade).
- hrTSS pela razão direta ignora FC de repouso e deriva cardíaca; a FC de limiar da fonte pode ser de corrida e subestimar o ciclismo.
- Esteira só por FC; natação e `outra` sem carga. `duracao_s` é tempo em movimento: a pausa do cronômetro não conta.

## Série diária: CTL, ATL e TSB
A série diária tem nota própria: [[metricas/serie-carga]] (`serie_carga@1`, `app/metricas/serie_carga.py`, #139).
