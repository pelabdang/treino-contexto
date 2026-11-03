---
tipo: meta
status: em-andamento
dono: paulo
atualizado: 2026-11-03
links: [[produto/roadmap]], [[produto/metas/meta-1-tiros-1km]], [[produto/meta-2-como-rodar]], [[decisoes/0004-contrato-tela-evolucao]], [[modulos/api]], [[modulos/api-client]], [[modulos/mobile]], [[modulos/grafico-tiros]], [[modulos/infra]], [[diario/2026-11-03]]
---
# Meta 2: evolução dos tiros no app

> **Situação: código entregue; falta o QA de ponta a ponta (#72) e o resultado da meta.** O passo a passo está em
> [[produto/meta-2-como-rodar]]. A conferência visual da tela ainda não foi feita.

## Objetivo
O atleta vê no app (web, iOS e Android) a evolução dos tiros de 1 km da Meta 1, sem o app formatar pace nem escolher
a escala dos eixos. Tudo pronto vem da API ([[decisoes/0004-contrato-tela-evolucao]]).

## Entrega visível
Tela "Evolução dos tiros de 1 km" no Expo, com os dados do endpoint da Meta 1, rodando local na web e no Expo Go.
Sem login e sem deploy; atleta fixo por `EXPO_PUBLIC_ATLETA_ID` ([[modulos/mobile]]).

## Critério de pronto
| Item | Onde | Situação |
|---|---|---|
| Na web, com as fixtures e só pela documentação, a tela mostra a evolução com os valores da API | #71 (passo a passo), #72 (QA) | API, CORS e bundle web **rodados** na #71; a **tela não foi vista**: conferência é da #72 |
| Estados carregando, vazio e erro no `npm test` e conferidos à mão | #70, #72 | `npm test` cobre; conferência à mão é da #72 |
| O app não tem função de pace: todo `m:ss` vem da API | #64, #70 | feito; teste com texto trocado (`9:99`) |
| Escala mínima nos eixos (5 bpm na FC, 30 s/km no pace), a mesma no PNG e no app | #63, #66 | feito |
| Cliente TypeScript gerado do OpenAPI, com teste que pega cliente desatualizado | #68 | feito ([[modulos/api-client]]) |
| OpenAPI declara o que o endpoint devolve, 404 incluído | #64 | feito |
| iOS e Android no Expo Go, ou registrados como não verificados | #72 | **não verificado** até o QA |

## O que foi entregue
| Issue | Entrega | PR |
|---|---|---|
| #62 | ADR 0004: contrato da tela de evolução | #75 |
| #63 | Escala mínima dos eixos de pace e FC, regra única `escala_eixo` (PNG) | #78 |
| #64 | Endpoint no contrato da ADR 0004 e `worker.reclassificar` | #77 |
| #65 | CORS por `CORS_ORIGENS` | #79 |
| #66 | Bloco `eixos` no JSON | #80 |
| #67 | Expo Router, tela inicial vazia e configuração | #76 |
| #68 | Cliente TypeScript gerado do OpenAPI e exemplo de contrato | #81 |
| #69 | Componente do gráfico de dois painéis | #82 |
| #70 | Tela ligada à API com os estados | #83 |
| #71 | Documentação, passo a passo e diário | este |

## O que ficou de fora
Login, lista de atletas, filtro de período na tela, deploy, upload de FIT e outras métricas.

## O que se aprendeu (até aqui)
- **Rodar o passo a passo mostra o que a leitura não mostra.** Ao executar os comandos: o compose do projeto
  reusa o volume do banco local quando se roda sem `-p`; a porta 5432 pode estar ocupada; a API demora alguns
  segundos para subir; o `expo start` reescreve o `tsconfig.json` do app.
- **Contrato antes do código** (ADR 0004) evitou retrabalho entre API, cliente e app.

## PRECISA DO ANGELO
Nada novo. Decisões do Angelo para a meta (app local, atleta fixo, escala de 5 bpm, Expo) estão na ADR 0004.

## Próximos passos
#72: QA da Bia com fixtures, incluindo ver a tela. Depois, o resultado da meta e o roteiro (Paulo).
