---
tipo: guia
status: em-uso
dono: nina
atualizado: 2026-11-03
links: [[produto/metas/meta-2-evolucao-tiros-app]], [[produto/meta-1-como-reproduzir]], [[modulos/api]], [[modulos/mobile]], [[modulos/infra]], [[modulos/worker]], [[modulos/api-client]], [[decisoes/0004-contrato-tela-evolucao]]
---
# Meta 2: como rodar a API e o app

Passo a passo de ponta a ponta, num clone limpo: Postgres, migrações, fixtures sintéticas, API com CORS e app na web.
Só dado sintético. Nada de dado real. Parte da base está em [[produto/meta-1-como-reproduzir]].

**Situação da verificação (#71):** os passos 1 a 6 foram rodados de verdade pela Nina, com o resultado abaixo.
O passo 7 (ver a tela com as sessões) **não foi verificado nesta issue; a conferência visual é da #72 (QA da Bia)**.

## Antes de começar
- `git`, `uv`, Docker (Compose 2.24 ou mais novo), Node e `curl`.
- Três terminais: um para a API, um para o app e um livre. Comandos na **raiz** do repositório, salvo indicação.

## Atenção com o banco (leia antes do passo 1)
- O `infra/docker-compose.yml` tem `name: treino-contexto`. Rodar `docker compose` **sem `-p`** usa o volume
  `treino-contexto_pgdata`. Se você já tem um banco local do projeto (por exemplo com dado real), o `up` reusa esse
  volume e a importação das fixtures cai **dentro dele**.
- Por isso, para o roteiro com fixtures, use sempre um projeto próprio: `-p treino-meta2`. O volume vira
  `treino-meta2_pgdata`, separado.
- Se a porta 5432 estiver ocupada (outro Postgres, ou outro container), use o override de porta pelo stdin,
  sem editar o repositório e sem arquivo fora dele (passo 1, variante B).

## Passo a passo
1. **Subir o Postgres.**
   - Variante A (porta 5432 livre):
     ```
     docker compose -p treino-meta2 -f infra/docker-compose.yml up -d
     export DATABASE_URL="postgresql+psycopg://treino:treino@localhost:5432/treino"
     ```
   - Variante B (5432 ocupada; aqui a 5439):
     ```
     docker compose -p treino-meta2 -f infra/docker-compose.yml -f - up -d <<'EOF'
     services:
       postgres:
         ports: !override
           - "5439:5432"
     EOF
     export DATABASE_URL="postgresql+psycopg://treino:treino@localhost:5439/treino"
     ```
   Esperado: container `treino-meta2-postgres-1` com status `healthy` (`docker compose -p treino-meta2 -f infra/docker-compose.yml ps`).
   O `export` vale só para o terminal aberto: use o mesmo terminal nos passos 2 a 4 e 5.
2. **Instalar e migrar** (o `alembic` roda dentro de `services/api`):
   ```
   uv sync
   (cd services/api && uv run alembic upgrade head)
   ```
   Esperado: três linhas `Running upgrade`, até a `0003`.
3. **Importar as fixtures** ([[modulos/ingestao-garmin]], [[modulos/worker]]):
   ```
   uv run python -m worker.importar_garmin tests/fixtures/garmin/exportacao_minima.zip --atleta "Atleta Fictício"
   ```
   Esperado: `inseridas=5 atualizadas=0 ignoradas=0 avisos=1` (o aviso é da esteira sem FIT, atividade `1000000005`).
   Rodando de novo, a importação é idempotente: `inseridas=0 atualizadas=0 ignoradas=5 avisos=1`.
4. **Subir a API com CORS para o app web** (terminal 1, mesmo `DATABASE_URL`):
   ```
   CORS_ORIGENS=http://localhost:8081 uv run uvicorn app.main:app --app-dir services/api --port 8000
   ```
   A API **demora alguns segundos** para responder depois do comando (o `uv run` pode levar mais de 4 s). Se o
   `curl` do passo 5 der "connection refused", espere e repita.
5. **Conferir a API** (terminal livre):
   ```
   curl localhost:8000/health
   curl "localhost:8000/atletas/1/evolucao/tiros-1km"
   curl -si -H "Origin: http://localhost:8081" localhost:8000/atletas/1/evolucao/tiros-1km | grep -i -E "^HTTP|access-control"
   curl -si -H "Origin: http://localhost:9999" localhost:8000/atletas/1/evolucao/tiros-1km | grep -i -E "^HTTP|access-control"
   curl localhost:8000/atletas/99/evolucao/tiros-1km
   ```
   Esperado, na ordem:
   - `{"status":"ok"}`;
   - JSON com `"versao_calculo":"tiros_1km@4"`, `"reclassificacao_pendente":false`, bloco `eixos` e 2 sessões;
   - `HTTP/1.1 200 OK` e `access-control-allow-origin: http://localhost:8081` (origem liberada);
   - `HTTP/1.1 200 OK` **sem** `access-control-allow-origin` (origem fora da lista: o navegador bloqueia);
   - `{"detail":"atleta não encontrado"}` (404).
6. **Subir o app na web** (terminal 2):
   ```
   cd apps/mobile
   cp .env.example .env.local
   npm install
   npx expo start --web --port 8081
   ```
   `.env.local` traz `EXPO_PUBLIC_API_URL=http://localhost:8000` e `EXPO_PUBLIC_ATLETA_ID=1`; reinicie o `expo` ao
   mudar. Esperado: o Metro diz `Waiting on http://localhost:8081`, a porta responde 200 e o bundle web é
   gerado (cerca de 856 módulos). A porta tem de ser a `8081`, a mesma de `CORS_ORIGENS`.
   Com `CI=1` o Expo não recarrega sozinho; sem `CI`, abre o menu interativo.
   **Não commite o `apps/mobile/tsconfig.json`:** o `expo start` o reescreve (reformata e tira `.expo/types/**/*.ts` e
   `expo-env.d.ts` do `include`). Descarte com `git checkout apps/mobile/tsconfig.json`.
7. **Ver a tela** em `http://localhost:8081`: "Evolução dos tiros de 1 km" com as 2 sessões (04/03/25 e 11/03/25).
   Valores: 6 x 1 km, `4:11`, 170,3 bpm; 5 x 1 km, `3:57`, 171,8 bpm ([[produto/meta-1-como-reproduzir]]).
   **Não verificado nesta issue; a conferência visual é da #72 (QA da Bia).** O `npm test` do app cobre os estados com
   `fetch` falso ([[modulos/mobile]]).

## Encerrar e limpar
- `Ctrl+C` na API e no Expo.
- Parar mantendo os dados: `docker compose -p treino-meta2 -f infra/docker-compose.yml stop`.
- Apagar de vez (só o projeto `treino-meta2`): `docker compose -p treino-meta2 -f infra/docker-compose.yml down -v`.

## Problemas comuns
- **App mostra erro de rede:** a API não subiu ainda, ou o app não está na porta 8081 (CORS).
- **Mudei a regra e o JSON diz `reclassificacao_pendente: true`:** veja "Reclassificar" em [[modulos/api]].
- **Celular no Expo Go:** `localhost` é o próprio aparelho; use o IP do computador em `EXPO_PUBLIC_API_URL` e
  inclua a origem do app em `CORS_ORIGENS` quando for web. iOS e Android não precisam de CORS ([[modulos/infra]]).
- **Tudo sem script fora do repositório:** o override de porta vai pelo stdin do `docker compose`.

## Testes
`uv run pytest -q` na raiz e `npm test` em `apps/mobile`.
