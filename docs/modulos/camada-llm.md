---
tipo: modulo
status: em-uso
dono: duda
atualizado: 2026-11-15
links: [[decisoes/0013-feedback-automatico]], [[metricas/checagens-feedback]], [[modulos/api]], [[modulos/worker]], [[produto/roadmap]]
---
# Módulo: camada de LLM

## Para que serve
A única porta do produto para um modelo de linguagem (regra do `AGENTS.md`: IA sempre por uma camada trocável, nunca provedor direto no código). Meta 9, issue #326; quem usa é o `worker.gerar_feedback` (#327, [[modulos/worker]]; o prompt fixo `feedback_prompt@3` está em `app/llm/prompt_feedback.py`). Código em `services/api/app/llm/camada.py`. A [[decisoes/0013-feedback-automatico]] (`aceita` em 10/11) decide o uso; esta nota descreve o que o módulo faz.

## Entradas e saídas
- `criar_redator()` monta o `Redator` do `.env`; `Redator.redigir(sistema, pacote)` recebe o prompt fixo e o pacote (dicionário, vira JSON) e **nunca levanta**; o texto que volta já vem limpo (`limpar_texto`: sem espaços no fim de cada linha nem nas pontas, #367, porque o provedor de verdade devolveu dois espaços no fim de cada linha e o texto era gravado assim): devolve `ResultadoLLM(texto, motivo, provedor, modelo)`. Ou há `texto`, ou há um `motivo`:

| `motivo` | quando |
|---|---|
| `provedor_nao_configurado` | sem `LLM_MODEL`, sem chave do provedor, provedor vazio ou desconhecido |
| `provedor_tempo_limite` | passou de `LLM_TIMEOUT_S` (padrão 20 s) |
| `provedor_erro` | qualquer outra falha (rede, limite do plano gratuito, 429, resposta vazia) |
| `limite_de_chamadas` | a execução já fez `LLM_LIMITE_CHAMADAS` (padrão 20) chamadas; a chamada acima do limite nem vai ao provedor |

São os mesmos códigos do `CHECK` previsto para `feedback_treino` ([[decisoes/0013-feedback-automatico]]). `texto_reprovado` não é daqui: é do worker, depois das checagens.
- **Provedor falso** (`LLM_PROVIDER=falso`): sem rede e sem chave, obrigatório em testes e CI. Devolve um texto fixo de 3 linhas que **passa na `checar_texto` real** (`checagens_feedback@4`) com um pacote comum: cada linha tem verbo da lista (com acento: "é", "foi"), sem número; com o atalho `dor` reprova por `dor_regra`, porque não traz a frase da dor (#361; teste em `test_camada.py` com as checagens reais, sem `checar` injetada). Quem mudar as checagens confere esse texto; `ProvedorFalso(modo="ruim")` devolve um texto de propósito reprovável, e os modos `erro`, `tempo` e `vazio` simulam falhas. O resultado leva `provedor = "falso"`.

## Regras
- **Troca só pelo `.env`:** `LLM_PROVIDER` (`groq`, `openai`, `anthropic` ou `falso`), `LLM_MODEL` e a chave (`GROQ_API_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`). O LiteLLM recebe `<provedor>/<modelo>` e a chave explícita. Padrão: `groq`. `.env.example` só com os nomes.
- **Sem nova tentativa dentro da chamada** (`num_retries=0`): a próxima execução do worker é a nova tentativa.
- **Nada do conteúdo em log, saída ou exceção** (o pacote e o texto são dado de saúde): o erro vira `motivo` pela **classe** da exceção e a mensagem é descartada. O LiteLLM é configurado para não registrar conteúdo: `litellm.turn_off_message_logging = True`, `litellm.redact_messages_in_exceptions = True`, `litellm.suppress_debug_info`, listas de *callbacks* vazias e os loggers `LiteLLM` e `httpx` em CRITICAL (o padrão do LiteLLM é DEBUG). Teste com um marcador sintético no prompt, no pacote e na resposta ou erro, em sucesso e em cada falha.
- **Dois cuidados com a importação do LiteLLM** (conferidos no código da 1.108.4, e por isso a camada define as variáveis **antes** de importar): `LITELLM_LOCAL_MODEL_COST_MAP=True` (sem isso a importação baixa a tabela de preços da internet; o teste de rede falhou até isso entrar) e `LITELLM_MODE=PRODUCTION` (no modo padrão a importação carrega o `.env` mais próximo para dentro de `os.environ`, o que misturaria credenciais de outros módulos e sobreporia a configuração). Importe o LiteLLM só pela camada.
- A chave é `SecretStr` em `app/config.py` (não aparece em `repr`).
- **Dado de saúde que sai da máquina:** com provedor real, o pacote de fatos vai ao provedor. O que o Groq diz sobre retenção e o que **não foi conferido** está na [[decisoes/0013-feedback-automatico]], "A confirmar", item 10; a regra do projeto é: provedor real só no computador do Angelo, com o "sim" dele, e provedor falso em CI e testes.

## Quem usa: `app/servicos/feedback.py` e `worker.gerar_feedback` (#327)
`gerar(session, atleta_id, redator, montar_pacote, checar, versoes, prompt, refazer)` (em `app/servicos/feedback.py`) recebe o pacote e as checagens por **injeção**:
- `montar_pacote(session, atividade, checkin) -> dict | None` (o pacote `fatos_treino@2`; `None` se não há check-in ou a atividade não é elegível);
- `checar(pacote, texto) -> str | None` (`None` se o texto passa; senão o **primeiro** código de motivo; a linha guarda só `texto_reprovado`, nunca o texto nem o código do termo).

Na linha de comando, os padrões são os reais: `app.servicos.feedback_fatos.fatos_da_atividade` (o **adaptador** que lê o banco e chama a função pura `app.explicacao.fatos_treino.fatos_treino`, #324), `app.explicacao.checagens.checar` (#325) e as `VERSAO` dos dois módulos. O adaptador usa os serviços de leitura que a API já tem (`linha_base_resultado`, `clima_da_atividade`, `carga_da_atividade`, `esforcos_da_atividade`, rótulo de transição) e não recalcula nada; natação fica sem bloco de clima. Desde a #374 ele também passa a recuperação (`app/servicos/recuperacao_pacote.py`, ver [[metricas/fatos-treino]]). Teste: o pacote que sai do banco semeado com as fixtures da meta 9 é igual ao do oráculo, com `recuperacao = sem_noite` (`services/api/tests/servicos/test_feedback_fatos.py`).

## Prompt `feedback_prompt@7` (`app/llm/prompt_feedback.py`)
Regras de forma, tom e do que falta no pacote, mais os **6 exemplos aprovados** (G01 a G06, pacote reduzido sem campos nulos e texto da ADR 0013). Os exemplos têm **fonte única** em `app/llm/exemplos_feedback.py`; um teste confere o texto contra `tests/fixtures/meta9/textos.py`, o pacote contra o oráculo e que cada texto passa nas checagens. Estimativa da época do `@1`: uns 2,5 mil tokens. Medido na rodada da #376 com o `@5`: cerca de 4.300 tokens (ver a seção da rodada e o teste de tamanho, abaixo). Se o texto mudar de forma relevante, a `VERSAO` sobe.

**`@7` (15/11, #403):** duas regras de redação: a frase "Ainda aprendendo o seu normal de ...: N de 14 noites." é **obrigatória** quando há medida `aprendendo` (com as três, duas linhas curtas), e FC, VFC e PSE são femininas ("a FC", "sua FC média"). Acompanha as `checagens_feedback@5` ([[metricas/checagens-feedback]]). O prompt foi a 14.260 caracteres (cerca de 4.320 tokens a 3,3), dentro do teste de tamanho.

**`@6` (14/11, #394):** a recuperação em **duas linhas**, decisão do Angelo de 13/11 depois da rodada da #376 (as três medidas numa linha passavam de 140 caracteres): linha 1 o sono, linha 2 a FC de repouso e a VFC; uma medida só, uma linha; `aprendendo` com "Na noite anterior você dormiu X." antes de "Ainda aprendendo o seu normal de sono: N de 14 noites."; o máximo de 5 linhas continua e o prompt manda juntar clima e carga e cortar o menos importante quando há recuperação. As `checagens_feedback@4` **não mudaram** (a forma nova já passava; textos novos em `tests/fixtures/meta10/textos_recuperacao.py`, 3 bons e 3 ruins). Tamanho: os exemplos aprovados saem do prompt **sem os campos numéricos que repetem o `*_texto`** (`valor`, `duracao_s`, `distancia_m`, `sensacao_nivel`, `parte_de_transicao`, `treino_chave`); os textos aprovados e as regras ficaram. O prompt foi de 13.766 para 13.311 caracteres; depois da rodada da #394 ele ganhou 3 esclarecimentos de redação (medida `dentro` sem diferença, as três dentro em uma linha, uma medida também com "Na noite anterior") e ficou com 13.737 (cerca de 4.160 tokens a 3,3), ver a seção da rodada.

**`@5` (13/11, #375):** a regra da recuperação (ADR 0014, item 6): a noite anterior numa linha própria, com os `*_texto` do pacote e só "abaixo/acima/dentro do seu normal"; `aprendendo` sem comparar; frase pronta do `sem_noite`; nada sobre recuperação em madrugada, `fora_do_periodo` ou sem o bloco; sem causa, conselho, julgamento nem outro dia. Os 6 exemplos aprovados não mudaram (as frases da regra são as da ADR). O teste de tamanho (#395) conta 3,3 caracteres por token e exige prompt + pacote (até 1.500 tokens) + `LLM_MAX_TOKENS` (padrão 1200) abaixo de 8.000, o limite por minuto do plano gratuito; o `@5` tem cerca de 4.170 tokens e passa. A rodada da #376 mediu cerca de 4.300. Checagens em [[metricas/checagens-feedback]] (`@4`).

**`@4` (12/11, #374):** acompanha o `fatos_treino@2`: sem rótulo (PSE 6, 8 e 9), `checkin.pse_texto` vem nulo (ou ausente nos exemplos, que não trazem campos nulos) e a regra manda escrever só o número de `checkin.pse`. Os exemplos G02 e G03 perderam o `pse_texto` repetido; os textos aprovados não mudaram.

**`@3` (12/11, #367):** uma regra nova: quando `checkin.pse_texto` é só o número (PSE 6, 8 e 9 não têm rótulo), escrever "esforço 6", nunca "esforço 6 (6)". Origem e checagem em [[metricas/checagens-feedback]] ("Versão `@3`"). O pacote não mudou.

**`@2` (11/11, #355):** a primeira rodada com o provedor de verdade deu textos aprovados nas checagens, mas telegráficos. O `@2` acrescenta regras de forma: toda linha com verbo conjugado (nada de lista de valores); quando a linha de base tem métrica `dentro` ou `fora`, a primeira linha traz valor e mediana, com o número de treinos e a janela; não repetir a mesma conclusão em duas linhas; do clima, só o essencial; o que falta é dito com dois-pontos, sem "pois" nem "porque". Também fixa o nome e o gênero de cada métrica ("sua FC média", "seu pace médio", "a carga por hora"), depois de uma resposta com erro de concordância. O prompt passou a uns 2,9 mil tokens (estimativa). **Medição com `feedback_prompt@2` e `checagens_feedback@2`, com 42 s entre chamadas (local, só fixtures; contagens):** 8 respostas, nenhuma recusa, 7 aprovadas e 1 reprovada (`linguagem_causa` e `forma_sem_verbo`). Medição anterior, com as checagens `@1`: com os 8 pacotes do oráculo no provedor (só fixtures; contagens): com o `@1`, 5 respostas e 5 aprovadas, 3 chamadas recusadas pelo provedor; com o `@2`, 6 respostas e 6 aprovadas, todas com valor e mediana na primeira linha quando havia comparação, 2 chamadas recusadas. As recusas vieram com chamadas a cada 12 s e a cada 28 s: sinal de limite por minuto do provedor (não conferido na documentação dele). **Mudar a versão do prompt não desatualiza o que já está `pronto`** (só `versao_fatos` e a edição do check-in desatualizam): para reescrever com o prompt novo, `worker.gerar_feedback --refazer`.

## Rodada com o provedor de verdade, Meta 10 (13/11, #376)
Só pacotes sintéticos (fixtures da meta 9 com os blocos `recuperacao` do oráculo da meta 10), sem banco, `feedback_prompt@5` e `checagens_feedback@4`, provedor Groq (`openai/gpt-oss-120b`, plano gratuito). **10 chamadas, 4 aprovadas e 6 reprovadas** (5 por `forma_tamanho_linha`, 1 por `recuperacao_forma`), nenhuma recusa por limite na rodada final.
Casos: abaixo/dentro/acima (R01, 5 chamadas, em 4 treinos diferentes), `aprendendo` (R02), `sem_noite` (R04), madrugada (R05), `fora_do_periodo` (R06) e todas dentro do normal (1 chamada).
- **Aprovados (4):** `sem_noite` (a frase pronta saiu exata), madrugada e `fora_do_periodo` (o texto não falou de sono, VFC nem FC de repouso) e "todas dentro do normal" (copiou os `*_texto`, sem causa nem conselho).
- **Reprovados por tamanho (5):** a linha da recuperação com as três medidas passa de 140 caracteres ("Na noite anterior você dormiu 5 h 45 min, 1 h 30 min abaixo do seu normal de 7 h 15 min, VFC 41 ms dentro do seu normal e FC de repouso 58 bpm, 6 bpm acima do seu normal de 52 bpm."). O texto em si estava certo: números do pacote, linha própria, sem causa, conselho nem julgamento. **A causa é o prompt**, que manda juntar as medidas numa linha ("junte as medidas dela numa linha"), o que não cabe nos 140 caracteres.
- **Reprovado por forma (1):** `aprendendo` saiu "Ainda aprendendo o seu normal de sono: 6 h 20 min." sem "noite anterior" (a regra 2 exige a expressão numa linha da recuperação) e sem o "N de 14 noites".
- **Falso positivo ou texto ruim que passou:** nenhum visto nas 10. As checagens novas não reprovaram texto bom por linguagem; nenhum texto ligou a noite ao resultado nem aconselhou.
- **Achado do provedor (importante):** o prompt tem ~4.300 tokens reais e o pacote com a recuperação passa de 5.100 no total; o teste `len(TEXTO)/4 < 3500` subestima (português: ~3,3 caracteres por token). Com a configuração da época da rodada (sem `max_tokens`) o provedor soma o teto de saída ao pedido: **8.184 pedidos contra o limite de 8.000 por minuto** ("Request too large"), e quando passa, o modelo de raciocínio gasta os ~3.000 tokens de saída pensando e devolve **texto vazio** (`provedor_erro`). A rodada só funcionou com `reasoning_effort=low` e `max_tokens=1200` (3 s por chamada). **Esses dois parâmetros foram passados só num script local da rodada, que não está no repositório; a camada da época não passava nenhum dos dois** (o `extra` do `ProvedorLiteLLM` existe só para testes). Cada chamada consome 5 a 6 mil dos 8.000 tokens por minuto: **40 s de pausa não bastam, usei 65 s**.
- **Propostas (da rodada; situação logo abaixo):** (1) o prompt manda a recuperação em duas linhas (sono; VFC e FC de repouso), com um exemplo, e o `aprendendo` com "Na noite anterior você dormiu X." antes; (2) a camada passa `max_tokens` e `reasoning_effort` ao Groq (hoje o `extra` do `ProvedorLiteLLM` só existe para testes); (3) o teste do tamanho do prompt passa a contar com 3,3 caracteres por token, ou o prompt encolhe; (4) `LLM_INTERVALO_S` sugerido de 65 s no plano gratuito. Um `feedback_prompt@6` e a mudança na camada são decisões do Theo.
- **Situação:** aplicadas na #395 (PR #399): a 2 (a camada passa `max_tokens` e `reasoning_effort`, ver "Teto de saída e esforço de raciocínio"), a 3 (teste de tamanho com 3,3 caracteres por token) e a 4 (`LLM_INTERVALO_S=65` no `.env.example`). A 1 (`feedback_prompt@6`, recuperação em duas linhas) é a #394, PR #398; a rodada dela está na seção seguinte.

## Teto de saída e esforço de raciocínio (#395)
A camada passa ao LiteLLM, em toda chamada, o teto de saída e o esforço de raciocínio do `.env`:

| Variável | Padrão | Efeito |
|---|---|---|
| `LLM_MAX_TOKENS` | `1200` | `max_tokens` da chamada. `0` ou negativo = não envia. |
| `LLM_REASONING_EFFORT` | `low` | `reasoning_effort` (`low`, `medium`, `high`, conforme o modelo). Vazio = não envia. |
| `LLM_INTERVALO_S` | `0` (no código); `65` no `.env.example` | Pausa entre chamadas. No plano gratuito do Groq (8.000 tokens por minuto) use 65. |

- **Por quê.** O provedor soma o teto de saída ao tamanho do pedido contra o limite por minuto. Prompt (~4.200 tokens) + pacote (~800) + teto padrão do modelo passava de 8.000 ("Request too large"). E o modelo de raciocínio, sem `reasoning_effort=low`, gasta a saída pensando e devolve texto vazio. Com 1200 e `low` a rodada da #376 fechou (3 s por chamada).
- **Modelo que não aceita `reasoning_effort`.** Quando o parâmetro está definido, a chamada leva também `drop_params=True`: o LiteLLM descarta o que o modelo não suporta (conferido na 1.108.4: sem isso, `groq/llama-3.3-70b-versatile` levanta `UnsupportedParamsError` e o feedback viraria `provedor_erro`). O teto (`max_tokens`) é aceito por todos. Para nunca enviar o esforço, deixe `LLM_REASONING_EFFORT=` vazio.
- **Texto vazio** continua `provedor_erro`, sem texto e sem gravar nada (teste).
- **Tamanho do prompt.** O teste conta 3,3 caracteres por token (português) e exige prompt + pacote (até 1.500 tokens) + `LLM_MAX_TOKENS` abaixo de 8.000.

## Rodada com o provedor de verdade, `feedback_prompt@6` (14/11, #394)
Mesmo formato da #376, só pacotes sintéticos (fixtures da meta 9 com os blocos da meta 10), sem banco, com a **camada do `main`** (#395): `LLM_MAX_TOKENS=1200`, `LLM_REASONING_EFFORT=low` e `LLM_INTERVALO_S=65` vieram do ambiente, nenhum parâmetro passado à mão. Groq, `openai/gpt-oss-120b`, plano gratuito; 2,4 a 3,7 s por chamada.
- **Primeira passada, `@6` como aberto o PR: 10 chamadas, 8 aprovadas, 2 reprovadas** (a #376 tinha 4 de 10, e 5 reprovações por tamanho). **Nenhuma reprovação por `forma_tamanho_linha`**: a recuperação em duas linhas cabe nos 140 caracteres. Casos: três medidas (3 chamadas, em F01, F02 e F04), `aprendendo`, `sem_noite`, madrugada, `fora_do_periodo`, tudo dentro do normal, uma medida só e natação.
- **Clima e recuperação juntos** (F01, `aprendendo` e três medidas; F04): o texto coube em 5 linhas. O modelo ou pôs a temperatura na linha do check-in ("Você marcou esforço 4 (um pouco difícil) e sensação 4 (bem) e nada a relatar, em 19 °C.") ou cortou a carga e manteve clima mais atalho; nenhum texto reprovou por falta de linha. Em F02 e F06 o clima saiu (F06 é natação, sem clima).
- **Reprovada 1, uma medida só (VFC):** "A VFC foi 46 ms, dentro do seu normal." sem "Na noite anterior" (`recuperacao_forma`). Texto certo; o prompt dizia só "a primeira começa com...". Corrigido no prompt (a linha de uma medida "TAMBÉM começa com 'Na noite anterior'"); repetida a chamada: aprovada.
- **Reprovada 2, as três dentro do normal:** o modelo calculou "5 min acima do seu normal de 7 h 15 min" para uma medida `dentro` (sem `diferenca_texto` no pacote): `numero_fora_do_pacote` e `recuperacao_forma`, reprovação correta. Primeiro ajuste no prompt ("`diferenca_texto` existe só em abaixo e acima"): repetiu o erro. Segundo ajuste (medida `dentro`: só o valor e "dentro do seu normal", sem diferença nem "abaixo"/"acima"): sem diferença, mas repetiu "dentro do seu normal" em duas linhas da recuperação (`conclusao_repetida`). Terceiro: com as três dentro, **uma linha só** ("Na noite anterior você dormiu 7 h 20 min, a FC de repouso foi 52 bpm e a VFC, 46 ms: todas dentro do seu normal."). Aprovada.
- **Total:** 14 chamadas com texto (10 da primeira passada e 4 de repetição: 1 do caso "uma medida só", aprovada, e 3 do caso "tudo dentro do normal", 2 reprovadas e 1 aprovada): **10 aprovadas e 4 reprovadas** (as 2 da primeira passada e 2 repetições do caso "tudo dentro do normal"), mais 1 recusa por limite do provedor (uma repetição minha menos de 1 minuto depois da anterior; no relato da camada ela aparece com o código `limite_de_chamadas`, que não é o teto de chamadas do worker). Os três ajustes são de redação do prompt (nenhuma checagem nova, `checagens_feedback@4` sem mudança); como o prompt mudou depois da primeira passada, os outros 8 casos não foram repetidos com o texto final.
- **Falso positivo ou texto ruim que passou:** nenhum visto. Nenhum texto ligou a noite ao resultado, aconselhou ou julgou.
- **Tamanho:** o prompt ficou com 13.737 caracteres (cerca de 4.160 tokens a 3,3), dentro do teste da #395.
- Os textos de B10, M29 e M30 em `tests/fixtures/meta10/textos_recuperacao.py` vêm dessa rodada.

## Rodada com o provedor de verdade, `feedback_prompt@7` (15/11, #403)
Mesmo formato, camada do `main`, pacotes sintéticos (fixtures da meta 9 com as noites do oráculo e as noites "três aprendendo" da fixture da meta 10). 9 chamadas ao todo (6 e 3 de repetição de casos que reprovaram por tamanho), 65 s entre elas.
- **A frase do `aprendendo` saiu em todos os textos com medida `aprendendo` (6 de 6); "Seu FC" não saiu em nenhum.** As duas checagens novas não reprovaram nada nesta rodada: sem falso positivo e sem o defeito de volta.
- **Resultado: 3 aprovadas, 5 reprovadas e 1 sem texto** (`provedor_erro`, uma chamada). Reprovações: 4 por `forma_tamanho_linha` (as três medidas `aprendendo` com as duas frases na mesma linha, ou a primeira linha de um treino com pace e FC média, que passa de 140 caracteres) e 1 por `recuperacao_mistura` (clima e carga na mesma linha da recuperação). São variações do modelo que as checagens pegam; o worker tenta de novo na próxima execução.
- **Ajuste de redação no prompt, depois da primeira passada:** com as três `aprendendo` o modelo juntava tudo numa linha; o prompt ganhou o par de linhas curtas (B13). Repetidas, 1 de 2 passou (a outra voltou a juntar as frases).
- Não há mais ajuste de redação em vista que não custe tokens: o prompt está em 4.320 tokens estimados.

## Limitações
- `groq`, `openai` e `anthropic` são os provedores aceitos hoje; outro exige uma linha em `CHAVES`.
- O LiteLLM traz o `openai` 3.x e o `httpx2`; por isso o `TestClient` do Starlette passou a usar o `httpx2`, e o `conftest` da API silencia o logger `httpx2` nos testes (o log é do cliente do teste, não da API).
- Limites do plano gratuito do Groq: não conferidos (a página só mostra o plano pago). O limite de 20 chamadas por execução é configurável.
- **Limite por minuto do provedor (#357):** a recusa (HTTP 429 ou erro de limite) vira `LimiteDoProvedor` na camada; o `Redator` marca `limite_do_provedor` e o worker para a execução sem gravar linha (o treino segue `pendente`). `LLM_INTERVALO_S` (padrão 0) é a pausa entre chamadas; numa medição local com fixtures, 28 s entre chamadas ainda teve recusa, então para o plano gratuito use 65 (cada chamada consome 5 a 6 mil dos 8.000 tokens por minuto; 40 s não bastaram na rodada da #376).
- As checagens `@1` deixavam passar "pois" como palavra de causa (visto numa resposta do `@1`); a `checagens_feedback@2` (#355) cobre.

## Arquivos principais
- `services/api/app/llm/camada.py`, `services/api/app/llm/__init__.py`
- `services/api/app/config.py` (`llm_provider`, `llm_model`, `llm_timeout_s`, `llm_limite_chamadas`, chaves)
- Testes: `services/api/tests/llm/test_camada.py` (provedor falso, LiteLLM real com `mock_response`, guarda de rede)

## Depende de
LiteLLM (`litellm` 1.108.4, em `services/api/pyproject.toml`).

## Como testar
`uv run pytest services/api/tests/llm -q` (sem rede e sem chave).
