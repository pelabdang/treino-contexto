---
tipo: metrica
status: rascunho
dono: caio
atualizado: 2026-11-28
links: [[decisoes/0017-chat-do-atleta]], [[decisoes/0013-feedback-automatico]], [[metricas/checagens-feedback]], [[metricas/chat-oraculo]], [[produto/roadmap]], [[glossario]]
---
# Checagens do texto do chat (`checagens_chat@1`)

## O que mede
Se o texto final que o modelo escreveu para o atleta pode chegar ao app. É uma função pura (`app/explicacao/checagens_chat.py`): recebe o texto e a **lista
de ferramentas chamadas naquela pergunta** (nome, argumentos, resultado) e devolve aprovado ou **só os códigos** dos motivos, nunca o texto nem o termo que
reprovou. Texto reprovado é descartado e o atleta recebe uma frase fixa ([[decisoes/0017-chat-do-atleta]], item 4).

## Regras (códigos)
| Código | Reprova quando |
|---|---|
| `numero_fora_dos_resultados` | número, com a unidade escrita, que não está em nenhum resultado das ferramentas da pergunta (mesma conta da `numero_fora_do_pacote`; "1 h 30 min" só se for texto composto do resultado) |
| `unidade_trocada`, `numero_por_extenso` | número do resultado com outra unidade; número escrito por extenso |
| `sem_ferramenta` | o texto traz número e nenhuma ferramenta de consulta devolveu resultado sem erro |
| `dado_ausente_afirmado` | todo resultado diz `sem_dados` (ou clima `indoor`) e o texto traz valor fora dos resultados |
| `linguagem_diagnostico`, `_culpa`, `_promessa`, `_causa` | as listas da [[metricas/checagens-feedback]] (`checagens_feedback@6`), com o rótulo da sensação do resultado ("mal") e a frase "sono ruim" mascarados |
| `linguagem_julgamento` | elogio e juízo de valor (lista do feedback sem os verbos de comparação, mais "em forma", "muito melhor") |
| `linguagem_quem_fala` | o modelo fala em primeira pessoa, cita professor, treinador ou IA, ou usa "!" (a fala entre aspas da observação do atleta é tirada antes) |
| `prescricao` | conselho, ordem ou plano (lista de conselho do feedback mais "faça", "treine", "troque", "siga", "deveria", "monte", "plano de"...) |
| `comparacao_sem_ferramenta` | palavra de comparação ("melhorou", "mais rápido", "subiu", "a mais") sem resultado com `direcao` maior ou menor; o `diferenca_texto` do resultado, citado, é permitido |
| `dor_regra` | com atalho `dor` nos resultados, o texto não é só a frase neutra da ADR 0013; sem atalho, qualquer menção a dor |
| `forma` | mais de 8 linhas, mais de 900 caracteres, Markdown, link, emoji ou nome próprio (siglas FC, PSE, UA, CTL, ATL, TSB e VFC e a observação citada entre aspas ficam de fora) |
| `fora_do_escopo_respondido` | o modelo chamou `recusar`: o atleta lê só o texto fixo (`TEXTOS_FIXOS`), nunca o do modelo |

## Fontes e versão
Regra própria do projeto, sem artigo: decisões do Angelo de 10/11 e 28/11 e as listas da `checagens_feedback@6`. `checagens_chat@1`. Mudar uma lista de lá
obriga a rever esta; qualquer mudança de regra sobe a versão (gravada em `mensagem.versao_checagens`).

## Casos
O oráculo é [[metricas/chat-oraculo]]: as 24 respostas boas de treino passam e as 32 ruins reprovam **exatamente** pelos motivos declarados. O teste é
`services/api/tests/explicacao/test_checagens_chat.py`.

## Limitações e quando não usar
É lista de palavras: não entende o sentido (uma causa dita sem palavra da lista passa). A rodada real com o Groq (#603) é que mede isso. A observação do atleta
citada entre aspas vale como fala dele para `forma` e `linguagem_quem_fala`, mas diagnóstico, causa e prescrição dentro dela ainda reprovam (ADR 0017, item 6).
