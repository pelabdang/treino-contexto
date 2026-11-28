---
tipo: modulo
status: em-uso
dono: nina
atualizado: 2026-11-28
links: [[decisoes/0017-chat-do-atleta]], [[decisoes/0004-contrato-tela-evolucao]], [[decisoes/0016-login-e-deploy-do-piloto]], [[modulos/api]], [[modulos/banco]], [[modulos/camada-llm]], [[modulos/mobile]], [[metricas/checagens-chat]], [[metricas/ferramentas-chat]], [[metricas/chat-oraculo]], [[design/telas/chat]], [[produto/roadmap]], [[glossario]]
---
# Módulo: chat do atleta

Mapa do chat "Pergunte ao seu treino" (Meta 14). Esta nota só aponta; o detalhe de cada parte está nas notas ligadas. Dados e exemplos reais nunca entram aqui.

## Para que serve
O atleta pergunta em texto livre, ou por uma pergunta pronta, qualquer coisa sensata sobre os próprios treinos. O modelo escolhe quais **ferramentas de consulta** chamar e redige; **os números vêm do código** e as checagens conferem o texto ([[decisoes/0017-chat-do-atleta]]). O que não é sobre treino recebe uma recusa de texto fixo.

## Entradas e saídas
- **Entrada:** a pergunta (até 1000 caracteres) e a sessão do atleta. Rotas em [[decisoes/0004-contrato-tela-evolucao]] (adendos 16, 17, 18 e 19): conversas, mensagens, avaliação 👍/👎 e perguntas prontas.
- **Saída:** `MensagemOut` com `estado` (`respondida`, `recusada`, `reprovada`, `erro`), `texto` pronto, `links[]` e `avaliacao`. Texto reprovado nunca é gravado nem devolvido.

## Arquivos principais
- `services/api/app/chat/`: registro e executor das ferramentas (`registro.py`, `esquema.py`, `periodo.py`), ferramentas de atividades e check-ins, o laço (`laco.py`), a recusa (`recusa.py`), o prompt (`prompt.py`, hoje `prompt_chat@3`) e as perguntas prontas. Ver [[modulos/api]].
- `services/api/app/explicacao/`: `checagens_chat.py` ([[metricas/checagens-chat]]) e `ferramentas_chat.py` ([[metricas/ferramentas-chat]]).
- `services/api/app/llm/camada.py`: método `conversar`, com o provedor falso nos testes ([[modulos/camada-llm]]).
- Tabelas `conversa` e `mensagem` (migrações 0019 e 0020, [[modulos/banco]]), apagadas com a conta.
- App: telas `/chat`, `/chat/<id>` e `/chat/conversas`, e o bloco do chat no Início ([[modulos/mobile]], spec em [[design/telas/chat]]).

## Depende de
O provedor de LLM pela camada trocável (Groq por padrão; nada de pergunta, resultado ou resposta em log), o escopo por sessão da [[decisoes/0016-login-e-deploy-do-piloto]] e as métricas já calculadas pelo código (séries, carga, linha de base, recuperação).

## Como testar
`services/api/tests/chat/`, `tests/rotas/test_chat*.py`, `tests/llm/test_conversar.py` e as fixtures de [[metricas/chat-oraculo]]. CI sem rede, com o provedor falso. O guia `meta-14-como-rodar` ainda não existe.

## Pendências
- Reconferir a rodada sintética no Groq com o `prompt_chat@3` (18 de 25 antes do ajuste).
- Guia `meta-14-como-rodar`, QA e resultado da meta ([[produto/roadmap]]).
- Termo de consentimento novo, com o aviso fixo "A sua pergunta vai a um serviço de IA." e o texto livre do check-in.
- Chat do professor (Meta 16): as ferramentas já recebem "quem pergunta"; o professor não vê a Evolução nem as conversas do atleta.
