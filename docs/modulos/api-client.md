---
tipo: modulo
status: em-uso
dono: duda
atualizado: 2026-11-03
links: [[modulos/api]], [[modulos/mobile]], [[decisoes/0004-contrato-tela-evolucao]]
---
# Módulo: api-client

## Para que serve
Pacote TypeScript `@treino/api-client` (`packages/api-client/`) com os tipos gerados do OpenAPI da [[modulos/api]] e
a função `buscarEvolucaoTiros1km`. O [[modulos/mobile]] usa o pacote para ler o JSON dos tiros sem escrever tipo à
mão. Contrato e decisões em [[decisoes/0004-contrato-tela-evolucao]] (item 6).

## Entradas e saídas
- `buscarEvolucaoTiros1km(atletaId, {inicio?, fim?}, {baseUrl?, fetch?})` devolve `Promise<Resultado>`; nunca lança:
  - `{ok: true, dados}` com `EvolucaoTiros1km` tipado (`200`);
  - `{ok: false, erro}` com `erro.tipo`: `nao_encontrado` (`404`, `detalhe: {detail}`), `validacao` (`422`, `detalhe` no
    formato do FastAPI), `http` (outro status ou corpo que não é JSON) ou `rede` (falha do `fetch`, com `mensagem`).
- `baseUrl` padrão `http://localhost:8000`; `fetch` padrão é o global (troque nos testes). O app passa `config.apiUrl`.
- Também exporta os tipos `EvolucaoTiros1km`, `SessaoTiros`, `TiroSessao`, `Eixos`, `ErroApi`, além de `components` e
  `operations` do `schema.d.ts`.
- O pacote não formata pace nem escolhe escala: tudo vem pronto da API.

## Arquivos principais
- `packages/api-client/openapi.json`: o OpenAPI de `app.main`, versionado (gerado, não edite).
- `packages/api-client/src/schema.d.ts`: tipos gerados pelo [openapi-typescript](https://github.com/openapi-ts/openapi-typescript)
  (MIT, gratuito). A primeira linha leva o `openapi-sha256` do `openapi.json` de onde saiu.
- `packages/api-client/src/index.ts`: a função e os tipos de erro (escritos à mão).
- `packages/api-client/exemplos/evolucao-tiros-1km.json`: resposta real do endpoint com as fixtures sintéticas (atleta 1), gerada por script.
- `packages/api-client/scripts/carimbar.mjs`: grava o carimbo no `schema.d.ts`.
- `services/api/scripts/exportar_openapi.py`: exporta `openapi.json` (`app.openapi()`, sem servidor) e o exemplo (`TestClient`, SQLite em memória).
- `services/api/tests/test_contrato_cliente.py`: falha se algo estiver desatualizado.

## Como regerar
Sempre que um modelo ou rota da API mudar (qualquer coisa que apareça no OpenAPI ou na resposta de exemplo):
```
uv run python services/api/scripts/exportar_openapi.py
cd packages/api-client && npm install && npm run gerar
```
O primeiro comando grava `openapi.json` e o exemplo; o segundo gera `src/schema.d.ts` e o carimbo. Faça commit dos
quatro arquivos. O `npm install` só é preciso na primeira vez (o `node_modules` do pacote fica fora do git).

## Depende de
- [[modulos/api]] (schema e fixtures). O [[modulos/mobile]] depende deste pacote: `"@treino/api-client": "file:../../packages/api-client"` em `apps/mobile/package.json`.
- Jest do app precisa de `moduleDirectories` com `<rootDir>/node_modules` (o pacote fica fora de `apps/mobile`).

## Como testar
- `uv run pytest -q`: `test_contrato_cliente.py` falha com a mensagem "desatualizado... Regere com: <comando>" se
  `openapi.json`, o exemplo ou o carimbo do `schema.d.ts` não batem com o `app.main`.
- `cd apps/mobile && npm test`: `__tests__/api-client.test.ts` cobre o cliente com `fetch` falso (`200`, `404`, `422`, rede, outros erros).

## Pendências
- Só o endpoint JSON da evolução dos tiros tem função (o PNG não é chamado pelo app).
- A tela que usa o cliente é a #69/#70 ([[modulos/mobile]]).
- `npm audit` aponta um aviso moderado de `minimatch` dentro do `openapi-typescript`, só na geração (ferramenta de desenvolvimento, não vai para o app).
