---
tipo: meta
status: em-uso
dono: paulo
atualizado: 2026-10-31
links: [[produto/roadmap]], [[produto/meta-1-como-reproduzir]], [[diario/2026-10-31]], [[metricas/tiros-1km]], [[modulos/ingestao-garmin]], [[modulos/worker]], [[modulos/api]], [[modulos/grafico-tiros]], [[decisoes/0002-segmento-intensidade-e-versao]], [[decisoes/0003-fuso-da-atividade]]
---
# Meta 1: tiros de 1 km a partir da exportação Garmin

> **Situação:** todos os itens do critério de pronto passaram com as fixtures (relatório da Bia, #18 / PR #45).
> Falta só o dado real (#19). A meta continua **atual** até o Angelo decidir sobre a #19.

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
| **Com dado real:** exportação do Angelo no Postgres local, PNG conferido com 2 ou 3 treinos | #19 | bloqueado: ver "PRECISA DO ANGELO" |

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
| #17 | Documentação da meta, passo a passo de reprodução e diário do ciclo | #44 (em revisão) |
| #18 | QA de ponta a ponta, com o teste automatizado `tests/test_e2e_meta1.py` | #45 (em revisão) |

Fora do plano original e acrescentado no caminho: #29, #30 e #39 (Caio, em paralelo), a ADR 0003 (fuso), o check
`docs` com a label `docs-ok` (#35) e a manutenção do roteiro (#27, #36, #43).

## O que ficou de fora
Como planejado: tela no app (Meta 2), upload de FIT pela API (Meta 3), outras distâncias de tiro e outras
modalidades, clima, sono, check-in, tipo de treino confirmado pelo professor (só a sugestão `intervalado`),
séries por segundo em Parquet, webhook da Garmin, login e várias assessorias.

Pendente da própria meta: a validação com o dado real (#19), bloqueada pelos itens do Angelo.

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

## PRECISA DO ANGELO
Bloqueiam só a #19; o resto da meta foi feito com fixtures.

1. **Exportação da Garmin em `dados-teste/garmin/`** (fora do git). O time não leu nem copiou nada de
   `~/Documents/Projects/garmin`. Se for a exportação, o Angelo copia o zip para `dados-teste/garmin/`.
2. **Docker (ou Postgres 16) instalado** para subir o Postgres local.
3. **Conferência do resultado:** 2 ou 3 treinos de 1 km de que se lembra (data e mais ou menos o pace), e se
   esteira e pista entram no mesmo gráfico (padrão até lá: entram todos, com o `subtipo` guardado).
4. **Decisão:** fechar a Meta 1 só com fixtures e seguir para a Meta 2, deixando a #19 para quando o dado real
   chegar, ou manter a Meta 1 aberta até a #19.

## Resultado
**Com as fixtures: critério de pronto cumprido.** Todos os itens passaram no QA da Bia (#18, PR #45), sem
divergência com a documentação e sem bug aberto. O PNG da API é idêntico byte a byte ao do comando.

Observações do QA, nenhuma delas bug:
- o eixo da FC exagera variações pequenas (ver "O que se aprendeu");
- o `atividade_id` do CSV e do JSON é o id do banco (1 e 4), como a documentação avisa;
- o passo a passo foi testado só em SQLite; o Postgres local fica para a #19.

**Com dado real: pendente (#19).** A meta fica **atual** até o Angelo decidir: trazer a exportação e o Docker
para fazer a #19, ou fechar a Meta 1 só com fixtures e seguir para a Meta 2 com a #19 em aberto.
