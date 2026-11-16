---
tipo: decisao
status: proposta
dono: caio
atualizado: 2026-11-16
links: [[decisoes/0001-modelo-de-dados-minimo]], [[decisoes/0003-fuso-da-atividade]], [[decisoes/0004-contrato-tela-evolucao]], [[decisoes/0011-linha-de-base-e-semana-padrao]], [[decisoes/0012-check-in-pos-treino]], [[decisoes/0013-feedback-automatico]], [[decisoes/0014-recuperacao-diaria]], [[metricas/linha-base]], [[modulos/banco]], [[modulos/api]], [[produto/roadmap]], [[produto/plano-mvp-execucao]], [[glossario]]
---
# ADR: 0015 Caixa do dia do professor no piloto local (identidade, vínculo, `atencao@1` e correção do tipo)

> **Proposta** (issue #419, Meta 11), para o Theo aprovar o **modelo de dados** (item 1) antes de qualquer migração, com a revisão da Duda sobre banco e API.
> As dez decisões do Angelo de 16/11 ("ok para as 10") estão no Contexto e esta ADR as respeita. **Nenhuma linha de código nem migração muda neste PR.**
> Todos os nomes, números, datas e textos são **sintéticos** (atletas fictícios). Esta ADR não consultou conta nem banco de ninguém.
> Check-in, observação, feedback e recuperação são dado pessoal e de saúde: nada disso, real, no repositório, em log, em captura ou em fixture gravada.
> Dá base para #420 (desenho), #421 (fixtures e oráculo), #422 (`atencao@1`), #423 (professor por configuração e filtro), #424 (`GET`), #425 (`PUT` em lote) e #431 (conferência local).

## Contexto
O MVP é vendido pela assessoria com o professor no meio ([[produto/plano-mvp-execucao]], seções 1 e 5.1) e a hipótese a validar é que o professor gasta menos tempo por aluno com o contexto pronto. Até a Meta 10 tudo era do atleta. A Meta 11 abre a **caixa do dia**: os alunos do professor ordenados por "precisa de atenção", com o motivo em uma linha, e os treinos novos com o tipo sugerido, que ele confirma ou corrige em lote.

Princípio que organiza tudo, o mesmo das ADRs 0010 a 0014: **quem calcula é o código**. A caixa não tem texto de IA: os motivos saem de uma função pura, com frases montadas por regra a partir do que o código já calcula (nenhum número novo), e **sem afirmar causa**.

### Decisões do Angelo (16/11, "ok para as 10"), que esta ADR respeita
1. Abrir as issues e começar a Meta 11 (P1 a P14).
2. **Sem login** nesta meta: o professor do piloto local é **fixo por configuração**, como o atleta fixo da Meta 2. Login, contas e controle de acesso vêm com a meta de deploy.
3. **Só atletas sintéticos** (fictícios, escritos à mão). Nenhum dado de outro aluno real até o termo de consentimento, o contrato com a assessoria e a consulta de LGPD.
4. Atleta **sem vínculo** com o professor, ou com vínculo **sem `consentimento_em`**, **nunca** aparece na caixa nem nos treinos dele. O texto do termo fica para a consulta jurídica.
5. A conta do Angelo pode ser ligada a um professor de teste **só no banco local**, com nada no repositório (#431).
6. `atencao@1` com **quatro motivos**: treino que diverge da semana-padrão; treino fora do normal na linha de base; atalho "dor" no check-in; treino sem check-in perto do fim do prazo de 7 dias. **Fora:** recuperação abaixo do normal e motivo de falta.
7. O professor vê tipo, PSE, sensação, atalhos, feedback e a **observação livre**. A observação **nunca** vai ao provedor de LLM. Rever na consulta de LGPD antes do primeiro aluno real.
8. A **correção do professor vence** a sugestão e a semana-padrão e **não é desfeita** pela reimportação nem por versão nova da regra. Confirmar sem mudar só marca o tipo como confirmado.
9. **Fora:** rascunho de devolutiva, revisão de amostra do feedback, feedback com o nome do professor, semana-padrão por grupo, ficha completa do aluno.
10. Celular de verdade amarrado ao ensaio com professor e atletas (plano, seção 9), fora desta meta.

### O que o código do `main` mostra (conferido em 16/11, commit `3c75a17`)
- A última migração é a `0015_feedback_clima_visto`; a próxima é a **`0016`**, **se esta ADR pedir**.
- `professor` (`id`, `assessoria_id` obrigatório, `nome`) e `vinculo_professor_atleta` (**chave composta** `(professor_id, atleta_id)` e `consentimento_em` anulável) existem desde a ADR 0001. Nenhuma rota, serviço ou teste os usa hoje (só o modelo).
- `atividade` tem `tipo_treino`, `tipo_origem` (`sugestao`, `professor`, `trainingpeaks`, `semana_padrao`), `tipo_confirmado` (padrão falso), `tipo_versao` e `tipo_divergencia`. O `CHECK tipo_divergencia_origem` só deixa a divergência existir com `tipo_origem = 'semana_padrao'`.
- **A proteção que a decisão 8 pede já existe no código:** `servicos/tipo_treino.aplicar_tipos` pula a atividade com `tipo_confirmado` ou origem em `ORIGENS_PROTEGIDAS = {professor, trainingpeaks}` ("nunca muda, nem a versão"). A reimportação (`ingestao/importacao.py`) atualiza a linha **no lugar** (o `id` não muda) e não escreve nenhum dos campos de tipo. O que **falta** é quem escreva `tipo_origem = 'professor'` (hoje ninguém escreve) e a regra do que acontece em volta (itens 5 e 6).
- Nada no `main` escreve `tipo_confirmado`: a coluna só é lida.
- O check-in: prazo de **7 dias** (`PRAZO_DIAS`, `no_prazo`, `dias_ate_hoje`) com "hoje" em `America/Sao_Paulo`; `checkin.elegivel` exclui `multiesporte_pai` e `troca`; o atalho `dor` é booleano; `texto` é a observação livre.
- A linha de base (`linha_base@2`) devolve por métrica `estado` (`fora`, `dentro`, `aprendendo`, `sem_valor`) e o `z` assinado, com limite de 2,5. Já existe cálculo por treino na leitura (`servicos/linha_base_leitura.py`), com as chaves `pace_medio`, `melhor_pace`, `fc_media`, `fc_melhor_tiro` e `carga_hora`.
- O feedback fica **desatualizado** só por `checkin`, `versao`, `noite` e `clima` (`servicos/feedback.motivos_desatualizado`). **Mudar o tipo do treino não desatualiza o feedback**, e o pacote de fatos leva `tipo_treino` e a linha de base daquele tipo. Isso vira um buraco real com a correção do professor (item 6).
- `Settings` (`app/config.py`) lê o `.env` da raiz; não há variável de professor nem de atleta fixo (o atleta é sempre o `atleta_id` da rota).

## Exemplos sintéticos de linha de motivo (para o Angelo ler)
Atletas fictícios. Hoje é quinta; a data local manda o nome do dia (ADR 0003). **Um motivo por linha**, sem causa, sem conselho, sem diagnóstico.

| Motivo (`codigo`) | Linha de exemplo |
|---|---|
| `dor` | Treino de terça com dor marcada no check-in. |
| `fora_do_normal` | Treino de terça fora do normal: FC média acima do habitual. |
| `fora_do_normal` (mais de uma medida) | Treino de quarta fora do normal: pace médio mais lento e FC média acima do habitual. |
| `divergencia` | Treino de terça diferente da semana-padrão: previsto intervalado, sem esforço detectado. |
| `divergencia` | Treino de sábado diferente da semana-padrão: previsto longo, com tiros detectados. |
| `checkin_vencendo` | Treino de segunda sem check-in; o prazo termina em 2 dias. |
| `checkin_vencendo` | Treino de quarta sem check-in; o prazo termina hoje. |

Um treino com dois motivos aparece com **duas linhas**, na ordem fixa do item 3 (não uma frase colada):

> **Atleta Exemplo B** · terça
> - Treino de terça com dor marcada no check-in.
> - Treino de terça fora do normal: FC média acima do habitual.

## Decisão

### 1. Modelo de dados (para aprovação do Theo)
**Princípio: a atenção não é guardada.** A lista de atenção é **calculada a cada leitura** a partir do que já está no banco (ver a tabela do item 4). Não há tabela de caixa, de "visto" nem de motivo: o que está guardado não pode ficar velho. O preço é que "dispensar um aviso" não existe (ver "A confirmar", item 6).

**O que já existe e basta:** `professor`, `vinculo_professor_atleta.consentimento_em` (consentido = **não nulo e `<= agora`**), `atividade.tipo_origem = 'professor'` e `tipo_confirmado`. **Revogar** o consentimento é pôr `consentimento_em` de volta em nulo (a linha do vínculo fica); o atleta some da caixa na leitura seguinte, sem apagar nada do atleta.

**O que esta ADR propõe mudar: uma migração `0016`, só aditiva** (colunas anuláveis, nenhuma linha existente muda):

| Onde | Coluna | Tipo | Para quê |
|---|---|---|---|
| `atividade` | `tipo_confirmado_por` | FK `professor.id`, `ON DELETE SET NULL`, anulável | quem confirmou ou corrigiu o tipo. **Constraint nomeada `fk_atividade_tipo_confirmado_por`** (no SQLite o `downgrade` só remove a coluna com FK nomeada). Cumpre o que a ADR 0011 prometeu ("quando houver professor, entra `professor_id` anulável numa migração própria"). Nulo em tudo que já existe |
| `atividade` | `tipo_confirmado_em` | datetime com fuso, anulável, **definido pela aplicação** (sem `server_default`) | quando; é a ordem de quem confirmou por último e a base de auditoria |
| `feedback_treino` | `tipo_visto` | texto (20), anulável | o tipo que o pacote de fatos viu na geração (`sem_tipo` quando não havia). **Nulo** = linha anterior à `0016`, que **não compara** (mesmo desenho do `clima_visto` da `0015`). Faz o feedback ficar desatualizado quando o professor muda o tipo (item 4) |

Sem `CHECK` novo: `tipo_confirmado = verdadeiro` com `_por` e `_em` nulos é **legal** (é o que sobra depois de `SET NULL` em `_por`). **`ON DELETE SET NULL` é escolha consciente:** perde o "quem" se o professor for apagado (`RESTRICT` o preservaria); nenhuma rota apaga professor hoje. **Teste do `SET NULL`:** liga `PRAGMA foreign_keys` no SQLite e roda também no Postgres (`TEST_DATABASE_URL`). `downgrade`: remove as três colunas. Não vira obrigatória nenhuma coluna existente. **Alternativa sem migração:** não guardar quem nem quando (só `tipo_origem = 'professor'`) e aceitar o feedback velho depois da correção; o custo é a incoerência visível (o feedback diz "dos treinos leves" e o treino virou longo). Ver "A confirmar", itens 3 e 4; a recomendação é a migração.

**Fora do modelo:** nome do professor no feedback (decisão 9), tabela de grupo, tabela de login.

### 2. Identidade do professor no piloto local
- **Variável `PROFESSOR_ID`** no `.env` local (inteiro, **sem valor padrão**), lida por `Settings` como `professor_id: int | None`. É o professor que o piloto "é". Não existe `.env` com valor no repositório; o `.env.example` traz a variável **comentada** (uma linha `PROFESSOR_ID=` vazia quebraria a leitura de `int | None` no pydantic-settings; a leitura também converte texto vazio em `None`) e o guia da #428 diz como preencher com o professor das fixtures.
- **A rota carrega o `professor_id`** (`/professores/{professor_id}/caixa-do-dia`), como as rotas de atleta carregam o `atleta_id`: quando houver login, a rota não muda de forma, só a origem da identidade. Hoje a API só aceita o `professor_id` **igual ao configurado**. Qualquer outro valor devolve a mesma resposta de um professor inexistente. **O filtro de vínculo usa sempre o id da configuração**, nunca o do caminho (são iguais quando a rota responde; a regra evita divergência se a rota mudar). O teste compara o **corpo do `404` byte a byte** nos três casos, e o log não registra qual deles ocorreu.
- **Professor inexistente** (id sem linha em `professor`, id diferente do configurado, ou `PROFESSOR_ID` vazio): `404` com `{"detail": [{"loc": ["path", "professor_id"], "msg": "...", "type": "professor_inexistente"}]}`, **a mesma forma** nos três casos (nem a API nem o log dizem qual deles aconteceu: não confirma que um id existe). O **app** não derruba: a tela mostra o estado de erro da #420. A API **sobe** sem `PROFESSOR_ID` (o resto do app não depende dele). Um validador de `Settings` converte texto vazio em `None` (sem ele o pydantic-settings falha ao importar com `PROFESSOR_ID=`); **teste:** a configuração sobe com a variável **ausente** e com a variável **vazia**.
- **Sem segredo:** o id não é segredo, mas **também não é autenticação**. Qualquer processo que chame a API local fala como o professor configurado. É aceitável porque o piloto roda na máquina local, sem rede (decisão 2); o "A confirmar" 1 pergunta o que fazer se alguém quiser abrir a API a outra máquina antes do login.

### 3. Filtro de vínculo e consentimento (decisão 4)
**Uma só função, usada por toda rota de professor:** `atletas_do_professor(professor_id, agora)` devolve uma **expressão SQL** (subconsulta de `atleta_id`, não uma lista Python; `agora` é parâmetro, um só por requisição, UTC com fuso, nunca `now()` no SQL), a saber os `atleta_id` com linha em `vinculo_professor_atleta` para aquele professor **e** `consentimento_em IS NOT NULL AND consentimento_em <= agora`. Nenhuma rota de professor consulta `atividade`, `checkin_treino`, `feedback_treino` ou `atleta` sem passar por ela (a mesma lista entra como condição da consulta, não como filtro depois de ler). Não há "atalho" por `assessoria_id`: **o vínculo com consentimento é o único filtro**, mesmo que o atleta e o professor sejam da mesma assessoria.

| Situação do atleta | Aparece na caixa | Treinos e check-in dele | `PUT` em lote |
|---|---|---|---|
| vínculo + `consentimento_em` preenchido (no passado) | sim | sim | sim |
| vínculo, `consentimento_em` nulo | **não** | **não** | **404** |
| vínculo, `consentimento_em` no futuro | **não** | **não** | **404** |
| sem vínculo com este professor (vínculo só com outro) | **não** | **não** | **404** |
| atleta inexistente | não | não | 404 |

**Regras de erro:** o que o professor não pode ver tem a **mesma resposta** de o que não existe (`404 atleta_nao_encontrado`, nunca `403`): a resposta não confirma que o atleta existe. No `PUT` em lote, **um id de atividade fora do filtro (`404 atividade_nao_encontrada`) derruba o lote inteiro** (nada é gravado) e o corpo do erro **não diz quais** ids foram recusados (só a contagem). **Nada de dado de saúde em log**: o log leva `professor_id`, quantidade e códigos, nunca nome de atleta, tipo, PSE nem texto.

**Teste obrigatório (#423):** uma matriz **rota x situação** com a tabela acima, nas **duas** rotas (`GET` da caixa e `PUT` em lote) e em toda rota de professor que a Meta 11 criar depois, com atletas das fixtures (um sem consentimento, um de outro professor). Passar numa só rota não basta.

### 4. `atencao@1`: os quatro motivos (função pura)
**Entrada** (uma lista de treinos de **um** atleta, sem banco, sem rede, sem relógio interno: o `hoje` entra por parâmetro, em `America/Sao_Paulo`) e **saída** (por treino, a lista de motivos na ordem do item 3). A função **não recebe a observação livre**: o campo `texto` do check-in não faz parte do tipo de entrada. Só `dor` (booleano) e se existe check-in.

**Janela.** Um treino entra se a data local dele (ADR 0003) está em `hoje - 7` a `hoje` (o mesmo `PRAZO_DIAS` do check-in; um só parâmetro, `JANELA_DIAS = 7`). Fica **de fora** da avaliação o treino `multiesporte_pai` e `troca` (mesmo critério do check-in e da carga).

**Quatro motivos**, todos com **só o que o código já calcula**:

| # | `codigo` | Quando dispara | Fonte (nada novo) | Para de disparar quando |
|---|---|---|---|---|
| 1 | `dor` | o treino tem check-in com `dor = verdadeiro` | `checkin_treino.dor` | sai da janela; o atleta edita o check-in e tira o atalho; o check-in é apagado |
| 2 | `fora_do_normal` | `linha_base@2` com `estado = ok` e **ao menos uma** métrica com `estado = fora` (|z| >= 2,5, ADR 0011) | `linha_base@2`; a direção é o **sinal do `z`** | sai da janela; a linha de base deixa de ter a medida fora (reimportação ou tipo mudou); o treino fica sem linha de base (por exemplo `divergente`) |
| 3 | `divergencia` | `tipo_origem = 'semana_padrao'`, `tipo_divergencia` preenchida e **tipo não confirmado** | `atividade.tipo_divergencia` (ADR 0011, item 4: `sem_esforco` ou `tem_tiros`) | o professor confirma ou corrige (item 5); a semana-padrão muda e a divergência some (a regra regrava); sai da janela |
| 4 | `checkin_vencendo` | treino elegível a check-in, **sem check-in**, com `dias_desde_o_treino >= 5` e ainda no prazo (`<= 7`). Restam `7 - dias` dias; `0` = "termina hoje" | `checkin.elegivel`, `no_prazo`, `dias_ate_hoje` | o atleta faz o check-in; o prazo vence (ver "Limitações") |

**Constantes de `atencao@1`** (escolha nossa, sem fonte; não é limiar clínico nem de desempenho): `JANELA_DIAS = 7`, `AVISO_CHECKIN_DIAS = 5` (avisa nos 3 últimos dias do prazo, 5, 6 e 7). O limite de "fora do normal" **não é novo**: é o da `linha_base@2` (2,5). Nada se re-calibra aqui. **Fonte das regras:** produto (plano seção 5.1) e ADRs 0011 e 0012; sem artigo.

**A linha do motivo 2 diz a direção e a métrica, nunca a causa.** Vocabulário fixo por chave (o sinal do `z` escolhe a palavra):

| Chave | `z > 0` | `z < 0` |
|---|---|---|
| `fc_media` | FC média acima do habitual | FC média abaixo do habitual |
| `fc_melhor_tiro` | FC do melhor tiro acima do habitual | FC do melhor tiro abaixo do habitual |
| `pace_medio` | pace médio mais lento | pace médio mais rápido |
| `melhor_pace` | melhor pace mais lento | melhor pace mais rápido |
| `carga_hora` | carga por hora acima do habitual | carga por hora abaixo do habitual |

(Pace é segundos por km, então `z > 0` é mais lento. As medidas fora saem na ordem da tabela, separadas por vírgula e "e".) **Proibido** em qualquer linha: causa ("por causa do calor", "porque dormiu mal"), diagnóstico ("lesão"), conselho ("descanse"), valor numérico de saúde, comparação entre atletas, juízo ("bom", "ruim", "preocupante").

**Ordem dos motivos dentro de um treino** (fixa, e é a prioridade): `dor` (1), `fora_do_normal` (2), `divergencia` (3), `checkin_vencendo` (4). **Ordem da lista de atletas:** (a) pelo motivo de **maior prioridade** presente em qualquer treino da janela do atleta; (b) empate: o atleta com o treino com motivo **mais recente** (data local, depois `inicio`); (c) empate: `atleta_id` crescente. Dentro do atleta: treinos do mais recente ao mais antigo. **Atleta sem motivo** vai depois de todos os outros, na ordem do `atleta_id`, com a frase única "Nada a destacar nos últimos 7 dias." (a ausência de motivo **não** é "está tudo bem"; a frase diz "nada a destacar" e só isso).

**Versão.** `atencao@1` é gravada na resposta (`versao`). A regra **não grava nada**: mudar para `atencao@2` muda a lista na próxima leitura, sem job e sem migração. Os motivos antigos não ficam guardados em lugar nenhum.

**Treinos novos** (o outro lado da caixa, que **não é motivo**): treino com **tipo sugerido para confirmar** = `tipo_treino` não nulo, `tipo_origem` em (`sugestao`, `semana_padrao`), `tipo_confirmado = falso`, de modalidade elegível, com data local em `hoje - 14` a `hoje` (`JANELA_NOVOS_DIAS = 14`, escolha nossa). Treino sem tipo, `trainingpeaks`, `professor` ou confirmado **não** vira "novo". Os 14 dias ficam fora da `atencao@1` de propósito (ver "A confirmar", item 2).

### 5. Confirmação em lote e correção: o que vence o quê
`PUT` em lote do tipo (#425): uma lista de `{atividade_id, tipo_treino}`; `tipo_treino` é **um dos cinco** (`leve`, `moderado`, `longo`, `intervalado`, `fartlek`) ou, para **confirmar sem mudar**, o mesmo que a atividade já tem (ou ausente, e a API usa o atual). **Tudo ou nada** (uma transação). Cada atividade tem que ser de um atleta do filtro do item 3. **Validações do lote (revisão da Duda e decisões do Theo), nesta ordem:** (1) o tipo fora dos cinco é `422` de validação, antes de tocar no banco; lote vazio é `422`; `atividade_id` repetido é `422`; máximo de **200** itens (`422` acima); (2) qualquer atividade inexistente **ou** fora do filtro é `404` com **um só** `type`, `atividade_nao_encontrada` (o item do `PUT` é a atividade, não o atleta), **antes** de qualquer `422` que dependa do estado da atividade; (3) só então o `422 atividade_sem_tipo` (multiesporte ou sem tipo para confirmar), para ele não revelar que a atividade existe. **Concorrência:** tudo ou nada em uma transação; o piloto **ignora** duas confirmações simultâneas (no Postgres bastaria `SELECT ... FOR UPDATE`; fica para quando houver mais de um professor). **Efeito no mesmo dia:** a atividade corrigida ou confirmada **continua consumindo** o item da semana-padrão do dia (ADR 0011, E13); corrigir a dona não libera o item para as irmãs, que seguem pela reserva. A FK nova leva constraint nomeada; o `GET` monta "confirmado" por `tipo_confirmado`, não pela origem. Sem índice novo em `vinculo_professor_atleta` (a consulta parte do prefixo da chave `(professor_id, atleta_id)`).

**Precedência do tipo, de cima para baixo** (completa a ADR 0011, item 2, que já tem os passos 1 a 4):
1. **Correção do professor** (`tipo_origem = 'professor'`) e **tipo confirmado**: não mudam por semana-padrão nem por regra (versão nova incluída).
2. `trainingpeaks` (mesma proteção, ainda sem fonte).
3. Semana-padrão (`semana_padrao`).
4. Regra de reserva (`sugestao`).
5. Nenhum: nulo.

| Ação do professor | O que grava na atividade | A divergência |
|---|---|---|
| **Corrigir** (tipo diferente do atual) | `tipo_treino = novo`, `tipo_origem = 'professor'`, `tipo_confirmado = verdadeiro`, `tipo_versao = nulo`, `tipo_divergencia = nulo`, `tipo_confirmado_por` e `_em` | **apagada**: o `CHECK tipo_divergencia_origem` só a admite com origem `semana_padrao` |
| **Confirmar** sem mudar | só `tipo_confirmado = verdadeiro`, `tipo_confirmado_por` e `_em`. **Origem e versão ficam** (continua `sugestao` ou `semana_padrao`: diz de onde o tipo veio) | **fica gravada** (é dado histórico), mas **o motivo 3 para de disparar**, porque o professor decidiu |
| Mandar o mesmo tipo de uma atividade já confirmada | nada muda (idempotente); `tipo_confirmado_em` **não** se renova | igual |
| Atividade `multiesporte_pai` ou `troca`, ou sem tipo para confirmar | recusa: `422` (`atividade_sem_tipo`), **o lote todo** | |

**O que a reimportação e a regra nova fazem com a correção:** nada. A reimportação atualiza a linha no lugar e não toca nenhum campo de tipo (conferido). A regra nova (`tipo_treino@2`, ou uma semana-padrão editada) **pula** a atividade confirmada ou `professor` (já é o código de hoje), inclusive a versão. **`ORIGENS_PROTEGIDAS` existe duas vezes** (`metricas/tipo_treino.py` e `servicos/evolucao_tiros.py`): a #425 as **unifica** numa constante. **Teste obrigatório (#425):** corrigir e confirmar nos dois bancos (o `CHECK tipo_divergencia_origem` aceita as duas gravações), um **dia com duas atividades**, corrigir, reimportar o mesmo FIT, reclassificar com a semana-padrão editada e conferir que o tipo, a origem e o `tipo_confirmado_em` não mudaram.

**A correção muda o que vem depois:** a linha de base daquele treino e dos seguintes do mesmo tipo passa a usar o tipo novo (a linha de base lê `tipo_treino`); o feedback do treino fica **desatualizado** pelo motivo novo `tipo` (item 6; o worker passa o **tipo atual** a `motivos_desatualizado`, como já passa o clima, e `tipo_visto` nulo não compara). Os feedbacks **de outros treinos** do atleta cuja mediana mudou um pouco **não** são refeitos (hoje também não são refeitos quando a semana-padrão muda um tipo; é a mesma lacuna, registrada em "Limitações").

### 6. O que muda a caixa, e quando
Nada da caixa é guardado (item 1): **toda mudança aparece na próxima leitura (`GET`) e em nenhuma outra hora**. Não há worker nem notificação (decisão 9 e plano: aviso por WhatsApp ou e-mail ficou fora).

| Evento | O que muda na caixa | Quando | O que **não** muda |
|---|---|---|---|
| **Check-in novo** | some `checkin_vencendo`; pode surgir `dor` e `fora_do_normal` (o feedback não mexe na caixa); o PSE, a sensação, os atalhos e a observação passam a ser vistos | próxima leitura | o tipo; o feedback ainda precisa do worker para existir |
| **Check-in editado** (mesmo um `PUT` idêntico) | `dor` aparece ou some; o conteúdo visto muda; o feedback fica desatualizado (ADR 0013) e a caixa mostra a frase "será refeito" no lugar do texto | próxima leitura | tipo; motivos 2 e 3 |
| **Check-in apagado** | volta `checkin_vencendo` (se ainda no prazo), some `dor` | próxima leitura | |
| **Reimportação do treino** (mesmo FIT ou o do Garmin) | os valores (pace, FC, duração) podem mudar: `fora_do_normal` aparece ou some na próxima leitura; se mudar `inicio` ou `duracao_s`, a atividade que "consome" o item da semana-padrão do dia pode trocar, e muda a sugestão e a divergência das **irmãs não confirmadas** do mesmo dia | próxima leitura | **o tipo corrigido ou confirmado**; o `id` do treino; o consentimento |
| **Treino novo importado** | entra na janela dos novos e, se for o caso, nos motivos | próxima leitura | |
| **Semana-padrão editada** (pelo atleta) | `aplicar_tipos` regrava tipo e divergência só dos treinos **não** confirmados e **não** `professor`; `divergencia` aparece ou some neles | na edição (já é o comportamento da Meta 7); a caixa vê na próxima leitura | treino confirmado ou corrigido: o tipo e o motivo 3 ficam como o professor decidiu |
| **Regra nova do tipo** (`tipo_treino@2`) | igual à semana-padrão editada | quando a regra rodar (job de hoje) | confirmado e `professor` |
| **Correção do professor** | o treino sai da lista de novos; some `divergencia`; a linha de base muda **do treino e dos seguintes do mesmo tipo** (pode surgir ou sumir `fora_do_normal` neles); as irmãs do mesmo dia **não** ganham o item do dia; o feedback fica desatualizado pelo motivo `tipo` | na gravação do `PUT`; a lista vê na próxima leitura | a divergência da coluna **fica apagada** (o `CHECK` exige) |
| **Confirmação sem mudar** | o treino sai da lista de novos; `divergencia` para de disparar (a coluna fica) | idem | tipo, origem, versão |
| **Consentimento concedido** | o atleta **entra** na caixa com os treinos da janela | próxima leitura | |
| **Consentimento retirado** (`consentimento_em` volta a nulo) | o atleta **some**, com os treinos e os dados dele; o `PUT` devolve `404` | próxima leitura | o que o professor já gravou em `atividade` (tipo corrigido) **fica** (é dado do treino do atleta; ver "A confirmar", item 8) |
| **Passagem do tempo** (o dia vira, em `America/Sao_Paulo`) | `checkin_vencendo` aparece (5 dias) e some (prazo vencido); treinos saem da janela; um atleta com `consentimento_em` **no futuro** **entra** quando a data chega, sem ninguém agir | próxima leitura depois da meia-noite local | |
| **Noite ou clima novos** (Meta 9 e 10) | nada na caixa; refazem o feedback pelo worker | | a lista de motivos |
| **`atencao@2`** (versão nova) | a lista inteira é recalculada com a regra nova | próxima leitura | nada guardado para desfazer |

### 7. O que o professor vê, e o que nunca sai do banco local (decisão 7)
**O professor vê, por treino do aluno com consentimento** (dentro da janela da caixa; a leitura do histórico do aluno é a "ficha completa", **fora**): modalidade, data local, tipo (valor, origem e se foi confirmado, com o texto pronto da API como nas outras telas), **PSE**, **sensação**, os **atalhos** (`dor`, `cansaço`, `sono ruim`, `calor`, `trabalho/estresse`), o **feedback** pronto e **a observação livre** (como o atleta a escreveu), mais os motivos do item 4. O nome do aluno é o do cadastro fictício.

**O professor não vê:** a recuperação (sono, VFC, FC de repouso: decisão 6 deixou o alerta fora, e ver o número seria ficha completa), clima, posição de início, carga numérica, arquivos FIT, semana-padrão do atleta, recordes. O feedback que ele vê, porém, **pode citar a recuperação em frase** (ADR 0014); isso é o texto aprovado pelas checagens e o Angelo decidiu que ele vê o feedback. Fica como pergunta (item 5 de "A confirmar").

**A observação livre nunca vai ao provedor de LLM.** O que garante, **por construção e por teste**: (a) o pacote `fatos_treino` não tem campo de observação (ADR 0013, item 2; o teste de que a chave não existe continua, e a #422 acrescenta um que prova que a `atencao@1` não recebe `texto`); (b) a caixa **não chama LLM**: os motivos são frases de regra; (c) a observação só viaja no `GET` do professor, e **nunca** em log, em mensagem de erro, em fixture gravada nem em captura (as capturas da #418 usam fixtures sintéticas). A decisão 7 manda **rever na consulta de LGPD antes do primeiro aluno real**: a ADR registra a revisão como condição, sem data.

**Nunca sai do banco local** (vale para o professor e para qualquer rota): observação, check-in, feedback, recuperação, posição, o nome real de qualquer pessoa, a conta do Angelo e qualquer dado real. O repositório só tem fixtures **fictícias escritas à mão**; a ligação da conta do Angelo a um professor de teste (decisão 5, #431) é uma operação no banco local, **sem script nem fixture no repositório** que contenha id ou dado real.

### 8. API e telas: o que esta ADR diz e o que deixa para o adendo
Esta ADR **não** define o JSON (isso é o adendo da ADR 0004 na #424). Fixa só: rota por `professor_id`; resposta com `versao: atencao@1`; atletas ordenados como no item 4; por treino, os motivos prontos (`codigo` e `texto`); treinos novos separados; textos montados pela API ("a API formata, o app mostra", adendo 2 da ADR 0004); `404` sem distinguir o que existe do que não existe; o `PUT` em lote **tudo ou nada**.

## Alternativas consideradas
- **Guardar a atenção** (tabela `atencao_atleta` calculada por worker): rápida de ler, mas fica velha a cada evento da tabela do item 6. Descartada: o volume do piloto (um professor, poucos alunos) não justifica.
- **Filtro por `assessoria_id`:** descartada. O consentimento é do atleta para **aquele** professor (decisão 4).
- **`403` para atleta fora do filtro:** descartada; confirmaria que o atleta existe.
- **Motivo de falta e recuperação baixa na atenção:** fora (decisão 6).
- **Uma frase só com todos os motivos:** descartada; "um motivo por linha" é mais fácil de ler e de testar.
- **Confirmar sem mudar muda a origem para `professor`:** descartada; perderia de onde veio o tipo. `tipo_confirmado` já protege o tipo.
- **Janela única de 7 dias para atenção e novos:** descartada; quem volta de dois dias de folga perde treino por falta de aviso (item 2 de "A confirmar").
- **Sem a coluna `feedback_treino.tipo_visto`:** o feedback ficaria com o texto do tipo antigo para sempre (item 3 de "A confirmar").

## Consequências
- Cada motivo é determinístico e testável com oráculo à mão (#421, #422); trocar a regra não pede migração.
- O filtro de consentimento é um ponto só de entrada e uma matriz de teste; um esquecimento numa rota nova **vaza dado de saúde** e é o risco mais sério da meta.
- A caixa roda sobre a hora da leitura: sem relógio injetável nos testes ela fica instável. `hoje` entra por parâmetro.
- A migração `0016` é pequena e aditiva; o `downgrade` apaga só o que ela criou.
- O feedback ganha um motivo de desatualizado (`tipo`), então o worker refaz o feedback depois de uma correção, **dentro do limite de chamadas** do plano gratuito.

## Limitações
- **Sem login, o `professor_id` não é autenticação.** Serve para a máquina do piloto e nada mais. Nada daqui vale para um servidor aberto.
- **Prazo vencido é silêncio:** o motivo 4 some no oitavo dia, justo quando o treino ficou sem check-in. A caixa não conta treinos "perdidos". Se o Angelo quiser, é um quinto motivo, em outra versão.
- **Os limiares são nossos:** `JANELA_DIAS`, `AVISO_CHECKIN_DIAS`, `JANELA_NOVOS_DIAS`. Revisão depois de uns 30 dias de uso, olhando só contagens (sem valores no repositório), como a ADR 0014.
- **"Fora do normal" herda os limites da linha de base:** 8 treinos de mínimo no tipo, tipo errado dá comparação errada, esteira sem pace.
- **Corrigir o tipo não refaz o feedback de outros treinos** (item 5).
- **A divergência apagada na correção não volta** se o professor se arrepender: ele corrige de novo (não há "voltar ao automático", ver "A confirmar", item 7).
- **FK sem `ondelete` em `vinculo_professor_atleta`:** apagar atleta ou professor com vínculo falha (NO ACTION). Fora do piloto.
- **Concorrência ignorada** no `PUT` em lote (um professor só).
- **Atleta de vários professores** (dois vínculos com consentimento): cada professor vê o atleta, e a última confirmação vale (`tipo_confirmado_em`). Não há conflito resolvido; fora do piloto.

## Fora desta ADR
Login, contas, controle de acesso e deploy; dado de aluno real; o texto do termo de consentimento; rascunho de devolutiva, revisão de amostra do feedback, feedback com o nome do professor, semana-padrão por grupo, ficha completa do aluno; recuperação baixa e motivo de falta como atenção; o JSON da API (adendo da ADR 0004, #424); o desenho da tela (#420); "voltar ao automático"; dispensar um aviso.

## Fontes
- Regra própria do projeto, sem artigo: os quatro motivos, a janela de 7 dias, o aviso aos 5 dias, a janela de 14 dias dos novos e a ordem dos motivos são **escolha nossa**.
- Reaproveitam o que já tem fonte: o limite de "fora do normal" (2,5) e a mediana/MAD são os da [[decisoes/0011-linha-de-base-e-semana-padrao]] (Leys et al., 2013; Rousseeuw e Croux, 1993; citações ainda não conferidas nos textos, a pendência da ADR 0011 continua). Aqui nada disso é recalculado.
- Produto: [[produto/plano-mvp-execucao]], seções 1 e 5.1 (caixa do dia), e as decisões do Angelo de 16/11.

## A confirmar
Cada item tem a **recomendação** (o padrão que vale se o Angelo responder "ok"). Os itens 3, 4 e 9 eram do **Theo** e estão resolvidos; faltam as respostas do **Angelo** aos itens **1, 2, 5, 6, 7, 8 e 10**.
1. **O `professor_id` configurado basta para o piloto, se a API só roda na máquina local?** *Recomendação:* sim, e a API local **escuta só em `127.0.0.1`**. Se ele quiser abrir a outra máquina antes do login, é um assunto novo (deploy). *Angelo.*
2. **Janelas.** Atenção olha os **últimos 7 dias** (o mesmo prazo do check-in) e os **treinos novos** os **últimos 14**. *Recomendação:* 7 e 14. Alternativa: 14 nos dois (mais ruído, o motivo "check-in vencendo" já tem seu próprio corte); ou 7 nos dois (quem folga 8 dias perde treino sem confirmar). *Angelo.*
3. **A migração `0016` (`tipo_confirmado_por`, `tipo_confirmado_em`, `feedback_treino.tipo_visto`).** **Resolvido em 16/11 (Theo, PR #435): aprovado, com a FK nomeada.** *Recomendação:* sim, as três colunas. Alternativa: só `tipo_visto` (sem quem nem quando, porque só há um professor no piloto) ou nenhuma (aceitar o feedback velho depois da correção). *Theo.*
4. **Corrigir o tipo desatualiza o feedback (motivo `tipo`).** **Resolvido em 16/11 (Theo): sim; entra na fila normal, o limite por execução segue valendo e o resto fica em `adiados`.** *Recomendação:* sim, e o worker refaz (consome o limite de 20 chamadas por execução, como o clima e a noite). Alternativa: não refazer e mostrar "tipo corrigido depois do feedback". *Theo e Caio.*
5. **O professor vê o feedback, que pode citar a recuperação (sono, VFC) em frase.** A decisão 7 lista o feedback, mas não a recuperação. *Recomendação:* aceitar (é o texto aprovado pelas checagens) e levar à consulta de LGPD junto com a observação. Alternativa: o professor vê o feedback só quando ele não menciona recuperação, o que exige marcar o texto (mais código). *Angelo.*
6. **Dispensar um aviso ("já vi")?** Hoje um treino com `dor` fica na caixa até sair da janela (7 dias), mesmo depois de o professor falar com o aluno. *Recomendação:* **não** nesta meta (seria estado novo e o piloto é pequeno); medir no ensaio se atrapalha. Alternativa: coluna `visto_em` por treino e professor. *Angelo.*
7. **"Voltar ao automático" (desfazer uma correção).** *Recomendação:* **não** nesta meta; o professor corrige de novo. A decisão 8 diz que a correção "não é desfeita" por reimportação nem regra, e isso inclui o botão. Alternativa: `DELETE` que volta ao que a regra daria. *Angelo.*
8. **Consentimento retirado depois de o professor ter corrigido tipos:** a correção **fica** na atividade (é dado do treino, e o atleta é dono do treino). *Recomendação:* fica; o texto do termo (consulta jurídica) diz o que acontece com o que o professor gravou. Alternativa: limpar `tipo_confirmado_por` ao retirar (perde a auditoria, mantém o tipo). *Angelo e consulta de LGPD.*
9. **Correção de tipo para ciclismo e natação (sem regra de tipo hoje).** **Resolvido em 16/11 (Theo): sim, os cinco tipos em qualquer modalidade elegível.** *Recomendação:* aceitar os cinco tipos em qualquer modalidade elegível, como o item da semana-padrão aceita (a linha de base de ciclismo e natação ignora o tipo). Alternativa: só corrida. *Theo e Duda.*
10. **"Treino fora do normal" para treino sem linha de base (sem tipo, divergente, `aprendendo`):** *Recomendação:* sem motivo 2 (a regra não inventa comparação); o treino segue na lista de novos para o professor dar o tipo, e depois a linha de base existe. Alternativa: motivo próprio "sem comparação". *Angelo.*

## Revisão da Duda (incorporada em 16/11)
Modelo de dados (item 1: três colunas, `ON DELETE SET NULL`, `consentimento_em` com futuro), filtro (item 3: a função única e a matriz de teste), identidade (item 2), o `PUT` tudo ou nada, o `CHECK tipo_divergencia_origem` e o que a correção apaga (item 5), o conflito com `ORIGENS_PROTEGIDAS` e a tabela do item 6 (reimportação e `aplicar_tipos`). Pontos em aberto para ela: o índice em `vinculo_professor_atleta(atleta_id)` (a chave é `(professor_id, atleta_id)`) e se `consentimento_em <= agora` cabe na consulta do filtro sem mudar o plano.

## Data e quem decidiu
2026-11-16. Proposta do Caio (ciência), com revisão da Duda (banco e API) pedida no PR. Decisões do Angelo de 16/11 ("ok para as 10") no Contexto. Issue #419. **Modelo de dados: aprovado pelo Theo em 2026-11-16** (comentário no PR #435), com a revisão da Duda incorporada no mesmo dia. **Status `proposta`:** vira `aceita` quando o Angelo responder aos itens 1, 2, 5, 6, 7, 8 e 10 de "A confirmar".
