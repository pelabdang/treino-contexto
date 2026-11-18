#!/usr/bin/env bash
# Ensaio local da restauracao (issue #505, ADR 0016, item 9): Postgres 16 descartavel no Docker, dado SINTETICO, backup cifrado,
# exclusao DEPOIS do backup, restauracao para um banco novo, reaplicacao da exclusao e conferencia. Sem dado real, sem rede alem do Docker.
#
#   infra/backup/ensaio-local.sh          # roda da raiz do repositorio; precisa de docker, pg_dump/pg_restore 16, age e uv
#
# Imprime o registro do ensaio (data, tamanho do backup, contagem por tabela antes e depois). Apaga tudo o que criou ao final.
set -euo pipefail

RAIZ="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$RAIZ"
NOME="treino-ensaio-505-$$"
PORTA="${PORTA_ENSAIO:-5442}"
TMP="$(mktemp -d)"
cleanup() { docker rm -f "$NOME" >/dev/null 2>&1 || true; rm -rf "$TMP"; }
trap cleanup EXIT

SENHA_DB="ensaio"
base="postgresql://postgres:${SENHA_DB}@localhost:${PORTA}"
docker run -d --name "$NOME" -e POSTGRES_PASSWORD="$SENHA_DB" -p "${PORTA}:5432" postgres:16 >/dev/null
for _ in $(seq 1 40); do
  docker exec "$NOME" pg_isready -U postgres >/dev/null 2>&1 && break
  sleep 0.5
done
sleep 1
docker exec "$NOME" psql -U postgres -qc "CREATE DATABASE origem" -c "CREATE DATABASE restaurado"

app() { echo "${base/postgresql:/postgresql+psycopg:}/$1"; }

echo "== 1. banco de origem: migracoes e dado sintetico"
export DATABASE_URL="$(app origem)"
(cd services/api && uv run alembic upgrade head >/dev/null 2>&1)
uv run python -m worker.importar_garmin tests/fixtures/garmin/exportacao_minima.zip --atleta "Atleta Sintetico Um" >/dev/null
uv run python -m worker.importar_garmin tests/fixtures/garmin/exportacao_minima.zip --atleta "Atleta Sintetico Dois" >/dev/null
SENHA_CONTA="senha-sintetica-ensaio-1"
echo "$SENHA_CONTA" | uv run python -m worker.conta criar --email um@exemplo.com --atleta 1 --senha-stdin >/dev/null
echo "$SENHA_CONTA" | uv run python -m worker.conta criar --email dois@exemplo.com --atleta 2 --senha-stdin >/dev/null
uv run python -m worker.conferir_restauracao > "$TMP/antes.txt"

echo "== 2. backup cifrado"
age-keygen -o "$TMP/chave.txt" 2>/dev/null
PUBLICA="$(grep -o 'age1[a-z0-9]*' "$TMP/chave.txt" | head -1)"
DATABASE_URL="$(app origem)" BACKUP_DIR="$TMP/backups" BACKUP_RECIPIENT="$PUBLICA" infra/backup/backup.sh | tee "$TMP/backup.txt"
ARQUIVO="$(ls "$TMP"/backups/treino-*.dump.age)"
if head -c 5 "$ARQUIVO" | grep -q "PGDMP"; then echo "ERRO: o backup nao esta cifrado" >&2; exit 1; fi

echo "== 3. exclusao do atleta 2 DEPOIS do backup (registro fora do banco)"
uv run python -m worker.excluir_conta excluir --atleta 2 --confirmar 2 --registro "$TMP/exclusoes.jsonl" | grep -E "^(atleta|conta|atividade):"

echo "== 4. restauracao para um banco NOVO, reaplicacao e conferencia"
BACKUP_ARQUIVO="$ARQUIVO" BACKUP_CHAVE="$TMP/chave.txt" RESTAURAR_URL="${base}/restaurado" REGISTRO_EXCLUSOES="$TMP/exclusoes.jsonl" \
  CONFERIR_ARGS="--email um@exemplo.com" infra/backup/restaurar.sh < <(echo "$SENHA_CONTA") | tee "$TMP/depois.txt"

echo "== registro do ensaio (sem dado pessoal)"
echo "data: $(date -u +%Y-%m-%d)"
cat "$TMP/backup.txt"
echo "-- contagem por tabela: origem (antes) -> restaurado (depois da reaplicacao)"
paste -d' ' <(sed 's/linhas=//' "$TMP/antes.txt") <(grep 'linhas=' "$TMP/depois.txt" | sed 's/.*linhas=//') | awk '{print $1, $2, "->", $3}'
grep -q "login: ok" "$TMP/depois.txt" && echo "login de uma conta no banco restaurado: ok"
