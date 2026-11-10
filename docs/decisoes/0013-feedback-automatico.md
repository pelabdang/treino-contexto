---
tipo: decisao
status: proposta
dono: caio
atualizado: 2026-11-10
links: [[decisoes/0004-contrato-tela-evolucao]], [[decisoes/0007-clima-da-atividade]], [[decisoes/0008-deteccao-de-esforcos]], [[decisoes/0010-carga-de-treino]], [[decisoes/0011-linha-de-base-e-semana-padrao]], [[decisoes/0012-check-in-pos-treino]], [[metricas/linha-base]], [[metricas/carga-treino]], [[metricas/carga-pse]], [[metricas/esforcos]], [[modulos/banco]], [[modulos/api]], [[modulos/worker]], [[produto/roadmap]], [[produto/plano-mvp-execucao]], [[glossario]]
---
# ADR: 0013 Feedback automático por treino (pacote de fatos, guarda, camada de LLM, checagens)

> **Proposta** (issue #322). **Modelo de dados aprovado pelo Theo em 10/11** (PR #340; item 2, com a ordem da fila do worker). Falta: a revisão da Duda na camada de LLM (item 3) e a leitura
> dos **6 exemplos de tom** pelo Angelo, com as respostas dele aos itens 1, 2 e 9 de "A confirmar", na seção "Exemplos sintéticos de feedback" logo abaixo, **antes** de qualquer código do feedback (#327).
> **Nenhuma linha de código nem migração muda neste PR.** Todos os números, textos e exemplos são **sintéticos**. Check-in e feedback são
> dado pessoal e de saúde: nada de check-in, pacote de fatos ou texto de feedback real no repositório, em log ou em captura.
> Fecha também, para a spec do cartão (PR #338, #329), a forma do campo `feedback`, quando o feedback é gerado e se existe "sem feedback possível" (item 2).
> Dá base para #323 (fixtures e oráculo), #324 (`fatos_treino@1`), #325 (checagens), #326 (camada de LLM), #327 (banco, migração 0013 e
> `worker.gerar_feedback`), #328 (API), #329 e #330 (cartão no app).

## Contexto
Na Meta 8 o atleta passou a registrar o treino em 3 toques ([[decisoes/0012-check-in-pos-treino]]). A Meta 9 devolve a ele, **depois do
check-in**, um texto de **3 a 5 linhas** sobre o treino: como foi em relação ao normal dele naquele tipo de treino e o que o check-in e o
contexto (clima, carga) mostram. É a camada 4 do [[produto/plano-mvp-execucao]] (seção 4.4) e a primeira linha da cadência da seção 4.6.

Princípio que organiza tudo: **quem calcula é o código; a IA só redige.** O modelo de linguagem recebe um **pacote de fatos** já pronto
(`fatos_treino@1`), escreve o texto, e um conjunto de **checagens em código** decide se o texto pode chegar ao atleta. Na dúvida, não há
feedback: nunca um texto de reserva escrito por regra.

### Decisões do Angelo (10/11, "ok para as oito"), que esta ADR respeita
1. Abrir as issues e começar a Meta 9.
2. **Ao provedor de LLM vai só o pacote de fatos** (números, unidades, estados e rótulos do tipo, do clima e da carga; PSE, sensação e os
   atalhos marcados). **Nunca** o texto livre da observação, nome, data real, posição ou qualquer identificador. Nada disso em log.
3. Na Meta 9 **só fixtures sintéticas** vão ao provedor de verdade, numa rodada pequena e local. Feedback dos treinos reais do Angelo só com
   um "sim" explícito dele. **O "sim" veio no mesmo dia (10/11, decisão 9 abaixo).**
4. **Só o plano gratuito** do provedor atual (Groq), sem cartão, com **limite de chamadas por execução** do `worker.gerar_feedback`.
5. **Feedback só depois do check-in.** Sem check-in: "Faça o check-in para ver o feedback". Editar o check-in deixa o feedback
   desatualizado e ele é refeito.
6. **Tom:** quem fala é o app, **sem o nome do professor** até a Meta 10; frases curtas, em segunda pessoa, sem diagnóstico, culpa,
   promessa nem causa afirmada. **Esclarecimento do Angelo:** o feedback é **texto escrito**, sem áudio. Ele lê os exemplos sintéticos desta ADR
   antes do código.
7. **Atalho "dor":** só uma frase neutra ("Você registrou dor neste treino."), sem conselho.
8. **Texto reprovado** nas checagens: sem feedback naquele treino, com o motivo na API, e nova tentativa no próximo `worker.gerar_feedback`.
   Nenhum texto de reserva escrito por regra.
9. **"Sim" explícito (10/11, depois do "ok para as oito")** para gerar o feedback dos **treinos reais** dele no provedor de LLM, com estes limites, que valem
   como regra: (a) **só localmente** (a máquina dele, nunca CI nem servidor); (b) ao provedor vai **só o pacote de fatos** (nunca o texto livre da observação, nome,
   data real, posição ou identificador); (c) **nada do pacote nem do texto gerado no repositório ou em log**: o texto real vive só no banco local; (d) **plano gratuito do Groq**,
   com limite de chamadas por execução. Os **exemplos desta ADR e as fixtures continuam sintéticos**; testes e CI seguem só com o provedor falso.

### O que o código do `main` mostra (conferido em 10/11, commit `03b7797`)
- A próxima migração é a **`0013`** (a última é a `0012_checkin_treino`).
- `CheckinTreino` (ADR 0012) já existe, com `UNIQUE (atividade_id)`, `atualizado_em` definido pela aplicação a cada `PUT` e `versao = checkin@1`.
  `Atividade.fc_media`, `distancia_m`, `duracao_s`, `tipo_treino` e `subtipo` estão no banco.
- Já são calculados por código: `linha_base@2` (`app/metricas/linha_base.py`, janela de 12 semanas, mínimo de 8 treinos, `fora` com |z| >= 2,5;
  textos prontos em `app/servicos/linha_base_leitura.py`), `carga@2`, `carga_pse@1`, `esforcos@1`, `tiros_1km@6`, clima (`clima_atividade`,
  estados `ok`, `pendente`, `falha`; `indoor` e `sem_posicao` na leitura) e `tipo_treino@1`.
- **Não existe** no código: pace ajustado por calor ou subida, estimativa de quanto cada fator pesa (motor de explicação, passo 3 da seção 4.3),
  sono, HRV, FC de repouso, séries de natação. Nada disso entra no pacote (ver "Fora desta ADR").
- `AGENTS.md` já fixa: IA do produto só por camada trocável (LiteLLM), `LLM_PROVIDER` e `LLM_MODEL` do `.env`, padrão Groq, nunca provedor direto
  no código. O `.env.example` já traz as duas variáveis (`LLM_MODEL` vazio).
- **Uma frase da ADR 0012 muda** (item 5.3): o check-in "não entra no pacote de fatos do feedback nesta meta". Era a regra da Meta 8; a decisão 2
  do Angelo a substitui: entram PSE, sensação e atalhos marcados, **nunca o texto livre**. Este PR acrescenta uma nota na ADR 0012.

## Exemplos sintéticos de feedback (para o Angelo ler o tom)
Todos inventados. Em cada um: o **pacote de fatos** (só os campos que mudam a conversa; campos nulos e blocos vazios ficam de fora, e
as métricas de linha de base aparecem em uma linha) e o **texto esperado**. O campo de cada número está explicado no item 1 da "Decisão".
Cada número do texto é um dos `*_texto` ou valores do pacote, copiado sem conta nova.

### Exemplo 1: corrida leve, dentro do normal
```json
{"versao": "fatos_treino@1",
 "treino": {"modalidade": "corrida", "tipo_treino": "leve", "duracao_s": 2820, "duracao_texto": "47 min", "distancia_m": 8200, "distancia_texto": "8,20 km", "fc_media_bpm": 146},
 "linha_base": {"versao": "linha_base@2", "estado": "ok", "janela_semanas": 12, "minimo_treinos": 8, "metricas": [
   {"chave": "pace_medio", "estado": "dentro", "valor_texto": "5:44/km", "mediana_texto": "5:48/km", "n": 11},
   {"chave": "fc_media", "estado": "dentro", "valor_texto": "146 bpm", "mediana_texto": "148 bpm", "n": 11},
   {"chave": "carga_hora", "estado": "dentro", "valor_texto": "49,1 pontos/h", "mediana_texto": "50,3 pontos/h", "n": 11}]},
 "clima": {"estado": "ok", "temperatura_c": 19, "sensacao_termica_c": 19, "umidade_pct": 62, "vento_kmh": 9},
 "carga": {"versao": "carga@2", "estado": "calculada", "valor": 38.5, "valor_texto": "38,5 pontos", "metodo": "rtss"},
 "carga_pse": {"versao": "carga_pse@1", "estado": "calculada", "valor": 188, "valor_texto": "188 UA"},
 "checkin": {"pse": 4, "pse_texto": "um pouco difícil", "sensacao_nivel": 4, "sensacao_texto": "bem", "nada_a_relatar": true, "atalhos": []}}
```
**Texto esperado**
> Seu pace médio foi 5:44/km, perto da mediana de 5:48/km nos 11 treinos leves das últimas 12 semanas.
> A FC média foi 146 bpm e a carga por hora, 49,1 pontos/h: ambas dentro do seu normal.
> Você marcou esforço 4 (um pouco difícil), sensação 4 (bem) e nada a relatar.
> Foram 47 min a 19 °C, com carga pela PSE de 188 UA.

### Exemplo 2: intervalado fora da linha de base
```json
{"versao": "fatos_treino@1",
 "treino": {"modalidade": "corrida", "tipo_treino": "intervalado", "duracao_s": 3120, "duracao_texto": "52 min", "distancia_m": 9500, "distancia_texto": "9,50 km", "fc_media_bpm": 158},
 "linha_base": {"versao": "linha_base@2", "estado": "ok", "janela_semanas": 12, "minimo_treinos": 8, "metricas": [
   {"chave": "melhor_pace", "estado": "fora", "valor_texto": "4:22/km", "mediana_texto": "4:09/km", "diferenca_texto": "13 s/km mais lento", "n": 10},
   {"chave": "fc_melhor_tiro", "estado": "dentro", "valor_texto": "171 bpm", "mediana_texto": "172 bpm", "n": 10},
   {"chave": "fc_media", "estado": "dentro", "valor_texto": "158 bpm", "mediana_texto": "157 bpm", "n": 10}]},
 "esforcos": {"versao": "esforcos@1", "treino_chave": false, "series": [{"faixa_rotulo": "1 km", "quantidade": 5}]},
 "clima": {"estado": "ok", "temperatura_c": 22, "sensacao_termica_c": 23, "umidade_pct": 55, "vento_kmh": 12},
 "carga": {"versao": "carga@2", "estado": "calculada", "valor": 61.3, "valor_texto": "61,3 pontos", "metodo": "rtss"},
 "carga_pse": {"versao": "carga_pse@1", "estado": "calculada", "valor": 416, "valor_texto": "416 UA"},
 "checkin": {"pse": 8, "pse_texto": "8", "sensacao_nivel": 3, "sensacao_texto": "normal", "nada_a_relatar": true, "atalhos": []}}
```
**Texto esperado**
> Seu melhor tiro foi 4:22/km, 13 s/km mais lento que a mediana de 4:09/km nos 10 treinos intervalados das últimas 12 semanas.
> É uma comparação com o seu histórico, não um julgamento do treino.
> A FC do melhor tiro foi 171 bpm, dentro do seu normal (mediana de 172 bpm).
> Você registrou esforço 8 e sensação 3 (normal), sem nada a relatar.
> Foram 5 tiros de 1 km e 416 UA de carga pela PSE.

### Exemplo 3: linha de base "aprendendo"
```json
{"versao": "fatos_treino@1",
 "treino": {"modalidade": "corrida", "tipo_treino": "moderado", "duracao_s": 2400, "duracao_texto": "40 min", "distancia_m": 7000, "distancia_texto": "7,00 km", "fc_media_bpm": 152},
 "linha_base": {"versao": "linha_base@2", "estado": "ok", "janela_semanas": 12, "minimo_treinos": 8, "metricas": [
   {"chave": "pace_medio", "estado": "aprendendo", "valor_texto": "5:43/km", "n": 3},
   {"chave": "fc_media", "estado": "aprendendo", "valor_texto": "152 bpm", "n": 3},
   {"chave": "carga_hora", "estado": "aprendendo", "valor_texto": "52,2 pontos/h", "n": 3}]},
 "clima": {"estado": "ok", "temperatura_c": 24, "sensacao_termica_c": 25, "umidade_pct": 60, "vento_kmh": 7},
 "carga": {"versao": "carga@2", "estado": "calculada", "valor": 34.8, "valor_texto": "34,8 pontos", "metodo": "hrtss"},
 "carga_pse": {"versao": "carga_pse@1", "estado": "calculada", "valor": 240, "valor_texto": "240 UA"},
 "checkin": {"pse": 6, "pse_texto": "6", "sensacao_nivel": 4, "sensacao_texto": "bem", "nada_a_relatar": false, "atalhos": ["sono_ruim"]}}
```
**Texto esperado**
> Ainda aprendendo o seu normal em treino moderado: 3 de 8 treinos nas últimas 12 semanas.
> Sem comparação com o seu histórico por enquanto.
> Seu pace médio foi 5:43/km e a FC média, 152 bpm.
> Você marcou esforço 6, sensação 4 (bem) e sono ruim.
> A carga pela PSE foi 240 UA em 40 min.

### Exemplo 4: com calor
```json
{"versao": "fatos_treino@1",
 "treino": {"modalidade": "corrida", "tipo_treino": "longo", "duracao_s": 5400, "duracao_texto": "90 min", "distancia_m": 15000, "distancia_texto": "15,00 km", "fc_media_bpm": 158},
 "linha_base": {"versao": "linha_base@2", "estado": "ok", "janela_semanas": 12, "minimo_treinos": 8, "metricas": [
   {"chave": "pace_medio", "estado": "fora", "valor_texto": "6:00/km", "mediana_texto": "5:42/km", "diferenca_texto": "18 s/km mais lento", "n": 9},
   {"chave": "fc_media", "estado": "fora", "valor_texto": "158 bpm", "mediana_texto": "150 bpm", "diferenca_texto": "8 bpm acima", "n": 9},
   {"chave": "carga_hora", "estado": "dentro", "valor_texto": "62,0 pontos/h", "mediana_texto": "60,5 pontos/h", "n": 9}]},
 "clima": {"estado": "ok", "temperatura_c": 33, "sensacao_termica_c": 37, "umidade_pct": 58, "vento_kmh": 6},
 "carga": {"versao": "carga@2", "estado": "calculada", "valor": 93.0, "valor_texto": "93,0 pontos", "metodo": "rtss"},
 "carga_pse": {"versao": "carga_pse@1", "estado": "calculada", "valor": 630, "valor_texto": "630 UA"},
 "checkin": {"pse": 7, "pse_texto": "muito difícil", "sensacao_nivel": 2, "sensacao_texto": "mal", "nada_a_relatar": false, "atalhos": ["calor", "cansaco"]}}
```
**Texto esperado**
> Seu pace médio foi 6:00/km, 18 s/km mais lento que a mediana de 5:42/km nos 9 treinos longos das últimas 12 semanas.
> A FC média foi 158 bpm, 8 bpm acima da mediana de 150 bpm.
> O clima registrado foi 33 °C, com sensação térmica de 37 °C e umidade de 58%.
> Você marcou calor e cansaço, esforço 7 (muito difícil) e sensação 2 (mal).
> A carga pela PSE foi 630 UA em 90 min.

Aqui o texto põe o clima e o check-in **ao lado** da comparação e **não liga** um ao outro: nada de "por causa do calor". É a regra da decisão 6.
Não há "observação positiva" porque nenhum fato do pacote a sustenta (ver "A confirmar", item 1).

### Exemplo 5: com o atalho "dor"
```json
{"versao": "fatos_treino@1",
 "treino": {"modalidade": "corrida", "tipo_treino": "leve", "duracao_s": 1800, "duracao_texto": "30 min", "distancia_m": 5000, "distancia_texto": "5,00 km", "fc_media_bpm": 139},
 "linha_base": {"versao": "linha_base@2", "estado": "ok", "janela_semanas": 12, "minimo_treinos": 8, "metricas": [
   {"chave": "pace_medio", "estado": "dentro", "valor_texto": "6:00/km", "mediana_texto": "5:56/km", "n": 10},
   {"chave": "fc_media", "estado": "dentro", "valor_texto": "139 bpm", "mediana_texto": "141 bpm", "n": 10}]},
 "clima": {"estado": "ok", "temperatura_c": 21, "sensacao_termica_c": 21, "umidade_pct": 50, "vento_kmh": 8},
 "carga_pse": {"versao": "carga_pse@1", "estado": "calculada", "valor": 90, "valor_texto": "90 UA"},
 "checkin": {"pse": 3, "pse_texto": "moderado", "sensacao_nivel": 3, "sensacao_texto": "normal", "nada_a_relatar": false, "atalhos": ["dor"]}}
```
(O check-in sintético tinha também um texto livre; ele **não aparece** no pacote, por construção.)

**Texto esperado**
> Seu pace médio foi 6:00/km, perto da mediana de 5:56/km nos 10 treinos leves das últimas 12 semanas.
> A FC média foi 139 bpm, dentro do seu normal.
> Você registrou dor neste treino.
> Esforço 3 (moderado) e sensação 3 (normal); a carga pela PSE foi 90 UA em 30 min.

Uma só frase sobre a dor, sempre esta, sem conselho, sem parte do corpo, sem elogio em volta (decisão 7).

### Exemplo 6: natação, sem tipo de treino
```json
{"versao": "fatos_treino@1",
 "treino": {"modalidade": "natacao", "tipo_treino": null, "duracao_s": 2400, "duracao_texto": "40 min", "distancia_m": 1600, "distancia_texto": "1.600 m", "fc_media_bpm": 128},
 "linha_base": {"versao": "linha_base@2", "estado": "sem_linha_base", "motivo": "sem_tipo", "metricas": []},
 "carga": {"versao": "carga@2", "estado": "sem_carga", "motivo": "modalidade_sem_carga"},
 "carga_pse": {"versao": "carga_pse@1", "estado": "calculada", "valor": 200, "valor_texto": "200 UA"},
 "checkin": {"pse": 5, "pse_texto": "difícil", "sensacao_nivel": 4, "sensacao_texto": "bem", "nada_a_relatar": true, "atalhos": []}}
```
**Texto esperado**
> Natação de 1.600 m em 40 min, com FC média de 128 bpm.
> Sem comparação com o seu histórico: o treino não tem tipo.
> A natação não tem carga do relógio; a carga pela PSE foi 200 UA.
> Você marcou esforço 5 (difícil), sensação 4 (bem) e nada a relatar.

## Decisão

### 1. Pacote de fatos `fatos_treino@1`
**O que é.** Um objeto JSON, **montado por uma função pura** (`app/explicacao/fatos_treino.py`, #324; sem banco, sem rede, sem IA) a partir do que o código
já calculou. É a **única** coisa que o provedor de LLM recebe sobre o treino. **Só números que o código já calcula**: o pacote não inventa número,
não faz conta nova e **não afirma causa**; põe os fatos lado a lado. Cada número vem em duas formas: o **valor** (para máquina) e o **texto
pronto** (`*_texto`, com as mesmas funções de formatação que a API já usa, p. ex. `formatar_pace`, `distancia_da_atividade`). O modelo de linguagem copia
os textos prontos; a checagem de números (item 4) compara contra eles.

**Nunca entra no pacote** (testado por oráculo, #323 e #324): o **texto livre** da observação do check-in (nem o fato de existir); nome do atleta;
`atleta_id`, `atividade_id` ou qualquer identificador; **data ou hora real** (só durações); posição (`inicio_lat`, `inicio_lon`) ou nome de lugar; nome de arquivo;
nome do professor; qualquer coisa fora desta lista de campos.

**Campos e de onde vêm.** Chaves sempre presentes, na ordem abaixo (ausente = `null`, nunca omitida); unidades no nome do campo ou em `*_texto`.

| Bloco e campo | Tipo e unidade | Origem |
|---|---|---|
| `versao` | texto, `fatos_treino@1` | constante; sobe quando muda um campo, uma unidade, um estado ou o que fica de fora (ver "Versão") |
| `treino.modalidade` | `corrida`, `natacao`, `ciclismo`, `outra` | `atividade.modalidade` |
| `treino.tipo_treino` | `intervalado`, `leve`, `longo`, `moderado`, `fartlek` ou `null` | `atividade.tipo_treino` (`tipo_treino@1`, semana-padrão ou confirmado). A **origem** do tipo não entra |
| `treino.parte_de_transicao` | booleano | rótulo de transição (ADR 0009); a linha de base da parte de transição é própria (`linha_base@2`) |
| `treino.ambiente` | `esteira` ou `null` | `atividade.subtipo = esteira`; os demais subtipos ficam de fora |
| `treino.duracao_s`, `duracao_texto` | s; "47 min" | `atividade.duracao_s` (cronômetro, ADR 0012 item 6) |
| `treino.distancia_m`, `distancia_texto` | m; "8,20 km" ou "1.600 m" | `atividade.distancia_m`; texto de `distancia_da_atividade` |
| `treino.fc_media_bpm` | bpm, inteiro | `atividade.fc_media` |
| `linha_base.versao`, `estado`, `motivo` | `linha_base@2`; `ok` ou `sem_linha_base`; motivo (`multiesporte`, `modalidade_sem_metricas`, `sem_tipo`, `divergente`) | `app/metricas/linha_base.py` |
| `linha_base.janela_semanas`, `minimo_treinos` | 12; 8 | `Parametros` da `linha_base@2` |
| `linha_base.metricas[]` | uma por métrica do tipo | `linha_base@2` (as chaves e unidades da ADR 0011, item 7) |
| `...metricas[].chave` | `pace_medio`, `melhor_pace`, `fc_media`, `fc_melhor_tiro`, `carga_hora` | idem |
| `...metricas[].estado` | `fora`, `dentro`, `aprendendo`, `sem_valor` | idem |
| `...metricas[].valor_texto`, `mediana_texto` | "5:44/km", "146 bpm", "49,1 pontos/h" | os mesmos textos que `linha_base_leitura.py` já monta para a API |
| `...metricas[].diferenca_texto` | "12 s/km mais lento"; só em `fora` | idem |
| `...metricas[].n` | treinos da janela com a métrica | idem |
| `...metricas[].motivo` | só em `sem_valor` (`esteira`, `sem_tiros`, `sem_fc`...) | idem |
| `esforcos.versao`, `treino_chave` | `esforcos@1`; booleano | `app/metricas/esforcos.py`, `tiros_1km@6` |
| `esforcos.series[]` | `faixa_rotulo` ("1 km", "4 min") e `quantidade` | contagem dos esforços por faixa (ADR 0008); sem pace por esforço nesta versão |
| `clima.estado` | `ok`, `pendente`, `falha`, `indoor`, `sem_posicao` | ADR 0007 |
| `clima.temperatura_c`, `sensacao_termica_c`, `umidade_pct`, `vento_kmh` | graus C, graus C, %, km/h; só em `ok` | `clima_atividade`; fonte, atribuição e posição **não** entram |
| `carga.versao`, `estado`, `valor`, `valor_texto`, `metodo`, `motivo` | `carga@2`; `calculada`, `sem_carga` ou `pendente`; pontos; `rtss`/`hrtss`; motivo da ADR 0010 | `carga_atividade` (pela mesma leitura da API) |
| `carga_pse.versao`, `estado`, `valor`, `valor_texto` | `carga_pse@1`; `calculada`, `sem_duracao`; UA | `app/metricas/carga_pse.py`, calculada na leitura. **Nunca comparada nem somada** com a `carga@2` (escalas diferentes) |
| `checkin.pse`, `pse_texto` | 0 a 10; âncora da CR-10 ou o número | `checkin_treino.pse` |
| `checkin.sensacao_nivel`, `sensacao_texto` | 1 a 5; "muito mal" a "muito bem" | `checkin_treino.sensacao` (nome do campo muda para não confundir com a sensação térmica do clima) |
| `checkin.nada_a_relatar` | booleano | `checkin_treino.nada_a_relatar` |
| `checkin.atalhos[]` | subconjunto de `dor`, `cansaco`, `sono_ruim`, `calor`, `trabalho_estresse` | `checkin_treino`; **só as chaves**, nunca o texto livre |

**Estados do pacote.** Todo bloco diz o seu estado (`sem_linha_base`, `aprendendo`, `sem_carga`, `pendente`, `sem_duracao`, clima `indoor`...), e o
texto pode dizer "sem" o que falta; não pode inventar o que falta. Sem check-in não há pacote (item 2): o feedback só nasce depois do check-in.
**Não elegível** (`multiesporte_pai` e `troca`, ADR 0012 item 4): sem pacote, sem feedback.

**O que o pacote não faz.** Não classifica fator como "provável" ou "possível", não estima quanto o calor ou a carga pesaram, não traz sono, HRV nem FC de
repouso, não traz pace ajustado por calor ou subida: nada disso existe no código hoje (seção 4.3, passos 2 e 3, ficam fora desta meta).
O calor aparece como **dois fatos separados** (a temperatura medida e o atalho "calor"), sem ligação entre eles.

**Versão.** `VERSAO = "fatos_treino@1"` em `app/explicacao/fatos_treino.py` (#324). **Sobe** quando mudar: um campo, uma unidade, um estado, a lista de
métricas ou o que fica de fora. Ao subir, os feedbacks gravados com a versão antiga ficam desatualizados e são refeitos (item 2). A `linha_base@2`, a
`carga@2` e as demais versões entram **dentro** do pacote (cada bloco carrega a sua); mudar uma delas muda o pacote, não a `fatos_treino`.

### 2. Onde o feedback fica guardado, quando é gerado e quando fica desatualizado
**Modelo de dados (para aprovação do Theo, antes de qualquer migração; a Duda opina).** Uma tabela nova, **`feedback_treino`**, na migração **`0013`**, **um
feedback por check-in**. Só existe linha depois do check-in. O pacote de fatos **não é gravado** (é recalculado a cada geração; guardá-lo duplicaria o check-in e
a linha de base).

| Coluna | Tipo | Observação |
|---|---|---|
| `id` | inteiro, chave | |
| `checkin_id` | FK `checkin_treino.id`, `ON DELETE CASCADE` | `UNIQUE`: **um feedback por check-in**. Apagar o check-in (ou a atividade, ou rodar `worker.apagar_checkin`) apaga o feedback **pelo banco**, sem código a lembrar. A atividade vem pelo check-in (sem `atividade_id` repetido) |
| `estado` | texto (20), `CHECK` | `pronto` ou `sem_feedback` |
| `motivo` | texto (30), anulável, `CHECK` | só em `sem_feedback`: `texto_reprovado`, `provedor_erro`, `provedor_tempo_limite`, `provedor_nao_configurado`, `limite_de_chamadas`. **Só o código**; nunca o texto reprovado nem o termo que reprovou |
| `texto` | texto, anulável | o feedback aprovado; `CHECK texto IS NULL OR length(texto) BETWEEN 1 AND 700`. **Nunca** o texto reprovado |
| `versao_fatos` | texto (20), não nulo | `fatos_treino@1`, com que pacote se gerou ou se tentou |
| `versao_prompt` | texto (40), não nulo | `feedback_prompt@1`, o prompt fixo do repositório (sem dado) |
| `versao_checagens` | texto (40), não nulo | `checagens_feedback@1` (números e linguagem proibida; item 4) |
| `provedor` | texto (40), anulável | de onde veio o texto: `groq`, `falso` (provedor falso dos testes)... o valor de `LLM_PROVIDER` no momento |
| `modelo` | texto (80), anulável | o valor de `LLM_MODEL` no momento |
| `tentativas` | inteiro, não nulo, padrão 1 | tentativas **sobre este mesmo check-in** (volta a 1 quando o check-in muda) |
| `checkin_atualizado_em` | datetime com fuso, não nulo | cópia de `checkin_treino.atualizado_em` no momento da geração: é o que mede se está desatualizado |
| `tentado_em` | datetime com fuso, não nulo | última tentativa; **definido pela aplicação** (`datetime.now(UTC)`), como no check-in |

**`CHECK` de coerência** (nome `estado_campos`, comparações explícitas, sem expressão que vire `NULL`):
`(estado = 'pronto' AND texto IS NOT NULL AND motivo IS NULL AND provedor IS NOT NULL AND modelo IS NOT NULL) OR (estado = 'sem_feedback' AND texto IS NULL AND motivo IS NOT NULL)`.

**Quando é gerado: só pelo `worker.gerar_feedback`, nunca dentro do `PUT` do check-in** (recomendação, ponto (b) da spec do cartão). Uma chamada de LLM dentro do `PUT` poria segundos e
uma falha de rede, de limite ou do provedor no caminho dos 3 toques (o check-in é "o produto" e não pode falhar por causa do texto); o `PUT` ficaria não determinístico e difícil de testar sem rede;
e o limite de chamadas por execução (decisão 4) só se controla num ponto único, o worker. **Custo aceito:** no piloto local o estado `pendente` **dura até alguém rodar o worker** (um comando:
`uv run python -m worker.gerar_feedback --atleta "<nome>"`), e o botão "Atualizar" do cartão basta, sem busca automática. Um gatilho de fundo depois do `PUT` fica para depois ("A confirmar", item 9).
Gera **só para atividade com check-in**. Entram na fila check-ins **sem linha** de feedback, linhas `sem_feedback` (nova tentativa, decisão 8) e linhas **desatualizadas**. **Ordem da fila de cada execução (Theo, 10/11):** primeiro quem
**nunca foi tentado** (sem linha, e o check-in editado, que volta a `tentativas = 1`); depois os demais **por menos `tentativas`** (empate: o mais recente primeiro). Assim um treino que sempre reprova não gasta o limite por execução dos outros.
Não há teto de tentativas.
Idempotente: rodar de novo sem mudança nova não faz nenhuma chamada.

**Quando fica desatualizado.** Quando `feedback_treino.checkin_atualizado_em <> checkin_treino.atualizado_em` (o check-in foi editado, inclusive um `PUT`
idêntico, que a ADR 0012 já trata como edição), **ou** quando `versao_fatos` difere da versão atual do código. **Não** fica desatualizado porque entrou um treino novo e
mudou a linha de base: o feedback descreve o treino **no momento em que foi gerado** (ver "Limitações"). Desatualizado = **o texto não é devolvido pela API** (ele pode contradizer o
check-in novo); a API diz `desatualizado` e o worker refaz. A refeita **substitui** a linha (o texto antigo se perde: menos dado guardado).

**Forma do campo `feedback` no `GET` da atividade** (fecha os pontos (a) e (c) da spec do cartão, PR #338; o contrato fino sai na #328, com adendo da ADR 0004 e cliente regerado).
O campo vem **só** no `GET` da atividade do próprio atleta, como o check-in (nunca em lista, série, exportação ou rota de professor). Atividade **não elegível** (`multiesporte_pai` e `troca`):
`feedback: null` (o cartão não aparece). Nos demais casos, **cinco estados**, que o app lê sem calcular nada:

| `estado` | quando | campos além de `estado` |
|---|---|---|
| `pronto` | linha `pronto` e não desatualizada | `texto` (3 a 5 linhas), `origem` |
| `sem_checkin` | a atividade não tem check-in | `mensagem` ("Faça o check-in para ver o feedback."), `checkin_aberto` (a janela de 7 dias da ADR 0012; falso = prazo vencido, sem botão) |
| `pendente` | tem check-in e ainda não há tentativa (o worker não rodou) | `mensagem` |
| `desatualizado` | o check-in foi editado ou `versao_fatos` mudou | `mensagem`; **a API não devolve o texto antigo** |
| `indisponivel` | linha `sem_feedback`, por qualquer motivo | `mensagem` e `motivo` (código fechado, só para quem cuida do app) |

- **`mensagem`**: a **frase pronta em português, escrita pela API** (como `carga_pse.texto`); o app a mostra como veio, e as frases da spec do cartão ficam só como reserva. A API pode variar a frase por `motivo`
  sem criar estado (`provedor_nao_configurado` pode dizer "O feedback automático não está ligado neste app."). Para **texto reprovado e provedor fora** (`texto_reprovado`, `provedor_erro`,
  `provedor_tempo_limite`, `limite_de_chamadas`) a frase é **a mesma**: "Ainda não foi possível gerar o feedback deste treino. Uma nova tentativa será feita mais tarde."
  O `motivo` é um **código** (nunca o texto reprovado nem o termo que reprovou) e o app **não o mostra**; vai na API porque a decisão 8 pede "o motivo na API".
- **`origem`** (só com texto): `automatico` ou `teste` (provedor falso). A API **não** devolve `provedor`, `modelo` nem `versao_fatos` (ficam no banco, para auditoria).
- **Não existe o estado "sem feedback possível"** (`sem_fatos`). Com check-in o pacote **sempre** existe e dá ao menos 3 linhas (o treino e o check-in estão nele). **Linha de base "aprendendo",
  `sem_linha_base` (sem tipo) e `sem_carga` não impedem o feedback**: viram frase no texto ("Ainda aprendendo o seu normal...", "Sem comparação..."), como nos exemplos 3 e 6. Se o modelo ou as checagens
  falharem, é `indisponivel`, como qualquer outro caso.

**Migração `0013`.** Só cria `feedback_treino` com os `CHECK` e o `UNIQUE`; não edita tabelas anteriores. O `downgrade` apaga a tabela (e os feedbacks: texto derivado, sem
cópia). Sem índice a mais: o `UNIQUE` de `checkin_id` já indexa. A gravação é um *upsert* por `checkin_id`, **sem savepoint**, como o check-in (ADR 0012, item 3) e a semana-padrão
(#282). Testes: apagar o check-in, a atividade e `worker.apagar_checkin` apagam o feedback; reimportar a atividade (ADR 0006: atualiza no lugar) mantém check-in e feedback.

**Dado de saúde (a regra da Meta 6, ADR 0010 item 2 e ADR 0012 item 5, aplicada ao feedback).** O feedback **é derivado de dado de saúde** (PSE, sensação, atalhos) e
**é dado de saúde**: só no banco local; **nunca em log, exceção, captura, fixture real ou arquivo versionado**; devolvido só ao próprio atleta
(`/atletas/{atleta_id}/...`, outro atleta recebe `404`); apagado **com o check-in**; o comando `worker.apagar_checkin` passa a cobrir o feedback
pela cascata e a imprimir só contagens (`checkins: apagados=N`, `feedbacks: apagados=M`). Comandos imprimem só contagens e códigos de motivo, nunca texto.

### 3. Camada de LLM trocável e `worker.gerar_feedback`
- **Biblioteca e configuração.** **LiteLLM** (interface unificada compatível com a da OpenAI; confirmar a versão e os nomes na documentação dela quando a #326
  abrir), como já manda o `AGENTS.md`. `LLM_PROVIDER` e `LLM_MODEL` vêm do `.env`; a chave do provedor também, por variável de ambiente (nome conforme
  o provedor; a conferir na #326), **nunca no repositório**. Padrão: **Groq**, **plano gratuito, sem cartão** (decisão 4). Trocar de provedor ou de modelo é mudar o `.env`, sem tocar no código.
  O resto do app **nunca** chama LiteLLM nem provedor: só a interface `redigir(pacote) -> texto` do módulo `app/explicacao/llm.py` (#326).
- **Provedor falso** (`LLM_PROVIDER=falso`), **obrigatório em testes e CI**: sem rede e sem chave. Devolve um texto fixo por fixture, e um modo para devolver
  **textos ruins** de propósito (número fora do pacote, linguagem proibida, 6 linhas), para provar que as checagens reprovam. O texto do provedor falso é de teste: grava
  `provedor = 'falso'` e a API o devolve em `provedor`, para nunca passar por texto de verdade. O padrão do `.env.example` continua `groq`.
- **Provedor não configurado** (`LLM_MODEL` vazio, sem chave ou provedor desconhecido): sem exceção na API; o feedback fica `sem_feedback` com `motivo = provedor_nao_configurado`.
- **Prompt.** Fixo, versionado no repositório (`feedback_prompt@1`; contém só regras e o guia de tom, **nenhum dado**). A mensagem do usuário é o pacote em JSON.
  A saída é texto simples, 3 a 5 linhas, uma frase por linha.
- **Tempo limite e erro.** Tempo limite por chamada (padrão 20 s, a confirmar). **Sem nova tentativa dentro da chamada**: a próxima execução do worker é a nova tentativa.
  Qualquer erro do provedor (rede, limite do plano gratuito, resposta vazia, tempo esgotado) vira `motivo` (`provedor_erro` ou `provedor_tempo_limite`), nunca exceção na API.
- **Limite por execução.** `uv run python -m worker.gerar_feedback --atleta "<nome>" [--limite N] [--refazer]`: no máximo **N chamadas ao provedor por execução** (padrão 20, a confirmar);
  as que sobrarem ficam sem linha ou `limite_de_chamadas` e entram na próxima execução. `--refazer` ignora o "já está pronto" e refaz o feedback do atleta (ainda dentro do limite).
  O plano gratuito tem limite de chamadas por minuto e por dia; **os números do plano não são fixados aqui** (a conferir na página do provedor quando a #326 abrir).
  Mesma convenção dos demais comandos: nome repetido pega o menor id, nome inexistente sai com código 1, saída só com contagens (`feedback: gerados=a sem_feedback=b ignorados=c`).
- **Nada em log.** Nem o pacote, nem o texto, nem o texto reprovado, nem a mensagem de exceção do provedor (que pode repetir o corpo da requisição): captura-se a **classe** do erro, converte-se
  em `motivo` e descarta-se a mensagem. O log de depuração e os *callbacks* do LiteLLM ficam desligados (os nomes exatos dos ajustes, a conferir na #326). Teste com um texto marcador sintético
  (`MARCADOR-SINTETICO-123`) no pacote e na resposta do provedor falso, em sucesso, em reprovação e em erro: o marcador não aparece em `caplog.text` (nível DEBUG), em `stdout`, em `stderr` nem em
  mensagem de exceção. O `worker` loga só contagens e códigos de motivo.
- **O que vai ao provedor** (decisões 2, 3 e 9): o prompt fixo e o pacote de fatos do item 1, e nada mais. **O pacote é dado de saúde** (PSE, sensação, atalhos, FC). Com o "sim" do Angelo (decisão 9), o
  worker pode gerar o feedback dos **treinos reais dele**, **só na máquina dele**, no plano gratuito do Groq e com o limite por execução; o texto real vai **só para o banco local**. Em **CI, testes, fixtures,
  exemplos e capturas** o provedor é o falso ou os dados são sintéticos. Os termos de retenção do provedor no plano gratuito ficam **a conferir** (ver "Limitações" e "A confirmar", item 10).

### 4. Checagens e o destino do texto reprovado
Função pura (`app/explicacao/checagens.py`, #325, `checagens_feedback@1`): recebe o pacote e o texto e devolve aprovado ou o **código** do motivo. **Qualquer reprovação** descarta o texto: ele **não é gravado**,
não chega ao app, e o feedback daquele treino fica `sem_feedback` com `motivo = texto_reprovado` (decisão 8). Nova tentativa na próxima execução do worker. **Não há texto de reserva escrito por regra.**

1. **Todo número do texto está no pacote.** Extrai-se do texto cada número (inteiro, decimal com vírgula, ponto de milhar, `m:ss`, porcentagem), junto da unidade quando há; cada um precisa ser um valor do pacote ou aparecer
   num `*_texto` dele. **Nenhuma conta**: "18 s/km mais lento" só vale porque o pacote traz `diferenca_texto`; "metade" ou "o dobro" não. **Números por extenso** (dois a dez, vinte, cem, mil, metade, dobro...)
   reprovam, para o número não escapar da checagem escrito em palavras ("um" e "uma" como artigo passam). A checagem também confere que o número e a unidade andam juntos (a conferir na #325: ver "A confirmar", item 5).
2. **Linguagem proibida.** Palavras e expressões, sem acento e sem diferença de maiúscula, em **lista própria** (nota em `docs/metricas/`, #325; a lista abaixo é o ponto de partida, com os exemplos que precisam reprovar):
   - **Diagnóstico médico:** lesão, lesionado, inflamação, tendinite, fratura, distensão, overtraining, sobretreino, supertreino, doença, infecção, sintoma, diagnóstico, síndrome, arritmia, desidratação.
   - **Culpa e juízo:** falhou, fracasso, fracassou, preguiça, desleixo, culpa, fraco, decepcionante, "você deveria", "você devia", péssimo, horrível, "treino ruim", "mau treino".
   - **Promessa:** vai melhorar, "com certeza", certamente, garanto, prometo, garantido, "você vai conseguir", "na próxima será", "em breve você".
   - **Causa afirmada ou sugerida:** porque, "por causa", "por conta", devido, "graças a", "se deve", "foi por isso", causou, explica, resultado do (calor, cansaço...), "pode ter sido", "deve ter sido",
     possivelmente, provavelmente, talvez. O texto põe fatos lado a lado; quem liga um ao outro é o atleta.
   - **Conselho:** descanse, descansar, procure, consulte, evite, tente, recomendo, sugiro, "o ideal", "precisa", "não esqueça", cuide, hidrate. Vale também para a dor: sem conselho (decisão 7).
   - **Quem fala:** professor, treinador, técnico, coach (a decisão 6: o app fala; o nome do professor só na Meta 10); **primeira pessoa** ("eu", "nós", "meu", "nosso"); IA ou modelo; exclamação e emoji.
   - **Exceção por frase exata:** "sono ruim", o rótulo do atalho, não é culpa. Fora dessa frase, a palavra "ruim" reprova.
3. **Forma.** Entre **3 e 5 linhas** (uma frase por linha, linhas vazias não contam), cada uma com até **140 caracteres** (a confirmar), sem lista, sem título, sem Markdown.
4. **Dor.** Com `dor` entre os atalhos, o texto tem **exatamente** a frase "Você registrou dor neste treino." e nenhuma outra menção a dor, nem a parte do corpo.
   Sem `dor`, o texto **não** fala em dor. Idem para os outros atalhos: só se diz que foi marcado (`cansaco`: "cansaço", `sono_ruim`: "sono ruim", `calor`: "calor", `trabalho_estresse`: "trabalho ou estresse"), e só os marcados.
5. **Nada do que não está no pacote:** o texto não cita o texto livre, nome, data ou lugar (a checagem 1 pega os números; a lista pega os termos; um nome próprio fora do vocabulário do pacote reprova).

Cada checagem tem teste com **textos ruins sintéticos que precisam reprovar** e **textos bons que precisam passar** (os 6 exemplos acima são os primeiros textos bons). O número de textos e as listas são
refinados na #323 e #325; a lista de linguagem proibida tem **nota própria** e sobe a versão `checagens_feedback@N` quando muda.

### 5. Tom do texto
- **Quem fala é o app.** Sem o nome do professor (até a Meta 10), sem primeira pessoa, sem "Olá"/"Parabéns": o texto fala **do treino**, com **segunda pessoa** quando é o atleta ("Você marcou...", "Seu pace...").
- **3 a 5 linhas, frases curtas**, uma por linha. É **texto escrito**: o feedback não é áudio nem fala (o Angelo esclareceu em 10/11); este documento não usa outro termo para o texto.
- **Conteúdo, nesta ordem, só o que o pacote sustenta:** (1) como foi **contra o normal** do tipo de treino (`fora`, `dentro`, `aprendendo` ou "sem comparação" e o motivo); (2) o que o **check-in** diz (PSE, sensação, atalhos marcados);
  (3) o **contexto** (clima, carga pela PSE, carga do relógio quando existe); (4) uma **observação positiva**, **só quando um fato a sustenta** (por exemplo, todas as métricas dentro do normal). Sem fato, sem elogio.
- **Nunca julga.** `fora` é "fora do seu normal", não "pior"; a comparação é com o histórico dele. **Nunca afirma causa**: o clima e o check-in ficam ao lado da comparação, sem "porque" (lista do item 4).
- **"Dor"**: uma frase, "Você registrou dor neste treino.", sem conselho, sem parte do corpo, sem elogio em volta. Os demais atalhos são ditos como foram marcados ("Você marcou calor e cansaço").
- **Mesma regra do dado:** nenhum exemplo desta ADR é dado real.

## Alternativas consideradas
- **Gerar o feedback no `PUT` do check-in.** O atleta esperaria a rede para registrar o treino, e uma falha do provedor atrapalharia o check-in. Descartada: só o worker gera (item 2).
- **Guardar o pacote de fatos junto do feedback.** Auditável, mas duplica o check-in (dado de saúde) e a linha de base, que muda. Descartada; guardam-se só as versões e o que o texto precisa.
- **Chave do feedback em `atividade_id` em vez de `checkin_id`.** Simples, mas o feedback poderia sobreviver ao check-in apagado se alguém esquecesse a exclusão. Com `checkin_id` e cascata, "apagado com o check-in" é garantia do banco. Descartada.
- **Marcar desatualizado também quando a linha de base muda.** O feedback seria refeito a cada treino novo, gastando chamadas e trocando um texto que o atleta já leu. Descartada; o texto descreve o treino no momento da geração.
- **Texto de reserva por regra quando a checagem reprova** ("Treino registrado."). Descartada pelo Angelo (decisão 8).
- **Guardar o texto reprovado para auditoria.** É dado de saúde sem utilidade para o atleta. Descartada: só o código do motivo.
- **Chamar o provedor direto (SDK da Groq).** Proibido pelo `AGENTS.md`; a camada trocável é regra do projeto.
- **Estado próprio "sem feedback possível" (`sem_fatos`).** Com check-in o pacote sempre existe; linha de base "aprendendo" ou sem tipo entram no texto. Descartada (item 2).
- **Um estado por motivo na API** (`reprovado`, `sem_provedor`...). O app trata todos como o mesmo cartão. Descartada: um `indisponivel` com `motivo` em código e `mensagem` pronta.
- **Mostrar o texto desatualizado com um aviso.** Ele pode contradizer o check-in novo. Descartada: a API não o devolve (item 2).
- **Deixar o modelo explicar o "porquê".** Proibido pela decisão 6 e pela seção 4.3 ("o motor nunca afirma causa").

## Consequências
- O feedback chega ao atleta **só** depois de passar por checagens em código; quando não passa, aparece "sem feedback" com o motivo, e o app não tem outro texto.
- Existe um dado novo de saúde (o texto do feedback) com a mesma regra da Meta 6; `worker.apagar_checkin` apaga o feedback junto (cascata).
- A API ganha um campo `feedback` com cinco estados (`pronto`, `sem_checkin`, `pendente`, `desatualizado`, `indisponivel`; `null` se não elegível) e um adendo da ADR 0004.
- A Meta 9 depende de um provedor externo; sem rede, sem chave ou sem o plano gratuito, o resultado é `sem_feedback` e tudo mais funciona.
- Nenhuma `VERSAO` existente sobe. Nascem `fatos_treino@1`, `feedback_prompt@1` e `checagens_feedback@1`.
- A migração `0013` é aditiva e reversível; o `downgrade` apaga os feedbacks.

## Limitações
- **O pacote é dado de saúde que sai da máquina** quando o provedor é real. Com o "sim" do Angelo (decisão 9) vale para os treinos **dele**, só local. Os termos de
  retenção e de uso de dados do provedor no plano gratuito **não foram lidos** nesta ADR (a conferir, "A confirmar" item 10). Para **outros atletas** o "sim" dele não vale: pediria base legal (LGPD) e consentimento de cada um (Meta 10 em diante).
- **Sem login:** "só ao próprio atleta" é o `atleta_id` da rota, como no check-in (ADR 0012, "Limitações"). Identidade é da Meta 10.
- **O texto de uma LLM pode ser inexato mesmo passando nas checagens** (o número bate, a frase interpreta mal). As checagens reduzem o risco; não o eliminam. A QA lê textos de fixtures; a revisão de uma amostra pelo professor é da Meta 10.
- **O feedback não acompanha reimportação** da atividade (mudou a duração ou a FC no arquivo): continua o texto antigo até o check-in mudar ou o `--refazer` (ver "A confirmar", item 6).
- Sem pace ajustado, sem estimativa de efeito do clima, sem sono, HRV nem FC de repouso, sem séries de natação, sem resumo semanal, quinzenal ou mensal, sem envio por WhatsApp ou e-mail.
- Fontes de LiteLLM e Groq **não foram abertas** para esta ADR (nomes de variáveis, ajustes de log e limites do plano gratuito são "a conferir" na #326).

## Fora desta ADR
Motor de explicação com estimativa de quanto cada fator pesa (seção 4.3, passo 3; o pacote só põe os fatos lado a lado); resumos semanal, quinzenal e mensal; mensagens em nome do professor e amostra para ele
revisar (Meta 10); aviso ou envio fora do app; agente com pergunta livre (Meta 11); feedback sem check-in; feedback de treino de **outros atletas** no provedor real (o "sim" da decisão 9 é só do Angelo).

## Fontes
Nenhuma fonte de literatura é nova: o pacote usa só o que as ADRs 0007, 0008, 0010, 0011 e 0012 e as notas de métrica já definem (as citações de Borg, Foster, Leys e Rousseeuw continuam **a conferir nos textos**, como nas ADRs 0011 e 0012).
Regra própria do projeto, sem artigo: o pacote de fatos, as checagens, a lista de linguagem proibida, o tom e as formas do texto (decisões do Angelo de 10/11 e propostas desta ADR). LiteLLM e Groq: **a conferir** (ver "Limitações").

## A confirmar
Cada item tem o **padrão** que vale se o Angelo disser "ok" sem mudança.
1. **A "observação positiva" é obrigatória?** O plano (seção 4.6) a pede em todo texto. **Padrão:** só quando um fato do pacote a sustenta (por exemplo, métricas dentro do normal); sem fato, o texto não tem elogio. É o que os exemplos 4 e 5 mostram. *Angelo.*
2. **Clima e check-in podem ser ligados com "possível"?** (por exemplo, "o calor possível pesou"). **Padrão:** não: lado a lado, sem ligação (exemplo 4); a ligação entra com o motor de explicação, em outra meta. *Angelo.*
3. **Tempo limite e limite de chamadas** (**Theo aprovou em 10/11**). **Padrão:** 20 s por chamada e 20 chamadas por execução, ajustáveis pelo `.env` ou por `--limite`; os números do plano gratuito do Groq são conferidos na #326. *Theo e Duda.*
4. **Quantas vezes tentar de novo** (**Theo aprovou em 10/11**: sem teto, com a fila por menos `tentativas`). **Padrão:** sem teto: a cada execução, uma nova tentativa para cada `sem_feedback` (decisão 8), contida só pelo limite por execução; o `--refazer` força. Um teto (por exemplo, 3 tentativas seguidas) evitaria gastar chamadas com um texto que sempre reprova. *Theo.*
5. **Quão estrita é a checagem de unidade.** **Padrão:** número e unidade juntos ("5:44/km" não vira "5:44 bpm"); número solto (sem unidade) só passa se for um valor do pacote. A regra fina fica para a #325. *Caio.*
6. **Reimportação da atividade e feedback** (**Theo aprovou em 10/11**). **Padrão:** o feedback **não** é refeito sozinho (descreve o treino na hora em que foi gerado); `--refazer` o refaz. A alternativa (comparar uma impressão do pacote) custa uma coluna a mais. *Theo e Duda.*
7. **Tamanho do texto.** **Padrão:** 3 a 5 linhas, até 140 caracteres por linha, até 700 no total (o `CHECK` da coluna). *Caio.*
8. **O provedor falso aparece na API?** **Padrão:** sim, como `origem = teste` (a API não manda nome de provedor nem de modelo), para um texto de teste nunca passar por texto de verdade; o cartão pode mostrar um selo "de teste" (Lia, #329). *Theo e Lia.*
9. **Gerar também depois do `PUT`, em segundo plano.** **Padrão:** não; só o worker (item 2). No piloto local o `pendente` dura até alguém rodar o comando. Se isso incomodar o Angelo, a alternativa é um gatilho de fundo depois do `PUT`
   (ainda com o limite por execução e sem atrasar a resposta), em issue própria. *Angelo e Theo.*
10. **Antes da primeira rodada com treino real.** **Padrão:** a Duda confirma na #326 os termos de retenção do provedor no plano gratuito e o que a LiteLLM registra; só então o Angelo roda o `worker.gerar_feedback` nos treinos dele. O resultado fica só no banco local (decisão 9). *Duda e Angelo.*

## Data e quem decidiu
2026-11-10. Proposta do Caio (ciência), com revisão da Duda (modelo de dados e camada de LLM) pedida no PR. Decisões do Angelo de 10/11 ("ok para as oito", com o esclarecimento do item 6) no Contexto. Issue #322.
Modelo de dados: **aprovado pelo Theo em 2026-11-10** (comentário no PR #340: FK em `checkin_id`, desatualizado pelo `atualizado_em` e por `versao_fatos`, só o worker gera, sem teto de tentativas com a fila acima, 20 s e 20 chamadas, reimportação só com `--refazer`, cinco estados, sem `sem_fatos`).
Exemplos de tom e itens 1, 2 e 9 de "A confirmar": aguardam o Angelo. Camada de LLM: aguarda a revisão da Duda. Status `proposta`; passa a `aceita` com essas duas respostas.
