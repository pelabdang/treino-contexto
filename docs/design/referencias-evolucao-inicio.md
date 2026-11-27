---
tipo: design
status: rascunho
dono: lia
atualizado: 2026-11-27
links: [[design/telas/evolucao-v1]], [[design/telas/inicio-v4]], [[design/identidade-visual-v3]], [[design/auditoria-ux-e-inicio-do-atleta]], [[metricas/evolucao-series]]
---
# Referências para a Evolução e o Início (Strava, Garmin e uma terceira)

Três referências para a [[design/telas/evolucao-v1]] e o [[design/telas/inicio-v4]]. **Escrito de memória, sem abrir os apps hoje** (o repositório é público:
nada de print nem dado real aqui). Os detalhes das versões atuais dos apps podem ter mudado; conferir com o Angelo se alguma decisão depender de um deles.
Roubamos a **ideia**, não o desenho. O que não queremos também está dito.

## Strava: escolher esporte e métrica, barras por semana
- **O que o app faz:** a tela de progresso deixa escolher o esporte e a métrica (distância, tempo, ganho de elevação) e mostra barras por semana.
  A linha do tempo de aptidão ("Fitness") mostra a tendência de longo prazo com o dia selecionado.
- **O que levamos:** "esporte primeiro, métrica depois" (nosso seletor em dois passos); barra por semana para volume ([[metricas/evolucao-series]], `volume`); tocar numa barra ou ponto para ver o valor.
- **O que não levamos:** o placar social (curtidas, segmentos, rankings) e métricas que nós não calculamos. Nada de "esforço relativo" com número solto.

## Garmin Connect: cartões do dia e a faixa do normal
- **O que o app faz:** a tela de hoje é uma lista de cartões que o usuário **reordena e esconde**; estados como o de VFC mostram um **intervalo "equilibrado" sombreado**
  com o valor do dia dentro ou fora dele, e a avaliação "treino produtivo", "recuperação" usa cores.
- **O que levamos:** a **faixa do normal sombreada** no gráfico (é exatamente o nosso desenho); cartão curto com número grande e uma linha; cartões que **somem** quando falta dado do relógio.
- **O que não levamos:** o julgamento por cor e rótulo ("improdutivo", "excelente"). Nós descrevemos a direção, nunca bom ou ruim. Reordenar cartões fica como **pergunta ao Angelo**; a recomendação é não começar por isso.

## Apple Saúde (Sinais vitais e Tendências): a faixa típica
- **O que o app faz:** mostra cada medida com a **faixa típica** da pessoa e destaca só o que saiu dela; frases curtas de tendência ("acima da sua média") sem juízo de valor.
- **O que levamos:** o tom: frase curta que **descreve**; ponto fora da faixa destacado com forma e texto, sem alarme; nada aparece se não há dado suficiente.
- **O que não levamos:** a explicação médica; não somos serviço de saúde ([[design/identidade-visual-v3]] e a regra de linguagem do projeto).

## Resumo do que entra no desenho
| ideia | origem | onde está |
|---|---|---|
| esporte e depois série | Strava | seletor em dois passos |
| faixa do normal sombreada, valor do dia | Garmin e Apple Saúde | gráfico da Evolução |
| cartões que somem sem dado | Garmin | Início v4 |
| frase curta que descreve | Apple Saúde | frase no topo da Evolução |
| barra por semana | Strava | cartão "Volume das 4 semanas" |
