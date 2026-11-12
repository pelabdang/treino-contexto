---
tipo: modulo
status: em-uso
dono: duda
atualizado: 2026-11-12
links: [[decisoes/0010-carga-de-treino]], [[produto/meta-3-como-rodar]], [[modulos/worker]], [[modulos/banco]], [[decisoes/0006-upload-de-fit]], [[decisoes/0007-clima-da-atividade]], [[produto/roadmap]], [[diario/2026-11-03]], [[produto/meta-4-como-rodar]], [[decisoes/0008-deteccao-de-esforcos]], [[decisoes/0009-treino-de-transicao]], [[modulos/api]]
---
# Módulo: ingestão Garmin

## Para que serve
Ler a exportação "Exportar seus dados" do Garmin Connect e transformar em atividades e voltas, para a Meta 1
(tiros de 1 km). O formato abaixo foi conferido com uma exportação real na #19 (ver "Conferência com a exportação real").
Os testes usam fixtures sintéticas.

## Entradas e saídas
### Estrutura esperada da exportação (zip)
```
DI_CONNECT/
  DI-Connect-Fitness/
    <id>_0_summarizedActivities.json        resumo das atividades (sem voltas)
  DI-Connect-Uploaded-Files/
    UploadedFiles_0-_Part1.zip              zip interno com os .fit originais
      <id>_<activityId>.fit
```
Os nomes variam (o prefixo tem o identificador do usuário e pode haver `_Part2`, `_1_`...). A leitura deve
procurar por sufixo (`summarizedActivities.json`, `.fit`), nunca por nome exato.

### JSON `summarizedActivities.json`
Lista com um objeto `summarizedActivitiesExport`, que é a lista de atividades.

| Campo | Unidade | Uso |
|---|---|---|
| `activityId` | inteiro | `fonte_id` |
| `activityType` | texto (`running`, `track_running`, `treadmill_running`, `lap_swimming`...) | modalidade e `subtipo` |
| `sportType` | texto (`RUNNING`, `SWIMMING`...) | apoio à modalidade |
| `startTimeGmt` | **milissegundos** desde 1970, UTC | `inicio` |
| `startTimeLocal` | ms; hora de parede local contada como se fosse UTC (**opcional**; nas fixtures só A e B, em UTC-3) | `inicio_local` |
| `duration` | **milissegundos** | `duracao_s` |
| `distance` | **centímetros** | `distancia_m` |
| `avgHr` | bpm | `fc_media` |

O JSON **não traz as voltas**.

### FIT original
Mensagens usadas (formato binário da Garmin, lido com `fitdecode`, ver "Parser" abaixo):

| Mensagem | Campo | Unidade no arquivo | Observação |
|---|---|---|---|
| `lap` | `start_time` | data/hora | offset da volta = `start_time` - início da sessão |
| `lap` | `total_timer_time` | segundos (escala 1000 no arquivo) | tempo em movimento; é o que vale como duração |
| `lap` | `total_distance` | metros (escala 100 no arquivo) | |
| `lap` | `avg_heart_rate` | bpm | pode faltar |
| `lap` | `intensity` | enum: `active`, `rest`, `warmup`, `cooldown`, `recovery`, `interval`, `other` | pode faltar |
| `session` | `start_time`, `total_*`, `avg_heart_rate`, `sport`, `sub_sport` | idem | totais da atividade |
| `file_id` | `serial_number`, `time_created` | | base do id quando não há JSON |

Os leitores de FIT costumam devolver as unidades já convertidas (s e m). A conversão de unidades fica num
único lugar do código (`app/ingestao/garmin/unidades.py`) e tem teste.

### Fixtures sintéticas
`tests/fixtures/garmin/exportacao_minima.zip`, gerada por `tests/fixtures/garmin/gerar_fixtures.py`
(saída determinística; um teste falha se o zip versionado estiver desatualizado). Sem GPS, nome, e-mail ou id real.
A tabela com os valores de cada volta está no topo do script. Só as atividades A e B trazem `startTimeLocal` (UTC-3). Resumo:

| activityId | Atividade | Tem FIT | Voltas |
|---|---|---|---|
| 1000000001 | Intervalado 6 x 1 km, recuperação de 400 m (`running`) | sim | 13: aquecimento, 6 tiros, 5 recuperações, desaquecimento |
| 1000000002 | Intervalado 5 x 1 km, recuperação de 2 min parado (`track_running`) | sim (começa 2 s depois do JSON) | 11 |
| 1000000003 | Corrida leve de 8 km, auto-lap de 1 km (`running`) | sim | 8, todas `active` |
| 1000000004 | Natação 400 m (`lap_swimming`) | sim | 4 (ignorada na Meta 1) |
| 1000000005 | Intervalado em esteira 4 x 1 km (`treadmill_running`) | **não** | 0 |

Regerar: `uv run python tests/fixtures/garmin/gerar_fixtures.py`. A biblioteca `fit-tool` é só dependência de
desenvolvimento (escreve FIT nos testes).

## Parser (`services/api/app/ingestao/garmin/`)
O parser mora na API desde a #92 ([[decisoes/0006-upload-de-fit]]), para a API e o worker usarem sem ciclo de dependência; o código e o comportamento são os mesmos de quando ficava em `services/worker/worker/garmin/`. `fitdecode` é dependência do `treino-api`.
`ler_exportacao(caminho) -> list[AtividadeImportada]`, sem banco. Aceita o zip completo, a pasta descompactada,
um `summarizedActivities.json` solto ou um `.fit` solto. Zips aninhados (o `UploadedFiles_*.zip`) são abertos
em memória, até 3 níveis. Na pasta e no zip só entram `*summarizedActivities.json` e `*.fit`.

| Módulo | Papel |
|---|---|
| `modelos.py` | `AtividadeImportada` e `VoltaImportada` (dataclasses) |
| `leitor.py` | entrada (4 formatos), leitura do JSON e casamento JSON x FIT |
| `fit.py` | leitura de um FIT (`file_id`, `session`, `lap`) |
| `tipos.py` | tipo Garmin para `modalidade` (corrida/natacao/ciclismo/outra) e `subtipo` (esteira, pista, trilha, piscina, aguas_abertas, virtual, multiesporte_pai, troca) |
| `unidades.py` | ms para s, cm para m, epoch ms para datetime UTC |

### Regras
- **Casamento JSON x FIT:** pelo horário de início, tolerância de 60 s (vale o par mais próximo primeiro, cada FIT casa
  uma vez: a troca de um triatlo, que começa 60 s antes da parte seguinte, não leva o FIT dela). O `inicio` da atividade é o do JSON; `inicio_offset_s` das voltas é relativo ao início da sessão no FIT.
- **`fonte_id`:** `activityId` do JSON quando existe. FIT sem JSON usa `fit-<serial_number>-<time_created em epoch>`
  do `file_id`; sem esses campos, `fit-` + 16 primeiros caracteres do SHA-1 do arquivo. O id é estável entre
  leituras (a importação idempotente, #13, depende disso).
- **`inicio_local`:** mesmo instante de `inicio`, com o fuso do atleta (deslocamento = `startTimeLocal` - `startTimeGmt`, em minutos), então `.date()` dá a data local. `None` quando o JSON não traz o campo (FIT sem JSON, atividades C, D e E das fixtures) ou o deslocamento sai de UTC-12 a UTC+14. O parser não inventa fuso: o fallback `America/Sao_Paulo` fica na série ([[modulos/api]]).
- **Posição de início (Meta 4, #110, [[decisoes/0007-clima-da-atividade]]):** `AtividadeImportada.inicio_lat/inicio_lon`,
  em graus, **já arredondados a 2 casas (~1 km) dentro do leitor** (`garmin/posicao.py`): a coordenada exata nunca chega
  a objeto de importação, banco, log nem teste. Só a posição de **início**; `record`, fim e trajeto não são lidos.
  - *FIT:* `session.start_position_lat/long`; se faltar, os da **primeira** `lap`. O `fitdecode` devolve **semicírculos**
    (inteiro de 32 bits, `units = semicircles`), convertidos por `graus = semicírculos * 180 / 2^31`; o inválido
    `0x7FFFFFFF` (e `None`) vira sem posição.
  - *JSON:* `startLatitude` / `startLongitude` (conferidos com JSON sintético nos testes).
  - *Descarte (as duas ficam `None`):* fora da faixa (lat -90..90, lon -180..180), não numérico, só um dos dois, ou
    `(0, 0)` depois do arredondamento (ponto "sem GPS").
  - *JSON e FIT casados:* vale a posição do JSON; se o JSON não tiver, a do FIT.
  - *Indoor não guarda posição:* `subtipo` em `esteira`, `piscina` ou `virtual` sai com `None`, mesmo que o arquivo traga coordenada.
    O subtipo novo **`virtual`** vem de `virtual_ride` (JSON) e `sub_sport = virtual_activity` (FIT); antes, ciclismo virtual saía sem subtipo. Banco importado nessa época: `worker.reclassificar_subtipo` corrige o subtipo (e apaga a posição) sem reimportar ([[modulos/worker]], #183).
- **Dados da atividade:** com JSON, duração/distância/FC vêm do JSON; só FIT, vêm da `session` (ou da soma das voltas).
- **`arquivo_bruto`:** caminho lógico dentro da exportação, com `!/` para zips aninhados
  (ex.: `exportacao.zip!/DI_CONNECT/.../UploadedFiles_0-_Part1.zip!/x.fit`). Sem FIT, é o caminho do JSON.
- **`duracao_s` da volta** é `total_timer_time`; `intensidade` é o texto do enum FIT, `None` se ausente.
- **Falhas não derrubam a leitura:** FIT corrompido/truncado, JSON inválido, zip quebrado, FIT repetido e atividade
  sem FIT geram `logging.warning`; a atividade do JSON entra sem voltas. Item de JSON sem `activityId` ou
  `startTimeGmt` é ignorado com aviso. Caminho inexistente levanta `FileNotFoundError`.
- Um FIT corrompido não pode ser casado (não se sabe o horário), então a atividade do JSON fica sem voltas.

### Biblioteca de FIT: `fitdecode`
Escolhida por ser pura Python (sem compilar nada), leve, MIT, com leitura em fluxo e conversão de escala e de
enums para texto (`intensity="active"`) e de datas para `datetime`, que é o que o modelo precisa. O
`garmin-fit-sdk` oficial também serve, mas devolve enums e unidades de outro jeito e traz mais código para o pouco
que usamos. Se algum relógio real trouxer mensagens que o `fitdecode` não entenda, reavaliar (#19).
`fit-tool` segue só como dependência de desenvolvimento (gera FIT nas fixtures).

## Importação no banco (`app/ingestao/importacao.py`, CLI em `worker/importar_garmin.py`)
```
uv run python -m worker.importar_garmin <caminho> --atleta "<nome>" [--com-clima]
```
Sem rede por padrão; `--com-clima` busca o clima das atividades que mudaram ([[modulos/worker]]). Usa `DATABASE_URL` (Postgres do docker compose; rode `alembic upgrade head` antes). Imprime
`inseridas`, `atualizadas`, `ignoradas` e os avisos (inclui os do parser). Função: `importar(session, caminho, atleta_nome)`. Uma atividade que já veio por upload (regra dos 60 s, abaixo) é atualizada, não duplicada.

- **Atleta:** busca pelo nome; cria se não existir (sem assessoria).
- **Chave:** `(atleta_id, fonte, fonte_id)`. Reimportar não duplica atividades nem segmentos e não muda o `id`.
- **Atividade já gravada:** se os dados são iguais, é *ignorada* (segmentos e classificações da #14 ficam intactos;
  o `arquivo_bruto` não conta como diferença). Se algo mudou, é *atualizada* e, quando as voltas mudaram,
  os segmentos são substituídos. Leitura sem voltas (JSON sem FIT) nunca apaga voltas já gravadas; vira aviso.
- **Segmentos:** cada volta vira `segmento` com `tipo = "volta"`, `pace_s_km = duracao_s / distancia_m * 1000`
  (`NULL` se a distância é 0), `versao_deteccao` vazio até a classificação (abaixo).
- **`intensidade`:** minúsculas e sem espaços; valor fora da lista do `CHECK` ([[decisoes/0002-segmento-intensidade-e-versao]]) vira `other`, nunca erro;
  sem valor fica `NULL`.
- **`fuso_min`:** a importação grava em `atividade.fuso_min` o deslocamento do fuso em minutos
  (`inicio_local` - `inicio`, ex.: `-180`), conforme [[decisoes/0003-fuso-da-atividade]]. Sem horário local na fonte
  fica `NULL`, e uma reimportação sem esse horário **não apaga** um `fuso_min` já gravado. `fuso_min` conta na
  comparação "mudou": reimportar a exportação preenche as atividades gravadas antes da migração 0003.
- **`inicio_lat` / `inicio_lon`:** gravadas em `atividade` e comparadas como os demais campos: reimportar uma exportação
  antiga preenche a posição (atividade `atualizada` uma vez, depois `ignorada`), sem duplicar e sem mudar o `id`. Atividade
  indoor grava `NULL`. Fonte sem posição **não apaga** uma já gravada (como `fuso_min`); a exceção é a atividade que passa a
  ser indoor (subtipo novo), que perde a posição. Upload que casa com linha da exportação sem posição completa a posição.
  `importar` e `importar_fit` usam o mesmo `gravar_atividade`. A posição não sai pela API.
- **Classificação no fim:** depois de gravar, chama `classificar_atividades` ([[modulos/api]]): marca os segmentos
  das corridas como `tiro`/`recuperacao`/`volta`, grava `versao_deteccao` e sugere `tipo_treino = intervalado`
  (sem sobrescrever professor/TrainingPeaks/confirmado). É idempotente e refaz a classificação quando as voltas
  foram substituídas. A comparação "mudou" das voltas considera segmentos de todos os tipos.
- **Blocos e esforços (#166, #168):** a importação não chama `detectar_esforcos` direto: quem chama é o `classificar_atividades`
  acima ([[modulos/api]]), que roda a detecção primeiro e grava `bloco_atividade` ([[modulos/banco]]) antes de marcar os tiros.
  É o único ponto de detecção da importação (exportação e upload de FIT). Erro na detecção vira aviso no log e não derruba a
  importação; `worker.detectar_esforcos` refaz ([[modulos/worker]]).
- **Rótulo de transição no fim (#157):** por último chama `aplicar_sugestao` ([[modulos/api]]) para o **atleta inteiro** (não só
  para as atividades alteradas), porque uma atividade nova pode formar par com uma antiga; só roda se alguma atividade entrou ou
  mudou. Roda na importação, como a detecção de esforços, porque a regra é pura, sem rede e custa uma leitura leve das
  atividades do atleta; sem isso o rótulo ficaria desatualizado até alguém lembrar do comando. É idempotente, nunca toca
  correção do atleta e um erro vira aviso no log, sem derrubar a importação; `worker.sugerir_transicao` refaz ([[modulos/worker]]).
- Atividade sem duração (nem soma de voltas) é ignorada com aviso, porque `duracao_s` é obrigatório.
- Testes: `services/worker/tests/test_importar_garmin.py` (SQLite local; Postgres via `TEST_DATABASE_URL`).

### FIT avulsos do upload (Meta 3, #93)
O mesmo gerador escreve 11 `.fit` em `tests/fixtures/garmin/fit/` (abril/2025, sintéticos, sem GPS). Valores
esperados e contas à mão em `tests/test_fixtures_fit_upload.py`.

| Arquivo | O que representa | Esperado |
|---|---|---|
| `upload_intervalado_5x1km.fit` | 5 x 1 km, recuperação de 400 m | entra na série: pace 1230 / 5 = 246,0 s/km, FC 210282 / 1230 = 170,96 |
| `upload_rodagem_6km.fit` | 6 km em 6 voltas de 1 km | não é intervalado, fora da série |
| `upload_mesma_atividade_1000000001.fit` | a 1000000001 da exportação com início 30 s depois | casa pela regra dos 60 s |
| `empate_candidata_a.fit`, `empate_candidata_b.fit` | duas corridas a 40 s uma da outra (inserir direto no banco) | candidatas do empate |
| `empate_chegada_equidistante.fit` | 20 s de A e 20 s de B | empate: menor `id` |
| `empate_chegada_mais_perto_de_b.fit` | 30 s de A e 10 s de B | vale B |
| `upload_truncado.fit` | 60% dos bytes do intervalado | `ValueError` |
| `upload_nao_atividade.fit` | `file_id.type` = settings | `FitSemAtividade` |
| `upload_esteira_4x1km.fit` | 4 x 1 km em esteira | subtipo `esteira`, fora da série |
| `upload_natacao_400m.fit` | natação em piscina, 4 x 100 m | modalidade `natacao`, no banco e fora da série |

## Upload de FIT (Meta 3, #94)
Decisões em [[decisoes/0006-upload-de-fit]]. O atleta envia um `.fit` pelo endpoint `POST /atletas/{atleta_id}/atividades/fit` ([[modulos/api]], #95) ou pelo botão do app ([[modulos/mobile]], #96);
a função é `importar_fit(session, atleta_id, conteudo)` em `services/api/app/ingestao/importacao.py`, que devolve
`inserida`, `atualizada` ou `ignorada`, o `atividade_id` e os avisos. A gravação (exportação e upload) mora na API
(`app/ingestao/importacao.py`), e `worker/importar_garmin.py` é só a linha de comando.

- **Leitura:** `ler_atividade_fit(bytes, fonte)` (parser) junta `ler_fit` e `tipos.de_fit`. O upload usa `fonte = fit_upload` e
  `fonte_id` = o id derivado do FIT; não há horário local, então `fuso_min` fica `NULL` (fallback `America/Sao_Paulo`).
- **Identidade (`gravar_atividade`, usada também por `importar`):** primeiro a chave `(atleta_id, fonte, fonte_id)`;
  se não existe, a regra dos 60 s (mesmo atleta, mesma modalidade, início a até 60 s). Empate: início mais
  próximo, depois menor `id`, com aviso `candidatas 12, 15; usada a 12`. A exclusão
  "exportação não casa com exportação" vale **só quando os dois lados têm `activityId`** (outro `activityId` é outra
  atividade). FIT avulso importado pela exportação (`fonte_id` `fit-…`) não tem `activityId` e casa pela regra dos 60 s
  ([[decisoes/0006-upload-de-fit]], ajuste da #133).
  - *FIT avulso casa com linha com `activityId`:* age como o upload (a linha mantém `fonte_id` e campos do JSON; o FIT só
    completa voltas e posição e preenche `arquivo_bruto` se vazio). Importar JSON e depois FIT avulso, ou o inverso, dá
    uma linha só; a linha termina com o `activityId`.
  - *Limitação conhecida (#133):* dois FIT avulsos `fit-…` da mesma modalidade com início a até 60 s um do outro viram
    uma atividade só, porque nenhum dos dois tem `activityId` para separá-los. É raro (dois treinos reais não começam
    com menos de 1 minuto de diferença); se acontecer, só o JSON da exportação os distingue.
  - *Exportação casa com linha de upload:* a linha vira `garmin_export` com o `activityId`, e a chave de hoje volta a valer.
  - *Upload casa com linha da exportação:* a linha mantém `fonte`, `fonte_id` e os campos da exportação (início, duração,
    distância, FC, `fuso_min`); o upload só completa as voltas se a linha não tinha nenhuma, a posição de início se a linha não tinha (e não é indoor), e troca o `arquivo_bruto`.
  - *Upload casa com linha de upload:* atualiza como a importação de hoje (campos e voltas).
- **Guarda (`app/ingestao/fit_guardado.py`):** `FIT_DIR` (padrão `dados-upload/fit/`, relativo à raiz do repositório,
  na lista de ignorados do controle de versão) / `<atleta_id>/<sha256>.fit`; `arquivo_bruto` leva o caminho relativo. Gravação em
  temporário com renomeação (permissão só do usuário); o nome enviado pelo cliente nunca é usado. Reenvio do mesmo conteúdo é
  `ignorada` e não regrava; se o arquivo sumiu, regrava e conta `atualizada`. FIT diferente que casa troca o `arquivo_bruto` e
  **apaga o antigo** se nenhuma outra atividade o referencia (falha ao apagar vira aviso). A exportação não troca um
  `arquivo_bruto` que já aponta para `FIT_DIR`. O FIT guardado é **dado pessoal de saúde** (FC, horários e voltas do
  atleta): fica fora do git (`dados-upload/` ignorado, com teste) e nunca vai para issue, PR, teste ou nota. Para
  apagar: `uv run python -m worker.apagar_fit --atleta-id <id>`.
- **Ordem:** valida e lê o FIT, grava a atividade na sessão, grava o arquivo, `commit`, apaga o antigo órfão, classifica as corridas
  do atleta. Se o `commit` falha, o arquivo criado é removido. Violação da chave única (envios simultâneos): lê de novo uma vez.
- **Erros (exceções):** `AtletaInexistente`, `FitGrande` (mais de 10 MB), `FitNaoEAtividade` (FIT que não é atividade) e
  `FitInvalido` (corrompido, truncado, sem início ou sem duração). Hierarquia: `FitInvalido` e `FitGrande` herdam de `ValueError`, `FitNaoEAtividade` herda de `FitInvalido` e `AtletaInexistente` de `LookupError`. No endpoint: `FitInvalido` e `FitNaoEAtividade` viram `400`, `FitGrande` `413` e `AtletaInexistente` `404`. Inválido nunca chega ao banco nem ao disco.
- **Só corrida entra na série:** natação, ciclismo e esteira ficam gravados e fora do gráfico ([[decisoes/0005-serie-de-tiros-o-que-entra]]).
- **Apagar:** `uv run python -m worker.apagar_fit --atleta-id <id>` apaga os arquivos do atleta e limpa `arquivo_bruto`
  das atividades que apontavam para eles; as atividades e a série ficam. Idempotente. Atleta inexistente: stderr e saída 1.
- Testes: `services/api/tests/ingestao/test_importar_fit.py` (FIT sintéticos da #93, `FIT_DIR` em diretório temporário).

## Buscar no Garmin Connect (piloto local, #335)
Paralela da Meta 9: o atleta não sobe FIT à mão; o worker busca a atividade do dia na conta dele. Só local, só na conta do próprio atleta.

> **Limitação:** usa a biblioteca **não oficial** `garminconnect` (0.3.20, fixada). Ela imita o login do app e **pode quebrar quando o Garmin mudar o login** (ou bloquear o cliente). A API oficial da Garmin segue sendo o caminho de produção e depende do CNPJ.

- **Comando:** `uv run python -m worker.buscar_garmin --atleta "<nome>" [--desde AAAA-MM-DD] [--ate AAAA-MM-DD] [--sem-clima]`. Padrão: hoje. O atleta precisa existir (importe a exportação antes).
- **Fluxo (`worker/buscar_garmin.py`):** lista as atividades do intervalo, **pula** as que já estão no banco (início a até 60 s de uma atividade do atleta, a regra da ADR 0006, sem baixar), baixa o FIT original (zip com um `.fit`, até 10 MB) e chama `importar_fit`, **o mesmo caminho do upload de FIT**: identidade, guarda em `FIT_DIR`, esforços e tipo (via `classificar_atividades`), transição. Depois roda a carga do atleta e, sem `--sem-clima`, o clima das atividades que entraram ou mudaram (os mesmos auxiliares do `importar_garmin`). A linha entra com `fonte = fit_upload`; **não há mudança no modelo de dados** e o id do Garmin não é guardado no banco (só no arquivo local de ids, abaixo).
- **Já no banco, em duas regras (#342):** (1) o **id do Garmin** já foi processado e a atividade correspondente ainda existe no banco (arquivo local de ids, abaixo); (2) o início da lista a até 60 s do início de uma atividade do atleta (ADR 0006). O caso que levou ao arquivo: o início da lista do Garmin pode estar distante do início do FIT além do que a sobreposição de intervalos cobre; a atividade era então baixada a cada rodada (e saía `ignorada`, sem duplicar). Uma regra por sobreposição de intervalos foi testada e **saiu**: não cobre inícios distantes e arriscaria falso positivo.
- **Arquivo de ids (`worker/garmin_vistos.py`):** `dados-garmin/ids-atleta-<id>.json`, ao lado do token (mesma pasta ignorada pelo controle de versão), por atleta, com o par `id do Garmin -> id interno da atividade` (`{"versao": 1, "ids": {...}}`). Antes de baixar, se o id da lista está no arquivo e a atividade existe no banco (e é do atleta), pula como `ja_no_banco`. Depois de cada importação (inserida, atualizada ou ignorada por já existir) o par é registrado. Escrita atômica (temporário + renomeação), arquivo 0600 em pasta 0700. **Sem mudança no modelo de dados.** É só um atalho: a verdade continua no banco e o `importar_fit` continua sem duplicar.
  - Arquivo ausente é o caso normal (baixa e reconstrói, sem aviso); corrompido ou ilegível vira um aviso fixo e o comportamento de antes (baixa, não duplica), nunca erro; atividade apagada do banco é baixada de novo. O conteúdo do arquivo nunca vai para log nem para a saída.
  - **A pasta `dados-garmin/` guarda o token e os ids. Apagar a pasta é seguro:** o próximo login usa as credenciais do `.env` (com código MFA, se pedido) e a primeira rodada baixa de novo o que já está no banco, sem duplicar.
  - Atenção em worktree: `dados-garmin/`, `dados-upload/` e o `.env` são relativos à raiz do repositório **em que o comando roda**. Rodar de um worktree usa a pasta dele (sem o token nem os FIT do repositório principal); o `importar_fit` regrava o FIT que não acha (conta como `atualizadas`, sem mudar o banco). Rode do repositório principal ou aponte `GARMINTOKENS` e `FIT_DIR` para caminhos absolutos.
- **Idempotente:** a segunda rodada não baixa nada do que já entrou e não duplica. Se o Garmin não mandar o horário, o FIT é baixado e o `importar_fit` reconhece a atividade (`ignorada`). Um FIT que não é atividade ou é inválido conta em `falhas`, não derruba a rodada e dá saída 6.
- **Cliente atrás de uma interface (`worker/garmin_cliente.py`):** `ClienteGarmin` tem `listar(desde, ate)` e `baixar_fit(id)`. `ClienteGarminConnect` é a implementação real; os testes usam um cliente falso e nenhum teste entra em conta ou abre rede.
- **Credenciais e token:** só `GARMIN_EMAIL` e `GARMIN_PASSWORD` do `.env` local (ou do ambiente) e `GARMINTOKENS` (pasta do token, padrão `dados-garmin/token` na raiz, no `.gitignore`); o `.env.example` traz só os nomes, vazios. Com token salvo o login não usa a senha. O token é gravado em `garmin_tokens.json` (permissão 0600, pasta 0700) **por nós**, depois do login: com `return_on_mfa=True` a biblioteca não o grava sozinha. Sem token e sem credenciais é erro de configuração (saída 1), não exceção. Nada disso vai para log, saída ou mensagem de erro: as mensagens são fixas e não repetem o texto da biblioteca (teste confere).
- **Uma tentativa de login por execução** (`retry_attempts=1`, sem nova tentativa). Token recusado: a mensagem manda apagar a pasta do token e rodar de novo.
- **Erros e códigos de saída:** 1 configuração, argumento ou atleta inexistente; 2 login ou sessão recusados; 3 MFA pedido e sem terminal, ou código recusado; 4 limite de requisições (429); 5 rede ou serviço fora do ar; 6 outro erro do Garmin ou atividades com falha. Tudo em `erro: <mensagem>` no stderr, sem traceback. O que já foi importado antes do erro fica; a próxima rodada completa.
- **MFA:** se o login pedir o código de verificação e a entrada for um terminal, o comando pergunta **uma vez** (`Codigo de verificacao do Garmin: `, sem eco), conclui com `resume_login` da biblioteca e grava o token como no login normal; as próximas rodadas usam o token. Sem terminal, código vazio ou código recusado: saída 3 com mensagem fixa, nada gravado. Não há opção de linha de comando para o código (ficaria no histórico do shell), e o código nunca vai para log, saída ou mensagem de erro (teste confere).
- **Fora (na Meta 9):** sono, VFC, estado de treino, prontidão e treinos planejados do Garmin Connect. Sono, VFC e FC de repouso entram na Meta 10: formato em "Sono, VFC e FC de repouso: formato das respostas", abaixo.
- Testes: `services/worker/tests/test_buscar_garmin.py` (FIT sintéticos de `tests/fixtures/garmin/fit/`, biblioteca e cliente falsos, guarda de rede, teste do log).
- O passo a passo de uso fica no guia de como rodar da Meta 9 ([[produto/roadmap]]).

## Sono, VFC e FC de repouso: formato das respostas (Meta 10, #371)
Formato do que a biblioteca do `worker.buscar_garmin` devolve para a recuperação. Esta seção descreve **só a estrutura** (chamada, caminho do campo, tipo, unidade, dia sem dado),
conferida em 12/11 com **uma** consulta local à conta do próprio atleta (3 noites recentes e uma faixa curta de VFC e de FC de repouso, token já salvo, nada gravado no banco nem
no repositório) e com o código da versão fixada, **`garminconnect==0.3.20`**. Nenhum valor, data, horário ou padrão real está aqui; as fixtures são escritas à mão (`tests/fixtures/meta10/`).
O leitor e o banco vieram na #372 (seção "Leitor e busca (#372)", abaixo). Sono, VFC e FC de repouso são dado de saúde: só no banco local, nunca em log, exceção, captura ou fixture gravada.

**Legenda:** *observado* = visto na resposta real; *código* = lido no código da biblioteca; *hipótese* = não visto, o leitor deve tolerar.

### Chamadas
| Medida | Chamada (`Garmin`) | Pedido | Resposta |
|---|---|---|---|
| Sono + VFC da noite + FC de repouso | `get_sleep_data(cdate)` | um dia `AAAA-MM-DD` | `dict` grande (séries de centenas de itens); o leitor usa só 4 campos |
| Sono (resumo) | `get_sleep_daily(start, end)` | faixa; a biblioteca parte em blocos de 28 dias e junta | lista de resumos por `calendarDate`. **Não usada** (formato dos itens não conferido); por isso o sono é uma chamada de `get_sleep_data` por noite |
| VFC noturna em faixa | `get_hrv_data_range(start, end)` | faixa | `dict` com `hrvSummaries` (abaixo) |
| VFC de um dia | `get_hrv_data(cdate)` | um dia | `None` possível (docstring de `typed.py`); formato não conferido |
| FC de repouso em faixa | `get_rhr_daily(start, end)` | faixa ("até ~1 ano", docstring) | lista de `{calendarDate, value}` |
| FC de repouso de um dia | `get_rhr_day(cdate)` | um dia | `dict` bruto da rota de bem-estar, não conferido |

As chamadas `get_sleep_data`, `get_rhr_day` e `get_rhr_daily` usam o nome de exibição da conta que a biblioteca obtém no login; as de VFC não.

### Sono: `get_sleep_data` (observado)
| Caminho | Tipo e unidade | Uso |
|---|---|---|
| `dailySleepDTO.calendarDate` | texto `AAAA-MM-DD` | **a data da noite = a data local de acordar** (ver abaixo) |
| `dailySleepDTO.sleepTimeSeconds` | inteiro, **segundos** | **tempo dormindo**: é `deepSleepSeconds + lightSleepSeconds + remSleepSeconds`, **sem** os despertares |
| `dailySleepDTO.awakeSleepSeconds` | inteiro, segundos | tempo acordado dentro da janela. `sleepTimeSeconds + awakeSleepSeconds + unmeasurableSleepSeconds` = janela (fim - início) |
| `dailySleepDTO.napTimeSeconds` | inteiro, segundos | sesta; `0` nas noites conferidas (ver "Sesta") |
| `dailySleepDTO.sleepStartTimestampGMT`, `sleepEndTimestampGMT` | inteiro, **milissegundos desde 1970** (instante real) | início e fim da janela |
| `dailySleepDTO.sleepStartTimestampLocal`, `sleepEndTimestampLocal` | inteiro, milissegundos | **hora de parede local lida como se fosse UTC** (`Local - GMT` = deslocamento do fuso, em horas inteiras). Não converter de novo |
| `avgOvernightHrv` (**no topo**, não no `dailySleepDTO`) | decimal, **ms** | **VFC noturna média** da noite; igual ao `lastNightAvg` da rota de faixa no mesmo dia |
| `restingHeartRate` (**no topo**) | inteiro, bpm | **FC de repouso** |
| `hrvStatus` (topo) | texto (enum) | status do Garmin; **não usar** (métrica proprietária) |

O resto da resposta (estágios, séries de FC, estresse, Body Battery, SpO2, respiração, notas, pontuações, necessidade de sono) **não é lido nem guardado** (decisão do Angelo). `dailySleepDTO.avgSleepHRV`,
que o tipo da biblioteca declara, **não existe** na resposta real: a VFC está em `avgOvernightHrv`. `userProfilePK` e `id` são identificadores: **ignorar**.

**Data da noite (observado):** nas três noites, `calendarDate` = data pedida (`cdate`) = data local do **fim** do sono (`sleepEndTimestampLocal`); o início cai na véspera. O Garmin atribui a noite
ao dia em que o atleta **acordou**, a regra da ADR 0014: pedir `cdate = D` devolve a noite que termina em `D`. Não foi testada noite com viagem entre fusos.

**Sono total x acordado (observado):** o campo a guardar é `sleepTimeSeconds` (sem os despertares). O tempo na cama é a janela (`sleepEnd - sleepStart`), ou a soma com `awakeSleepSeconds`.

**Sesta:** só se viu `napTimeSeconds` (inteiro, segundos) no mesmo `dailySleepDTO`, igual a `0` nas três noites; **a estrutura das sestas (lista com início e fim) não foi observada**. Como `sleepTimeSeconds` é a soma
dos três estágios da janela da noite, o leitor usa `sleepTimeSeconds` e **ignora** `napTimeSeconds`. Se a sesta soma ou não em `sleepTimeSeconds` quando `napTimeSeconds > 0`: **não conferido** (hipótese: não soma).

**FC de repouso (observado):** a resposta do sono **traz** `restingHeartRate` (no topo), e o valor é **igual** ao de `get_rhr_daily` para o mesmo `calendarDate`, inclusive na noite que terminou naquela manhã. **Não existe uma FC de
repouso "da noite" separada**: é a FC de repouso **do dia** `calendarDate`. Não foi conferido se o valor muda ao longo do dia (exigiria nova consulta horas depois), então a regra da ADR 0014
(preencher só quando a data já passou) continua necessária enquanto isso não for medido.

### VFC em faixa: `get_hrv_data_range` (observado)
`{"hrvSummaries": [...], "userProfilePk": inteiro}`. Cada item, **um por dia com leitura**, em ordem crescente de `calendarDate`:

| Campo | Tipo e unidade | Observação |
|---|---|---|
| `calendarDate` | texto `AAAA-MM-DD` | a mesma data da noite no `get_sleep_data` (data de acordar) |
| `lastNightAvg` | inteiro, **ms** | VFC noturna média (inteiro aqui; no sono, decimal) |
| `lastNight5MinHigh` | inteiro, ms | maior janela de 5 min; **não usar** |
| `weeklyAvg` | inteiro ou `None` | `None` nas noites conferidas; não usar |
| `baseline.lowUpper`, `balancedLow`, `balancedUpper` | inteiro, ms | faixa de base do Garmin; **não usar** (métrica proprietária); `markerValue` era `None` |
| `status`, `feedbackPhrase` | texto (enum e chave) | **não usar**. Uma noite tinha `status = "NONE"` e mesmo assim `lastNightAvg` inteiro |
| `createTimeStamp` | texto de data e hora | quando o Garmin criou o resumo |

**Limite de faixa:** a biblioteca não impõe limite ao `get_hrv_data_range` (só valida `start <= end`) e o limite do servidor **não foi medido** (a consulta usou 3 dias). O `get_sleep_daily` tem 28 dias por pedido
(a biblioteca parte em blocos) e o `get_rhr_daily` documenta "até ~1 ano". Recomendação para o leitor: pedir **blocos de no máximo 28 dias** nas três rotas e parar no primeiro erro.

### FC de repouso em faixa: `get_rhr_daily` (observado)
Lista de `{"calendarDate": "AAAA-MM-DD", "value": decimal}` (a faixa devolve decimal; o `restingHeartRate` do sono, inteiro; mesmo número). **A biblioteca descarta as linhas com `value = None`** (código):
dia sem FC de repouso = a linha não existe.

### Como vem "dia sem dado"
| Caso | O que chega | Origem |
|---|---|---|
| Sono de um dia sem registro (HTTP 204) | `{}` (dicionário vazio) | código (`_EmptyJSONResp`); **não observado** (as três noites tinham dado) |
| `dailySleepDTO` presente sem duração | `sleepTimeSeconds` = `None` ou `0` | hipótese; o leitor trata `None`, `0` e fora de `1..86400` como sem sono |
| VFC ausente numa noite com sono | `avgOvernightHrv`, `hrvData`, `hrvStatus` ausentes **ou** `None` | hipótese (as três noites tinham VFC); ausente e `None` valem o mesmo |
| VFC em faixa, dia sem leitura | o dia **não aparece** em `hrvSummaries`; faixa toda sem dado: lista vazia ou `{}` (204) | código + hipótese |
| FC de repouso em faixa, dia sem valor | a linha não existe; faixa toda sem dado: `[]` | código |
| Dia com 404 | `GarminConnectNotFoundError` (subclasse de `GarminConnectConnectionError`) | código |

Não se viu `0` como sentinela, mas o leitor trata `0` ou fora da faixa dos `CHECK` como sem dado (ADR 0014). Relógio que não sincronizou não se distingue de "sem dado": a resposta é a mesma.

### Erros e limite (429)
- Rotas de dados: a biblioteca (`client/transport.py`) levanta **`GarminConnectConnectionError("API Error 429 ...")`**, com a resposta HTTP em `.response` (`.response.status_code == 429`). **Não** levanta
  `GarminConnectTooManyRequestsError`: essa classe só sai do **login** (SSO e troca do token), e **não** é subclasse de `GarminConnectConnectionError`. Lido no código; o 429 não foi provocado.
- Consequência para `worker.garmin_cliente._traduzir`: hoje todo `GarminConnectConnectionError` vira `ErroRede` (saída 5). Para a recuperação, o 429 das rotas de dados tem de virar `ErroLimite` (saída 4), olhando
  `getattr(getattr(e, "response", None), "status_code", None) == 429` **antes** do caso de rede e sem repetir o texto do erro. Fica para a #372. Vale também para as rotas de atividade da Meta 9.
- 401: a biblioteca renova a sessão uma vez; recusa persistente vira `GarminConnectAuthenticationError`.
- A biblioteca escreve `logger.debug("Requesting ...")` por chamada, sem o conteúdo; ainda assim o logger `garminconnect` fica acima de DEBUG por código.

### Fixtures sintéticas (`tests/fixtures/meta10/`)
Escritas à mão, com valores e datas inventados (março de 2026); cada dicionário traz `_sintetico`. Teste: `tests/test_fixtures_meta10.py`.

| Arquivo | Caso |
|---|---|
| `sono_noite_completa.json` | noite completa: sono, VFC no topo, FC de repouso |
| `sono_noite_sem_vfc.json`, `sono_noite_sem_vfc_none.json` | sem VFC (chaves ausentes; chaves `None`), hipótese |
| `sono_dia_sem_dado.json`, `sono_dto_sem_duracao.json` | `{}` (204); duração `None` |
| `sono_noite_com_sesta.json` | `napTimeSeconds > 0` |
| `sono_noite_com_marcador.json` | texto `MARCADOR-SINTETICO-META10-NAO-LOGAR` em campos de texto e em campo desconhecido, para o teste de log da #372 |
| `vfc_faixa.json`, `vfc_faixa_com_buraco.json`, `vfc_faixa_sem_dado.json` | faixa de VFC; faixa com dia faltando; `{}` |
| `rhr_faixa.json`, `rhr_faixa_sem_dado.json` | faixa de FC de repouso (com dia faltando); `[]` |

### Leitor e busca (#372)
O **leitor** fica dentro do cliente real (`worker/garmin_cliente.py`: `ler_sono`, `ler_vfc`, `ler_fc_repouso`, `VERSAO_LEITURA = "recuperacao_leitura@1"`); o nome de campo do Garmin **não sai dele**. `ClienteGarmin.recuperacao(desde, ate, medidas)` devolve `NoiteRecuperacao(noite, sono_s, vfc_ms, fc_repouso_bpm)` (`None` para o que faltou); cada chamada é **uma requisição** (`"vfc"` e `"fc"` aceitam até 28 dias, `"sono"` um dia). Regras: sono = `dailySleepDTO.sleepTimeSeconds` só se `calendarDate` for a data pedida; VFC = `hrvSummaries[].lastNightAvg`; FC de repouso = `get_rhr_daily` arredondada; ausente, `None`, `0`, não numérico e fora da faixa dos `CHECK` viram `None`; formato inesperado nunca levanta. O comando é `worker.buscar_recuperacao` ([[modulos/worker]]). **O 429 das rotas de dados** (#386): `_traduzir` agora trata como `ErroLimite` (saída 4) todo `GarminConnectConnectionError` cuja `.response.status_code` é 429, também em `listar` e `baixar_fit` do `buscar_garmin`.

O oráculo de `recuperacao@1` (comparação com o normal) é do Caio e fica em `docs/metricas/`; usa estas fixtures como formato, não como valores.

## Arquivos principais
- `services/api/app/ingestao/garmin/` e `services/api/tests/ingestao/test_garmin_parser.py`
- `services/api/app/ingestao/importacao.py` (gravação: `importar`, `importar_fit`, `gravar_atividade`) e `fit_guardado.py` (guarda em `FIT_DIR`)
- `services/worker/worker/importar_garmin.py` e `apagar_fit.py` (linhas de comando) e `services/worker/tests/test_importar_garmin.py`
- `services/api/tests/ingestao/test_importar_fit.py`
- `tests/fixtures/garmin/gerar_fixtures.py` e `tests/fixtures/garmin/exportacao_minima.zip`
- `tests/test_fixtures_garmin.py`
- `tests/fixtures/garmin/fit/` e `tests/test_fixtures_fit_upload.py` (FIT do upload)
- `tests/fixtures/garmin/gerar_fixtures_saude.py`, `tests/fixtures/garmin/saude/` e `tests/test_fixtures_saude.py` (saúde e métricas, #135)

## Depende de
- [[modulos/api]] (onde fica o parser, `app/ingestao/`), [[modulos/worker]] (importação no banco e CLI) e [[modulos/banco]] (destino).

## Como testar
`uv run pytest -q` na raiz.

## Conferência com a exportação real (#19)
Feita em 2026-11-01 com uma exportação real (fica em `dados-teste/`, fora do git). Aqui só o **formato**:
nenhum valor, contagem, data ou nome de atividade vem do dado pessoal.

Confirmado, igual ao esperado:
- `startTimeGmt`, `duration` (ms) e `distance` (cm): duração, distância e pace das corridas saem plausíveis, e
  `startTimeGmt` bate com o início do FIT, então o casamento por horário funciona.
- `startTimeLocal` existe em todas as atividades, com a semântica descrita acima. Há também `timeZoneId` (não usado).
- `activityType`: os valores de corrida, ciclismo e natação (`running`, `treadmill_running`, `trail_running`,
  `cycling`, `indoor_cycling`, `virtual_ride`, `lap_swimming`, `open_water_swimming`) mapeiam como esperado, e
  qualquer outro tipo vira `outra`. `track_running` (pista) não apareceu nesses dados.
- As voltas vêm dos `lap` do FIT. `intensity` aparece nos relógios usados, mas não em todas as atividades
  (ciclismo e natação costumam vir sem).

Divergências em relação às fixtures:
- **Resumo paginado:** vários `<usuario>_<n>_summarizedActivities.json` (com um número de página no nome), cada um com
  uma página da lista. O parser lê todos; um teste cobre.
- **A árvore tem cópias:** a pasta descompactada, `DI_CONNECT/` e `Arquivo.zip` repetem os mesmos `.fit`. O parser
  lê cada arquivo uma vez (hash do conteúdo).
- **Nem todo `.fit` é atividade:** a maioria dos arquivos (monitoramento diário e outros) tem `file_id.type` diferente
  de `activity`. O parser descarta esses sem decodificar o resto e sem aviso. Isso, mais o hash e não abrir arquivos
  irrelevantes, reduziu a leitura de vários minutos para poucos.
- **O número no nome do `.fit` não é o `activityId`** (nome `<usuario>_<número>.fit`), então o casamento é só por
  horário (já era a regra). Há nomes de outros apps e um `.gpx` no zip interno, ignorado.
- **Lixo do macOS:** `__MACOSX/` e `._*` aparecem nos zips; são ignorados.
- **Arquivos sem relação** com treino estão na raiz; só `*summarizedActivities.json`, `.fit` e `.zip`
  são lidos, e os outros nem são abertos.
- **Atividades sem FIT:** parte das atividades do resumo não tem `.fit`; entram sem voltas, com aviso.
  Conferido com o dono em 03/11: não faltam arquivos.
- **Regra dos tiros em dado real:** a intensidade de uma rodagem leve real não vem toda igual (a última volta,
  parcial, vem `rest`/`recovery`/`cooldown`), então a regra "intensidade informativa" de [[metricas/tiros-1km]]
  marca falsos intervalados. Registrado em issue própria (regra do Caio).

## Como importar a exportação real
Aponte para a pasta descompactada (ou o zip):
```
docker compose -f infra/docker-compose.yml up -d
cd services/api && uv run alembic upgrade head && cd ../..
uv run python -m worker.importar_garmin dados-teste/garmin --atleta "<nome>"
uv run python -m worker.grafico_tiros_1km --atleta-id <id>
```
Se a porta 5432 já estiver ocupada por um Postgres nativo, o container não é alcançado (erro de papel `treino`
inexistente): confira com `lsof -iTCP:5432 -sTCP:LISTEN` e use a porta padrão do container (5433) em `DATABASE_URL`; detalhes em [[modulos/infra]]. A importação completa leva alguns minutos.

## Treino multiesporte: atividade-pai e atividade de troca (#230, ADR 0009)
Um relógio pode gravar um treino multiesporte como uma atividade **pai**, que agrupa as partes, mais uma atividade por parte e, às
vezes, atividades próprias para a **troca** entre elas. O pai repete a distância e o tempo das partes; por isso a carga da Meta 6 não
pode somar tudo (contaria o treino duas vezes).

**Como ficou (direção aprovada pelo Theo em 06/11):**
1. **Importa como antes, sem descartar nada**: `modalidade = outra`; identidade e reimportação não mudam. Sem migração.
2. **`subtipo`** (texto livre) recebe `multiesporte_pai` (agrupador) ou `troca` (transição entre as partes). Constantes e mapeamento em
   `tipos.py` (`SUBTIPO_PAI`, `SUBTIPO_TROCA`, `SUBTIPOS_MULTIESPORTE`), para JSON e FIT.
3. **A carga (Meta 6) ignora os dois subtipos**: cada parte conta uma vez, como diz a ADR 0009 (item 6). O tempo da troca não é treino.
   Aviso para a [[decisoes/0010-carga-de-treino]] (carga, #134): a ADR registra que a carga exclui
   `subtipo in (multiesporte_pai, troca)`.
4. A regra `transicao@1` não muda: continua só com corrida, natação e ciclismo; pai e troca (`outra`) não entram nem atrapalham a
   vizinhança (teste em `services/api/tests/ingestao/test_multiesporte.py`).
5. **Banco já importado:** `uv run python -m worker.reclassificar_multiesporte --exportacao CAMINHO [--atleta-id N] [--dry-run]`
   (ver [[modulos/worker]]).

**Valores reconhecidos (igualdade exata, sem diferenciar maiúsculas) e fonte pública:**

| Formato | Campo | `multiesporte_pai` | `troca` |
|---|---|---|---|
| FIT | `sport` (enum `sport` do Profile do FIT SDK, <https://developer.garmin.com/fit/>) | `multisport` (valor 18) | `transition` (valor 3) |
| Exportação Garmin (JSON) | `activityType` ou `sportType` | `multi_sport`, `multisport`, `triathlon`, `duathlon` | `transition` |

Os valores de FIT vêm do Profile publicado pela Garmin. Os do JSON seguem as chaves de tipo de atividade do Garmin Connect, que
repetem esses nomes (documentação pública do FIT SDK e bibliotecas abertas); a lista é conservadora e pode crescer. **Esta nota não
afirma o que uma exportação específica contém**: depois de rodar o passo com `--dry-run`, o relatório mostra quantas linhas casaram, e
quem tem o dado confere localmente que os valores batem. Fixtures sintéticas: `tests/fixtures/multiesporte/`
(`exportacao_multiesporte.json`, `fit/multiesporte_pai.fit`, `fit/troca.fit`; gerador `gerar_fixtures_multiesporte.py`).

**Limitações:** o passo de banco cobre as linhas `garmin_export` (casa por `fonte_id`); atividades vindas de upload de FIT já importadas
antes do #230 só mudam se o arquivo for reenviado. O `worker.reclassificar_subtipo` (#183), por usar o mesmo `tipos.py`, também grava
esses subtipos; o novo comando é o caminho estreito (só `outra` sem subtipo, nunca sobrescreve outro subtipo).

Alternativas descartadas: **não importar** pai e troca (perde dado e muda a contagem de atividades) e **nova coluna ou modalidade**
(migração e mudança de `CHECK` para algo que o subtipo resolve).

## Dados de saúde e métricas da exportação (Meta 6, #135)
A carga de treino da Meta 6 usa o que o Garmin já calculou: limiar de lactato (FC e velocidade) com histórico de alterações, zonas de
FC, recordes pessoais e carga aguda/crônica diária. Esta seção descreve **só o formato** (pastas, nomes de campo, unidades, datas),
conferido com uma exportação real em 2026-11-07 (fica em `dados-teste/`, fora do git); nenhum valor, data ou identificador real está
aqui. O leitor (#136) está descrito em "Leitor de saúde (#136)", abaixo; o parser de atividades (`ler_exportacao`) continua ignorando esses arquivos (teste em `tests/test_fixtures_saude.py`). Decisão de produto
(04/11): tudo pode ser guardado no banco local; atleta sem esses dados fica "sem carga", com o motivo, e o limiar nunca é estimado.

### Como achar os arquivos (sem identificador do usuário)
Procure por **nome da pasta + padrão do nome do arquivo**, em qualquer profundidade do caminho (a raiz varia: `DI_CONNECT/` na pasta
descompactada, nenhuma no `Arquivo.zip`; a mesma árvore pode aparecer duas vezes, ver "A árvore tem cópias": leia cada conteúdo uma
vez). O identificador do usuário (número no meio ou e-mail no começo do nome) **nunca** entra na busca.

| Dado | Pasta | Padrão do nome (`*` = identificador do usuário) | Quantos |
|---|---|---|---|
| Limiar de lactato, com histórico | `DI-Connect-Wellness/` | `*_userBioMetrics.json` | 1 |
| Zonas de FC, método, FC máxima e de repouso | `DI-Connect-Wellness/` | `*_heartRateZones.json` | 1 |
| Limiar mais recente (retrato) | `DI-Connect-Wellness/` | `*_bioMetrics_latest.json` | 1 |
| Recordes pessoais | `DI-Connect-Fitness/` | `*_personalRecord.json` | 1 |
| Carga aguda/crônica diária | `DI-Connect-Metrics/` | `MetricsAcuteTrainingLoad_<AAAAMMDD>_<AAAAMMDD>_*.json` | vários, um por período |

Os nomes em `DI-Connect-Metrics/` começam com o tipo da métrica (`MetricsAcuteTrainingLoad_`; há outros tipos na pasta, não usados).
Os dois `AAAAMMDD` do nome são o período do arquivo (o fim de um arquivo é o começo do seguinte); não use o nome para saber o dia de um
item, use o campo `calendarDate`. Todos são JSON com **lista na raiz**. Arquivo ausente ou lista vazia = atleta sem aquele dado.

### Limiar de lactato: `*_userBioMetrics.json`
É o **histórico de alterações**: uma lista de registros, cada um um evento de mudança do perfil biométrico (a maioria só de VO2 max).
Um registro traz **só os campos que mudaram**; para saber o limiar vigente num dia, ande pelos registros em ordem de data e guarde o
último valor de **cada campo separadamente** (um registro pode mudar a FC e não a velocidade). **O arquivo não está em ordem
cronológica**: ordene por `metaData.calendarDate` (empate: `metaData.sequence`).

| Campo | Tipo e unidade | Observação |
|---|---|---|
| `metaData.calendarDate` | texto `AAAA-MM-DDTHH:MM:SS.f` (1 a 3 casas decimais), **sem fuso** | quando a mudança foi registrada. Comparado com `firstbeatRunningLtTimestamp`, indica hora local de parede, não UTC; o que importa é o dia |
| `metaData.sequence` | inteiro | desempate |
| `metaData.userProfilePK` | inteiro | identificador do usuário: **ignorar e não gravar** |
| `version` | inteiro (ms desde 1970) | versão do registro; não usar como data |
| `lactateThresholdHearRate` | inteiro, bpm | FC de limiar. **O nome tem erro de grafia da Garmin ("Hear")**. `0` é sentinela de **sem limiar** (não é 0 bpm) |
| `lactateThresholdSpeed` | decimal, **m/s dividido por 10** | velocidade de limiar (multiplique por 10 para m/s; pace em s/km = 100 / valor). Conferido por plausibilidade, não por documentação da Garmin |
| `thresholdHeartRateAutoDetected` | bool | `true` detectado pelo relógio, `false` ajustado à mão |
| `firstbeatRunningLtTimestamp` | inteiro, segundos desde 1989-12-31 UTC (época Garmin) | quando o relógio detectou o limiar de corrida; acompanha a velocidade |
| `vo2MaxRunning`, `vo2MaxCycling`, `functionalThresholdPower`, `sportId`, `height`, `weight.*`, `activityClass` | vários | não usados na Meta 6 |
| `userSetNullFor*` | bool | marcam campo apagado pelo usuário; `true` aparece em registros sem o valor correspondente (leitura a confirmar) |

Como vem o histórico:
- Há registros com **FC e velocidade** (limiar detectado) e registros **só com FC** (ajuste manual ou `0`); a velocidade não aparece sem a FC.
- **Período sem limiar:** antes do primeiro registro com `lactateThresholdHearRate > 0` não há limiar. Um registro com `0` volta o atleta a "sem limiar".
- O limiar vigente num dia é o do **último registro com data menor ou igual ao dia** (qual dia vale para a atividade, local ou UTC, é da [[decisoes/0010-carga-de-treino]]).
- Atividades anteriores ao primeiro limiar ficam "sem carga".

### Zonas de FC: `*_heartRateZones.json` e FIT
`*_heartRateZones.json` é **só o retrato atual** (sem data, sem histórico): uma entrada por esporte.

| Campo | Tipo e unidade | Observação |
|---|---|---|
| `sport` | enum texto | `DEFAULT`, `RUNNING`, `CYCLING` |
| `trainingMethod` | enum texto | método das zonas (visto: `HR_MAX`, percentual da FC máxima) |
| `maxHeartRateUsed`, `restingHeartRateUsed`, `lactateThresholdHeartRateUsed` | inteiro, bpm | FC máxima, de repouso e de limiar usadas |
| `zone1Floor` ... `zone5Floor` | inteiro, bpm | piso de cada zona |
| `restingHrAutoUpdateUsed` | bool | repouso atualizado automaticamente |
| `changeState` | enum texto | estado da última alteração |

**O histórico de zonas não está nesse JSON.** O que vigorava em cada atividade está nos **FIT originais** (mensagens que o parser de hoje
não lê); logo, o histórico de zonas só existe para atividades com FIT:

| Mensagem FIT | Campo | Unidade | Observação |
|---|---|---|---|
| `time_in_zone` com `reference_mesg = session` (as de `lap`, `split` e `set` são outras) | `hr_calc_type` | enum (`percent_max_hr`, `percent_hrr`, `percent_lthr`, `custom`) | método das zonas na atividade |
| | `max_heart_rate`, `resting_heart_rate`, `threshold_heart_rate` | bpm | FC máxima, de repouso e de limiar **vigentes na atividade** |
| | `hr_zone_high_boundary` | lista de bpm (6 itens) | limites superiores das zonas |
| | `time_in_hr_zone` | lista em segundos (7 itens; `fitdecode` já converte a escala) | tempo em cada faixa; índice 0 = abaixo do primeiro limite |
| `zones_target` | `max_heart_rate`, `threshold_heart_rate`, `hr_calc_type` | bpm, enum | mesma informação, sem as listas |

A correspondência entre os 6 limites, os 7 tempos e as zonas 1 a 5 está em "Conferência com o Profile do FIT SDK (#140)", abaixo. Campos como `threshold_heart_rate` podem faltar. O `summarizedActivities.json` traz o **tempo em
cada zona** por atividade (`hrTimeInZone_0` ... `hrTimeInZone_6`, em **milissegundos**, somando cerca de `duration`), mas não os limites.

### Recordes pessoais: `*_personalRecord.json`
Lista na raiz com **um** objeto que tem a lista `personalRecords`.

| Campo | Tipo e unidade | Observação |
|---|---|---|
| `personalRecordId` | inteiro | |
| `activityId` | inteiro | mesmo `activityId` do resumo de atividades; `0` quando o recorde não vem de uma atividade (passos, sequência de metas) |
| `personalRecordType` | texto | nome em inglês: `Best 1km Run`, `Best 5km Run`, `Best Half Marathon`, `Farthest Run`, `Best 400m Pool Swim`, `Max Avg Power (20 min)`, `Most Steps in a Day`... |
| `value` | decimal | **segundos** nos `Best ...`; **metros** nos `Farthest ...` e `Longest ...`; watts, metros ou contagem nos demais: a unidade depende do tipo |
| `prStartTimeGMT` | texto estilo Java `Dia Mês DD HH:MM:SS GMT AAAA` (nomes em inglês, UTC) | início do recorde |
| `createdDate` | texto `AAAA-MM-DD` | dia em que o recorde foi gravado |
| `current` | bool | `true` no recorde vigente de cada tipo; os outros são recordes superados (histórico) |
| `confirmed` | bool | |

### Carga aguda/crônica: `MetricsAcuteTrainingLoad_*.json`
Lista de itens por dia, um arquivo por período.

| Campo | Tipo e unidade | Observação |
|---|---|---|
| `calendarDate` | inteiro, **ms desde 1970, sempre meia-noite UTC** | o **dia** do item (não é `AAAAMMDD`) |
| `timestamp` | inteiro, ms desde 1970 | momento da atualização |
| `dailyTrainingLoadAcute` | inteiro | carga aguda do dia (unidade de carga do Garmin) |
| `dailyTrainingLoadChronic` | inteiro | carga crônica do dia |
| `dailyAcuteChronicWorkloadRatio` | decimal | razão calculada pelo Garmin; nem sempre bate com `aguda / crônica` (outro arredondamento): use o campo. **Pode faltar** |
| `acwrPercent` | inteiro, 0 a 100 | posição da razão na faixa do Garmin. Pode faltar |
| `acwrStatus` | enum texto | `LOW`, `OPTIMAL`, `HIGH`, `VERY_HIGH` ou `NONE` (sem razão) |
| `acwrStatusFeedback` | enum texto | `FEEDBACK_1` ... `FEEDBACK_5` ou `NONE` |
| `deviceId`, `userProfilePK` | inteiro | identificadores: **ignorar e não gravar** |

Como vem o histórico: **pode haver vários itens para o mesmo `calendarDate`** (atualizações ao longo do dia, com valores diferentes); vale
o de **maior `timestamp`**. Dia sem item = sem dado do Garmin naquele dia.

### Leitor de saúde (#136)
`app/ingestao/garmin/saude.py` (`ler_saude(caminho, dia_retrato=None)`), mais `modelos_saude.py` (objetos devolvidos) e `zonas_fit.py`
(zonas de um FIT). Função pura: sem banco e sem rede. Aceita a mesma entrada de `ler_exportacao` (zip, pasta, zip dentro de zip) e
devolve `SaudeGarmin` (`limiares`, `zonas`, `recordes`, `carga_dia`, `avisos`). Achar os arquivos: pasta + sufixo, qualquer
profundidade; a árvore repetida (pasta, `DI_CONNECT/`, zip interno) é lida uma vez por conteúdo (hash). Arquivo ausente, ilegível ou
campo inválido: lista vazia (ou item ignorado) e um aviso em `avisos` e no log, sem exceção (só `FileNotFoundError` se o próprio
caminho não existe). Os avisos não trazem nome de arquivo, id nem valor.

| Dado | Regra do leitor ([[decisoes/0010-carga-de-treino]]) |
|---|---|
| Limiar (`LimiarRegistro`) | uma série por grandeza (`fc_bpm`, `velocidade_ms`); registros ordenados por `calendarDate` e `sequence`; `vigente_desde` é o dia; por dia e por campo vale o último valor; valor igual ao vigente da mesma grandeza não abre vigência nova. FC `0` = sem limiar: não vira registro (e não cancela um limiar anterior). FC fora de 30 a 250 bpm e velocidade fora de 0,5 a 10 m/s: ignoradas com aviso |
| Velocidade e pace | m/s = valor da fonte × 10 (0,370 → 3,70 m/s); pace s/km = 1000 / m/s = 100 / valor da fonte (0,370 → 270,27 s/km). `LimiarRegistro.pace_s_km` |
| Zonas (`ZonaFc`) | `garmin_export`: retrato do `heartRateZones.json`, um por esporte (`DEFAULT` → `padrao`, `RUNNING` → `corrida`, `CYCLING` → `ciclismo`), `vigente_desde` = `dia_retrato` (o JSON não tem data); teto da zona 5 = FC máxima. `garmin_fit`: `time_in_zone` da sessão, dia local da sessão, uma linha por mudança de zonas por esporte (`corrida`, `ciclismo` ou `padrao`); os 6 limites de `hr_zone_high_boundary` são o piso das zonas 1 a 5 e o teto da 5. `metodo` fica como a fonte traz (`HR_MAX` no JSON, `percent_max_hr` no FIT) |
| Recordes (`RecordePessoal`) | `activityId` 0 → id nulo; `prStartTimeGMT` lido sem depender de locale; modalidade e unidade (`s`, `m`, `W`, `passos`) deduzidas do nome do tipo (tipo desconhecido: unidade nula); `current` guardado em `atual` |
| Carga (`CargaGarminDia`) | um valor por dia (`calendarDate` em ms → dia UTC): vale o item de maior `timestamp`; a razão pode faltar (`None`) |

Testes: `services/api/tests/ingestao/test_saude_garmin.py` (tabelas escritas à mão a partir da linha do tempo das fixtures).
**Fora do leitor:** `bioMetrics_latest.json` (o histórico do `userBioMetrics` o cobre) e o tempo em cada zona.

#### Conferência com o Profile do FIT SDK (#140)
Fonte pública: o Profile do SDK da Garmin (pacote `garmin-fit-sdk` 21.221.0, repositório <https://github.com/garmin/fit-python-sdk>, arquivo
`profile.py`), conferido em 07/11/2026. Mensagem `time_in_zone`:

| Campo | O que o Profile diz |
|---|---|
| `hr_zone_high_boundary` | `uint8`, lista, bpm |
| `time_in_hr_zone` | `uint32`, lista, escala 1000, segundos |
| `hr_calc_type` | enum `hr_zone_calc`: `custom`, `percent_max_hr`, `percent_hrr`, `percent_lthr` |
| `max_heart_rate`, `resting_heart_rate`, `threshold_heart_rate` | bpm |

**O que o Profile não diz:** quantos itens a lista tem e que o primeiro é o piso da zona 1. O nome "high boundary" quer dizer limite
**superior** de cada faixa de `time_in_hr_zone`. A leitura dos 6 limites como piso das zonas 1 a 5 e teto da 5 vem de duas conferências:
`time_in_hr_zone` tem 7 faixas (índice 0 = abaixo do primeiro limite), logo 6 limites separam as 7 faixas e o primeiro é o limite superior da
faixa 0, ou seja o piso da zona 1; e os limites do FIT são crescentes e têm a mesma forma do retrato do JSON (`zone1Floor` ... `zone5Floor` em 50, 60, 70, 80 e 90 % da
FC máxima, e a FC máxima como teto; nas fixtures, 95 a 190 no FIT e 94 a 188 no JSON). Essa parte é **inferência confirmada por consistência, não texto do Profile**. O
leitor rejeita FIT cujos 6 limites não sejam positivos e em ordem não decrescente.

### Gravação no banco (#140 e #174)
`app/ingestao/saude.py`: `importar_saude(session, caminho, atleta_nome, dia_retrato=None)` (`dia_retrato` padrão: hoje) lê com
`ler_saude` e grava em `limiar_atleta`, `zona_fc_atleta`, `recorde_pessoal` e `carga_garmin_dia` ([[modulos/banco]], [[decisoes/0010-carga-de-treino]]). Sem rede. Devolve
`RelatorioSaude` (contagens `inseridas`, `atualizadas`, `ignoradas` por tabela: limiar, zonas, recordes e carga, mais os avisos do leitor; nunca valor).
- **Chaves:** limiar `(atleta, grandeza, origem, vigente_desde)`; zonas `(atleta, esporte, origem, vigente_desde)`; recordes `(atleta, origem, modalidade, categoria, alcancado_em)`; carga do Garmin
  `(atleta, origem, dia)`. Chave nova = linha nova
  (histórico). Mesma chave com valor diferente = correção da fonte: atualiza, conta `atualizadas` e dá aviso (o único caso de sobrescrita).
- **Retrato das zonas** (`garmin_export`): `vigente_desde` = dia da importação. Se as zonas são iguais às vigentes do esporte, nada é gravado
  (reimportar em outro dia não duplica); se diferem, abre uma vigência nova. Zonas do FIT (`garmin_fit`): uma linha por mudança, no dia local da sessão.
- **Recordes (#174):** um recorde melhorado tem outra data (`prStartTimeGMT`), logo é **linha nova**, e o anterior fica (nas fixtures,
  `Best 1km Run` fica com duas linhas, 04/03 e 11/03). A flag `current` do leitor não é gravada: o vigente de cada tipo é o de maior
  `alcancado_em`. `unidade` é `s`, `m`, `W`, `passos` ou nula (tipo que o leitor não reconhece); `atividade_fonte_id` nulo quando o
  `activityId` é 0; sem FK, porque a atividade pode não estar importada. **Carga do Garmin:** uma linha por dia (já resolvida pelo leitor);
  aguda, crônica e razão aceitam nulo. Correção da fonte na mesma chave atualiza (aviso sem valor).
- **Exportação mais curta nunca apaga linhas.** Sem dados de saúde (nem limiar, zonas, recordes nem carga): nada é gravado, nem o atleta é criado; os motivos
  vêm em `avisos` ("sem carga" com motivo é da #141).
- `limiar_vigente(session, atleta_id, grandeza, dia)` e `zonas_vigentes(session, atleta_id, esporte, dia, origem=None)` aplicam a regra de
  vigência (maior `vigente_desde <= dia`; antes da primeira, `None`; no mesmo dia `informado` vence `garmin_export`). A #141 usa a primeira.
- Comando: `uv run python -m worker.importar_saude <caminho> --atleta "<nome>"` ([[modulos/worker]]); o `importar_garmin` chama a mesma função no
  fim, e erro ali vira aviso. `uv run python -m worker.apagar_saude --atleta "<nome>"` (LGPD) apaga as quatro tabelas de saúde do atleta
  (`apagar_saude_do_atleta`); o atleta, as atividades e os FIT ficam. Imprime só contagens.
- Testes: `services/api/tests/ingestao/test_importar_saude.py` e `services/worker/tests/test_importar_saude.py`.

### Atleta sem dados de saúde
Os arquivos acima são opcionais. Um atleta sem eles tem a exportação com atividades e FIT e nenhuma das pastas de saúde e métricas
(ou os arquivos com lista vazia). Fica "sem carga", com o motivo; o limiar não é estimado. Nas fixtures: `saude/exportacao_sem_saude.zip`
(e `exportacao_minima.zip`, o mesmo caso).

### Fixtures de saúde (`tests/fixtures/garmin/saude/`)
Geradas por `tests/fixtures/garmin/gerar_fixtures_saude.py` (saída determinística; `tests/test_fixtures_saude.py` falha se estiverem
desatualizadas). Valores, identificador de usuário (`7000001`), dispositivo e nome (`atleta-ficticio`) inventados. A linha do tempo
(limiares, FC máxima e atividades) está no topo do script.

| Arquivo | Conteúdo |
|---|---|
| `exportacao_saude.zip` | as mesmas 5 atividades de `exportacao_minima.zip` mais os 5 tipos de arquivo acima (carga em 2 arquivos); os FIT trazem `time_in_zone` e `zones_target` |
| `exportacao_sem_saude.zip` | só atividades e FIT comuns, nenhuma pasta de saúde |

Cobertura: período **sem limiar** no começo (registros de VO2 max e um registro de FC `0`); **1º limiar** entre as atividades A e C;
**limiar de FC ajustado à mão** (só FC) e **FC máxima alterada** (zonas novas) entre D e B; **2º limiar** entre D e B; registro fora de
ordem no arquivo; carga diária de 25 dias, com dias de mais de um item e o primeiro dia sem razão; 6 recordes (um tipo com recorde
superado e vigente; um sem atividade, `activityId = 0`).

## Pendências
- Corrigir a regra de tiros em rodagens com intensidade mista (#48).
- `track_running` (pista) ainda sem exemplo real; a fixture B continua cobrindo.
- ~~Atividades do resumo sem FIT~~: resolvido em 03/11. Não faltam arquivos.
