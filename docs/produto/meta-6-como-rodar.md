---
tipo: guia
status: em-uso
dono: nina
atualizado: 2026-11-09
links: [[produto/meta-5-como-rodar]], [[produto/meta-4-como-rodar]], [[produto/roadmap]], [[decisoes/0010-carga-de-treino]], [[decisoes/0003-fuso-da-atividade]], [[metricas/carga-treino]], [[metricas/serie-carga]], [[metricas/carga-oraculo]], [[metricas/conferencia-carga]], [[modulos/grafico-carga]], [[modulos/banco]], [[modulos/worker]], [[modulos/api]], [[modulos/api-client]], [[modulos/ingestao-garmin]], [[diario/2026-11-07]], [[diario/2026-11-08]]
---
# Meta 6: como rodar a carga de treino

Passo a passo da Meta 6 com as fixtures: Postgres próprio, migrações até a 0010, a importação dos dados de saúde da exportação
Garmin (limiar, zonas, recordes e carga do Garmin), a carga de cada atividade (`worker.calcular_carga`), a API
(`GET /atletas/{id}/carga` e o objeto `carga` da atividade), o gráfico (`worker.grafico_carga`) e a conferência com o Garmin
(`worker.conferir_carga`). **Só dado sintético.** As regras estão na [[decisoes/0010-carga-de-treino]]; os números esperados, no
oráculo [[metricas/carga-oraculo]]. A carga é sempre **estimativa**, nunca medida.

**Situação da verificação (#145, Nina, 08/11):** os passos 1 a 9 foram rodados de verdade, num clone de trabalho a partir do
`main` (`1e0a6f9`, com a `carga@2`), com banco `treino-meta6` (Postgres na 5446, API na 8046). Os números abaixo são os que
saíram e batem com o oráculo. O banco e a API foram derrubados no fim. **Nada usou a rede.** **Não rodado aqui:** o app (a Meta 6
não tem tela de carga), `npm test` e `uv run pytest -q` completo. A QA de ponta a ponta é da #146 (Bia).

## Antes de começar
- `git`, `uv`, Docker (Compose 2.24 ou mais novo) e `curl`. Comandos na **raiz** do repositório.
- **Não use o banco do seu dia a dia** (`treino-contexto-postgres-1`). Rode sempre com `-p treino-meta6` (volume
  `treino-meta6_pgdata`). Sem `-p`, o `docker compose` usa o volume `treino-contexto_pgdata`.
- Escolha uma **porta livre** (`docker ps` e `lsof -iTCP:<porta> -sTCP:LISTEN`). Abaixo, 5446 para o Postgres e 8046 para a API.
- Nada deste guia usa a rede: o `importar_garmin` só busca clima com `--com-clima`, e o guia nunca o passa.
- Os arquivos de saída vão para uma pasta fora do git (`--saida`). O padrão, `entregas/meta-6/`, também está fora do git.

## Passo a passo
1. **Subir o Postgres.** Salve fora do repositório um `porta.yml` com
   ```
   services:
     postgres:
       ports: !override
         - "5446:5432"
   ```
   e rode:
   ```
   docker compose -p treino-meta6 -f infra/docker-compose.yml -f /caminho/porta.yml up -d
   export DATABASE_URL="postgresql+psycopg://treino:treino@localhost:5446/treino"
   ```
   Se preferir não exportar, ponha o prefixo em cada comando:
   `env DATABASE_URL="postgresql+psycopg://treino:treino@localhost:5446/treino" uv run python -m worker.calcular_carga --atleta-id 1`.
   Esperado: `treino-meta6-postgres-1` `healthy`.
2. **Instalar e migrar:**
   ```
   uv sync
   (cd services/api && uv run alembic upgrade head && uv run alembic current)
   ```
   Esperado: dez linhas `Running upgrade` e `0010 (head)`. A `0008` cria `limiar_atleta` e `zona_fc_atleta`, a `0009`,
   `recorde_pessoal` e `carga_garmin_dia`, e a `0010`, `carga_atividade` ([[modulos/banco]]).
3. **Importar a exportação sintética com saúde.** O zip de `tests/fixtures/garmin/carga/` é o do oráculo: 23 atividades de
   março e abril de 2025 e os arquivos de saúde ([[metricas/carga-oraculo]]):
   ```
   uv run python -m worker.importar_garmin tests/fixtures/garmin/carga/exportacao_carga.zip --atleta "Atleta Fictício"
   ```
   Esperado: `inseridas=23`, `avisos=5` (cinco atividades "sem FIT correspondente: entra sem voltas", normais: o pai e as trocas
   do triatlo e a corrida só no JSON), as linhas `saude limiar: inseridas=5`, `saude zonas: inseridas=3`,
   `saude recordes: inseridas=6` e `saude carga: inseridas=25`, o aviso `nenhum FIT com zonas de FC` (as fixtures não têm
   histórico de zonas) e, no fim, o resumo da carga (passo 4). **A importação já grava os dados de saúde e calcula a carga**:
   os passos 4 e 5 mostram os comandos soltos, que servem para reprocessar. Confira as tabelas:
   ```
   docker exec treino-meta6-postgres-1 psql -U treino -d treino -c "select count(*) from limiar_atleta"
   ```
   Esperado: 23 atividades, 5 limiares, 3 zonas, 6 recordes, 25 dias de carga do Garmin e 20 linhas em `carga_atividade`. Reimportar
   o mesmo zip dá `inseridas=0 ... ignoradas=23` e `ignoradas=` em todas as linhas de saúde: nada duplica.
4. **Carga por atividade: `worker.calcular_carga` (sem rede).**
   ```
   uv run python -m worker.calcular_carga --atleta-id 1
   ```
   Esperado: `carga carga@2 do atleta 1`, `atividades processadas: 20 (gravadas: 0, já atualizadas: 20)` (a importação já calculou),
   `calculadas: 13`, `sem carga: 7` (`sem_limiar_na_data: 2`, `sem_fc: 1`, `sem_pace: 1`, `cobertura_insuficiente: 1`,
   `modalidade_sem_carga: 2`) e `ignoradas (multiesporte e troca, sem linha): 3`. São 20 linhas porque o pai do triatlo e as duas
   trocas não têm carga ([[decisoes/0010-carga-de-treino]], item 5). Os números batem com os `TOTAIS` do oráculo.
   Para ver o recálculo, volte uma linha para a versão antiga e rode de novo:
   ```
   docker exec treino-meta6-postgres-1 psql -U treino -d treino -c "update carga_atividade set versao='carga@1' where atividade_id=3"
   uv run python -m worker.calcular_carga --atleta-id 1
   ```
   Esperado: `gravadas: 1, já atualizadas: 19` (só a linha desatualizada é regravada). Entre uma etapa e a outra a API mostra a
   atividade como `pendente` (passo 6).
5. **Suba a API** em outro terminal, com a mesma `DATABASE_URL`:
   ```
   FIT_DIR="$(mktemp -d)" uv run uvicorn app.main:app --app-dir services/api --port 8046
   ```
6. **A carga na API** ([[modulos/api]], "Carga"; contrato em [[modulos/api-client]]):
   ```
   curl -s localhost:8046/atletas/1/carga
   curl -s "localhost:8046/atletas/1/carga?inicio=2025-04-15&fim=2025-04-16"
   curl -s localhost:8046/atletas/1/atividades/3
   ```
   Esperado na primeira: `"versao": "serie_carga@1"`, `"versao_carga": "carga@2"`, `aviso: null`, **43 dias** (05/03/25 a
   16/04/25) e `totais` com `atividades_importadas: 23`, `calculadas: 13`, `sem_carga_total: 7`, `ignoradas_multiesporte: 3`,
   `pendentes: 0` e `por_motivo` com os seis motivos (`sem_dados_saude: 0`, `sem_limiar_na_data: 2`, `sem_fc: 1`, `sem_pace: 1`,
   `cobertura_insuficiente: 1`, `modalidade_sem_carga: 2`). O primeiro dia traz carga `37,2463`, CTL `0,8763`, ATL `4,9583`,
   TSB `-4,0820` e `aprendendo: true`; o último (dia 42 da série), CTL `6,0070`, ATL `5,8199`, TSB `0,1871` e
   `aprendendo: false`. Tudo igual ao `SERIE` do oráculo. **A API não arredonda**; a tela decide as casas. O recorte
   `inicio`/`fim` só filtra `dias` (CTL e ATL partem do primeiro dia com carga), e `periodo` repete o filtro. `inicio` depois de
   `fim` dá `422`, e atleta que não existe dá `404`:
   ```
   curl -s -o /dev/null -w "%{http_code}\n" "localhost:8046/atletas/1/carga?inicio=2025-04-10&fim=2025-04-01"   # 422
   curl -s -o /dev/null -w "%{http_code}\n" localhost:8046/atletas/99/carga                                    # 404
   ```
   Na atividade 3 (corrida de 05/03): `"carga": {"estado": "calculada", "carga": 37.2463..., "metodo": "rtss", "cobertura_pct": 100.0,
   "motivo": null, "versao": "carga@2"}`. Outras para comparar: a 4 (natação) é `sem_carga` com `motivo` `modalidade_sem_carga`; a 7
   (esteira sem FC), `sem_fc`; a 13 (o pai do triatlo) tem `carga: null` (sem linha); a 20 (corrida só no JSON), carga `31,2338`.
   Com a linha da atividade 3 em `carga@1` (passo 4), ela vem `pendente` (`carga`, `metodo` e `versao` nulos), a série perde esse dia
   (41 dias) e `totais.pendentes` vale 1; depois do `calcular_carga` volta ao normal. A API **nunca** devolve limiar, zonas, recordes
   nem a carga do Garmin.
7. **Gráfico: `worker.grafico_carga`** ([[modulos/grafico-carga]]):
   ```
   uv run python -m worker.grafico_carga --atleta-id 1 --saida /caminho/saida
   ```
   Esperado: `gravado:` do `carga-atleta-1.png` (PNG 1600 x 1200, estimativa no título, dias "ainda aprendendo" sombreados, triângulo
   nos dias com treino sem carga) e do `carga-atleta-1.csv` (43 linhas e o cabeçalho `dia,carga,ctl,atl,tsb,aprendendo,atividades,
   calculadas,sem_carga`; a primeira linha é `2025-03-05,37.246346,0.876344,4.958312,-4.081968,sim,1,1,0`, as casas do oráculo). Abra
   o PNG para ver. `--inicio` e `--fim` só recortam o desenho.
8. **Conferência com o Garmin: `worker.conferir_carga`** ([[metricas/conferencia-carga]]):
   ```
   uv run python -m worker.conferir_carga --atleta-id 1 --saida /caminho/saida
   ```
   Esperado: `conferência conferencia_carga@1: dias comparados 11 de 16 em comum (descartados por atividade sem carga: 5)` e três
   arquivos (`conferencia-carga-atleta-1.csv`, `...-resumo.csv`, `...-cobertura.csv`). No `-cobertura.csv`, a regra `adr` tem 43 dias
   nossos, 25 do Garmin, 16 em comum, 5 descartados e 11 comparados; a regra `todos_os_dias` compara os 16. **Atenção:** a carga do
   Garmin deste zip é uma série inventada de 25 dias, sem relação com a nossa; os Spearman que saem aqui **não querem dizer nada**.
   O teste `services/worker/tests/test_conferir_carga.py` usa uma série do Garmin com relação conhecida (Spearman 1, 43 dias, 5
   descartados, 38 comparados). A conferência é só descritiva: não há faixa de aprovação (ADR 0010, item 8). O terminal mostra só
   contagens.
9. **Atleta sem dados de saúde.** Duas formas:
   Atenção: a importação cria um **segundo atleta** ("Atleta Sem Saúde"). O `--atleta-id 1` continua sendo o primeiro
   atleta, o das etapas anteriores. O segundo tem outro id (num banco limpo, 2).
   ```
   uv run python -m worker.importar_garmin tests/fixtures/garmin/carga/exportacao_carga_sem_saude.zip --atleta "Atleta Sem Saúde"
   uv run python -m worker.apagar_saude --atleta "Atleta Fictício"
   uv run python -m worker.calcular_carga --atleta-id 1
   ```
   Esperado: a primeira importa as 23 atividades com `saude limiar: inseridas=0` (e zonas, recordes e carga também) e avisos
   `sem arquivo de limiar de lactato ...`. A segunda (LGPD) imprime `apagadas=5`, `apagadas=3`, `apagadas=6` e `apagadas=25`, e
   o atleta e as atividades ficam. Depois do `calcular_carga` o atleta 1 fica com `gravadas: 18`, `calculadas: 0`,
   `sem_dados_saude: 18` e `modalidade_sem_carga: 2`: **sem limiar não há carga, e o limiar nunca é estimado**. Na API,
   `/atletas/1/carga` volta com `"aviso": "sem_carga_calculada"` e `dias` vazio, e a conferência diz `dias comparados 0 de 0 em comum`.

## Encerrar e limpar
- `Ctrl+C` na API; apague a pasta de `FIT_DIR`, a pasta de saída e o `porta.yml`.
- Apagar o banco de vez (só o projeto `treino-meta6`): `docker compose -p treino-meta6 -f infra/docker-compose.yml down -v`.
- Confira com `docker ps`: só devem sobrar os containers que já existiam.

## Problemas comuns
- **Porta ocupada no `up`:** escolha outra porta no override e ajuste a `DATABASE_URL`.
- **Tudo cai no banco errado:** faltou o `-p treino-meta6` ou o `export DATABASE_URL` (ou o prefixo `env DATABASE_URL=...`) neste terminal.
- **`uv` avisa que `VIRTUAL_ENV` não bate com o ambiente do projeto:** é só um aviso (você tem outro ambiente ativo); rode
  `unset VIRTUAL_ENV` ou ignore.
- **`"aviso": "sem_carga_calculada"` e `dias` vazio:** nenhuma atividade tem carga. Veja `totais.por_motivo`: `sem_dados_saude` pede
  `worker.importar_saude`; rode depois `worker.calcular_carga`.
- **`estado: "pendente"` numa atividade:** não há linha de carga ou ela guarda outra versão. Rode `worker.calcular_carga`.
- **Esteira ou ciclismo sem GPS ficam `sem_pace`/`sem_fc`:** é a regra da ADR, não erro. O hrTSS usa a FC média da atividade quando
  nenhuma volta tem FC (`carga@2`, adendo de 08/11).
- **Dia com treino e carga 0 na série:** `sem_carga > 0` no dia (natação, `outra` ou falta de dado); não é descanso.
- **Limiar do dia errado:** vale o limiar vigente no **dia local** da atividade ([[decisoes/0003-fuso-da-atividade]]).

## Testes
`uv run pytest -q` na raiz. Os da Meta 6: `services/api/tests/metricas/test_carga.py`, `test_serie_carga.py` e
`test_conferencia_carga.py`, `services/api/tests/ingestao/test_saude_garmin.py` e `test_importar_saude.py`,
`services/api/tests/rotas/test_carga.py`, `services/worker/tests/test_calcular_carga.py`, `test_grafico_carga.py`,
`test_conferir_carga.py` e `test_importar_saude.py`, e `tests/test_fixtures_saude.py`. Nenhum abre conexão externa.
