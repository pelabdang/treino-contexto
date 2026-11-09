---
tipo: metrica
status: rascunho
dono: caio
atualizado: 2026-11-09
links: [[decisoes/0012-check-in-pos-treino]], [[decisoes/0003-fuso-da-atividade]], [[metricas/carga-oraculo]], [[metricas/carga-treino]], [[produto/roadmap]], [[glossario]]
---
# Check-in e carga pela PSE: fixtures e oráculo

## O que mede
O resultado esperado da **carga pela PSE** (`carga_pse@1`), do **prazo para criar** o check-in, da **lista de pendentes** e da **validação do corpo
do `PUT`** para 18 atividades sintéticas de 15/10 a 09/11/2026, com 9 check-ins sintéticos. É o oráculo que a função pura (#297), o banco e a API
(#296, #298) e o QA reaproveitam. Regras: [[decisoes/0012-check-in-pos-treino]]. Nenhum número vem de IA nem de dado real, e **nenhum check-in é real**.
Rascunho: vira "em-uso" quando as funções existirem.

Arquivos (`tests/fixtures/meta8/`): `gerar_fixtures_meta8.py` (gera `atividades.json` e `checkins.json`), `oraculo.py` (valores esperados e `PARAMETROS`) e o
teste `tests/test_fixtures_meta8.py`, que confere o JSON contra o gerador e o oráculo contra uma referência curta e independente. "Agora" das fixtures:
09/11/2026 às 15:00 locais (UTC-3).

## Fórmula
`carga_pse = PSE x minutos`, `minutos = duracao_s / 60` (tempo de cronômetro), em UA. Regra própria do projeto sobre a sRPE (Foster et al., 2001,
*J. Strength Cond. Res.* 15(1):109-115; citação a conferir). Calculada na leitura. PSE 0 vale 0; check-in com `duracao_s = 0` é `sem_duracao`; sem
check-in é `sem_checkin`; pai e troca do multiesporte não têm carga pela PSE.

## Carga pela PSE esperada
| Atividade | PSE | Minutos | Conta | Estado e valor |
|---|---|---|---|---|
| 09/11 corrida 07:00 | 6 | 45 | 6 x 45 | calculada, **270 UA** |
| 08/11 natação (piscina) | 4 | 40 | 4 x 40 | calculada, **160 UA** (a `carga@2` dela é `sem_carga`) |
| 08/11 ciclismo (virtual) | 7 | 50 | 7 x 50 | calculada, **350 UA** |
| 07/11 corrida | 6 | 45,4167 | 6 x 2725 / 60 | calculada, **272,5 UA** |
| 06/11 força (`outra`) | 0 | 30 | 0 x 30 | calculada, **0 UA** |
| 03/11 natação (águas abertas) | 5 | 30 | 5 x 30 | calculada, **150 UA** |
| 03/11 ciclismo | 6 | 45 | 6 x 45 | calculada, **270 UA** |
| 15/10 corrida (antiga) | 5 | 45 | 5 x 45 | calculada, **225 UA** |
| 09/11 corrida 06:00 (`duracao_s = 0`) | 5 | 0 | | `sem_duracao` |
| 05/11, 04/11, 03/11 (corrida), 02/11, 01/11 (duas) | sem check-in | | | `sem_checkin` |
| 03/11 pai e duas trocas | | | | sem carga pela PSE (`null`) |

## Prazo e pendentes
Criar vale se a data local da atividade (ADR 0003) é `>= hoje - 7`: janela de 02/11 a 09/11 às 15:00 de 09/11. A corrida de 01/11 às 23:30 locais já é
02/11 em UTC e **fica fora** (vale a data local); a de 02/11 (com `fuso_min` nulo) fica no limite e **dentro**. Editar não tem prazo (a de 15/10 tem check-in).

| Relógio | `dias` | Pendentes (mais recentes primeiro) |
|---|---|---|
| 09/11 15:00 | 7 | 05/11 corrida, 04/11 ciclismo (subtipo nulo), 03/11 corrida das 09:20, 02/11 corrida |
| 10/11 00:01 | 7 | os três primeiros (a de 02/11 sai da janela) |
| 09/11 15:00 | 5 | 05/11 e 04/11 |
| 09/11 15:00 | 3 | nenhuma |

Não entram: o pai e as trocas do multiesporte, as que já têm check-in e as fora da janela.

## Validação do corpo do `PUT`
21 casos em `VALIDACAO`: 7 válidos (completo, nada a relatar, só texto, só atalho, PSE 0, texto de 500 caracteres, os cinco atalhos) e 14 inválidos (PSE
fora de 0 a 10, sensação fora de 1 a 5, nada a relatar com atalho ou texto, sem nada a relatar e sem atalho nem texto, texto só de espaços, atalho
desconhecido ou repetido, texto de 501 caracteres, campos obrigatórios ausentes).

## Como conferir
`uv run pytest tests/test_fixtures_meta8.py` (sem rede).
