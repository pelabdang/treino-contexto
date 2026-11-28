---
tipo: metrica
status: rascunho
dono: caio
atualizado: 2026-11-28
links: [[decisoes/0017-chat-do-atleta]], [[decisoes/0013-feedback-automatico]], [[metricas/checagens-feedback]], [[metricas/evolucao-series]], [[produto/roadmap]], [[glossario]]
---
# Chat do atleta: oráculo das fixtures (`checagens_chat@1`)

## O que mede
O oráculo do chat da [[decisoes/0017-chat-do-atleta]]: para cada pergunta **sintética**, quais ferramentas deveriam ser chamadas, com quais argumentos e o que
devolvem, uma resposta que **passa** nas checagens e uma que **reprova**, com os códigos dos motivos. Tudo inventado (o "hoje" é 15/03/2030): **nenhum dado de
conta, relógio ou treino de ninguém**. Os arquivos estão em `services/api/tests/fixtures/chat/` (`perguntas.json`, `atletas.json`) e o teste é
`services/api/tests/explicacao/test_fixtures_chat.py`.

## Casos
33 perguntas, com os atletas fictícios `atleta_a` (histórico de 14 semanas, clima e check-ins completos) e `atleta_b` (natação e ciclismo, pouco histórico, treinos indoor).

| Grupo | Ids | O que cobre |
|---|---|---|
| Evolução | E01 a E05 | comparar pace e FC leves, volume, tiros, e a série da natação sem dados suficientes (a resposta diz o que falta, sem "não sei") |
| Treino específico | T01 a T04 | último treino, o mais longo, o intervalado e a natação mais longa |
| Comparação | C01 a C04 | volume entre períodos, rua e casa no ciclismo, `direcao = parecido` e esta semana contra a passada (cortada nos mesmos dias) |
| Check-ins | K01 a K04 | esforço da semana, pior sensação com a observação livre, treino com dor (só a frase neutra) e "o que eu escrevi" (ADR 0017, item 6) |
| Carga e forma | F01 a F04 | CTL, ATL e TSB do dia, carga semanal, dois dias comparados e histórico curto |
| Clima | L01 a L03 | calor no treino, treinos leves quentes e treino indoor sem clima |
| Recuperação | R01 | sono e FC de repouso, com VFC sem dado |
| Fora do tema | X01 a X05 | receita, política, diagnóstico médico, código e compra; resposta = texto fixo da ADR |
| Pedido de mudança | M01 a M03 | montar treino, trocar o dia do longão, plano de maratona; resposta = encaminhar ao professor |

Cada resposta boa só cita números que aparecem nos resultados das ferramentas (o teste confere por código). Cada resposta ruim erra por um ou mais motivos
declarados: número inventado (`numero_fora_dos_resultados`), causa afirmada (`linguagem_causa`), prescrição (`prescricao`), diagnóstico, promessa, comparação sem
ferramenta, dado ausente afirmado, dor além da frase neutra, e pergunta recusável respondida (`fora_do_escopo_respondido`).

## Fontes e versão
Regra própria do projeto: decisões do Angelo de 10/11 e 28/11 e as listas da [[metricas/checagens-feedback]]. `fixtures_chat@1`.

## Limitações e quando não usar
O teste do contrato confere as fixtures e a regra dos números; o `test_checagens_chat.py` roda cada boa e cada ruim contra a [[metricas/checagens-chat]] e exige os motivos declarados, sem sobra nem falta. Os resultados das ferramentas são o formato proposto na ADR; a #593 e a #594 podem ajustar nomes de campo e este oráculo acompanha.
