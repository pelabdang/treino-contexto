---
tipo: decisao
status: em-uso
dono: theo
atualizado: 2026-10-31
links: [[decisoes/0001-modelo-de-dados-minimo]], [[decisoes/0002-segmento-intensidade-e-versao]], [[modulos/banco]], [[modulos/ingestao-garmin]], [[produto/roadmap]]
---
# ADR: 0003 Fuso da atividade e data local da sessão

## Contexto
`atividade.inicio` é guardado em UTC. A série de tiros (Meta 1, #14) tem a data da sessão no eixo X, e o
atleta pensa na data **local**: um treino às 22:30 em São Paulo é 01:30 UTC do dia seguinte, e cairia no dia errado.
A exportação Garmin traz `startTimeLocal` (hora de parede local) além de `startTimeGmt`; o parser (#10) já
calcula `inicio_local` com fuso, mas a tabela não tem onde guardar esse dado.

## Decisão
- Em `atividade`, uma coluna nova, anulável (migração Alembic `0003`, sem editar as anteriores):
  `fuso_min` (inteiro): deslocamento do fuso em minutos, `startTimeLocal` - `startTimeGmt` (ex.: `-180` para UTC-3).
  `NULL` quando a fonte não traz o horário local (FIT sem JSON, atividades antigas). `CHECK`:
  `fuso_min IS NULL OR fuso_min BETWEEN -720 AND 840` (fusos reais vão de UTC-12 a UTC+14).
- A importação (#13) preenche `fuso_min` a partir de `inicio_local` do parser. Como a reimportação já atualiza
  atividades que mudaram, reimportar a exportação preenche a coluna nas atividades antigas. `fuso_min` entra na
  comparação "mudou ou não" da importação.
- **Data local da sessão** = data de `inicio + fuso_min minutos`. Se `fuso_min` é `NULL`, usa `America/Sao_Paulo`
  (zoneinfo, respeita o horário de verão histórico) aplicado ao `inicio` em UTC.
- O cálculo fica numa função única (`data_local(inicio, fuso_min)`) usada pela série e pelo filtro `inicio`/`fim`.
- O parser continua sem inventar fuso: `inicio_local` é `None` quando o campo falta ou o deslocamento sai de
  UTC-12 a UTC+14 (mesmo intervalo do `CHECK`).

## Alternativas consideradas
- Guardar `inicio_local` como timestamp sem fuso: duplica o instante e dá duas fontes de verdade; o deslocamento
  basta e é menor.
- Guardar o nome do fuso (`America/Sao_Paulo`): a exportação só dá o deslocamento do dia, não o nome.
- Sempre `America/Sao_Paulo`, sem coluna: erra para quem treina ou viaja fora desse fuso.
- Fuso do atleta no cadastro: não existe cadastro na Meta 1; pode complementar o fallback depois.

## Consequências
- Atividades já gravadas ficam com `fuso_min` `NULL` e usam o fallback até serem reimportadas.
- Atividade nova de FIT sem JSON usa o fallback `America/Sao_Paulo`.
- Mudança no modelo (`services/api/app/db/models.py`): precisa da aprovação do Theo (este ADR).
- O teste de migração continua garantindo que a `0003` gera o esquema dos modelos.

## Data e quem decidiu
2026-10-31. Proposta da Duda; direção do Theo na issue #14. Aprovada por Theo (com o `CHECK` de faixa) na issue #14.
