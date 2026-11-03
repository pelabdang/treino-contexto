---
tipo: decisao
status: em-uso
dono: theo
atualizado: 2026-11-03
links: [[modulos/ingestao-garmin]], [[modulos/api]], [[modulos/worker]], [[modulos/banco]], [[modulos/mobile]], [[modulos/api-client]], [[decisoes/0001-modelo-de-dados-minimo]], [[decisoes/0003-fuso-da-atividade]], [[decisoes/0004-contrato-tela-evolucao]], [[decisoes/0005-serie-de-tiros-o-que-entra]], [[produto/roadmap]]
---
# ADR: 0006 Upload de arquivo FIT (Meta 3)

**Status: aceita (Theo, 03/11).** Só documentação: nenhum código muda aqui. As
issues da Meta 3 (leitor, `importar_fit`, endpoint, app) seguem esta ADR.

## Contexto
Enquanto a API da Garmin não é aprovada, o plano B é o atleta enviar um `.fit` pelo app. A atividade entra no banco
e, se for um treino de tiros, na série da Meta 2. Isso toca API, worker, banco e app, por isso é ADR.

O que o código do `main` mostra (conferido antes de escrever):
- **O leitor FIT está no worker** (`services/worker/worker/garmin/`: `fit.py`, `modelos.py`, `unidades.py`,
  `tipos.py`, `leitor.py`), e o `treino-worker` depende do `treino-api` (`services/worker/pyproject.toml`, fonte
  `workspace`). A API não pode importar o worker sem criar um ciclo. Hoje só um script da API
  (`services/api/scripts/exportar_openapi.py`) e testes importam o worker.
- **A gravação no banco também está no worker** (`worker/importar_garmin.py`). `importar(session, caminho,
  atleta_nome)` recebe um **caminho** e o **nome** do atleta (cria o atleta se faltar), lê com `ler_exportacao`,
  grava, faz `commit` e chama `classificar_atividades`. Ela não recebe bytes nem `atleta_id`, então o upload não a
  reaproveita como está: o corpo do laço (comparar, inserir ou atualizar uma atividade) precisa virar função própria.
- **`ler_fit(bytes)` já serve ao upload**: devolve `FitLido` ou levanta `ValueError` (corrompido ou truncado) e
  `FitSemAtividade`, que é `ValueError` (FIT que não é atividade). `tipos.de_fit` dá a modalidade. Falta uma função
  pública que junte os dois e devolva `AtividadeImportada` (hoje `_de_fit` é privada e recebe um objeto interno).
- **Identidade:** a chave única de `atividade` é `(atleta_id, fonte, fonte_id)`. Na exportação, a atividade com JSON
  usa o `activityId` como `fonte_id`; um FIT sem JSON usa `fit-<serial>-<criação>` do `file_id`, ou `fit-` + 16
  caracteres do SHA-1 do conteúdo. A `fonte` padrão é `garmin_export`. Um upload e a exportação do mesmo treino têm
  chaves diferentes, então **entrariam duas vezes**, e isso vale nos dois sentidos (upload antes ou depois da
  exportação). O parser já casa JSON e FIT por início com tolerância de **60 s** (`TOLERANCIA_S`).
- **`atividade.arquivo_bruto`** é `String(500)`, hoje o caminho lógico dentro da exportação (com `!/` para zips
  aninhados). A comparação "mudou" da importação **ignora** esse campo (`_igual`).
- **A API não aceita arquivo hoje:** `python-multipart` não está no `uv.lock`. O CORS libera só `GET` (ADR 0004,
  item 7).
- A importação já classifica as corridas do atleta no fim (`classificar_atividades`, idempotente), então a série da
  Meta 2 se atualiza sozinha.

## Decisão
Já decididas antes desta ADR e só registradas aqui: guardar o FIT localmente (Angelo); sem login, só local, atleta
fixo por configuração (Angelo); 10 MB (Angelo); qualquer modalidade, só corrida na série (Angelo); regra dos 60 s,
empate e leitor num lugar compartilhado (Theo); `python-multipart` (Theo). A ADR fixa os detalhes.

### 1. Onde fica o leitor: dentro da API (`app/ingestao/`), e o worker importa de lá
O worker já depende da API, então mover para a API não cria ciclo e não mexe no grafo do workspace:
- `services/worker/worker/garmin/` (parser inteiro) vai para `services/api/app/ingestao/garmin/`, sem mudar o
  comportamento.
- O que grava no banco (o corpo do laço de `importar`, `normalizar_intensidade`, `pace_s_km`, a nova `importar_fit`)
  vai para `services/api/app/ingestao/importacao.py`, ao lado de `classificar_atividades`, que já mora em
  `app/servicos/`. O endpoint e o worker chamam as mesmas funções.
- `worker/importar_garmin.py` fica só como linha de comando (`python -m worker.importar_garmin`) e continua
  expondo `importar(session, caminho, atleta_nome)`, que os testes e o `exportar_openapi.py` usam.
- `fitdecode` passa para as dependências do `treino-api` (o worker a recebe por `treino-api`). `python-multipart`
  entra no `treino-api`. O `uv.lock` é atualizado e o CI roda `uv sync --locked`. `fit-tool` continua só como
  dependência de desenvolvimento.

Por quê: a API é a dona do modelo de dados (ADR 0001), e o upload é a primeira entrada de dados que nasce na API.
Quem precisa ler FIT e gravar atividade é a API; o worker é só mais um chamador.

### 2. Identidade da atividade: regra dos 60 s, nos dois caminhos
Uma atividade que chega (por upload ou pela exportação) **casa** com uma existente quando:
1. a chave `(atleta_id, fonte, fonte_id)` já existe (caminho de hoje; `fonte` do upload é `fit_upload`); ou, se não existir,
2. há atividade **do mesmo atleta, da mesma modalidade** com `inicio` a **até 60 s** de diferença (inclusive, como `TOLERANCIA_S`).

Casou: **atualiza** a atividade existente (mesmo `id`), nunca insere outra. Não casou: insere.

- **Empate** (duas ou mais candidatas na regra 2): escolhe a de **início mais próximo**; se ainda empatar, a de
  **menor `id`**. O relatório leva um aviso com os ids (por exemplo `candidatas 12 e 15; usada a 12`). As outras
  não são tocadas.
- **A regra vale também para `importar` (exportação).** Sem isso, o treino enviado por upload e depois vindo na
  exportação entraria duas vezes (a chave por `activityId` não encontra a linha do upload). Essa mudança no
  `importar` não estava na proposta da Meta 3 e entra na issue do `importar_fit`.
- **Qual `fonte` e `fonte_id` ficam:** a exportação é a fonte mais rica (JSON com fuso local e totais). Quando a
  exportação casa com uma linha de upload, a linha passa a ter `fonte = garmin_export` e o `fonte_id` do
  `activityId`, e a chave volta a ser a de hoje (reimportar é idempotente sem consultar os 60 s). Quando o upload
  casa com uma linha da exportação, a linha **não muda** `fonte` nem `fonte_id`.
- **Quais campos mudam:** os mesmos da importação de hoje (modalidade, subtipo, início, duração, distância, FC,
  `fuso_min` só se a fonte trouxer, voltas substituídas se mudaram). Um upload sem horário local **não apaga**
  `fuso_min` já gravado (ADR 0003).
- **Resultado:** `inserida`, `atualizada` (algo mudou) ou `ignorada` (nada mudou), com o `id` da atividade. Depois
  de qualquer um, `classificar_atividades` roda para o atleta.
- **Corrida concorrente** (dois envios iguais ao mesmo tempo, violação da chave única): relê uma vez e trata como
  existente. Uso local, de uma pessoa, então não há mais tratamento.

### 3. Guarda do FIT
- **Pasta:** variável `FIT_DIR` (em `app/config.py` e `.env.example`, sem segredo). Padrão `dados-upload/fit/`,
  **relativo à raiz do repositório** (não ao diretório em que o comando roda), incluído no `.gitignore` junto de
  `dados-upload/`. Um teste confere que o padrão está no `.gitignore`. A pasta é criada na primeira gravação,
  com permissão só do usuário.
- **Nome:** `<atleta_id>/<sha256 do conteúdo>.fit`. Sem nome do atleta, data, lugar nem o nome que o cliente mandou:
  **o nome do arquivo enviado nunca é usado no disco** (também evita caminho com `../`). Exemplo sintético:
  `1/9f2c…e41a.fit`.
- **`atividade.arquivo_bruto`** recebe o caminho **relativo a `FIT_DIR`** (`1/9f2c…e41a.fit`). Nenhuma migração: o
  campo e o tamanho já servem. Um valor com `!/` é caminho dentro de uma exportação; sem `!/` e no formato
  `<número>/<64 hex>.fit` é arquivo guardado em `FIT_DIR`. Quando a importação da exportação atualiza uma linha cujo
  `arquivo_bruto` já está nesse formato, ela **mantém** o valor.
- **Reenvio do mesmo conteúdo:** o arquivo já existe com o mesmo hash, então não é gravado de novo e a atividade
  fica `ignorada`. Se o arquivo sumiu do disco, o reenvio o grava de novo e conta como `atualizada`.
- **FIT diferente que casa** com uma atividade existente (regra de 60 s ou mesma chave): grava o arquivo novo e
  troca o `arquivo_bruto`. O arquivo antigo é **apagado da pasta se nenhuma outra atividade o referencia** (é dado
  pessoal órfão); se outra atividade ainda aponta para ele, fica. A conferência é por `arquivo_bruto` igual ao caminho
  antigo, e a remoção só acontece **depois do `commit`** (falha ao apagar vira aviso, não erro). Quando o upload casa com
  uma atividade da exportação, o `arquivo_bruto` deixa de apontar para o original dentro do zip; o zip da
  exportação segue onde está.
- **Ordem das operações:** valida e lê o FIT; mexe no banco na sessão; grava o arquivo num temporário e renomeia;
  só então faz `commit`; depois do `commit`, apaga o arquivo antigo órfão, se houver. Se o `commit` falha, apaga o
  arquivo que esta chamada criou. FIT inválido ou recusado
  **nunca** chega ao disco nem ao banco.
- **Como apagar:** comando `uv run python -m worker.apagar_fit --atleta-id N` apaga os arquivos do atleta em
  `FIT_DIR/<N>/` e põe `arquivo_bruto = NULL` nas atividades dele que apontavam para eles (formato acima). **As
  atividades, os segmentos e a série ficam.** Imprime quantos arquivos apagou e quantas atividades limpou, e é
  idempotente. Apagar a pasta à mão também é seguro: nada lê o FIT guardado hoje (serve para reprocessar e para
  conferência), só sobra um `arquivo_bruto` apontando para o vazio; o comando limpa isso.

### 4. Limites
- Um arquivo por envio, campo multipart `arquivo`. Só nome terminado em `.fit` (sem diferenciar maiúsculas); o
  conteúdo é validado de qualquer jeito pelo `ler_fit`.
- **10 MB** no máximo (10 485 760 bytes). Acima disso, `413`. O limite vale pelos bytes realmente lidos (lê em
  pedaços e para em 10 MB + 1), não só pelo `Content-Length`.
- **Qualquer modalidade** entra no banco; **só corrida** entra na série (regra de [[decisoes/0005-serie-de-tiros-o-que-entra]]
  e esteira fora, como hoje). Natação e ciclismo ficam gravados e fora do gráfico.

### 5. Erros
Corpo no modelo `Erro {detail: string}` da ADR 0004, declarados no OpenAPI. A mensagem não repete dado do arquivo.

| Caso | Status |
|---|---|
| FIT corrompido, truncado, sem horário de início ou sem duração; extensão que não é `.fit` | `400` |
| FIT válido que não é atividade (`file_id.type` diferente de `activity`) | `400` (mensagem própria) |
| Arquivo acima de 10 MB | `413` |
| Atleta inexistente | `404` |
| Campo `arquivo` ausente (ou mais de um) | `422` (formato do FastAPI) |
| Gravação criada | `201`; atividade que já existia (`atualizada` ou `ignorada`) `200` |

Resposta de sucesso: `{"resultado": "inserida" | "atualizada" | "ignorada", "atividade_id": 1, "avisos": []}`.
O endpoint é `POST /atletas/{atleta_id}/atividades/fit`. O CORS passa a liberar `POST` além de `GET` (isso amplia o
item 7 da [[decisoes/0004-contrato-tela-evolucao]], que dizia só `GET`; continua sem `*`). O cliente de
`packages/api-client/` é regerado.

### 6. Sem login, só local
O atleta vem da configuração do app (`EXPO_PUBLIC_ATLETA_ID`, ADR 0004, item 8). Qualquer um que alcance a API grava
arquivos na máquina: por isso é só para uso local, sem deploy. Autenticação fica para a meta de login.

### Exemplo sintético
Upload de um FIT de intervalado (fixtures) de um atleta de id 1, depois o mesmo treino na exportação:
```
POST /atletas/1/atividades/fit   (arquivo=intervalado.fit)
-> 201 {"resultado": "inserida", "atividade_id": 7, "avisos": []}      fonte=fit_upload, arquivo_bruto="1/<sha256>.fit"
POST /atletas/1/atividades/fit   (mesmo arquivo)
-> 200 {"resultado": "ignorada", "atividade_id": 7, "avisos": []}      nada gravado de novo
importar exportação (JSON com início a 2 s do FIT)
-> atividade 7 atualizada: fonte=garmin_export, fonte_id=<activityId>, fuso_min preenchido, arquivo_bruto mantido
```

## Alternativas consideradas
- **Pacote próprio no workspace `uv` para o leitor** (por exemplo `services/ingestao/`): o leitor é puro e poderia
  morar sozinho, mas o `importar_fit` grava no banco e usa os modelos da API, então esse pacote dependeria do
  `treino-api` e a API dele: ciclo de novo. Ficaria só o parser lá, com um pacote, um `pyproject` e um lock a mais,
  e a gravação ainda numa terceira parte. Descartado.
- **A API chamar o worker** (fila ou processo): fila foi adiada (ver [[modulos/worker]]); para um arquivo de
  até 10 MB, local, ler na requisição basta.
- **Não guardar o FIT** (proposta inicial do time): descartada pelo Angelo; o arquivo permite reprocessar quando a
  regra de detecção mudar.
- **Nome com data ou nome original**: expõe dado pessoal no nome do arquivo e abre caminho para `../`. Hash do
  conteúdo dá reenvio idempotente de graça.
- **Casar só pela chave** (sem os 60 s): duplica o treino quando ele chega por upload e por exportação.
- **Casar só no upload** (não no `importar`): deixa a ordem upload e depois exportação duplicar.
- **Deixar o arquivo antigo na pasta quando um FIT novo casa** (primeira proposta): sobraria dado pessoal de saúde
  órfão, sem atividade que o referencie e fora do alcance do `arquivo_bruto`. Por isso o antigo é apagado quando
  ninguém mais o usa.
- **Limite só pelo `Content-Length`:** o cabeçalho pode mentir ou faltar.

## Consequências
- Mudança de estrutura: o parser e a gravação saem do worker para `app/ingestao/` (issue do leitor, sem mudar
  resultado; o oráculo das fixtures e os testes de ponta a ponta continuam valendo).
- `importar` (exportação) passa a aplicar a regra dos 60 s; reimportar a exportação continua idempotente.
- Uma pasta nova fora do git (`dados-upload/`) guarda dado pessoal de saúde do atleta; o repositório é público,
  então o `.gitignore` e o teste dele são obrigatórios, e os testes usam só FIT sintético em `tmp_path`.
- Sem mudança de modelo de dados nem migração.
- O endpoint de upload é síncrono e lê o arquivo na memória (até 10 MB). Serve ao uso local; fila e processamento
  em segundo plano ficam para quando houver deploy.
- `classificar_atividades` roda sobre todas as corridas do atleta a cada upload (idempotente, barato localmente).
  Também regrava `versao_deteccao`, então um upload pode zerar `reclassificacao_pendente` ([[modulos/api]]).
- O `arquivo_bruto` de uma atividade da exportação pode passar a apontar para o upload.
- Teste previsto na issue do `importar_fit` (#94): FIT diferente que casa troca o `arquivo_bruto` e apaga o antigo da
  pasta; se uma segunda atividade ainda aponta para o antigo, ele fica; erro ao apagar não derruba o envio.
- Ordem das issues: ADR (esta), leitor movido e FIT sintéticos (em paralelo), `importar_fit` com o comando de
  apagar, endpoint com cliente regerado, botão no app, documentação, QA e resultado.

## Data e quem decidiu
2026-11-03. Guardar o FIT localmente, sem login e só local, 10 MB e qualquer modalidade com só corrida na série:
Angelo. Regra dos 60 s, leitor compartilhado sem ciclo e `python-multipart`: Theo. Empate (início mais próximo,
depois menor `id`, com aviso), lugar do leitor, nome do arquivo, ordem das operações, apagar e erros: proposta da
Duda, aprovadas pelo Theo em 03/11. O Theo também decidiu que o FIT substituído é apagado quando nenhuma outra
atividade o referencia. Se algo aqui mudar o que é guardado dos alunos, volta para o Angelo.
