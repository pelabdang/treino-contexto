---
tipo: decisao
status: aceita
dono: duda
atualizado: 2026-11-06
links: [[decisoes/0001-modelo-de-dados-minimo]], [[decisoes/0003-fuso-da-atividade]], [[decisoes/0005-serie-de-tiros-o-que-entra]], [[decisoes/0006-upload-de-fit]], [[decisoes/0007-clima-da-atividade]], [[decisoes/0008-deteccao-de-esforcos]], [[metricas/esforcos]], [[modulos/banco]], [[modulos/api]], [[produto/roadmap]], [[glossario]]
---
# ADR: 0009 Treino de transição (rótulo sugerido e corrigível)

> Aceita em 06/11: o Angelo respondeu "ok para todas" às recomendações (seção "Decisões do Angelo") e o Theo aprovou o modelo de dados, o esboço das rotas e a regra sem mesmo dia local. **Nenhuma linha de código nem migração muda neste PR.**
> Todos os exemplos abaixo são sintéticos. Issue #155; dá base para #156 (regra), #157 (banco e comando) e #170 (API).

## Contexto
Um **treino de transição** (também chamado de brick) é feito em uma modalidade logo seguida de outra, e o relógio grava cada parte como
uma atividade separada. Hoje nada no produto diz que essas atividades formam um treino só, e o atleta multiesporte não consegue listá-los nem
compará-los.

**Decisão de produto (Angelo, 04/11):** não juntar as atividades numa sessão composta. Cada atividade ganha um **rótulo "treino de
transição" (sim/não)**. Uma regra automática **sugere** o rótulo; o atleta **corrige**. Com o rótulo, ele lista e compara.

### O que o código do `main` mostra (conferido em 06/11)
- `Atividade` (`services/api/app/db/models.py`) tem `modalidade` (`corrida`, `natacao`, `ciclismo`, `outra`, com `CHECK`), `subtipo`, `inicio` (UTC),
  `fuso_min` (ADR 0003), `duracao_s`, `distancia_m` e `fc_media`. **Não existe** campo, tabela nem nota sobre transição ou multiesporte.
- A atividade é identificada por `(atleta_id, fonte, fonte_id)` e a importação **atualiza no lugar** o que mudou (ADR 0006). O `id` não muda, então
  uma tabela que aponte para `atividade.id` sobrevive à reimportação. As tabelas ligadas à atividade seguem `ON DELETE CASCADE`
  (`segmento`, `clima_atividade`, `bloco_atividade` da ADR 0008).
- `tipos.py` devolve `outra` para tudo que não é natação, ciclismo ou corrida. **Não conferi como a exportação real trata o multiesporte** (os
  arquivos reais ficam com o Caio, fora do repositório); ver "Seguimento".
- `duracao_s` é o tempo em movimento (`total_timer_time` no FIT; é a mesma dúvida do item 5 de "A confirmar" da ADR 0008). Logo `inicio + duracao_s`
  é o fim **no melhor caso**: com pausa automática ligada o fim real é um pouco depois, e o intervalo calculado sai maior que o real.
- Todos os consumidores atuais (identidade, clima, `tiros_1km`, `bloco_atividade`) olham **uma atividade por vez**, e continuam olhando.

## Decisão

### 1. Onde fica o rótulo: tabela própria `rotulo_transicao` (proposta; precisa do Theo)
Uma linha por atividade que tem um rótulo que vale registrar. A atividade não ganha coluna e não muda de identidade.

| Coluna | Tipo | Observação |
|---|---|---|
| `id` | inteiro, chave | |
| `atividade_id` | FK única | `atividade.id`, `ON DELETE CASCADE` |
| `transicao` | booleano, não nulo | `true` = é treino de transição; `false` = o atleta disse que não |
| `origem` | texto (20), `CHECK` | `sugerido` (pela regra) ou `atleta` |
| `versao_regra` | texto (40), nulo | só em `sugerido`; ex. `transicao@1` (formato da ADR 0002). Nulo em `atleta` |
| `definido_em` | datetime com fuso | quando a regra sugeriu ou o atleta corrigiu |

`CHECK`: `origem = 'sugerido'` implica `transicao = true` e `versao_regra` preenchida (a regra só grava "sim"). A migração é do Alembic, em #157, só cria a
tabela e não edita as anteriores. **Não há migração nesta issue.**

**Ausência de linha = "não", sem origem.** A regra só grava linha quando sugere "sim". Isso evita uma linha por atividade do histórico. Uma linha
`atleta` com `transicao = false` é o único jeito de dizer "a regra sugeriu e eu discordo".

**Por que tabela e não coluna na `atividade`:** (a) a importação compara e reescreve campos da atividade; uma coluna de rótulo entraria nessa
comparação e um erro ali poderia apagar a correção do atleta; (b) a correção é dado do atleta e tem ciclo de vida próprio (origem, versão, quando
mudou); (c) é o padrão já aceito para dado derivado (`clima_atividade`, `bloco_atividade`); (d) retirar o recurso é apagar uma tabela, sem tocar `atividade`.

### 2. Regra de sugestão `transicao@1` (geral e nomeada)
A regra é uma **função pura** sobre as atividades de **um** atleta: entra uma lista de registros leves (`id`, `modalidade`, `inicio`, `duracao_s`) e sai o
conjunto de `id` sugeridos. Sem banco e sem rede. Em #156 o Caio escreve e calibra; em #157 a Duda persiste. As constantes têm nome e são iguais para todos
os atletas (ADR 0005, item 2): nada de dia da semana, nome de treino nem critério de um atleta.

Duas atividades **vizinhas** (ordenadas por `inicio`) do mesmo atleta formam um **par de transição** quando:
1. as duas têm modalidade em `MODALIDADES_DE_TRANSICAO = {corrida, natacao, ciclismo}` (`outra` fica fora: não se sabe o que é);
2. as **modalidades são diferentes**;
3. o **intervalo** `inicio_seguinte - (inicio + duracao_s)` fica entre `-SOBREPOSICAO_MAX_S` e `INTERVALO_MAX_S`.

Valores: os 30 min foram aceitos pelo Angelo (06/11) e o Caio pode calibrar em #156; a sobreposição de 60 s é proposta: `INTERVALO_MAX_S = 1800` (30 min) e `SOBREPOSICAO_MAX_S = 60`.
A sobreposição pequena cobre relógios que começam a parte seguinte antes de fechar a anterior e o fim estimado do aviso acima; sobreposição maior é
registro duplicado ou dois aparelhos, não transição.

Toda atividade que está em algum par é **sugerida** (uma vez só, mesmo estando em dois pares). A cadeia sai transitiva por construção: ciclismo, corrida e
natação seguidas sugerem as três. Duas atividades vizinhas da **mesma modalidade** não formam par (o relógio cortou, ou o atleta pausou e retomou); se
estão no meio de uma cadeia (corrida, ciclismo, ciclismo, corrida), cada ciclismo ainda forma par com a corrida do seu lado, e o agrupamento do item 4 junta o bloco.

**Sem condição de "mesmo dia local"** (diferente do exemplo da issue, que era ilustrativo). Com limite de 30 min ela só mudaria algo na virada da meia-noite,
e ali erraria (23:40 a 00:20 é uma transição). O limite de intervalo já separa o treino da manhã do da tarde, e a regra fica sem depender de `fuso_min`.
Se o Caio achar, com dado real, que o dia local melhora a regra, entra na `transicao@2`.

**Exemplos sintéticos** (A = ciclismo, B = corrida, mesmo dia):

| Atividades | Intervalo | Sugerido? |
|---|---|---|
| A 07:00 a 08:00, B 08:02 a 08:30 | 2 min | sim, as duas |
| A 07:00 a 08:00, B 14:00 a 14:30 | 6 h | nenhuma |
| A 07:00 a 07:50, depois A 07:52 a 08:20 (mesma modalidade) | 2 min | nenhuma |
| A 07:00 a 08:00, B 08:40 a 09:00 | 40 min | nenhuma (acima de 30 min) |
| A 07:00 a 08:00, B começa 07:59 | -1 min | sim (dentro de 60 s de sobreposição) |
| A 07:00 a 08:00, B 08:02 a 08:30, A 08:34 a 09:10 | 2 e 4 min | as três |
| A 23:40 a 23:55, B 00:00 a 00:20 (virada do dia) | 5 min | sim, as duas |

### 3. Correção do atleta: a correção sempre vence
- O atleta marca **sim** ou **não** em qualquer atividade dele, tenha a regra sugerido ou não. Isso grava (ou troca) a linha `origem = 'atleta'`,
  `versao_regra = NULL`, `definido_em = agora`. Ele também pode **desfazer** a correção: apaga a linha `atleta`, e a regra volta a valer na próxima rodada.
- **Rodar a regra de novo nunca toca numa linha `origem = 'atleta'`.** O comando de #157, para cada atleta: calcula o conjunto sugerido; insere linha
  `sugerido` para as sugeridas **sem linha**; atualiza `versao_regra` e `definido_em` das `sugerido` que continuam sugeridas; **apaga** as `sugerido` que a
  regra não sugere mais; e **ignora** toda atividade com linha `atleta`. É idempotente: rodar duas vezes deixa o mesmo banco.
- Exemplo: a regra sugere A e B; o atleta marca "não" em B. A regra roda de novo (mesma versão, versão nova, depois de reimportar): B continua "não"
  e A continua `sugerido`.
- A sugestão é calculada sobre as **atividades**, não sobre os rótulos dos vizinhos: corrigir uma atividade não muda a sugestão das outras. Só o
  agrupamento do item 4 usa os rótulos finais.
- Nesta meta a correção sai **pela API** (#170, item 5); a tela fica para depois, com o rafa-app.
- Apagar a atividade apaga o rótulo (cascata). Reimportar a atividade não apaga a correção (o `id` não muda).

### 4. Agrupar para comparar
O grupo **não é guardado**: é calculado na leitura, a partir dos rótulos finais (`transicao = true`, por linha `sugerido` ou `atleta`).
- Ordene as atividades rotuladas do atleta por `inicio`. **Um grupo é uma sequência de atividades rotuladas em que cada uma começa até `INTERVALO_MAX_S`
  depois do fim da anterior.** O limite é o mesmo da regra, para não haver duas definições. Uma atividade que o atleta marcou "sim" sozinha vira grupo de uma
  parte, e a listagem a marca como `incompleto`.
- Cada grupo tem: `inicio` (da primeira parte), `fim` (da última, estimado), as **partes em ordem** (`atividade_id`, `modalidade`, `inicio`, `duracao_s`,
  `distancia_m`, `fc_media`, ritmo da parte) e as **transições** (o intervalo entre cada duas partes, em segundos, com mínimo 0).
- **Forma** do grupo = a sequência de modalidades, ex. `ciclismo>corrida`. **Só se comparam grupos da mesma forma.** Formas diferentes podem aparecer na mesma
  listagem, mas a comparação parte a parte não faz sentido e a API recusa (400, dizendo a forma de cada um).
- **O que se compara**, parte a parte e no total:
  - **duração** de cada parte (`duracao_s`), a soma das partes, o **tempo de transição** de cada par e a soma das transições, e o tempo total (início da
    primeira ao fim da última, com o aviso do fim estimado);
  - **ritmo** de cada parte, como na métrica de esforços ([[metricas/esforcos]]): corrida em s/km (`duração / distância x 1000`), natação em s/100 m,
    ciclismo em km/h (`distância / duração x 3,6`); vazio quando falta a distância;
  - **FC** da parte (`fc_media`) e FC do treino (média das partes ponderada pela duração, só entre as partes com FC; vazia se nenhuma tiver);
  - a comparação é a **diferença** (B menos A, em segundos, no ritmo e em bpm) com os dois lados à vista; sem nota e sem "melhor".
- A distância **não se soma entre partes** (corrida com natação não tem unidade comum).

### 5. Contrato da API (esboço; os detalhes saem em #170, com cliente regerado)
- `GET /atletas/{id}/treinos-de-transicao?inicio=&fim=`: lista os grupos no período (data local, ADR 0003), mais recentes primeiro, com `grupo_id`
  (o `id` da primeira atividade do grupo), partes, transições, forma e `incompleto`.
- `GET /atletas/{id}/treinos-de-transicao/comparar?a=<grupo_id>&b=<grupo_id>`: item 4. `400` para formas diferentes; `404` para grupo inexistente ou de outro atleta.
- `PUT /atletas/{id}/atividades/{atividade_id}/transicao` com `{"transicao": true|false}` corrige (item 3). `DELETE` no mesmo caminho desfaz a correção.
- `AtividadeOut` ganha `transicao`: `{"valor": true|false, "origem": "sugerido"|"atleta"|null}` (campo novo e opcional; sem linha é `valor = false`, `origem = null`).
- Atividade de outro atleta responde `404`, como nas demais rotas de atividade.
- O `grupo_id` é derivado e **muda** quando uma correção parte ou junta o grupo: o app não deve guardá-lo. Isso entra na descrição do esquema.

### 6. Efeito nos outros consumidores
**Nenhum.**
- **Identidade:** a atividade não ganha coluna nem muda de chave; a importação (ADR 0006) não lê nem escreve o rótulo.
- **Clima (ADR 0007):** continua por atividade e pela posição de início; cada parte tem o seu.
- **Série de tiros e esforços (ADR 0008):** continuam por atividade; o rótulo não entra em `tiros_1km` nem em `esforcos`, e nenhuma `VERSAO` sobe.
- **Carga (Meta 6):** cada parte conta uma vez, como atividade; o rótulo não duplica nem funde.
- **Reclassificação** (`worker.reclassificar`, `detectar_esforcos`): não toca o rótulo.

### 7. Por onde segue
- **#156 (Caio):** a regra `transicao@1` como função pura, a nota da regra em `docs/metricas/`, a calibragem de `INTERVALO_MAX_S` com dado real (fora do git) e
  fixtures sintéticas dos exemplos do item 2.
- **#157 (Duda):** migração e modelo `RotuloTransicao`, persistência da regra e o comando `uv run python -m worker.sugerir_transicao [--atleta-id N]`,
  idempotente e sem rede; testes dos exemplos do item 3.
- **#170 (Duda):** as rotas do item 5, o agrupamento e a comparação do item 4 e o cliente regerado. A tela fica para depois.

## Alternativas consideradas
- **Sessão composta (fundir as atividades):** rejeitada pelo Angelo (04/11). Mudaria identidade, série, clima e carga, e é difícil de desfazer.
- **Coluna booleana na `atividade`:** mais simples, mas entra na comparação de campos da importação e não guarda origem nem versão (seriam mais duas
  colunas). Aceitável se o Theo preferir; regra e correção seguem iguais.
- **Tabela de grupos (`treino_transicao`, com as partes ligadas):** é fusão por outro nome. Cada correção teria de reorganizar grupos, e o grupo derivado do
  rótulo basta para listar e comparar.
- **Gravar também o "não sugerido" como linha:** daria a versão por atividade, mas uma linha por atividade do histórico. A regra é barata e roda no atleta inteiro.
- **Condição de mesmo dia local:** descartada pela virada da meia-noite (item 2).
- **Contar mesma modalidade colada como transição:** não é transição, é corte do relógio.

## Consequências
- Tabela nova `rotulo_transicao` e migração nova em #157; nada muda em `atividade`. Aprovada pelo Theo (06/11).
- Mais uma versão de regra (`transicao@1`), que sobe a cada mudança da regra; subir a versão exige rodar o comando, que não toca em correções do atleta.
- Uma regra de intervalo erra nos dois sentidos (pausa longa entre duas partes reais; duas atividades sem relação coladas). Por isso a correção é parte do
  desenho, não um extra, e a nota da regra registra isso como limitação.
- O fim da atividade é estimado por `inicio + duracao_s` (tempo em movimento): o intervalo mostrado pode ser maior que o real. API e nota dizem isso.
- O produto passa a ter dois rótulos por atividade (tipo de treino e transição); eles não se influenciam.

## Decisões do Angelo (06/11)
O Angelo aceitou as recomendações ("ok para todas"):
1. **Intervalo máximo** entre uma parte e a seguinte: **30 min** (`INTERVALO_MAX_S = 1800`). O Caio ainda pode propor ajuste em #156 com o histórico real.
2. **Natação entra:** corrida, natação e ciclismo, em qualquer ordem; `outra` fica fora.
3. **O atleta pode marcar "sim"** numa atividade que a regra não sugeriu ou numa só; a listagem mostra como `incompleto`.
4. **Compara-se só grupos com a mesma sequência de modalidades**; os outros só listam.
5. **Esteira e piscina contam como partes**, sem tratamento especial (o subtipo não entra na regra).

## Seguimento (não bloqueia)
- **Multiesporte gravado como uma atividade só (`outra`):** o Caio confere no histórico real (fora do repositório) e responde só sim ou não no PR da #156. Se sim, essa atividade já é "um treino" e a regra não se aplica a ela; se as partes vêm separadas, tudo acima vale.

## Aprovação do Theo (06/11)
Aprovados: a tabela `rotulo_transicao` (item 1; migração só em #157, sem tocar `atividade`), o esboço das rotas e de `AtividadeOut.transicao` (item 5; o detalhe volta ao Theo na #170) e a regra `transicao@1` sem a condição de mesmo dia local (item 2).

## Data e quem decidiu
2026-11-06. Pedido de produto: Angelo (04/11), issue #155. Rascunho: Duda (dados), tendo como base científica as notas do Caio em `docs/metricas/` e a ADR 0008.
Aceita em 06/11: Angelo (decisões acima) e Theo (modelo de dados, rotas e regra, no PR #214).
