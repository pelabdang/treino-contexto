---
tipo: modulo
status: em-uso
dono: theo
atualizado: 2026-11-03
links: [[decisoes/0001-modelo-de-dados-minimo]], [[decisoes/0002-segmento-intensidade-e-versao]], [[decisoes/0003-fuso-da-atividade]], [[decisoes/0007-clima-da-atividade]], [[modulos/api]], [[modulos/infra]]
---
# Módulo: banco

## Para que serve
Guarda atleta, atividades importadas e segmentos (voltas, tiros, recuperações). Modelo mínimo da Meta 1.
Motivos da escolha em [[decisoes/0001-modelo-de-dados-minimo]].

## Entradas e saídas
- Tabelas: `assessoria`, `professor`, `atleta`, `vinculo_professor_atleta`, `atividade`, `segmento`, `clima_atividade`.
- `atividade` é única por `(atleta_id, fonte, fonte_id)`: reimportar não duplica.
- `segmento` tem `intensidade` (valor do FIT, com `CHECK`) e `versao_deteccao` (ex.: `tiros_1km@1`), ambos anuláveis. Ver [[decisoes/0002-segmento-intensidade-e-versao]].
- `atividade.fuso_min` (int, anulável, `CHECK` de -720 a 840): deslocamento do fuso em minutos; a data local da sessão é a de `inicio + fuso_min`, ou `America/Sao_Paulo` se for `NULL`. Ver [[decisoes/0003-fuso-da-atividade]].
- `atividade.inicio_lat` e `inicio_lon` (float, anuláveis): posição de **início** em graus, arredondada a 2 casas (~1 km) no leitor, sem trajeto. `CHECK` de faixa (-90..90 e -180..180) e `CHECK` de que as duas são nulas ou as duas preenchidas. `NULL` para atividade indoor (`esteira`, `piscina`, `virtual`), sem GPS ou antiga ainda não reimportada. Nunca sai pela API. Ver [[decisoes/0007-clima-da-atividade]].
- `clima_atividade` (migração 0005, [[decisoes/0007-clima-da-atividade]]): uma linha por atividade **consultada** (`atividade_id` único, `ON DELETE CASCADE`). `estado` (`ok`, `pendente`, `falha`, com `CHECK`), `temperatura_c`, `sensacao_c`, `umidade_pct`, `vento_kmh` (nulos fora de `ok`), `fonte` (`open-meteo-archive`), `entrada` (SHA-256 de `inicio` em UTC e segundos, `duracao_s` inteiro, `inicio_lat` e `inicio_lon` com 2 casas), `tentativas` (rodadas), `erro` (até 200 caracteres, sem coordenada) e `consultado_em`. **Não há linha** para `indoor` nem `sem_posicao`: esses estados são calculados na leitura (`app.servicos.clima.clima_da_atividade`).
- `arquivo_bruto` guarda o caminho do original (princípio "guardar o dado bruto").
- Domínios fixos (modalidade, tipo de treino, origem do tipo, tipo de segmento) são texto com `CHECK`.

## Arquivos principais
- `services/api/app/db/models.py`: modelos SQLAlchemy. Mudança só com aprovação do Theo.
- `services/api/alembic/versions/0001_modelo_de_dados_minimo.py`: migração inicial.
- `services/api/alembic/versions/0002_segmento_intensidade_e_versao.py`: colunas `intensidade` e `versao_deteccao`.
- `services/api/alembic/versions/0003_atividade_fuso_min.py`: coluna `fuso_min` e seu `CHECK`.
- `services/api/alembic/versions/0004_atividade_posicao_inicio.py`: colunas `inicio_lat`, `inicio_lon` e seus três `CHECK` (linhas antigas ficam `NULL`).
- `services/api/alembic/versions/0005_clima_atividade.py`: tabela `clima_atividade`, `CHECK` do estado, FK com cascata e unicidade de `atividade_id`. Testada com upgrade, downgrade e upgrade num Postgres isolado.
- `services/api/tests/test_migracoes.py`: garante que a migração gera o esquema dos modelos.

## Depende de
- Postgres 16 em [[modulos/infra]]. Usado pela [[modulos/api]].

## Como testar
`uv run pytest -q`. Para Postgres: defina `TEST_DATABASE_URL`. Migrar: `cd services/api && uv run alembic upgrade head`.

## Pendências
- Check-in, bem-estar, métricas derivadas e linha de base entram em migrações futuras, cada uma com ADR.
- Séries por segundo irão para Parquet, não para o banco.
