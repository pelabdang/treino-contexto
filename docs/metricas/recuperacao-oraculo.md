---
tipo: metrica
status: rascunho
dono: caio
atualizado: 2026-11-12
links: [[decisoes/0014-recuperacao-diaria]], [[metricas/recuperacao]], [[metricas/linha-base]], [[produto/roadmap]], [[glossario]]
---
# Recuperação: oráculo à mão (`recuperacao@1`)

## O que mede
O resultado esperado da `recuperacao@1` ([[metricas/recuperacao]]) em casos **sintéticos** escritos à mão, com a conta de cada um. Os valores são inventados
(o dia do treino é 15/03/2030, sintético) e **nenhum vem de resposta do Garmin nem da conta de ninguém**. O teste é `services/api/tests/metricas/test_recuperacao.py`.
Parâmetros: janela 28 noites, mínimo 14, piso 0,05, limite 2,0, corte 06:00.

## Casos
| Caso | Entrada | Conta | Esperado |
|---|---|---|---|
| A | sono em min: 400, 410, 420, 420, 425, 430, 435, 435, 440, 440, 445, 450, 460, 470 (14 noites, D-14 a D-1) | mediana (435 + 435) / 2 = 435; desvios ordenados 0, 0, 5, 5, 5, 10, 10, 15, 15, 15, 25, 25, 35, 35; MAD (10 + 15) / 2 = 12,5; desvio `max(1,4826 x 12,5 = 18,5325; 0,05 x 435 = 21,75) = 21,75` (1305 s) | noite de 345 min: z = -4,138, `abaixo`; de 420 min: z = -0,690, `dentro` |
| A, limite | o mesmo, 2 x 21,75 = 43,5 min | 435 - 43,5 = 391,5; 435 + 43,5 = 478,5 | 391,5: `abaixo`; 392: `dentro`; 478: `dentro`; 478,5: `acima` |
| B | o caso A com só 13 noites (a mais antiga some), noite de 345 min | n = 13 < 14 | `aprendendo`, valor 345 min, n = 13, sem mediana, desvio nem z |
| C | FC de repouso: 14 noites iguais a 52 bpm | MAD 0; desvio = piso = 0,05 x 52 = 2,6 | 57: z = 1,923 `dentro`; 58: z = 2,308 `acima`; 47: z = -1,923 `dentro`; 46: z = -2,308 `abaixo` |
| D | VFC em ms: 40, 42, 44, 44, 45, 46, 47, 47, 48, 49, 50, 52, 54, 56 | mediana 47; desvios ordenados 0, 0, 1, 1, 2, 2, 3, 3, 3, 5, 5, 7, 7, 9; MAD 3; desvio `max(4,4478; 2,35) = 4,4478` | 41 ms: z = -1,349 `dentro`; 38 ms: z = -2,0235 `abaixo` |
| E | 28 noites de 26100 s (D-1 a D-28), mais uma de 1 s em D-29, uma de 1 s em D+1 e a noite D | só D-28 a D-1 entram | n = 28, mediana 26100 (as de 1 s e a noite D não entram); sem a de D-28, n = 27 |
| F | noite D com sono e FC de repouso, sem VFC; histórico só de sono | VFC sem valor na noite | bloco `ok`; sono `dentro`, VFC `sem_dado`, FC de repouso `aprendendo` (n = 0) |
| G | sem linha em D, ou linha com as três medidas vazias | | `sem_dado` / `sem_noite`, sem medidas |
| H | treino às 05:59 e às 06:00, com noite gravada | corte às 06:00 | 05:59: `sem_dado` / `treino_de_madrugada`; 06:00: `ok` |
| I | treino um dia antes da noite mais antiga; no próprio dia da mais antiga; nenhuma noite gravada | | `fora_do_periodo`; `ok` com as medidas `aprendendo` (n = 0); `sem_noite` |
| J | madrugada num dia anterior à noite mais antiga | madrugada vem primeiro | `treino_de_madrugada` |
| K | dois treinos no mesmo dia (07:00 e 22:00) | mesma noite | o mesmo resultado |

## Fontes e versão
Mesmas da [[metricas/recuperacao]]. `recuperacao@1`.

## Limitações e quando não usar
Os casos cobrem a função pura; o `importado_em`, o "desatualizado" e os textos são das issues #372 e #374.
