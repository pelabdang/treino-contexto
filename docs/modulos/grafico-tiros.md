---
tipo: modulo
status: em-uso
dono: caio
atualizado: 2026-10-31
links: [[metricas/tiros-1km]], [[modulos/api]], [[modulos/worker]], [[produto/roadmap]]
---
# Módulo: gráfico dos tiros de 1 km

## Para que serve
Desenha a evolução dos tiros de 1 km (pace e FC médios por sessão) e monta as linhas do CSV, a partir de uma
série já calculada. Não acessa banco: a #15 (comando que grava em `entregas/`) e a #16 (endpoint PNG) só leem
a série e chamam estas funções, então o PNG é o mesmo nos dois lugares.

## Entradas e saídas
- `render_png(serie, atleta_nome) -> bytes`: PNG 1600 x 1000 px (figsize 16 x 10, dpi 100), fundo branco.
  Dois painéis com o mesmo eixo X (data `dd/mm/aa`, rótulo "Data do treino"): em cima "Pace médio dos tiros
  (min/km)", eixo `m:ss` invertido (mais rápido para cima); embaixo "FC média dos tiros (bpm)". Sessão sem FC
  fica sem ponto no painel de FC. Série vazia gera o PNG com "Sem treinos intervalados com tiros de 1 km no
  período".
- `linhas_csv(serie) -> list[dict[str, str]]`: colunas `data, atividade_id, n_tiros, pace_medio_s_km,
  pace_medio_min_km, fc_media`; pace com 1 casa, `m:ss` via `formatar_pace`, FC com 1 casa ou vazia.
- `formatar_pace(s_km) -> "m:ss"` (em `app/metricas/tiros_1km.py`): regra única, ver [[metricas/tiros-1km]].
- Entrada: `list[PontoSessao]` (ver [[metricas/tiros-1km]]).

## Arquivos principais
- `services/api/app/graficos/tiros_1km.py`
- `services/api/app/metricas/tiros_1km.py` (`formatar_pace`)
- Testes: `services/api/tests/metricas/test_grafico_tiros_1km.py`

## Depende de
matplotlib (backend `Agg`, sem display) e de [[metricas/tiros-1km]].

## Como testar
Exemplo gerado com os 2 pontos do oráculo (#30): ![[_anexos/tiros-1km-fixtures.png]]

`uv run pytest -q services/api/tests/metricas/test_grafico_tiros_1km.py`. Os testes usam os 2 pontos do oráculo
da #30 (250,83 s/km e 170,30 bpm; 237,0 s/km e 171,77 bpm).

## Pendências
- Usadas pelo comando `worker.grafico_tiros_1km` ([[modulos/worker]], #15) e pelo endpoint PNG ([[modulos/api]], #16).
- Revisar o desenho com o dado real (#19).
