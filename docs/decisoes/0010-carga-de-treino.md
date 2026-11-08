---
tipo: decisao
status: aceita
dono: caio
atualizado: 2026-11-08
links: [[decisoes/0001-modelo-de-dados-minimo]], [[decisoes/0002-segmento-intensidade-e-versao]], [[decisoes/0003-fuso-da-atividade]], [[decisoes/0004-contrato-tela-evolucao]], [[decisoes/0006-upload-de-fit]], [[decisoes/0008-deteccao-de-esforcos]], [[decisoes/0009-treino-de-transicao]], [[modulos/banco]], [[modulos/ingestao-garmin]], [[produto/roadmap]], [[glossario]]
---
# ADR: 0010 Carga de treino (rTSS, hrTSS, CTL, ATL e TSB)

> Aceita em 07/11 (issue #134): modelo de dados aprovado pelo Theo e citações conferidas. O Angelo respondeu "sim" às sete propostas de produto em 07/11
> (seção "A confirmar"). **Nenhuma linha de código nem migração muda neste PR.** Todos os números são sintéticos. Os nomes concretos
> de arquivo e de campo da exportação ficam na nota [[modulos/ingestao-garmin]] (#135), não nesta ADR.
> Dá base para #136, #137, #138, #139, #140, #141, #142, #144 e #174.

## Contexto
A Meta 6 entrega a primeira métrica derivada de carga: a carga de cada atividade (**rTSS** pelo pace, **hrTSS** pela FC) e, dia a
dia, condicionamento (**CTL**), fadiga (**ATL**) e forma (**TSB**). Sempre estimativa, nunca medida.

**Decisões de produto já tomadas (Angelo, 04/11, e Theo, 06/11, #230), que esta ADR respeita:**
- O limiar vem dos **dados de saúde da exportação Garmin**. **Nunca se estima o limiar** a partir do histórico de atividades.
- Atleta sem os dados de saúde importados fica **"sem carga"**, com o motivo. Atividade anterior ao primeiro limiar importado também:
  **nunca se usa um limiar posterior**.
- Todos os dados de saúde (limiar com vigência, zonas de FC, recordes pessoais, carga aguda/crônica do Garmin) são **guardados**, só no
  banco local.
- A carga **ignora** atividades com `subtipo` em (`multiesporte_pai`, `troca`), para não contar duas vezes.
- A conferência com o Garmin é local; os números do histórico real ficam só em `entregas/` (fora do git).

### O que o código do `main` mostra (conferido em 07/11, commit `bbdd7cf`)
- `Atividade` (`services/api/app/db/models.py`) tem `modalidade` (`corrida`, `natacao`, `ciclismo`, `outra`), `subtipo` (texto livre:
  `esteira`, `pista`, `trilha`, `piscina`, `aguas_abertas`, `virtual`, `multiesporte_pai`, `troca`), `inicio` (UTC), `fuso_min` (ADR 0003),
  `duracao_s` (**tempo em movimento**, `total_timer_time`), `distancia_m` e `fc_media`. Não há FC máxima, limiar nem zona.
- `Segmento` tem, **por volta**, `ordem`, `inicio_offset_s`, `duracao_s`, `distancia_m`, `fc_media` (inteiro, anulável) e `pace_s_km`
  (anulável: `NULL` com distância 0). `segmento.zona` existe e **nunca é preenchida**. Não há série por segundo: o leitor FIT
  (`ingestao/garmin/fit.py`) só lê `session` e `lap`.
- `bloco_atividade` (ADR 0008) existe só para corrida e ciclismo e é recalculado quando `esforcos@N` sobe.
- As tabelas derivadas do `main` seguem o mesmo padrão: uma tabela por derivado, FK `ON DELETE CASCADE` para `atividade`, `versao_*` em
  texto `<regra>@<n>` (ADR 0002) e `CHECK` em vez de enum (`clima_atividade`, `bloco_atividade`, `rotulo_transicao`). A última migração é
  a `0007`; a próxima é a `0008`.
- A importação (`ingestao/importacao.py`) é idempotente por `(atleta_id, fonte, fonte_id)`, sem rede por padrão, e chama a classificação no
  fim, com erro virando aviso. O upload de FIT (ADR 0006) **não traz dados de saúde**.
- `metricas/` hoje: `esforcos.py`, `tiros_1km.py`, `transicao.py`. Não existe nenhuma métrica de carga, limiar nem CTL.

## Decisão

### 1. Limiar do atleta, com vigência e origem
Tabela nova **`limiar_atleta`**: uma linha por (grandeza, início de vigência).

| Coluna | Tipo | Observação |
|---|---|---|
| `id` | inteiro, chave | |
| `atleta_id` | FK `atleta.id` | indexada |
| `grandeza` | texto (20), `CHECK` | `fc_bpm` (FC de limiar, bpm) ou `velocidade_ms` (velocidade de limiar, m/s) |
| `valor` | float, não nulo | `CHECK valor > 0` |
| `vigente_desde` | date | dia (do calendário, sem fuso) em que o valor passou a valer; é o que a fonte entrega |
| `origem` | texto (20), `CHECK` | `garmin_export` agora; `informado` reservado (o atleta digitar o valor, fora da Meta 6) |
| `versao_leitura` | texto (40) | versão do leitor que gravou, ex. `saude_garmin@1`; mesmo formato da ADR 0002 |
| `importado_em` | datetime com fuso | |

**Idempotência:** `UNIQUE (atleta_id, grandeza, origem, vigente_desde)`. Reimportar o mesmo registro não duplica.

**Por que uma linha por grandeza, e não uma linha com as duas colunas:** a fonte pode registrar a FC e a velocidade de limiar em datas
diferentes. Uma linha por grandeza deixa cada série ter o seu próprio histórico, sem linhas com metade `NULL`.

**Qual limiar vale para uma atividade.** Para a grandeza `g` e a atividade com data local `t` (`data_local(inicio, fuso_min)`, ADR 0003):
a linha de maior `vigente_desde` com `vigente_desde <= t`. Se há linhas de duas origens para o mesmo dia, `informado` vence
`garmin_export` (só `garmin_export` existe na Meta 6). Um limiar registrado no dia da atividade já vale para ela. A vigência termina
quando a próxima começa; **não há** `vigente_ate` nem prazo de validade. Se não existe linha com `vigente_desde <= t`: **não há limiar
na data**, e **nunca** se olha para a linha seguinte. O leitor guarda uma linha por grandeza e dia, com o último valor de cada campo
(os registros da fonte trazem só o que mudou).

**Pace de limiar** = `1000 / velocidade_ms` s/km. Guardamos velocidade porque é a grandeza em que o IF é linear e (a confirmar na #135)
o que a fonte traz.

### 2. Tabelas dos demais dados de saúde
Todas guardam **dado fisiológico, sensível pela LGPD**: só no banco local, nunca em log, nunca em fixture real, nunca no git. A API
da Meta 6 **não devolve** nenhum destes valores (a carga sai pronta); o `GET` mostra só a carga, o método e o motivo.
Todas têm `atleta_id` (FK `atleta.id`), `origem` (`CHECK`, `garmin_export`), `versao_leitura` e `importado_em`, como a de limiar.

**`zona_fc_atleta`**: zonas de FC com vigência.

| Coluna | Observação |
|---|---|
| `esporte` | texto (20): perfil de esporte a que as zonas se aplicam (`padrao`, `corrida`, `ciclismo`...); valores a confirmar na #135 |
| `vigente_desde` | date: o dia do retrato (dia da importação) na origem `garmin_export`; o dia local da sessão na origem `garmin_fit` |
| `metodo` | texto (40): como a fonte calcula as zonas (por % da FC máxima, da reserva, do limiar...); **guardado como veio**, sem `CHECK` (a lista real é a confirmar) |
| `fc_max_bpm`, `fc_repouso_bpm` | inteiros, anuláveis: os usados no cálculo das zonas |
| `zona1_min_bpm` ... `zona5_min_bpm`, `zona5_max_bpm` | inteiros: limites inferiores das cinco zonas e o teto da quinta (a confirmar que são cinco) |

**Origem das zonas (achado da #135).** A exportação só tem o retrato atual, sem data; o histórico existe apenas nos FIT, por sessão.
Proposta: `origem` das zonas aceita `garmin_export` (o retrato, datado pelo dia da importação, só para exibir "as zonas de hoje") e
`garmin_fit` (uma linha por mudança de zonas vista nos FIT importados; só há histórico para atividades com FIT). A `carga` não depende
disso. Se o Theo preferir, a tabela fica só com o retrato ou sai da Meta 6 (decisão em "A confirmar").

Chave: `UNIQUE (atleta_id, esporte, origem, vigente_desde)`. **Quem usa:** nenhuma métrica da `carga`. Ficam guardadas para o hrTSS
por zonas e para `segmento.zona`, em versão futura. A decisão de guardar é do Angelo (04/11).

**`recorde_pessoal`**: recordes pessoais.

| Coluna | Observação |
|---|---|
| `modalidade` | texto (20), mesmos valores de `atividade.modalidade` |
| `categoria` | texto (60): o código do recorde **como a fonte traz** (distância ou duração); o mapeamento para `d1000`, `t20` etc. é da calibração futura |
| `valor` | float, não nulo; `unidade` texto (10): `s`, `m`, `W`, `passos` ou nulo (ver o adendo), conforme a categoria |
| `alcancado_em` | datetime com fuso: data em que o recorde foi batido |
| `atividade_fonte_id` | texto (100), anulável: id da atividade na fonte, **sem FK** (a atividade pode não estar importada) |

Chave: `UNIQUE (atleta_id, origem, modalidade, categoria, alcancado_em)`. **Quem usa:** a detecção de esforços, numa calibração futura
(ADR 0008, item 7, `esforcos@2`). A `carga` não usa.

**`carga_garmin_dia`**: carga aguda e crônica calculadas pelo Garmin, um valor por dia.

| Coluna | Observação |
|---|---|
| `dia` | date: dia do registro, como a fonte entrega (local ou UTC, a confirmar na #135) |
| `carga_aguda`, `carga_cronica` | float, anuláveis (a fonte pode trazer só uma); **na escala do Garmin**, que não é a do TSS |
| `razao` | float, anulável: razão aguda/crônica, se a fonte traz; não é recalculada por nós |

Chave: `UNIQUE (atleta_id, origem, dia)`. **Quem usa:** só a conferência (item 8). Nunca entra na nossa carga.

**Mudança de valor na fonte.** Um registro com chave nova vira linha nova (histórico). Um registro com a **mesma chave e valor diferente**
(correção da fonte) **atualiza a linha** e conta como `atualizada`, com aviso; é o único caso de sobrescrita.
Nenhum registro é apagado por uma reimportação que não o traz (uma exportação mais curta não apaga o histórico).

### 3. Caminho de ingestão dos dados de saúde
- **Leitor puro** em `services/api/app/ingestao/garmin/saude.py`: lê os arquivos de saúde da exportação (nomes na #135) e devolve
  registros tipados. Sem banco e sem rede. Mesma regra do leitor atual: procura por **sufixo**, nunca por nome exato.
- **Gravação** em `services/api/app/ingestao/saude.py`: `importar_saude(session, caminho, atleta_nome)`, idempotente pela chave de cada
  tabela, devolvendo `inseridas`, `atualizadas`, `ignoradas` e avisos **por tabela**. Não grava valor em log; só contagens.
- **Comando próprio** `uv run python -m worker.importar_saude <caminho> --atleta "<nome>"`, e o `importar_garmin` chama a mesma função **no
  fim** da importação das atividades (mesma política da detecção de esforços: erro vira aviso e **não derruba** a importação das
  atividades; arquivo de saúde ausente é aviso, não erro).
  Motivo de ser função separada: falha, ausência e reexecução dos dados de saúde são independentes das atividades (quem importou só o
  FIT, ou importou a exportação antes desta Meta, roda só o comando de saúde).
- **Sem rede.** O upload de FIT (ADR 0006) não passa por aqui: atleta que só usa o upload fica `sem_dados_saude` até importar a
  exportação completa.
- **Limiar ou zona que muda** = linha nova com nova vigência, nunca edição da anterior (item 2, regra de chave). Quem recalcula é a carga
  (item 5), pela entrada da conta, e não a importação.
- **Apagar:** `worker.apagar_saude --atleta` (LGPD) remove as quatro tabelas de saúde do atleta; fica para a #174 detalhar.
- Depois de gravar a saúde, a importação chama o cálculo da carga do atleta (`worker.calcular_carga`, #141), também com erro virando aviso.

### 4. Fórmula por volta, método por modalidade e a versão `carga@1`
**Unidade comum.** Todas as fórmulas usam a forma do Training Stress Score: `TSS = horas x IF^2 x 100`, em que `IF` (fator de
intensidade) é a razão entre a intensidade e a de limiar. **Uma hora no limiar vale 100.** Fonte: Coggan, A. & Allen, H.,
*Training and Racing with a Power Meter* (VeloPress), e o artigo "The Development of the Training Stress Score" do TrainingPeaks:
`TSS = (s x NP x IF) / (FTP x 3600) x 100`, que com `NP = IF x FTP` é `horas x IF^2 x 100` (ver "Fontes conferidas").

**rTSS por volta** (corrida, pace). Para a volta `i` com `duracao_s > 0` e `distancia_m > 0`:
```
v_i  = distancia_m_i / duracao_s_i                 (m/s)
IF_i = v_i / velocidade_limiar                     (= pace_limiar / pace_i)
rTSS_i = (duracao_s_i / 3600) x IF_i^2 x 100
```
Fontes: o rTSS do TrainingPeaks (*Running Training Stress Score (rTSS) Explained*), que usa o pace ajustado à subida (NGP) contra o
pace de limiar; e, como origem da ideia "100 = o esforço de teste na velocidade de limiar", Skiba, P. F. (2006), *Calculation of Power
Output and Quantification of Training Stress in Distance Runners: The Development of the GOVSS Algorithm* (GOVSS não é a fórmula do
rTSS do TrainingPeaks; só contexto). **Aqui não há ajuste de subida**: usa-se a velocidade bruta da volta (limitação declarada, item 9).

**hrTSS por volta** (corrida e ciclismo, FC). Para a volta `i` com `duracao_s > 0` e `fc_media` presente:
```
IF_i = fc_media_i / fc_limiar
hrTSS_i = (duracao_s_i / 3600) x IF_i^2 x 100
```
**Atenção: este hrTSS não é o do TrainingPeaks.** O do TrainingPeaks é por **tempo em zona de FC** (zonas a partir da FC de limiar, com
uma tabela de pontos), e não por razão ao quadrado. O nosso é uma **adaptação**: a mesma forma do TSS (`horas x IF^2 x 100`) com o IF
tirado da FC, análogo ao hrTSS "estilo potência" descrito na literatura de divulgação. Mantém a escala (100 = 1 h no limiar), mas os
valores não são comparáveis aos do TrainingPeaks. Usa só a FC de limiar, sem zonas nem FC de repouso. O hrTSS por zonas, a variante
pela reserva de FC e o TRIMP de Banister (Banister, E. W. (1991), "Modeling elite athletic performance", em MacDougall, Wenger & Green
(eds.), *Physiological Testing of the High-Performance Athlete*, 2a ed., Human Kinetics, p. 403-425) ficam como alternativa (`carga@2`).

**Carga da atividade** = soma da carga das voltas (`segmento`, **de todos os `tipo`**: `volta`, `tiro` e `recuperacao`, pois a
recuperação também é carga). Usa as **voltas e não os blocos** da ADR 0008, por três motivos: (a) blocos existem só para corrida e
ciclismo e são recalculados quando `esforcos@N` sobe, o que acoplaria a carga a outra regra versionada; (b) a volta é o dado importado,
sem interpretação; (c) `IF^2` é convexo, então juntar voltas de ritmos diferentes **subestima** a carga, e a volta é o grão mais fino que
o leitor entrega. Uma atividade **sem voltas** (JSON sem FIT) é tratada como **uma volta única** (`duracao_s`, `distancia_m`,
`fc_media`), com `granularidade = 'atividade'` (mais grosseira, mesmo critério).

**Cobertura.** Uma volta sem o dado do método (sem FC no hrTSS, sem distância no rTSS) conta 0 e **não é inventada**. O método só vale se
as voltas com dado cobrem **pelo menos 95%** da soma das durações (`COBERTURA_MIN = 0,95`); a cobertura fica gravada. Abaixo disso, o
método não vale.

**Qual método vale, por modalidade:**

| Modalidade | Caminhos possíveis, em ordem | Observação |
|---|---|---|
| `corrida` (fora da esteira) | rTSS, depois hrTSS | rTSS vence quando há velocidade de limiar na data **e** cobertura; senão hrTSS |
| `corrida` com `subtipo = esteira` | só hrTSS | a distância da esteira vem do sensor do aparelho, não do GPS; o pace é pouco confiável |
| `ciclismo` (inclui `virtual` e `esteira`) | só hrTSS | sem potência no modelo; a FC é real mesmo no pedal virtual |
| `natacao` | nenhum: `modalidade_sem_carga` | não há limiar de natação nos dados, e a FC de limiar de outra modalidade não vale na água |
| `outra` | nenhum: `modalidade_sem_carga` | |
| `subtipo` em (`multiesporte_pai`, `troca`) | **fora da conta** (item 5) | |

O rTSS vence quando há as duas: o pace não sofre com a deriva cardíaca, o calor nem o atraso da FC em blocos curtos. Quando os dois
existem, **ambos são gravados** (`carga_rtss`, `carga_hrtss`), e `carga` é a do método vencedor. Isso é a matéria-prima da conferência.
Os dois estão na mesma escala (100 = 1 h no limiar), então cair de rTSS para hrTSS não muda a unidade, só a precisão.

**Exemplo 1 (rTSS, sintético).** Velocidade de limiar 1000/270 = 3,7037 m/s (pace de limiar 270 s/km). Volta A: 1000 m em 300 s:
IF = 270/300 = 0,9; rTSS = 300/3600 x 0,81 x 100 = **6,75**. Volta B: 1000 m em 240 s: IF = 270/240 = 1,125;
rTSS = 240/3600 x 1,265625 x 100 = **8,4375**. Atividade = **15,1875**. Sanidade: 1 h a 270 s/km dá IF = 1 e carga 100.

**Exemplo 2 (hrTSS, sintético).** FC de limiar 170 bpm. Volta A: 300 s a 153 bpm: IF = 0,9, hrTSS = **6,75**. Volta B: 240 s a
187 bpm: IF = 1,1; hrTSS = 240/3600 x 1,21 x 100 = **8,0667**. Atividade = **14,8167**.

**Exemplo 3 (cobertura).** 10 voltas de 100 s (1000 s), 9 com FC e uma sem: cobertura 90% < 95%, o hrTSS não vale
(`cobertura_insuficiente`). Com 20 voltas de 50 s e uma sem FC, a cobertura é 95% e vale: a volta sem FC conta 0.

**Versão `carga@1`** (hoje `carga@2`, ver o adendo de 08/11). Constante `VERSAO = "carga@1"` em `services/api/app/metricas/carga.py`, no formato `<regra>@<n>` da ADR 0002.
**Sobe** quando mudar: a fórmula; o método preferido; `COBERTURA_MIN`; a lista de motivos ou a regra que escolhe o motivo; a tabela de
modalidade e subtipo; ou a regra de qual limiar vale. Subindo a versão, `worker.calcular_carga` recalcula todas as linhas de versão
antiga. As janelas de CTL/ATL (item 6) não fazem parte da `carga@1`.

### 5. Onde a carga fica: tabela própria `carga_atividade`
A ADR 0002 pediu para reavaliar a tabela de métrica derivada genérica (`metrica_derivada`) quando houvesse mais de uma métrica derivada.
Reavaliado: já existem três tabelas derivadas próprias e tipadas (`clima_atividade`, `bloco_atividade`, `rotulo_transicao`), e a carga é
uma só métrica com colunas fixas (carga, método, motivo, cobertura). Uma tabela genérica (`nome`, `valor`, `json`) perde `CHECK`, tipos e
índice por data, e esconde o motivo dentro de JSON. **Decisão: tabela própria**, no padrão das anteriores. `metrica_derivada` continua
sem existir.

**`carga_atividade`**: uma linha por atividade **elegível** (todas, menos as de subtipo ignorado).

| Coluna | Tipo | Observação |
|---|---|---|
| `id` | inteiro, chave | |
| `atividade_id` | FK única | `atividade.id`, `ON DELETE CASCADE` |
| `estado` | texto (20), `CHECK` | `calculada` ou `sem_carga` |
| `carga` | float, anulável | a do método vencedor; `NULL` em `sem_carga` |
| `metodo` | texto (10), anulável, `CHECK` | `rtss` ou `hrtss`; `NULL` em `sem_carga` |
| `carga_rtss`, `carga_hrtss` | float, anuláveis | cada uma só se o seu método valeu (cobertura e limiar) |
| `motivo` | texto (30), anulável, `CHECK` | só em `sem_carga` (item 7) |
| `cobertura_pct` | float, anulável | do método vencedor (ou do mais próximo de valer, em `sem_carga` por cobertura) |
| `granularidade` | texto (10), `CHECK` | `volta` ou `atividade` |
| `limiar_fc_bpm`, `limiar_velocidade_ms`, `limiar_vigente_desde` (date) | anuláveis | os valores de limiar **usados** (auditoria; a API não os devolve) |
| `entrada` | texto (64) | SHA-256 do que entrou na conta: modalidade, subtipo, voltas (duração, distância, FC) e os limiares usados |
| `versao` | texto (40) | `carga@2` (a `carga@1` até 08/11) |
| `calculado_em` | datetime com fuso | |

`CHECK`: `estado = 'calculada'` implica `carga`, `metodo` e `cobertura_pct` preenchidos e `motivo` nulo; `estado = 'sem_carga'` implica
`motivo` preenchido e `carga`, `metodo`, `carga_rtss`, `carga_hrtss` nulos. A linha **sem carga existe de propósito**: é ela que guarda o
motivo.

**Idempotência e recálculo.** `worker.calcular_carga` (#141) calcula `entrada` e `versao` e **só regrava a linha quando algum dos dois
mudou** (mesmo padrão do `clima_atividade`, ADR 0007). Efeitos:
- reimportar sem mudança não toca nada; rodar de novo não duplica (`atividade_id` único);
- uma nova vigência de limiar recalcula **só** as atividades cujo limiar usado mudou (inclusive a que passa de `sem_limiar_na_data`
  para calculada, quando entra um limiar mais antigo);
- subir `carga@N` recalcula tudo;
- a atividade cujo `subtipo` virou `multiesporte_pai` ou `troca` (reclassificação) **perde a linha**.

**Atividades ignoradas.** `multiesporte_pai` e `troca` **não têm linha** e **não aparecem como "sem carga"**: não são treino sem dado,
são atividades que não contam (o pai repete as partes; a troca não é treino). A série diária devolve a contagem delas num campo próprio
(`ignoradas_multiesporte`), só para o total fechar com o número de atividades importadas. Cada parte de um treino de transição (ADR 0009)
tem a sua carga; o grupo não soma nada além das partes.

**CTL, ATL e TSB: calculados na leitura, não gravados.** São uma recursão simples sobre a carga diária (poucos milhares de dias no
máximo); gravar criaria uma segunda cópia que precisaria ser invalidada a cada atividade nova, a cada limiar novo e a cada recálculo.
Calcular na leitura nunca fica desatualizado. A série tem versão própria na resposta, **`serie_carga@1`** (janelas, valor inicial e regra
do dia). Se o custo virar problema, grava-se depois como cache, sem mudar o contrato.

**Dia da atividade** = data local pela ADR 0003 (`data_local(inicio, fuso_min)`, com `America/Sao_Paulo` se `fuso_min` é `NULL`).

### 6. CTL, ATL e TSB
- **Janelas:** `TAU_CTL = 42` dias e `TAU_ATL = 7` dias (padrão do *Performance Management Chart* do TrainingPeaks; base teórica: modelo
  de impulso-resposta de Banister, Calvert, Savage e Bach, IEEE Trans. Syst. Man Cybern. SMC-6(2):94-102, 1976; ver "Fontes conferidas").
  Todo atleta usa as mesmas.
- **Recursão** (média móvel exponencial, na forma exata de decaimento), por dia `d`, com `L_d` a soma das cargas `calculada` do dia local:
  ```
  k_ctl = 1 - exp(-1/42)   (0,023528)       k_atl = 1 - exp(-1/7)   (0,133122)
  CTL_d = CTL_(d-1) + (L_d - CTL_(d-1)) x k_ctl
  ATL_d = ATL_(d-1) + (L_d - ATL_(d-1)) x k_atl
  TSB_d = CTL_d - ATL_d                          (como no glossário)
  ```
  Duas escolhas conscientes, conferidas nas fontes: (a) a forma exata `1 - exp(-1/tau)` (planilha do Golden Cheetah) em vez da
  aproximação `1/tau`, que dá 1,2% a mais no CTL e 7% a mais no ATL por passo; (b) o **TSB do TrainingPeaks é CTL e ATL do dia anterior**
  (a "forma da manhã"), enquanto o nosso é o do **fim do mesmo dia**, como no glossário. Os números do TSB, portanto, **não batem dia a
  dia** com os do TrainingPeaks; CTL e ATL batem a menos do item (a).
- **Dia sem treino:** `L_d = 0`; a série tem **todos os dias** entre o primeiro e o último, e CTL e ATL decaem.
- **Valor inicial:** `CTL = ATL = 0` **antes do primeiro dia com carga calculada**; a série começa nesse dia. Não se usa a carga do
  Garmin para semear (escala diferente) nem se estima um histórico anterior.
- **Fim da série:** o dia da última atividade importada do atleta (sem estender até hoje, para não mostrar o decaimento de dados que
  ainda não chegaram). Parâmetros opcionais de intervalo ficam para a #142.
- **"Ainda aprendendo":** o campo `aprendendo` é `true` enquanto o dia estiver a **menos de 42 dias** do primeiro dia da série
  (`dias_de_historico < 42`). Aos 42 dias com carga constante, o CTL chegou a 1 - 1/e = 63% do valor estável: é o limite honesto de "pouca
  história" e coincide com a janela. A tela mostra o aviso; os números continuam sendo devolvidos. O ATL, com janela de 7 dias,
  estabiliza antes e usa o mesmo marcador (mais conservador).
- **Dia incompleto:** um dia em que há atividade `sem_carga` fica marcado, e `L_d` conta só as calculadas. A série traz `atividades`,
  `calculadas` e `sem_carga` por dia, para o app não mostrar um dia de descanso onde houve treino sem dado.

**Exemplo 4 (sintético).** Cargas diárias 100, 0 e 50 a partir do primeiro dia:
dia 1: ATL = 100 x 0,133122 = 13,3122; CTL = 100 x 0,023528 = 2,3528.
dia 2: ATL = 13,3122 + (0 - 13,3122) x 0,133122 = 11,5401; CTL = 2,3528 + (0 - 2,3528) x 0,023528 = 2,2975.
dia 3: ATL = 11,5401 + (50 - 11,5401) x 0,133122 = 16,6599; CTL = 2,2975 + (50 - 2,2975) x 0,023528 = 3,4198; TSB = -13,2401.
(Valores de teste a conferir à mão e com planilha na #137.)

### 7. Sem dado: "sem carga" com motivo
`motivo` é um de seis valores (`CHECK`). A ordem de avaliação, para cada atividade:

1. `subtipo` em (`multiesporte_pai`, `troca`): fora da conta, sem linha (item 5).
2. `natacao` ou `outra`: `sem_carga` com **`modalidade_sem_carga`**.
3. Montam-se os caminhos da tabela do item 4 para a modalidade. **Um caminho está disponível se há limiar da sua grandeza na data**
   (rTSS: `velocidade_ms`; hrTSS: `fc_bpm`).
4. **Nenhum caminho disponível:** se o atleta não tem **nenhuma** linha em `limiar_atleta` das grandezas necessárias:
   **`sem_dados_saude`**; se tem, mas todas começam depois da atividade: **`sem_limiar_na_data`**.
5. Há caminhos disponíveis, mas nenhum com dado suficiente nas voltas: o motivo é o do **primeiro caminho disponível**, em ordem:
   **`sem_fc`** (hrTSS e nenhuma volta com FC), **`sem_pace`** (rTSS e nenhuma volta com distância e duração) ou
   **`cobertura_insuficiente`** (há dado, mas abaixo de 95%).
6. Caso contrário: `calculada`.

Assim o motivo sempre aponta o que o atleta (ou a importação) pode consertar: com limiar disponível para um caminho, o motivo é o dado
que falta **nesse** caminho, e não a falta de limiar do outro. Nunca se grava carga de atividade `sem_carga`, nem uma carga "aproximada".

**A série diz quantas ficaram de fora:** a resposta traz `sem_carga_total` e a contagem por motivo (`sem_dados_saude`,
`sem_limiar_na_data`, `sem_fc`, `sem_pace`, `cobertura_insuficiente`, `modalidade_sem_carga`), mais `ignoradas_multiesporte`. Atleta
sem os dados de saúde: nenhuma atividade `calculada`, **série vazia** (não há primeiro dia), e a contagem mostra todas como
`sem_dados_saude`. Jamais um número inventado.

### 8. Conferência com a carga do Garmin
A escala do Garmin **é outra** (a carga aguda/crônica dele vem de um modelo próprio, não de TSS; a descrição da fonte é item de "A
confirmar"). Por isso **não se compara igualdade nem valor absoluto**. Compara-se, nos dias em que as duas séries existem e em que
**nenhuma atividade ficou sem carga**:
- **tendência:** correlação de Spearman entre a nossa **ATL** e a carga aguda do Garmin, e entre a nossa **CTL** e a crônica;
- **variação:** correlação das **diferenças dia a dia** (tira a autocorrelação das médias móveis, que infla a correlação dos níveis);
- **defasagem:** a mesma correlação com deslocamento de -3 a +3 dias, para ver se as séries andam juntas ou uma atrasa;
- **razão:** a nossa ATL/CTL contra a razão do Garmin, em correlação, não em valor;
- **cobertura:** número de dias comparados e de dias descartados por atividade sem carga, sempre junto do resultado.

**Fixtures (CI):** uma série do Garmin sintética, construída para ter relação conhecida com a nossa, serve para testar o **código** da
conferência, não a fisiologia. **Histórico real: só local**, por script da #144, com os números **só em `entregas/meta-6/`** (fora do git,
`.gitignore`). No repositório, nota e PR dizem apenas que a conferência foi feita e o que se aprendeu em termos gerais, sem valores nem
datas. A conferência é **só descritiva** (decisão do Angelo, 07/11): não há faixa de aprovação; o resultado diz o que se observou, com a cobertura.

### 9. Limitações assumidas (repetidas na nota da métrica)
- **Sem ajuste de subida nem de calor** no rTSS: a subida deixa o pace lento e subestima a carga; a descida faz o contrário.
  Uma versão futura (`carga@2`) lê a série por segundo (`record`) e usa o pace ajustado.
- **Voltas, não segundos:** `IF^2` por volta subestima treinos com variação dentro da volta.
- **hrTSS pela razão direta** ignora FC de repouso e deriva cardíaca, e o limiar de FC da fonte pode ser de corrida: no ciclismo tende a
  subestimar (a FC de limiar na bicicleta costuma ser menor). Sempre estimativa.
- **Esteira** só por FC; **natação e `outra`** sem carga.
- **Tempo em movimento:** `duracao_s` não conta o tempo parado, então a carga não conta a pausa do cronômetro.
- **Recálculo em dois níveis:** a carga por atividade é gravada e versionada; a série CTL/ATL é calculada na hora.

## Alternativas consideradas
- **Estimar o limiar do histórico** (melhor esforço de 20 min, FC média dos esforços): contradiz a decisão do Angelo.
- **Usar o primeiro limiar importado para as atividades anteriores:** descartado (decisão do Angelo, nunca limiar posterior).
- **`metrica_derivada` genérica:** descartada no item 5.
- **Carga por bloco da ADR 0008:** descartada no item 4.
- **hrTSS por tempo em zona (TrainingPeaks) ou por TRIMP de Banister:** mais fiel à fisiologia, exige zonas, FC de repouso e máxima por
  data; fica como `carga@2`, já que as tabelas de zona estarão no banco.
- **CTL/ATL gravados:** descartado no item 5.
- **Semear CTL/ATL com a carga crônica/aguda do Garmin:** escala diferente; contamina a conferência.
- **Natação com hrTSS:** a FC de limiar de corrida não vale na água.
- **Um limiar por esporte (corrida, ciclismo):** a Meta 6 grava só o que a fonte traz; se a #135 mostrar limiar por esporte,
  `limiar_atleta` ganha a coluna `esporte` (ainda dentro da Meta, antes da migração).

## Consequências
- **Cinco tabelas novas** (`limiar_atleta`, `zona_fc_atleta`, `recorde_pessoal`, `carga_garmin_dia`, `carga_atividade`), numa ou mais
  migrações a partir da `0008`, sem editar as anteriores. **Mudança no modelo de dados: precisa da aprovação do Theo** neste PR.
- Código novo (nas issues indicadas): `metricas/carga.py` (#138) e `metricas/serie_carga.py` (#139), puros; leitor e gravação de saúde
  (#136, #140, #174); `worker.calcular_carga` (#141); endpoint e campo na atividade (#142); conferência (#144).
- Quem não importou a exportação completa vê "sem carga" em tudo, com `sem_dados_saude`, e a tela precisa explicar como resolver
  (a tela fica fora desta ADR).
- Tudo o que o atleta importa de saúde fica no banco local; nenhum valor sai pela API, por log ou por git. Fixtures de teste e
  exemplos são sintéticos.
- A nota `docs/metricas/carga.md` (template de métrica) e o oráculo (#137) nascem junto da implementação; esta ADR é a fonte das
  constantes.

## A confirmar
**Achados da #135 (Duda), incorporados.** Os nomes concretos de arquivo e de campo ficam na nota
[[modulos/ingestao-garmin]] (PR #242), não nesta ADR. O que mudou aqui:
- **Limiar:** os registros trazem só o que mudou e vêm fora de ordem; o leitor ordena pela data do calendário (um **dia, sem fuso**) e
  guarda o último valor de **cada campo separadamente**. FC igual a 0 significa "sem limiar" (não vira linha). A velocidade vem numa
  escala própria da fonte e o leitor converte para m/s. Por isso `vigente_desde` do limiar é **data**, e a comparação é com a data
  local da atividade (itens 1 e 5).
- **Zonas de FC:** a exportação traz só o **retrato atual**, sem data e sem histórico. O histórico de zonas (método, FC máxima e de
  repouso, limite das zonas) só existe nos FIT, por sessão. Ver `zona_fc_atleta` no item 2.
- **Recordes:** o tipo vem como nome e a unidade do valor depende do tipo; id de atividade zero significa recorde sem atividade
  (`atividade_fonte_id` fica `NULL`).
- **Carga do Garmin:** o dia é a meia-noite UTC; pode haver vários itens por dia e vale o de maior carimbo de tempo; a razão pode faltar.
- Ainda em aberto: se há limiar **por esporte** ou um só (a nota da #135 diz o que a exportação traz).

**Pelo Theo (aprovadas em 07/11, ver "Data e quem decidiu"):**
- Aprovar as cinco tabelas e a escolha da tabela própria no lugar de `metrica_derivada` (item 5).
- Aprovar CTL/ATL/TSB **calculados na leitura**, com `serie_carga@1` na resposta (item 5).
- Zonas de FC (achado da #135): manter `zona_fc_atleta` com as origens `garmin_export` (retrato) e `garmin_fit` (histórico só dos FIT), só com o retrato, ou deixar fora da Meta 6 (a `carga` não usa).
- Aprovar `importar_garmin` chamar `importar_saude` e `calcular_carga` no fim, com erro virando aviso (item 3).
- Aprovar que `multiesporte_pai` e `troca` ficam **sem linha** e saem na contagem `ignoradas_multiesporte`, e não como "sem carga" (item 5).
- `worker.apagar_saude` (LGPD) como comando da #174.

**Decididas pelo Angelo (07/11, "sim" às sete propostas):**
- Esteira e ciclismo só por hrTSS (item 4).
- rTSS preferido ao hrTSS quando há os dois (item 4).
- Cobertura mínima de 95%, com volta sem dado contando 0 (item 4).
- "Aprendendo" = menos de 42 dias, e a série começa no primeiro dia com carga, sem semente (item 6).
- A série termina na última atividade importada, não em hoje (item 6).
- Natação sem carga na Meta 6, mesmo com FC (item 4).
- Conferência com o Garmin **só descritiva**, sem faixa de aprovação (item 8).

**Ainda em aberto (não bloqueia):**
- A descrição pública do modelo da carga aguda/crônica do Garmin (para a nota da conferência).
- Se `IF^2` é adequado para pace perto do limiar (a relação entre pace e custo energético não é linear).
- A forma do rTSS do TrainingPeaks aparece só em imagem na página oficial; o `IF^2` do rTSS segue da identidade do TSS, mas o texto não o afirma.
- O hrTSS é adaptação própria (item 4); a comparação com o do TrainingPeaks fica descartada.

## Fontes conferidas (07/11)
Conferido com busca e leitura de páginas em 07/11; o que não pôde ser aberto está dito.
- **TSS = (s x NP x IF) / (FTP x 3600) x 100** e IF = NP/FTP: confirmado em páginas secundárias que reproduzem a fórmula e em
  <https://trainingpeaks.com/blog/the-development-of-the-training-stress-score> (atribui TSS e IF a Coggan e Allen). **Não** abri o
  livro: edição e páginas de Coggan & Allen, *Training and Racing with a Power Meter* (VeloPress), não conferidas.
- **rTSS (TrainingPeaks):** <https://www.trainingpeaks.com/learn/articles/running-training-stress-score-rtss-explained/>. Confirmado: usa
  NGP contra o pace de limiar ("fastest pace sustainable for one hour") e a duração; IF = NGP / pace de limiar. A fórmula só aparece em
  imagem; a página não menciona Skiba nem GOVSS. **Correção:** a versão anterior da ADR citava Skiba como fonte do rTSS; passou a contexto.
- **Skiba 2006:** o título é *...: The Development of the GOVSS Algorithm* (não "Evolution", como estava). Confirmado por fontes
  secundárias (<https://topofusion.com/govss.php>): em GOVSS, 100 = o esforço de teste na velocidade de limiar. O artigo original não foi aberto.
- **hrTSS (TrainingPeaks):** <https://help.trainingpeaks.com/hc/en-us/articles/204071944>. Confirmado: é por **tempo em zonas de FC**
  (a partir da FC de limiar), com tabela, e menos preciso que o TSS por potência e o rTSS. **Correção:** a ADR dizia "a ideia do hrTSS do
  TrainingPeaks"; agora diz que o nosso é uma adaptação por razão ao quadrado (item 4).
- **Banister 1975:** não localizei o artigo de 1975 (*Aust J Sports Med*, v. 7, p. 57-61); uma lista de referências o dá como "Aust J Sci
  Med Sport, v. 7, p. 57", sem título. **Correção:** a base verificada é Calvert, T. W., Banister, E. W., Savage, M. V. & Bach, T. (1976),
  "A systems model of the effects of training on physical performance", *IEEE Transactions on Systems, Man, and Cybernetics*,
  SMC-6(2):94-102. A citação de 1975 fica como "citada por outras fontes, não verificada".
- **Banister 1991:** o livro é *Physiological Testing of the High-Performance Athlete* (2a ed., Human Kinetics, p. 403-425), e não
  "...of Elite Athletes", como estava. **Correção feita.** Não confirmei que o capítulo usa a sigla TRIMP.
- **CTL/ATL:** a forma `1 - exp(-1/tau)` está nas planilhas da lista do Golden Cheetah
  (<https://groups.google.com/g/golden-cheetah-users/c/h_KSL1oUmLI>, tau 7 e 42). Fontes de divulgação descrevem `1/tau`; qual das duas o
  TrainingPeaks usa por dentro **não ficou confirmado**. Mantida a forma exata (diferença no item 6).
- **TSB:** confirmado, TrainingPeaks e Golden Cheetah usam CTL e ATL do **dia anterior**. A ADR mantém o do mesmo dia (glossário) e agora diz a diferença no item 6.

## Adendo (07/11, #174)
Aprovado pelo Theo no PR #244. `recorde_pessoal.unidade` aceita `s`, `m`, `W`, `passos` **ou nulo** (tipo de recorde que o leitor não
reconhece), com `CHECK`; o item 2 dizia só `s` ou `m`. Implementado na migração 0009, com `carga_garmin_dia`. O comando
`worker.apagar_saude --atleta "<nome>"` apaga as quatro tabelas de saúde do atleta e imprime só contagens.

## Adendo (08/11, #255): `carga@2`, FC média da atividade
Decisão do Angelo (opção a). Há arquivos FIT cuja mensagem de volta não traz FC, embora a sessão e o resumo da atividade tragam a FC
média. Na `carga@1` (item 4) esses pedais ficavam `sem_fc`. **Regra nova, só no hrTSS:** se há voltas, **nenhuma** tem FC e a atividade
tem `fc_media` (e duração), a atividade entra como **volta única** (`duracao_s` e `fc_media` da atividade), com cobertura 100% e
`granularidade = 'atividade'` quando o hrTSS é o método vencedor. FC em **parte** das voltas segue a cobertura de 95%, sem mudança (a FC
da atividade não completa voltas que faltam). O rTSS não muda. Na corrida em que o rTSS vence, a `granularidade` continua `volta` (é a
do método vencedor) e o `carga_hrtss` gravado ao lado vem da atividade.
**Limitação:** a volta única ignora a variação de ritmo dentro da atividade e, por `IF^2` ser convexo, **subestima** a carga em relação ao
hrTSS por volta (precisão menor, como na atividade sem voltas). `VERSAO = "carga@2"`; `worker.calcular_carga` recalcula as linhas `@1`. A
`entrada` (hash) inclui a duração e a FC média da atividade **somente** quando esta regra a usa, para não recalcular à toa.

## Data e quem decidiu
2026-11-07. Proposta do Caio (ciência), com revisão da Duda (dados e ingestão) pedida no PR. **Modelo de dados aprovado pelo Theo em
07/11**: as cinco tabelas e a tabela própria no lugar de `metrica_derivada`; `zona_fc_atleta` com as duas origens (`garmin_export` e
`garmin_fit`); CTL/ATL/TSB na leitura com `serie_carga@1`; `importar_garmin` chamando `importar_saude` e `calcular_carga` no fim, com erro
virando aviso; `multiesporte_pai` e `troca` sem linha, em `ignoradas_multiesporte`; `worker.apagar_saude` na #174. Decisões de produto
do Angelo em 07/11 (seção "A confirmar"). Citações conferidas em 07/11 (seção "Fontes conferidas"). Issue #134.
