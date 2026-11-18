#!/usr/bin/env bash
# Backup do banco do piloto: pg_dump no formato custom, CIFRADO com age (so a chave publica fica no servidor) e retencao de 7 dias.
# Issue #505, ADR 0016, item 9. Backup guarda dado de saude: vale a mesma regra do banco (acesso restrito, mesma regiao, nunca no git).
#
#   DATABASE_URL=postgresql://...   BACKUP_DIR=/pasta/segura   BACKUP_RECIPIENT=age1...   infra/backup/backup.sh
#
# Variaveis: DATABASE_URL (URL libpq do banco), BACKUP_DIR (pasta do backup), BACKUP_RECIPIENT (chave PUBLICA age; a privada fica
# fora do servidor), RETENCAO_DIAS (padrao 7), PG_DUMP (padrao pg_dump). Nunca grava dump sem cifra: sem BACKUP_RECIPIENT, para.
# Saida: so o nome e o tamanho do arquivo, nunca a URL (tem senha).
set -euo pipefail

: "${DATABASE_URL:?defina DATABASE_URL}"
: "${BACKUP_DIR:?defina BACKUP_DIR}"
if [ -z "${BACKUP_RECIPIENT:-}" ]; then
  echo "erro: defina BACKUP_RECIPIENT (chave publica age); backup sem cifra nao e feito" >&2
  exit 2
fi
RETENCAO_DIAS="${RETENCAO_DIAS:-7}"
PG_DUMP="${PG_DUMP:-pg_dump}"

# o .env usa o formato do SQLAlchemy (postgresql+psycopg://); o pg_dump quer o da libpq (postgresql://)
URL_LIBPQ="${DATABASE_URL/postgresql+psycopg:/postgresql:}"

umask 077
mkdir -p "$BACKUP_DIR"
arquivo="$BACKUP_DIR/treino-$(date -u +%Y%m%dT%H%M%SZ).dump.age"
tmp="$arquivo.parcial"
trap 'rm -f "$tmp"' EXIT

"$PG_DUMP" --format=custom --no-owner --no-privileges "$URL_LIBPQ" | age -r "$BACKUP_RECIPIENT" -o "$tmp"
mv "$tmp" "$arquivo"
trap - EXIT

# retencao: apaga o que passou de RETENCAO_DIAS dias (so os arquivos deste padrao)
find "$BACKUP_DIR" -maxdepth 1 -name 'treino-*.dump.age' -type f -mtime +"$((RETENCAO_DIAS - 1))" -delete

tamanho=$(wc -c < "$arquivo" | tr -d ' ')
echo "backup: $(basename "$arquivo") bytes=$tamanho"
