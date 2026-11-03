---
tipo: guia
status: em-uso
dono: nina
atualizado: 2026-11-03
links: [[produto/meta-3-como-rodar]], [[produto/meta-2-como-rodar]], [[produto/meta-1-como-reproduzir]], [[decisoes/0007-clima-da-atividade]], [[modulos/clima]], [[modulos/ingestao-garmin]], [[modulos/banco]], [[modulos/worker]], [[modulos/api]], [[modulos/api-client]], [[metricas/clima-oraculo]], [[diario/2026-11-03]]
---
# Meta 4: como rodar o clima da atividade

Passo a passo do clima de cada atividade: Postgres próprio, migrações até a 0005, fixtures, posição de início,
`preencher_clima` com a **resposta gravada** (sem rede) e o `GET` novo da API. Só dado sintético ("Parque do Exemplo",
lugar inventado). A base é a mesma do [[produto/meta-3-como-rodar]]; as regras estão na
[[decisoes/0007-clima-da-atividade]] e em [[modulos/clima]].

**Situação da verificação (#115, Nina, 03/11):** todos os passos abaixo foram rodados de verdade, com banco
`treino-meta4` na porta 5444, e o banco foi derrubado no fim. **Nada chamou o Open-Meteo:** o clima usou o cliente real
com transporte falso (`httpx.MockTransport`) e a resposta gravada. **Não rodado aqui:** a chamada real à API (uma
chamada manual com a posição inventada foi feita na #112, resultado em [[modulos/clima]]), o app mobile (o clima ainda não aparece na tela). O upload de FIT seguido
de `preencher_clima` com `FIT_DIR` foi rodado depois, na #116 (parágrafo abaixo), e é coberto por `tests/test_e2e_meta4.py`.

**Verificado na #116 (Bia, 03/11):** o guia foi rodado de novo, com banco `treino-qa116` (Postgres 5455, API na 8055,
`FIT_DIR` temporária), só dado sintético, e tudo foi derrubado no fim (`down -v`; `docker ps` só com os containers que já
existiam). **Bateu:** cinco `Running upgrade` até a `0005`; `inseridas=5` (JSON, 5 avisos) e `inseridas=6` (FIT); posições
`12.35 / -45.68` só nas atividades 7, 12, 13 e 15; `--so-posicao` com `0`, `1` e `0`; `clima_gravado.py ok` com `chamadas=4`
(`ok=4 indoor=5 sem_posicao=7`) e depois `chamadas=0`; os valores da tabela do passo 5; o `GET` da 13, 9, 10, 8, 7 e os dois
`404`; `openapi.json` sem `inicio_lat`; e a tabela do passo 7 (pendente nos 7 dias com `chamadas=0`, `null` com 12 e 13
pendentes e a 15 `ok`, 503 até `tentativas=5` com "5 rodadas sem sucesso: HTTP 503", 400 como `falha` na hora, e
`--refazer-falhas` com `chamadas=3`). **O que o guia não cobria e agora foi rodado:** o upload do FIT da lap por
`POST /atletas/1/atividades/fit` (`201`, atividade 17, posição `12.35 / -45.68`, `pendente` até `clima_gravado.py ok`, depois
`ok` com os mesmos valores da 13). **Não bateu:** nada. **Diferença:** na Bia o passo 3 importou a Meta 1 também pela função
`importar` (e não por `worker.importar_garmin`), para não passar por nenhum caminho com rede; por isso a linha `clima: chamadas=0`
desse comando **não foi conferida** na #116. **Não verificados:** a chamada real ao Open-Meteo (proibida aqui), o app (web, iOS e
Android: o clima não tem tela, "não se aplica") e o `worker.importar_garmin` com as fixtures de clima. O teste automatizado é
`tests/test_e2e_meta4.py` (15 testes, guarda de socket, `httpx.MockTransport` sobre a resposta gravada).

## Antes de começar
- `git`, `uv`, Docker (Compose 2.24 ou mais novo) e `curl`. Comandos na **raiz** do repositório.
- **Não use o banco do seu dia a dia** (`treino-contexto-postgres-1`). Rode sempre com `-p treino-meta4`
  (volume `treino-meta4_pgdata`). Sem `-p`, o `docker compose` usa o volume `treino-contexto_pgdata`.
- Escolha uma **porta livre** (`docker ps` e `lsof -i :<porta>`). Abaixo, a 5444 para o Postgres e a 8044 para a API.
- **Cuidado com `worker.importar_garmin`:** no fim, ele busca o clima das atividades que entraram e **usa a rede de
  verdade**. Com as fixtures de clima isso mandaria a posição inventada ao Open-Meteo. Por isso o passo 3 importa as
  fixtures de clima por um script Python, que não chama a rede. (As fixtures da Meta 1 não têm posição: sem chamada.)

## Passo a passo
1. **Subir o Postgres.** Salve fora do repositório um `porta.yml` com
   ```
   services:
     postgres:
       ports: !override
         - "5444:5432"
   ```
   e rode:
   ```
   docker compose -p treino-meta4 -f infra/docker-compose.yml -f /caminho/porta.yml up -d
   export DATABASE_URL="postgresql+psycopg://treino:treino@localhost:5444/treino"
   ```
   Esperado: `treino-meta4-postgres-1` `healthy`. (O override também pode vir pelo stdin, como no guia da Meta 3.)
2. **Instalar e migrar:**
   ```
   uv sync
   (cd services/api && uv run alembic upgrade head)
   ```
   Esperado: cinco linhas `Running upgrade`, até a `0005` (a `0004` põe `inicio_lat/lon` em `atividade`; a `0005` cria
   `clima_atividade`, [[modulos/banco]]).
3. **Fixtures.** As da Meta 1 (atleta 1, atividades 1 a 5, sem posição) e as de `tests/fixtures/clima/`:
   ```
   uv run python -m worker.importar_garmin tests/fixtures/garmin/exportacao_minima.zip --atleta "Atleta Fictício"
   ```
   Esperado: `inseridas=5 ... avisos=1` e `clima: chamadas=0`. Agora as de clima, sem rede. Salve como `importar_clima.py`
   (fora do repositório) e rode com `uv run python importar_clima.py`:
   ```python
   from app.db.session import SessionLocal
   from app.ingestao.importacao import importar

   with SessionLocal() as s:
       for caminho, atleta in [("tests/fixtures/clima/exportacao_clima.json", "Atleta Fictício"),
                               ("tests/fixtures/clima/fit", "Atleta dos FIT")]:
           r = importar(s, caminho, atleta)
           print(caminho, f"inseridas={r.inseridas} atualizadas={r.atualizadas} ignoradas={r.ignoradas} avisos={len(r.avisos)}")
   ```
   Esperado: `inseridas=5` (JSON; 5 avisos de "sem FIT correspondente", normais) e `inseridas=6` (FIT). Ficam 11
   atividades: 6 a 10 no atleta 1 e 11 a 16 no atleta 2. O que cada arquivo representa está em [[metricas/clima-oraculo]].
   Confira a posição gravada (arredondada, nunca a exata):
   ```
   docker exec treino-meta4-postgres-1 psql -U treino -d treino -c "select id, atleta_id, subtipo, inicio, inicio_lat, inicio_lon from atividade where id > 5 order by id"
   ```
   Com posição ficam só as atividades **7** (09:20, JSON), **12** (09:20), **13** (10:45, posição na `lap`) e **15**
   (13:40, longa), todas com `12.35 / -45.68`. As de esteira e o pedal virtual (9, 10, 16) vêm **sem posição**, mesmo
   com coordenada no arquivo. O ponto zero e o inválido (8, 11, 14) e a corrida sem coordenada (6) também.
4. **`--so-posicao`: reler a posição do passado (sem rede).** Para simular uma atividade antiga, apague a posição de duas:
   ```
   docker exec treino-meta4-postgres-1 psql -U treino -d treino -c "update atividade set inicio_lat=null, inicio_lon=null where id in (7,15)"
   uv run python -m worker.preencher_clima --so-posicao
   uv run python -m worker.preencher_clima --so-posicao --exportacao tests/fixtures/clima/exportacao_clima.json
   uv run python -m worker.preencher_clima --so-posicao --exportacao tests/fixtures/clima/exportacao_clima.json
   ```
   Esperado: `posicoes preenchidas=0` (sem arquivo para reler), depois `=1` (a 7, que está na exportação) e `=0`
   (idempotente: só preenche `NULL`). A 15 é de FIT que não está em `FIT_DIR`, então fica sem posição. Devolva a posição
   dela para seguir: `update atividade set inicio_lat=12.35, inicio_lon=-45.68 where id=15`. A linha final de cada rodada
   mostra a contagem por estado (`ok`, `indoor`, `sem_posicao`, `pendente`, `falha`). Os avisos "sem FIT correspondente"
   saem em stderr e são normais.
5. **Clima com a resposta gravada, sem rede.** O comando de linha de comando sempre usa o cliente real. Por isso este
   script usa o mesmo `rodar` do comando, mas com `ClienteOpenMeteo` trocado para um **transporte falso** que devolve a
   fixture, como fazem os testes. Salve como `clima_gravado.py` (fora do repositório; rode da raiz):
   ```python
   import sys
   from pathlib import Path

   import httpx
   from app.clima import ClienteOpenMeteo
   from app.db.session import SessionLocal
   from worker.preencher_clima import imprimir, rodar

   modo = sys.argv[1]  # ok | null | 503 | 400
   pasta = Path("tests/fixtures/clima")
   arquivo = {"ok": "open_meteo_archive_2026-05-10.json", "null": "open_meteo_archive_2026-05-10_com_null.json"}


   def resposta(request: httpx.Request) -> httpx.Response:
       if modo in arquivo:
           return httpx.Response(200, content=(pasta / arquivo[modo]).read_bytes(),
                                 headers={"content-type": "application/json"})
       return httpx.Response(int(modo), json={"error": True, "reason": "simulado"})


   cliente = ClienteOpenMeteo(transporte=httpx.MockTransport(resposta), dormir=lambda s: None)
   with SessionLocal() as session:
       imprimir(*rodar(session, cliente, refazer_falhas="--refazer-falhas" in sys.argv, pausa_s=0))
   ```
   O `modo` escolhe a resposta: `ok` (fixture normal), `null` (a fixture com `null` às 10h e 11h), `503` e `400` (erro
   HTTP). Nada de rede: o transporte não abre socket e a espera é falsa. Rode duas vezes o modo `ok`:
   ```
   uv run python clima_gravado.py ok
   uv run python clima_gravado.py ok
   ```
   Esperado: na primeira, `chamadas=4` e `ok=4 indoor=5 sem_posicao=7 pendente=0 falha=0`; na segunda, `chamadas=0`
   (`ok` com a mesma `entrada` não é consultada de novo). Os valores batem com o oráculo de [[metricas/clima-oraculo]]:
   ```
   docker exec treino-meta4-postgres-1 psql -U treino -d treino -c "select atividade_id, estado, temperatura_c, sensacao_c, umidade_pct, vento_kmh from clima_atividade order by 1"
   ```
   | Atividade | temperatura | sensação | umidade | vento |
   |---|---|---|---|---|
   | 7 e 12 (09:20, 50 min) | 27,02 | 30,4 | 70,2 | 9,84 |
   | 13 (10:45, 30 min) | 28,3 | 32,2 | 65 | 11,15 |
   | 15 (13:40, 2 h 30) | 29,8933 | 34,62 | 57,8 | 12,78 |

   (`chamadas` conta atividades consultadas, não chamadas HTTP: cada uma pode fazer até 4 chamadas com as repetições.)
6. **O `GET` novo da API.** Em outro terminal, com a mesma `DATABASE_URL`:
   ```
   FIT_DIR="$(mktemp -d)" uv run uvicorn app.main:app --app-dir services/api --port 8044
   curl -s localhost:8044/atletas/2/atividades/13
   ```
   Resposta (`200`): `{"atividade_id":13,"modalidade":"corrida",...,"clima":{"estado":"ok","temperatura_c":28.3,"sensacao_c":32.2,"umidade_pct":65.0,"vento_kmh":11.15}}`.
   Fora do `ok`, o `clima` só traz o `estado`. A posição nunca aparece (o `openapi.json` não tem `inicio_lat`).
   Veja a tabela do passo 7 para forçar cada estado. Erros: atleta inexistente dá `404` `{"detail":"atleta não encontrado"}`;
   atividade inexistente, ou de outro atleta, dá `404` `{"detail":"atividade não encontrada"}`.

## 7. Como forçar cada estado
Todos foram rodados. Os estados `indoor` e `sem_posicao` são **calculados** na leitura; `pendente` e `falha` vêm da tabela.

| Estado | Como forçar | Resultado |
|---|---|---|
| `ok` | passo 5, modo `ok` | `curl .../atletas/2/atividades/13` dá os quatro valores acima |
| `indoor` | nada a fazer: esteira (10) e pedal virtual (9) já estão no banco | `curl .../atletas/1/atividades/9` e `.../10` dão `{"estado":"indoor"}`; sem chamada, sem linha em `clima_atividade` |
| `sem_posicao` | atividade 8 (ponto `(0, 0)`) | `curl .../atletas/1/atividades/8` dá `{"estado":"sem_posicao"}`; sem chamada |
| `pendente` (dentro dos 7 dias) | `update atividade set inicio = now() - interval '2 days' where id=7`, depois `clima_gravado.py ok` | `chamadas=0`; a API dá `{"estado":"pendente"}`. Sem chamada, sem contar rodada. (A linha `ok` antiga deixa de valer: a `entrada` mudou.) |
| `pendente` (resposta com `null`) | `delete from clima_atividade where atividade_id in (12,13,15)`, depois `clima_gravado.py null` | 12 e 13 ficam `pendente`, `tentativas=1`, `erro` "resposta com null na janela"; a 15 (13h a 16h) segue `ok`: `null` fora da janela não atrapalha |
| `pendente` (rede ou 5xx) | `clima_gravado.py 503` | `pendente`, `erro` "HTTP 503", `tentativas` +1 por rodada |
| `falha` (HTTP 400) | `delete from clima_atividade where atividade_id=15`, depois `clima_gravado.py 400` | `falha` na hora, `erro` "HTTP 400", `tentativas=1`; a API dá `{"estado":"falha"}` |
| `falha` (5 rodadas) | repita `clima_gravado.py 503` até somar 5 | `tentativas=5`, `erro` "5 rodadas sem sucesso: HTTP 503" |

**As 5 rodadas:** depois do modo `null` (rodada 1), quatro rodadas `503` levam 12 e 13 por `tentativas=2, 3, 4` e, na
quinta, `falha` (`pendente=0 falha=2`). Rodado assim. **`--refazer-falhas`:** com `falha` e a `entrada` igual, o modo `ok`
sozinho dá `chamadas=0` (a falha fica). Com a flag, `uv run python clima_gravado.py ok --refazer-falhas` refaz todas as
`falha` (`chamadas=3`, `ok=3`) e zera `tentativas`. A API passa a dar o clima (28,3 para a 13). Se a `entrada` tivesse mudado,
a `falha` seria refeita sem a flag.

**Chamada real (opcional, uma só):** para ver a API de verdade, use a posição inventada do "Parque do Exemplo" e uma data
fixa, por exemplo `curl 'https://archive-api.open-meteo.com/v1/archive?latitude=12.35&longitude=-45.68&start_date=2026-05-10&end_date=2026-05-10&hourly=temperature_2m&timezone=GMT'`.
**Nunca** com posição do atleta. Não foi rodada neste guia; o que ela mostrou está em [[modulos/clima]].

## Encerrar e limpar
- `Ctrl+C` na API; apague a pasta de `FIT_DIR` e os scripts `importar_clima.py`, `clima_gravado.py` e `porta.yml`.
- Apagar o banco de vez (só o projeto `treino-meta4`): `docker compose -p treino-meta4 -f infra/docker-compose.yml down -v`.
- Confira com `docker ps`: só devem sobrar os containers que já existiam.

## Problemas comuns
- **`connection refused` no `curl`:** a API ainda está subindo; espere alguns segundos.
- **Porta ocupada no `up`:** escolha outra porta no override e ajuste a `DATABASE_URL`.
- **Tudo cai no banco errado:** faltou o `-p treino-meta4` ou o `export DATABASE_URL` neste terminal.
- **O `importar_garmin` tentou usar a rede com as fixtures de clima:** use o script do passo 3. O comando faz a busca no
  fim da importação; erro de clima ali vira aviso e nunca derruba a importação.
- **`chamadas=0` e nada mudou:** o estado já estava resolvido (`ok` com a mesma `entrada`, `falha` sem a flag, ou atividade
  dentro dos 7 dias).
- **Clima de atividade recente fica `pendente`:** a API do passado tem atraso de 5 dias; a janela é de 7 (ADR 0007, item 4).
  Não é erro.

## Testes
`uv run pytest -q` na raiz. O de ponta a ponta é `tests/test_e2e_meta4.py`. Os do clima: `services/api/tests/clima`, `services/worker/tests/test_preencher_clima.py`,
`services/api/tests/rotas/test_atividade_clima.py` e `tests/test_fixtures_clima.py`. Nenhum abre conexão externa.
Atribuição dos dados: Weather data by Open-Meteo.com (CC BY 4.0).
