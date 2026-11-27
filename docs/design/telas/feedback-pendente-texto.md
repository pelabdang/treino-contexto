---
tipo: design
status: rascunho
dono: lia
atualizado: 2026-11-27
links: [[design/telas/feedback]], [[decisoes/0013-feedback-automatico]], [[modulos/camada-llm]], [[design/telas/treino]]
---
# Cartão Feedback: texto do "pendente" e do botão

**Problema (Angelo, 27/11).** O botão "Atualizar" do estado `pendente` só lê de novo o que está salvo. Não gera feedback (a geração é manual, em lote, pelo
`worker.gerar_feedback`). O texto atual, "Toque em Atualizar para ver se já está pronto.", e o nome "Atualizar" sugerem que o toque gera. Parece erro.

## Proposta
| estado | texto | botão |
|---|---|---|
| `pendente` | "O feedback deste treino ainda não foi gerado. Ele é preparado em lote; volte mais tarde." | **"Verificar de novo"** |
| `desatualizado` | mantém a frase da API ("Você editou o check-in. O feedback será refeito.") e junta: "Volte mais tarde para ler." | **"Verificar de novo"** |
| durante a busca | | "Verificando..." |
| continua pendente depois do toque | o leitor de tela e uma linha pequena abaixo do botão dizem: "Ainda não foi gerado." | volta a "Verificar de novo" |
| apareceu o texto | o cartão troca pelo feedback; o leitor anuncia "Feedback pronto" | |

## Por quê
- "Verificar" diz o que o botão faz (olhar de novo), sem prometer que produz algo; "Atualizar" soa como "refazer".
- "Em lote; volte mais tarde" diz **quando** (não agora) sem prazo, que não temos. Nada de "em instantes" nem "gerando".
- A linha "Ainda não foi gerado." dá resposta ao toque: sem ela o atleta acha que o botão quebrou.
- Se o piloto passar a gerar sozinho (ADR 0013), o texto muda para "O feedback deste treino está sendo preparado." Aí sim o app pode girar um indicador.

## Para o Rafa
Trocar a constante do `pendente` em `CartaoFeedback.tsx`, o rótulo do botão (e "Atualizando..." por "Verificando...") e a linha "Ainda não foi gerado.". O comportamento do botão não muda.
