---
tipo: decisao
status: proposta
dono: caio
atualizado: 2026-11-09
links: [[decisoes/0003-fuso-da-atividade]], [[decisoes/0004-contrato-tela-evolucao]], [[decisoes/0009-treino-de-transicao]], [[decisoes/0010-carga-de-treino]], [[decisoes/0011-linha-de-base-e-semana-padrao]], [[metricas/carga-treino]], [[modulos/banco]], [[modulos/api]], [[produto/roadmap]], [[produto/plano-mvp-execucao]], [[glossario]]
---
# ADR: 0012 Check-in pós-treino (PSE, sensação, observação) e `carga_pse@1`

> Proposta de 09/11 (issue #293). Fica "aceita" quando o Theo aprovar o modelo de dados no PR e o Angelo responder a seção "A confirmar".
> **Nenhuma linha de código nem migração muda neste PR.** Todos os números e exemplos são sintéticos. Check-in é dado pessoal e de
> saúde: nada de check-in real em repositório, log ou captura.
> Dá base para #294 (fixtures e oráculo), #295 (desenho da tela), #296 (banco, migração 0012 e API), #297 (`carga_pse@1`),
> #298 (check-in no `GET` da atividade e lista de pendentes) e #299 (tela).

## Contexto
"O check-in é o produto" ([[produto/plano-mvp-execucao]], seções 3.1 e 6): se o atleta não responde, o motor de explicação e o
feedback ficam sem o que mais importa (esforço percebido, trabalho, estresse, dor). A Meta 8 entrega o registro em **3 toques**, com
"nada a relatar" como resposta válida, e uma carga pela PSE (`carga_pse@1`) que dá carga também à natação, que a `carga@2` não tem.

### Decisões do Angelo (09/11, "ok para as cinco"), que esta ADR respeita
1. Abrir as issues e começar a Meta 8.
2. **3 toques:** PSE de 0 a 10 (CR-10), sensação em 5 níveis e observação por atalhos (dor, cansaço, sono ruim, calor, trabalho ou
   estresse) com texto livre opcional e **"nada a relatar"** como resposta válida.
3. **`carga_pse@1` = PSE x minutos**, por atividade, **separada da `carga@2`** e **sem série diária**.
4. Ele abre a tela de check-in no celular uma vez, no fim da meta.
5. A **observação** segue a regra dos dados de saúde da Meta 6 ([[decisoes/0010-carga-de-treino]], item 2): só no banco local, nunca em
   log, devolvida só ao próprio atleta, com comando para apagar.

### O que o código do `main` mostra (conferido em 09/11, commit `a41f759`)
- `Atividade` (`services/api/app/db/models.py`) tem `atleta_id`, `modalidade` (`corrida`, `natacao`, `ciclismo`, `outra`), `subtipo`
  (`multiesporte_pai` e `troca` entre eles), `inicio` (UTC), `fuso_min` (ADR 0003) e `duracao_s`, o **tempo de cronômetro**
  (`total_timer_time`, sem a pausa automática). Não há duração total (tempo corrido) gravada.
- `carga_atividade` (ADR 0010) guarda a `carga@2` por atividade; natação e `outra` ficam `sem_carga` com `modalidade_sem_carga`;
  `multiesporte_pai` e `troca` não têm linha.
- Não existe check-in no banco nem na API. A última migração é a `0011`; a próxima é a **`0012`**.
- As tabelas derivadas seguem o padrão: FK `ON DELETE CASCADE` para `atividade`, `CHECK` em vez de enum, `versao` em texto
  `<regra>@<n>` (ADR 0002). Os dados sensíveis da Meta 6 têm `worker.apagar_saude` (contagens, nunca valores).
- A API não tem login. "Devolvida só ao próprio atleta" vale, por ora, como: só as rotas de `/atletas/{atleta_id}/...` do próprio
  atleta (atividade de outro atleta responde `404`), e nunca em lista, agregado ou rota de professor (ver "Limitações").

## Decisão

### 1. Modelo de dados (para aprovação do Theo, antes de qualquer migração)
Uma tabela nova, **`checkin_treino`**, na migração **`0012`**, **um check-in por atividade**. Sem coluna nova em `atividade`
(o check-in tem ciclo de vida próprio, como o rótulo de transição, ADR 0009).

| Coluna | Tipo | Observação |
|---|---|---|
| `id` | inteiro, chave | |
| `atividade_id` | FK `atividade.id`, `ON DELETE CASCADE` | `UNIQUE`: **um check-in por atividade**; o atleta vem da atividade (sem `atleta_id` repetido) |
| `pse` | inteiro pequeno, não nulo | `CHECK pse BETWEEN 0 AND 10` (CR-10, item 2) |
| `sensacao` | inteiro pequeno, não nulo | `CHECK sensacao BETWEEN 1 AND 5` (item 2) |
| `nada_a_relatar` | booleano, não nulo | resposta explícita do terceiro toque |
| `dor`, `cansaco`, `sono_ruim`, `calor`, `trabalho_estresse` | booleanos, não nulos, padrão falso | os cinco atalhos da observação |
| `texto` | texto, anulável | texto livre opcional; `CHECK texto IS NULL OR length(texto) BETWEEN 1 AND 500`; a API apara espaços e grava vazio como `NULL` |
| `versao` | texto (20), não nulo | versão do formulário, `checkin@1` (escala CR-10 de inteiros, sensação em 5 níveis, os 5 atalhos); formato da ADR 0002 |
| `registrado_em` | datetime com fuso, não nulo | quando o atleta fez o check-in; **definido pela aplicação** (`datetime.now(UTC)`), não por `server_default` |
| `atualizado_em` | datetime com fuso, não nulo | igual a `registrado_em` na criação; a aplicação o atualiza a cada `PUT` (o `server_default` do SQLite é `CURRENT_TIMESTAMP` sem fuso e não há `onupdate` no banco) |

**`CHECK` de coerência** (um só, nome `observacao_coerente`): ou é "nada a relatar" **sem** atalho e **sem** texto, ou não é e há **ao menos
um** atalho **ou** texto:
`(nada_a_relatar = TRUE AND dor = FALSE AND cansaco = FALSE AND sono_ruim = FALSE AND calor = FALSE AND trabalho_estresse = FALSE AND texto IS NULL) OR (nada_a_relatar = FALSE AND (dor = TRUE OR cansaco = TRUE OR sono_ruim = TRUE OR calor = TRUE OR trabalho_estresse = TRUE OR texto IS NOT NULL))`.
Comparações **explícitas** com `TRUE`/`FALSE` (valem no Postgres e no SQLite 3.23 ou mais novo, versão a conferir no CI); nada de booleano solto nem de soma de booleanos.
Todas as colunas envolvidas são `NOT NULL`, exceto `texto`, que só aparece em comparação com `IS [NOT] NULL`: a expressão nunca vira `NULL`
(o `CHECK` aceitaria uma expressão `NULL`). Os cinco atalhos têm `server_default` falso.

**Por que booleanos e não JSON ou tabela filha para os atalhos.** São cinco atalhos fixos, consultáveis por coluna (o motor de explicação
da Meta 9 pergunta "teve dor?" sem abrir JSON) e com os `CHECK` acima. Um sexto atalho vira migração própria, o que é aceitável e deixa
a mudança visível. A `versao` registra com qual formulário a linha foi respondida.

**Por que PSE e sensação são obrigatórias.** A `carga_pse@1` precisa da PSE, e a sensação é o segundo toque. A observação é obrigatória
**como escolha explícita**: "nada a relatar" ou ao menos um atalho/texto. Assim o terceiro toque nunca é silêncio ambíguo (não respondeu x
nada a relatar). Salvar só a PSE não é permitido ("A confirmar" 3).

**Migração `0012`.** Só cria `checkin_treino` com seus `CHECK` e o `UNIQUE`; não edita tabelas anteriores. O `downgrade` apaga a tabela
(e, com ela, os check-ins: dado do atleta, sem cópia). Nomes pela naming convention do repo: no modelo, só `pse`, `sensacao`, `texto_tamanho` e `observacao_coerente`; na migração, `op.f('ck_checkin_treino_<nome>')` (o mais longo tem 34 caracteres, abaixo do limite de 63 do Postgres). **Sem índice a mais:** o `UNIQUE` de `atividade_id` já indexa a busca. Testes de migração subindo e descendo nos dois bancos, como nas anteriores.

**Cascata e reimportação.** `atleta` -> `atividade` -> `checkin_treino` depende de `PRAGMA foreign_keys` no SQLite: teste de que apagar a atividade apaga o check-in. A importação **atualiza a atividade no lugar** (mesma chave `(atleta_id, fonte, fonte_id)`, ADR 0006) e nunca apaga e recria; teste de que **reimportar mantém o check-in**, pois recriar a atividade o apagaria em silêncio pela cascata.

### 2. Escalas e textos
**PSE, CR-10 (0 a 10, inteiros).** A API devolve o número e o texto da âncora. Âncoras (a conferir nas fontes):

| PSE | Texto |
|---|---|
| 0 | repouso |
| 1 | muito leve |
| 2 | leve |
| 3 | moderado |
| 4 | um pouco difícil |
| 5 | difícil |
| 6 | (sem âncora) |
| 7 | muito difícil |
| 8 | (sem âncora) |
| 9 | (sem âncora) |
| 10 | máximo |

Os pontos 6, 8 e 9 ficam sem âncora própria: a tela mostra só o número, como na CR-10 modificada de Foster (a conferir). O que cada número significa é
sempre o do atleta: a PSE não se compara entre atletas.

**Sensação, 5 níveis (1 a 5).** 1 muito mal, 2 mal, 3 normal, 4 bem, 5 muito bem. Pergunta: "Como você se sentiu no treino?".

**Observação, atalhos** (`chave`, texto na tela): `dor` "Dor", `cansaco` "Cansaço", `sono_ruim` "Sono ruim", `calor` "Calor",
`trabalho_estresse` "Trabalho ou estresse". Vários podem estar marcados. **Texto livre** opcional, até 500 caracteres, junto dos
atalhos ou sozinho. **"Nada a relatar"** é um botão do terceiro toque; escolhê-lo limpa atalhos e texto (o `CHECK` exige).

**Os 3 toques.** (1) PSE; (2) sensação; (3) observação: um atalho, "nada a relatar" ou texto. A tela mostra uma pergunta por vez
e o `PUT` sai no fim, com as três respostas. O texto livre é opcional e **não** conta como toque.

### 3. Prazo, edição e apagar
- **Quando dá para criar:** até **7 dias** depois do dia do treino: a data local da atividade (ADR 0003: `inicio` + `fuso_min`; sem `fuso_min`,
  `America/Sao_Paulo`) precisa ser `>= hoje - 7 dias`, com "hoje" na data de `America/Sao_Paulo` (relógio injetável nos testes; bordas
  23:59 e 00:01 locais). A janela é **[hoje - 7, hoje]** e vem de **uma única função** (`dias_ate_hoje(N)`: `data_local >= hoje - N`) usada
  pela criação (N = 7) e pela lista de pendentes (`dias=N`). Depois disso o `PUT` de uma atividade **sem** check-in responde `422` com
  o código `fora_do_prazo`. Motivo: o esforço lembrado semanas depois deixa de ser PSE do treino ("A confirmar" 1).
- **Editar:** sem prazo. O `PUT` em atividade que já tem check-in **substitui** o registro inteiro (atualiza `atualizado_em`; `registrado_em`
  e `id` ficam). Não se guarda histórico das edições: só o último valor (menos dado pessoal guardado).
- **Apagar:** `DELETE` de um check-in, sem prazo, **remove a linha** (não só limpa campos). Idempotente.
- **Pendentes:** atividades do atleta **sem check-in**, com data local na janela acima (`dias` de 1 a 7), de toda modalidade, **menos**
  `multiesporte_pai` e `troca` (item 4). Mais recentes primeiro. Consulta: `atividade LEFT JOIN checkin_treino ... WHERE checkin_treino.id IS NULL`,
  com a exclusão escrita `subtipo IS NULL OR subtipo NOT IN (...)` (um `NOT IN` solto exclui os subtipos nulos, que são quase todos);
  a #296 e a #298 precisam de fixture com subtipo nulo. A data local não sai em SQL: filtra-se por `inicio >= hoje - (dias + 1) dias` e confere-se a data local em Python.
- **Uma atividade nunca tem dois check-ins** (`UNIQUE`); duas requisições simultâneas do mesmo `PUT` (clique duplo): busca a linha; se não há, `INSERT ... ON CONFLICT DO NOTHING`
  (por dialeto, SQLite e Postgres) em `atividade_id`, nova busca (acha a linha do outro `PUT`) e `UPDATE`. **Sem savepoint**, como o upsert da semana-padrão
  (ADR 0011, #282): o `SAVEPOINT` do pysqlite commita a transação externa no `RELEASE`. No Postgres o `INSERT` do segundo espera o commit do primeiro.
  O `UPDATE` não toca `id` nem `registrado_em`.
  O `PUT` **substitui** tudo: os atalhos que não vierem na lista ficam **desligados** (teste: `PUT` com dor e sono ruim, depois só calor, deixa só calor).
  `200` na criação e na edição (não `201`).

### 4. Multiesporte e atividades elegíveis
- **Elegível** = toda atividade, de qualquer modalidade (inclui `outra`, como força), **menos** `subtipo` em (`multiesporte_pai`, `troca`):
  o pai repete as partes e a troca não é treino (mesmo critério da carga e do tipo). O `PUT` nelas responde `422` com o código
  `atividade_sem_checkin`; o `GET` da atividade traz `checkin: null` e `carga_pse: null`.
- **Cada parte do multiesporte tem o seu check-in.** Não há check-in do treino inteiro nem cópia entre partes; a tela pode sugerir a PSE da
  parte anterior como valor inicial (`pse_sugerida` no `GET` da atividade, item 7; a tela é da #299; "A confirmar" 2). O rótulo de transição
  (ADR 0009) não entra aqui.

### 5. Dado sensível: a regra da Meta 6 aplicada ao check-in
O check-in inteiro é dado pessoal e de saúde (a observação é o mais sensível: dor, estresse, sono). Vale o que a ADR 0010 fixou:
1. **Só no banco local.** Nada de check-in em fixture real, captura, log ou arquivo versionado. Os backups do banco herdam a regra.
2. **Nunca em log.** Nenhum valor (PSE, sensação, atalhos, texto) em log, em mensagem de exceção ou em saída de comando. Os comandos
   imprimem só contagens. O `422` do check-in **não repete o que foi enviado**: a resposta traz só `loc`, `msg` e `type` (nem `input`, nem `ctx`,
   que também carrega o valor em erros de tamanho e de enum); o validador de coerência usa **mensagem fixa**, sem f-string com o valor. O
   handler vale só para as rotas de check-in (uma `APIRoute` própria no router do check-in; aplicar a toda a API mudaria as respostas das outras
   rotas). O schema 422 do OpenAPI não muda (`HTTPValidationError` só declara `loc`, `msg`, `type`). **Formato único** para o check-in: os 422 de
   domínio (`fora_do_prazo`, `atividade_sem_checkin`) saem como `{"detail": [{"loc": [...], "msg": "...", "type": "fora_do_prazo"}]}`, com o
   código no `type`. Teste com um texto marcador sintético (`MARCADOR-SINTETICO-123`) em vários cenários (texto longo demais, tipo errado, atalho
   desconhecido, `nada_a_relatar` com texto, erro 500 forçado): o marcador não aparece em `response.text` nem em `caplog.text` (nível DEBUG); nenhum
   middleware ou log de acesso registra corpo ou query. O `PUT` feliz loga só ids e contagens.
3. **Devolvido só ao próprio atleta.** O check-in só sai nas rotas do item 7, sob `/atletas/{atleta_id}/...` do dono da atividade
   (outro atleta responde `404`). **Não entra** em listas, na série de carga, em exportação, no pacote de fatos do feedback nem em
   qualquer rota de professor nesta meta. A lista de pendentes **não traz** nenhum campo do check-in.
4. **Comando para apagar:** `uv run python -m worker.apagar_checkin --atleta "<nome>"` apaga **todos** os check-ins do atleta
   (`checkin_treino` pelas atividades dele), idempotente, imprime só `checkins: apagados=N`. O atleta e as atividades ficam. Mesma convenção
   do `worker.apagar_saude` (nome repetido: o de menor id, com aviso de que os outros ficam; nome inexistente: código 1). Implementação:
   `DELETE FROM checkin_treino WHERE atividade_id IN (SELECT id FROM atividade WHERE atleta_id = :id)` com `synchronize_session=False`. Teste: dois
   atletas, só o escolhido perde os check-ins; uma segunda rodada dá 0. `DELETE` por atividade cobre o apagar pontual.
5. **O que é derivado** (`carga_pse`) é calculado na leitura e não guarda a observação.

### 6. `carga_pse@1`: carga pela PSE
**Fórmula.** `carga_pse = PSE x minutos`, em **UA** (unidades arbitrárias), a "sRPE" de Foster. Os minutos são `duracao_s / 60`,
o **tempo de cronômetro** (tempo em movimento) da atividade. Foster descreve a duração do treino; a nossa fonte só guarda o cronômetro, que
é o dado que existe e o mesmo que a `carga@2` usa. Em treino com muita parada (intervalado, natação com descanso na borda) o cronômetro pode
ficar abaixo da duração total e a carga pela PSE sai um pouco menor: limitação declarada. Usar o tempo corrido pediria gravar a duração total
na importação, e seria uma `carga_pse@2`.

**Casos.**
- `pse = 0` vale: carga `0` (repouso).
- Atividade com check-in e `duracao_s <= 0`: `estado = sem_duracao`, sem valor.
- Sem check-in: `estado = sem_checkin`, sem valor. Não se estima PSE.
- `multiesporte_pai` e `troca`: `carga_pse: null` (sem linha, como a `carga@2`).
- A natação **tem** carga pela PSE, ao contrário da `carga@2` (`modalidade_sem_carga`).
- **Não se soma nem se compara com a `carga@2`:** escalas diferentes (UA x TSS). Não há série diária, CTL, ATL nem TSB pela PSE
  (fora da meta). A `linha_base@2` não usa a `carga_pse` nesta versão.

**Exemplos à mão (sintéticos).**
- Corrida de 2700 s (45 min), PSE 6: `6 x 45 = 270 UA`.
- Natação de 2400 s (40 min), PSE 4: `4 x 40 = 160 UA` (a `carga@2` dela é `sem_carga`).
- Ciclismo de 3000 s (50 min), PSE 7: `7 x 50 = 350 UA`.
- Corrida de 2725 s (45,4167 min), PSE 6: `6 x 45,4167 = 272,5 UA`.
- PSE 0 em 1800 s: `0 UA`. Check-in em atividade com `duracao_s = 0`: `sem_duracao`.

**Calculada na leitura, não gravada.** É um produto de dois campos já gravados (PSE e duração); gravá-lo criaria uma cópia a invalidar a cada
edição do check-in ou reimportação. A resposta traz `versao = "carga_pse@1"`.

**Versão.** `VERSAO = "carga_pse@1"` em `services/api/app/metricas/carga_pse.py` (#297), função pura (PSE e `duracao_s` entram, a carga sai).
**Sobe** quando mudar: a fórmula; os minutos usados (cronômetro x tempo corrido); o tratamento de PSE 0 e de atividade sem duração; ou a regra
de elegibilidade.

### 7. API (esboço; os detalhes saem em #296 e #298, com cliente regerado e adendo da ADR 0004)
Todas sob `/atletas/{atleta_id}`. Atleta ou atividade inexistente, ou de outro atleta, responde `404` (`Erro`), nas **três** rotas, inclusive no `DELETE` (que não devolve `204` para atividade de outro atleta). A validação do corpo roda antes do handler: um `PUT` inválido numa atividade inexistente dá `422`, não `404` (sem vazamento).

**`PUT /atletas/{atleta_id}/atividades/{atividade_id}/checkin`** (`registrarCheckin`): cria ou substitui o check-in.
```json
{"pse": 6, "sensacao": 4, "nada_a_relatar": false, "atalhos": ["cansaco", "trabalho_estresse"], "texto": "Semana puxada no trabalho."}
```
`200` com o `CheckinOut` abaixo (criação ou edição). Idempotente. `422` (sempre sem repetir a entrada) para: `pse` fora de 0 a 10; `sensacao` fora de 1 a 5;
`atalhos` com chave desconhecida ou repetida; `nada_a_relatar = true` com atalho ou texto; `nada_a_relatar = false` sem atalho nem texto;
`texto` com mais de 500 caracteres; campo obrigatório ausente (`pse`, `sensacao`, `nada_a_relatar`); atividade de `multiesporte_pai` ou `troca`
(`atividade_sem_checkin`); criação fora do prazo (`fora_do_prazo`).

**`GET /atletas/{atleta_id}/atividades/{atividade_id}/checkin`** (`checkinDaAtividade`): o `CheckinOut`, ou `404` ("sem check-in") se a atividade
existe e não tem.

**`DELETE /atletas/{atleta_id}/atividades/{atividade_id}/checkin`** (`apagarCheckin`): `204`, também quando já não havia (idempotente).

**`CheckinOut`:**
```json
{
  "atividade_id": 12,
  "pse": 6,
  "pse_texto": "6",
  "sensacao": 4,
  "sensacao_texto": "bem",
  "nada_a_relatar": false,
  "atalhos": [{"chave": "cansaco", "texto": "Cansaço"}, {"chave": "trabalho_estresse", "texto": "Trabalho ou estresse"}],
  "texto": "Semana puxada no trabalho.",
  "versao": "checkin@1",
  "registrado_em": "2026-11-09T21:30:00-03:00",
  "atualizado_em": "2026-11-09T21:30:00-03:00"
}
```
`pse_texto` é a âncora quando existe ("difícil" para 5) e o número quando não ("6"). Valores brutos sem arredondar; o texto é só da API
(adendo 2 da ADR 0004).

**`GET /atletas/{atleta_id}/checkins/pendentes?dias=7`** (`listarCheckinsPendentes`): atividades elegíveis sem check-in dos últimos `dias`
(padrão e máximo 7; fora de 1 a 7, `422`), mais recentes primeiro. Sem nenhum campo de check-in.
```json
{"dias": 7, "total": 2, "pendentes": [
  {"atividade_id": 14, "modalidade": "corrida", "data_local": "2026-11-09", "hora_local": "07:10", "duracao": "0:45:00", "titulo": "Corrida, 45 min"},
  {"atividade_id": 13, "modalidade": "natacao", "data_local": "2026-11-08", "hora_local": "06:30", "duracao": "0:40:00", "titulo": "Natação, 40 min"}
]}
```
`data_local`, `hora_local` e `duracao` seguem o adendo 2 da ADR 0004; `titulo` é pronto pela API.

**`GET /atletas/{atleta_id}/atividades/{atividade_id}`** ganha, sem remover campo (adendo da ADR 0004, #298):
- `checkin`: o `CheckinOut`, ou `null` (sem check-in ou atividade não elegível);
- `checkin_aberto` (booleano): decide se a tela oferece "Fazer check-in". `false` em `multiesporte_pai`/`troca` e quando o prazo de
  criação (item 3) passou sem check-in; `true` se já existe check-in, porque editar não tem prazo. Só orienta a tela: o `PUT` continua
  recusando o que não vale (`fora_do_prazo`, `atividade_sem_checkin`);
- `pse_sugerida` (inteiro ou `null`): numa parte de multiesporte, a PSE do check-in da **parte anterior do mesmo multiesporte**, definida
  como a atividade elegível de `inicio` imediatamente menor dentro do intervalo do `multiesporte_pai` (a `troca` no meio não conta).
  `null` fora de multiesporte, na primeira parte ou quando a parte anterior não tem check-in. É só valor inicial sugerido: o atleta
  responde a PSE da parte, e nada é copiado entre partes (item 4).

  Os dois campos vieram do desenho da tela (#295) e entraram no `GET` pela #298; decisão do Theo em 09/11.
- `carga_pse`: `null` (não elegível) ou
```json
{"versao": "carga_pse@1", "estado": "calculada", "pse": 6, "minutos": 45.0, "valor": 270.0, "valor_texto": "270 UA",
 "texto": "Carga pela PSE: 6 x 45 min = 270 UA."}
```
`estado`: `calculada`, `sem_checkin` (`valor: null`, texto "Sem check-in: a carga pela PSE precisa da PSE do treino.") ou `sem_duracao`.
Com `estado = calculada`, `valor_texto` e o texto trazem 1 casa quando não é inteiro ("272,5 UA"). O objeto não traz a observação.
`checkin` é carregado com `LEFT JOIN` na mesma consulta da atividade (sem consulta extra); listas de atividades que não precisam dele não o carregam nem o
devolvem. O `datetime` sai sempre com fuso (o SQLite devolve sem `tzinfo`; a API o completa). `operationId`s únicos: `registrarCheckin`, `checkinDaAtividade`,
`apagarCheckin`, `listarCheckinsPendentes`; cliente regerado e `test_contrato_cliente.py` verde. A lista de pendentes devolve só `titulo` (modalidade e minutos),
que não é dado de saúde, e `dias` fora de 1 a 7 dá `422` pelo mesmo handler.

### 8. Por onde segue
- **#294 (Caio, à mão):** fixtures sintéticas de check-in (completos, "nada a relatar", só texto, PSE 0, fora do prazo, multiesporte) e o oráculo da `carga_pse@1`.
- **#295 (Lia):** desenho da tela de 3 toques e da lista de pendentes.
- **#296 (Duda):** migração `0012`, modelo, `PUT`/`GET`/`DELETE`, `worker.apagar_checkin`, o `422` sem eco da entrada, cliente regerado.
- **#297 (Caio):** `carga_pse@1` como função pura, nota em `docs/metricas/`.
- **#298 (Duda):** `checkin` e `carga_pse` no `GET` da atividade e a lista de pendentes.
- **#299 (Rafa):** a tela no app (web e celular).

## Alternativas consideradas
- **Vários check-ins por atividade (histórico de respostas).** Mais dado pessoal guardado e nenhum consumidor que precise da versão antiga.
  Descartada: um por atividade, o `PUT` substitui.
- **Atalhos em JSON ou em tabela filha.** JSON perde `CHECK` e consulta; a tabela filha pede junção para uma pergunta simples. Descartadas (item 1).
- **Colunas do check-in dentro de `atividade`.** A importação compara e reescreve campos da atividade (ADR 0009, item 1); uma coluna de dado do atleta
  entraria nessa comparação. Descartada.
- **Gravar `carga_pse`.** Cópia a invalidar a cada edição. Descartada (item 6).
- **Minutos pelo tempo corrido.** O dado não está gravado. Fica para uma `carga_pse@2`.
- **Check-in só do pai no multiesporte.** Perde a PSE por modalidade e o pai não tem tipo nem carga. Descartada (item 4).
- **Prazo duro também para editar.** Corrigir um toque errado não acrescenta lembrança nova. Descartada.
- **PSE como campo opcional.** Quebra a `carga_pse` e deixa o primeiro toque sem sentido. Descartada.

## Consequências
- A natação ganha uma carga (pela PSE), e a `carga@2` não muda. Nenhuma `VERSAO` existente sobe.
- Existe um dado novo de saúde (a observação); toda a regra da ADR 0010 passa a valer para ele, com seu comando de apagar.
- A API passa a ter um `422` próprio sem o campo `input`; é um desvio do padrão do FastAPI, restrito às rotas de check-in.
- O app passa a depender da lista de pendentes para o atleta não perder treinos recentes.
- A migração `0012` é aditiva e reversível; o `downgrade` apaga os check-ins.

## Limitações
- **Sem login:** "só ao próprio atleta" é o `atleta_id` da rota; qualquer cliente que conheça o id lê e grava o check-in dele. A mesma
  limitação do `PUT` da semana-padrão (ADR 0011, "A confirmar" 7). Exigir identidade é da Meta 10.
- A `carga_pse@1` usa o cronômetro e não o tempo total (item 6).
- Sem histórico de edições do check-in e sem check-in do treino multiesporte inteiro.
- As âncoras da CR-10 e a duração de referência de Foster vêm de fontes ainda não abertas (ver "Fontes").
- Lembrete por WhatsApp ou e-mail, check-in semanal, motivo de falta, equipamento e zona, e o professor vendo o check-in ficam fora.

## Fontes
Citações **ainda não conferidas nos textos**; o Caio abre cada uma antes de a nota da métrica citá-la (mesma pendência das ADRs 0008 e 0011):
- Borg, G. (1982). *Psychophysical bases of perceived exertion.* Medicine and Science in Sports and Exercise, 14(5), 377-381. Origem da
  percepção de esforço e das escalas de Borg.
- Borg, G. (1998). *Borg's Perceived Exertion and Pain Scales.* Human Kinetics. A escala de razão categórica CR-10 e suas âncoras.
- Foster, C., Florhaug, J. A., Franklin, J., Gottschall, L., Hrovatin, L. A., Parker, S., Doleshal, P. e Dodge, C. (2001). *A new approach to
  monitoring exercise training.* Journal of Strength and Conditioning Research, 15(1), 109-115. A sRPE: PSE da sessão x duração em minutos,
  em unidades arbitrárias, com a CR-10 modificada de 0 a 10.
- Regra própria do projeto, sem artigo: 3 toques, os 5 níveis de sensação, os cinco atalhos, o limite de 500 caracteres e o prazo de 7 dias
  (decisões do Angelo de 09/11 e propostas desta ADR).

## A confirmar
Para o Angelo; só o que é de produto e ainda não está decidido. Cada item traz **o padrão que o time segue enquanto não houver resposta**.

1. **Prazo para registrar.** Até quando o atleta pode fazer o check-in de um treino. **Padrão:** até 7 dias depois do treino (a mesma
   janela da lista de pendentes); editar e apagar, sem prazo.
2. **Quais treinos pedem check-in.** **Padrão:** toda atividade (inclui força/`outra`), menos o "pai" e a troca do multiesporte; no
   multiesporte, **um check-in por parte** (cada modalidade tem a sua PSE), e a tela pode oferecer a PSE da parte anterior como ponto de partida.
3. **Salvar só com a PSE.** **Padrão:** não: PSE, sensação e a escolha da observação (inclusive "nada a relatar") são obrigatórias; são
   3 toques, e um registro incompleto deixa a observação ambígua.
4. **Nome da carga pela PSE na tela.** **Padrão:** "Carga pela PSE", em **UA** (unidades arbitrárias), diferente de "pontos" da carga
   do relógio, para não misturar as duas escalas.
5. **Check-in sem login.** Hoje o "só ao próprio atleta" é o `atleta_id` do caminho: quem conhece o id lê, grava e apaga o check-in. **Padrão:**
   aceitar no piloto local (a API não é exposta); exigir identidade quando houver login (Meta 10). Mesma decisão do `PUT` da semana-padrão (ADR 0011).

## Data e quem decidiu
2026-11-09. Proposta do Caio (ciência), com revisão da Duda (modelo de dados e API) pedida no PR. Decisões do Angelo de 09/11 ("ok para as
cinco") no Contexto. Issue #293. Aprovação do Theo e respostas do Angelo ainda pendentes.
