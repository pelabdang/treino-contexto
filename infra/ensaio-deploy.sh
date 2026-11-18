#!/usr/bin/env bash
# Ensaio local do deploy do piloto (issue #504, ADR 0016, item 10): sobe a MESMA imagem do servidor com um Postgres descartavel e confere o que
# o criterio de pronto pede, sem conta nem rede de provedor e sem dado real: migracao, /health, /docs desligado, login, 401 sem sessao,
# upload acima de 10 MB recusado e log sem query string, senha nem marca.   Rode da raiz do repositorio:   infra/ensaio-deploy.sh
set -euo pipefail
cd "$(dirname "$0")/.."
F=infra/docker-compose.ensaio-deploy.yml
API=http://localhost:8090
MARCA="MARCA-SINTETICA-NO-LOG"
SENHA="senha-de-ensaio-123"
dc() { docker compose -f "$F" "$@"; }
cleanup() { dc down -v >/dev/null 2>&1 || true; rm -f /tmp/ensaio-grande.fit; }
trap cleanup EXIT
falha() { echo "FALHOU: $1" >&2; exit 1; }
codigo() { curl -s -o /dev/null -w '%{http_code}' "$@"; }

dc up -d --build >/dev/null 2>&1
for _ in $(seq 1 60); do [ "$(codigo "$API/health")" = 200 ] && break; sleep 1; done
[ "$(codigo "$API/health")" = 200 ] || falha "/health"
echo "ok  migracao e API no ar (/health 200)"

for p in /docs /redoc /openapi.json; do [ "$(codigo "$API$p")" = 404 ] || falha "$p deveria dar 404 em producao"; done
echo "ok  /docs, /redoc e /openapi.json desligados"

[ "$(codigo "$API/atletas/1/carga")" = 401 ] || falha "rota de dado sem sessao deveria dar 401"
echo "ok  rota de dado sem sessao: 401"

dc run --rm -T -v "$PWD/tests/fixtures:/fixtures:ro" worker python -m worker.carregar_professor --fixtures /fixtures/professor_piloto >/dev/null 2>&1
echo "$SENHA" | dc run --rm -T worker python -m worker.conta criar --email ensaio@exemplo.com --atleta 1 --senha-stdin >/dev/null 2>&1
TOKEN=$(curl -s -X POST "$API/sessao?segredo=$MARCA" -H 'content-type: application/json' \
  -d "{\"email\":\"ensaio@exemplo.com\",\"senha\":\"$SENHA\"}" | python3 -c 'import sys,json; print(json.load(sys.stdin)["token"])')
[ "$(codigo -H "Authorization: Bearer $TOKEN" "$API/atletas/1/carga")" = 200 ] || falha "login e leitura do proprio dado"
[ "$(codigo -H "Authorization: Bearer $TOKEN" "$API/atletas/2/carga")" = 404 ] || falha "dado de outro atleta deveria dar 404"
echo "ok  login, leitura do proprio dado (200) e do dado de outro (404)"

head -c 11000000 /dev/zero > /tmp/ensaio-grande.fit
[ "$(codigo -X POST "$API/atletas/1/atividades/fit?segredo=$MARCA" -H "Authorization: Bearer $TOKEN" -F "arquivo=@/tmp/ensaio-grande.fit")" = 413 ] \
  || falha "upload acima de 10 MB deveria dar 413"
echo "ok  upload de 11 MB recusado (413)"

codigo -X PUT "$API/atletas/1/semana-padrao" -H "Authorization: Bearer $TOKEN" -H 'content-type: application/json' -d "{\"senha\":\"$MARCA\"}" >/dev/null
LOG="$(dc logs api 2>&1)"
echo "$LOG" | grep -q "app.acesso acesso POST /sessao 200" || falha "linha de acesso ausente no log"
if echo "$LOG" | grep -q -e "$MARCA" -e "$SENHA" -e "$TOKEN" -e "segredo="; then falha "log com query string, senha, token ou marca"; fi
echo "ok  log com metodo, caminho e status; sem query string, senha, token nem marca"
echo "ensaio completo: tudo ok"
