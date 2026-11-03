---
tipo: meta
status: em-uso
dono: paulo
atualizado: 2026-11-03
links: [[produto/roadmap]], [[diario/2026-11-03]], [[decisoes/0005-serie-de-tiros-o-que-entra]], [[produto/meta-1-como-reproduzir]], [[diario/2026-10-31]], [[metricas/tiros-1km]], [[modulos/ingestao-garmin]], [[modulos/worker]], [[modulos/api]], [[modulos/grafico-tiros]], [[decisoes/0002-segmento-intensidade-e-versao]], [[decisoes/0003-fuso-da-atividade]]
---
# Meta 1: tiros de 1 km a partir da exportação Garmin

> **Situação: feita.** Todos os itens do critério de pronto passaram com as fixtures (relatório da Bia, #18 / PR #45)
> e com o dado real (#19), depois da evolução da regra até a `tiros_1km@4`. Fechamento: #60.

## Objetivo
Provar o caminho completo do dado: exportação da Garmin, banco, métrica determinística, gráfico e API.
Ler a exportação, guardar as atividades no Postgres e mostrar a evolução dos tiros de 1 km dos intervalados de
corrida (pace e FC médios por sessão).

## Entrega visível
- Comando `uv run python -m worker.grafico_tiros_1km --atleta-id <id> [--inicio AAAA-MM-DD] [--fim AAAA-MM-DD]`,
  que grava `entregas/meta-1/tiros-1km-atleta-<id>.png` (1600 x 1000, dois painéis: pace invertido em `m:ss` e
  FC) e o `.csv` com a mesma série (#15, #39).
- `GET /atletas/{atleta_id}/evolucao/tiros-1km` (JSON com sessões e tiros) e
  `GET /atletas/{atleta_id}/evolucao/tiros-1km.png` (#16).
- `entregas/` e `dados-teste/` ficam fora do git.

## Critério de pronto
Resultado de cada item conforme o relatório da Bia na #18 (PR #45). Ela rodou num clone limpo, em SQLite,
seguindo só [[produto/meta-1-como-reproduzir]] (#17).

| Item | Onde foi feito | Resultado |
|---|---|---|
| Fixtures, clone limpo, só pela documentação: importar, gerar PNG e CSV, chamar os dois endpoints | #18 | **ok**. Passos 1 a 7 sem ajuste; importação `inseridas=5`; JSON 200; PNG 200 `image/png` 1600 x 1000; 404 e 422 conferidos; filtro `inicio` traz só a sessão de 11/03 |
| Pace e FC de cada sessão batem com a conta à mão (6 x 1 km: 250,8 s/km "4:11", 170,3 bpm; 5 x 1 km: 237,0 s/km "3:57", 171,8 bpm) | oráculo #30, testes de #14, #15 e #16 | **ok**. Recalculado das tabelas do banco: 250,83 s/km e 170,305 bpm; 237,0 s/km e 171,769 bpm. JSON e CSV trazem 250.8 "4:11" 170.3 e 237.0 "3:57" 171.8 |
| Reimportar não duplica atividades nem segmentos | #13 | **ok**. Reimportação `inseridas=0 atualizadas=0 ignoradas=5`; continuam 5 atividades, 36 segmentos e 1 atleta |
| Rodagem leve com auto-lap, natação e intervalado sem FIT fora da série | #11, #14, #30 | **ok**. Série e CSV só com 1000000001 e 1000000002; as outras três estão no banco sem `tipo_treino` e sem segmento `tiro` |
| Check `testes` verde e "docs ok" (label `docs-ok` a partir do #35) em todos os PRs | todos | **ok** no local (`uv run pytest -q`: 123 passed); CI e label `docs-ok` conferidos pelo Theo em cada merge |
| Notas: ingestão Garmin, métrica tiros-1km, ADR 0002 e passo a passo de reprodução | #8, #9, #17 | **ok**. Nenhuma divergência entre a documentação e o comportamento |
| **Com dado real:** exportação do Angelo no Postgres local, série conferida pelo atleta | #19, com #48, #51, #53 e #58 | **ok**. A série ficou de acordo com a conferência do atleta, com as limitações conhecidas em [[metricas/tiros-1km]]. Detalhes só no relatório privado em `entregas/meta-1/` |

## O que foi entregue
| Issue | Entrega | PR |
|---|---|---|
| #8 | Fixtures sintéticas da exportação Garmin e nota de formato | #23 |
| #9 | ADR 0002: intensidade da volta e versão da detecção no `segmento` | #26 |
| #10 | Parser da exportação (JSON e FIT) | #31 |
| #11 | Detecção dos tiros de 1 km (`tiros_1km@1`) | #24 |
| #12 | Agregação por sessão (pace e FC médios) | #25 |
| #29 | `versao_deteccao` levada até o ponto da série | #32 |
| #30 | Oráculo das fixtures: valores por sessão calculados à mão | #33 |
| #13 | Importação no banco, idempotente | #34 |
| #14 | Classificação no banco, série por sessão e ADR 0003 (fuso e data local) | #38 |
| #39 | Desenho do gráfico, CSV e `formatar_pace` (regra única de `m:ss`) | #40 |
| #16 | Endpoint JSON e PNG, com o serviço `sessoes_tiros_1km` | #41 |
| #15 | Comando que grava o gráfico e o CSV em `entregas/meta-1/` | #42 |
| #17 | Documentação da meta, passo a passo de reprodução e diário do ciclo | #44 |
| #18 | QA de ponta a ponta, com o teste automatizado `tests/test_e2e_meta1.py` | #45 |
| #43 | Resultado da meta com as fixtures e roteiro | #46 |
| #19 | Validação com a exportação real e o Postgres local (parser ajustado ao dado real) | #49 |
| #48 | Regra `tiros_1km@2`: separação por recuperação e bloco principal de 1 km | #50 |
| #51 | Esteira fora da série (JSON, PNG e CSV) | #52 |
| #53 | Regra `tiros_1km@3`: tiros mais rápidos que o ritmo habitual do atleta | #54 |
| #58 | Regra `tiros_1km@4`: progressivo e fartlek de 1 km não são tiros | #59 |
| #60 | Resultado com o dado real, roteiro e meta feita | este |

Fora do plano original e acrescentado no caminho: #29, #30 e #39 (Caio, em paralelo), a ADR 0003 (fuso), o check
`docs` com a label `docs-ok` (#35) e a manutenção do roteiro (#27, #36, #43).

## O que ficou de fora
Como planejado: tela no app (Meta 2), upload de FIT pela API (Meta 3), outras distâncias de tiro e outras
modalidades, clima, sono, check-in, tipo de treino confirmado pelo professor (só a sugestão `intervalado`),
séries por segundo em Parquet, webhook da Garmin, login e várias assessorias.

Nada pendente da própria meta. Ficam como limitação documentada (sem critério geral) os casos listados em
[[metricas/tiros-1km]], seção "Limitações e quando não usar".

## O que se aprendeu
- **Oráculo cedo paga.** A tabela de valores esperados (#30), tirada das fixtures antes do banco, virou a
  referência de #14, #15, #16 e #18; ninguém recalculou à mão de novo.
- **Funções puras em paralelo destravam.** Detecção, agregação e desenho do gráfico (#11, #12, #39) andaram
  sem banco enquanto a ingestão andava. As metas seguintes devem separar a parte pura cedo.
- **Contrato de saída antes de escrever a issue de API.** A #16 pedia campos (`inicio`, lista de tiros) que a
  série da #14 não devolvia; a lacuna foi achada na revisão e virou o serviço `sessoes_tiros_1km`. Na Meta 2,
  conferir o contrato contra o que o serviço devolve antes de abrir as issues.
- **Formatação também é regra.** `m:ss` aparecia em dois lugares sem regra de arredondamento; virou uma função
  única (meio para cima, não o `round()` do Python).
- **Fuso é decisão de modelo.** A data local da sessão precisou de coluna e ADR (0003). Vale para toda métrica por dia.
- **Escala do eixo da FC (ponto de atenção para a Meta 2).** No PNG, o eixo da FC se ajusta à faixa dos dados
  (170,3 a 171,8 bpm), e 1,5 bpm parece uma subida grande (observação da Bia na #18; não é bug). Na tela do app,
  definir uma escala mínima no eixo (por exemplo, uma faixa fixa de alguns bpm) para não exagerar variações
  pequenas. Vale também para o pace.
- **Processo:** a revisão de docs passou de comentário para label (`docs-ok`, check `docs`). Um commit novo remove
  a label, então PRs de roteiro devem sair de uma vez, não em pedaços.

- **O dado real ensina o que a fixture não ensina.** Com fixtures, a regra `@1` passava; com a exportação real, a
  regra precisou de quatro versões (`@1` a `@4`) para separar os tiros de outros treinos com voltas de 1 km. Nas próximas metas com regra nova, prever uma rodada de conferência com o atleta antes de fechar.
- **Regra geral, nunca do atleta.** Nenhuma versão usa dia da semana ou algo específico de um atleta; o que não teve
  critério geral virou limitação documentada ([[decisoes/0005-serie-de-tiros-o-que-entra]]).
- **Conferência sem vazar dado.** O gabarito do atleta ficou só no relatório privado em `entregas/meta-1/`; issues,
  PRs e notas falam só de casos sintéticos.

## PRECISA DO ANGELO
Nada em aberto da Meta 1. Os bloqueios da #19 foram resolvidos (exportação, Docker e conferência do resultado).
Também resolvidos em 03/11: **Histórico público:** resolvido (Angelo, 03/11). Atividades do resumo sem arquivo FIT:
não faltam arquivos. Os itens das
próximas metas estão em [[produto/roadmap]].

## Resultado
**Meta 1 feita.** Com as fixtures, o critério de pronto foi cumprido no QA da Bia (#18, PR #45), sem divergência
com a documentação e sem bug aberto; o PNG da API é idêntico byte a byte ao do comando.

**Com o dado real (#19):** a exportação foi importada no Postgres local e a série foi conferida pelo atleta. Ela
ficou de acordo com a conferência depois da evolução da regra de `tiros_1km@1` até `tiros_1km@4` (#48, #51, #53,
#58), com as limitações conhecidas documentadas em [[metricas/tiros-1km]]. Nenhum número do dado real está no
repositório: o detalhe fica no relatório privado em `entregas/meta-1/`.

Observações do QA com fixtures, nenhuma delas bug:
- o eixo da FC exagera variações pequenas (entra na Meta 2 como escala mínima);
- o `atividade_id` do CSV e do JSON é o id do banco (1 e 4), como a documentação avisa.

Próxima: Meta 2, evolução dos tiros no app ([[produto/roadmap]]).
