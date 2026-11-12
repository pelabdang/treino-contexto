---
tipo: decisao
status: proposta
dono: caio
atualizado: 2026-11-12
links: [[decisoes/0003-fuso-da-atividade]], [[decisoes/0004-contrato-tela-evolucao]], [[decisoes/0010-carga-de-treino]], [[decisoes/0011-linha-de-base-e-semana-padrao]], [[decisoes/0012-check-in-pos-treino]], [[decisoes/0013-feedback-automatico]], [[metricas/linha-base]], [[metricas/fatos-treino]], [[metricas/checagens-feedback]], [[modulos/banco]], [[modulos/api]], [[modulos/worker]], [[modulos/ingestao-garmin]], [[modulos/camada-llm]], [[produto/roadmap]], [[produto/plano-mvp-execucao]], [[glossario]]
---
# ADR: 0014 Recuperação diária (sono, VFC e FC de repouso) no contexto do treino

> **Proposta** (issue #370, Meta 10). **Nenhuma linha de código nem migração muda neste PR.** O modelo de dados (item 1) precisa da aprovação do Theo
> antes da migração `0014` (#372). Todos os números, textos e exemplos são **sintéticos**. Sono, VFC e FC de repouso são dado pessoal e de
> saúde: nada de valor, data ou padrão real do atleta no repositório, em log, em captura ou em fixture gravada. Esta ADR não consultou a conta
> nem o banco do Angelo; o formato real das respostas do Garmin é assunto da #371 e da #372.
> Dá base para #371 (formato e fixtures), #372 (banco, busca e apagar), #373 (`recuperacao@1`), #374 (`fatos_treino@2`) e #375 (prompt e checagens).

## Contexto
O plano pede no feedback de cada treino "o que pesou (sono, calor, carga)" ([[produto/plano-mvp-execucao]], seção 4.6) e põe sono, VFC e FC de repouso
entre os fatores da seção 4.3. Calor e carga já estão no pacote de fatos ([[decisoes/0013-feedback-automatico]]); a recuperação é o fator que falta.
A Meta 10 põe a **noite anterior ao treino**, comparada com o **normal do próprio atleta**, **ao lado** do resultado do treino, sem afirmar causa.
Princípio de sempre: **quem calcula é o código; a IA só redige.**

### Decisões do Angelo (12/11, "ok para as nove"), que esta ADR respeita
1. Tema da Meta 10: recuperação no contexto do treino.
2. Guardar a recuperação diária da conta dele no **banco local**: **só** duração do sono, VFC noturna e FC de repouso, com a regra do dado de saúde
   (só banco local, nunca em log, comando para apagar).
3. Fonte: a mesma biblioteca **não oficial** do `worker.buscar_garmin` (#335), **só local**, aceita como limitação; a API oficial segue como caminho de produção.
4. Ao provedor de LLM vai **só a comparação da noite anterior ao treino com o normal do atleta** (valor, normal e estado), **nunca a série diária**.
   Os limites da decisão 9 da ADR 0013 continuam (só local, só o pacote, plano gratuito, nada em log ou repositório).
5. No texto: **lado a lado** com o resultado, **sem causa e sem conselho**.
6. Sem tela nova: a recuperação aparece só no texto do cartão "Feedback". (As decisões 7 a 9 da Meta 10 não tocam esta ADR.)

### O que o código do `main` mostra (conferido em 12/11, commit `f5209fd`)
- A próxima migração é a **`0014`** (a última é a `0013_feedback_treino`).
- `ORIGENS_SAUDE = ("garmin_export",)` serve a `recorde_pessoal` e `carga_garmin_dia`; a recuperação **não vem da exportação**, então a origem nova é `garmin_connect`.
  `carga_garmin_dia` é o molde de "um valor por dia por atleta, com `origem`, `versao_leitura` e `importado_em`".
- A data local de uma atividade vem de `data_local(inicio, fuso_min)`, com `fuso_min` nulo caindo em `America/Sao_Paulo` ([[decisoes/0003-fuso-da-atividade]]).
- `worker.buscar_garmin` usa `garminconnect==0.3.20` (`worker/garmin_cliente.py`, interface `ClienteGarmin`, códigos de saída 0 a 6, token em pasta local, nada de credencial em log).
- `linha_base@2`: mediana e MAD na janela, `1,4826 x MAD`, piso relativo, limite 2,5, mínimo de 8, estados `aprendendo`/`dentro`/`fora` ([[decisoes/0011-linha-de-base-e-semana-padrao]]).
- `fatos_treino@1` e as checagens `@1` existem (ADR 0013); `feedback_treino` guarda `versao_fatos` e `checkin_atualizado_em`, e `worker.apagar_checkin` imprime só contagens.
- **O que a biblioteca documenta** (lido no código instalado, versão 0.3.20, sem rede e sem conta): `get_sleep_data(cdate)` e `get_sleep_daily(start, end)` (a segunda
  junta janelas de até 28 dias e deduplica por data), `get_rhr_day`/`get_rhr_daily(start, end)` (faixa de até cerca de 1 ano numa chamada), `get_hrv_data(cdate)` (devolve `dict` ou `None`) e
  `get_hrv_data_range(start, end)`. A documentação do `get_sleep_data` diz que a resposta passa "exatamente como o Garmin devolve" e que, em algumas contas, os horários
  `*Local` do sono vieram deslocados duas vezes pelo fuso; a recomendação dela é usar os campos `*GMT`. **A biblioteca não documenta os nomes dos campos da resposta nem o que vem num dia sem dado**:
  isso é da #371 (ver item 6). Esta ADR só exige o que o leitor precisa devolver.

## Decisão

### 1. O que se guarda e em que tabela (modelo de dados, para aprovação do Theo)
Uma tabela nova, **`recuperacao_dia`**, na migração **`0014`**, **um registro por atleta, origem e noite**. Guarda **três números**, e mais nada da resposta do Garmin
(sem estágios do sono, horário de dormir ou acordar, estresse, prontidão, Body Battery, série de FC, resposta bruta).

| Coluna | Tipo e unidade | Observação |
|---|---|---|
| `id` | inteiro, chave | |
| `atleta_id` | FK `atleta.id`, `ON DELETE CASCADE`, indexada | apagar o atleta apaga a recuperação |
| `origem` | texto (20), `CHECK` | `garmin_connect` (única hoje; a exportação **não** é fonte, ver "Fora desta ADR"). Entra na chave como em `carga_garmin_dia`, para a API oficial entrar sem mexer na tabela |
| `noite` | `Date` | a **data local de acordar** (item 2). Não é a data em que deitou |
| `sono_s` | inteiro, segundos, anulável | **duração do sono** da noite principal (tempo dormindo; a #371 confirma se é o total ou o total sem os despertares). Sem sesta. `CHECK sono_s IS NULL OR sono_s BETWEEN 1 AND 86400` |
| `vfc_ms` | real, milissegundos, anulável | **VFC noturna** da noite: o valor médio da noite que o Garmin publica, na unidade em que ele publica (ms). A fórmula do Garmin não é aberta (ver "Limitações"). `CHECK vfc_ms IS NULL OR (vfc_ms > 0 AND vfc_ms <= 500)` |
| `fc_repouso_bpm` | inteiro, bpm, anulável | **FC de repouso** do dia. `CHECK fc_repouso_bpm IS NULL OR fc_repouso_bpm BETWEEN 20 AND 150` |
| `versao_leitura` | texto (40), não nulo | `recuperacao_leitura@1`: a versão do leitor que extraiu os três números da resposta (sobe quando a regra de extração muda; é a ligação com a #371) |
| `importado_em` | datetime com fuso, não nulo | **definido pela aplicação**, e só **muda quando algum dos três valores muda** (item 5): é o que mede "a noite foi atualizada" para o feedback |

Restrições: `UNIQUE (atleta_id, origem, noite)` (chave natural, como `carga_garmin_dia`); `CHECK origem IN ('garmin_connect')`; e `CHECK` de que **ao menos uma das três medidas não é nula**
(`sono_s IS NOT NULL OR vfc_ms IS NOT NULL OR fc_repouso_bpm IS NOT NULL`): **noite sem nenhum dado não vira linha**, a ausência da linha é o "sem dado" (item 5).
Cada medida é independente: pode haver sono e FC de repouso sem VFC (relógio sem a função, noite com pouca leitura).

Uma segunda mudança, em tabela existente, e por isso **também para o Theo aprovar**: `feedback_treino` ganha a coluna **`recuperacao_importada_em`** (`DateTime(timezone=True)`, **anulável**),
a cópia do `importado_em` da noite usada no pacote na hora da geração (`NULL` = o pacote saiu sem noite). Ela existe para o feedback gerado **antes** de o relógio sincronizar a noite
poder ser refeito quando a noite chegar (item 4, "Desatualizado"). Sem ela, o feedback de um treino de manhã, gerado antes da busca, ficaria para sempre sem a recuperação. Alternativa descartada
em "Alternativas consideradas".

**Migração `0014`.** Cria `recuperacao_dia` e adiciona a coluna em `feedback_treino` (aditiva; no SQLite a coluna entra por `batch_alter_table`). O `downgrade` remove a coluna e apaga a tabela
(dado de saúde derivado de uma fonte que se rebusca). Sem índice além do `UNIQUE` e do índice de `atleta_id`. Testes de migração: `CHECK` rejeita linha com as três medidas nulas, `sono_s = 0`,
`fc_repouso_bpm = 0` e origem desconhecida; `alembic upgrade head` e `downgrade base` continuam no CI. Gravação em *upsert* por `(atleta_id, origem, noite)`, **sem savepoint**, como nas ADRs 0012 e 0013.

### 2. A que "noite" pertence cada valor e como ela se liga a um treino
**Noite = a data local de acordar** (a data do dia em que o atleta levantou). É a convenção em que o Garmin atribui o sono ao dia seguinte à noite, e a que o `cdate` do
`get_sleep_data` usa na chamada; a #371 **confirma** com a resposta (campo e data) e, se divergir, o leitor converte para esta regra (o ADR manda a regra; o leitor se adapta).
A **FC de repouso** e a **VFC** entram na linha da **mesma data**: o dia que começa na manhã em que o atleta acordou.
Fuso: a data é a **data local do atleta**, sem conversão por nós (o Garmin já entrega no fuso do relógio); quem viaja entre fusos pode ter uma noite duplicada ou ausente (limitação aceita).

**Ligação com o treino.** Para um treino com data local `D` (a de [[decisoes/0003-fuso-da-atividade]]: `inicio + fuso_min`, ou `America/Sao_Paulo`) e hora local `H`:
- **Regra:** a noite do treino é a linha com `noite = D`, a noite que **terminou na manhã de `D`**, desde que o treino comece **às `HORA_CORTE = 06:00` locais ou depois** (escolha nossa).
- **Treino de manhã ou depois, até à noite:** usa a noite de `D`. Treino às 22h ainda usa a noite que terminou na manhã desse mesmo dia: é "a noite anterior ao treino" no sentido de "a última noite dormida".
- **Treino de madrugada (início local antes de `06:00`):** **sem recuperação** (`estado = sem_dado`, `motivo = treino_de_madrugada`). Sem o horário de acordar (que **não** se guarda, item 1) não dá para saber se o treino foi
  antes ou depois de acordar, e usar a noite de `D` poderia pôr no pacote uma noite que ainda não tinha acabado; usar a de `D - 1` seria a noite de dois dias antes. O padrão é **não adivinhar** (A confirmar, item 3).
- **Dois treinos no mesmo dia:** os dois usam **a mesma noite** (a de `D`); o segundo não vê a noite "entre" os treinos porque não existe. Nenhum estado especial. O texto diz só "na noite anterior"; não diz que o outro treino aconteceu.
- **Multiesporte e trocas:** nada muda; só a atividade elegível ao feedback (ADR 0013) recebe o bloco.
- Sem `fuso_min` o fallback é `America/Sao_Paulo`, como em todo o app.

### 3. `recuperacao@1`: o "normal" do atleta e o estado de cada medida
**Função pura** (`app/metricas/recuperacao.py`, #373; sem banco, sem rede): recebe o valor da noite e a lista de valores da janela e devolve o estado, o normal e a diferença. Não grava nada: o "normal" é
**calculado na leitura**, como a linha de base (ADR 0011, item 6), porque muda a cada noite nova.

| Escolha | Valor | Fonte ou "escolha nossa" |
|---|---|---|
| Medida do normal | **mediana** das noites da janela; dispersão por **MAD** (`desvio = max(1,4826 x MAD, PISO_REL x mediana)`), o mesmo cálculo da `linha_base@2` | reaproveita a ADR 0011: Leys et al. (2013) para mediana e MAD, Rousseeuw e Croux (1993) para a constante 1,4826. **Citações ainda não conferidas nos textos** (a pendência da ADR 0011 continua) |
| Janela | as **28 noites** que terminam na **véspera** da noite do treino (noites `D - 28` a `D - 1`); a noite do treino **não entra** no próprio normal | **escolha nossa** (4 semanas, todas com o mesmo número de cada dia da semana). Referência de ordem de grandeza, não fonte da escolha: a página de ajuda do Garmin sobre o *HRV status* diz que o relógio precisa de cerca de **três semanas** de leituras noturnas para formar a faixa de base da VFC e compara uma média de 7 dias com ela. Lida em 12/11 por uma ferramenta que resume; vale abrir a página |
| Mínimo | **14 noites com valor** daquela medida na janela (`MINIMO_NOITES = 14`), contado **por medida** | **escolha nossa** (metade da janela). Abaixo disso a medida é `aprendendo` |
| `PISO_REL` | **0,05** (5% da mediana) | **escolha nossa**, sem calibração: evita dividir por zero e evita chamar de "fora" uma variação de poucos minutos ou de 1 a 2 bpm. A calibrar |
| Limite | `\|z\| >= 2,0` (`LIMITE_FORA = 2,0`) com `z = (valor - mediana) / desvio` | Leys et al. (2013) citam 2, 2,5 e 3 como limites; **a escolha do 2,0 é nossa** (A confirmar, item 4): a `linha_base@2` usa 2,5 porque compara um treino contra treinos do mesmo tipo; a noite é um dado mais ruidoso e o texto não é alerta. **Não é limiar clínico** |

**Estados de cada medida:** `dentro` (`\|z\| < 2,0`), `abaixo` (`z <= -2,0`), `acima` (`z >= 2,0`), `aprendendo` (menos de 14 noites com valor: o pacote traz o valor e `n`, **não** traz mediana nem comparação),
`sem_dado` (a noite não tem valor desta medida). "Abaixo" e "acima" são **só direção**: **não** significam bom nem ruim, e vale para as três (uma FC de repouso "acima" e um sono "abaixo" não são julgados).
Nada de limiar absoluto (nenhum "menos de 6 horas é pouco", nenhuma FC de repouso "alta"): só a comparação com o histórico do próprio atleta.

**Exemplo à mão (sintético), sono em minutos, 14 noites:** 400, 410, 420, 420, 425, 430, 435, 435, 440, 440, 445, 450, 460, 470. Mediana = (435 + 435) / 2 = **435**.
Desvios absolutos ordenados: 0, 0, 5, 5, 5, 10, 10, 15, 15, 15, 25, 25, 35, 35; MAD = (10 + 15) / 2 = **12,5**.
`desvio = max(1,4826 x 12,5 = 18,5325; 0,05 x 435 = 21,75) = 21,75`. Noite de 345 min: `z = (345 - 435) / 21,75 = -4,138`, **abaixo**, "1 h 30 min abaixo" do normal de 7 h 15 min.
Noite de 420 min: `z = -0,690`, **dentro**. Com 13 noites com valor, a medida é **aprendendo** (sem mediana).

**Texto da diferença** (`diferenca_texto`, só em `abaixo` e `acima`): sono em horas e minutos ("1 h 30 min abaixo"), VFC em ms ("6 ms abaixo"), FC de repouso em bpm ("3 bpm acima"), arredondadas ao inteiro
da unidade de exibição (minuto, ms, bpm). O "normal" no texto é a mediana, também arredondada.

**Estado do bloco** (`recuperacao.estado`): `ok` quando ao menos uma medida tem valor na noite; `sem_dado` (com `motivo`) quando não há noite utilizável (item 5). `aprendendo` é estado **da medida**; o bloco com as três
medidas `aprendendo` continua `ok` (há valores, ainda sem comparação), como a linha de base com todas as métricas `aprendendo` (exemplo 3 da ADR 0013).

**Versão.** `VERSAO = "recuperacao@1"`. Sobe com a janela, o mínimo, o piso, o limite, a medida ou a regra da noite do treino. Nota em `docs/metricas/` e oráculo com fixtures **escritas à mão** (#371 e #373), nunca resposta real gravada.

### 4. O que entra no pacote (`fatos_treino@2`)
`fatos_treino@1` sobe para **`fatos_treino@2`**: **um bloco novo, `recuperacao`**, depois de `clima` e antes de `carga` (a ordem das chaves é fixa, ausente = `null`, como na ADR 0013). Nada mais muda nos demais blocos.
O pacote continua **sem número novo**: cada valor vem da função `recuperacao@1`, e o texto vem pronto (`*_texto`).

| Campo | Tipo e unidade | Origem |
|---|---|---|
| `recuperacao.versao` | `recuperacao@1` | constante |
| `recuperacao.estado` | `ok` ou `sem_dado` | item 3 |
| `recuperacao.motivo` | só em `sem_dado`: `sem_noite` (a noite não tem linha, ou o relógio/conta não devolveu), `treino_de_madrugada`, `sem_fuso` não existe (fallback do item 2) | item 2 e 5 |
| `recuperacao.janela_noites` | 28 | parâmetro |
| `recuperacao.minimo_noites` | 14 | parâmetro |
| `recuperacao.medidas[]` | uma por medida, na ordem `sono`, `vfc`, `fc_repouso`; **sempre as três quando `estado = ok`** | |
| `...medidas[].chave` | `sono`, `vfc`, `fc_repouso` | |
| `...medidas[].estado` | `dentro`, `abaixo`, `acima`, `aprendendo`, `sem_dado` | item 3 |
| `...medidas[].valor`, `valor_texto` | s, ms, bpm; "5 h 40 min", "41 ms", "55 bpm" | linha da noite; só quando há valor |
| `...medidas[].normal_texto` | "7 h 10 min", "47 ms", "52 bpm" (a mediana); **só** em `dentro`, `abaixo`, `acima` | `recuperacao@1` |
| `...medidas[].diferenca_texto` | "1 h 30 min abaixo"; **só** em `abaixo` e `acima` | `recuperacao@1` |
| `...medidas[].n` | noites da janela com valor | `recuperacao@1` |

**Nunca entra no pacote** (testado por oráculo, #371 e #374): a **série diária** ou qualquer valor de **outra noite**; a **data** da noite (nem o dia da semana); horário de dormir ou acordar; MAD, `z`, desvio
ou o valor numérico da mediana (só o texto); estágios do sono, estresse, Body Battery, prontidão, estado de treino, *HRV status* do Garmin ou qualquer métrica proprietária dele; o fato de a noite ter vindo de um relógio ou
da API; a resposta bruta; identificador do atleta. Estado `sem_dado`: só `versao`, `estado` e `motivo`, sem `medidas`.

**Estados e o que o texto pode fazer.** `ok`: o texto pode dizer a noite e a comparação de cada medida. `aprendendo`: diz o valor e que ainda está aprendendo o normal (n de 14), sem comparação.
`sem_dado`: o texto **pode** dizer "Sem dado de sono, VFC e FC de repouso da noite anterior." ou **omitir** a recuperação; **não** pode estimar nem comentar ("provavelmente dormiu...").
A decisão de dizer ou omitir o "sem dado" é do prompt (#375); padrão: **omitir** quando o motivo é `treino_de_madrugada` e **dizer** nos demais (A confirmar, item 6).

**Desatualizado (muda a ADR 0013, item 2).** Além das regras que já existem, o feedback fica **desatualizado** quando **(a)** `versao_fatos` difere da versão atual (então **todos** os feedbacks de `fatos_treino@1` ficam desatualizados quando
o código subir; o worker os refaz respeitando o limite de chamadas por execução, e o texto antigo é **substituído**: a Meta 10 muda o que o atleta lê nos treinos antigos, e isso fica dito no guia); ou **(b)** `recuperacao_importada_em` difere do `importado_em` da noite
do treino **hoje** (a noite chegou depois, mudou um valor, ou o atleta apagou a recuperação: sem linha, o lado de lá é `NULL`). Os dois lados são normalizados para UTC antes de comparar (o mesmo cuidado da ADR 0013).
**Não** fica desatualizado porque o **normal** mudou (entrou noite nova na janela): o feedback descreve o treino no momento em que foi gerado, como a linha de base (ADR 0013, item 2).

**O que vai ao provedor (decisão 4).** O prompt fixo e o pacote `fatos_treino@2`, e nada mais; do bloco `recuperacao`, só o que está na tabela acima: **a noite anterior ao treino** e o normal dela, nunca a série. O limite de quatro tópicos da decisão 9 da ADR 0013 continua:
só local, só o pacote, plano gratuito, nada em log nem no repositório. Em CI e testes o provedor é o falso.

### 5. Idempotência da busca, apagar e quando o Garmin não devolve a noite
**Busca:** `uv run python -m worker.buscar_recuperacao --atleta "<nome>" [--desde AAAA-MM-DD] [--ate AAAA-MM-DD]` (#372), **na mesma biblioteca** do `worker.buscar_garmin`, mesma interface `ClienteGarmin`
(estendida com `recuperacao(desde, ate)`; cliente **falso** em testes e CI, sem rede), mesmas variáveis de ambiente, token e **mesmos códigos de saída** (0 ok; 1 configuração; 2 login; 3 MFA; 4 limite; 5 rede; 6 outro erro do Garmin).
- **Padrão de datas:** sem `--desde`, se o atleta **não tem** nenhuma linha, busca as últimas **35 noites** (a janela de 28 mais folga; a primeira rodada enche o normal); se já tem, busca as últimas **3 noites** (a de hoje e duas antes, para pegar sincronização atrasada). `--ate` padrão: hoje (data local do atleta, ou `America/Sao_Paulo`).
- **Chamadas:** por faixa, não por dia (a biblioteca oferece `get_sleep_daily`, `get_rhr_daily` e `get_hrv_data_range`), em janelas de até 28 dias. **Cada medida é pedida e gravada à parte**: se a VFC falhar e o sono vier, o sono é gravado e o comando sai com código 6 e conta a falha.
- **Idempotente:** *upsert* por `(atleta_id, origem, noite)`. Rodar de novo com o mesmo resultado não muda nada (`importado_em` **não** muda se os três valores são iguais). Um valor **nulo vindo do Garmin nunca apaga** um valor já guardado
  (um dia sem leitura não desfaz o que veio antes); um valor **diferente** substitui e muda `importado_em` (o Garmin recalcula a noite depois da sincronização).
- **Saída:** só contagens e códigos (`recuperacao: noites_novas=a atualizadas=b iguais=c sem_dado=d falhas=e`). **Nunca** valor, data, resposta ou nome de campo da resposta.
- **Nada em log:** as respostas do Garmin não são registradas, nem em depuração, nem em mensagem de exceção (captura-se a classe do erro e converte-se em código, como na ADR 0013). Teste com um marcador sintético na resposta do cliente falso, em sucesso e erro: o marcador não aparece em `caplog` (DEBUG),
  `stdout`, `stderr` nem em exceção. Os loggers da biblioteca (que no nível DEBUG escrevem só que "pediram" um dado, sem o conteúdo, mas sem garantia) ficam acima de DEBUG por código.
- **Só o piloto local:** biblioteca não oficial, pode quebrar quando o Garmin mudar o login ou os campos (limitação aceita, decisão 3); a API oficial é o caminho de produção e **não** entra na Meta 10.

**Quando o Garmin não devolve a noite.** (1) Dia sem sono, sem VFC e sem FC de repouso: **nenhuma linha** (o `CHECK` proíbe linha vazia). (2) Só algumas medidas: a linha fica com as que vieram, as outras ficam `NULL`.
(3) Erro de rede, login ou limite: nada é gravado para a faixa que falhou, o código de saída diz o porquê, e a próxima rodada tenta de novo. (4) **Nunca** número inventado: não se interpola, não se copia da noite vizinha, não se estima pela FC do treino.
No pacote isso é `recuperacao.estado = sem_dado` (`sem_noite`) ou a medida `sem_dado`. (5) O formato exato do "dia sem dado" na resposta (campo ausente, valor zero, `None`, lista vazia) é da #371; **valor zero ou fora da faixa dos `CHECK` é tratado como sem dado pelo leitor**, nunca gravado.

**Apagar (LGPD).** `uv run python -m worker.apagar_recuperacao --atleta "<nome>"` (#372): apaga todas as linhas de `recuperacao_dia` do atleta e imprime só a contagem (`recuperacao: apagadas=N`); idempotente; mesmo tratamento de nome repetido (menor id) e inexistente (código 1) dos demais comandos.
Apagar a recuperação deixa **desatualizados** os feedbacks que a usaram (item 4(b)), que serão refeitos **sem** ela. O atleta e as atividades ficam. `worker.apagar_checkin` não muda. Apagar o atleta apaga tudo pela cascata.

**Dado de saúde (a regra da Meta 6, ADR 0010 item 2, ADR 0012 item 5 e ADR 0013 item 2, aplicada à recuperação).** `recuperacao_dia` é dado de saúde: **só no banco local**; nunca em log, exceção, captura, fixture real ou arquivo versionado; sem rota que a devolva
(a API só a usa por dentro, para montar o pacote; a recuperação aparece **só no texto do feedback**, decisão 6); comando para apagar; comandos imprimem só contagens. **Fixtures são escritas à mão** (a #371 cria o formato; a #372 e as demais só usam fixtures sintéticas), nunca uma resposta gravada
da conta de ninguém.

### 6. Regras de linguagem novas (`checagens_feedback@3`, #375)
As checagens da ADR 0013 (item 4) continuam; a lista de linguagem proibida ganha o que vem **com a recuperação** (sobe `checagens_feedback@2` para `@3`; a `@2` é a do #367, se houver). Em duas partes:

**A. Palavras e expressões novas** (sem acento e sem diferença de maiúscula, como as demais):
- **Causa ligando recuperação a resultado**: "por isso", "então", "portanto", "logo", "assim", "daí", "reflete", "refletiu", "reflexo", "influenciou", "influência", "afetou", "impactou", "pesou", "contribuiu", "efeito do sono", "efeito da noite", "explica", "o sono explica", "culpa do sono", "mesmo com", "apesar de", "apesar do", "mesmo assim", "mas" e "porém" entre a recuperação e o resultado, "no entanto", "enquanto" quando liga as duas ideias. (A ADR 0013 já proíbe "porque", "por causa", "devido", "causou"...)
- **Conselho**: "durma", "dormir mais", "dormir cedo", "vá dormir", "descanse", "priorize", "durma pelo menos", "o ideal é dormir". (A ADR 0013 já proíbe "descanse", "evite", "tente"...)
- **Julgamento da noite**: "noite ruim", "noite boa", "mal dormido", "mal dormiu", "dormiu mal", "dormiu bem", "sono curto", "sono bom", "sono pouco", "sono insuficiente", "pouco sono", "bem recuperado", "mal recuperado", "recuperado", "descansado", "cansado", "VFC baixa", "VFC alta", "FC de repouso alta", "FC de repouso baixa", "melhor", "pior", "boa recuperação", "má recuperação". Vale a direção só com **"abaixo/acima do seu normal"** e **"dentro do seu normal"**.
  Atenção ao atalho "sono ruim" do check-in (ADR 0013, item 4, exceção por frase exata): continua permitido **só como rótulo marcado pelo atleta** ("Você marcou sono ruim."); a checagem 2 de linguagem **não** pode aceitar "ruim" em frase da recuperação.
- **Diagnóstico e termos fisiológicos fora da conta**: "insônia", "apneia", "sistema nervoso", "parassimpático", "simpático", "estresse", "fadiga", "overreaching", "prontidão", "bateria", "Body Battery", "estado de treino", "readiness", "ansiedade", "arritmia" (já), "cardíaco" fora de "FC de repouso".

**B. Regras mecânicas (em código, com texto ruim que precisa reprovar):**
1. **Recuperação numa linha própria.** A frase que traz sono, VFC ou FC de repouso não traz nenhuma outra medida, nem pace, FC do treino, carga, clima ou check-in (cada linha = uma ideia, e a recuperação não divide a linha com o resultado). A checagem reprova a linha que mistura os vocabulários.
2. **Só a forma permitida.** A linha da recuperação usa "noite anterior" (ou equivalente do prompt), o valor do pacote, o normal do pacote e "abaixo", "acima" ou "dentro do seu normal". Sem estado `ok`, não se fala em recuperação; sem `aprendendo`, não se diz comparação.
3. **Só números do pacote**, na mesma checagem 1 da ADR 0013, que ganha as unidades `h`, `min` (em duração composta, "5 h 40 min" vale como **um** número), `ms` e `bpm`; "1 h 30 min" só passa se for o `diferenca_texto` do pacote. Número por extenso continua reprovando ("seis horas").
4. **Não falar de outro dia.** "Ontem", "anteontem", "semana", "média de 7 dias", "nos últimos dias", "esta semana" e qualquer dia da semana ou data reprovam na linha da recuperação: o pacote só tem a noite anterior e o normal.
5. **Sem recuperação no pacote, sem recuperação no texto.** Se `recuperacao` é `sem_dado`, o texto não cita sono, VFC nem FC de repouso, exceto a frase pronta de "sem dado" (item 4).
6. **Forma geral** continua: 3 a 5 linhas, 140 caracteres cada, até 700 no total. A linha da recuperação conta (o prompt da #375 pode enxugar outras para caber).

**Exemplos de frase (sintéticos, para o prompt da #375).** Em cada um, o texto ao lado do resultado, sem ligar os dois.
- **Bom, `abaixo`:** "Na noite anterior você dormiu 5 h 40 min, 1 h 30 min abaixo do seu normal de 7 h 10 min." (linha só da recuperação; as linhas do resultado vêm antes ou depois, sem "por isso").
- **Bom, `acima` e `dentro`:** "Na noite anterior, a FC de repouso foi 55 bpm, 3 bpm acima do seu normal de 52 bpm. A VFC foi 47 ms, dentro do seu normal." (só números do pacote.)
- **Bom, `aprendendo`:** "Na noite anterior você dormiu 6 h 20 min. Ainda estou..." **não**: a frase correta é "Na noite anterior você dormiu 6 h 20 min. Ainda aprendendo o seu normal de sono: 9 de 14 noites."
- **Bom, `sem_dado`:** "Sem dado de sono, VFC e FC de repouso da noite anterior."
- **Ruim (precisa reprovar):** "Você correu mais devagar porque dormiu pouco." (causa; "pouco sono"); "Dormir mais pode ajudar nos próximos treinos." (conselho); "Com 5 h 40 min de sono, o ritmo caiu." (une recuperação e resultado na mesma linha); "Seu sono foi ruim e sua VFC está baixa." (julgamento); "Seu sono ficou 1,5 h abaixo do normal." (número que não está no pacote); "Nos últimos dias você dormiu menos." (outro dia).

### 7. Como ficam os estados de ponta a ponta (resumo)
| Situação | `recuperacao.estado` | `medidas[].estado` | O que o texto pode |
|---|---|---|---|
| Noite com as três medidas e 14 ou mais noites de histórico | `ok` | `dentro`/`abaixo`/`acima` | valor, normal e direção |
| Noite com sono e FC de repouso, sem VFC | `ok` | `vfc: sem_dado` | só o que tem |
| Menos de 14 noites com valor de uma medida | `ok` | `aprendendo` | valor e "aprendendo (n de 14)" |
| Relógio não sincronizou, conta sem dado, busca nunca rodou | `sem_dado` (`sem_noite`) | (sem `medidas`) | dizer que não há dado, ou omitir |
| Treino antes das 06:00 | `sem_dado` (`treino_de_madrugada`) | (sem `medidas`) | omitir (padrão) |
| Recuperação apagada | `sem_dado` (`sem_noite`) | (sem `medidas`) | feedback refeito sem a recuperação |

## Alternativas consideradas
- **Uma tabela por medida** (sono, VFC, FC de repouso). Três tabelas e três buscas para o mesmo dia; o atleta pensa na noite como uma só. Descartada: uma linha por noite, medidas anuláveis.
- **Guardar o horário de dormir e de acordar.** Resolveria o treino de madrugada, mas é dado de hábito além das três medidas que o Angelo autorizou (decisão 2). Descartada; fica o corte das 06:00 (A confirmar, item 3).
- **Guardar a linha de "noite sem dado".** Evitaria rebuscar noites vazias, mas uma noite vazia hoje pode chegar depois (sincronização tardia) e a linha vazia seria mais um estado a manter. Descartada: a ausência da linha é o "sem dado".
- **Guardar o "normal" calculado.** Teria de ser refeito a cada noite nova. Descartada, como a linha de base: calcula-se na leitura.
- **Marcar o feedback desatualizado quando o normal muda.** Refaria todos os feedbacks recentes a cada noite nova e gastaria chamadas. Descartada (como na ADR 0013).
- **Sem a coluna `recuperacao_importada_em`; recuperação só no `--refazer`.** Mais simples, mas o feedback de um treino de manhã gerado antes de o relógio sincronizar ficaria para sempre sem a recuperação até alguém lembrar do `--refazer`. Recomendação: a coluna (A confirmar, item 5).
- **Limiar absoluto** ("menos de 6 h de sono", "FC de repouso acima de X"). É julgamento clínico sem a nossa fonte. Descartada: só o normal do próprio atleta.
- **Média de 7 dias da VFC contra uma faixa de base (como o Garmin).** Mais estável, mas pede uma série de 7 noites no pacote ou um número a mais para explicar, e o Angelo decidiu que a série não vai ao provedor. Descartada nesta meta; a mediana da janela de 28 noites já suaviza.
- **Z de média e desvio padrão no lugar de mediana e MAD.** Uma noite muito fora do comum (doença, viagem) desloca média e desvio. Descartada (ADR 0011).
- **Exportação do Garmin como segunda fonte.** A exportação traz sono e FC de repouso, mas o formato e o ciclo de importação são outros (e a ADR 0010 só a usa para saúde de exportação). Fora desta meta; se a #371 mostrar que sai de graça, vira issue própria.
- **Estimar sono ou VFC quando falta** (pela FC do treino, pela noite vizinha). Proibido: números só por código a partir de dado medido.

## Consequências
- Existe um dado novo de saúde (`recuperacao_dia`) com a regra da Meta 6 e comando para apagar; nenhuma rota o devolve.
- `fatos_treino` sobe a `@2`; **todos os feedbacks gerados com a `@1` ficam desatualizados** e são refeitos pelo worker, com o limite de chamadas por execução. O texto antigo é substituído.
- `feedback_treino` ganha uma coluna anulável; `worker.apagar_checkin` continua igual.
- Nasce `recuperacao@1`; sobem `feedback_prompt@3` e `checagens_feedback@3` (as `@2` ficam com a #367).
- A API **não** ganha campo nem rota nova: o `GET` da atividade continua com os cinco estados do `feedback`; só o texto muda. Sem adendo da ADR 0004 (confirmar com a Duda na #374).
- A migração `0014` é aditiva e reversível.

## Limitações
- **Biblioteca não oficial** do Garmin Connect: pode parar de funcionar quando o Garmin mudar o login ou os campos; aceito para o piloto local (decisão 3). Produção exige a API oficial e outro modelo de consentimento.
- **A VFC e o sono são medidas proprietárias do Garmin** (algoritmo fechado): esta ADR usa o número publicado, na unidade publicada, e **não** o interpreta. O Garmin pode recalcular uma noite (por isso o upsert atualiza).
- **Sem horário de acordar:** o treino de madrugada fica sem recuperação, e o treino logo depois de acordar usa a noite certa só se começar às 06:00 ou depois; um atleta que acorda às 04:30 e treina às 05:00 fica sem recuperação por causa do corte (perda aceita, melhor que a noite errada).
- **Fuso:** quem viaja entre fusos pode ter uma noite duplicada ou ausente.
- **Um dia sem uso do relógio** deixa a noite sem dado; com menos de 14 noites com valor, a medida fica `aprendendo` (início frio de cerca de duas semanas com o relógio no pulso).
- **O normal é do próprio atleta, não da população** e a janela de 28 noites segue tendências lentas (mudança de rotina, viagem, doença): uma fase longa fora do padrão vira o "normal". Os parâmetros (28, 14, 0,05, 2,0) são escolhas nossas, sem calibração, e valem a mesma ressalva do `PISO_REL` da linha de base.
- **O texto de uma LLM pode ser inexato mesmo passando nas checagens** (ADR 0013). Aqui há um risco a mais: o texto pôr a noite e o resultado próximos de um jeito que **sugere** causa sem usar as palavras da lista. As regras mecânicas (item 6B) reduzem; a rodada pequena (#376) lê textos reais de fixtures para procurar isso.
- **Correlação não é causa.** Mesmo lado a lado, o atleta pode ler a ligação. A Meta 10 não estima quanto o sono pesou no resultado; isso é o motor de explicação (outra meta).
- **Sem login:** "só ao próprio atleta" é o `atleta_id` da rota, como no check-in; identidade é de outra meta.
- **Provedor externo:** o bloco `recuperacao` é dado de saúde que sai da máquina quando o provedor é real; vale a autorização do Angelo (só local, só o pacote) e as ressalvas da ADR 0013, item 10 de "A confirmar".

## Fora desta ADR
Estágios do sono, estresse, prontidão, estado de treino, Body Battery e qualquer métrica proprietária do Garmin; tela própria da recuperação; alerta de recuperação baixa; motor de explicação com peso de fator ("provável", "possível"); treinos planejados do Garmin;
exportação do Garmin como segunda fonte da recuperação; API oficial do Garmin; outros atletas; sesta; série diária na API; média semanal; a recuperação ligada ao check-in.

## Fontes
- **Conferido no código** (12/11): `garminconnect==0.3.20` (assinaturas e docstrings de `get_sleep_data`, `get_sleep_daily`, `get_rhr_day`, `get_rhr_daily`, `get_hrv_data`, `get_hrv_data_range`), sem rede e sem conta. **Não** conferido: nomes dos campos das respostas e o formato do dia sem dado (#371).
- Leys, C., Ley, C., Klein, O., Bernard, P. e Licata, L. (2013), Hampel (1974) e Rousseeuw e Croux (1993): mediana, MAD, constante 1,4826 e limites 2, 2,5 e 3, **como na ADR 0011, citações ainda não conferidas nos textos** (pendência do Caio, antes da nota da métrica).
- Garmin, ajuda do *HRV status* (páginas de manual `www8.garmin.com/manuals/webhelp/...`, "Heart Rate Variability Status"): cerca de três semanas de leituras noturnas para formar a faixa de base e comparação de uma média de 7 dias com ela. Lido em 12/11 numa busca que resume a página, **não aberta por inteiro**; serve só como ordem de grandeza da janela, não como fonte da regra.
- Plews, D. J., Laursen, P. B., Stanley, J., Kilding, A. E. e Buchheit, M. (2013). *Training adaptation and heart rate variability in elite endurance athletes: opening the door to effective monitoring.* Sports Medicine, 43(9), 773-781. Só o **resumo** foi lido (12/11): a VFC é usada para acompanhar a adaptação ao treino de resistência. **Não** é fonte de nenhuma escolha desta ADR (o artigo trata de médias móveis de VFC em atletas de elite; não adotamos o método). Citada como contexto.
- Regra própria do projeto, sem artigo: janela de 28 noites, mínimo de 14, `PISO_REL = 0,05`, limite 2,0, corte das 06:00, a lista de linguagem, as regras mecânicas e o corte "só a noite anterior ao provedor" (decisão 4 do Angelo).

## A confirmar
Cada item tem o **recomendado** (o padrão se o Angelo não responder). Itens 1 e 2 são do Angelo; 3 a 6, do Angelo com o Caio; 7 e 8 são técnicos (Theo e Duda).
1. **Guardar o dia sem dado como "sem dado" ou deixar sem linha?** *Recomendação:* sem linha (a ausência é o "sem dado"; o `CHECK` proíbe linha vazia). *Angelo (ciente) e Duda.*
2. **Os feedbacks já gerados (`fatos_treino@1`) devem ser refeitos com a recuperação?** Refazer troca o texto que ele já leu, e gasta chamadas do plano gratuito (20 por execução). *Recomendação:* sim, refazer (é a consequência da versão; o guia avisa). Alternativa: só os treinos novos e os com `--refazer`, o que deixa dois "jeitos" de feedback no histórico. *Angelo.*
3. **Treino de madrugada (antes das 06:00):** *Recomendação:* sem recuperação, e o texto **omite** a recuperação (sem frase de "sem dado"). Alternativa: guardar o horário de acordar (mais um dado de hábito, além das três medidas autorizadas) e usar a noite certa. *Angelo.*
4. **O limite do "fora do normal" (2,0) e a janela de 28 noites com mínimo de 14.** *Recomendação:* valem como estão e são revistos após uns 30 dias de uso, olhando só a contagem de `abaixo`/`acima` (sem ver os valores no repositório). Alternativa: 2,5 como na linha de base (menos avisos). *Angelo e Caio.*
5. **A coluna extra `recuperacao_importada_em` em `feedback_treino`** para refazer o feedback quando a noite chega ou muda. *Recomendação:* sim (item 4(b)). Alternativa: sem a coluna, só `--refazer` manual. *Theo.*
6. **Quando a noite falta, o texto diz "Sem dado de sono..." ou omite?** *Recomendação:* diz, exceto em treino de madrugada (omite); o atleta sabe que o relógio não enviou. Alternativa: sempre omitir, para o cartão não ter uma linha de "falta". *Angelo e Lia.*
7. **A origem `garmin_connect` e a chave `(atleta_id, origem, noite)`.** *Recomendação:* origem na chave, como em `carga_garmin_dia`, mesmo com uma só fonte hoje. Alternativa: chave só `(atleta_id, noite)`, e a API oficial substituiria a linha. *Theo e Duda.*
8. **Busca inicial de 35 noites e rebusca das 3 últimas.** *Recomendação:* sim. Pode ser ajustada por `--desde`. Ao chamar o Garmin 3 vezes por faixa (sono, VFC, FC de repouso), a primeira rodada faz cerca de 6 chamadas. *Duda.*

## Data e quem decidiu
2026-11-12. Proposta do Caio (ciência), com revisão da Duda (modelo de dados, busca e apagar) pedida no PR. Decisões do Angelo de 12/11 ("ok para as nove") no Contexto. Issue #370.
Modelo de dados: **aguardando aprovação do Theo.** Status `proposta` até o Theo aceitar e o Angelo responder o "A confirmar".
