---
tipo: decisao
status: em-uso
dono: theo
atualizado: 2026-10-31
links: [[decisoes/0001-modelo-de-dados-minimo]], [[modulos/banco]], [[modulos/ingestao-garmin]], [[produto/roadmap]]
---
# ADR: 0002 Segmento com intensidade da volta e versão da detecção

## Contexto
A ADR 0001 criou `atividade` e `segmento` (tipo volta/tiro/recuperacao, distância, duração, FC, pace). Para
detectar os tiros de 1 km com segurança (Meta 1, #11) faltam dois dados:
- a **intensidade da volta** que o relógio grava no FIT (`active`, `rest`, `warmup`, `cooldown`, `recovery`,
  `interval`). Sem ela, uma recuperação trotada de 1 km se confunde com um tiro lento;
- a **versão do cálculo** que classificou o segmento como tiro. O plano pede versionar cada métrica derivada:
  se a regra mudar, sabemos quais segmentos recalcular.

## Decisão
Em `segmento`, duas colunas novas, ambas anuláveis (migração Alembic `0002`, sem editar a `0001`):
- `intensidade` (texto, 20): valor do FIT normalizado em minúsculas, com `CHECK`:
  `active, rest, warmup, cooldown, recovery, interval, other`. `NULL` quando o FIT não traz o campo ou não há FIT.
- `versao_deteccao` (texto, 40): identificador da regra que classificou o segmento, no formato
  `<regra>@<n>` (ex.: `tiros_1km@1`). `NULL` enquanto nenhuma regra classificou.

A importação (#13) grava `intensidade` como veio do FIT; a classificação (#14) preenche `tipo` e `versao_deteccao`.
Se a detecção não conseguir usar a intensidade (ela é opcional), cai para distância e pace.

## Alternativas consideradas
- Enum do Postgres para `intensidade`: mais difícil de migrar; segue a regra da 0001 (texto com `CHECK`).
- Guardar a intensidade só dentro de `tipo`: perde o dado bruto do relógio e mistura origem com classificação.
- Tabela separada de métricas derivadas versionadas: mais correta no longo prazo, grande demais para a Meta 1.
  Reavaliar quando houver mais de uma métrica derivada (Meta 5).
- Não mudar o modelo e detectar só por distância e pace: fica como plano B se a mudança for recusada.

## Consequências
- Segmentos já gravados ficam com os dois campos `NULL`; nada quebra.
- Nova regra de detecção = novo valor em `versao_deteccao` e recálculo apenas dos segmentos de versão antiga.
- Valores de `intensidade` fora da lista são rejeitados pelo banco; novo valor do FIT exige nova migração.
- O teste de migração (`services/api/tests/test_migracoes.py`) continua garantindo que a migração gera o esquema dos modelos.

## Data e quem decidiu
2026-10-31. Direção aprovada por Theo (tech lead) no comentário da issue #9; aprovação final no PR desta ADR. Issue #9.
