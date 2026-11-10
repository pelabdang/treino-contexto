---
tipo: modulo
status: em-uso
dono: duda
atualizado: 2026-11-09
links: [[decisoes/0011-linha-de-base-e-semana-padrao]], [[decisoes/0010-carga-de-treino]], [[decisoes/0009-treino-de-transicao]], [[produto/meta-3-como-rodar]], [[modulos/api]], [[modulos/mobile]], [[decisoes/0004-contrato-tela-evolucao]], [[decisoes/0006-upload-de-fit]], [[decisoes/0007-clima-da-atividade]], [[produto/meta-4-como-rodar]], [[decisoes/0008-deteccao-de-esforcos]]
---
# Módulo: api-client

## Para que serve
Pacote TypeScript `@treino/api-client` (`packages/api-client/`) com os tipos gerados do OpenAPI da [[modulos/api]] e
as funções `buscarEvolucaoTiros1km`, `buscarAtividade`, `buscarCarga` e `enviarAtividadeFit`. O [[modulos/mobile]] usa o pacote para ler o JSON dos tiros sem escrever tipo à
mão. Contrato e decisões em [[decisoes/0004-contrato-tela-evolucao]] (item 6).

## Entradas e saídas
- `buscarEvolucaoTiros1km(atletaId, {inicio?, fim?}, {baseUrl?, fetch?})` devolve `Promise<Resultado>`; nunca lança:
  - `{ok: true, dados}` com `EvolucaoTiros1km` tipado (`200`);
  - `{ok: false, erro}` com `erro.tipo`: `nao_encontrado` (`404`, `detalhe: {detail}`), `validacao` (`422`, `detalhe` no
    formato do FastAPI), `http` (outro status ou corpo que não é JSON) ou `rede` (falha do `fetch`, com `mensagem`).
- `baseUrl` padrão `http://localhost:8000`; `fetch` padrão é o global (troque nos testes). O app passa `config.apiUrl`.
- Também exporta `EsforcosAtividade` e `BlocoEsforco` (o objeto `esforcos` da atividade, #167, [[decisoes/0008-deteccao-de-esforcos]]) e os tipos `EvolucaoTiros1km`, `SessaoTiros`, `TiroSessao`, `Eixos`, `ErroApi` e `TransicaoAtividade`, `TreinosDeTransicao`, `GrupoTransicao`, `ParteTransicao` e `ComparacaoTransicao` (treino de transição, #170: só tipos, sem função; a tela vem depois), `Atividade`, `ClimaAtividade` e `EstadoClima` (a atividade do `GET /atletas/{atleta_id}/atividades/{atividade_id}` com o `clima` da [[decisoes/0007-clima-da-atividade]]; use `buscarAtividade`), `RespostaUploadFit` (alias de `UploadFitOut`, a resposta do `POST /atletas/{atleta_id}/atividades/fit` da [[modulos/api]], [[decisoes/0006-upload-de-fit]]), além de `components` e
  `operations` do `schema.d.ts`.
- `buscarAtividade(atletaId, atividadeId, {baseUrl?, fetch?})` faz o `GET /atletas/{id}/atividades/{id}` (#159) e devolve `Resultado<Atividade>` com os campos prontos (`data_local`, `hora_local`, `duracao`, `pace_medio`, `distancia`, `clima.atribuicao`); `404` vira `nao_encontrado`, `422` vira `validacao`, outros status `http`, falha do `fetch` `rede`. Nunca lança. Testes em `apps/mobile/__tests__/TelaTreino.test.tsx`.
- Tipo e linha de base da atividade (#266): `Atividade` ganha `tipo_treino`, `tipo_origem`, `tipo_confirmado`, `tipo_divergencia` e `linha_base`; tipos exportados `LinhaBase`, `MetricaLinhaBase`, `EstadoMetricaLinhaBase`, `DivergenciaTipo` e `OrigemTipo`. Textos prontos: o app não monta frase nem arredonda. Contrato em [[modulos/api]].
- Check-in pós-treino (#296, [[decisoes/0012-check-in-pos-treino]]): só tipos, sem função (a tela é da #299). `Checkin` (resposta de `registrarCheckin` e `checkinDaAtividade`), `CheckinEnvio` (corpo do `PUT`), `AtalhoCheckin`, `CheckinsPendentes` e `CheckinPendente` (a lista da #298, sem campo do check-in). `Atividade` ganha `checkin`, `carga_pse` (`CargaPse`), `checkin_aberto` e `pse_sugerida`. O `422` das rotas de check-in traz só `loc`, `msg` e `type` (sem `input` nem `ctx`); os de domínio têm `type` `fora_do_prazo` ou `atividade_sem_checkin`. Contrato em [[modulos/api]].
- `buscarCarga(atletaId, {inicio?, fim?}, {baseUrl?, fetch?})` (#142) faz o `GET /atletas/{id}/carga` e devolve `Resultado<SerieCarga>` (mesmos erros de `buscarAtividade`). Também exporta `CargaAtividade` (o objeto `carga` da atividade; `estado` `calculada`, `sem_carga` ou `pendente`, e `versao` `null` em `pendente`), `SerieCarga`, `DiaCarga`, `TotaisCarga` e `MotivoSemCarga`. Contrato em [[modulos/api]], "Carga".
- Semana-padrão (#264, [[decisoes/0011-linha-de-base-e-semana-padrao]]): só tipos, sem função (a tela é da #267). `SemanaPadrao` (resposta do `GET`), `SemanaPadraoVigente`, `SemanaPadraoItem`, `SemanaPadraoVigencia`, `SemanaPadraoEnvio` (corpo do `PUT`) e `SemanaPadraoGravada` (resposta do `PUT`, com `atividades_reaplicadas`, o que a #265 reaplica). `operations` traz `semanaPadraoDoAtleta` e `gravarSemanaPadrao`. Contrato em [[modulos/api]], "Semana-padrão".
- `enviarAtividadeFit(atletaId, arquivo, {baseUrl?, fetch?, nome?})` faz o `POST /atletas/{id}/atividades/fit` (multipart, campo `arquivo`; ver [[modulos/api]], "Upload de FIT") e nunca lança. `arquivo` é `ArquivoFit`: `Blob`/`File` (web; `nome` dá o nome do arquivo) ou `{uri, name, type}` (React Native).
  - `{ok: true, dados: {criada, resposta}}`: `criada` é `true` no `201` e `false` no `200`; `resposta` é `RespostaUploadFit`.
  - `{ok: false, erro}`: `404` vira `nao_encontrado`, `422` vira `validacao`; os demais status (`400`, `413`...) viram `http` com `status` e `detail?` (o `detail` string do corpo `Erro`, quando houver); falha do `fetch` vira `rede`.
  - Também exporta `ArquivoFit` e `SucessoUploadFit`.
- O pacote não formata pace nem escolhe escala: tudo vem pronto da API.

## Arquivos principais
- `packages/api-client/openapi.json`: o OpenAPI de `app.main`, versionado (gerado, não edite).
- `packages/api-client/src/schema.d.ts`: tipos gerados pelo [openapi-typescript](https://github.com/openapi-ts/openapi-typescript)
  (MIT, gratuito). A primeira linha leva o `openapi-sha256` do `openapi.json` de onde saiu.
- `packages/api-client/src/index.ts`: as funções e os tipos de erro e de upload (escritos à mão).
- `packages/api-client/exemplos/evolucao-tiros-1km.json`: resposta real do endpoint com as fixtures sintéticas (atleta 1), gerada por script.
- `packages/api-client/exemplos/atividade-esforcos.json`: a atividade com `esforcos` (FIT sintético da #161 mais uma corrida de histórico), gerada pelo mesmo script.
- `packages/api-client/exemplos/treinos-de-transicao.json`: a listagem de treinos de transição (#170), com quatro atividades inventadas (dois treinos ciclismo>corrida), gerada pelo mesmo script.
- `packages/api-client/exemplos/carga.json`: a série de carga das fixtures sintéticas da #137, gerada pelo mesmo script.
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
mesmos arquivos (`openapi.json`, os quatro exemplos e `schema.d.ts`). O `npm install` só é preciso na primeira vez (o `node_modules` do pacote fica fora do git).

## Depende de
- [[modulos/api]] (schema e fixtures). O [[modulos/mobile]] depende deste pacote: `"@treino/api-client": "file:../../packages/api-client"` em `apps/mobile/package.json`.
- Jest do app precisa de `moduleDirectories` com `<rootDir>/node_modules` (o pacote fica fora de `apps/mobile`).

## Como testar
- `uv run pytest -q`: `test_contrato_cliente.py` falha com a mensagem "desatualizado... Regere com: <comando>" se
  `openapi.json`, os exemplos ou o carimbo do `schema.d.ts` não batem com o `app.main`.
- `cd apps/mobile && npm test`: `__tests__/api-client.test.ts` cobre o cliente com `fetch` falso (`200`, `404`, `422`, rede, outros erros) e o upload (`201`, `200`, `400`, `404`, `413`, `422`, rede).

## Pendências
- A atividade com clima só tem tipos; a função de busca nasce quando o app precisar (Meta 4). Para ver o JSON, veja o `curl` em [[produto/meta-4-como-rodar]].
- Só o endpoint JSON da evolução dos tiros tem função (o PNG não é chamado pelo app).
- A tela que usa o cliente é a #69/#70 ([[modulos/mobile]]).
- `npm audit` aponta um aviso moderado de `minimatch` dentro do `openapi-typescript`, só na geração (ferramenta de desenvolvimento, não vai para o app).
