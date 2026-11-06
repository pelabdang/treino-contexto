---
tipo: modulo
status: em-uso
dono: rafa
atualizado: 2026-11-06
links: [[modulos/api]], [[modulos/api-client]], [[produto/roadmap]], [[decisoes/0004-contrato-tela-evolucao]], [[produto/meta-2-como-rodar]], [[decisoes/0006-upload-de-fit]], [[design/guia-visual]], [[design/tokens]], [[decisoes/0007-clima-da-atividade]], [[modulos/clima]]
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
| `src/app/treino/[id].tsx` | `/treino/<atividade_id>` | `TelaTreino` (#159); ainda sem link vindo da lista (#217, ver abaixo) |

## Tela de evolução (`TelaEvolucao`)
`src/componentes/TelaEvolucao.tsx` chama `buscarEvolucaoTiros1km` e mostra um estado por vez:
- carregando (#202): o texto "Carregando seus tiros..." e o esqueleto dos três cartões (`EsqueletoEvolucao`, `src/componentes/Esqueleto.tsx`; `cor.superficie-2`, `raio.pequeno`), com pulso de opacidade 1 para 0,6 em `movimento.esqueleto` (1200 ms). Com "reduzir movimento" no sistema (`AccessibilityInfo`) o esqueleto fica parado. O esqueleto é escondido do leitor de tela; o texto fica;
- vazio (`sessoes: []`): ícone `insert-chart-outlined` (40, `cor.texto-2`), título "Ainda não há treinos de tiros de 1 km" e a frase "Envie o arquivo FIT de um treino com tiros para ver a evolução aqui."; o botão "Enviar arquivo FIT" do alto vira **primário** (`variante="primario"` do `BotaoEnviarFit`). Fica um botão só, no mesmo lugar, para não perder o aviso de envio quando a lista passa a ter dados;
- erro (ícone de 40 em `cor.erro`, frase e `accessibilityRole="alert"`): rede usa `wifi-off`, "Não foi possível falar com o servidor" e o botão "Tentar de novo"; `404` usa `error-outline`, "Atleta não encontrado"; `422` ou outro status usa `error-outline`, "Não foi possível carregar os tiros. Tente de novo mais tarde.";
- sucesso, nesta ordem (#154): cartão "Último treino · dd/mm/aa" (a última sessão da lista, que a API manda em data crescente) com o **melhor tiro** em `fonte.numero-destaque` (`pace_melhor` + "min/km"), "FC do melhor tiro" (`fc_melhor_tiro` ou "sem FC") e, em secundário, "Média dos tiros" (`pace_medio`) e `n_tiros`; cartão "Evolução" com o `GraficoTiros`; cartão "Treinos" com a lista, **mais recente no alto**, uma linha por sessão (data, `pace_melhor`, `fc_melhor_tiro` ou "sem FC") e abaixo "média `pace_medio` · `n_tiros` tiros". A linha é **tocável** (#202): altura mínima de 56 (`tamanho.listaLinhaAltura`, `lista.linha-altura`), `accessibilityRole="button"`, `accessibilityState.selected` e fundo `cor.destaque-suave` quando selecionada. A seleção é uma só, guardada na `TelaEvolucao`: tocar a linha ou o ponto do gráfico escolhe a mesma sessão (ponto maior com anel, linha destacada e o detalhe do gráfico). A partir de 600 de largura (web larga) a lista ganha um cabeçalho de colunas e a coluna "Média dos tiros" (`pace_medio` · `n_tiros`) em vez da segunda linha; e o rodapé "cálculo: <versao_calculo>" como texto, mais "cálculo em atualização" quando `reclassificacao_pendente` é `true`. O app nunca compara a versão com um valor fixo.
- Margem da tela: 16 no celular e 24 a partir de 600 de largura (`useMargemTela` / `margemDaTela` em `src/tema/`, #197).
Testes em `__tests__/index.test.tsx` com `fetch` falso (todos os estados, ícones, esqueleto, toque na linha e no ponto marcando a mesma sessão, coluna da média na web larga, cartão do último treino, ordem da lista, "9:99" em `pace_melhor` e rótulo de eixo trocados (prova que o app não recalcula), margem 16/24, versão `tiros_1km@9`, aviso de reclassificação). O componente aceita `fetchFn` só para teste.

Rodar com dado sintético: passo a passo em [[produto/meta-2-como-rodar]] (API com fixtures, `CORS_ORIGENS` com `http://localhost:8081` e `npx expo start --web --port 8081`). O `expo start` reescreve `apps/mobile/tsconfig.json`: não commitar.

## Tela de um treino (`TelaTreino`, #159)
`src/componentes/TelaTreino.tsx`, na rota `/treino/<atividade_id>` (`src/app/treino/[id].tsx`, que lê o parâmetro e passa `aoVoltar`). Chama `buscarAtividade(atletaId, atividadeId)` do [[modulos/api-client]] (`GET /atletas/{id}/atividades/{id}`) e mostra um estado por vez. **O app só mostra:** `data_local`, `hora_local`, `duracao` e `pace_medio` vêm prontos da API ([[decisoes/0004-contrato-tela-evolucao]], adendo 2); não há pace, fuso nem hora calculados no app. As únicas transformações são a data `AAAA-MM-DD` para `dd/mm/aa` (a mesma `dataCurta` da evolução), a distância `distancia_m` em km com vírgula (a API ainda não manda a distância pronta: #216) e o ponto decimal do clima trocado por vírgula.
- carregando: esqueleto dos dois cartões (`EsqueletoTreino`, mesmo pulso da evolução) e o texto "Carregando o treino..." (#219); erro `404`: "Treino não encontrado" (ou "Atleta não encontrado" quando o `detail` é "atleta não encontrado"); outros status: "Não foi possível carregar este treino. Tente de novo mais tarde."; rede: "Não foi possível falar com o servidor" com "Tentar de novo". O erro (#219) é o mesmo da evolução: ícone de 40 em `cor.erro` (`wifi-off` na rede, `error-outline` nos outros), frase com `accessibilityRole="alert"` e, só na rede, "Tentar de novo".
- sucesso: botão "Voltar" (44 de altura), título "Treino", chip da modalidade (ícone e cor do guia; corrida, ciclismo, natação) e "dd/mm/aa às HH:MM"; cartão com a **duração** em `fonte.numero-destaque`, "Distância", "Pace médio" **só quando `pace_medio` vem preenchido** (corrida; natação e ciclismo não mostram a linha) e "FC média" ou "sem FC"; cartão "Clima".
- cartão "Clima" por `clima.estado`: `ok` mostra Temperatura, Sensação térmica, Umidade e Vento (valor ausente vira "sem dado") e, embaixo, o texto de `clima.atribuicao` ("Weather data by Open-Meteo.com", ADR 0007 item 4; o app não escreve a atribuição, só mostra o que vem, e ela só vem com clima `ok`); `indoor`: "Treino em ambiente fechado: não há clima para mostrar."; `sem_posicao`: "O arquivo não tem posição, então não dá para buscar o clima."; `pendente`: "O clima deste treino ainda não chegou. Treinos recentes podem levar cerca de uma semana."; `falha`: "Não foi possível obter o clima deste treino." (aviso âmbar com ícone). Sem objeto `clima`, o cartão não aparece. Nunca se mostra posição.
- Decisões sem spec de tela (a implementação veio antes da spec; hoje a spec é [[design/telas/treino]], que fixa o que segue; antes disso seguiu-se o [[design/guia-visual]] e os tokens): cabeçalho com Voltar, título, chip e data; um número em destaque por cartão (a duração); cartão de clima em linhas rótulo/valor de 44, cada uma lida junta pelo leitor de tela ("Temperatura, 24,3 °C", #219); avisos com ícone e texto (`info-outline` para indoor, sem posição e pendente; `warning-amber` para falha); margem 16/24 como nas outras telas.
- Pendência: a lista "Treinos" da `TelaEvolucao` ainda não leva a esta rota (mexer nela conflitaria com a #202); por ora a rota abre digitando a URL (#217). Tela de um treino com blocos, carga e esforços entra nas issues da Meta 5.
- Testes: `__tests__/TelaTreino.test.tsx` (um por estado do clima, natação sem pace e sem FC, "9:99" e "99:88" provam que não reformata, atribuição só quando vem da API, 404, 500, rede, voltar) e `__tests__/rotaTreino.test.tsx` (parâmetro da rota). Atividades sintéticas em `apps/mobile/__fixtures__/atividades.ts`; os testes trocam o `MaterialIcons` por um falso (`__fixtures__/iconesFalsos.tsx`), porque o real carrega a fonte do ícone e quebra no Jest.
- Capturas por estado (dados sintéticos, 390 de largura, claro e escuro) em `docs/design/telas/treino/`: `treino-<estado>-<tema>.png` para `clima-ok`, `indoor`, `sem-posicao`, `pendente`, `falha`, `natacao-sem-pace`, `erro-404` e `erro-500`, mais `carregando` (esqueleto), regeradas no #219 com o título final "Treino".
- Como gerar as capturas (#218), sem trocar config: `npm run api-falsa` (em `apps/mobile`; API falsa com dados sintéticos em `scripts/api-falsa.mjs`, porta 8000, serve a evolução e `GET /atletas/{id}/atividades/{id}`) e, em outro terminal, `EXPO_PUBLIC_API_URL=http://localhost:8000 npx expo start --web --port 8081`. Abra `http://localhost:8081` (e `/treino/101`). O modo escuro vem do `prefers-color-scheme` do navegador. Captura de prova da tela de evolução em `docs/design/telas/web/evolucao-web-static-218.jpg`.
- Web com `web.output: "static"` (#218): **causa e correção**. No Expo Router 58 o export e o servidor de dev entregam o `<script>` do bundle, o CSS e as fontes pelo `useServerDocumentContext()` (`headNodes` e `bodyNodes`). O nosso `src/app/+html.tsx` não os renderizava, então o HTML saía sem o bundle (só o fundo "carregando-fonte"); `EXPO_WEB_DEV_HYDRATE` não tem relação. Corrigido no `+html.tsx` (mantido "static", que dá `lang="pt-BR"` e pré-render). Não remova `{headNodes}` e `{bodyNodes}`. Verificação: `npm run verificar:web` (exporta a web e falha se o `index.html` não tiver o `<script>` do `entry-*.js` ou o `lang="pt-BR"`) e `__tests__/html.test.tsx` (o `<script>` do contexto chega ao HTML).

## Botão "Enviar arquivo FIT" (`BotaoEnviarFit`)
`src/componentes/BotaoEnviarFit.tsx`, no alto da `TelaEvolucao`, usa o mesmo `apiUrl` e `atletaId` da tela. Toque abre o seletor do `expo-document-picker` (`getDocumentAsync`, `type: "*/*"`); na web entrega o `File`, no celular o `uri`. Envia com `enviarAtividadeFit` ([[modulos/api-client]]) e mostra um estado por vez:
- enviando: "Enviando..." e botão desligado;
- `201`: "Atividade adicionada"; `200`: "Essa atividade já estava aqui". Nos dois casos a tela busca a evolução de novo (o gráfico antigo fica visível até a resposta chegar);
- erro: o `detail` da API (`400`, `413`, `404`); falha de rede: "Não foi possível falar com o servidor. Verifique a conexão e tente de novo."; outro erro, mensagem genérica;
- seletor cancelado: nada acontece.
Regras do arquivo (só `.fit`, 10 MB, FIT sintético ou do atleta) são da API ([[decisoes/0006-upload-de-fit]]); o app não valida. Testes em `__tests__/BotaoEnviarFit.test.tsx` (seletor e `fetch` falsos: 201, 200, 400, 413, rede, cancelar).
Verificado na web (#96) com API e Postgres locais, FIT sintético `upload_intervalado_5x1km.fit`: o `POST` devolveu `201` e a tela passou de 2 para 3 sessões (01/04/2025). Como forçar cada estado na tela: [[produto/meta-3-como-rodar]]. O HTML da web declara `lang="pt-BR"` em `src/app/+html.tsx` (#119). Para o `+html.tsx` valer no export, o `app.json` tem `web.output: "static"`: `npx expo export --platform web` gera `index.html` com `lang="pt-BR"` e a tela pré-renderizada no estado "Carregando". Teste: `__tests__/html.test.tsx`. Assim o Chrome não oferece tradução e não é mais preciso desligá-la (antes o tradutor mexia nas mensagens, aparecia só "Atividade").

## Componente GraficoTiros
`src/componentes/GraficoTiros.tsx` recebe `dados: EvolucaoTiros1km` (tipo de `@treino/api-client`) e desenha dois painéis com o mesmo eixo X (data `dd/mm/aa`, posição proporcional ao tempo): "Melhor pace (min/km)" (com "mais rápido ↑") em cima e "FC do melhor tiro (bpm)" embaixo, um ponto por sessão. O valor principal é o do melhor tiro (`pace_melhor_s_km` e `fc_melhor_tiro`, contrato do Adendo 1 da [[decisoes/0004-contrato-tela-evolucao]]); a média não entra no gráfico, porque os `eixos` são calculados pelo melhor tiro. Usa `react-native-svg` (gratuito, incluído no Expo Go) para linhas e pontos; rótulos são `Text` nativo.
- Faixa, marcas e rótulos vêm só de `eixos` da API. O app só converte valor em posição na tela; não formata pace nem escolhe escala (ver [[decisoes/0004-contrato-tela-evolucao]]).
- Pace invertido (`eixos.pace.invertido`): pace menor fica no alto.
- A única formatação no app é a data (dd/mm/aa); pace, FC e rótulos vêm prontos da API.
- Sessão com `fc_melhor_tiro` nulo: sem ponto no painel de FC, com ponto no de pace.
- Ponto selecionado: raio 7 com anel de 2 em `cor.texto`, e a data dele no eixo fica em negrito (#197).
- O toque fica num `Pressable` transparente (44 de altura) por cima de cada ponto, com o `testID` `toque-<painel>-<atividade_id>`; o `Circle` do SVG não leva `onPress`. Com `onPress` no `Circle`, o `react-native-svg` repassava props de responder (`onResponderTerminate` e outras) ao DOM na web e o React avisava "Unknown event handler property" no modo dev.
- A largura do alvo é 44, cortada no meio do caminho até o ponto vizinho (`faixasDeToque`), para dois alvos nunca se sobreporem quando as datas estão próximas; a largura nunca fica abaixo de 24 (centrada no ponto): com datas coladas ou iguais os alvos se sobrepõem e vale a sessão mais recente, por cima (`zIndex`). `accessibilityLabel`: "Sessão de 18/03/25, melhor tiro 4:05 min/km" (pace) e "..., FC do melhor tiro 176 bpm" (FC).
- Tocar num ponto mostra o detalhe: data e `n_tiros`, "Melhor tiro", "FC do melhor tiro", "Média dos tiros" e "FC média", todos como vieram da API; sem FC, "sem FC".
- Mensagens de "sem dados":
  - "Sem sessões de tiros no período." (`eixos` null ou nenhuma sessão);
  - "Sem pace para mostrar." (`eixos.pace` null);
  - "Nenhuma sessão deste período tem frequência cardíaca." (painel de FC quando `eixos.fc` é null).
- Carregamento, erro e ligação com a API ficam na `TelaEvolucao`. O gráfico aceita `selecionadaId` e `aoSelecionar` (seleção controlada pela tela, #202); sem eles guarda a seleção sozinho.

## Tema (tokens do guia visual)
`src/tema/` transforma [[design/tokens]] (fonte única) em código, com os mesmos nomes do guia ([[design/guia-visual]]):
- `tokens.ts`: `cores.claro` e `cores.escuro` (chaves como na tabela, sem o prefixo `cor.`: `cor["superficie-2"]`, `cor["grafico.pace"]`), `espaco`, `raio`, `borda`, `tamanho`, `movimento`, `familia` e `fonte` (Inter, com `tabular-nums` nos números).
- `index.tsx`: `useTema()` devolve `{ escuro, cor }` conforme o tema do sistema (`useColorScheme`; claro quando o sistema não informa). O objeto é estável, então serve de dependência de `useMemo`.
- `fontes.ts`: `useFontesInter()` carrega a Inter (`@expo-google-fonts/inter`, OFL); o `_layout.tsx` espera as fontes mostrando uma `View` com `cor.fundo` (sem piscar em branco) e, se falharem, segue com a fonte do sistema. Fica separado do resto para os testes dos componentes não carregarem `expo-font`.
- Os componentes montam o `StyleSheet` com `criarEstilos(tema)` dentro de `useMemo`. Cor, fonte, espaço e raio das telas só vêm de tokens: sem cor literal nas telas.
- `@expo/vector-icons` (Material Icons) é usado nos estados vazio e de erro da `TelaEvolucao` (#202), sempre com texto ao lado (o ícone fica fora da acessibilidade). Nos testes de Jest o pacote é trocado por um texto `nome:tamanho`, porque a fonte do ícone carrega de forma assíncrona e não existe no Jest.
- Teste `__tests__/tema.test.tsx` lê a tabela "Cores" de `docs/design/tokens.md` e exige que o tema tenha os mesmos nomes e valores (claro e escuro), mais conferências de espaço, raio e tipografia e do `useTema`. Mudou uma cor no guia? Atualize `tokens.ts` na mesma hora, senão o teste falha.
- Diferenças visuais pequenas em relação às telas antigas, vindas do guia: botão com 48 de altura e cor `destaque`, desligado em `superficie-2` (antes opacidade 0,5), alvo de toque do ponto do gráfico em 44 (antes 32), rótulos de eixo em 12 (antes 11) e conteúdo limitado a 720 de largura na web. O destaque do melhor tiro é da #154 (acima).

## Arquivos principais
- `apps/mobile/src/componentes/TelaEvolucao.tsx`
- `apps/mobile/src/componentes/BotaoEnviarFit.tsx`
- `apps/mobile/src/componentes/GraficoTiros.tsx` e `apps/mobile/__tests__/GraficoTiros.test.tsx` (usa o exemplo de `packages/api-client/exemplos/`)
- `apps/mobile/src/app/` (rotas do Expo Router; código que não é rota fica fora)
- `apps/mobile/src/tema/` (tokens, `useTema`, fontes) e `apps/mobile/__tests__/tema.test.tsx`
- `apps/mobile/__tests__/layout.test.tsx` (fundo do tema enquanto a fonte carrega)
- `apps/mobile/src/config.ts` (`lerConfig` e `config`)
- `apps/mobile/__tests__/index.test.tsx`, `BotaoEnviarFit.test.tsx`, `config.test.ts` e `api-client.test.ts` (cliente com `fetch` falso)
- `apps/mobile/package.json` (Jest via `jest-expo`, Testing Library), `app.json`, `eslint.config.js`, `.env.example`

## Depende de
- [[modulos/api]] (via o cliente: leitura da evolução e upload de FIT) e [[modulos/api-client]] (tipos e funções `buscarEvolucaoTiros1km` e `enviarAtividadeFit`). Pacote `expo-document-picker` para escolher o arquivo; `@expo-google-fonts/inter`, `expo-font`, `expo-asset` e `@expo/vector-icons` para o tema.

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
