---
tipo: decisao
status: aceita
dono: caio
atualizado: 2026-11-04
links: [[metricas/tiros-1km]], [[decisoes/0001-modelo-de-dados-minimo]], [[decisoes/0002-segmento-intensidade-e-versao]], [[decisoes/0005-serie-de-tiros-o-que-entra]], [[modulos/banco]], [[modulos/ingestao-garmin]], [[produto/roadmap]], [[glossario]]
---
# ADR: 0008 Detecção de esforços (corrida por distância, ciclismo por duração)

> Aceita em 04/11 (issue #148): item 9 aprovado pelo Theo e itens 2 a 4 de "A confirmar" aprovados pelo Angelo.
> Ficam só duas pendências com dado real (itens 5 e 6), que não bloqueiam. Nenhuma linha de código muda neste PR. Todos os números abaixo são sintéticos.

## Contexto
A série de tiros reconhece só voltas de ~1 km, uma a uma ([[metricas/tiros-1km]], `tiros_1km@4`). Ficam de fora:
tiros de outras distâncias; tiros que o lap automático corta (1500 m chega como 1000 m + 500 m); a leitura do treino
inteiro (aquecimento, bloco principal, recuperações, desaquecimento); treinos contínuos fortes; e o ciclismo, em que
o esforço se define por tempo. Pedido de produto de 04/11: detecção genérica de esforços na Meta 5, antes da carga
(que passou a ser a Meta 6). Corrida por **distância**, ciclismo por **duração**.

### O que o código do `main` faz hoje (conferido)
- `tiros_1km.py` (`VERSAO = "tiros_1km@4"`) trabalha volta a volta. Candidata = 950 a 1050 m (`TOLERANCIA_M = 50`).
  Pausa = volta de menos de 200 m (`PAUSA_MAX_M`). Recuperação = vizinha mais lenta em 8% (`GANHO_MINIMO_PACE`).
  Filtros: ritmo parecido 20%, bloco contínuo 15%, ritmo habitual 10%, volume do bloco principal.
  A intensidade do FIT só veta (`rest`, `recovery`, `warmup`, `cooldown`) e marca fronteira (`warmup`, `cooldown`).
  Só corrida. Não olha o tempo entre uma volta e outra, só pace e distância.
- `Segmento` (`db/models.py`): `ordem`, `tipo` (`volta`, `tiro`, `recuperacao`, com `CHECK`), `inicio_offset_s`,
  `duracao_s`, `distancia_m`, `fc_media`, `pace_s_km`, `intensidade`, `versao_deteccao`. **Uma linha por volta.**
  Não há velocidade, potência, cadência nem altimetria por volta.
- **Duração gravada = tempo em movimento.** Em `ingestao/garmin/fit.py`, `duracao_s` do segmento é o
  `total_timer_time` do lap (o relógio para o cronômetro quando a pausa automática atua), e `inicio_offset_s` é
  `lap.start_time - session.start_time` em relógio de parede. Logo `inicio_offset_s` conta o tempo corrido e
  `duracao_s` não conta o tempo parado: a diferença entre os dois é justamente o tempo de pausa (item 3).
- `Atividade.modalidade` é `corrida`, `natacao`, `ciclismo` ou `outra`. `pace_habitual()` (mediana do pace das
  corridas de mais de 3 km nas 12 semanas anteriores, sem esteira) já existe e vale para qualquer métrica de corrida.

## Decisão

### 1. O que é um esforço, e as categorias de bloco
Lê-se a atividade como uma sequência de **blocos**. Bloco = uma ou mais voltas consecutivas juntadas (item 2), com
`distancia_m`, `duracao_s` (tempo em movimento), pace (corrida) ou velocidade (ciclismo) e FC média ponderada pela
duração (mesma conta da `agregar_sessao`: soma(FC x duração) / soma(duração), só sobre voltas com FC).
Pace do bloco = soma das durações / soma das distâncias x 1000, nunca a média dos paces das voltas.
Velocidade (km/h) = distância / duração x 3,6.

Cinco categorias, mutuamente exclusivas, a mesma lista nas duas modalidades:

| categoria | o que é |
|---|---|
| `esforco` | bloco de intensidade alta pelo item 5 (corrida: pace; ciclismo: velocidade) |
| `recuperacao` | tudo que fica entre dois esforços e não é esforço (trote, caminhada, parado) |
| `aquecimento` | tudo que vem antes do primeiro esforço, se houver esforço |
| `desaquecimento` | tudo que vem depois do último esforço, se houver esforço |
| `leve` | atividade sem nenhum esforço: todos os blocos são `leve` |

Pausas (tempo parado) não são blocos: são o intervalo entre blocos e entram na conta da recuperação (item 3).
Consequência: a categoria vem da **posição relativa aos esforços**, não de um limite absoluto, o que mantém a regra
geral (ADR 0005, item 2). A intensidade do FIT (`warmup`, `cooldown`) é só dica: nunca transforma um bloco em
esforço e, se a estrutura disser que o bloco é esforço, a estrutura vence (mesma política da `tiros_1km`).

### 2. Juntar laps automáticos
Duas voltas consecutivas entram no mesmo bloco quando **as duas condições** valem:
- **sem pausa**: tempo parado entre elas menor que `PAUSA_SEPARA_S` (proposta: **15 s** na corrida, **30 s** no
  ciclismo, onde semáforo e cruzamento são comuns);
- **ritmo parecido**: pace (ou velocidade) da volta dentro de `JUNTAR_TOLERANCIA` (proposta: **5%**) do pace do
  bloco acumulado até ali (ponderado por distância). Comparar com o bloco e não com a volta anterior evita que um
  progressivo suave se junte inteiro por passos de 3% a 4%.

O limite de 5% fica entre o ruído do auto-lap (3% a 4% numa rodagem, nota da `tiros_1km`) e os 8% que separam
recuperação de tiro. Voltas entre 5% e 8% diferentes ficam em blocos separados.
No ciclismo a comparação é da velocidade (km/h), na corrida do pace (s/km); como são inversos, 5% de diferença
de velocidade é ~4,8% de pace, e a nota da métrica escreve a conta.

Exemplo 1 (corrida, lap automático de 1 km): 1000 m a 240 s/km (240 s) e 500 m a 241 s/km (120,5 s), sem pausa,
seguidos de 2 min parado. Diferença de pace 0,4%, menor que 5%: **um bloco** de 1500 m, 360,5 s,
pace = 360,5 / 1500 x 1000 = **240,3 s/km**. Cai na faixa `d1500` (item 5).

Exemplo 5 (ciclismo, lap a cada 5 km): bloco de 20 min a 24 km/h = 8 km, cortado em 5 km (750 s) + 3 km (450 s),
mesma velocidade, sem pausa: um bloco de 8 km e 1200 s (velocidade = 8 / 1200 x 3600 = 24 km/h), faixa `t20`.

### 3. Recuperação pelo tempo de pausa
Para a volta `i`, **tempo parado** `parada_s[i] = (inicio_offset_s[i+1] - inicio_offset_s[i]) - duracao_s[i]`,
mínimo zero. Funciona porque `inicio_offset_s` é tempo corrido e `duracao_s` é tempo de cronômetro (ver "O que o
código faz hoje"). Para a última volta não há `i+1`: `parada_s = 0`. A pausa automática do relógio aparece aqui;
se o atleta usa lap manual sem pausa automática, a parada fica **dentro** da volta (como volta lenta ou de poucos
metros) e é tratada como **volta de pausa**:
- corrida: pace maior que `PAUSA_PACE_S_KM` (proposta **600 s/km**, caminhada ou parado) ou distância menor que
  `PAUSA_DIST_MIN_M` (proposta **50 m**);
- ciclismo: velocidade menor que `PAUSA_VEL_KMH` (proposta **5 km/h**).

A regra antiga de "menos de 200 m é pausa" (`PAUSA_MAX_M`) fica só na visão `tiros_1km`, porque uma volta de
200 m é um esforço válido na nova detecção.

**Tempo de recuperação** entre dois esforços = soma de `parada_s` das voltas do trecho + duração dos blocos
`recuperacao` do trecho. Um intervalo sem bloco entre dois esforços (só parada) é uma recuperação passiva.
Um intervalo com parada de pelo menos `PAUSA_SEPARA_S` separa os blocos mesmo que o ritmo seja parecido.

Exemplo 2 (corrida): 2 km a 330 s/km (660 s), 10 x 400 m a 220 s/km (88 s cada) com 90 s parado entre eles,
1 km a 340 s/km (340 s). Parada de 90 s e maior que 15 s: nada se junta. Resultado: 9 recuperações de
90 s (810 s no total), `aquecimento` (2000 m), 10 `esforco` de 400 m a 220 s/km (faixa `d400`, 4000 m, 880 s) e
`desaquecimento` (1000 m).

### 4. Aquecimento e desaquecimento
Regra geral, sem nada de atleta: com **pelo menos um esforço** na atividade, todos os blocos antes do primeiro são
`aquecimento` e todos depois do último são `desaquecimento`. Como esforço é por definição mais rápido que o ritmo
de referência (item 5), o aquecimento é sempre mais lento que o bloco principal. Sem nenhum esforço, não há
aquecimento nem desaquecimento: tudo é `leve`. Não há limite de duração do aquecimento nesta versão (limitação, "a
confirmar"). Exemplo 4 (ciclismo): a última recuperação de 2 min a 22 km/h vem depois do último esforço e fica
no desaquecimento junto dos 10 min a 24 km/h (22 e 24 diferem mais de 5%, então são dois blocos, ambos
`desaquecimento`: 12 min no total).

### 5. Medida do esforço por modalidade
**Referência de intensidade** (`ref`):
- corrida: o **ritmo habitual** do atleta (`pace_habitual`, já existente);
- ciclismo: a **velocidade habitual** em bicicleta, mesma ideia: mediana da velocidade das pedaladas de mais de
  30 min, fora do trainer e anteriores à sessão, nas 12 semanas anteriores (com menos de 10, todo o histórico);
- sem histórico (atleta novo), a referência é a mediana, ponderada pela duração, dos blocos da própria atividade
  (nas duas modalidades). Limitação: num treino em que o esforço domina o volume, a mediana sobe e o
  esforço some; por isso a referência por atividade é só reserva, marcada no resultado (`ref_origem`).

**Limiar de esforço**: corrida, `pace do bloco <= ref x 0,90` (mesmo 10% da `HABITUAL_GANHO_MINIMO`);
ciclismo, `velocidade do bloco >= ref x 1,15` (**15%**, maior porque relevo e vento mexem muito na velocidade).

**Faixas nomeadas de corrida (por distância)**, com tolerância `max(5%, 30 m)` para cada lado, escolhida para
bater com a faixa atual de 1 km (950 a 1050 m) e não deixar faixas se sobreporem:

| faixa | alvo | aceita |
|---|---|---|
| `d200` | 200 m | 170 a 230 m |
| `d300` | 300 m | 270 a 330 m |
| `d400` | 400 m | 370 a 430 m |
| `d500` | 500 m | 470 a 530 m |
| `d600` | 600 m | 570 a 630 m |
| `d800` | 800 m | 760 a 840 m |
| `d1000` | 1000 m | 950 a 1050 m |
| `d1200` | 1200 m | 1140 a 1260 m |
| `d1500` | 1500 m | 1425 a 1575 m |
| `d2000` | 2000 m | 1900 a 2100 m |
| `d3000` | 3000 m | 2850 a 3150 m |
| `d5000` | 5000 m | 4750 a 5250 m |

**Faixas nomeadas de ciclismo (por duração)**, tolerância `max(8%, 15 s)` para cada lado:
`t1` (1 min, 45 a 75 s), `t2` (105 a 135 s), `t3` (165 a 195 s), `t4` (221 a 259 s), `t5` (276 a 324 s),
`t8` (442 a 518 s), `t10` (552 a 648 s), `t12` (662 a 778 s), `t15` (828 a 972 s), `t20` (1104 a 1296 s),
`t30` (1656 a 1944 s), `t40` (2208 a 2592 s), `t60` (3312 a 3888 s). Os limites usam a duração em segundos,
arredondados ao segundo mais próximo (só a `t12` muda: 662,4 a 777,6 vira 662 a 778; nas outras o resultado é o mesmo).

Um esforço fora de qualquer faixa continua sendo esforço, com `faixa = NULL` e a distância (ou duração) real.

**Intensidade do ciclismo sem potência**: velocidade do bloco contra a velocidade habitual, e a FC como
**apoio**, não como critério (FC tem atraso de 1 a 2 min em blocos curtos e deriva em blocos longos, e muda com calor
e hidratação). Sem altimetria e sem vento no modelo, a velocidade subestima a intensidade na subida e superestima
na descida e com vento a favor. A ADR **assume** essa limitação e a repete na nota da métrica; quando houver potência
(Meta futura), o critério muda e a versão sobe.

**Fartlek por tempo na corrida** (esforços em minutos): proposta, **fora da Meta 5**. A estrutura já comporta
(o item 5 só ganharia um segundo conjunto de faixas por duração para a corrida), mas não há demanda confirmada.

Exemplo 4 (ciclismo): 15 min a 25 km/h, 5 x [4 min a 36 km/h + 2 min a 22 km/h], 10 min a 24 km/h, com velocidade
habitual de 22 km/h. Limiar = 22 x 1,15 = 25,3 km/h: 25, 24 e 22 ficam abaixo, 36 passa (36 / 22 = 1,64).
Resultado: `aquecimento` (15 min), 5 `esforco` de 4 min a 36 km/h (faixa `t4`, 36 x 4 / 60 = 2,4 km cada), 4
`recuperacao` de 2 min a 22 km/h entre eles, `desaquecimento` (2 + 10 min). Com habitual de 20 km/h o limiar
seria 23 km/h e o aquecimento de 25 km/h viraria esforço: a regra depende da referência, e por isso ela é
limitação declarada.

### 6. Treino-chave contínuo
Uma **sequência contínua forte** = blocos `esforco` consecutivos, sem `recuperacao` entre eles. É **treino-chave
contínuo** quando soma pelo menos `CONTINUO_MIN_S` (proposta **20 min**, 1200 s, nas duas modalidades) e a atividade
não tem outra estrutura de repetição (menos de 2 esforços fora da sequência). Corrida: o limiar do item 5
(pace <= habitual x 0,90). Ciclismo: velocidade >= habitual x 1,15 durante os 20 min.

Exemplo 3 (corrida): 8 km a 270 s/km = 2160 s (36 min), ritmo habitual 330 s/km. Limiar = 330 x 0,90 = 297 s/km;
270 <= 297, margem de 18,2% (1 - 270/330). 2160 s >= 1200 s: **treino-chave contínuo**, 1 esforço, sem repetições.
Esse esforço fica sem faixa (8000 m passa de `d5000`).
Fartlek moderado e progressivo forte podem cair aqui como contínuo forte (os blocos têm 10% ou mais de ganho
sobre o habitual); a visão da série de 1 km ainda os exclui (item 8).

### 7. Calibração pelos recordes pessoais
**Só o desenho**; fica fora da Meta 5. Os recordes pessoais chegam ao banco na Meta 6 (#174). Desenho: no lugar de
(ou além de) `ref` e dos 10% fixos, o limiar passa a ser expresso como fração do recorde do atleta na distância da
faixa (corrida) ou na duração da faixa (ciclismo): por exemplo, esforço de `d400` se o pace for no máximo X% mais
lento que o recorde de 400 m. Exige a ADR da calibração e uma nova versão (`esforcos@2`). Até lá vale o ritmo
habitual, que só depende do histórico de atividades.

### 8. Relação com a `tiros_1km`
A série de 1 km passa a ser uma **visão** dos esforços: `categoria = esforco`, `faixa = d1000`, corrida, fora da
esteira, mínimo de **2** por sessão (decisão de produto de 04/11, #149) e treino misto contando (#150): os de 1 km
contam, os curtos não. O "bloco principal" fica definido pela posição (do primeiro ao último esforço), sem a regra de
volume (item 6 da `tiros_1km@4`), porque o aquecimento e o desaquecimento já saem por categoria. Seguem como filtros da
visão: ritmo parecido (20% sobre a mediana), bloco contínuo (15% sobre o vizinho de ~1 km) e ritmo habitual (10%).
Um esforço de 1500 m (item 2) **não** é tiro de 1 km. Dois km seguidos no mesmo ritmo viram um único esforço de
2000 m (`d2000`), o que reproduz a regra "vizinha de 1 km no mesmo ritmo não separa".
- Versão: a visão sai como nova versão da `tiros_1km`, cujo número a #168 define (depende de as #149 e #150 serem
  implementadas antes ou absorvidas). A visão deixa de ler voltas e passa a ler `bloco_atividade` (item 9).
- Reclassificação: `worker.reclassificar` recria os esforços e a visão (ADR 0005, item 4).
- **Testes de regressão** (casos das #149, #150 e #168, todos sintéticos):
  1. 2 x 1000 m a 250 s/km com 400 m de recuperação a 420 s/km: `250 <= 420 x 0,92 = 386,4`, 2 tiros, entra.
  2. Rodagem de 1 km seguidos no mesmo ritmo: um bloco `leve`, fora.
  3. 1 x 1000 m isolado: um esforço só, fora (mínimo de 2).
  4. 5 x 1000 m a 250 s/km com 400 m a 420 s/km, depois 8 x 400 m a 230 s/km com 200 m a 450 s/km: entra, 5 tiros
     de 1 km, pace da sessão 250 s/km (os `d400` não contam).
  5. Tiros curtos com 1 km de aquecimento e 1 km de desaquecimento lentos: fora (são `aquecimento` e `desaquecimento`).
  6. Progressivo, fartlek e bloco contínuo de `test_tiros_1km.py`: mesmo resultado, ou mudança justificada na nota.

### 9. Modelo de dados (aprovado: Theo, 04/11)
**Decisão (aprovada pelo Theo em 04/11): tabela nova `bloco_atividade`** (nome escolhido para não se confundir com a categoria `esforco`), uma linha por **bloco** (todas as categorias, não só os esforços), e `segmento`
não muda.

Por que não ampliar `segmento.tipo`: o segmento é uma volta e o bloco junta N voltas (1000 m + 500 m = 1 esforço);
`tipo` de uma volta não guarda a distância, a duração, o pace e a FC do bloco juntado, nem a faixa, nem o tempo
parado. Ampliar o `CHECK` também obrigaria a migrar a lista a cada categoria nova.

Colunas:
| coluna | tipo | notas |
|---|---|---|
| `id` | inteiro, PK | |
| `atividade_id` | FK `atividade.id`, `ON DELETE CASCADE`, indexada | |
| `ordem` | inteiro | posição do bloco; `UNIQUE (atividade_id, ordem)` |
| `categoria` | texto (20), `CHECK` | `esforco`, `recuperacao`, `aquecimento`, `desaquecimento`, `leve` |
| `volta_inicial`, `volta_final` | inteiros | `segmento.ordem` da primeira e da última volta do bloco (voltas contíguas) |
| `inicio_offset_s` | real | do primeiro segmento do bloco |
| `duracao_s` | real | tempo em movimento (soma) |
| `parada_apos_s` | real, nulo | tempo parado entre este bloco e o seguinte (item 3) |
| `distancia_m` | real, nulo | |
| `fc_media` | real, nulo | ponderada pela duração |
| `pace_s_km` | real, nulo | como no `segmento`; velocidade (km/h) se calcula na leitura |
| `faixa` | texto (10), nulo | `d400`, `t4`...; nulo fora de qualquer faixa |
| `treino_chave` | booleano | item 6, só em `esforco` |
| `versao_deteccao` | texto (40) | `esforcos@1`, mesmo formato da ADR 0002 |

Regras: a tabela guarda **só o que a regra produz**; a modalidade vem de `atividade.modalidade`. Idempotência:
detectar de novo apaga e recria os blocos da atividade numa transação (rodar duas vezes não muda nada; versão nova
redetecta tudo; `worker.detectar_esforcos`, #166). Migração nova do Alembic (sem editar as anteriores), com
`downgrade`, testada em SQLite e Postgres. `segmento.tipo`, `segmento.versao_deteccao` e a `tiros_1km` continuam
funcionando enquanto a #168 não troca a fonte da série.

**Alternativas ao item 9**: (a) ampliar `segmento.tipo` com as 5 categorias: menor, mas perde o bloco juntado;
(b) não gravar, calcular na leitura: simples, mas a série e a API teriam de reprocessar as voltas toda vez e não
haveria versão gravada para reclassificar. A ADR 0002 já previa uma tabela de derivadas "na Meta 5"; esta é ela, só
para esforços. Decisão do Theo (04/11): **tabela `bloco_atividade`**.

## Alternativas consideradas
- **Referência só da atividade (mediana ponderada)** em vez do ritmo habitual: independe de histórico, mas falha
  quando o esforço domina o volume (2 km lentos + 4 km fortes: a mediana é a do esforço). Fica só como reserva.
- **Limiar absoluto de pace** (ex.: abaixo de 4:00/km): específico de atleta, proibido pela ADR 0005 (item 2).
- **Usar a intensidade do FIT para classificar**: o relógio nem sempre a grava e, em rodagem, rotula tudo `active`.
  Fica como dica e veto (ADR 0002 e 0005).
- **Faixas por volta, sem juntar laps**: mantém `segmento` como está, mas um tiro de 1500 m com lap de 1 km nunca
  aparece.
- **Faixas de ciclismo por distância**: o treino de ciclismo se prescreve por tempo; distância depende de relevo.
- **Potência para o ciclismo**: não existe no modelo nem nas fixtures; fora do escopo.

## Consequências
- Cada atividade ganha blocos com categoria; a série de tiros de 1 km vira consulta sobre eles (#168).
- O ciclismo passa a ter estrutura de treino (aquecimento, esforços de minutos, desaquecimento) sem potência, com
  limitação conhecida de relevo e vento.
- Nova tabela `bloco_atividade` e nova migração (item 9, aprovado pelo Theo), e uma nova `VERSAO` (`esforcos@1`) com reclassificação
  completa ao mudar qualquer constante.
- Todos os limites propostos (5%, 15 s, 30 s, 600 s/km, 50 m, 5 km/h, 10%, 15%, 20 min) são **decisão do projeto,
  não de artigo**, e ficam como constantes nomeadas em um só módulo; validação só com dado real fora do git.
- Fixtures e oráculo dos exemplos acima: #161. Blocos: #162. Corrida: #163. Ciclismo: #164 e #165.
  Banco e worker: #166.

## Limitações
- **Ciclismo sem histórico**: a referência é a mediana, ponderada pela duração, da própria atividade. Se o esforço
  domina o volume, a mediana sobe e esforços reais deixam de ser detectados; num treino todo leve, o ritmo de
  passeio pode virar esforço. O resultado traz `ref_origem` para a tela poder avisar.
- **Fartlek e progressivo** (blocos com 10% ou mais de ganho sobre o habitual, sem recuperação lenta no meio) caem como
  **treino-chave contínuo** (item 6), não como séries. A visão de tiros de 1 km continua os excluindo (item 8).
- Ciclismo sem potência: a velocidade sofre com relevo e vento (item 5). Sem teto de duração para o aquecimento.

## Fontes
- Garmin FIT SDK, mensagem `lap`: `total_timer_time` (tempo de cronômetro, exclui pausa automática),
  `total_elapsed_time` (tempo corrido), `intensity` (`active`, `rest`, `warmup`, `cooldown`, `recovery`, `interval`,
  `other`). Base do item 3. Ver ADR 0002 e `ingestao/garmin/fit.py`.
- Regra própria do projeto, sem artigo: 5% de junção, 8% recuperação, 10% ritmo habitual, 20% ritmo parecido, 15%
  bloco contínuo (todos já registrados na `tiros_1km` e na ADR 0005).
- Estrutura "esforço, recuperação" e durações típicas de séries: Buchheit e Laursen, *High-intensity interval
  training, solutions to the programming puzzle*, Sports Medicine, 2013 (partes I e II); Seiler, *What is best
  practice for training intensity and duration distribution in endurance athletes?*, IJSPP, 2010; Daniels,
  *Daniels' Running Formula* (ritmos de limiar e de intervalado, esforços contínuos de ~20 min). Citados como
  apoio da ideia de faixas e do mínimo de 20 min; **não consultados nesta rodada**, ver "A confirmar".

## A confirmar
Itens 1 a 4 aprovados. Em aberto, sem bloquear: 5 e 6 (Caio, com dado real). Os itens 7 a 10 são seguimentos de outras issues.

1. ~~Modelo de dados do item 9~~: aprovado pelo Theo em 04/11 (tabela `bloco_atividade`).
2. ~~Aprovado pelo Angelo em 04/11.~~ Tolerância de junção (5%) e pausa que separa (15 s corrida, 30 s ciclismo); conferir com um treino
   real, fora do git, que o lap automático cortando esforço de 1500 m junta como esperado.
3. ~~Aprovado pelo Angelo em 04/11.~~ O que é treino-chave contínuo (20 min e 10% de ganho na corrida; 20 min e 15% no ciclismo).
4. ~~Aprovado pelo Angelo em 04/11.~~ Faixas de corrida e de ciclismo (as listas acima) e a tolerância de cada lado.
5. **Caio com dado real**: o campo `total_timer_time` do lap e o `start_time` do lap são mesmo coerentes em
   exportações com pausa automática ligada e desligada (premissa do item 3). Se o relógio não grava `start_time`
   do lap, `inicio_offset_s` vem 0 (código em `fit.py`) e o tempo parado não é computável: cair para a volta de pausa.
6. **Caio**: velocidade habitual do ciclismo (janela de 12 semanas e mínimo de 30 min por pedalada) e se a
   referência por atividade (reserva) é aceitável para atleta novo.
7. **Caio**: as referências bibliográficas: abrir os textos e conferir o que sustentam antes de a nota da métrica citá-las.
8. **Theo, na #168**: numeração final da versão da `tiros_1km` conforme a decisão sobre as #149 e #150.
9. Fartlek por tempo na corrida (proposta, fora da Meta 5) e teto de duração do aquecimento.
10. Calibração pelos recordes pessoais (item 7): ADR própria depois da #174.

## Data e quem decidiu
2026-11-04. Pedido de produto: Angelo (04/11). Rascunho: Caio (ciência). Aprovação do Theo no PR desta ADR
(item 9 em especial). Issue #148.

Aprovações em 04/11: item 9 (tabela `bloco_atividade`) pelo Theo; itens 2 a 4 de "A confirmar" pelo Angelo (junção de laps com
pausa abaixo de 15 s na corrida e 30 s no ciclismo e 5% de ritmo; faixas de corrida e de ciclismo com as tolerâncias
propostas; treino-chave contínuo de 20 min, com 10% na corrida e 15% no ciclismo). Status passa de `rascunho` a `aceita`.
Pendências sem bloqueio: itens 5 e 6, do Caio com dado real.
