---
tipo: metrica
status: rascunho
dono: caio
atualizado: 2026-11-28
links: [[decisoes/0017-chat-do-atleta]], [[metricas/evolucao-series]], [[metricas/serie-carga]], [[metricas/linha-base]], [[metricas/checagens-chat]], [[metricas/chat-oraculo]], [[produto/roadmap]], [[glossario]]
---
# Ferramentas do chat sobre as métricas (`ferramentas_chat@1`)

## O que faz
Cinco ferramentas de consulta da [[decisoes/0017-chat-do-atleta]] (item 1), em `app/explicacao/ferramentas_chat.py`. **Nenhuma métrica nova**: cada uma lê o que a API já calcula e
devolve um `dict` com os números em **texto pronto** (`*_texto`, com a unidade), o único texto que o modelo pode citar. Só `SELECT`; o `atleta_id` é parâmetro do código
(a sessão, pelo registro da #593), nunca argumento do modelo. Erro volta como `{"estado": "erro", "codigo": ...}`.

| Ferramenta | Função | Lê | Devolve |
|---|---|---|---|
| `ler_serie` | `serie_evolucao` | `evolucao_serie` (a mesma da rota da Evolução) | pontos do período com `valor_texto` e unidade, o último valor, a faixa do normal e a frase de 4 semanas; `sem_dados` com o motivo se não há ponto |
| `comparar_periodos` | `comparar_periodos` | `frase_evolucao@1` | dois períodos de mesmo tamanho (ver abaixo): valor e `n` de cada um, `direcao` (`maior`, `menor`, `parecido`), `diferenca_texto`, `diferenca_pct_texto` e `margem_texto` (o limite de "parecido") |
| `ler_carga_forma` | `carga_e_forma` | `serie_carga@2` e `frase_forma@1` | CTL, ATL, TSB (sinal explícito) e carga do dia, a frase da forma e `estimativa: true`; `parcial` com o aviso "aprendendo" nos 42 primeiros dias |
| `ler_recuperacao` | `recuperacao_noites` | `recuperacao@1` e os textos do pacote de fatos | sono, VFC e FC de repouso de cada noite do período (as 14 mais recentes, padrão 7 dias) contra a mediana das 28 noites anteriores: valor, normal, diferença ("abaixo" e "acima" são direção, nunca bom ou ruim) e `texto` pronto; `aprendendo` com menos de 14 noites; `sem_dados` se nada foi importado. Só do papel atleta |
| `ler_linha_base` | `linha_base` | `linha_base@3` | mediana, `n` e estado de cada métrica do tipo, lidos pelo treino mais recente do tipo; `parcial` sem nenhuma métrica com normal |

## Escolhas e limites (v1)
- **`comparar_periodos` compara dois períodos de mesmo tamanho.** Nomes aceitos: `ultimos_7_dias`, `ultimos_14_dias`, `ultimos_28_dias`, `ultimas_12_semanas` (terminam **ontem**, como a `frase_evolucao@1`),
  cada um com o sufixo `_anteriores` (a janela de igual tamanho logo antes), `esta_semana` (segunda até hoje), `semana_passada`, `semana_retrasada`, `este_mes`, `mes_passado` e um mês de calendário `AAAA-MM`.
  `periodo_a` é o lado "de agora" (a `direcao` diz se o valor de `a` é maior, menor ou parecido com o de `b`).
- **Estatística por tipo de série**, sobre os valores mostrados (as regras da `frase_evolucao@1`): treino e tiros = mediana dos treinos, limite de "parecido" da série (pace 3%, FC 4 bpm, velocidade e eficiência 3%); volume = **média por semana** (total / (dias / 7)), limite 10%; condicionamento = o valor do último dia, limite max(2; 5%). Diferença absoluta (`diferenca_texto`) e em % do valor de `b` (`diferenca_pct_texto`).
- **Para 28 contra 28 o resultado é o da `frase_evolucao@1`**, não uma segunda conta (no volume, a mediana das 4 somas semanais; o `medida_texto` diz qual). Um teste confere que a estatística dos períodos livres dá o mesmo valor mostrado para a janela de 28 dias.
- **Poucos treinos:** com menos de 3 treinos em um dos períodos (2 nos tiros; 1 semana de volume), o resultado é `parcial`: traz os valores e o `n`, o `motivo_texto` ("Poucos treinos para comparar...") e **nenhuma `direcao`**, então o modelo não pode afirmar uma comparação.
- **Semana ou mês em curso** (`esta_semana`, `este_mes`, ou o mês de calendário atual) é comparado com os **mesmos primeiros dias** do outro período (o `corte_texto` avisa). Dois meses de calendário de tamanhos diferentes (28 a 31 dias) podem ser comparados: a mediana não depende do tamanho e o volume já é por semana.
- **`comparacao_nao_suportada`, só nestes casos:** tamanhos diferentes (7 dias contra 14, semana contra mês) e períodos que se sobrepõem. Nome desconhecido ou mês no futuro é `argumento_invalido`, com a lista dos nomes válidos. A estatística faz sentido nos demais pares; não há outra exclusão.
- **A carga vai até ontem** (hoje ainda não acabou, `serie_carga@2`): sem `data` ou com data posterior vale o último dia calculado, e o `data_texto` diz qual é; data antes do primeiro dia com carga é `sem_dados`.
- **Ids do catálogo real** (`evolucao_series.POR_ID`): `corrida.volume_km`, `geral.ctl`, `corrida.pace.leve`... O docs/metricas/evolucao-series.md ainda cita séries (`corrida.carga`, `geral.calor`) que não estão no código; o que vale é o código e as fixtures usam só ids dele (teste).
- `ler_serie` recorta qualquer período nomeado ou `de`/`ate`, mas a faixa do normal é sempre a das 12 semanas.
- Datas nos pontos saem como na rota ("qui 14/03").

## Casos à mão
Os valores esperados estão nos comentários de `services/api/tests/explicacao/test_ferramentas_chat.py`: pace leve (R 342 s/km, A 362 s/km, `menor`, 20 s/km, 6%, margem 11 s/km), esta semana contra a passada cortada em 5 dias (344 e 360 s/km, 16 s/km, 4%), este mês contra fevereiro cortado, janeiro contra fevereiro no volume (3,8 e 1,1 km por semana, 245%), poucos treinos sem direção, FC (144 contra 152 bpm, 8 bpm, margem 4 bpm),
CTL/ATL/TSB de um treino de carga 100 (2,3528 e 13,3122 no dia; −9,2426 no dia seguinte) e a linha de base com 5 treinos (aprendendo) e com 9 (mediana 5:44/km).

## Links para a Evolução
A rota do chat monta o "Abrir na Evolução" a partir do `serie_id` que aparece nos resultados. `ler_serie` e `comparar_periodos` devolvem `serie_id` no nível de cima, em `ok`, `parcial` e `sem_dados` (teste em `tests/chat/test_ferramentas_metricas.py`); nada a ajustar do lado da rota. O link do treino usa `atividade_id` e `data_texto` do mesmo objeto: os pontos de `ler_serie` trazem os dois, com a data como "qui 14/03" (a mesma data que o texto precisa citar).

## Fontes e versão
As das métricas lidas: [[metricas/evolucao-series]] (Leys et al. 2013 na mediana e MAD), [[metricas/serie-carga]] (Banister et al. 1976), [[metricas/linha-base]]. `ferramentas_chat@1`.

## Registro e escopo
`app/chat/ferramentas_metricas.py` registra as quatro funções no registro da #593 ([[modulos/api]]): o esquema não tem campo de atleta e recusa argumento extra; o `atleta_id` e o "hoje" vêm da `Consulta`.
`ler_serie` e `comparar_periodos` são só do papel `atleta` (o professor não vê a Evolução); `ler_carga_forma` e `ler_linha_base` valem para os dois; `ler_recuperacao` (sono e VFC são dado de saúde) é só do atleta. Testes de escopo em `tests/chat/test_ferramentas_metricas.py`.

## Limitações e quando não usar
É lista fechada de períodos: pergunta sobre um intervalo livre ("de 3 a 9 de fevereiro") usa `ler_serie` com `de` e `ate`, mas `comparar_periodos` só aceita os nomes acima e o mês `AAAA-MM`. Os valores são de séries com
poucos treinos por período (semana): o resultado diz o `n` e, abaixo do mínimo, não dá direção.
