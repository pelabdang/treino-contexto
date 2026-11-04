---
tipo: modulo
status: em-uso
dono: duda
atualizado: 2026-11-04
links: [[produto/meta-3-como-rodar]], [[modulos/worker]], [[modulos/banco]], [[decisoes/0006-upload-de-fit]], [[decisoes/0007-clima-da-atividade]], [[produto/roadmap]], [[diario/2026-11-03]], [[produto/meta-4-como-rodar]]
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
| `tipos.py` | tipo Garmin para `modalidade` (corrida/natacao/ciclismo/outra) e `subtipo` (esteira, pista, trilha, piscina, aguas_abertas) |
| `unidades.py` | ms para s, cm para m, epoch ms para datetime UTC |

### Regras
- **Casamento JSON x FIT:** pelo horário de início, tolerância de 60 s (vale o FIT mais próximo, cada FIT casa
  uma vez). O `inicio` da atividade é o do JSON; `inicio_offset_s` das voltas é relativo ao início da sessão no FIT.
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

## Arquivos principais
- `services/api/app/ingestao/garmin/` e `services/api/tests/ingestao/test_garmin_parser.py`
- `services/api/app/ingestao/importacao.py` (gravação: `importar`, `importar_fit`, `gravar_atividade`) e `fit_guardado.py` (guarda em `FIT_DIR`)
- `services/worker/worker/importar_garmin.py` e `apagar_fit.py` (linhas de comando) e `services/worker/tests/test_importar_garmin.py`
- `services/api/tests/ingestao/test_importar_fit.py`
- `tests/fixtures/garmin/gerar_fixtures.py` e `tests/fixtures/garmin/exportacao_minima.zip`
- `tests/test_fixtures_garmin.py`
- `tests/fixtures/garmin/fit/` e `tests/test_fixtures_fit_upload.py` (FIT do upload)

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
inexistente): suba o container em outra porta e ajuste `DATABASE_URL`. A importação completa leva alguns minutos.

## Pendências
- Corrigir a regra de tiros em rodagens com intensidade mista (#48).
- `track_running` (pista) ainda sem exemplo real; a fixture B continua cobrindo.
- ~~Atividades do resumo sem FIT~~: resolvido em 03/11. Não faltam arquivos.
