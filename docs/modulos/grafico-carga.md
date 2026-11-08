---
tipo: modulo
status: em-uso
dono: caio
atualizado: 2026-11-08
links: [[metricas/serie-carga]], [[metricas/carga-treino]], [[metricas/carga-oraculo]], [[decisoes/0010-carga-de-treino]], [[modulos/grafico-tiros]], [[modulos/worker]], [[produto/roadmap]]
---
# Módulo: gráfico da carga (CTL, ATL, TSB e carga diária)

## Para que serve
Desenha a carga de treino do atleta (estimativa, nunca medida) e grava o CSV com a mesma série, para o atleta conferir
(#143). Como o gráfico dos tiros ([[modulos/grafico-tiros]]): funções puras de desenho sobre a série já calculada, e um
comando que lê o banco e grava em `entregas/meta-6/` (fora do git). Não calcula nada: os números vêm de
[[metricas/serie-carga]] e de [[metricas/carga-treino]].

## Entradas e saídas
- `render_png(dias, atleta_nome) -> bytes`: PNG 1600 x 1200 px, fundo branco, três painéis com o mesmo eixo X (data
  `dd/mm/aa`, "Data do treino"): barras da carga do dia (TSS estimado); CTL (azul) e ATL (laranja); TSB (verde, linha em 0).
  Título e legendas dizem "estimativa". Os dias "ainda aprendendo" (menos de 42 dias desde o primeiro dia da série) ficam
  sombreados nos três painéis, com legenda. Dia com treino sem carga (falta dado: `sem_carga > 0`) leva um triângulo vermelho
  na base do painel das barras: não é dia de descanso. Série vazia: PNG com "Sem carga calculada no período".
- `linhas_csv(dias) -> list[dict]`: colunas `dia, carga, ctl, atl, tsb, aprendendo (sim/nao), atividades, calculadas,
  sem_carga`, um dia por linha (inclusive os sem treino), números com 6 casas (as do oráculo [[metricas/carga-oraculo]]).
- Eixos: mesma ideia da Meta 1 ([[modulos/grafico-tiros]], escala mínima), com `escala_eixo`: faixa mínima de 50 pontos
  para carga, CTL e ATL e de 20 pontos para o TSB (valores iniciais, regra própria do projeto), para uma variação pequena
  não parecer grande. As barras partem do zero.
- Comando: `uv run python -m worker.grafico_carga --atleta-id <id> [--inicio AAAA-MM-DD] [--fim AAAA-MM-DD] [--saida <pasta>]`
  grava `entregas/meta-6/carga-atleta-<id>.png` e `.csv`. `--inicio` e `--fim` só recortam o desenho: CTL e ATL são os da
  série inteira. Avisa em stderr se há atividade sem linha em `carga_atividade` (rode `worker.calcular_carga`). Só lê o
  banco; sem rede. Atleta inexistente: stderr e código 1.
- `app.servicos.serie_carga_banco.serie_carga_do_atleta(session, atleta_id)`: monta a série a partir de `carga_atividade`
  (dia local, [[decisoes/0003-fuso-da-atividade]]; ignora `multiesporte_pai` e `troca`). Reaproveitada pela conferência (#144).

## Arquivos principais
- `services/api/app/graficos/carga.py`
- `services/api/app/servicos/serie_carga_banco.py`
- `services/worker/worker/grafico_carga.py`
- Teste: `services/worker/tests/test_grafico_carga.py`

## Depende de
matplotlib (backend `Agg`), [[metricas/serie-carga]], `app.graficos.escala`.

## Como testar
`uv run pytest -q services/worker/tests/test_grafico_carga.py`. O teste importa as fixtures sintéticas de
`tests/fixtures/garmin/carga/`, calcula a carga e confere o CSV com o oráculo da #137 (`SERIE` e `CARGA_DIA`: 43 dias,
05/03 a 16/04/2025) e gera o PNG (teste de fumaça: assinatura e 1600 x 1200). Nenhum PNG ou CSV com dado real entra no git.

## Pendências
- Revisar o desenho com o histórico real (local, em `entregas/meta-6/`).
