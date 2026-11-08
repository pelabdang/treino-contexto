---
tipo: metrica
status: rascunho
dono: caio
atualizado: 2026-11-07
links: [[decisoes/0010-carga-de-treino]], [[decisoes/0003-fuso-da-atividade]], [[metricas/carga-treino]], [[metricas/carga-oraculo]], [[metricas/conferencia-carga]], [[produto/roadmap]], [[glossario]]
---
# Série de carga: CTL, ATL e TSB diários (`serie_carga@1`)

## O que mede
Da carga de cada dia sai o **condicionamento (CTL)**, a **fadiga (ATL)** e a **forma (TSB)** do atleta, dia a dia. A carga de cada
atividade vem de [[metricas/carga-treino]]; aqui só se combina. Sempre estimativa, nunca medida. Regras da
[[decisoes/0010-carga-de-treino]], item 6.

## Fórmula
Por dia `d`, com `L_d` a soma das cargas `calculada` das atividades do dia local ([[decisoes/0003-fuso-da-atividade]]):

```
k_ctl = 1 - exp(-1/42) = 0,023528        k_atl = 1 - exp(-1/7) = 0,133122
CTL_d = CTL_(d-1) + (L_d - CTL_(d-1)) x k_ctl
ATL_d = ATL_(d-1) + (L_d - ATL_(d-1)) x k_atl
TSB_d = CTL_d - ATL_d                      (fim do mesmo dia)
```

- **Semente:** `CTL = ATL = 0` antes do primeiro dia com carga calculada. A série começa nesse dia.
- **Dia sem treino:** `L_d = 0`; a série tem todos os dias entre o primeiro e o último, e CTL e ATL decaem.
- **Fim:** o dia da última atividade recebida (calculada ou não), sem estender até hoje.
- **`aprendendo`:** verdadeiro enquanto `dia - primeiro_dia < 42` dias.
- **Por dia:** `atividades`, `calculadas` e `sem_carga` (contam as atividades elegíveis do dia local). Um dia com `sem_carga > 0`
  não é dia de descanso: houve treino sem dado.
- **Totais:** `calculadas`, `sem_carga_total`, `por_motivo` (seis motivos, sempre todos presentes) e `ignoradas_multiesporte`.
  Contam **todas** as atividades recebidas, inclusive as anteriores ao primeiro dia da série.
- **Sem nenhuma carga calculada:** série vazia, com os totais.

**Exemplo à mão.** Cargas 100, 0 e 50 a partir do primeiro dia (mesmo da ADR, exemplo 4):

| Dia | L | ATL | CTL | TSB |
|---|---|---|---|---|
| 1 | 100 | 100 x 0,133122 = 13,3122 | 100 x 0,023528 = 2,3528 | -10,9594 |
| 2 | 0 | 13,3122 - 13,3122 x 0,133122 = 11,5401 | 2,3528 - 2,3528 x 0,023528 = 2,2975 | -9,2426 |
| 3 | 50 | 11,5401 + (50 - 11,5401) x 0,133122 = 16,6599 | 2,2975 + (50 - 2,2975) x 0,023528 = 3,4198 | -13,2401 |

Dois treinos no mesmo dia (60 e 40) valem um de 100: `L_d = 100`.

## Dados de entrada
Função pura `calcular_serie(atividades, ignoradas_multiesporte)`. Cada `AtividadeCarga` traz o **dia local já calculado**
(`data_local(inicio, fuso_min)` de `app.servicos.fuso`, feito por quem chama, para a função não depender de fuso), e `carga`
(ou `None` com um dos seis `motivo`). Atividades `multiesporte_pai` e `troca` não entram: quem chama passa só a contagem delas.
Carga negativa, motivo inválido, ou carga junto com motivo levantam `ValueError`.

## Referência
- Banister, Calvert, Savage e Bach, "A systems model of training for athletic performance", IEEE Trans. Syst. Man Cybern.
  SMC-6(2):94-102, 1976 (modelo de impulso-resposta).
- Janelas de 42 e 7 dias: *Performance Management Chart* do TrainingPeaks. Forma exata `1 - exp(-1/tau)`: planilha do Golden Cheetah.
- Diferença conhecida: o TSB do TrainingPeaks usa CTL e ATL do dia anterior; o nosso é o do fim do mesmo dia (glossário).

## Código e teste
- Código: `services/api/app/metricas/serie_carga.py` (`VERSAO = "serie_carga@1"`).
- Teste: `services/api/tests/metricas/test_serie_carga.py`. Valores à mão: dia único (CTL 2,3528, ATL 13,3122), sequência 100/0/50
  com dia sem treino, dois treinos no mesmo dia, carga constante (CTL no 42o dia = c x (1 - e^-1)). Bate com `CARGA_DIA`, `SERIE`
  e `TOTAIS` do oráculo ([[metricas/carga-oraculo]]).

## Limitações e quando não usar
- Com menos de 42 dias de histórico o CTL ainda está subindo (`aprendendo`); os números são devolvidos mesmo assim.
- Carga de atividades sem dado (`sem_carga`) não entra: a série subestima a carga nesses dias, e por isso eles ficam marcados.
- Não se estima histórico anterior à primeira carga nem se usa a carga do Garmin para semear.
- CTL e ATL batem com o TrainingPeaks só a menos da forma exata do decaimento; o TSB não bate dia a dia.
