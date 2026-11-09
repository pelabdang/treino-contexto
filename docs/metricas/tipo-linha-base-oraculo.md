---
tipo: metrica
status: rascunho
dono: caio
atualizado: 2026-11-09
links: [[decisoes/0011-linha-de-base-e-semana-padrao]], [[metricas/carga-oraculo]], [[metricas/tiros-1km]], [[produto/roadmap]], [[glossario]]
---
# Tipo de treino e linha de base: fixtures de 12 semanas e oráculo

## O que mede
O resultado esperado do **tipo de treino** (origem e divergência) e da **linha de base** (mediana, desvio robusto, estado) para 81
atividades sintéticas de 04/01 a 28/03/2026, com uma semana-padrão que muda de vigência em 02/03. É o oráculo que `tipo_treino@1` (#262),
`linha_base@1` (#263), o serviço (#265), a API (#266) e o QA reaproveitam. Regras: [[decisoes/0011-linha-de-base-e-semana-padrao]].
Nenhum número vem de IA nem de dado real. Rascunho: vira "em-uso" quando as funções puras existirem.

Arquivos (`tests/fixtures/meta7/`): `gerar_fixtures_meta7.py` (gera `atividades.json` e `semana_padrao.json`), `oraculo.py` (valores
esperados e `PARAMETROS`) e o teste `tests/test_fixtures_meta7.py`, que confere o JSON contra o gerador e o oráculo contra uma
referência curta e independente da ADR. Valores que dependem do "A confirmar" ficam em `PARAMETROS`.

## Semana-padrão das fixtures
Vigência A (desde 05/01, `definido_por` atleta) e B (desde 02/03, `professor`). Dia da semana ISO (1 = segunda).

| Dia | Vigência A | Vigência B |
|---|---|---|
| segunda | natação sem tipo | natação `leve` |
| terça | corrida `intervalado` | igual |
| quarta | ciclismo `leve` | igual |
| quinta | corrida `fartlek` | corrida `moderado` |
| sábado | corrida `longo`, ciclismo `moderado` | igual |
| domingo | corrida sem tipo | igual |
| sexta | sem itens | sem itens |

## Casos do encaixe (E1 a E16)
| Caso | Atividade | Esperado |
|---|---|---|
| E1 plano e formato coerentes | 27/01 corrida com 6 tiros | `intervalado`, `semana_padrao` |
| E2 duas corridas no dia | 20/01: 15 min solta e 50 min com tiros | a de 50 min leva o plano; a solta fica sem tipo (abaixo de 20 min) |
| E3 plano diverge, empate de duração | 13/01: duas de 30 min sem esforço | a das 07:30: `intervalado` + `sem_esforco`; a das 18:00: `leve` por reserva |
| E4 item sem tipo (natação) | segundas até 23/02 | sem tipo |
| E5 item de corrida sem tipo | 11/01 corrida 40 min sem esforço | `leve`, `sugestao` |
| E6 dia sem item | sextas | `leve`, `sugestao` |
| E7 reserva por tiros | 09/01 sexta com 6 tiros | `intervalado`, `sugestao` |
| E8 esteira | 06/01 terça | `intervalado` por plano; sem `melhor_pace` |
| E9 pedal virtual | 14/01 quarta | `leve` por plano |
| E10 multiesporte | 10/01: pai, natação, troca, ciclismo, troca, corrida | pai e trocas sem tipo; natação sem tipo; ciclismo `moderado`; corrida `longo` (plano, mesmo com 20 min) |
| E11 data local x UTC | 24/02 às 23:10 local (já quarta em UTC) | `intervalado`, usa a terça |
| E12 `fuso_min` nulo | 12/02 quinta | `fartlek`, dia por `America/Sao_Paulo` |
| E13 tipo prévio | 08/01 `professor`, 15/01 confirmado, 29/01 TrainingPeaks | não mudam |
| E14 antes da primeira vigência | 04/01 domingo | sem plano: `leve`, `sugestao` |
| E15 troca de vigência | quintas: `fartlek` até 26/02, `moderado` de 05/03 | cada uma usa a vigência da sua data |
| divergência `tem_tiros` | 28/03 sábado com 6 tiros | `longo` por plano, divergência `tem_tiros` |

## Linha de base nas sessões-alvo
Janela de 56 dias, só treinos anteriores à sessão, mínimo de 8; `desvio = max(1,4826 x MAD, 0,02 x mediana)`; `z = (valor - mediana) / desvio`;
fora quando `|z| >= 2,5`. As contas estão comentadas em `oraculo.py`.

| Sessão | Métrica | n | Mediana | Desvio | z | Estado |
|---|---|---|---|---|---|---|
| 13/03 corrida `leve` (306 s/km) | pace médio | 8 | 330 | 8,8956 | -2,698 | fora |
| 13/03 corrida `leve` | FC média | 5 | | | | aprendendo |
| 20/03 corrida `leve` (330 s/km) | pace médio | 8 | 330 | 8,8956 | 0 | dentro |
| 14/03 corrida `longo` (324 s/km) | pace médio | 8 | 334,5 | 6,69 (piso) | -1,570 | dentro |
| 21/03 corrida `longo` (315 s/km) | pace médio | 8 | 333 | 6,66 (piso) | -2,703 | fora |
| 17/03 `intervalado` (249 s/km) | melhor pace | 8 | 262,5 | 5,25 (piso) | -2,571 | fora |
| 17/03 `intervalado` | FC do melhor tiro | 7 | | | | aprendendo |
| 10/03 `intervalado` | melhor pace | 7 | | | | aprendendo (a de 13/01 é divergente) |
| 18/03 ciclismo `leve` (carga 55) | carga | 8 | 43 | 2,9652 | 4,047 | fora |
| 18/03 ciclismo `leve` (FC 133) | FC média | 8 | 130 | 2,6 (piso) | 1,154 | dentro |
| 16/03 natação `leve` | FC média | 2 | | | | aprendendo |
| 19/03 corrida `moderado` | pace médio e FC | 3 | | | | aprendendo |
| 06/01 esteira `intervalado` | melhor pace | 0 | | | | sem valor (esteira) |

Sem linha de base (com motivo): multiesporte (pai e trocas de 10/01), `sem_tipo` (natação das segundas até 23/02, a corrida solta
de 20/01 e a natação de 10/01), `divergente` (13/01 e 28/03), `transicao` (ciclismo e corrida de 10/01).

## Como conferir
`uv run pytest tests/test_fixtures_meta7.py` (sem rede).
