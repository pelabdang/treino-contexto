---
tipo: modulo
status: em-uso
dono: theo
atualizado: 2026-10-31
links: [[decisoes/0001-modelo-de-dados-minimo]], [[modulos/api]], [[modulos/infra]]
---
# Módulo: banco

## Para que serve
Guarda atleta, atividades importadas e segmentos (voltas, tiros, recuperações). Modelo mínimo da Meta 1.
Motivos da escolha em [[decisoes/0001-modelo-de-dados-minimo]].

## Entradas e saídas
- Tabelas: `assessoria`, `professor`, `atleta`, `vinculo_professor_atleta`, `atividade`, `segmento`.
- `atividade` é única por `(atleta_id, fonte, fonte_id)`: reimportar não duplica.
- `arquivo_bruto` guarda o caminho do original (princípio "guardar o dado bruto").
- Domínios fixos (modalidade, tipo de treino, origem do tipo, tipo de segmento) são texto com `CHECK`.

## Arquivos principais
- `services/api/app/db/models.py`: modelos SQLAlchemy. Mudança só com aprovação do Theo.
- `services/api/alembic/versions/0001_modelo_de_dados_minimo.py`: migração inicial.
- `services/api/tests/test_migracoes.py`: garante que a migração gera o esquema dos modelos.

## Depende de
- Postgres 16 em [[modulos/infra]]. Usado pela [[modulos/api]].

## Como testar
`uv run pytest -q`. Para Postgres: defina `TEST_DATABASE_URL`. Migrar: `cd services/api && uv run alembic upgrade head`.

## Pendências
- Check-in, clima, bem-estar, métricas derivadas e linha de base entram em migrações futuras, cada uma com ADR.
- Séries por segundo irão para Parquet, não para o banco.
