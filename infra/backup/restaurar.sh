#!/usr/bin/env bash
# Restaura um backup (cifrado com age) para um banco NOVO e VAZIO, reaplica as exclusoes posteriores ao backup e confere.
# Issue #505, ADR 0016, item 9. Nunca restaura por cima do banco em uso: crie o banco novo antes e aponte RESTAURAR_URL para ele.
#
#   BACKUP_ARQUIVO=/pasta/treino-...dump.age   BACKUP_CHAVE=/fora-do-servidor/chave.txt
#   RESTAURAR_URL=postgresql://.../banco_novo   REGISTRO_EXCLUSOES=/fora-do-banco/exclusoes.jsonl
#   infra/backup/restaurar.sh
#
# Passos: (1) decifra e pg_restore no banco novo; (2) `worker.excluir_conta reaplicar` apaga de novo quem foi excluido depois do
# backup (o registro fica FORA do banco); (3) `worker.conferir_restauracao` imprime a contagem de linhas por tabela, sem valores.
# Variaveis opcionais: PG_RESTORE (padrao pg_restore), UV (padrao "uv run"), CONFERIR_ARGS (ex.: "--email x@y" para provar um login).
set -euo pipefail

: "${BACKUP_ARQUIVO:?defina BACKUP_ARQUIVO}"
: "${BACKUP_CHAVE:?defina BACKUP_CHAVE (chave privada age, fora do servidor)}"
: "${RESTAURAR_URL:?defina RESTAURAR_URL (banco novo e vazio)}"
: "${REGISTRO_EXCLUSOES:?defina REGISTRO_EXCLUSOES (arquivo de exclusoes, fora do banco)}"
PG_RESTORE="${PG_RESTORE:-pg_restore}"
UV="${UV:-uv run}"

# a URL do banco novo vale nos dois formatos: libpq (pg_restore) e SQLAlchemy (worker)
URL_LIBPQ="${RESTAURAR_URL/postgresql+psycopg:/postgresql:}"
URL_APP="${URL_LIBPQ/postgresql:/postgresql+psycopg:}"

echo "restaurando $(basename "$BACKUP_ARQUIVO") para o banco novo"
age -d -i "$BACKUP_CHAVE" "$BACKUP_ARQUIVO" | "$PG_RESTORE" --no-owner --no-privileges --exit-on-error --dbname="$URL_LIBPQ"

# a API e o worker leem DATABASE_URL: aponta para o banco restaurado so neste processo
export DATABASE_URL="$URL_APP"
$UV python -m worker.excluir_conta reaplicar --registro "$REGISTRO_EXCLUSOES"
# shellcheck disable=SC2086
$UV python -m worker.conferir_restauracao ${CONFERIR_ARGS:-}
