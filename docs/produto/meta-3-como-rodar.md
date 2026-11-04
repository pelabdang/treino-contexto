---
tipo: guia
status: em-uso
dono: nina
atualizado: 2026-11-03
links: [[produto/meta-2-como-rodar]], [[produto/meta-1-como-reproduzir]], [[decisoes/0006-upload-de-fit]], [[modulos/ingestao-garmin]], [[modulos/api]], [[modulos/api-client]], [[modulos/mobile]], [[modulos/worker]], [[modulos/infra]], [[diario/2026-11-03]]
---
# Meta 3: como rodar o upload de FIT

Passo a passo do upload de um `.fit` com os FIT sintéticos de `tests/fixtures/garmin/fit/`: Postgres, migrações,
fixtures, API com `FIT_DIR` temporária, app na web e envio pelo botão. Só dado sintético. A base é a mesma do
[[produto/meta-2-como-rodar]]; as regras do upload estão na [[decisoes/0006-upload-de-fit]].

**Situação da verificação (#97, complementada na #98):** a Nina rodou de verdade os passos 1 a 4 (Postgres, migrações, fixtures, API) e
**todos os `curl` do passo 5**, inclusive o `apagar_fit` (passo 7). Rodou também o `npm install` e o `expo start --web`
(a porta 8081 respondeu `200`). O clique no botão no navegador não foi rodado na #97: o envio pela tela foi verificado na
#96 (`201`, de 2 para 3 sessões) e o clique foi rodado de verdade na #98 (veja "Verificado na #98" abaixo). Os estados `413` e rede na tela estão cobertos pelo `npm test`
(`__tests__/BotaoEnviarFit.test.tsx`); o `404` e o `413` na API, pelo `curl`.

**Verificado na #98 (Bia, 03/11):** o clique no botão foi rodado no Chrome, com banco `treino-qa98` (Postgres 5441), API com `FIT_DIR` temporária e app na web, só com FIT sintético. Resultados na tela: `201` "Atividade adicionada" (série de 2 para 3 sessões, a nova em 01/04/25, 4:06 min/km), `200` "Essa atividade já estava aqui" no reenvio e na mesma atividade da exportação (sem duplicar: 6 atividades no banco), `400` "FIT inválido ou corrompido", `400` "o arquivo é um FIT, mas não é uma atividade", `400` "o arquivo precisa ter extensão .fit" e `413` "arquivo acima de 10 MB". O seletor nativo do Chrome não é acessível à automação: o `File` foi montado em JavaScript com os bytes do FIT sintético e o evento `change` foi disparado no input que o botão cria (como na #96). Em `FIT_DIR` ficaram só `<atleta_id>/<sha256>.fit`, e `git status` não mostrou a pasta (`dados-upload/` está no `.gitignore`). O `404` na tela, a rede fora do ar e iOS/Android (sem aparelho) **não foram verificados** na #98. O teste automatizado é `tests/test_e2e_meta3.py`. Print do `201`, com a série em 3 sessões: ![[_anexos/meta-3-qa-201-serie.jpg]]

**Tradutor do Chrome:** o app declara `lang="pt-BR"` no HTML da web (`apps/mobile/src/app/+html.tsx`, com `web.output: "static"` no `app.json`), então o Chrome não oferece tradução e não é mais preciso desligá-la nem usar proxy. Antes (#96, #98) o `index.html` saía com `lang="en"` e o tradutor mudava as mensagens.

## Antes de começar
- `git`, `uv`, Docker (Compose 2.24 ou mais novo), Node e `curl`.
- Três terminais: API, app e um livre. Comandos na **raiz** do repositório, salvo indicação.
- **Não use o banco do seu dia a dia.** Rode sempre com `-p treino-meta3` (volume `treino-meta3_pgdata`, separado).
  Sem `-p`, o `docker compose` usa o volume `treino-contexto_pgdata`.
- Escolha uma **porta livre** para o Postgres. O padrão do compose é a 5433 (a 5432 costuma ter um Postgres nativo, erro `role "treino" does not exist`). Confira com
  `docker ps` e `lsof -iTCP:<porta> -sTCP:LISTEN`. Abaixo, a 5440.

## Passo a passo
1. **Subir o Postgres** (porta 5440, override pelo stdin, sem editar o repositório):
   ```
   docker compose -p treino-meta3 -f infra/docker-compose.yml -f - up -d <<'EOF'
   services:
     postgres:
       ports: !override
         - "5440:5432"
   EOF
   export DATABASE_URL="postgresql+psycopg://treino:treino@localhost:5440/treino"
   ```
   Esperado: `treino-meta3-postgres-1` com status `healthy` (`docker compose -p treino-meta3 -f infra/docker-compose.yml ps`).
   Se a 5433 estiver livre, pode tirar o override e usar a porta 5433 na URL. Use o mesmo terminal nos passos 2 a 4.
2. **Instalar e migrar:**
   ```
   uv sync
   (cd services/api && uv run alembic upgrade head)
   ```
   Esperado: três linhas `Running upgrade`, até a `0003`.
3. **Importar as fixtures** (dão ao atleta 1 as sessões de 04/03/25 e 11/03/25, [[modulos/ingestao-garmin]]):
   ```
   uv run python -m worker.importar_garmin tests/fixtures/garmin/exportacao_minima.zip --atleta "Atleta Fictício"
   ```
   Esperado: `inseridas=5 atualizadas=0 ignoradas=0 avisos=1`.
4. **Subir a API com `FIT_DIR` numa pasta temporária** (terminal 1):
   ```
   export FIT_DIR="$(mktemp -d)"
   CORS_ORIGENS=http://localhost:8081 uv run uvicorn app.main:app --app-dir services/api --port 8000
   ```
   A API demora alguns segundos. Sem `FIT_DIR`, os FIT vão para `dados-upload/fit/` (fora do git), que é dado pessoal
   de saúde quando o FIT é real. Com FIT sintético, a pasta temporária evita deixar lixo no repositório. Confira com `curl localhost:8000/health`.
5. **Enviar pelo `curl`** (terminal livre; `F=tests/fixtures/garmin/fit`). Cada linha abaixo foi rodada; o resultado é o esperado:

   | Estado | Como forçar | Resposta |
   |---|---|---|
   | `201` novo | `curl -si -F arquivo=@$F/upload_intervalado_5x1km.fit localhost:8000/atletas/1/atividades/fit` | `{"resultado":"inserida","atividade_id":6,"avisos":[]}` |
   | `200` reenvio | o mesmo comando de novo | `{"resultado":"ignorada","atividade_id":6,...}` |
   | `200` mesma atividade da exportação | `-F arquivo=@$F/upload_mesma_atividade_1000000001.fit` | `{"resultado":"atualizada","atividade_id":1,...}` (regra dos 60 s) |
   | `400` truncado | `-F arquivo=@$F/upload_truncado.fit` | `{"detail":"FIT inválido ou corrompido"}` |
   | `400` não é atividade | `-F arquivo=@$F/upload_nao_atividade.fit` | `{"detail":"o arquivo é um FIT, mas não é uma atividade"}` |
   | `400` extensão errada | copie um FIT para `treino.txt` e envie `-F arquivo=@treino.txt` | `{"detail":"o arquivo precisa ter extensão .fit"}` |
   | `404` atleta | troque `/atletas/1/` por `/atletas/99/` | `{"detail":"atleta não encontrado"}` |
   | `413` grande | `head -c 10485761 /dev/zero > grande.fit` e envie `-F arquivo=@grande.fit` | `{"detail":"arquivo acima de 10 MB"}` |
   | `422` sem campo | `-F outro=x` | `detail` em lista (formato do FastAPI) |

   Os dois últimos FIT da pasta entram no banco e ficam fora da série: `upload_esteira_4x1km.fit` (esteira) e
   `upload_natacao_400m.fit` (natação) dão `201` e não mudam o gráfico (rodados). `upload_rodagem_6km.fit` (rodagem,
   não é tiro) também fica fora da série (coberto pelo teste das fixtures, não rodado aqui). Para conferir: `curl localhost:8000/atletas/1/evolucao/tiros-1km` deve ter **3 sessões** depois do primeiro envio (a nova é 01/04/25).
   O `-si` mostra o status; sem ele, use `-w ' [%{http_code}]\n'`.
6. **Subir o app na web e enviar pelo botão** (terminal 2):
   ```
   cd apps/mobile
   cp .env.example .env.local
   npm install
   npx expo start --web --port 8081
   ```
   Abra `http://localhost:8081`. No alto da tela está o botão "Enviar arquivo FIT" ([[modulos/mobile]]). Toque, escolha o arquivo no seletor e
   veja a mensagem. Como forçar cada estado na tela:
   - **`201`** "Atividade adicionada": envie `upload_intervalado_5x1km.fit` (banco sem ele). O gráfico passa de 2 para 3 sessões.
   - **`200`** "Essa atividade já estava aqui": envie o mesmo arquivo de novo.
   - **`400`**: envie `upload_truncado.fit`, `upload_nao_atividade.fit` ou qualquer arquivo sem `.fit` (por exemplo, o `treino.txt`). A tela mostra o `detail` da API.
   - **`404`** "atleta não encontrado": em `.env.local` ponha `EXPO_PUBLIC_ATLETA_ID=99` e **reinicie o `expo`**; envie qualquer FIT. (A tela de evolução também mostra "Atleta não encontrado".)
   - **`413`**: envie um arquivo `grande.fit` de mais de 10 MB (o `head -c 10485761 /dev/zero > grande.fit` do passo 5).
   - **Rede**: derrube a API (`Ctrl+C` no terminal 1) e envie. Aparece "Não foi possível falar com o servidor. Verifique a conexão e tente de novo." Religue a API e envie de novo.
   - Para voltar ao estado `201`, apague os FIT e as atividades do envio: veja o passo 7 e "Encerrar e limpar".

   **Chrome:** não é mais preciso desligar a tradução. O HTML da web sai com `lang="pt-BR"` (#119) e o Chrome não
   oferece tradutor; as mensagens aparecem como escritas.
   **Não commite o `apps/mobile/tsconfig.json`:** o `expo start` o reescreve; descarte com `git checkout apps/mobile/tsconfig.json`.
7. **Apagar os FIT guardados** (rodado: apagou 4 arquivos e limpou `arquivo_bruto` em 4 atividades; as atividades e a série ficam):
   ```
   uv run python -m worker.apagar_fit --atleta-id 1
   ```
   Saída: `apagados 4 arquivos; arquivo_bruto limpo em 4 atividades do atleta 1`. Rodar de novo é seguro (`apagados 0 ...`).
   Atleta inexistente (`--atleta-id 99`): mensagem em stderr e saída 1. Use a mesma `FIT_DIR` da API. Veja [[modulos/worker]].
   Isto não desfaz o `201`: para reenviar como "novo", recrie o banco (`down -v` e passo 1).

## Encerrar e limpar
- `Ctrl+C` na API e no Expo; apague a pasta de `FIT_DIR` (`rm -rf "$FIT_DIR"`) e os arquivos `treino.txt` e `grande.fit`.
- Apagar o banco de vez (só o projeto `treino-meta3`): `docker compose -p treino-meta3 -f infra/docker-compose.yml down -v`.

## Problemas comuns
- **`connection refused` no `curl`:** a API ainda está subindo; espere e repita.
- **Porta ocupada no `up`:** escolha outra porta no override e ajuste a `DATABASE_URL`.
- **Tudo cai no banco errado:** você esqueceu o `-p treino-meta3` ou o `export DATABASE_URL` neste terminal.
- **Rodou o passo 5 duas vezes e o `201` virou `200`:** é o esperado (idempotência). Recrie o banco para repetir.
- **Navegador bloqueia o `POST`:** o app tem de estar em `http://localhost:8081`, a origem de `CORS_ORIGENS` ([[modulos/api]]).
- **Celular no Expo Go:** `localhost` é o próprio aparelho; use o IP do computador em `EXPO_PUBLIC_API_URL` ([[modulos/infra]]).

## Testes
`uv run pytest -q` na raiz e `npm test` em `apps/mobile`.
