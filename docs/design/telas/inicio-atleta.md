---
tipo: design
status: rascunho
dono: lia
atualizado: 2026-11-18
links: [[design/identidade-visual-v2]], [[design/auditoria-ux-e-inicio-do-atleta]], [[design/telas/treino]], [[design/telas/checkin]], [[design/telas/feedback]], [[design/telas/evolucao-tiros]], [[metricas/serie-carga]], [[metricas/linha-base]], [[modulos/mobile]]
---
# Telas v2 do atleta: início e treino (proposta em alta fidelidade)

Resposta do Angelo à [[design/auditoria-ux-e-inicio-do-atleta]]: a tela inicial é "uma mistura das direções", o gráfico de carga e
forma é **quinzenal com uma frase de análise**, e a ordem do primeiro olhar depois do treino é "proponha". Aqui estão a **tela
inicial v2** e a **tela do treino** redesenhadas, já na identidade de [[design/identidade-visual-v2]]. Rascunho para ele reagir: nenhuma
linha do app muda. O nome "Pulso" que aparece nos esboços é **provisório** (os nomes Pulso, Cadência e Contexto são propostas, sem decisão do Angelo; ver [[design/identidade-visual-v2]]). Atleta (Ana), treinos e números **sintéticos**; linha do tempo: hoje é **sexta, 21/03/25**.

## Tela inicial v2
Celular claro e escuro, e computador:
![[design/telas/inicio-atleta/inicio-v2-celular-claro.svg]]
![[design/telas/inicio-atleta/inicio-v2-celular-escuro.svg]]
![[design/telas/inicio-atleta/inicio-v2-computador-claro.svg]]
![[design/telas/inicio-atleta/inicio-v2-computador-escuro.svg]]

### Objetivo
Em cinco segundos, depois do treino: "o que eu faço agora? como foi? e como eu estou?".

### Ordem (a mistura recomendada)
1. **Saudação** ("Olá, Ana", data). Vem do nome da sessão.
2. **Cartão "Agora"** (da Direção C), **só quando há treino sem check-in**. Volt, o mais forte da tela: a pergunta ("Como foi a natação
   de ontem?"), a modalidade e a hora, o botão "Responder o check-in (3 perguntas)" e o prazo. "+ N treinos sem check-in" abre a lista.
   Sem pendência, o cartão some e o último treino sobe.
3. **Último treino com feedback** (da Direção A): modalidade e tipo, o **número grande** (o melhor tiro, em corrida de tiros; ver
   "Número do treino"), "dentro do seu normal", e o começo do feedback (3 linhas) com "Ler feedback completo".
4. **Seus últimos 14 dias** (da Direção B): gráfico de duas linhas e uma frase de análise.
5. **Treinos recentes** (4 itens) e "Ver todos" (a aba Treinos).
6. **Abas** na base (celular) ou menu à esquerda (computador): Início, Treinos (com selo do número de pendentes), Evolução, Conta.

No computador (1280): menu à esquerda de 232, e duas colunas de 470: "Agora" + último treino à esquerda; quinzena + treinos recentes
à direita.

### Número do treino (o que é o "número grande")
Não inventamos métrica. Por modalidade e tipo, o número grande é o que a API já entrega como valor principal:
| treino | número grande |
|---|---|
| corrida intervalada | melhor tiro de 1 km (`pace_melhor`, `m:ss`, /km) |
| corrida leve, longa ou moderada | pace médio (`pace_medio`, /km) |
| ciclismo, natação, sem pace | duração (`h:mm:ss`) |
Linhas pequenas abaixo: o que a tela do treino já mostra (FC, distância, duração). O texto vem pronto da API; o app não formata pace.

### "Dentro do seu normal"
Vem de `linha_base` da atividade ([[metricas/linha-base]]), só para a mesma modalidade e tipo.
| estado da API | o que aparece |
|---|---|
| todas as métricas `dentro` | chip volt-suave com confere: "Dentro do seu normal para <tipo>" |
| alguma `fora` | chip alerta com ícone (não só cor): "Fora do seu normal: <frase da API>" (ex.: "FC média acima do habitual") |
| `aprendendo` | chip neutro com ampulheta: o `texto` da API ("Ainda aprendendo o seu normal...") |
| sem `linha_base` | o chip não aparece |
Nunca "bom" ou "ruim": só a comparação com o histórico dele.

### Quinzena: gráfico e frase de análise
- **Dados:** os últimos 14 itens de `dias` de `GET /atletas/{id}/carga` (`ctl`, `atl`, números). A série termina no **último dia com
  atividade** (não estende até hoje), e o rótulo do eixo mostra as datas reais (07/03 a 20/03 no exemplo).
- **Nomes na tela:** "Condicionamento" (linha cheia, azul) e "Fadiga" (tracejada, magenta); o valor final em número condensado ao lado.
  **Nada de CTL, ATL ou TSB.** O chip "estimativa" fica sempre. O Angelo pediu sem jargão; as definições do glossário
  ("média da carga nos últimos 42 dias" / "7 dias") abrem ao tocar no nome da linha.
- **Frase de análise (regra, sem adjetivo de valor e sem conselho):**
| situação | frase |
|---|---|
| fadiga > condicionamento | "Sua fadiga (F) está acima do condicionamento (C): a carga dos últimos dias passou da média das últimas 6 semanas." |
| fadiga < condicionamento | "Sua fadiga (F) está abaixo do condicionamento (C): a carga dos últimos dias ficou abaixo da média das últimas 6 semanas." |
| iguais (arredondados) | "Sua fadiga e o seu condicionamento estão iguais (N)." |
| `aprendendo` | o `texto_aprendendo` da API |
| sem carga calculada | o `texto` da API, sem gráfico |
  **Pendência para o Caio e a Duda:** a frase deve ser **texto fixo aprovado pelo Caio**, de preferência entregue pela API (como já são
  `ctl_texto` e `texto_aprendendo`), para o app não calcular nem decidir. Sem recomendação ("descanse"): o app descreve, não prescreve.
  Os números 44 e 58 do exemplo são sintéticos.
- **Sem cores como única pista:** as duas linhas diferem por traço, rótulo direto e valor.

### Estados
| estado | o que aparece |
|---|---|
| carregando | esqueleto de quatro cartões; o texto "Carregando..." para leitor de tela |
| sem treinos | linha de pulso e "Nenhum treino ainda. Envie o arquivo do seu relógio e a análise aparece aqui." com o botão "Enviar arquivo FIT" |
| sem pendência | o cartão "Agora" some; o último treino ocupa o topo |
| último treino sem feedback | o cartão mostra o número e a linha de estado do feedback da [[design/telas/feedback]] (pendente, indisponível, prazo vencido) |
| erro de rede | cada cartão falha sozinho com "Tentar de novo"; os outros aparecem |
| acesso expirado | como em [[design/telas/entrar]] |

### Dados e API
Todos existem hoje, **menos um**: a lista de treinos recentes e "o último treino de qualquer modalidade" precisam de uma rota que liste
as atividades do atleta (data, modalidade, duração, tem check-in, tem feedback). Registrado na auditoria; o Angelo disse que o histórico
"não é prioridade, mas é interessante" porque alimenta feedbacks, análises e perguntas. Até a rota existir, o início usa o último
treino da evolução de tiros e os pendentes.

## Tela do treino v2 e a ordem do primeiro olhar
Celular claro e escuro:
![[design/telas/inicio-atleta/treino-v2-celular-claro.svg]]
![[design/telas/inicio-atleta/treino-v2-celular-escuro.svg]]

### A ordem que proponho (e por quê)
O atleta termina o treino com quatro perguntas, sempre nesta ordem. A tela responde cada uma, de cima para baixo, e o detalhe só
vem depois:
1. **Como foi?** O **número grande** e o **feedback** juntos no topo. É o que o Angelo mais quer; o feedback usa o check-in, então
   é a recompensa de ter respondido.
2. **Foi diferente do meu normal?** A comparação com o histórico dele: chip "dentro do seu normal" e uma barra com a faixa normal e o
   ponto de hoje (o medidor do Garmin).
3. **O que eu disse?** O check-in (esforço, sensação, observação), com editar e apagar. Fecha o ciclo: o texto de cima nasceu dele.
4. **O que aconteceu em detalhe?** Os tiros (uma barra por tiro, mais alta = mais rápida) e, depois, voltas.
5. **Contexto:** duração, distância, pace, FC, carga do treino (estimativa) e clima, numa lista só.
O que mudou em relação a hoje: o feedback sobe do 3º para o 1º cartão; os oito cartões iguais viram cinco blocos numerados com um
só cartão de números no fim; a carga pela PSE (UA) e a do relógio (pontos) saem do topo para o contexto, com os nomes simples.

### Variações
| situação | topo da tela |
|---|---|
| tem check-in e feedback pronto | como no esboço |
| **sem check-in** | o número grande continua; no lugar do feedback, o cartão "Agora" ("Responda o check-in para receber o feedback") |
| feedback pendente, indisponível ou prazo vencido | a linha de estado da [[design/telas/feedback]] no lugar do texto |
| sem pace (natação) | o número grande é a duração; sem barra de normal de pace |
| `linha_base` aprendendo | o bloco 2 mostra o texto de "aprendendo" |
| sem posição (esteira) | nada muda: mapa não faz parte desta versão |

### Acessibilidade
- Cada bloco é um título ("1 Como foi", "2 Comparado ao seu normal"...) para navegar por títulos.
- Número grande com rótulo completo: "Melhor tiro, 4 minutos e 11 segundos por quilômetro".
- A barra do normal tem alternativa em texto na mesma linha ("hoje 4:11, seu normal 4:08 a 4:24"); o gráfico de tiros, a lista dos
  tempos já escritos sobre as barras.
- Contraste, alvos de 48 e foco: conforme [[design/identidade-visual-v2]].

## Perguntas ao Angelo
1. A **ordem do primeiro olhar** (como foi, normal, o que eu disse, detalhe, contexto) é a sua?
2. Na tela inicial, o cartão "Agora" em volt chamando o check-in é o que você quer em primeiro lugar, ou prefere o último treino no topo
   e o convite menor?
3. O gráfico de **14 dias** com **condicionamento e fadiga** e a frase estão claros? Prefere só uma linha (a forma) para ficar mais
   simples?
4. O que **mais** gostaria de ver na tela inicial que não está aqui?
