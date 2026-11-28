---
tipo: metrica
status: rascunho
dono: caio
atualizado: 2026-11-28
links: [[metricas/frase-forma]], [[metricas/serie-carga]], [[metricas/tiros-1km]], [[metricas/linha-base]], [[metricas/esforcos]], [[metricas/recuperacao]], [[metricas/carga-treino]], [[design/telas/evolucao-tiros]], [[design/telas/inicio-atleta-v3]], [[modulos/grafico-tiros]], [[glossario]]
---
# Evolução: catálogo de séries, "frase da evolução" e cartões do início (proposta)

**Só proposta.** Nada aqui muda código: o que cada série precisa, a frase de cada uma (`frase_evolucao@1`, mesmo espírito da
[[metricas/frase-forma]]) e os candidatos a cartão do início. A Lia desenha as telas a partir desta nota; o Theo decide a rota e a
ordem de implementação. A cobertura de cada série é descrita pelo que a fonte entrega e pelo que falta para a série existir.

## O que mede
Para cada série da Evolução: o que o gráfico mostra, de onde vem o dado, quando ela aparece e a **frase** que diz o que o gráfico diz.
Descrição, nunca recomendação, nunca alarme, nunca "melhorou/piorou", nunca causa. Números sempre calculados por código; a frase é um
modelo de texto preenchido pela API, sem IA.

## Por que o gráfico de tiros "não diz nada" hoje
Só há pontos: sem **referência** (o normal do atleta, que a [[metricas/linha-base]] já calcula), sem **frase** (a tendência não está escrita
em lugar nenhum), e uma única série (o melhor tiro de 1 km), que só existe para quem faz tiros de 1 km. Propostas: faixa do normal ao fundo
e a frase da seção "Regra geral". A escolha da série vira o tema da tela.

## Regra geral da frase (`frase_evolucao@1`)
Vale para as séries "por treino" (pace, FC, eficiência, melhor esforço). Tudo calculado sobre a data local do treino ([[decisoes/0003-fuso-da-atividade]]).
- **Janelas:** `R` = os 28 dias que terminam **ontem** (como a série de carga: hoje ainda não acabou); `A` = os 28 dias antes de `R`. São
  4 semanas contra 4 semanas, qualquer que seja o período mostrado no gráfico.
- **Mínimo:** 3 treinos em cada janela (2 no melhor esforço de tiros, igual ao mínimo de `tiros_1km@6`). Menos que isso em `R`: "Poucos
  treinos para comparar: N nas últimas 4 semanas, M nas 4 anteriores." Zero em `R`: "Sem treinos desse tipo nas últimas 4 semanas."
- **Estatística:** mediana de cada janela (`mR`, `mA`), a mesma robustez da linha de base. `d = mR - mA`.
- **Limiar de "parecido":** `L = max(piso_abs, piso_rel x |mA|)`, com o piso da série (tabela abaixo). `|d| < L` → "ficou parecido"
  (o limite entra como diferença). Os pisos de pace (3%), FC (4 bpm) e carga por hora (5%) são os da `linha_base@3`, para o gráfico e o selo de
  normal não discordarem.
- **Direção:** só a palavra do eixo (mais rápido/lento; mais alta/baixa; mais/menos). Nunca bom ou ruim.
- **Modelo:** "{série}, nas últimas 4 semanas: {mR} (mediana de {nR} treinos), {|d|} {direção} que nas 4 semanas anteriores ({mA}, {nA}
  treinos)." ou "..., parecido com as 4 semanas anteriores ({mA}, {nA} treinos)."
- **Aviso à parte:** treinos com a medida sem valor (ex.: sem FC, esteira) não entram nem na conta; a frase diz quantos ficaram de fora quando
  forem 20% ou mais dos treinos da série na janela `R`.

**Exemplo à mão (pace de corrida leve).** `R`: 342, 336, 348 s/km → mediana 342 (5:42). `A`: 354, 348, 360 → mediana 354 (5:54). `d = -12`;
`L = max(0; 0,03 x 354 = 10,62) = 10,62`; `|d| = 12 >= 10,62` → "12 s/km mais rápido". Com `A` = 348, 345, 351 (mediana 348): `d = -6 < 10,44` → "parecido".
**FC:** `R` 148, 150, 152 (150); `A` 146, 148, 150 (148); `d = 2 < 4` bpm → parecido.

## Catálogo de séries

A coluna "precisa para existir" diz o que a fonte tem de entregar para a série ter pontos (nada aqui descreve um atleta). Existe na API: **sim** / **parcial** (dado e conta existem, falta a rota) / **não** (falta métrica).
**Ids que existem no código (28/11, `evolucao_series.POR_ID`):** `corrida.tiros`, `corrida.pace.<tipo>`, `corrida.fc.<tipo>`, `corrida.volume_km`, `corrida.volume_h`, `natacao.ritmo`, `natacao.fc`, `natacao.volume_m`, `ciclismo.velocidade.<rua|casa>`, `ciclismo.fc.<rua|casa>`, `ciclismo.volume_km` e `geral.ctl`. Os outros ids das tabelas abaixo (marcados "previsto") ainda **não existem** no catálogo; a lista do código é a que vale (o chat só aceita estes, [[decisoes/0017-chat-do-atleta]]).

Janela do gráfico (decidida): abre em 12 semanas, com 6 meses e 1 ano como opção do atleta; a frase não muda com ela.

### Corrida
| id | o que o gráfico mostra | origem | precisa para existir | na API | piso |
|---|---|---|---|---|---|
| `corrida.tiros` | melhor tiro (e FC) de cada sessão intervalada, com a faixa do normal | [[metricas/tiros-1km]] | treino com 2 ou mais tiros de 1 km detectados (`tiros_1km@6`) | **sim** (`/evolucao/tiros-1km`), sem frase nem faixa | pace 3% |
| `corrida.esforcos` | melhor pace do esforço na distância escolhida (200 m a 5 km) por sessão | `bloco_atividade` (`esforcos@1`, [[metricas/esforcos]]) | treino com esforços detectados na distância escolhida (`esforcos@1`) | **parcial** (a conta de `tiros_1km` generaliza por `faixa`) | pace 3% |
| `corrida.pace.<tipo>` | pace médio de cada treino do tipo (leve, moderado, longo) | `atividade.duracao_s / distancia_m`, sem esteira | treino com tipo, distância e duração; sem esteira | **parcial** (valor já usado na linha de base) | pace 3% |
| `corrida.fc.<tipo>` | FC média de cada treino do tipo | `atividade.fc_media` | treino com tipo e FC média (FIT ou export) | **parcial** | 4 bpm |
| `corrida.eficiencia` | metros por batimento (ver fórmula) nos treinos leve/moderado/longo | pace e FC médios | treino com tipo, distância, duração e FC | **não** (`eficiencia@1` a implementar) | 3% |
| `corrida.recordes` | linha do tempo dos recordes (1 km, 1 milha, 5 km, 10 km, meia, maior distância) | `recorde_pessoal` (Garmin) | marcas pessoais do export Garmin importado | **parcial** (tabela gravada, sem rota) | sem limiar |
| `corrida.limiar` | limiar de FC e de velocidade estimados pelo relógio, no tempo | `limiar_atleta` (Garmin) | limiares do export Garmin importado | **parcial** (sem rota) | sem limiar |
| `corrida.volume` | km e horas por semana | soma de `atividade` | qualquer corrida (distância e duração) | **não** | 10% |
| `corrida.carga` (previsto; hoje só `geral.ctl`) | carga por semana e CTL ao longo do tempo | `carga@2` e `serie_carga@2` | treino com carga calculada (FC e limiar, ou pace e limiar) | **sim** (`/carga`, só 14 dias na tela) | 5% (CTL) |

### Natação
| id | o que o gráfico mostra | origem | precisa para existir | na API | piso |
|---|---|---|---|---|---|
| `natacao.ritmo` | ritmo médio com pausas por 100 m de cada treino de piscina | `duracao_s / distancia_m x 100` | treino de piscina com distância e duração; águas abertas é outro ambiente | **não** | 3% |
| `natacao.volume` | metros e horas por semana | soma de `atividade` | qualquer treino de natação | **não** | 10% |
| `natacao.fc` | FC média por treino | `atividade.fc_media` | treino com FC média | **parcial** | 4 bpm |
| `natacao.recordes` | recordes 100, 400, 750, 1000 e 1500 m de piscina e a maior distância | `recorde_pessoal` | marcas pessoais do export Garmin importado | **parcial** | sem limiar |
| `natacao.series` | melhor 100 m (ou melhor série) por treino | detecção de séries de natação | **não existe ainda** (detecção de séries por fazer) | **não** (métrica por fazer, fica para depois) | 3% |
Limitações: **natação não tem carga** (`modalidade_sem_carga`, [[metricas/carga-treino]]), então volume e ritmo são a evolução possível. A duração da
atividade pode incluir o descanso entre séries; `duracao_s` é o tempo do cronômetro e **inclui descansos na borda** (FIT e export, conferido pelo Theo no código de ingestão): `duracao_s / distancia` **não é pace em movimento**. A série se chama **"ritmo médio com pausas"** e só vira "pace" com os segmentos de descanso filtrados.
Sem braçadas, SWOLF ou estilo: o modelo de dados não os guarda.

### Ciclismo
| id | o que o gráfico mostra | origem | precisa para existir | na API | piso |
|---|---|---|---|---|---|
| `ciclismo.velocidade.<rua\|casa>` | velocidade média de cada pedal, em duas séries: **na rua** (ar livre) e **em casa** (virtual e rolo) | `distancia_m / duracao_s`, separando pelo `subtipo` | pedal com distância e duração; o `subtipo` separa rua (ar livre) de casa (virtual e rolo) | **não** (a linha de base não usa velocidade) | 3% |
| `ciclismo.fc.<rua\|casa>` | FC média por pedal, na rua e em casa | `atividade.fc_media` | pedal com FC média | **parcial** | 4 bpm |
| `ciclismo.eficiencia` | metros por batimento no ar livre | velocidade e FC médias | pedal ao ar livre com distância, duração e FC | **não** | 3% |
| `ciclismo.esforcos` | melhor velocidade do esforço de 1 a 60 min | `bloco_atividade` (`t1` a `t60`) | pedal com esforços detectados (`esforcos@1`) | **parcial** | 3% |
| `ciclismo.volume` | km e horas por semana | soma | qualquer pedal | **não** | 10% |
| `ciclismo.carga` (previsto; hoje só `geral.ctl`) | carga por semana e CTL | `carga@2` | pedal com carga calculada | **sim**, via `/carga` | 5% |
| `ciclismo.recordes` | melhor 40 km, maior distância, potência média de 20 min | `recorde_pessoal` | marcas pessoais do export Garmin importado | **parcial** | sem limiar |
Limitações: **sem potência, cadência nem altimetria** no modelo de dados (só o recorde de 20 min vem do Garmin): não há potência normalizada nem
eficiência por watt. A rua (ar livre) e a casa (virtual e rolo) têm física diferente: **duas séries separadas** (decisão do Angelo, 27/11).

### Transversais (todas as modalidades)
| id | o que o gráfico mostra | origem | precisa para existir | na API | limiar |
|---|---|---|---|---|---|
| `geral.volume_semana` (previsto) | horas por semana, empilhadas por modalidade | soma de `atividade` (sem pai multiesporte e sem troca, como a carga) | qualquer treino (sem pai multiesporte nem troca) | **não** | 10% |
| `geral.mistura` (previsto) | quantos treinos de cada tipo por mês (leve, longo, intervalado...) | `tipo_treino` | treinos com tipo | **parcial** | sem limiar |
| `geral.carga` (previsto; no código é `geral.ctl`, só o CTL) | CTL, ATL e TSB em 6 meses ou 1 ano | `serie_carga@2` | treinos com carga calculada; natação não tem carga | **sim** | 5% / 10% |
| `geral.recuperacao.<medida>` (previsto) | sono, VFC e FC de repouso por noite, com a faixa do normal | `recuperacao_dia` ([[metricas/recuperacao]]) | dados de saúde importados (sono, VFC, FC de repouso); depende de o relógio medir | **parcial** (`noites_do_atleta`, sem rota) | `z` 2,0 |
| `geral.calor` (previsto, sem id no código) | pace e FC dos treinos leves, com os dias quentes **marcados** | `clima_atividade` (temperatura e sensação) | treino ao ar livre com clima consultado | **parcial** | ver abaixo |
| `geral.carga_garmin` (previsto) | carga aguda e crônica do relógio | `carga_garmin_dia` | carga do relógio importada do export Garmin | **parcial** | **não recomendada** (duas curvas de carga confundem; serve só à [[metricas/conferencia-carga]]) |

**O que fica de fora, e por quê:** pace **ajustado** por subida (não há altimetria gravada: precisaria reler os FIT, e não está no modelo,
mudança que só o Theo aprova, ADR); pace ajustado por **calor** (os modelos publicados usam WBGT, que o clima não entrega; por isso só
**marcamos** o treino quente, sem corrigir); desacoplamento aeróbico (precisa de séries por segundo, que não guardamos; com voltas daria uma
aproximação em treinos contínuos longos, **fase 2**); transição (brick) não é evolução, entra como contexto no treino.

## Fórmulas novas

**Metros por batimento (`eficiencia@1`):** `EF = (distancia_m / (duracao_s / 60)) / fc_media`, em m por batimento. Exemplo à mão: 10 000 m em
3 300 s (55 min) com FC média 150 → 10 000 / 55 = 181,82 m/min; 181,82 / 150 = **1,212 m/bat**. Equivale ao "fator de eficiência" de
Friel (velocidade sobre FC, TrainingPeaks); lá a corrida usa o pace ajustado ao relevo, aqui **sem ajuste** (limitação). Piso de 3%, escolha
nossa. Só em treinos leve, moderado e longo, com FC e sem esteira (ritmo e FC de tiros misturam esforço e pausa).

**Volume semanal:** soma de `distancia_m` (e `duracao_s`) por semana ISO local (segunda a domingo), semanas sem treino valem 0. Frase: mediana das
4 semanas de `R` contra a das 4 de `A` (ver "Frase de volume").

## Frases por série

Os números vêm da conta; o app só mostra o texto. Nenhuma frase usa sigla, adjetivo de valor ou conselho.

1. **Pace por tipo / melhor esforço / tiros** (regra geral). "Pace dos seus treinos leves nas últimas 4 semanas: 5:42/km (mediana de 3 treinos),
   12 s/km mais rápido que nas 4 semanas anteriores (5:54/km, 3 treinos)." Natação: mesma frase, "/100 m".
2. **FC por tipo.** "Frequência cardíaca dos seus treinos leves nas últimas 4 semanas: 150 bpm, parecida com a das 4 semanas anteriores (148 bpm)."
3. **Metros por batimento.** "Nas últimas 4 semanas você percorreu 1,21 m por batimento nos treinos leves, 3% mais que nas 4 semanas anteriores (1,17 m)."
   Direção: "mais" ou "menos", nunca "mais eficiente". Se a FC subiu e o pace subiu junto, a frase só descreve os dois números.
4. **Volume.** Janela `R` = 4 semanas completas até domingo passado (semana em curso fora). `d = mediana(R) - mediana(A)`, `L = 10% de mediana(A)`.
   Exemplo à mão: `R` = 30, 36, 24, 30 km (mediana 30); `A` = 40, 36, 44, 40 (mediana 40); `d = -10`, `L = 4` → "Nas últimas 4 semanas
   você correu 30 km por semana (mediana), 10 km a menos (25%) que nas 4 anteriores (40 km)." `A` com mediana menor que 3 km: sem percentual.
5. **Carga e CTL** (período longo). Compara o CTL de ontem com o de 28 dias antes: `limiar = max(2, 0,05 x CTL28)` (a mesma escala da `frase_forma@1`, que
   usa 14 dias). "Seu condicionamento está em 42, estável em relação a 4 semanas atrás (41). O maior valor do período foi 47, em 14/09."
   Dia `aprendendo` em qualquer ponta: sem tendência, só o valor. A frase da forma da quinzena (`frase_forma@1`) segue como está.
6. **Recordes e limiar.** Sem comparação de janela (os pontos são raros): "Seu melhor 5 km no relógio é 21:10, de 12/05 (há 6 meses). Foram 4 recordes
   nesta distância nos últimos 2 anos." Zero recorde: "Ainda sem recorde de 5 km no seu relógio." Limiar: "Seu limiar de FC estimado pelo relógio é 168 bpm
   desde 02/10; era 165 bpm em 20/06." Fonte sempre dita (Garmin); não é medida nossa.
7. **Recuperação** (`geral.recuperacao.*`). Compara a mediana das **14 últimas noites** (mínimo 10 com valor) com o normal das **28 anteriores a elas**
   (mínimo 14, mesma conta da `recuperacao@1`: mediana, `desvio = max(1,4826 x MAD; 0,05 x |mediana|)`, `z = (mR - mA)/desvio`, `|z| >= 2,0` fora).
   "Nas últimas 2 semanas sua variabilidade da frequência cardíaca (VFC) mediana foi 44 ms, abaixo do seu normal (50 ms nas 4 semanas antes)."
   Abaixo ou acima é direção, nunca bom ou ruim. Poucas noites: só "Poucas noites com este dado."
8. **Calor.** Marca, nos gráficos de pace e FC dos treinos leves, o treino com sensação térmica de 28 °C ou mais (corte decidido pelo Angelo, 27/11).
   Frase só quando há 3 ou mais treinos quentes e 3 ou mais não quentes na janela de 12 semanas: "Nos 5 treinos leves com 28 °C ou mais, o pace foi 14 s/km mais
   lento que nos 11 sem calor (mediana)." Descreve, não corrige nem explica. A mesma regra de piso e mínimo.
9. **Mistura de tipos.** Sem frase de tendência: "Nas últimas 4 semanas: 6 treinos leves, 2 intervalados e 1 longo." (contagem).

## Quando a série aparece
O catálogo da API traz, por atleta e por série: `id`, `titulo`, `modalidade`, `n_pontos` e `disponivel`. Regra: ao menos 8 pontos nas últimas
12 semanas (o mesmo mínimo da linha de base) **ou** 3 em cada janela da frase. Senão o app mostra a série cinza com o motivo ("Poucos treinos de tiros
nas últimas 12 semanas"), nunca uma tela vazia. O atleta de uma modalidade só vê as séries dela. Série padrão ao abrir: a do último treino.

## Contrato sugerido (a decidir pelo Theo e pela Duda)
`GET /atletas/{id}/evolucao/series` (catálogo) e `GET /atletas/{id}/evolucao/series/{serie_id}?periodo=12s|6m|1a` com `pontos` (data, valor, texto pronto),
`referencia` (faixa do normal, quando existir), `eixos` (como os de hoje), `frase` (`versao`, `texto`, `tendencia`) e `marcas` (calor, recorde).
A rota `/evolucao/tiros-1km` continua. Cada série nova vem com sua `versao_calculo` e teste à mão, como as demais métricas.

## Cartões candidatos do início (valor para o atleta e custo)
Valor A/M/B para o atleta; custo P (pequeno, só rota ou arranjo), M (métrica nova simples), G (depende de dado raro ou métrica nova). Todos em
texto pronto da API, sem número calculado no app.

| # | cartão | dado | na API? | valor | custo |
|---|---|---|---|---|---|
| 1 | **Esta semana**: treinos feitos, km e horas, contra a semana anterior | `atividade` (soma por semana) | não (a rota de volume resolve) | A | P |
| 2 | **Hoje na sua semana** ("quinta: corrida moderada"), a rotina do próprio atleta, sem conselho | `semana_padrao` | **sim** (`/semana-padrao`) | A | P |
| 3 | **Volume das 4 semanas** com 4 barras semanais e a frase | `geral.volume_semana` | não | A | P |
| 4 | **Em movimento**: a série que mais mudou nas 4 semanas (maior `|d| / L` entre as disponíveis, mínimo 1,0) e sua frase | catálogo de séries | não | A | M |
| 5 | **Melhor marca recente**: "Melhor 5 km: 21:10, em 12/05" ou "Novo recorde em 3 dias" | `recorde_pessoal` | parcial | M | P |
| 6 | **Recuperação da noite**: sono, VFC e FC de repouso contra o normal | `recuperacao@1` | parcial (existe por treino; falta "última noite") | M | M |
| 7 | **Mistura das 4 semanas** (leve, longo, intervalado) em contagem | `tipo_treino` | parcial | M | P |
| 8 | **Condicionamento (CTL) em 6 meses**, com a frase de período | `serie_carga@2` | sim (falta o recorte longo na tela) | M | P |
| 9 | **Limiar atual** do relógio | `limiar_atleta` | parcial | B | P |

Já existem no início: último treino, check-in e a quinzena de forma. **Decisão do Angelo (27/11): até 5 cartões no início**, sem personalizar por
enquanto (esconder cartões só depois do piloto). Conjunto proposto: **1, 2, 3, 4 e 5**. O cartão da noite (6) fica para depois; se entrar, depende da
importação de saúde de cada atleta e só aparece com dado. **Regularidade (semanas seguidas) não entra**, para não virar cobrança. Os cartões 7 a 9 ficam
como reserva, fora do limite de 5.

## Decisões do Angelo (27/11, "ok em tudo")
1. Ciclismo em casa (virtual, rolo) e na rua (ar livre): séries separadas.
2. O gráfico abre em 12 semanas, com 6 meses e 1 ano como opção; a frase compara sempre 4 semanas com as 4 anteriores.
3. Cartão "Hoje na sua semana" (rotina que o atleta cadastrou, sem sugerir treino): sim.
4. Treino "quente": sensação térmica de 28 °C ou mais.
5. Cartão de regularidade: não entra.
6. Natação e ciclismo evoluem por ritmo, volume e FC por enquanto.
7. Início sem personalização agora; a Evolução lembra a última série escolhida; até 5 cartões, "Noite" depois.

## Limitações e quando não usar
- Quantos atletas terão cada série depende do que cada um importa (FIT, export Garmin, saúde) e de ter treinos tipados; a API diz por atleta se a série está disponível.
- Todos os pisos, janelas (28 dias, 14 noites, 28 °C) e mínimos acima são **escolha nossa**, sem artigo e sem calibração; mudar um sobe `frase_evolucao@2`.
- Pace e velocidade **sem ajuste** de relevo, vento ou calor: a frase descreve a diferença, não a causa. Treino de tipo errado (tipo sugerido não confirmado) entra com o tipo
  que tem; o aviso de tipo da linha de base continua valendo.
- Pontos da carga e do pace dependem de a ingestão estar em dia; a API avisa os treinos pendentes como na `frase_forma`.
- Fontes: mediana e MAD (Leys et al., 2013; citação ainda a conferir, ADR 0011); fator de eficiência (Friel, TrainingPeaks); CTL (Banister et al., 1976).
  Resto: regra própria do projeto.

## Referência
Mediana e MAD: Leys et al. (2013), J. Exp. Soc. Psychol. 49(4):764-766 (citação ainda a conferir, ADR 0011). Fator de eficiência: Friel, TrainingPeaks. CTL: Banister et al. (1976). Pisos, janelas e mínimos: regra própria do projeto, sem artigo.

## Código e teste
- **Frase (`frase_evolucao@1`), implementada:** `services/api/app/servicos/frase_evolucao.py`, função pura (sem banco, rede ou IA), no espírito da `frase_forma`.
  Teste: `services/api/tests/servicos/test_frase_evolucao.py` (um por ramo e os exemplos à mão desta nota).
- **Assinatura:** `frase_evolucao(tipo, pontos, hoje, titulo=None, minimo=None) -> FraseEvolucao`. `pontos` = lista de `Ponto(dia, valor, aprendendo=False)`;
  `hoje` = data local do atleta; `tipo` ∈ `pace_km`, `pace_100m`, `fc`, `eficiencia`, `velocidade`, `volume_km`, `volume_h`, `volume_m`, `ctl`.
  Devolve `versao`, `tipo` (`comparada`, `poucos`, `sem_treino`, `so_valor`, `sem_dado`), `mudanca` (`maior`/`menor`/`parecido` do valor), `a_favor`
  (a mudança foi no sentido do "melhor" da série, só para cor ou ícone neutros, nunca no texto), `texto`, `valor_atual`, `valor_anterior`, `n_atual`, `n_anterior`.
- **Decisões de código:** as regras decidem sobre os valores **mostrados** (arredondados, meio para cima), como a `frase_forma`; o limite entra como diferença.
  Ponto sem valor (`None` ou não finito) fica fora da conta e vira aviso a partir de 20% dos treinos de `R`. Volume soma os treinos por semana ISO e a semana
  sem treino vale 0; no próprio domingo a semana ainda não conta. Eficiência mostra a diferença em %; o resto na unidade da série. Sentido do "melhor":
  pace, ritmo e FC menor; eficiência, velocidade, volume e condicionamento maior (escolha nossa, só para `a_favor`).
- **Ainda sem frase em código:** recordes e limiar, recuperação, calor e mistura de tipos (itens 6 a 9 de "Frases por série").
- Versão e limiares: mudar um texto, piso, janela ou mínimo sobe `frase_evolucao@2`.
