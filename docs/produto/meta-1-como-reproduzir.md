---
tipo: guia
status: em-uso
dono: nina
atualizado: 2026-10-31
links: [[produto/roadmap]], [[modulos/ingestao-garmin]], [[modulos/worker]], [[modulos/api]], [[modulos/grafico-tiros]], [[metricas/tiros-1km]], [[decisoes/0002-segmento-intensidade-e-versao]], [[decisoes/0003-fuso-da-atividade]], [[modulos/banco]]
---
# Meta 1: como reproduzir

Guia para gerar, num clone limpo, o gráfico e o JSON dos tiros de 1 km com as fixtures sintéticas.
Meta e critério de pronto em [[produto/roadmap]].

## Antes de começar
- `git`, `uv` (instala o Python 3.12 sozinho) e `curl`.
- Não precisa de Docker: o caminho abaixo usa um arquivo SQLite. O Postgres está na seção final.
- Todos os comandos rodam na **raiz** do repositório, exceto o `alembic`.

## Passo a passo (SQLite)
1. Clonar e instalar:
   ```
   git clone https://github.com/pelabdang/treino-contexto.git
   cd treino-contexto
   uv sync
   ```
2. Apontar para um banco novo. Use caminho absoluto; vale só para o terminal aberto:
   ```
   export DATABASE_URL="sqlite:///$PWD/meta1.db"
   ```
3. Criar as tabelas (o `alembic` roda dentro de `services/api`):
   ```
   (cd services/api && uv run alembic upgrade head)
   ```
   Esperado: três linhas `Running upgrade`, até a `0003`.
4. Importar a fixture ([[modulos/ingestao-garmin]]):
   ```
   uv run python -m worker.importar_garmin tests/fixtures/garmin/exportacao_minima.zip --atleta "Atleta Fictício"
   ```
   Esperado: `inseridas=5 atualizadas=0 ignoradas=0 avisos=1`. O aviso é da atividade `1000000005`
   (esteira sem FIT): ela entra sem voltas.
5. Gerar o gráfico e o CSV ([[modulos/grafico-tiros]]). O atleta criado é o `1`:
   ```
   uv run python -m worker.grafico_tiros_1km --atleta-id 1
   ```
   Esperado: `gravado: entregas/meta-1/tiros-1km-atleta-1.png` e `.csv`. A pasta `entregas/` é criada
   e fica fora do git.
6. Subir a API e chamar os dois endpoints ([[modulos/api]]):
   ```
   uv run uvicorn app.main:app --app-dir services/api --port 8000
   ```
   Em outro terminal, na mesma pasta:
   ```
   curl "http://localhost:8000/atletas/1/evolucao/tiros-1km"
   curl -o entregas/tiros-api.png "http://localhost:8000/atletas/1/evolucao/tiros-1km.png"
   curl "http://localhost:8000/atletas/99/evolucao/tiros-1km"
   ```
   Esperado: JSON com 2 sessões, PNG `image/png` de 1600 x 1000 px e, na última chamada,
   `404` com `{"detail":"atleta não encontrado"}`.
7. Conferir que reimportar não duplica (mesmo terminal e mesmo `DATABASE_URL` do passo 2):
   ```
   uv run python -m worker.importar_garmin tests/fixtures/garmin/exportacao_minima.zip --atleta "Atleta Fictício"
   ```
   Esperado: `inseridas=0 atualizadas=0 ignoradas=5`.

## Valores esperados
Calculados à mão a partir da tabela das fixtures; conta completa em [[metricas/tiros-1km]].

| Sessão (`activityId`) | Data | Tiros | Pace médio | FC média |
|---|---|---|---|---|
| 1000000001 (6 x 1 km) | 2025-03-04 | 6 | 250,8 s/km (`4:11`) | 170,3 bpm |
| 1000000002 (5 x 1 km) | 2025-03-11 | 5 | 237,0 s/km (`3:57`) | 171,8 bpm |

- O CSV tem as colunas `data, atividade_id, n_tiros, pace_medio_s_km, pace_medio_min_km, fc_media`
  e **duas linhas**, com esses valores. O `atividade_id` é o id do banco, que depende da ordem da
  importação; não compare esse número com o `activityId` do Garmin.
- Ficam **fora** da série: a rodagem leve de 8 km (`1000000003`), a natação (`1000000004`) e a esteira
  sem FIT (`1000000005`).
- O PNG tem dois painéis com o mesmo eixo X (`dd/mm/aa`): pace em cima, com o eixo invertido
  (mais rápido para cima), e FC embaixo. O exemplo está em [[modulos/grafico-tiros]].
- `periodo` do JSON é `null` sem filtro. Filtro: `?inicio=AAAA-MM-DD&fim=AAAA-MM-DD`, datas locais
  ([[decisoes/0003-fuso-da-atividade]]).

## Com Postgres
Mesmos passos, trocando o passo 2:
```
docker compose -f infra/docker-compose.yml up -d
cp .env.example .env
export DATABASE_URL="postgresql+psycopg://treino:treino@localhost:5432/treino"
```
O CI roda os testes contra o Postgres 16. O roteiro acima foi executado de ponta a ponta só em SQLite;
com o Postgres local e com a exportação real isso fica para a #19.

## Testes
`uv run pytest -q` na raiz.

## Notas da Meta 1
- Formato da exportação, parser e importação: [[modulos/ingestao-garmin]].
- Regra dos tiros e agregação por sessão: [[metricas/tiros-1km]].
- Série no banco e endpoint: [[modulos/api]]. Gráfico e CSV: [[modulos/grafico-tiros]] e [[modulos/worker]].
- Tabelas: [[modulos/banco]]. Decisões: [[decisoes/0001-modelo-de-dados-minimo]],
  [[decisoes/0002-segmento-intensidade-e-versao]] e [[decisoes/0003-fuso-da-atividade]].
