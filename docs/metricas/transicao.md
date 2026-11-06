---
tipo: metrica
status: rascunho
dono: caio
atualizado: 2026-11-06
links: [[decisoes/0009-treino-de-transicao]], [[decisoes/0005-serie-de-tiros-o-que-entra]], [[decisoes/0003-fuso-da-atividade]], [[metricas/esforcos]], [[produto/roadmap]], [[glossario]]
---
# Treino de transição: regra que sugere o rótulo (`transicao@1`)

## O que mede
Diz se uma atividade provavelmente faz parte de um **treino de transição** (brick): uma modalidade logo seguida de outra, gravadas pelo
relógio como atividades separadas ([[decisoes/0009-treino-de-transicao]]). É uma **sugestão**: o atleta corrige depois, e a correção sempre vence.
A regra só sugere "sim"; quem não aparece no resultado fica sem rótulo. Cálculo determinístico, em código, sem banco e sem IA.

## Fórmula
Função pura `sugerir_transicao(atividades)` em `services/api/app/metricas/transicao.py`. Entrada: registros leves de **um** atleta
(`id`, `modalidade`, `inicio` com fuso, `duracao_s`); saída: o conjunto de `id` sugeridos. Constantes iguais para todos os atletas
(ADR 0005, item 2); fonte: regra própria do projeto, sem artigo (decisão do Angelo em 04/11 e 06/11).

| Constante | Valor | Papel |
|---|---|---|
| `MODALIDADES_DE_TRANSICAO` | corrida, natação, ciclismo | `outra` fica fora e nem corta a vizinhança |
| `INTERVALO_MAX_S` | 1800 (30 min) | maior intervalo estimado aceito |
| `SOBREPOSICAO_MAX_S` | 60 | maior sobreposição aceita |

Passos:
1. Descarte as atividades de modalidade fora de `MODALIDADES_DE_TRANSICAO` e ordene o resto por `inicio` (empate por `id`).
2. `fim = inicio + duracao_s` (mínimo 0). Vá em ordem guardando o **maior fim já visto** e as atividades que o têm.
3. Para cada atividade, `intervalo = inicio - maior_fim` (em segundos). Se `-60 <= intervalo <= 1800`, ela forma par com cada atividade que
   tem o maior fim e **modalidade diferente da sua**; as duas entram no resultado (uma atividade em dois pares entra uma vez).
4. Compare com o maior fim, e não só com a vizinha imediata: uma atividade aninhada ou duplicada dentro de outra não esconde a transição real.
5. A cadeia sai transitiva: ciclismo, corrida e natação seguidas sugerem as três. Duas seguidas da mesma modalidade não formam par.

Sem condição de mesmo dia local (ADR 0009): a virada da meia-noite funciona porque a conta é em instantes.

## Dados de entrada
`modalidade`, `inicio` (UTC) e `duracao_s` da atividade (tempo em movimento; `duration` do resumo, `total_timer_time` no FIT). Não usa `fuso_min`, distância, FC nem subtipo.
Como a duração é tempo em movimento, o fim estimado é igual ou anterior ao real e o intervalo estimado é **maior ou igual** ao real.

## Referência
Sem artigo: é uma regra de produto. Base: [[decisoes/0009-treino-de-transicao]] (itens 2 e 3).

## Código e teste
- Código: `services/api/app/metricas/transicao.py`
- Teste: `services/api/tests/metricas/test_transicao.py` (fixtures sintéticas; valores esperados calculados à mão, nos comentários)

Exemplos à mão (A = ciclismo, B = corrida; todos sintéticos):

| Atividades | Intervalo | Resultado |
|---|---|---|
| A 07:00 a 08:00, B 08:02 | 120 s | A e B |
| A 07:00 a 08:00, B 08:30:00 | 1800 s (limite, inclusive) | A e B |
| A 07:00 a 08:00, B 08:30:01 | 1801 s | nenhuma |
| A 07:00 a 08:00, B 08:40 | 2400 s | nenhuma |
| A 07:00 a 08:00, B 07:59:00 | -60 s (limite, inclusive) | A e B |
| A 07:00 a 08:00, B 07:58:59 | -61 s | nenhuma (duplicata ou dois aparelhos) |
| A 07:00 a 08:00, B 08:02 a 08:30, A 08:34 | 120 s e 240 s | as três |
| A 07:00 a 07:50, A 07:52 | 120 s, mesma modalidade | nenhuma |
| A 07:00 a 08:00, A' aninhada 07:10 a 07:20, B 08:02 | 120 s contra A (2520 s contra A') | A e B (A' não entra) |
| A 07:00 a 08:00 duplicada, B 08:02 | 120 s | as duas A e B |
| A 23:40 a 23:55, B 00:00 no dia seguinte | 300 s | A e B |

## Limitações e quando não usar
**Falsos positivos esperados** (a regra sugere, o atleta corrige):
- **Deslocamento de bicicleta** (ir de bicicleta ao local da corrida, ou voltar dele) gravado como atividade: ciclismo seguido de corrida em menos de 30 min parece brick.
- **Pedal leve de volta** depois de um treino de corrida, ou uma corrida curta depois de um pedal sem ligação com ele.
- Duas atividades sem relação coladas no tempo (por exemplo, natação na piscina e corrida logo depois, em horários que apenas coincidem).
- Sobreposição entre 0 e 60 s causada por dois aparelhos gravando a mesma sessão com modalidades diferentes.

**Falsos negativos esperados**:
- **Pausa maior que 30 min** entre as partes (troca de equipamento, fila, descanso): o intervalo estimado passa de `INTERVALO_MAX_S` e nada é sugerido. O atleta pode marcar "sim".
- Partes com modalidade `outra` (o relógio ou o `tipos.py` não reconhece a modalidade): ficam fora.
- Parte única gravada sozinha (a outra parte não foi gravada): sem par, sem sugestão.

**Estimativa do fim:** com pausa automática ligada, o fim real é depois de `inicio + duracao_s`; o intervalo mostrado fica maior que o real. Por isso o -60 s não compensa essa diferença.
**Não usar** para decidir carga ou nota: é só um rótulo. Mudança de regra ou de constante sobe a versão (`transicao@2`) e exige rodar o comando de #157; correções do atleta não são tocadas.
