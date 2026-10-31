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
(tiros de 1 km). O formato abaixo vem do que se conhece da exportação; **ainda não foi confirmado com dado real**
(a exportação do Angelo não está em `dados-teste/garmin/`). Tudo é testado com fixtures sintéticas.

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
- **`inicio_local`:** mesmo instante de `inicio`, com o fuso do atleta (deslocamento = `startTimeLocal` - `startTimeGmt`, em minutos), então `.date()` dá a data local. `None` quando o JSON não traz o campo (FIT sem JSON, atividades C, D e E das fixtures) ou o deslocamento passa de 15 h. O parser não inventa fuso: o fallback `America/Sao_Paulo` fica na #14.
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
  (`NULL` se a distância é 0), `versao_deteccao` vazio (a #14 preenche).
- **`intensidade`:** minúsculas e sem espaços; valor fora da lista do `CHECK` (ADR 0002) vira `other`, nunca erro;
  sem valor fica `NULL`.
- **`inicio_local` não é gravado:** a tabela `atividade` não tem a coluna (mudaria o modelo; exige ADR e aprovação do Theo).
  A #14 usa `America/Sao_Paulo` a partir do `inicio` em UTC enquanto isso.
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

## Pendências
A confirmar com o dado real (#19):
- nomes exatos das pastas e dos arquivos, e se há mais de um `summarizedActivities.json`;
- unidades de `duration` (ms) e `distance` (cm) e o fuso de `startTimeGmt`;
- se `startTimeLocal` existe com esse nome e semântica na exportação real;
- valores reais de `activityType` para esteira, pista e natação em águas abertas;
- se os `.fit` vêm todos no zip interno e se o `activityId` aparece no nome deles;
- se `intensity` vem preenchido em todos os relógios (intervalados sem treino estruturado podem trazer só `active`).
