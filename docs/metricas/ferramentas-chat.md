---
tipo: metrica
status: rascunho
dono: caio
atualizado: 2026-11-28
links: [[decisoes/0017-chat-do-atleta]], [[metricas/evolucao-series]], [[metricas/serie-carga]], [[metricas/linha-base]], [[metricas/checagens-chat]], [[metricas/chat-oraculo]], [[produto/roadmap]], [[glossario]]
---
# Ferramentas do chat sobre as métricas (`ferramentas_chat@1`)

## O que faz
Quatro ferramentas de consulta da [[decisoes/0017-chat-do-atleta]] (item 1), em `app/explicacao/ferramentas_chat.py`. **Nenhuma métrica nova**: cada uma lê o que a API já calcula e
devolve um `dict` com os números em **texto pronto** (`*_texto`, com a unidade), o único texto que o modelo pode citar. Só `SELECT`; o `atleta_id` é parâmetro do código
(a sessão, pelo registro da #593), nunca argumento do modelo. Erro volta como `{"estado": "erro", "codigo": ...}`.

| Ferramenta | Função | Lê | Devolve |
|---|---|---|---|
| `ler_serie` | `serie_evolucao` | `evolucao_serie` (a mesma da rota da Evolução) | pontos do período com `valor_texto` e unidade, o último valor, a faixa do normal e a frase de 4 semanas; `sem_dados` com o motivo se não há ponto |
| `comparar_periodos` | `comparar_periodos` | `frase_evolucao@1` | últimos 28 dias contra os 28 anteriores: valor e `n` de cada um, `direcao` (`maior`, `menor`, `parecido`), `diferenca_texto` e `margem_texto` (o limite de "parecido") |
| `ler_carga_forma` | `carga_e_forma` | `serie_carga@2` e `frase_forma@1` | CTL, ATL, TSB (sinal explícito) e carga do dia, a frase da forma e `estimativa: true`; `parcial` com o aviso "aprendendo" nos 42 primeiros dias |
| `ler_linha_base` | `linha_base` | `linha_base@3` | mediana, `n` e estado de cada métrica do tipo, lidos pelo treino mais recente do tipo; `parcial` sem nenhuma métrica com normal |

## Escolhas e limites (v1)
- **`comparar_periodos` só aceita o par `ultimos_28_dias` e `ultimos_28_dias_anteriores`**, a janela da `frase_evolucao@1`: outro par devolve `comparacao_nao_suportada` com o par válido. É menos que o rascunho da ADR (qualquer par); pares livres pedem uma regra nova de piso e de mínimo e ficam para depois.
- **A carga vai até ontem** (hoje ainda não acabou, `serie_carga@2`): sem `data` ou com data posterior vale o último dia calculado, e o `data_texto` diz qual é; data antes do primeiro dia com carga é `sem_dados`.
- **Ids do catálogo real** (`evolucao_series.POR_ID`): `corrida.volume_km`, `geral.ctl`, `corrida.pace.leve`... O docs/metricas/evolucao-series.md ainda cita séries (`corrida.carga`, `geral.calor`) que não estão no código; o que vale é o código e as fixtures usam só ids dele (teste).
- `ler_serie` recorta qualquer período nomeado ou `de`/`ate`, mas a faixa do normal é sempre a das 12 semanas.
- Datas nos pontos saem como na rota ("qui 14/03").

## Casos à mão
Os valores esperados estão nos comentários de `services/api/tests/explicacao/test_ferramentas_chat.py`: pace leve (R 342 s/km, A 362 s/km, `menor`, 20 s/km, margem 11 s/km), FC (144 contra 152 bpm, 8 bpm, margem 4 bpm),
CTL/ATL/TSB de um treino de carga 100 (2,3528 e 13,3122 no dia; −9,2426 no dia seguinte) e a linha de base com 5 treinos (aprendendo) e com 9 (mediana 5:44/km).

## Fontes e versão
As das métricas lidas: [[metricas/evolucao-series]] (Leys et al. 2013 na mediana e MAD), [[metricas/serie-carga]] (Banister et al. 1976), [[metricas/linha-base]]. `ferramentas_chat@1`.

## Limitações e quando não usar
Não são o registro do chat: o escopo por sessão, os papéis e o esquema dos argumentos são da #593 (Duda). Estas funções assumem que o `atleta_id` já foi conferido.
