---
tipo: design
status: aprovado
dono: lia
atualizado: 2026-11-27
links: [[design/identidade-visual-v3]], [[design/telas/evolucao-tiros]], [[design/telas/inicio-v4]], [[design/telas/inicio-atleta-v3]], [[design/telas/treino]], [[design/referencias-evolucao-inicio]], [[metricas/evolucao-series]], [[metricas/linha-base]], [[metricas/tiros-1km]], [[decisoes/0004-contrato-tela-evolucao]], [[modulos/mobile]]
---
# Tela: Evolução v1 (o atleta escolhe a série e o gráfico diz o que mostra)

Substitui, no desenho, a [[design/telas/evolucao-tiros]] (só tiros de 1 km). Pedido do Angelo (27/11): o atleta escolhe qual evolução
quer ver, e o gráfico atual "não diz nada". Séries, frases e regras de aparecer vêm do inventário do Caio ([[metricas/evolucao-series]]).
**Nada aqui muda o app** até o Rafa implementar. Identidade v3 ([[design/identidade-visual-v3]]). Atleta (Ana), datas e números **sintéticos**.
Os nomes de série nos esboços são **exemplo**; a lista final é a que a API devolver.

## Objetivo
Responder, em poucos segundos: "o que eu quero acompanhar, e estou mais rápido, igual ou mais lento do que nas semanas anteriores?".
O gráfico mostra, a frase **diz**.

## O que torna o gráfico legível (o que faltava)
| faltava | agora |
|---|---|
| uma referência | **faixa do seu normal** ao fundo ([[metricas/linha-base]]), com rótulo escrito |
| a leitura | **frase no topo**, antes do gráfico (`frase_evolucao@1`, texto da API) |
| o que olhar | **destaques**: último treino (número grande e anel), melhor treino (losango), fora do normal (triângulo) |
| escolha | seletor de modalidade e série |
| saber qual treino é o ponto | tocar num ponto mostra o treino e o botão "Abrir treino" |

## Dados (contrato sugerido pelo Caio, a decidir com Theo e Duda)
- Catálogo: `GET /atletas/{id}/evolucao/series` com `id`, `titulo`, `modalidade`, `n_pontos`, `disponivel` e o motivo quando não há.
- Série: `GET /atletas/{id}/evolucao/series/{serie_id}?periodo=12s|6m|1a` com `pontos`, `referencia` (faixa do normal), `eixos`, `frase` e `marcas`.
- **Pedido novo à API:** cada ponto traz `atividade_id` (para "Abrir treino") e o texto pronto do valor e da data. Série sem treino por ponto
  (volume por semana, carga) não abre treino; ver "Tocar num ponto".
- O app **não calcula** pace, mediana, faixa nem frase. Pace em `m:ss`, FC em bpm, como no contrato.

## Hierarquia da informação (de cima para baixo)
1. Título "Evolução".
2. **Escolha:** modalidade (Corrida, Natação, Ciclismo, Geral) e **série**.
3. **Frase** da série (faixa `marca-suave`).
4. **Gráfico** com o valor do último treino em número grande, faixa do normal, destaques e legenda.
5. **Período:** 12 semanas, 6 meses, 1 ano (a frase **não muda** com o período).
6. **Detalhe do ponto selecionado** e "Abrir treino".
7. "Ver os valores em lista" (alternativa em texto) e a versão do cálculo.

## Esboços
Celular, claro e escuro:
![[design/telas/evolucao-v1/evolucao-v1-celular-claro.svg]]
![[design/telas/evolucao-v1/evolucao-v1-celular-escuro.svg]]

Computador (1280): série à esquerda, gráfico à direita, detalhe dentro do cartão:
![[design/telas/evolucao-v1/evolucao-v1-computador-claro.svg]]
![[design/telas/evolucao-v1/evolucao-v1-computador-escuro.svg]]

Escolha da série no celular (9 séries em 4 grupos, uma delas cinza):
![[design/telas/evolucao-v1/evolucao-v1-seletor-celular-claro.svg]]
![[design/telas/evolucao-v1/evolucao-v1-seletor-celular-escuro.svg]]

Estados (carregando, aprendendo, vazio, erro):
![[design/telas/evolucao-v1/evolucao-v1-estados-claro.svg]]
![[design/telas/evolucao-v1/evolucao-v1-estados-escuro.svg]]

## O seletor (funciona com 5 a 10 opções)
Três ideias para não virar uma lista longa:
1. **Dois passos.** A modalidade vem primeiro (segmento de 3 a 4 itens, alvo 44; só aparecem modalidades com ao menos uma série).
   Depois a série, dentro da modalidade. O atleta de uma modalidade só vê as dela.
2. **Grupos com título** dentro da modalidade: **Ritmo**, **Coração**, **Esforço e volume**, **Marcas**. Em 9 a 12 itens o olho acha
   o grupo antes de ler as linhas. Os grupos vêm da API (campo `grupo` no catálogo).
3. **Série indisponível aparece cinza com o motivo** ("Poucos pontos para mostrar"), nunca some e nunca abre tela vazia (regra do Caio).
   Cinza é só um dos sinais: o motivo está escrito.

| tela | como o seletor aparece |
|---|---|
| celular | campo de 56 de altura ("Melhor tiro de 1 km", subtítulo, seta); toque abre **folha de baixo** com os grupos; linha de 56, a escolhida em `marca-suave` com ✓ |
| computador (≥ 900) | **coluna fixa** à esquerda dos gráficos, grupos com título; a escolhida tem barra `cor.link` à esquerda |
| mais de 12 séries numa modalidade | fora do v1; se acontecer, entra busca no topo da folha |

- **Série ao abrir:** a do último treino na primeira vez; depois, **a última que o atleta escolheu** (o app lembra no aparelho; decidido pelo Angelo em 27/11).
- Cada linha: título (`fonte.titulo-cartao`) e uma linha dizendo o que o gráfico mostra (`fonte.rotulo`, `texto-2`).
- Folha: arrastar ou "Fechar" (alvo 44). Escolher fecha a folha e põe o foco no título da série.

## Anatomia do gráfico
| parte | regra | token |
|---|---|---|
| valor grande | valor do **último treino** da série, texto da API, unidade ao lado; abaixo "último treino, ter 18/03" | `fonte.numero-grande` (44), `fonte.rotulo` |
| eixo Y | 3 marcos de `eixos`; pace e velocidade com "mais rápido ↑"; a escala é da API | `fonte.eixo` (11,5) |
| eixo X | datas reais do período (ex.: 03/01, 31/01, 28/02, 21/03) | `fonte.eixo` |
| linha | cheia, 2,5, `cor.grafico.condicionamento` (azul); em "aprendendo", pontilhada | tokens da [[design/identidade-visual-v3]] |
| faixa do normal | retângulo `marca-suave` com o rótulo **"Seu normal 4:08 a 4:24"** (`link` sobre `marca-suave`: 6,3 no claro, 12,7 no escuro); só existe com `referencia`; **nunca** "bom" ou "ruim" | `cor.marca-suave`, `cor.link` |
| ponto comum | círculo vazado, raio 5, alvo de toque 44 | |
| melhor | **losango** cheio, raio 8 (rótulo "melhor" na legenda) | |
| fora do normal | **triângulo** `cor.alerta`, raio 7 (descreve, não alarma: a frase diz "fora do seu normal", sem "problema") | `cor.alerta` |
| selecionado | anel de 2 em `cor.texto`, raio 12, e linha vertical pontilhada | |
| legenda | treino, fora do normal, melhor, normal; sempre visível | `fonte.eixo` |
Nada depende só da cor: forma (círculo, losango, triângulo), rótulo escrito e legenda. Contraste de gráfico mínimo 3:1 (calculado com a fórmula do `contraste.py`): linha azul sobre `superficie` 6,5 no claro e 8,1 no escuro; sobre a faixa do normal 5,9 e 7,0;
triângulo âmbar sobre `superficie` 6,3 e 9,6.

**Janelas da frase.** A frase compara as **4 semanas até ontem** com as **4 anteriores** (mediana). O gráfico **não** desenha essas janelas
no v1 (poluiria); a frase diz os números. O v2 pode sombrear as duas janelas.

**Pontos próximos.** Se dois pontos ficarem a menos de 44 de distância (período de 1 ano), o toque escolhe o ponto **mais próximo no eixo do tempo**,
e o detalhe tem setas "treino anterior" e "treino seguinte" (alvo 44).

## A frase (`frase_evolucao@1`, texto da API)
Descreve; nunca "melhorou", "piorou", conselho ou causa ([[metricas/evolucao-series]], "Regra geral da frase"). Exemplos do Caio:
- Pace: "Pace dos seus treinos leves nas últimas 4 semanas: 5:42/km (mediana de 3 treinos), 12 s/km mais rápido que nas 4 semanas anteriores (5:54/km, 3 treinos)."
- Parecido: "Frequência cardíaca dos seus treinos leves nas últimas 4 semanas: 150 bpm, parecida com a das 4 semanas anteriores (148 bpm)."
- Tiros (esboço): "Melhor tiro de 1 km nas últimas 4 semanas: 4:10/km (mediana de 3 sessões), 8 s/km mais rápido que nas 4 semanas anteriores (4:18/km, 3 sessões)."

Faixa de 14,5 de texto sobre `marca-suave`, rótulo "EM UMA FRASE" em `fonte.sobretitulo`. **Por que em cima:** o atleta lê a conclusão antes de decifrar o gráfico;
o gráfico confirma. Até 4 linhas no celular; o texto escala até 2x sem cortar. Quando a API traz o aviso de "treinos sem FC ficaram de fora", ele vai em
`fonte.rotulo` abaixo da frase.

## Tocar num ponto abre o treino
1. **Primeiro toque:** seleciona o ponto (anel, linha vertical) e mostra o **detalhe** (celular: cartão logo abaixo do gráfico, com faixa `cor.grafico` à esquerda; computador: cartão no canto do gráfico):
   data e hora, o valor, o tipo do treino, o selo de normal e **"Abrir treino"** (botão primário, alvo 48 no celular).
2. **Botão "Abrir treino":** abre a [[design/telas/treino]]. "Voltar" devolve à evolução **com o mesmo ponto selecionado**.
3. Por que dois passos: o dedo cobre o ponto; o primeiro toque mostra o que é, o segundo decide. Evita abrir o treino errado.
4. Séries **sem treino por ponto** (volume e carga por semana, recordes sem atividade): o detalhe mostra só o valor e a data; **sem** botão.
   (Se o recorde do Garmin tiver `atividade_id`, ganha o botão; a API decide.)

## Estados
| estado | o que aparece | texto |
|---|---|---|
| carregando | esqueleto da frase e do gráfico; o seletor já funciona | "Carregando" (só leitor de tela) |
| série ok | tudo acima | |
| aprendendo (menos de 8 pontos no período, sem faixa) | linha **pontilhada**, sem faixa e sem destaque de "fora"; a frase é o texto da API | "Ainda estamos aprendendo o seu normal no treino leve: faltam 3 treinos para mostrar a faixa." |
| poucos treinos para a frase (menos de 3 por janela) | gráfico normal; faixa de frase com o texto da API | "Poucos treinos para comparar: 2 nas últimas 4 semanas, 4 nas 4 anteriores." |
| sem treino nas últimas 4 semanas | gráfico do período; frase da API | "Sem treinos desse tipo nas últimas 4 semanas." |
| série indisponível | só no seletor, cinza e com o motivo; se for a escolhida (via cartão do início), mostra o vazio abaixo | "Poucos treinos de tiros nas últimas 12 semanas" |
| vazio (nenhum dado nessa série) | linha de pulso, título, frase, link "Escolher outra série" | "Sem treinos de tiros ainda" e "Quando você fizer tiros de 1 km, a evolução aparece aqui." |
| erro de rede | ícone de aviso, mensagem, "Tentar de novo" (o seletor continua) | "Não foi possível carregar esta série." e "Verifique a conexão e tente de novo." |
| erro 404 (atleta) | como as outras telas | "Atleta não encontrado" |
| cálculo em atualização (`reclassificacao_pendente`) | linha pequena no rodapé | "cálculo em atualização" |
| acesso expirado | como em [[design/telas/entrar]] | |
| sem nenhuma série disponível | linha de pulso e "Envie o arquivo do seu relógio pela aba Conta e a evolução aparece aqui." | |
Trocar de série **não** limpa a modalidade nem o período; trocar de modalidade vai para a primeira série disponível dela.

## Textos
Título "Evolução"; subtítulo "Escolha o que acompanhar"; rótulo "SÉRIE"; "Corrida: o que acompanhar" (título da folha); "Fechar"; "EM UMA FRASE";
"Seu normal 4:08 a 4:24" (os números vêm da API); "mais rápido ↑"; legenda "treino", "fora do normal", "melhor", "normal"; "Período", "12 semanas", "6 meses", "1 ano";
"8 treinos no período. Toque num ponto para ver o treino."; "Abrir treino"; "Ver os valores em lista"; "Treino anterior", "Treino seguinte"; rodapé "cálculo: tiros_1km@5".

## Acessibilidade
- Ordem de leitura: título, modalidade, série, **frase**, gráfico, período, detalhe, lista.
- O gráfico é um item com o rótulo igual à **frase**; os pontos são itens de lista dentro de "Ver os valores em lista" (data, valor, "dentro/fora do normal", "Abrir treino"). Quem usa leitor de tela nunca precisa tocar no desenho.
- Ponto: "Sessão de 18/03, 4:11 por quilômetro, dentro do seu normal". Faixa: "Seu normal, de 4:08 a 4:24 por quilômetro".
- Alvos de 44 (modalidade, período, ponto, setas, fechar). Foco visível com `cor.link`. Respeita "reduzir movimento": sem animação de linha.
- Seletor: papel de lista com seleção; a escolhida é anunciada ("selecionada"); a cinza é anunciada com o motivo.
- Texto até 2x: o seletor quebra linha; o número grande limita a 1,3x.

## O que muda em relação ao app de hoje
| hoje | proposta |
|---|---|
| só tiros de 1 km | catálogo de séries por modalidade |
| gráfico sem referência e sem frase | faixa do normal, destaques e frase no topo |
| dois painéis (pace e FC) | um gráfico por série; a FC dos tiros vira série própria ou segundo painel opcional (decisão do Rafa com o Caio) |
| ponto abre detalhe e "Ver treino" | primeiro toque detalha, "Abrir treino" abre o treino |
| sem período | 12 semanas, 6 meses e 1 ano |
| `GET /evolucao/tiros-1km` | continua; o catálogo novo é a rota da tela |

## Fora do v1
Sombrear as janelas da frase; comparar duas séries na mesma tela; busca no seletor; "Ver os treinos da semana" a partir de uma barra de volume; zoom e arrasto no gráfico;
metas e alertas.

## Decisões do Angelo (27/11, "ok em tudo")
Ciclismo em casa e na rua em séries separadas; período inicial de 12 semanas, com 6 meses e 1 ano; treino "quente" = sensação de 28 °C ou mais;
natação e ciclismo evoluem por ritmo, volume e FC por enquanto; a Evolução lembra a última série escolhida.
