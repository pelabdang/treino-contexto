---
tipo: modulo
status: em-uso
dono: duda
atualizado: 2026-10-31
links: [[modulos/worker]], [[modulos/banco]], [[produto/roadmap]]
---
# Módulo: ingestão Garmin

## Para que serve
Ler a exportação "Exportar seus dados" do Garmin Connect e transformar em atividades e voltas, para a Meta 1
(tiros de 1 km). O formato abaixo vem do que se conhece da exportação; **foi conferido com uma exportação real na #19**
(conferido depois com uma exportação real, ver "Conferência com a exportação real"). Os testes usam fixtures sintéticas.

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
único lugar do código (`worker/garmin/unidades.py`) e tem teste.

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

## Parser (`services/worker/worker/garmin/`)
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

## Importação no banco (`worker/importar_garmin.py`)
```
uv run python -m worker.importar_garmin <caminho> --atleta "<nome>"
```
Usa `DATABASE_URL` (Postgres do docker compose; rode `alembic upgrade head` antes). Imprime
`inseridas`, `atualizadas`, `ignoradas` e os avisos (inclui os do parser). Função: `importar(session, caminho, atleta_nome)`.

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
- **Classificação no fim:** depois de gravar, chama `classificar_atividades` ([[modulos/api]]): marca os segmentos
  das corridas como `tiro`/`recuperacao`/`volta`, grava `versao_deteccao` e sugere `tipo_treino = intervalado`
  (sem sobrescrever professor/TrainingPeaks/confirmado). É idempotente e refaz a classificação quando as voltas
  foram substituídas. A comparação "mudou" das voltas considera segmentos de todos os tipos.
- Atividade sem duração (nem soma de voltas) é ignorada com aviso, porque `duracao_s` é obrigatório.
- Testes: `services/worker/tests/test_importar_garmin.py` (SQLite local; Postgres via `TEST_DATABASE_URL`).

## Arquivos principais
- `services/worker/worker/garmin/` e `services/worker/tests/test_garmin_parser.py`
- `services/worker/worker/importar_garmin.py` e `services/worker/tests/test_importar_garmin.py`
- `tests/fixtures/garmin/gerar_fixtures.py` e `tests/fixtures/garmin/exportacao_minima.zip`
- `tests/test_fixtures_garmin.py`

## Depende de
- [[modulos/worker]] (onde fica o parser) e [[modulos/banco]] (destino).

## Como testar
`uv run pytest -q` na raiz.

## Conferência com a exportação real (#19)
Feita em 2026-11-01 com uma exportação real (fica em `dados-teste/`, fora do git). Aqui só o **formato**:
nenhum valor, contagem, data ou nome de atividade vem do dado pessoal.

Confirmado, igual ao esperado:
- `startTimeGmt`, `duration` (ms) e `distance` (cm): duração, distância e pace das corridas saem plausíveis, e
  `startTimeGmt` bate com o início do FIT, então o casamento por horário funciona.
- `startTimeLocal` existe em todas as atividades, com a semântica descrita acima. Há também `timeZoneId` (não usado).
- `activityType`: `running`, `treadmill_running`, `trail_running`, `cycling`, `indoor_cycling`, `virtual_ride`,
  `lap_swimming` e `open_water_swimming` mapeiam como esperado; `strength_training`, `pilates`, `elliptical`,
  `multi_sport` e `transition_v2` viram `outra`. Não apareceu `track_running` (pista) nesses dados.
- As voltas vêm dos `lap` do FIT. `intensity` aparece nos relógios usados, mas não em todas as atividades
  (ciclismo e natação costumam vir sem).

Divergências em relação às fixtures:
- **Resumo paginado:** vários `<usuario>_<n>_summarizedActivities.json` (`_1_`, `_301_`, `_601_`...), cada um com
  uma página da lista. O parser lê todos; um teste cobre.
- **A árvore tem cópias:** a pasta descompactada, `DI_CONNECT/` e `Arquivo.zip` repetem os mesmos `.fit`. O parser
  lê cada arquivo uma vez (hash do conteúdo).
- **Nem todo `.fit` é atividade:** a maioria dos arquivos (monitoramento diário e outros) tem `file_id.type` diferente
  de `activity`. O parser descarta esses sem decodificar o resto e sem aviso. Isso, mais o hash e não abrir arquivos
  irrelevantes, reduziu a leitura de vários minutos para poucos.
- **O número no nome do `.fit` não é o `activityId`** (nome `<usuario>_<número>.fit`), então o casamento é só por
  horário (já era a regra). Há nomes de outros apps (`zwift-activity`) e um `.gpx` no zip interno, ignorado.
- **Lixo do macOS:** `__MACOSX/` e `._*` aparecem nos zips; são ignorados.
- **Arquivos sem relação** (aviação, golfe, saúde...) estão na raiz; só `*summarizedActivities.json`, `.fit` e `.zip`
  são lidos, e os outros nem são abertos.
- **Atividades sem FIT:** parte das atividades do resumo não tem `.fit` (musculação e semelhantes, e algumas
  corridas); entram sem voltas, com aviso.
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
- Corrigir a regra de tiros em rodagens com intensidade mista (issue aberta).
- `track_running` (pista) ainda sem exemplo real; a fixture B continua cobrindo.
- Atividades do resumo sem FIT: confirmar com o dono se faltam arquivos ou se são atividades sem voltas.
