---
tipo: modulo
status: em-uso
dono: duda
atualizado: 2026-11-11
links: [[decisoes/0013-feedback-automatico]], [[modulos/api]], [[modulos/worker]], [[produto/roadmap]]
---
# Módulo: camada de LLM

## Para que serve
A única porta do produto para um modelo de linguagem (regra do `AGENTS.md`: IA sempre por uma camada trocável, nunca provedor direto no código). Meta 9, issue #326; quem usa é o `worker.gerar_feedback` (#327, [[modulos/worker]]; o prompt fixo `feedback_prompt@1` está em `app/llm/prompt_feedback.py`). Código em `services/api/app/llm/camada.py`. A [[decisoes/0013-feedback-automatico]] (`aceita` em 10/11) decide o uso; esta nota descreve o que o módulo faz.

## Entradas e saídas
- `criar_redator()` monta o `Redator` do `.env`; `Redator.redigir(sistema, pacote)` recebe o prompt fixo e o pacote (dicionário, vira JSON) e **nunca levanta**: devolve `ResultadoLLM(texto, motivo, provedor, modelo)`. Ou há `texto`, ou há um `motivo`:

| `motivo` | quando |
|---|---|
| `provedor_nao_configurado` | sem `LLM_MODEL`, sem chave do provedor, provedor vazio ou desconhecido |
| `provedor_tempo_limite` | passou de `LLM_TIMEOUT_S` (padrão 20 s) |
| `provedor_erro` | qualquer outra falha (rede, limite do plano gratuito, 429, resposta vazia) |
| `limite_de_chamadas` | a execução já fez `LLM_LIMITE_CHAMADAS` (padrão 20) chamadas; a chamada acima do limite nem vai ao provedor |

São os mesmos códigos do `CHECK` previsto para `feedback_treino` ([[decisoes/0013-feedback-automatico]]). `texto_reprovado` não é daqui: é do worker, depois das checagens.
- **Provedor falso** (`LLM_PROVIDER=falso`): sem rede e sem chave, obrigatório em testes e CI. Devolve um texto fixo de 3 linhas; `ProvedorFalso(modo="ruim")` devolve um texto de propósito reprovável, e os modos `erro`, `tempo` e `vazio` simulam falhas. O resultado leva `provedor = "falso"`.

## Regras
- **Troca só pelo `.env`:** `LLM_PROVIDER` (`groq`, `openai`, `anthropic` ou `falso`), `LLM_MODEL` e a chave (`GROQ_API_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`). O LiteLLM recebe `<provedor>/<modelo>` e a chave explícita. Padrão: `groq`. `.env.example` só com os nomes.
- **Sem nova tentativa dentro da chamada** (`num_retries=0`): a próxima execução do worker é a nova tentativa.
- **Nada do conteúdo em log, saída ou exceção** (o pacote e o texto são dado de saúde): o erro vira `motivo` pela **classe** da exceção e a mensagem é descartada. O LiteLLM é configurado para não registrar conteúdo: `litellm.turn_off_message_logging = True`, `litellm.redact_messages_in_exceptions = True`, `litellm.suppress_debug_info`, listas de *callbacks* vazias e os loggers `LiteLLM` e `httpx` em CRITICAL (o padrão do LiteLLM é DEBUG). Teste com um marcador sintético no prompt, no pacote e na resposta ou erro, em sucesso e em cada falha.
- **Dois cuidados com a importação do LiteLLM** (conferidos no código da 1.108.4, e por isso a camada define as variáveis **antes** de importar): `LITELLM_LOCAL_MODEL_COST_MAP=True` (sem isso a importação baixa a tabela de preços da internet; o teste de rede falhou até isso entrar) e `LITELLM_MODE=PRODUCTION` (no modo padrão a importação carrega o `.env` mais próximo para dentro de `os.environ`, o que misturaria credenciais de outros módulos e sobreporia a configuração). Importe o LiteLLM só pela camada.
- A chave é `SecretStr` em `app/config.py` (não aparece em `repr`).
- **Dado de saúde que sai da máquina:** com provedor real, o pacote de fatos vai ao provedor. O que o Groq diz sobre retenção e o que **não foi conferido** está na [[decisoes/0013-feedback-automatico]], "A confirmar", item 10; a regra do projeto é: provedor real só no computador do Angelo, com o "sim" dele, e provedor falso em CI e testes.

## Quem usa: `app/servicos/feedback.py` e `worker.gerar_feedback` (#327)
`gerar(session, atleta_id, redator, montar_pacote, checar, versoes, prompt, refazer)` (em `app/servicos/feedback.py`) recebe o pacote e as checagens por **injeção**:
- `montar_pacote(session, atividade, checkin) -> dict | None` (o pacote `fatos_treino@1`; `None` se não há check-in ou a atividade não é elegível);
- `checar(pacote, texto) -> str | None` (`None` se o texto passa; senão o **primeiro** código de motivo; a linha guarda só `texto_reprovado`, nunca o texto nem o código do termo).

Na linha de comando, os padrões são os reais: `app.servicos.feedback_fatos.fatos_da_atividade` (o **adaptador** que lê o banco e chama a função pura `app.explicacao.fatos_treino.fatos_treino`, #324), `app.explicacao.checagens.checar` (#325) e as `VERSAO` dos dois módulos. O adaptador usa os serviços de leitura que a API já tem (`linha_base_resultado`, `clima_da_atividade`, `carga_da_atividade`, `esforcos_da_atividade`, rótulo de transição) e não recalcula nada; natação fica sem bloco de clima. Teste: o pacote que sai do banco semeado com as fixtures da meta 9 é igual ao do oráculo (`services/api/tests/servicos/test_feedback_fatos.py`).

## Prompt `feedback_prompt@1` (`app/llm/prompt_feedback.py`)
Regras de forma, tom e do que falta no pacote, mais os **6 exemplos aprovados** (G01 a G06, pacote reduzido sem campos nulos e texto da ADR 0013). Os exemplos têm **fonte única** em `app/llm/exemplos_feedback.py`; um teste confere o texto contra `tests/fixtures/meta9/textos.py`, o pacote contra o oráculo e que cada texto passa nas checagens. O prompt tem uns 2,5 mil tokens (estimativa), para caber no limite por minuto do plano gratuito (não conferido). Se o texto mudar de forma relevante, a `VERSAO` sobe.

## Limitações
- `groq`, `openai` e `anthropic` são os provedores aceitos hoje; outro exige uma linha em `CHAVES`.
- O LiteLLM traz o `openai` 3.x e o `httpx2`; por isso o `TestClient` do Starlette passou a usar o `httpx2`, e o `conftest` da API silencia o logger `httpx2` nos testes (o log é do cliente do teste, não da API).
- Limites do plano gratuito do Groq: não conferidos (a página só mostra o plano pago). O limite de 20 chamadas por execução é configurável.

## Arquivos principais
- `services/api/app/llm/camada.py`, `services/api/app/llm/__init__.py`
- `services/api/app/config.py` (`llm_provider`, `llm_model`, `llm_timeout_s`, `llm_limite_chamadas`, chaves)
- Testes: `services/api/tests/llm/test_camada.py` (provedor falso, LiteLLM real com `mock_response`, guarda de rede)

## Depende de
LiteLLM (`litellm` 1.108.4, em `services/api/pyproject.toml`).

## Como testar
`uv run pytest services/api/tests/llm -q` (sem rede e sem chave).
