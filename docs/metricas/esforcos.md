---
tipo: metrica
status: rascunho
dono: caio
atualizado: 2026-11-04
links: [[decisoes/0008-deteccao-de-esforcos]], [[metricas/esforcos-oraculo]], [[metricas/tiros-1km]], [[modulos/ingestao-garmin]], [[produto/roadmap]], [[glossario]]
---
# Esforços: blocos do treino

## O que mede
Lê a sequência de voltas de uma atividade como **blocos** e dá a cada bloco uma categoria: `aquecimento`, `esforco`,
`recuperacao`, `desaquecimento` ou `leve`. É o primeiro passo comum da detecção de esforços (corrida por distância,
ciclismo por duração; [[decisoes/0008-deteccao-de-esforcos]]). Esta nota cobre a versão `esforcos@1`, da função de
blocos. Faixas nomeadas (`d400`, `t4`...) e treino-chave contínuo vêm nas notas das issues seguintes. Cálculo
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

## Dados de entrada
Voltas do banco (`segmento`: `ordem`, `inicio_offset_s`, `duracao_s`, `distancia_m`, `fc_media`, `intensidade`) e
`atividade.modalidade`. O FIT sem `start_time` no lap grava `inicio_offset_s = 0` e o tempo parado não é computável: a
conta dá 0 e a parada só aparece como volta de pausa (ADR 0008, "A confirmar", item 5).

## Referência
- [[decisoes/0008-deteccao-de-esforcos]], itens 1 a 5. Regra própria do projeto; os valores de referência
  bibliográfica da ADR (Buchheit e Laursen, Seiler, Daniels) ainda não foram conferidos.
- Oráculo: [[metricas/esforcos-oraculo]] (sete atividades sintéticas, com a conta à mão).

## Código e teste
- Código: `services/api/app/metricas/esforcos.py` (`montar_blocos`, `VERSAO = "esforcos@1"`).
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
- **Progressivo suave** e fartlek moderado juntam num bloco só ou viram um esforço contínuo; a distinção fica para o
  treino-chave (#163).
- Pausa só por pace, distância ou velocidade quando o relógio não grava `start_time`; uma parada curta (menos de
  15 s) dentro do esforço não separa os blocos.
- A tabela `bloco_atividade` (ADR 0008, item 9) é da Duda e da #166; esta função não toca o banco.
