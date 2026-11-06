---
tipo: guia
status: em-uso
dono: nina
atualizado: 2026-11-06
links: [[produto/meta-4-como-rodar]], [[produto/meta-3-como-rodar]], [[produto/meta-2-como-rodar]], [[produto/meta-1-como-reproduzir]], [[decisoes/0008-deteccao-de-esforcos]], [[decisoes/0009-treino-de-transicao]], [[decisoes/0004-contrato-tela-evolucao]], [[metricas/esforcos]], [[metricas/esforcos-oraculo]], [[metricas/tiros-1km]], [[metricas/transicao]], [[modulos/banco]], [[modulos/worker]], [[modulos/api]], [[modulos/api-client]], [[modulos/ingestao-garmin]], [[modulos/mobile]], [[design/telas/treino]], [[diario/2026-11-06]]
---
# Meta 5: como rodar a detecção de esforços

Passo a passo da Meta 5 com as fixtures: Postgres próprio, migrações até a 0007, os esforços (`worker.detectar_esforcos`),
a série de tiros pelos esforços (`tiros_1km@5`, `worker.reclassificar`), o treino de transição (`worker.sugerir_transicao`
e as rotas), o multiesporte (`worker.reclassificar_multiesporte`) e o app (`npm run api-falsa`, `npm run verificar:web`).
**Só dado sintético.** A base é a mesma do [[produto/meta-4-como-rodar]]. As regras estão na
[[decisoes/0008-deteccao-de-esforcos]] e na [[decisoes/0009-treino-de-transicao]].

**Situação da verificação (#171, Nina, 06/11):** os passos 1 a 9 foram rodados de verdade, num clone de trabalho a partir
do `main` (`5b549f5`), com banco `treino-meta5` (Postgres na 5445, API na 8045), e os números abaixo são os que saíram.
O banco foi derrubado no fim. **Nada usou a rede.** **Rodado também:** `npm run api-falsa` (porta 8046, natação no id 106) e
`npm run verificar:web` (`OK: index.html traz o script do bundle e lang pt-BR`). **Não rodado aqui:** a tela no navegador
(web, iOS e Android; as capturas estão em `docs/design/telas/treino/`), `npm test`, e `uv run pytest -q` completo. A QA de ponta a
ponta é da #172 (Bia).

## Antes de começar
- `git`, `uv`, Docker (Compose 2.24 ou mais novo), `curl`, Node e `npm`. Comandos na **raiz** do repositório.
- **Não use o banco do seu dia a dia** (`treino-contexto-postgres-1`). Rode sempre com `-p treino-meta5`
  (volume `treino-meta5_pgdata`). Sem `-p`, o `docker compose` usa o volume `treino-contexto_pgdata`.
- Escolha uma **porta livre** (`docker ps` e `lsof -iTCP:<porta> -sTCP:LISTEN`). Abaixo, 5445 para o Postgres e 8045 para a API.
- `worker.importar_garmin` não usa a rede por padrão; este guia nunca passa `--com-clima`.
- Uma função `P` encurta os `psql`: `P() { docker exec treino-meta5-postgres-1 psql -U treino -d treino "$@"; }`.

## Passo a passo
1. **Subir o Postgres.** Salve fora do repositório um `porta.yml` com
   ```
   services:
     postgres:
       ports: !override
         - "5445:5432"
   ```
   e rode:
   ```
   docker compose -p treino-meta5 -f infra/docker-compose.yml -f /caminho/porta.yml up -d
   export DATABASE_URL="postgresql+psycopg://treino:treino@localhost:5445/treino"
   ```
   Esperado: `treino-meta5-postgres-1` `healthy`.
2. **Instalar e migrar:**
   ```
   uv sync
   (cd services/api && uv run alembic upgrade head && uv run alembic current)
   ```
   Esperado: sete linhas `Running upgrade` e `0007 (head)`. A `0006` cria `bloco_atividade` (esforços) e a `0007`,
   `rotulo_transicao` ([[modulos/banco]]).
3. **Fixtures.** A exportação mínima da Meta 1 e os sete FIT sintéticos dos esforços ([[metricas/esforcos-oraculo]]):
   ```
   uv run python -m worker.importar_garmin tests/fixtures/garmin/exportacao_minima.zip --atleta "Atleta Fictício"
   uv run python -m worker.importar_garmin tests/fixtures/garmin/esforcos --atleta "Atleta Fictício"
   ```
   Esperado: `inseridas=5 ... avisos=1` e `inseridas=7 ... avisos=0`, sempre com `clima: nao buscado (sem rede)`. Ficam 12
   atividades do atleta 1: 1 a 5 (Meta 1) e 6 a 12 (os FIT, `fonte_id` `fit-1-...` a `fit-7-...`). A importação já detecta os
   esforços (pela `classificar_atividades`, ver o passo 5).
4. **Esforços: `worker.detectar_esforcos` (sem rede).** Para ver o comando trabalhar, apague os blocos e detecte de novo:
   ```
   P -c "delete from bloco_atividade"
   uv run python -m worker.detectar_esforcos --atleta-id 1
   uv run python -m worker.detectar_esforcos --atleta-id 1
   ```
   Esperado na primeira: `atividades processadas: 11 (gravadas de novo: 10, sem mudança: 1, sem blocos: 1)`,
   `corrida: esforcos=38 treinos-chave=1`, `ciclismo: esforcos=5 treinos-chave=0` e
   `esforcos por faixa: ciclismo t4=5, corrida d1000=16, corrida d1500=3, corrida d400=18`; a linha
   `referencia da propria atividade (sem historico): 2 atividades` conta quem não tinha histórico. Na segunda,
   `gravadas de novo: 0, sem mudança: 11` (idempotente). A natação (atividade 3) fica fora: só corrida e ciclismo têm blocos.
   Confira os blocos de uma corrida de 400 m e de uma de 1500 m:
   ```
   P -c "select atividade_id, ordem, categoria, faixa, treino_chave from bloco_atividade where atividade_id in (6,7) order by 1,2"
   ```
   Esperado: atividade 6, aquecimento, dez `esforco` `d400` e desaquecimento (12 blocos); atividade 7, aquecimento, três `d1500`
   e desaquecimento (5 blocos). A atividade 8 (8 km contínuos) tem 1 esforço e `treino_chave = t`: é o treino-chave contínuo
   ([[metricas/esforcos]], item 6 da ADR 0008). A 11 é o pedal de blocos de 4 min (cinco `t4`). A 12 (pedal com lap cortado) **não** tem esforço neste banco: a referência de ciclismo vem do histórico (a 11,
   cerca de 26 km/h), e o bloco de 20 min a 24 km/h não passa do limiar. O oráculo da #161 usa 20 km/h de referência; importada
   sozinha, a 12 dá o esforço do oráculo (coberto por `tests/test_e2e_meta5.py`).
5. **Série de tiros pelos esforços: `tiros_1km@5` e `worker.reclassificar`.** A série passou a ser uma visão dos esforços
   (faixa `d1000`; 2 ou mais tiros; treino misto conta). Suba a API em outro terminal, com a mesma `DATABASE_URL`:
   ```
   FIT_DIR="$(mktemp -d)" uv run uvicorn app.main:app --app-dir services/api --port 8045
   ```
   Para simular um banco classificado antes da `@5`, volte a versão e consulte:
   ```
   P -c "update segmento set versao_deteccao='tiros_1km@4'"
   curl -s localhost:8045/atletas/1/evolucao/tiros-1km
   ```
   Esperado: `"versao_calculo": "tiros_1km@5"` e `"reclassificacao_pendente": true` (a API avisa que as voltas guardam outra versão).
   Reclassifique e consulte de novo:
   ```
   uv run python -m worker.reclassificar --atleta-id 1
   curl -s localhost:8045/atletas/1/evolucao/tiros-1km
   ```
   Esperado: `reclassificadas 9 corridas do atleta 1` e `"reclassificacao_pendente": false` com 3 sessões: 04/03/25 (6 tiros,
   melhor 4:08), 11/03/25 (5 tiros, 3:54) e 12/05/25 (5 tiros, 4:10). A última vem dos FIT de esforços e entra porque tem 2 ou
   mais tiros de 1 km (decisão do Angelo de 04/11). O contrato não mudou ([[decisoes/0004-contrato-tela-evolucao]]).
6. **Esforços na API.** O objeto `esforcos` vem na atividade ([[modulos/api]], "Atividade e clima"). A API só lê os blocos
   gravados, não detecta:
   ```
   curl -s localhost:8045/atletas/1/atividades/8
   curl -s localhost:8045/atletas/1/atividades/11
   ```
   Esperado na 8 (corrida, 05h00 local): `"duracao": "0:36:00"`, `"distancia": "8,00 km"`, `"pace_medio": "4:30"` e
   `esforcos` com `versao: esforcos@1`, `treino_chave: true`, `referencia_da_atividade: false` e um bloco `esforco` sem faixa
   (8 km passa de `d5000`). Na 11 (ciclismo): `"pace_medio": null`, `referencia_da_atividade: true` (a tela avisa: sem
   histórico), 12 blocos, o segundo um `esforco` `t4` ("4 min", `4:00`, `2,40 km`, `36,0 km/h`). Os textos vêm prontos
   (duração `m:ss`, distância "2,40 km" ou "733 m", natação em metros): o app só mostra. O exemplo de contrato está em
   `packages/api-client/exemplos/atividade-esforcos.json` ([[modulos/api-client]]).
7. **Treino de transição.** As fixtures não têm um brick. Insira quatro atividades **inventadas** (dois treinos ciclismo e
   depois corrida, com 2 e 3 minutos entre as partes):
   ```
   P -c "insert into atividade (atleta_id,fonte,fonte_id,modalidade,inicio,duracao_s,distancia_m,fc_media) values
   (1,'guia','brick-1a','ciclismo','2025-06-02 10:00:00+00',3600,30000,140),
   (1,'guia','brick-1b','corrida','2025-06-02 11:02:00+00',1800,6000,155),
   (1,'guia','brick-2a','ciclismo','2025-06-09 10:00:00+00',3600,31000,142),
   (1,'guia','brick-2b','corrida','2025-06-09 11:03:00+00',1800,6200,158)"
   uv run python -m worker.sugerir_transicao --atleta-id 1
   uv run python -m worker.sugerir_transicao --atleta-id 1
   ```
   Esperado (ids 13 a 16): na primeira, `atividades: 16 (elegiveis: 16)`, `sugeridas pela regra: 4` e
   `inseridas: 4, atualizadas (versao nova): 0, removidas: 0, sem mudanca: 0`; na segunda, `inseridas: 0 ... sem mudanca: 4`
   (idempotente). A importação também sugere sozinha (para o atleta inteiro); o comando serve para o histórico e para uma versão
   nova da regra ([[metricas/transicao]]). Liste, compare e corrija pela API:
   ```
   curl -s localhost:8045/atletas/1/treinos-de-transicao
   curl -s "localhost:8045/atletas/1/treinos-de-transicao/comparar?a=13&b=15"
   ```
   Esperado: dois grupos `ciclismo>corrida` (`grupo_id` 15, de 09/06, e 13, de 02/06; mais recente no alto), `incompleto: false`,
   intervalos estimados de `3:00` e `2:00`, tempos totais `1:33:00` e `1:32:00`, ritmos "31,0 km/h" e "4:50 /km" no 15, "30,0 km/h" e
   "5:00 /km" no 13. A comparação é B menos A, sem nota: `soma_duracoes_dif` `0:00`, `soma_intervalos_estimados_dif` `+1:00`,
   `tempo_total_dif` `+1:00`, `fc_dif_texto` `+2 bpm`. O `grupo_id` é derivado: não o guarde.
   | Ação | Comando | Resultado |
   |---|---|---|
   | Discordar da regra | `curl -s -X PUT -H 'content-type: application/json' -d '{"transicao": false}' localhost:8045/atletas/1/atividades/14/transicao` | `{"valor":false,"origem":"atleta"}`; `sugerir_transicao` de novo mostra `correcoes do atleta (nao tocadas): 1 (em 1 delas a regra sugere sim)`; o grupo 15 fica, e o pedal 13 sobra como grupo `ciclismo` com `incompleto: true` |
   | Desfazer a correção | `curl -s -X DELETE localhost:8045/atletas/1/atividades/14/transicao` | `{"valor":true,"origem":"sugerido"}` (o estado real, depois de rodar a regra) |
   | "Sim" numa atividade que a regra não sugeriu | `PUT` com `{"transicao": true}` na atividade 9 | `{"valor":true,"origem":"atleta"}`; vira grupo `corrida` com `incompleto: true` |
   | Comparar formas diferentes | `.../comparar?a=13&b=9` | `400` "só se comparam treinos da mesma sequência de modalidades: a é ciclismo>corrida e b é corrida" |
   | Grupo que não existe | `.../comparar?a=13&b=8` | `404` "treino de transição não encontrado" |
   Desfaça o "sim" da 9 com `DELETE` antes de seguir.
8. **Multiesporte (`worker.reclassificar_multiesporte --dry-run`).** As fixtures sintéticas de
   `tests/fixtures/multiesporte/` têm um pai, duas trocas e as partes:
   ```
   uv run python -m worker.importar_garmin tests/fixtures/multiesporte/exportacao_multiesporte.json --atleta "Atleta Multiesporte"
   P -c "select id, modalidade, subtipo from atividade where atleta_id=2 order by id"
   ```
   Esperado: `inseridas=7` (7 avisos de "sem FIT correspondente", normais) e, no atleta 2, `multiesporte_pai` e duas `troca` com
   `modalidade = outra` (ids 17, 19 e 21). O importador já grava o subtipo; o comando é para **banco importado antes**. Simule
   um assim e rode:
   ```
   P -c "update atividade set subtipo=null where id in (17,19,21)"
   uv run python -m worker.reclassificar_multiesporte --exportacao tests/fixtures/multiesporte/exportacao_multiesporte.json --atleta-id 2 --dry-run
   uv run python -m worker.reclassificar_multiesporte --exportacao tests/fixtures/multiesporte/exportacao_multiesporte.json --atleta-id 2
   uv run python -m worker.reclassificar_multiesporte --exportacao tests/fixtures/multiesporte/exportacao_multiesporte.json --atleta-id 2
   ```
   Esperado: o `--dry-run` imprime `NULL -> multiesporte_pai: 1`, `NULL -> troca: 2` e
   `atividades que mudariam (dry-run, nada gravado): 3` (e `P -t -c "select count(*) ... subtipo in ('troca','multiesporte_pai')"`
   continua `0`); a 2ª linha grava (`atividades que mudaram: 3`) e a 3ª não muda nada (`0`). Depois
   `uv run python -m worker.sugerir_transicao --atleta-id 2` dá `elegiveis: 4` e `sugeridas pela regra: 3` (com `inseridas: 0 ... sem mudanca: 3`, porque a importação já sugeriu): pai e troca (`outra`)
   ficam fora, e as partes viram um grupo `natacao>ciclismo>corrida`. Os valores de tipo reconhecidos e a fonte pública estão em
   [[modulos/ingestao-garmin]]. A carga (Meta 6) vai ignorar os dois subtipos.
9. **O app sem backend: `npm run api-falsa` e `npm run verificar:web`.** Em `apps/mobile`:
   ```
   npm ci
   node scripts/api-falsa.mjs 8046        # ou: npm run api-falsa (porta 8000)
   curl -s localhost:8046/atletas/1/atividades/106
   npm run verificar:web
   ```
   Esperado: a API falsa (dados sintéticos) diz `API falsa (dados sintéticos) em http://localhost:8046`; a atividade 106 é a natação
   (`"distancia": "1.800 m"`, `"pace_medio": null`, clima `indoor`). O `verificar:web` exporta a web e termina com
   `OK: index.html traz o script do bundle e lang pt-BR` (a causa e a correção do HTML sem bundle estão em [[modulos/mobile]]).
   Para ver as telas: `EXPO_PUBLIC_API_URL=http://localhost:8046 npx expo start --web --port 8081` e abra a evolução, selecione uma
   sessão e toque em "Ver treino" (ou abra `/treino/101`). Com a API do passo 5 no lugar da falsa, use
   `EXPO_PUBLIC_API_URL=http://localhost:8045` e adicione `CORS_ORIGENS=http://localhost:8081` ao subir a API. A spec da tela
   é [[design/telas/treino]].

## Encerrar e limpar
- `Ctrl+C` na API e na API falsa; apague a pasta de `FIT_DIR` e o `porta.yml`.
- Apagar o banco de vez (só o projeto `treino-meta5`): `docker compose -p treino-meta5 -f infra/docker-compose.yml down -v`.
- Confira com `docker ps`: só devem sobrar os containers que já existiam.

## Problemas comuns
- **Porta ocupada no `up`:** escolha outra porta no override e ajuste a `DATABASE_URL`.
- **Tudo cai no banco errado:** faltou o `-p treino-meta5` ou o `export DATABASE_URL` neste terminal.
- **`reclassificacao_pendente: true` na API:** as voltas guardam outra versão da detecção ou algum bloco foi gravado por outra
  versão dos esforços. Rode `worker.reclassificar --atleta-id N` (e, se for só dos blocos, `worker.detectar_esforcos`).
- **`esforcos` vem `null`:** a atividade não é corrida nem ciclismo. Vem com `blocos` vazio se ninguém detectou ainda.
- **`referencia_da_atividade: true`:** não havia histórico; a referência foi a mediana da própria atividade. Num treino em que o
  esforço domina o volume, ele pode não ser detectado ([[metricas/esforcos]], limitações).
- **`ref_origem` não é gravado:** a API recalcula na leitura. Depois de importar muito histórico antigo, rode
  `worker.detectar_esforcos` de novo.
- **Dois esforços vizinhos viraram dois (`d1000` e `d500`, não `d1500`):** é a decisão do Angelo de 04/11 quando a regra de
  5% não junta.
- **Parada de 15 s (corrida) ou 30 s (ciclismo) corta a sequência do treino-chave:** é a decisão do Angelo de 06/11.

## Testes
`uv run pytest -q` na raiz e `cd apps/mobile && npm test`. Os da Meta 5: `services/api/tests/metricas/` (esforços, treino-chave,
transição e a série `@5`), `services/api/tests/servicos/test_esforcos_banco.py`, `services/api/tests/rotas/test_atividade_esforcos.py`,
`test_atividade_distancia.py` e `test_treinos_de_transicao.py`, `services/worker/tests/test_detectar_esforcos.py`,
`test_sugerir_transicao.py` e `test_reclassificar_multiesporte.py`, e no app `TelaTreino.test.tsx`, `index.test.tsx` e `html.test.tsx`.
Nenhum abre conexão externa.
