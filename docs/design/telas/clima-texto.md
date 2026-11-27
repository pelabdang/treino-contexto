---
tipo: design
status: rascunho
dono: lia
atualizado: 2026-11-27
links: [[design/telas/treino]], [[decisoes/0007-clima-da-atividade]], [[metricas/clima-oraculo]], [[modulos/clima]], [[metricas/checagens-feedback]]
---
# Cartão Clima: números inteiros e texto do treino antigo

Dois ajustes de texto pedidos pelo Angelo e pelo Theo (27/11) ao cartão "Clima" da [[design/telas/treino]]. O Rafa troca a tabela da `treino.md` na implementação.

## 1. Números inteiros (temperatura, sensação, umidade e vento)
- **Vale para os quatro.** Temperatura e sensação térmica ("23 °C", "25 °C"), **umidade** ("61 %") e **vento** ("8 km/h"). Todos sem casa decimal. A umidade já vinha inteira
  no exemplo; o vento passa de "8,2 km/h" para "8 km/h".
- **Regra:** arredondar para o inteiro mais próximo; metade vai para longe do zero (23,5 → 24; -3,5 → -4); nunca "-0" (vira "0"). É só **exibição**: a API
  segue mandando o valor com decimal, que é o do oráculo ([[metricas/clima-oraculo]]). A PR #565 do Rafa já faz isso com testes.
- **Sinal:** o menos de temperatura negativa se lê "menos 3 graus Celsius" no leitor de tela (rótulo falado); na tela, "-3 °C" com o sinal de menos do texto.
- **Rótulo falado:** "Temperatura, 23 graus Celsius"; "Umidade, 61 por cento"; "Vento, 8 quilômetros por hora".
- **Outros lugares com o mesmo número:** o **texto do feedback** gerado pode citar o clima com decimal. Pedido ao Caio: conferir se as
  [[metricas/checagens-feedback]] aceitam e se o prompt manda arredondar, para a tela e o texto não discordarem ("23 °C" no cartão e "23,4 °C" no feedback).

## 2. Treino antigo sem clima buscado
**Problema.** O texto de hoje, "O clima deste treino ainda não chegou. Treinos recentes podem levar cerca de uma semana.", é **enganoso** num treino de meses atrás:
a espera de uma semana já passou e o texto promete que vai chegar. Não sabemos se vai.

**Proposta, dois textos conforme a idade do treino** (o mesmo estado `pendente`):
| treino | texto | por quê |
|---|---|---|
| **recente** (menos de 7 dias) | "O clima deste treino ainda não chegou. Costuma levar até uma semana." | verdadeiro, e a promessa é curta |
| **antigo** (7 dias ou mais) | "O clima deste treino ainda não foi buscado." | diz só o fato; **sem prazo e sem promessa** |
Em ambos: ícone `info-outline`, aviso neutro (não é erro do atleta), sem botão. Se um dia houver "Buscar agora", o antigo ganha o botão "Buscar o clima".

**Quem sabe a idade:** o app tem a data do treino e a do aparelho, mas o relógio do aparelho pode errar. Prefiro que a **API** mande o campo
(`clima.recente: true|false`) ou o texto pronto, como nos outros avisos. **Pergunta à Duda e ao Theo.** Enquanto não houver, o app usa o texto
do treino antigo em **todos** os casos, que nunca engana (perde só a dica de espera). Texto de `indoor`, `sem_posicao` e `falha`: sem mudança.
