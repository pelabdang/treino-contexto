---
tipo: meta
status: em-uso
dono: paulo
atualizado: 2026-11-03
links: [[produto/roadmap]], [[produto/metas/meta-1-tiros-1km]], [[produto/meta-2-como-rodar]], [[decisoes/0004-contrato-tela-evolucao]], [[modulos/api]], [[modulos/api-client]], [[modulos/mobile]], [[modulos/grafico-tiros]], [[modulos/infra]], [[diario/2026-11-03]]
---
# Meta 2: evolução dos tiros no app

> **Situação: feita.** Código e QA no main (#62 a #72). A Bia viu a tela no Chrome com as fixtures sintéticas e
> conferiu os valores contra o JSON da API (#72, PR #85). Fechamento: #73. Ficam registrados como não verificados
> iOS e Android (sem simulador) e os estados carregando e vazio na tela (vistos só pelo `npm test`).

## Objetivo
O atleta vê no app (web, iOS e Android) a evolução dos tiros de 1 km da Meta 1, sem o app formatar pace nem escolher
a escala dos eixos. Tudo pronto vem da API ([[decisoes/0004-contrato-tela-evolucao]]).

## Entrega visível
Tela "Evolução dos tiros de 1 km" no Expo, com os dados do endpoint da Meta 1, rodando local na web e no Expo Go.
Sem login e sem deploy; atleta fixo por `EXPO_PUBLIC_ATLETA_ID` ([[modulos/mobile]]). Passo a passo em
[[produto/meta-2-como-rodar]].

## Critério de pronto
Resultado de cada item conforme o relatório da Bia na #72 (PR #85), na web, com as fixtures sintéticas.

| Item | Onde | Resultado |
|---|---|---|
| Na web, com as fixtures e só pela documentação, a tela mostra a evolução com os valores da API | #71, #72 | **ok**. Tela com as 2 sessões das fixtures nos dois painéis; pace `m:ss`, FC e marcas dos eixos iguais ao JSON; o toque num ponto abre o detalhe; rodapé `cálculo: tiros_1km@4`. O banco foi reusado (importação idempotente); os passos do zero foram rodados pela Nina na #71 |
| Estados carregando, vazio e erro no `npm test` e conferidos à mão | #70, #72 | **ok, com ressalva.** Erro 404 ("Atleta não encontrado") e erro de rede com "Tentar de novo" conferidos na tela. Carregando e vazio **só pelo `npm test`**; o vazio também no backend (período sem sessões devolve `sessoes: []`) |
| O app não tem função de pace: todo `m:ss` vem da API | #64, #70 | **ok**. Teste com texto trocado (`9:99`); na tela, os rótulos batem com o JSON |
| Escala mínima nos eixos (5 bpm na FC, 30 s/km no pace), a mesma no PNG e no app | #63, #66 | **ok** |
| Cliente TypeScript gerado do OpenAPI, com teste que pega cliente desatualizado | #68 | **ok** ([[modulos/api-client]]) |
| OpenAPI declara o que o endpoint devolve, 404 incluído | #64 | **ok** |
| iOS e Android no Expo Go, ou registrados como não verificados | #72 | **não verificado**: sem simulador nem aparelho na máquina do QA |
| Testes | todos | `uv run pytest -q` e `npm test` verdes no QA; `tests/test_e2e_meta2.py` compara a API com o exemplo de contrato e roda no CI |

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
| #71 | Documentação, passo a passo e diário | #84 |
| #72 | QA de ponta a ponta com fixtures e `tests/test_e2e_meta2.py` | #85 |
| #73 | Resultado da meta e roteiro | este |

## Melhorias abertas depois da meta
Não estão no critério de pronto, então não são pendências da Meta 2. Ficam abertas e entram quando couberem:
- **#86:** aviso "Unknown event handler property `onResponderTerminate`" do `react-native-svg` na web, só no modo de
  desenvolvimento. Não afeta a tela.
- **#87:** o eixo de pace mostra poucas marcas (passo de 15 s/km). A tela fica legível, mas o eixo é curto.

## O que ficou de fora
Como planejado: login, lista de atletas, filtro de período na tela, deploy (EAS, lojas, conta Expo), upload de FIT
(Meta 3) e outras métricas.

## O que se aprendeu
- **Contrato antes do código.** A conferência do endpoint antes das issues e a ADR 0004 evitaram retrabalho entre
  API, cliente e app: as issues do app andaram em cima de um exemplo de contrato gerado das fixtures.
- **Uma regra só, testada com texto trocado.** O teste com `9:99` provou que o app mostra o texto da API e não
  recalcula. Vale para todo valor formatado nas próximas metas.
- **Rodar o passo a passo mostra o que a leitura não mostra.** O compose sem `-p` reusa o volume do banco local, a
  porta 5432 pode estar ocupada, a API demora alguns segundos para subir e o `expo start` reescreve o
  `tsconfig.json` do app.
- **Ver a tela é uma etapa própria.** Até o QA, o código estava pronto e testado, mas ninguém tinha visto a tela.
  Nas metas com tela, prever no QA a conferência visual e dizer de antemão como cobrir iOS e Android.
- **Estados difíceis de provocar à mão** (carregando e vazio) precisam de um jeito documentado de forçar, por
  exemplo um período sem sessões ou um atraso simulado, para não ficarem só no `npm test`.
- **Teste de ponta a ponta ligado ao contrato.** O `test_e2e_meta2.py` compara a API com o mesmo exemplo que o app
  usa nos testes; se o contrato muda, quebra dos dois lados.

## PRECISA DO ANGELO
Nada da Meta 2. As decisões dele (app local, atleta fixo, escala de 5 bpm, Expo) estão na ADR 0004. As da Meta 3
estão em [[produto/roadmap]].

## Resultado
**Meta 2 feita.** Na web, com as fixtures, a tela mostra a evolução dos tiros com os valores da API, sem nenhuma
formatação de pace no app e com a mesma escala do PNG. Não verificados: iOS e Android, e os estados carregando e
vazio na tela (cobertos pelo `npm test`). Melhorias abertas: #86 e #87.

Próxima: Meta 3, upload de arquivo FIT ([[produto/roadmap]]).
