---
tipo: modulo
status: em-uso
dono: rafa
atualizado: 2026-11-03
links: [[modulos/api]], [[modulos/api-client]], [[produto/roadmap]], [[decisoes/0004-contrato-tela-evolucao]], [[produto/meta-2-como-rodar]], [[decisoes/0006-upload-de-fit]]
---
# Módulo: mobile

## Para que serve
App em React Native com Expo (TypeScript, Expo Router) para iOS, Android e web. Hoje tem a tela "Evolução dos tiros de 1 km" ligada à API (botão "Enviar arquivo FIT", gráfico de dois painéis, lista das sessões e rodapé) e a leitura da configuração. Sem login e sem deploy: roda local, na web e no Expo Go.

O app não calcula pace: todo `m:ss` virá da [[modulos/api]].

## Entradas e saídas
- Entrada: variáveis `EXPO_PUBLIC_API_URL` (padrão `http://localhost:8000`) e `EXPO_PUBLIC_ATLETA_ID` (padrão `1`, o atleta das fixtures), lidas só em `src/config.ts`. Modelo em `apps/mobile/.env.example`; copie para `.env.local` (ignorado pelo git).
- Consome a [[modulos/api]] pelo pacote `@treino/api-client` (`packages/api-client/`, tipos gerados do OpenAPI; ver [[modulos/api-client]]), dependência local `"@treino/api-client": "file:../../packages/api-client"`. Uso: `buscarEvolucaoTiros1km(config.atletaId, {inicio, fim}, {baseUrl: config.apiUrl})`. A tela inicial chama pelo componente `TelaEvolucao`.
- Jest: `package.json` tem `moduleDirectories` com `<rootDir>/node_modules`, para o pacote (fora de `apps/mobile`) achar os helpers do Babel.

## Rotas
| Arquivo | Rota | O que mostra |
|---|---|---|
| `src/app/_layout.tsx` | (raiz) | `Stack` sem cabeçalho |
| `src/app/index.tsx` | `/` | `TelaEvolucao` com `config.apiUrl` e `config.atletaId` |

## Tela de evolução (`TelaEvolucao`)
`src/componentes/TelaEvolucao.tsx` chama `buscarEvolucaoTiros1km` e mostra um estado por vez:
- carregando: "Carregando seus tiros...";
- vazio (`sessoes: []`): "Ainda não há treinos de tiros de 1 km.";
- erro `404`: "Atleta não encontrado"; `422` ou outro status: "Não foi possível carregar os tiros. Tente de novo mais tarde."; rede: "Não foi possível falar com o servidor" com o botão "Tentar de novo";
- sucesso: `GraficoTiros`, lista das sessões (data, `pace_medio`, `fc_media` ou "sem FC", `n_tiros`) e rodapé "cálculo: <versao_calculo>" como texto, mais "cálculo em atualização" quando `reclassificacao_pendente` é `true`. O app nunca compara a versão com um valor fixo.
Testes em `__tests__/index.test.tsx` com `fetch` falso (todos os estados, "9:99" e rótulo de eixo trocados, versão `tiros_1km@9`, aviso de reclassificação). O componente aceita `fetchFn` só para teste.

Rodar com dado sintético: passo a passo em [[produto/meta-2-como-rodar]] (API com fixtures, `CORS_ORIGENS` com `http://localhost:8081` e `npx expo start --web --port 8081`). O `expo start` reescreve `apps/mobile/tsconfig.json`: não commitar.

## Botão "Enviar arquivo FIT" (`BotaoEnviarFit`)
`src/componentes/BotaoEnviarFit.tsx`, no alto da `TelaEvolucao`, usa o mesmo `apiUrl` e `atletaId` da tela. Toque abre o seletor do `expo-document-picker` (`getDocumentAsync`, `type: "*/*"`); na web entrega o `File`, no celular o `uri`. Envia com `enviarAtividadeFit` ([[modulos/api-client]]) e mostra um estado por vez:
- enviando: "Enviando..." e botão desligado;
- `201`: "Atividade adicionada"; `200`: "Essa atividade já estava aqui". Nos dois casos a tela busca a evolução de novo (o gráfico antigo fica visível até a resposta chegar);
- erro: o `detail` da API (`400`, `413`, `404`); falha de rede: "Não foi possível falar com o servidor. Verifique a conexão e tente de novo."; outro erro, mensagem genérica;
- seletor cancelado: nada acontece.
Regras do arquivo (só `.fit`, 10 MB, FIT sintético ou do atleta) são da API ([[decisoes/0006-upload-de-fit]]); o app não valida. Testes em `__tests__/BotaoEnviarFit.test.tsx` (seletor e `fetch` falsos: 201, 200, 400, 413, rede, cancelar).
Verificado na web (#96) com API e Postgres locais, FIT sintético `upload_intervalado_5x1km.fit`: o `POST` devolveu `201` e a tela passou de 2 para 3 sessões (01/04/2025). Obs.: o tradutor automático do Chrome mexe no texto das mensagens (aparecia só "Atividade"); desligue a tradução ao conferir.

## Componente GraficoTiros
`src/componentes/GraficoTiros.tsx` recebe `dados: EvolucaoTiros1km` (tipo de `@treino/api-client`) e desenha dois painéis com o mesmo eixo X (data `dd/mm/aa`, posição proporcional ao tempo): "Pace médio dos tiros (min/km)" em cima e "FC média dos tiros (bpm)" embaixo, um ponto por sessão. Usa `react-native-svg` (gratuito, incluído no Expo Go) para linhas e pontos; rótulos são `Text` nativo.
- Faixa, marcas e rótulos vêm só de `eixos` da API. O app só converte valor em posição na tela; não formata pace nem escolhe escala (ver [[decisoes/0004-contrato-tela-evolucao]]).
- Pace invertido (`eixos.pace.invertido`): pace menor fica no alto.
- A única formatação no app é a data (dd/mm/aa); pace, FC e rótulos vêm prontos da API.
- Sessão sem `fc_media`: sem ponto no painel de FC, com ponto no de pace.
- O toque fica num `Pressable` transparente (32 px) por cima de cada ponto, com o `testID` `toque-<painel>-<atividade_id>`; o `Circle` do SVG não leva `onPress`. Com `onPress` no `Circle`, o `react-native-svg` repassava props de responder (`onResponderTerminate` e outras) ao DOM na web e o React avisava "Unknown event handler property" no modo dev.
- Tocar num ponto mostra data, `pace_medio` e `fc_media` como vieram da API; sem FC na sessão, mostra "FC média: sem FC".
- Mensagens de "sem dados":
  - "Sem sessões de tiros no período." (`eixos` null ou nenhuma sessão);
  - "Sem pace para mostrar." (`eixos.pace` null);
  - "Nenhuma sessão deste período tem frequência cardíaca." (painel de FC quando `eixos.fc` é null).
- Carregamento, erro e ligação com a API ficam na #70.

## Arquivos principais
- `apps/mobile/src/componentes/TelaEvolucao.tsx`
- `apps/mobile/src/componentes/BotaoEnviarFit.tsx`
- `apps/mobile/src/componentes/GraficoTiros.tsx` e `apps/mobile/__tests__/GraficoTiros.test.tsx` (usa o exemplo de `packages/api-client/exemplos/`)
- `apps/mobile/src/app/` (rotas do Expo Router; código que não é rota fica fora)
- `apps/mobile/src/config.ts` (`lerConfig` e `config`)
- `apps/mobile/__tests__/index.test.tsx`, `BotaoEnviarFit.test.tsx`, `config.test.ts` e `api-client.test.ts` (cliente com `fetch` falso)
- `apps/mobile/package.json` (Jest via `jest-expo`, Testing Library), `app.json`, `eslint.config.js`, `.env.example`

## Depende de
- [[modulos/api]] (via o cliente: leitura da evolução e upload de FIT) e [[modulos/api-client]] (tipos e funções `buscarEvolucaoTiros1km` e `enviarAtividadeFit`). Pacote `expo-document-picker` para escolher o arquivo.

## Como testar
```
cd apps/mobile
npm install
npm test
npx tsc --noEmit
npx expo lint
```

## Como rodar
```
cd apps/mobile
cp .env.example .env.local   # ajuste se precisar
npx expo start --web         # navegador
npx expo start               # QR code para o Expo Go (celular na mesma rede)
```
No celular, `localhost` aponta para o próprio aparelho: use o IP do computador em `EXPO_PUBLIC_API_URL`. Reinicie o servidor ao mudar as variáveis.

## Pendências
- Filtro de período na tela (o cliente já aceita `inicio` e `fim`). Ver [[decisoes/0004-contrato-tela-evolucao]] e [[produto/roadmap]].
