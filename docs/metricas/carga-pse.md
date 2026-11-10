---
tipo: metrica
status: rascunho
dono: caio
atualizado: 2026-11-09
links: [[decisoes/0012-check-in-pos-treino]], [[metricas/carga-pse-oraculo]], [[metricas/carga-treino]], [[decisoes/0010-carga-de-treino]], [[produto/roadmap]], [[glossario]]
---
# Carga pela PSE (`carga_pse@1`)

## O que mede
O esforço de uma sessão como o atleta o sentiu, multiplicado pelo tempo: `carga_pse = PSE x minutos`, em **UA** (unidades arbitrárias). Função pura em
`services/api/app/metricas/carga_pse.py`: `carga_pse(pse, duracao_s, subtipo)`. Sem banco, sem rede, sem IA. Decisão: [[decisoes/0012-check-in-pos-treino]].
É estimativa de esforço percebido, nunca medida, e **não se soma nem se compara com a `carga@2`** ([[metricas/carga-treino]]): escalas diferentes (UA x TSS).
Sem série diária, CTL, ATL nem TSB pela PSE. Dá carga também à natação, que a `carga@2` não tem.

## Regra
- `minutos = duracao_s / 60`, o **tempo de cronômetro** (tempo em movimento) da atividade; o tempo corrido não está gravado. Em treino com muita parada
  (intervalado, descanso na borda) o cronômetro pode ser menor que a duração total e a carga sai um pouco menor.
- **PSE** é a CR-10 em inteiros, de 0 a 10. PSE 0 vale `0 UA`. Fora da faixa é erro de quem chama (`ValueError`, mensagem fixa, sem repetir o valor).
- **Estados:** `calculada` (valor = PSE x minutos); `sem_checkin` (sem PSE, nunca se estima); `sem_duracao` (check-in com `duracao_s <= 0`).
- **Não elegível** (`multiesporte_pai`, `troca`): a função devolve `None`, sem carga pela PSE e sem pedir check-in. Natação, `outra` e qualquer outro subtipo são elegíveis.
- Calculada na leitura, não gravada: é o produto de dois campos já gravados (PSE e duração).

## Fonte e versão
Regra própria do projeto sobre a sRPE: Foster et al. (2001), *J. Strength Cond. Res.* 15(1):109-115; a CR-10 é de Borg (1982), *Med. Sci. Sports Exerc.* 14(5):377-381, e
Borg (1998), *Borg's Perceived Exertion and Pain Scales*. Citações ainda a conferir nos textos. `VERSAO = "carga_pse@1"`; sobe quando mudar a fórmula, os minutos
usados, o tratamento de PSE 0 e de atividade sem duração, ou a elegibilidade.

## Exemplos à mão
Corrida de 2700 s (45 min), PSE 6: `6 x 45 = 270 UA`. Natação de 2400 s (40 min), PSE 4: `4 x 40 = 160 UA`. Ciclismo de 3000 s (50 min), PSE 7: `350 UA`.
Corrida de 2725 s (45,4167 min), PSE 6: `272,5 UA`; o texto da API mostra a duração em minutos e segundos: "Carga pela PSE: 6 x 45 min 25 s = 272,5 UA." (inteira: "6 x 45 min = 270 UA."). PSE 0 em 1800 s: `0 UA`. Check-in com `duracao_s = 0`: `sem_duracao`. Mais casos em [[metricas/carga-pse-oraculo]].

## Testes
`services/api/tests/metricas/test_carga_pse.py` (oráculo das 18 atividades da #294, valores à mão e bordas).

## Limitações
Usa o cronômetro e não o tempo total (uma `carga_pse@2` pediria gravar o tempo corrido na importação). A formatação ("270 UA", "272,5 UA") e o texto são da API (#298): `services/api/app/servicos/carga_pse_leitura.py`, no `GET` da atividade ([[modulos/api]]).
