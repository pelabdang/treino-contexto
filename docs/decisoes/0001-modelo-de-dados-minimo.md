---
tipo: decisao
status: em-uso
dono: theo
atualizado: 2026-10-31
links: [[produto/plano-mvp-execucao]], [[produto/roadmap]]
---
# ADR: 0001 Modelo de dados mínimo e estrutura do monorepo

## Contexto
A Meta 1 precisa guardar atividades da exportação Garmin e os tiros de 1 km dos intervalados.
O plano (seção 3.2) descreve um modelo completo; começar com tudo atrasaria a primeira entrega.

## Decisão
- Monorepo: `apps/mobile` (Expo), `services/api` e `services/worker` (FastAPI, workspace uv na raiz),
  `infra/docker-compose.yml` (Postgres 16). Migrações com Alembic em `services/api/alembic/`.
- Tabelas iniciais (migração `0001`): `assessoria`, `professor`, `atleta`,
  `vinculo_professor_atleta`, `atividade` e `segmento`.
- `atividade` é única por `(atleta_id, fonte, fonte_id)`, para que reimportar a mesma exportação não duplique.
  Guarda `arquivo_bruto` (caminho do original) seguindo o princípio "guardar o dado bruto".
- `segmento` guarda voltas, tiros e recuperações com `ordem`, duração, distância, FC média e pace (s/km),
  mais `zona` e `equipamento` opcionais.
- Domínios fixos (modalidade, tipo de treino, origem do tipo, tipo de segmento) como texto com `CHECK`,
  mais fáceis de migrar que enums do Postgres.
- Testes rodam em SQLite em memória localmente e em Postgres no CI (`TEST_DATABASE_URL`).
  Um teste garante que a migração gera exatamente o esquema dos modelos.

## Alternativas consideradas
- Modelo completo do plano já na largada: muitas tabelas sem uso na Meta 1.
- Séries por segundo no banco: o plano pede Parquet em storage. Fica para depois.

## Consequências
- Check-in, clima, bem-estar, métricas derivadas e linha de base entram em migrações futuras, cada uma com ADR.
- Mudanças em `services/api/app/db/models.py` precisam de aprovação do Theo.

## Data e quem decidiu
2026-10-31, Theo (tech lead). Issue #1.
