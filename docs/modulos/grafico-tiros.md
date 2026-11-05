---
tipo: modulo
status: em-uso
dono: caio
atualizado: 2026-11-04
links: [[metricas/tiros-1km]], [[decisoes/0004-contrato-tela-evolucao]], [[modulos/api]], [[modulos/worker]], [[produto/roadmap]]
---
# Módulo: gráfico dos tiros de 1 km

## Para que serve
Desenha a evolução dos tiros de 1 km (melhor pace e FC do melhor tiro por sessão, com a média como detalhe) e monta as linhas do CSV, a partir de uma
série já calculada. Não acessa banco: a #15 (comando que grava em `entregas/`) e a #16 (endpoint PNG) só leem
a série e chamam estas funções, então o PNG é o mesmo nos dois lugares.

## Entradas e saídas
- `render_png(serie, atleta_nome) -> bytes`: PNG 1600 x 1000 px (figsize 16 x 10, dpi 100), fundo branco.
  Dois painéis com o mesmo eixo X (data `dd/mm/aa`, rótulo "Data do treino"). Valor principal = melhor tiro
  ([[decisoes/0004-contrato-tela-evolucao]], adendo 1, #153):
  - em cima "Pace do melhor tiro (min/km); tracejado: média dos tiros": melhor pace como linha cheia azul
    `#3340B0` (legenda "Melhor tiro (principal)"); a média como linha tracejada cinza `#6B7176`, fina, com
    legenda "Média dos tiros (secundária)". Eixo `m:ss` invertido (mais rápido para cima), faixa mínima de 30 s/km.
  - embaixo "FC do melhor tiro (bpm)": linha magenta `#A3205F`, faixa mínima de 5 bpm. A FC média não aparece
    no PNG, só no CSV. Sessão cujo melhor tiro não tem FC fica sem ponto.
  - A escala dos dois eixos é calculada pelo valor principal (melhor tiro), igual ao bloco `eixos` da API; a
    média pode sair da faixa e é cortada. Ponto sem melhor tiro (montado à mão, sem os campos) só aparece na média.
  Série vazia gera o PNG com "Sem treinos intervalados com tiros de 1 km no período".
- `linhas_csv(serie) -> list[dict[str, str]]`: colunas `data, atividade_id, n_tiros, pace_medio_s_km,
  pace_medio_min_km, fc_media` (média, como antes) e, ao final, `pace_melhor_s_km, pace_melhor_min_km,
  fc_melhor_tiro, ordem_melhor_tiro` (melhor tiro). Pace com 1 casa, `m:ss` via `formatar_pace` sobre o valor sem
  arredondar, FC com 1 casa ou vazia (vazia também se o melhor tiro não tem FC; o melhor tiro não é trocado).
- `escala_eixo(valores, amplitude_minima, passo, rotulo, max_marcas) -> Escala | None` (em
  `app/graficos/escala.py`): regra única da escala dos eixos, usada pelo PNG e, na #66, pelo bloco `eixos` do JSON.
  Veja a seção "Escala mínima dos eixos".
- `formatar_pace(s_km) -> "m:ss"` (em `app/metricas/tiros_1km.py`): regra única, ver [[metricas/tiros-1km]].
- Entrada: `list[PontoSessao]` (ver [[metricas/tiros-1km]]).

## Escala mínima dos eixos (issue #63)
Antes o eixo se ajustava à faixa dos dados, e 1 a 2 bpm de diferença parecia uma subida grande (QA da Meta 1, #18).
Agora `escala_eixo` devolve `min`, `max` e as marcas (`valor` e `rotulo`):

1. Faixa dos dados (maior menos menor) maior ou igual à amplitude mínima: `min` e `max` são os próprios dados.
2. Faixa menor: centro = (menor + maior) / 2 e faixa = centro mais ou menos amplitude / 2.
3. Marcas nos múltiplos do passo dentro da faixa. Passando de 8 marcas, o passo sobe (x2, x5, x10...), sempre
   múltiplo do passo base.
4. Lista vazia ou só `None`: `None` (sem eixo).

| Eixo | Constante | Valor | Passo | Rótulo |
|---|---|---|---|---|
| FC | `AMPLITUDE_MIN_FC_BPM` | 5 bpm (decisão do Angelo, não muda sem ele) | 1 bpm | inteiro |
| Pace | `AMPLITUDE_MIN_PACE_S_KM` | 30 s/km (valor inicial; Caio e Bia podem ajustar, registrando aqui) | 10 s | `formatar_pace` |

Passo da FC: 1 bpm, porque 2 bpm pode dar só 2 marcas numa faixa de 5 (centro 171: 168,5 a 173,5 tem 170 e 172).
Com 1 bpm uma faixa de 5 sempre tem 5 ou 6 marcas.

Passo do pace: 10 s/km desde a #87 (era 15, que dava só 2 marcas na faixa mínima: centro 241, faixa 226 a 256, marcas
240 e 255). Uma faixa de 30 s/km contém sempre 3 marcas (ou 4 quando as pontas são múltiplos de 10), então a regra
"pelo menos 3 marcas na faixa mínima" vale para qualquer centro.

Exemplos à mão: FC 170 e 171 (faixa 1): centro 170,5, faixa 168 a 173, marcas 168 a 173. Pace 240 e 242:
centro 241, faixa 226 a 256, marcas 230 ("3:50"), 240 ("4:00") e 250 ("4:10"). FC de 150 a 180 (faixa 30): os dados; passo 1 dá 31
marcas, x2 dá 16, x5 dá 7 (150, 155, ..., 180). Mudar uma constante muda o contrato: ver
[[decisoes/0004-contrato-tela-evolucao]].

## Arquivos principais
- `services/api/app/graficos/tiros_1km.py`
- `services/api/app/graficos/escala.py` (`escala_eixo`, `escala_pace`, `escala_fc` e as constantes)
- `services/api/app/metricas/tiros_1km.py` (`formatar_pace`)
- Testes: `services/api/tests/metricas/test_grafico_tiros_1km.py` e `services/api/tests/metricas/test_escala_eixo.py`

## Depende de
matplotlib (backend `Agg`, sem display) e de [[metricas/tiros-1km]].

## Como testar
Exemplo gerado com os 2 pontos do oráculo (#30): ![[_anexos/tiros-1km-fixtures.png]]

`uv run pytest -q services/api/tests/metricas/test_grafico_tiros_1km.py`. Os testes usam os 2 pontos do oráculo
da #30 (média: 250,83 s/km e 170,30 bpm; 237,0 s/km e 171,77 bpm) e da #151 (melhor tiro: 248,0 s/km "4:08" e
FC 175; 234,0 s/km "3:54" e FC 177). O teste do worker confere o CSV gerado a partir das fixtures com esses valores.

## Pendências
- Usadas pelo comando `worker.grafico_tiros_1km` ([[modulos/worker]], #15) e pelo endpoint PNG ([[modulos/api]], #16).
- Revisar o desenho com o dado real (#19).
