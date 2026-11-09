---
tipo: decisao
status: aceita
dono: caio
atualizado: 2026-11-09
links: [[decisoes/0002-segmento-intensidade-e-versao]], [[decisoes/0003-fuso-da-atividade]], [[decisoes/0004-contrato-tela-evolucao]], [[decisoes/0005-serie-de-tiros-o-que-entra]], [[decisoes/0008-deteccao-de-esforcos]], [[decisoes/0009-treino-de-transicao]], [[decisoes/0010-carga-de-treino]], [[metricas/tiros-1km]], [[metricas/carga-treino]], [[modulos/banco]], [[modulos/api]], [[produto/roadmap]], [[produto/plano-mvp-execucao]], [[glossario]]
---
# ADR: 0011 Linha de base pessoal, semana-padrão e tipo de treino

> Aceita em 09/11 (issue #260): modelo de dados aprovado pelo Theo no PR #277 e os sete itens de "A confirmar" respondidos pelo Angelo ("ok para as sete": valem os padrões).
> **Nenhuma linha de código nem migração muda neste PR.** Todos os números e exemplos são sintéticos.
> Dá base para #261 (fixtures e oráculo), #262 (`tipo_treino@1`), #263 (`linha_base@1`), #264 (banco e API da semana-padrão),
> #265 (`classificar_atividades`), #266 (`linha_base` no `GET` da atividade) e #267 (desenho da tela).

**Status atual: implementada na Meta 7 (#260 a #266, #268, #288; falta a conferência local com o histórico real, #269).** Código: [[metricas/tipo-treino]] (`tipo_treino@1`),
[[metricas/linha-base]] (`linha_base@2`, adendo 2), o banco e a API ([[modulos/banco]], [[modulos/api]]), o cliente ([[modulos/api-client]]) e a tela ([[modulos/mobile]], [[design/telas/semana-padrao]]).
O oráculo é o [[metricas/tipo-linha-base-oraculo]]. Passo a passo: [[produto/meta-7-como-rodar]].

## Contexto
A Meta 7 compara cada treino com o **normal do próprio atleta**, só na **mesma modalidade e no mesmo tipo de treino**: uma linha de
base móvel (mediana da janela) e uma medida robusta de quanto a sessão fugiu do normal (camada 2 do [[produto/plano-mvp-execucao]],
seção 4.2). Para isso cada atividade precisa de um **tipo de treino** confiável. Decisões já tomadas, que esta ADR respeita:

**Angelo (09/11).**
- Início frio: **só "ainda aprendendo"**, sem valores de literatura.
- Janela de **8 semanas**, com **mínimo de 8 treinos** do mesmo tipo.
- O limite "fora do normal" e o texto do aviso são **propostos aqui** (item 6) e vão para "A confirmar".
- O tipo de treino vem da **semana-padrão** definida pelo atleta ou pelo treinador (por dia da semana: modalidade e tipo opcional,
  seção 3.1 do plano). A regra automática (`leve` e `longo` só na corrida) fica **só como reserva**.

**Theo (09/11).**
- Semana-padrão **por atleta**, com `vigente_desde` e `definido_por`; **sem grupo** de atletas.
- Precedência do tipo: confirmado, `professor` e `trainingpeaks` > semana-padrão (origem nova) > regra.
- Encaixe pela **data local** (ADR 0003) e pela **modalidade**.
- Formato que contradiz o plano **mantém o tipo do plano** e marca divergência **só como dado**.
- Mudar a semana-padrão **não reescreve** atividades anteriores a `vigente_desde`.

### O que o código do `main` mostra (conferido em 09/11, commit `863a415`)
- `Atividade` (`services/api/app/db/models.py`) tem `modalidade` (`corrida`, `natacao`, `ciclismo`, `outra`), `subtipo` (texto livre),
  `inicio` (UTC), `fuso_min`, `duracao_s` (tempo em movimento), `distancia_m`, `fc_media`, `tipo_treino` (`leve`, `moderado`,
  `longo`, `intervalado`, `fartlek`), `tipo_origem` (`sugestao`, `professor`, `trainingpeaks`, com `CHECK` de nome `tipo_origem`) e
  `tipo_confirmado`. Não há coluna de versão do tipo nem de divergência.
- Hoje **só a série de tiros sugere tipo**: `classificar_atividades` (`servicos/evolucao_tiros.py`) grava `intervalado` com origem
  `sugestao` quando há 2 ou mais tiros, desfaz a própria sugestão quando a regra deixa de achar tiros, e nunca toca tipo confirmado,
  `professor` ou `trainingpeaks`. A série de tiros (`sessoes_tiros_1km`) **não lê** `tipo_treino`: lê os blocos.
- `bloco_atividade` (ADR 0008) existe para corrida e ciclismo; a categoria `leve` marca a atividade **sem nenhum esforço**.
- `carga_atividade` (ADR 0010, `carga@2`) tem a carga por atividade; `multiesporte_pai` e `troca` não têm linha; natação e `outra`
  ficam `sem_carga` com o motivo `modalidade_sem_carga`.
- `rotulo_transicao` (ADR 0009) marca partes de treino de transição, por atividade, sem efeito no tipo.
- A última migração é a `0010`; a próxima é a **`0011`**. Não existe semana-padrão no banco; `professor` e `assessoria` existem como
  tabelas (ADR 0001), mas **sem login e sem vínculo usado**.

## Decisão

### 1. Modelo de dados (para aprovação do Theo, antes de qualquer migração)
Duas tabelas novas e duas colunas novas em `atividade`, mais o `CHECK` de `tipo_origem` ampliado, tudo na migração **`0011`**. Padrão
das anteriores: `CHECK` em vez de enum, nomes de constraint curtos, sem editar migrações antigas.

**`semana_padrao`**: uma linha por (atleta, vigência). É o cabeçalho; os itens ficam na tabela seguinte.

| Coluna | Tipo | Observação |
|---|---|---|
| `id` | inteiro, chave | |
| `atleta_id` | FK `atleta.id` | sem índice próprio: o `UNIQUE` abaixo já cobre a busca por atleta |
| `vigente_desde` | date | dia do calendário (sem fuso) a partir do qual a semana vale |
| `definido_por` | texto (20), `CHECK` | `atleta` ou `professor`; **declarado**, não verificado (não há login, ver "A confirmar" 1) |
| `definido_em` | datetime com fuso | `server_default now()`; atualizado a cada `PUT` |

`UNIQUE (atleta_id, vigente_desde)`. Reenviar a mesma vigência **substitui** os itens dela (idempotente). Uma vigência com **zero
itens** é válida e significa "a partir daqui, sem plano": é o jeito de encerrar uma semana-padrão.

**`semana_padrao_item`**: zero ou mais itens por dia.

| Coluna | Tipo | Observação |
|---|---|---|
| `id` | inteiro, chave | |
| `semana_padrao_id` | FK `semana_padrao.id`, `ON DELETE CASCADE` | indexada |
| `dia_semana` | inteiro pequeno, `CHECK dia_semana BETWEEN 1 AND 7` | ISO: 1 = segunda ... 7 = domingo (`date.isoweekday()`) |
| `modalidade` | texto (20), `CHECK` | `corrida`, `natacao` ou `ciclismo` (`outra` fica de fora: não tem tipo em nenhuma regra) |
| `tipo_treino` | texto (20), anulável, `CHECK` | os mesmos cinco valores de `atividade.tipo_treino`; `NULL` = "treina essa modalidade nesse dia, sem tipo" |

`UNIQUE (semana_padrao_id, dia_semana, modalidade)`: **um item por modalidade por dia**. Dois treinos da mesma modalidade no mesmo dia
com tipos diferentes no plano ficam fora desta versão (limitação declarada); dois treinos de modalidades diferentes no mesmo dia são
dois itens.

**Qual semana vale numa data.** Mesma regra do limiar (ADR 0010, item 1): para a data local `t` da atividade, a linha de
**maior `vigente_desde` com `vigente_desde <= t`**. Uma vigência no dia da atividade já vale para ela. A vigência termina quando a
próxima começa; **não há** `vigente_ate`. Sem nenhuma linha com `vigente_desde <= t`, **não há plano na data** e **nunca** se olha a
vigência seguinte. Isso é o que impede a mudança de plano de reescrever o passado.

**Mudanças em `atividade`** (nada é preenchido na migração):

| Coluna | Tipo | Observação |
|---|---|---|
| `tipo_origem` | (existente) | o `CHECK` `tipo_origem` passa a aceitar também **`semana_padrao`**: a migração remove e recria a constraint com os quatro valores (`sugestao`, `professor`, `trainingpeaks`, `semana_padrao`); no `downgrade`, as linhas com `semana_padrao` voltam a `tipo_treino`, `tipo_origem`, `tipo_versao` e `tipo_divergencia` nulos antes de recriar a constraint antiga (são derivadas e se reaplicam) |
| `tipo_versao` | texto (40), anulável | a versão da regra que escreveu `tipo_treino` quando a origem é `sugestao` ou `semana_padrao` (`tipo_treino@1`, formato da ADR 0002); nulo nas demais origens |
| `tipo_divergencia` | texto (20), anulável, `CHECK` | `sem_esforco` ou `tem_tiros` (item 4); só existe com `tipo_origem = 'semana_padrao'` |

São **dois** `CHECK` com nomes diferentes em `atividade`: `tipo_divergencia` (os valores `sem_esforco` e `tem_tiros`, ou nulo) e
`tipo_divergencia_origem` (`tipo_divergencia IS NULL OR (tipo_origem IS NOT NULL AND tipo_origem = 'semana_padrao')`; sem o `IS NOT NULL` a expressão vira NULL com `tipo_origem` nulo e o `CHECK` aceitaria a divergência). Tipo confirmado, `professor` e
`trainingpeaks` nunca têm divergência.

**Notas da migração `0011` (revisão da Duda).**
- Recriar o `CHECK` `tipo_origem` pede `batch_alter_table` no SQLite e `drop_constraint` + `create_constraint` no Postgres, com o
  nome `op.f('ck_atividade_tipo_origem')` nos dois. A migração sobe e desce nos dois bancos em teste.
- Ordem do `downgrade`: zerar `tipo_treino`, `tipo_origem`, `tipo_versao` e `tipo_divergencia` das linhas com `semana_padrao`; remover
  os `CHECK` de `tipo_divergencia`; recriar o `CHECK` antigo de `tipo_origem`; remover as colunas; remover as tabelas (itens primeiro).
- **Linhas antigas** com `tipo_origem = 'sugestao'` e `tipo_versao` nulo contam como **desatualizadas** e são regravadas na primeira
  passada de `worker.reclassificar` (ou da importação).

**Por que colunas em `atividade` e não tabela própria, ao contrário da ADR 0009.** O tipo **já mora** na `atividade` com origem e
confirmação, e a importação não o lê nem o escreve (quem escreve é `classificar_atividades`). Dividir o tipo em duas tabelas
obrigaria toda leitura a juntar as duas. A divergência é derivada do mesmo cálculo que escolhe o tipo e precisa ser **consultável em
lote** (a caixa do professor, Meta 10, lista as divergentes sem recalcular blocos). Uma coluna de dois valores atende; se a
divergência ganhar mais atributos, vira tabela depois.

**Sem `professor_id`.** O `definido_por` é só `atleta` ou `professor`, sem chave para a tabela `professor`: não há login nem vínculo
usado. Quando houver (Meta 10 em diante), entra `professor_id` anulável numa migração própria.

**Dado pessoal.** A semana-padrão é plano de treino do atleta: fica só no banco local, não vai para log nem para fixture real.

### 2. Precedência do tipo, na ordem (`tipo_treino@1`)
Para cada atividade elegível, o tipo vem do **primeiro** que se aplica:
1. **Tipo confirmado** (`tipo_confirmado`) ou origem `professor` ou `trainingpeaks`: **não muda**, nem pela semana-padrão nem pela regra.
   Sem `tipo_versao` e sem `tipo_divergencia`.
2. **Semana-padrão** vigente na data local, com item da mesma modalidade **e `tipo_treino` preenchido**, e a atividade sendo a
   escolhida do dia (item 3): `tipo_treino = tipo do item`, `tipo_origem = 'semana_padrao'`, `tipo_versao = 'tipo_treino@1'`,
   mais a divergência do item 4.
3. **Regra de reserva** (item 5): `tipo_origem = 'sugestao'`, `tipo_versao = 'tipo_treino@1'`.
4. Nenhum dos três: `tipo_treino`, `tipo_origem`, `tipo_versao` e `tipo_divergencia` nulos.

**Elegível** = toda atividade menos as de `subtipo` em (`multiesporte_pai`, `troca`), que **nunca recebem tipo** (mesmo critério da
carga, ADR 0010: o pai repete as partes e a troca não é treino).

**Função pura.** `tipo_treino@1` é uma função sem banco e sem rede: entra a lista de atividades de **um dia** de um atleta (id,
modalidade, subtipo, `inicio`, `duracao_s`, tipo e origem atuais, confirmado, resultado dos blocos e dos tiros) e os itens da semana
vigente; sai, por atividade, `(tipo, origem, divergencia)`. O serviço (#265) lê o banco, chama a função e grava **só o que mudou**.

**Idempotência.** Rodar duas vezes dá o mesmo resultado. O que a função grava e o que ela apaga:
- apaga e regrava só as origens que ela mesma escreve (`sugestao`, `semana_padrao`); nunca as três do passo 1;
- uma atividade cujo plano sumiu (item removido, vigência esvaziada) cai para a regra de reserva ou para nulo na próxima passada;
- o `intervalado` por tiros, que hoje é a única sugestão, **passa a fazer parte desta regra** (item 5) e mantém o comportamento atual
  quando não há plano.

### 3. Encaixe na semana-padrão: casos ambíguos
O encaixe usa o **dia da semana da data local** (ISO) e a **modalidade**; `subtipo` não entra (esteira é corrida, pedal virtual é
ciclismo, piscina e águas abertas são natação).

Semana de exemplo, **vigente desde 2026-02-02** (segunda), para todos os casos abaixo:

| Dia | Itens (modalidade, tipo) |
|---|---|
| segunda (1) | natação sem tipo |
| terça (2) | corrida `intervalado` |
| quarta (3) | ciclismo `leve` |
| quinta (4) | corrida `fartlek` |
| sexta (5) | (sem itens) |
| sábado (6) | corrida `longo`, ciclismo `moderado` |
| domingo (7) | corrida sem tipo |

**Casos (cada um vira teste na #261):**

| # | Situação | Regra | Resultado |
|---|---|---|---|
| E1 | Terça 2026-02-03, uma corrida de 50 min com 6 tiros de 1 km | encaixa; sem divergência | `intervalado`, origem `semana_padrao` |
| E2 | Terça, **duas corridas**: 15 min às 07:00 (solta) e 45 min às 07:30 (com 5 tiros) | o item vale para **uma** atividade por (modalidade, dia): a de **maior `duracao_s`**; empate: a de `inicio` mais cedo, depois a de menor `id`. As outras seguem para a regra de reserva. A escolhida pode ser protegida (E13): ela ainda "consome" o item | 45 min: `intervalado` (plano); 15 min: sem tipo (abaixo de `LEVE_MIN_S`, item 5) |
| E3 | Terça, duas corridas de 30 min às 07:00 e às 18:00, sem tiros | empate de duração: a mais cedo leva o plano | 07:00: `intervalado` com divergência `sem_esforco`; 18:00: `leve` por reserva |
| E4 | Segunda, natação de 2000 m | item **sem tipo** | sem tipo (natação não tem regra de reserva) |
| E5 | Domingo, corrida de 40 min sem esforço; item "corrida sem tipo" | item sem tipo **não é plano de tipo**: cai na reserva | `leve`, origem `sugestao` |
| E6 | Sexta, corrida de 40 min sem esforço; sexta não tem itens | sem item no dia: reserva | `leve`, origem `sugestao` |
| E7 | Sexta, corrida com 6 tiros de 1 km; sem item | reserva (a série de tiros) | `intervalado`, origem `sugestao`, como hoje |
| E8 | Terça de **esteira** (corrida, `subtipo = esteira`) com tiros | modalidade igual: encaixa | `intervalado` por plano; a esteira fica fora das métricas de pace da linha de base (item 7) |
| E9 | Quarta, **pedal virtual** (ciclismo, `subtipo = virtual`) | modalidade igual: encaixa | `leve` por plano |
| E10 | Sábado, **multiesporte**: pai (`multiesporte_pai`), natação, ciclismo, troca (`troca`), corrida de 20 min | pai e troca nunca recebem tipo; cada parte encaixa pela **sua** data local e pela sua modalidade | pai e troca: sem tipo; ciclismo: `moderado`; corrida: `longo` (plano); natação: sem item no sábado, sem tipo |
| E11 | Domingo 23:30 local (2026-02-09T02:30Z, `fuso_min = -180`) | usa a **data local** (ADR 0003): domingo, não segunda | encaixa o item de domingo |
| E12 | Atividade sem `fuso_min` | `America/Sao_Paulo`, como a ADR 0003 | dia local calculado por `data_local` |
| E13 | Terça com o tipo **confirmado** `fartlek` | passo 1 da precedência | continua `fartlek`; o item de terça é consumido por ela |
| E14 | Terça 2026-01-27, antes de qualquer vigência | sem plano na data; **não** olha a vigência seguinte | reserva ou nulo |
| E15 | Transição de vigência (item 8) | cada atividade usa a vigência da **sua** data | ver o exemplo do item 8 |
| E16 | Treino que cruza a meia-noite (início 23:50 local) | vale a data local do **início** | encaixa o dia do início |

**Parte de treino de transição.** O rótulo `rotulo_transicao` (ADR 0009) **não entra** na decisão do tipo: a ordem em que o rótulo e
o tipo são calculados não pode mudar o resultado. A parte recebe o tipo pelo plano como qualquer outra; o rótulo entra só na linha
de base (item 7).

### 4. Divergência: gravada como dado, sem mudar o tipo
Só para `tipo_origem = 'semana_padrao'` e só **corrida** (blocos e tiros só existem para ela com a confiança da ADR 0008). O tipo
do plano **fica**; a coluna `tipo_divergencia` guarda o motivo:

| Motivo | Quando | Exemplo |
|---|---|---|
| `sem_esforco` | o plano diz `intervalado`, e os blocos da atividade são todos `leve` (nenhum esforço pela ADR 0008) | terça de 30 min contínuos, sem esforço (E3) |
| `tem_tiros` | o plano diz `leve` ou `longo`, e a série de tiros acha intervalado (2 ou mais tiros, `tiros_1km@6`) | sábado com "longo" e 6 tiros de 1 km |

**Sem blocos gravados não é "sem esforço".** Corrida antiga pode não ter `bloco_atividade`; nesse caso a divergência `sem_esforco`
**não** é marcada (só vale com blocos gravados e todos `leve`).

Fora desses dois casos **não há divergência**: `moderado` e `fartlek` não têm critério de formato confiável na ADR 0008, e uma
duração diferente da média não contradiz `longo`. Atividade sem blocos (sem voltas) não tem divergência.

**Gravada ou calculada na leitura?** **Gravada**, escrita pelo mesmo `classificar_atividades` que escolhe o tipo (os blocos já estão
carregados ali). Motivos: é consultável em lote (Meta 10), tem a versão junto (`tipo_versao`) e a leitura de uma atividade não
precisa recarregar os blocos. O custo é a coluna a mais, que o `CHECK` do item 1 mantém coerente.

**O que a divergência faz.** Só aparece no `GET` da atividade (item 9), com texto pronto. **Não muda** o tipo, **não gera aviso** e
não é "caixa do professor" (Meta 10). Única consequência: uma atividade divergente **não entra na linha de base nem recebe uma**,
porque o tipo dela é duvidoso (item 7; "A confirmar" 2).

### 5. Regra de reserva `tipo_treino@1` (só quando o plano não dá o tipo)
Roda para a atividade elegível, não protegida, **sem tipo vindo do plano** (sem plano na data, sem item no dia, item sem tipo, ou
atividade não escolhida do dia).

| Modalidade | Regra | Tipo |
|---|---|---|
| `corrida` | 2 ou mais tiros pela série de tiros (`tiros_1km@6`, como hoje) | `intervalado` |
| `corrida` | **todos os blocos `leve`** (nenhum esforço, ADR 0008) e `duracao_s >= LONGO_MIN_S` | `longo` |
| `corrida` | todos os blocos `leve` e `LEVE_MIN_S <= duracao_s < LONGO_MIN_S` | `leve` |
| `corrida` | todos os blocos `leve` e `duracao_s < LEVE_MIN_S` | sem tipo (treino solto demais para ser referência) |
| `corrida` | tem esforço, mas não é série de tiros | sem tipo (não inventa `moderado` nem `fartlek`) |
| `corrida` sem blocos | | sem tipo |
| `ciclismo`, `natacao`, `outra` | | sem tipo |

Constantes da `tipo_treino@1`, iguais para todos os atletas (ADR 0005, item 2): `LEVE_MIN_S = 1200` (20 min) e
`LONGO_MIN_S = 4500` (75 min). São **propostas**: a calibração com o histórico real é da #269, só com números em `entregas/`.
`moderado` e `fartlek` **nunca** saem da reserva; só o plano, o professor, o TrainingPeaks ou a confirmação os dão. A `esteira`
segue a mesma tabela (o critério é "sem esforço", pelos blocos).

**Versão.** `VERSAO = "tipo_treino@1"` em `services/api/app/metricas/tipo_treino.py` (#262). **Sobe** quando mudar: a precedência;
a regra de encaixe ou a escolha da atividade do dia; as constantes `LEVE_MIN_S` e `LONGO_MIN_S`; a tabela de reserva; ou os critérios
de divergência. Subindo a versão, `worker.reclassificar` regrava as linhas de versão antiga. Mudar a versão de `tiros_1km` ou de
`esforcos` também reclassifica (é o que `reclassificar` já faz), mas **não** sobe a `tipo_treino`.

### 6. Linha de base `linha_base@1` (substituída pela `linha_base@2`, ver o adendo 2 no fim)
**Definição.** Para a sessão `S` (atleta, modalidade `M`, tipo `T`, métrica `k`), a linha de base é calculada sobre os **valores da
métrica `k` das atividades** que cumprem **todas** estas condições:
- mesmo atleta, **mesma modalidade `M` e mesmo `tipo_treino = T`** (qualquer origem; tipos e modalidades diferentes nunca se misturam);
- **anteriores à sessão**: `inicio < inicio de S` e data local dentro de **56 dias (8 semanas) antes da data local de S**, inclusive
  o primeiro dia. Ex.: sessão em 2026-03-10, janela de 2026-01-13 a 2026-03-10. **A sessão nunca entra na própria linha de base**;
- elegíveis (item 2), **não divergentes** (item 4) e **fora de treino de transição** (`rotulo_transicao.transicao = true`);
- com **valor** para `k` (cada métrica conta os seus treinos; uma atividade sem FC não conta na linha da FC, mas conta na do pace).

**Estados** (por métrica):
- `aprendendo`: menos de **8** valores (`MINIMO_TREINOS = 8`). A resposta traz o valor da sessão, `n` e o mínimo; **não traz** mediana
  nem desvio (não se mostra precisão que não existe). Sem valores de literatura e sem combinação ponderada.
- `dentro`: 8 ou mais valores e `|z| < LIMITE_FORA`.
- `fora`: 8 ou mais valores e `|z| >= LIMITE_FORA`.
- `sem_valor`: a sessão não tem a métrica (ex.: sem FC); explica o motivo.

**Medida robusta: mediana e MAD.** Com os valores `x_1..x_n` da janela:
```
mediana = mediana(x)
MAD     = mediana(|x_i - mediana|)
desvio  = max(1,4826 x MAD, PISO_REL x |mediana|)         PISO_REL = 0,02
z       = (valor_da_sessao - mediana) / desvio
```
O fator 1,4826 torna o MAD comparável ao desvio padrão numa distribuição normal. O **piso de 2% da mediana** evita dividir por zero
quando os valores são todos iguais e evita chamar de "fora" uma diferença menor que o ruído da medida; é proposta do Caio e vai
para a calibração da #269. Fontes (a conferir, ver "Fontes"): Leys et al. (2013) para mediana e MAD no lugar de média e desvio
padrão; Hampel (1974) e Rousseeuw e Croux (1993) para a constante 1,4826.

**Limite "fora do normal": `LIMITE_FORA = 2,5`.** Leys et al. chamam 2,5 de limite "moderadamente conservador" (2 deixa passar muito
falso positivo e 3 é "muito conservador"). Com 8 treinos no mínimo, um limite mais baixo marcaria quase todo mês um treino como
"fora". **Proposta para o Angelo** ("A confirmar" 3). Abaixo de 2,5 em módulo, o texto não é de alerta, é só a comparação.

**Textos prontos** (a API formata, o app mostra; ADR 0004, adendo 2). Sem juízo de valor: a linha de base compara com o histórico
do atleta, não diz se o treino foi bom.
- **Aprendendo:** `Ainda aprendendo o seu normal em treino {tipo}: {n} de 8 treinos nas últimas 8 semanas.`
- **Dentro:** `{Rótulo} dentro do seu normal para treino {tipo}: {valor}, perto da mediana de {mediana} ({n} treinos nas últimas 8 semanas).`
- **Fora:** `{Rótulo} fora do seu normal para treino {tipo}: {valor}, {diferença} {mais rápido|mais lento|acima|abaixo|maior|menor} que a mediana de {mediana} ({n} treinos nas últimas 8 semanas). Isto compara com o seu histórico; não diz se o treino foi bom ou ruim.`
- **Sem valor:** `Sem {rótulo em minúsculas} neste treino: {motivo}.`
- **Sem linha de base** (nível da atividade): `Sem linha de base: {motivo}.`, com motivos em palavras (ex.: "o treino não tem tipo", "treino
  com formato diferente do plano", "parte de treino de transição").

**Calculada na leitura, não gravada.** Mesma decisão da ADR 0010 para CTL e ATL. A linha de base de uma sessão muda quando chega
treino novo, quando um tipo é confirmado, quando a semana-padrão muda ou quando uma regra sobe de versão; gravá-la criaria uma cópia
a invalidar em todos esses casos. O custo é pequeno: uma consulta das atividades do atleta, da modalidade e do tipo nos 56 dias
anteriores (da ordem de dezenas de linhas), mais as cargas e, para o intervalado, os blocos delas. Se o custo virar problema, grava-se
depois como cache sem mudar o contrato. A resposta traz `versao = "linha_base@1"`.

**Exemplo à mão (pace médio do `leve`, 8 treinos na janela, s/km).** Valores: 330, 324, 336, 330, 342, 318, 330, 336.
Ordenados: 318, 324, 330, 330, 330, 336, 336, 342; **mediana = (330 + 330) / 2 = 330**. Desvios absolutos: 12, 6, 0, 0, 0, 6, 6, 12;
ordenados: 0, 0, 0, 6, 6, 6, 12, 12; **MAD = (6 + 6) / 2 = 6**. `desvio = max(1,4826 x 6 = 8,8956; 0,02 x 330 = 6,6) = 8,8956`.
- Sessão a 306 s/km: `z = (306 - 330) / 8,8956 = -2,698`; `|z| >= 2,5`: **fora**, "24 s/km mais rápido" que a mediana de 5:30/km.
- Sessão a 318 s/km: `z = -12 / 8,8956 = -1,349`: **dentro**.
- Com 7 valores (retirado o 342): **aprendendo**, `n = 7`.
- Piso: se os 8 valores fossem todos 330, `MAD = 0` e `desvio = 6,6`; a sessão a 340 dá `z = 10 / 6,6 = 1,515`: dentro.

**Consequência a registrar.** Janela de 8 semanas com mínimo de 8 treinos pede **pelo menos um treino do tipo por semana**. Um tipo feito
a cada duas semanas (um `fartlek` quinzenal, por exemplo) fica em "ainda aprendendo" para sempre. É a decisão de 09/11; uma janela
maior para o tipo raro seria `linha_base@2` ("A confirmar" 4).

**Versão.** `VERSAO = "linha_base@1"` em `services/api/app/metricas/linha_base.py` (#263). **Sobe** quando mudar: a janela
(`JANELA_DIAS = 56`); `MINIMO_TREINOS`; a medida (mediana, MAD, constante, `PISO_REL`); `LIMITE_FORA`; a lista de condições de
entrada; ou a lista de métricas por modalidade e tipo.

### 7. Métricas por modalidade e tipo (`linha_base@1`; a `@2` troca `carga` por `carga_hora`, ver o adendo 2)
A linha de base é por **métrica**, e cada atividade com tipo mostra as métricas do seu tipo.

| Modalidade | Tipo | Métricas | De onde vêm |
|---|---|---|---|
| corrida | `intervalado` | `melhor_pace` (s/km), `fc_melhor_tiro` (bpm), `carga` | melhor tiro da série `tiros_1km@6` (`melhor_pace_s_km`, `melhor_fc_media`); `carga@2` |
| corrida | `leve`, `longo`, `moderado` | `pace_medio` (s/km), `fc_media` (bpm), `carga` | `duracao_s / distancia_m x 1000`; `atividade.fc_media`; `carga@2` |
| corrida | `fartlek` | `fc_media`, `carga` | o pace médio de um fartlek mistura esforço e trote e muda com a estrutura do dia, então não é referência |
| ciclismo | todos | `fc_media`, `carga` | `atividade.fc_media`; `carga@2` (hrTSS) |
| natação | todos | `fc_media` | `atividade.fc_media`; **sem carga** (a `carga@2` é `modalidade_sem_carga`) |
| outra | | nenhuma | |

**Regras.**
- `melhor_pace` e `fc_melhor_tiro` valem só para a sessão com tiros pela série (a divergência `sem_esforco` já a exclui); sem tiros, a
  métrica fica `sem_valor` com o motivo `sem_tiros`. Se o melhor tiro não tem FC, `fc_melhor_tiro` fica `sem_valor` (não troca de tiro,
  como o `PontoSessao`).
- **`esteira` não entra nas métricas de pace** (`pace_medio`, `melhor_pace`): a distância vem do sensor do aparelho (decisão do Angelo
  na #51 e ADR 0010); a FC e a carga seguem. O `sem_valor` traz o motivo `esteira`.
- **Ciclismo sem velocidade média e natação sem pace por 100 m ficam fora da `linha_base@1`.** Motivos: a velocidade média do pedal
  depende de terreno, vento e do pedal virtual, e entra com a potência (fora do MVP); o pace na natação mistura piscina e águas
  abertas e não há detecção de séries de natação ainda. A natação fica com a FC média; se ela faltar, o `sem_valor` explica.
- `carga` existe só com `carga_atividade.estado = 'calculada'`; sem ela, a métrica fica `sem_valor` com o motivo da `carga@2`
  (ex.: `sem_dados_saude`).
- Ciclismo e natação só têm linha de base se o **plano** deu o tipo (a reserva não tipa essas modalidades); o item sem tipo (natação do
  exemplo) deixa a atividade **sem linha de base**.

**Atividade sem linha de base** (nível da atividade, `estado = sem_linha_base`, sempre com `motivo`):

| Motivo | Quando |
|---|---|
| `sem_tipo` | a atividade não tem `tipo_treino` |
| `modalidade_sem_metricas` | modalidade `outra` |
| `divergente` | tem `tipo_divergencia` |
| `transicao` | é parte de treino de transição (`rotulo_transicao.transicao = true`) |
| `multiesporte` | `subtipo` em (`multiesporte_pai`, `troca`) |

Quando mais de um motivo vale, aparece o primeiro desta ordem: `multiesporte`, `modalidade_sem_metricas`, `sem_tipo`, `divergente`, `transicao`.

### 8. Mudança da semana-padrão e reaplicação
Gravar uma vigência (`PUT`, item 9) faz:
1. grava `semana_padrao` e os itens da vigência `vigente_desde` (cria ou substitui) numa transação;
2. **reaplica o tipo** nas atividades do atleta com **data local >= `vigente_desde`**, rodando a `tipo_treino@1` por dia. Atividades
   anteriores a `vigente_desde` **não são lidas nem regravadas**. Atividades que já usam uma vigência **mais nova** que a editada
   voltam ao mesmo resultado (idempotência);
3. não toca tipo confirmado, `professor` nem `trainingpeaks` (item 2, passo 1);
4. não roda `detectar_esforcos`: usa os blocos já gravados (a reaplicação é leve, sem recalcular esforços);
5. devolve `atividades_reaplicadas` (quantas mudaram de tipo, origem ou divergência).

**Detalhes de implementação (revisão da Duda, #264 e #265).**
- A data local sai de `inicio` e `atividade.fuso_min`: filtra-se no SQL por `inicio >= vigente_desde - 1 dia` e confere-se a data
  local em Python. A faixa pode ser limitada a `[vigente_desde, próxima vigência)`; é só otimização.
- Reaplicar sem mudança **não toca a linha**.
- Se a reaplicação falhar, o `PUT` inteiro faz **rollback** (a vigência também não fica gravada).
- Dois `PUT` concorrentes da mesma vigência (clique duplo): o upsert trata a violação do `UNIQUE (atleta_id, vigente_desde)` e repete
  como atualização.

**Mesmo resultado em qualquer caminho.** Importação, upload de FIT, `worker.reclassificar` e o `PUT` chamam a **mesma** função; a
diferença é só o intervalo de datas e se os esforços são detectados antes.

**Exemplo (E15).** Vigência A desde 2026-02-02 (terça `intervalado`) e vigência B desde 2026-03-02 (terça `fartlek`). Terça
2026-02-24 usa A: `intervalado`. Terça 2026-03-03 usa B: `fartlek`. Terça 2026-01-27 não tem plano: reserva ou nulo. Se o atleta grava B
em 2026-03-10, só as atividades com data local de 2026-03-02 em diante são reaplicadas; a terça de 2026-02-24 não é tocada.

### 9. Contrato da API (esboço; os detalhes saem em #264 e #266, com cliente regerado e adendo da ADR 0004)
**`GET /atletas/{atleta_id}/semana-padrao?em=AAAA-MM-DD`** devolve a semana **vigente em `em`** (padrão: hoje, data local de
`America/Sao_Paulo`) e o histórico de vigências. `404` para atleta inexistente. `vigente` é `null` só quando nenhuma vigência começou até `em`; uma vigência com `itens: []` volta como objeto com `itens: []`, mantendo quem definiu e quando.
```json
{
  "atleta_id": 1,
  "em": "2026-03-10",
  "vigente": {
    "vigente_desde": "2026-03-02",
    "definido_por": "atleta",
    "definido_em": "2026-03-01T21:10:00-03:00",
    "itens": [
      {"dia_semana": 1, "dia_semana_texto": "segunda", "modalidade": "natacao", "tipo_treino": null},
      {"dia_semana": 2, "dia_semana_texto": "terça", "modalidade": "corrida", "tipo_treino": "fartlek"}
    ]
  },
  "vigencias": [
    {"vigente_desde": "2026-03-02", "definido_por": "atleta", "total_itens": 2},
    {"vigente_desde": "2026-02-02", "definido_por": "atleta", "total_itens": 7}
  ]
}
```
Itens em ordem de dia e modalidade. `vigencias` em ordem decrescente.

**`PUT /atletas/{atleta_id}/semana-padrao`** cria ou substitui a vigência `vigente_desde`:
```json
{
  "vigente_desde": "2026-03-02",
  "definido_por": "atleta",
  "itens": [
    {"dia_semana": 2, "modalidade": "corrida", "tipo_treino": "fartlek"},
    {"dia_semana": 1, "modalidade": "natacao", "tipo_treino": null}
  ]
}
```
Resposta `200` com o mesmo objeto de `vigente` mais `"atividades_reaplicadas": 3`. `itens: []` é válido (encerra o plano). `422` para
`dia_semana` fora de 1 a 7, `modalidade` fora de `corrida`/`natacao`/`ciclismo`, `tipo_treino` fora dos cinco valores, `definido_por`
fora de `atleta`/`professor` ou **ausente**, `vigente_desde` inválido ou ausente, `itens` ausente, ou duas vezes o mesmo (`dia_semana`, `modalidade`). `404` para atleta
inexistente. `vigente_desde` no futuro é aceito (nenhuma atividade muda até a data). Não há `DELETE` nesta versão: reenviar
com `itens: []` faz o mesmo efeito.

**`GET /atletas/{atleta_id}/atividades/{atividade_id}`** ganha, sem remover campo (adendo da ADR 0004, #266):
- `tipo_origem` aceita também `semana_padrao`;
- `tipo_divergencia`: `null` ou `{"motivo": "sem_esforco", "texto": "O plano diz intervalado, mas o treino não teve esforço detectado."}` /
  `{"motivo": "tem_tiros", "texto": "O plano diz leve, mas o treino teve 6 tiros de 1 km."}`;
- `linha_base`:
```json
{
  "versao": "linha_base@1",
  "estado": "ok",
  "motivo": null,
  "modalidade": "corrida",
  "tipo_treino": "leve",
  "janela_semanas": 8,
  "minimo_treinos": 8,
  "metricas": [
    {
      "chave": "pace_medio",
      "rotulo": "Pace médio",
      "unidade": "s/km",
      "estado": "fora",
      "valor": 306.0,
      "valor_texto": "5:06/km",
      "mediana": 330.0,
      "mediana_texto": "5:30/km",
      "desvio": 8.9,
      "z": -2.7,
      "n": 8,
      "diferenca_texto": "24 s/km mais rápido",
      "texto": "Pace médio fora do seu normal para treino leve: 5:06/km, 24 s/km mais rápido que a mediana de 5:30/km (8 treinos nas últimas 8 semanas). Isto compara com o seu histórico; não diz se o treino foi bom ou ruim."
    },
    {
      "chave": "fc_media", "rotulo": "FC média", "unidade": "bpm", "estado": "aprendendo",
      "valor": 148.0, "valor_texto": "148 bpm", "mediana": null, "mediana_texto": null,
      "desvio": null, "z": null, "n": 5, "diferenca_texto": null,
      "texto": "Ainda aprendendo o seu normal em treino leve: 5 de 8 treinos nas últimas 8 semanas."
    }
  ]
}
```
**Custo da `linha_base`.** Uma consulta agregada por atleta, modalidade e tipo na janela de 56 dias (nunca mistura atletas), com
limite natural de dezenas de linhas; cargas e blocos só dessas atividades. Cliente regerado e teste de contrato rodam na #266.

`estado` da `linha_base`: `ok` (tem ao menos uma métrica) ou `sem_linha_base` (com `motivo` do item 7 e `metricas: []`). Os números
brutos (`valor`, `mediana`, `desvio`, `z`) são para o app ordenar e para o motor de explicação (Meta 9); o texto é só da API. Os valores
são sempre calculados por código, nunca por modelo de linguagem.

### 10. Sem login de professor: como a tela grava `definido_por`
Hoje não há login. Proposta: a tela mostra um campo **"Quem definiu"** com `Eu (atleta)` e `Treinador`, **pré-selecionado em "atleta"**,
e a API exige `definido_por` no corpo. É um rótulo **declarado**, não verificado, e não dá permissão a ninguém. "A confirmar" 1.

### 11. Por onde segue
- **#261 (Caio, à mão):** fixtures de 10 a 12 semanas com semana-padrão que muda de vigência, e o oráculo dos casos E1 a E16 e do exemplo do item 6.
- **#262 (Caio):** `tipo_treino@1` como função pura, nota em `docs/metricas/`.
- **#263 (Caio):** `linha_base@1` como função pura, nota em `docs/metricas/`.
- **#264 (Duda):** migração `0011`, modelos, `GET` e `PUT` da semana-padrão, adendo da ADR 0004, cliente regerado.
- **#265 (Duda):** `classificar_atividades` com a precedência do item 2, `tipo_versao`, `tipo_divergencia` e a reaplicação do item 8.
- **#266 (Duda):** `linha_base` e `tipo_divergencia` no `GET` da atividade.
- **#267 (Lia):** desenho da tela, com o campo "Quem definiu" e a data de vigência.

## Alternativas consideradas
- **Semana-padrão em uma tabela só, com `vigente_desde` e `definido_por` repetidos em cada item.** Mais simples, mas não representa a
  vigência vazia ("sem plano daqui em diante") e repete o dado do cabeçalho. Descartada.
- **Semana-padrão como JSON numa coluna.** Perde `CHECK`, `UNIQUE` e consulta. Fora do padrão do projeto (ADR 0010, item 5).
- **Tipo e divergência em tabela própria (como o rótulo de transição, ADR 0009).** O tipo já está em `atividade`; separar a
  divergência do tipo obriga a juntar duas tabelas em toda leitura. Descartada (item 1).
- **Calcular a divergência na leitura.** Exige recarregar blocos a cada `GET` e impede a consulta em lote da Meta 10. Descartada.
- **Linha de base gravada.** Teria de ser invalidada a cada treino novo, tipo confirmado ou semana-padrão nova. Descartada (item 6).
- **Média e desvio padrão no lugar de mediana e MAD.** Um único treino fora do comum (doença, prova) desloca média e desvio, e a
  janela tem poucos pontos (8). Descartada.
- **Dar o tipo do plano a todas as atividades da mesma modalidade no dia.** O aquecimento solto em atividade separada entraria na linha de
  base do `intervalado`. Descartada (item 3, E2).
- **Item sem tipo bloqueia a reserva.** Deixaria corrida em dia "sem tipo" sempre sem tipo, mesmo com o formato dizendo `leve`. Descartada (E5).
- **Valores de literatura no início frio.** Fora, decisão do Angelo de 09/11.

## Consequências
- O tipo de treino passa a vir do **plano** quando existe; a corrida sem plano mantém o comportamento de hoje (`intervalado` por
  tiros) e ganha `leve` e `longo` como sugestão.
- A série de tiros e a carga **não mudam**: nenhuma `VERSAO` existente sobe. A série de tiros não lê `tipo_treino`. Regressão em teste.
- `tipo_origem` ganha um valor; consumidores que listam as origens (API, cliente regerado) precisam aceitar `semana_padrao`.
- O atleta que não cadastra semana-padrão ainda tem linha de base para corrida `leve`, `longo` e `intervalado` pela reserva; para
  bike e natação, só com plano.
- A linha de base de tipos feitos menos de uma vez por semana fica "aprendendo" (item 6).
- A migração `0011` é aditiva e reversível; o `downgrade` apaga o que é derivado e reaplicável.

## Limitações
- Um item por modalidade por dia: dois treinos da mesma modalidade com tipos diferentes no mesmo dia não cabem no plano.
- A divergência cobre só `intervalado` sem esforço e `leve`/`longo` com tiros, só em corrida.
- `LEVE_MIN_S`, `LONGO_MIN_S` e `PISO_REL` são constantes únicas para todos os atletas, ainda sem calibração.
- Treino de transição não entra na linha de base; quem faz brick toda semana não terá linha de base para essas partes até uma `linha_base@2`.
- `definido_por` não é verificado.

## Fontes
Citações **ainda não conferidas nos textos**; o Caio abre cada uma antes de a nota da métrica citá-la (mesma pendência da ADR 0008, item 7 de "A confirmar"):
- Leys, C., Ley, C., Klein, O., Bernard, P. e Licata, L. (2013). *Detecting outliers: do not use standard deviation around the mean, use
  absolute deviation around the median.* Journal of Experimental Social Psychology, 49(4), 764-766. Base da mediana e do MAD e dos
  limites 2, 2,5 e 3.
- Hampel, F. R. (1974). *The influence curve and its role in robust estimation.* Journal of the American Statistical Association, 69(346), 383-393. Origem do MAD como medida robusta.
- Rousseeuw, P. J. e Croux, C. (1993). *Alternatives to the median absolute deviation.* Journal of the American Statistical Association,
  88(424), 1273-1283. A constante 1,4826 como fator de consistência com o desvio padrão normal.
- Regra própria do projeto, sem artigo: janela de 8 semanas e mínimo de 8 treinos (decisão do Angelo, 09/11), `PISO_REL`, `LEVE_MIN_S` e `LONGO_MIN_S`.

## A confirmar (respondido em 09/11)
O Angelo aceitou os sete padrões abaixo em 09/11 ("ok para as sete"). Eles valem como decisão.

1. **`definido_por` sem login.** A tela pergunta "Quem definiu" (atleta ou treinador) ou grava sempre "atleta"?
   **Padrão:** a tela pergunta, com "atleta" já marcado. O rótulo é declarado, não dá permissão a ninguém.
2. **O plano vence quando contradiz o treino?** Plano diz `intervalado` e o treino não teve esforço (ou plano diz `leve` e teve tiros).
   **Padrão:** o plano vence (o tipo fica o do plano), o treino fica marcado como divergente e **não entra na linha de base** de ninguém
   (nem recebe uma), porque o tipo dele é duvidoso. A alternativa é o formato vencer e o tipo ser o que a regra achar.
3. **Limite "fora do normal" e o texto do aviso (item 6).** **Padrão:** `|z| >= 2,5` (mediana e MAD, piso de 2%) e os textos do item 6, sem
   juízo de valor ("compara com o seu histórico; não diz se o treino foi bom ou ruim").
4. **Tipo feito menos de uma vez por semana.** *(Substituído pelo adendo 2: janela de 12 semanas na `linha_base@2`.)* Com 8 semanas e mínimo de 8 treinos, um tipo quinzenal fica sempre "ainda aprendendo".
   **Padrão:** manter a regra de 09/11 e olhar os números reais na #269 antes de propor outra janela para o tipo raro.
5. **Parte de treino de transição na linha de base.** *(Substituído pelo adendo 2: base própria na `linha_base@2`.)* **Padrão:** fica fora da linha de base e não recebe uma (motivo `transicao`),
   para não misturar a corrida pós-pedal com a corrida isolada.
6. **Dois treinos da mesma modalidade no dia.** **Padrão:** o plano vale para o de **maior duração**; o outro cai na regra de reserva.
7. **`PUT` da semana-padrão sem autenticação.** Hoje não há login, então qualquer cliente da API reescreve o tipo das atividades do
   atleta inteiro a partir de `vigente_desde`. **Padrão:** aceitar no piloto local (a API não é exposta); exigir identidade quando
   houver login (Meta 10).

Calibração que **não** precisa do Angelo: `LEVE_MIN_S`, `LONGO_MIN_S` e `PISO_REL` (Caio, na #269, números só em `entregas/`).

## Data e quem decidiu
2026-11-09. Proposta do Caio (ciência), com revisão da Duda (modelo de dados e API) pedida no PR. Decisões de produto do Angelo e do
Theo de 09/11 listadas no Contexto. Issue #260. Modelo de dados aprovado pelo Theo (PR #277, 09/11); "A confirmar" respondido pelo
Angelo em 09/11 com os sete padrões.

## Adendo 2 (2026-11-09): `linha_base@2` (issue #288)
**Status: decidido pelo Angelo em 09/11 ("ok para as quatro").** Sobe `linha_base@1` para `linha_base@2`. A `tipo_treino@1`, o modelo de dados e
a semana-padrão **não mudam**. Substitui os itens 4 e 5 do "A confirmar" e muda os itens 6 e 7.

1. **Janela de 84 dias (12 semanas), mínimo de 8 treinos mantido** (`JANELA_DIAS = 84`). Com 56 dias a regra pede 8 treinos de 8 semanas
   seguidas: um treino perdido manda o tipo semanal de volta a "ainda aprendendo" por 8 semanas. Com 84 dias há folga para uma ou mais
   faltas. Tipos quinzenais ou mais raros seguem perto de "aprendendo" (limitação aceita).
2. **Parte de treino de transição tem base própria.** A parte (`rotulo_transicao.transicao = true`) compara só com **outras partes de
   transição da mesma modalidade e do mesmo tipo**; a atividade isolada compara só com isoladas. O motivo `transicao` de "sem linha de
   base" **deixa de existir**; sem parte anterior, a métrica fica `aprendendo` com `n = 0`. Nos textos o tipo aparece como
   "treino moderado (parte de transição)". Ordem dos motivos de "sem linha de base": `multiesporte`, `modalidade_sem_metricas`,
   `sem_tipo`, `divergente`. O parâmetro `TRANSICAO_FORA_DA_BASE` some; entra a regra fixa da base própria.
3. **`carga` vira `carga_hora`** (carga da atividade, `carga@2`, dividida pelas horas de `duracao_s`). A carga absoluta cresce com a duração e
   acaba medindo volume; por hora ela mede intensidade. Chave `carga_hora`, rótulo "Carga por hora", unidade `pontos/h`, textos
   "55,0 pontos/h" e diferença "13,0 pontos/h maior". `sem_duracao` é o novo motivo de métrica sem valor.
4. **Intervalado sem série de 1 km.** O melhor esforço curto (por faixa de distância) **fica fora**: limitação registrada. Sem série de 1 km,
   `melhor_pace` e `fc_melhor_tiro` ficam `sem_valor` com `sem_tiros`, e o intervalado passa a ter também a **FC média** da atividade
   (`fc_media`) e a `carga_hora`.

**Métricas da `linha_base@2`.** Corrida `intervalado`: `melhor_pace`, `fc_melhor_tiro`, `fc_media`, `carga_hora`; `leve`, `longo`, `moderado`:
`pace_medio`, `fc_media`, `carga_hora`; `fartlek`: `fc_media`, `carga_hora`. Ciclismo: `fc_media`, `carga_hora`. Natação: `fc_media`. O resto do
item 7 (esteira fora do pace, motivos de métrica sem valor) vale como está.

**Contrato (adendo 7 da ADR 0004).** `MetricaBaseOut.chave`: `carga` sai e `carga_hora` entra; `unidade`: `pontos` sai e `pontos/h` entra;
`LinhaBaseOut.motivo` perde `transicao`; `janela_semanas` passa a 12 e `versao` a `linha_base@2`. O app ainda não lê o objeto `linha_base`.
Cliente regerado.

**Efeito nos dados.** Nada é gravado: a linha de base é calculada na leitura, então a `@2` vale na hora.

