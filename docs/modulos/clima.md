---
tipo: modulo
status: em-uso
dono: duda
atualizado: 2026-11-03
links: [[decisoes/0007-clima-da-atividade]], [[modulos/ingestao-garmin]], [[modulos/banco]], [[modulos/worker]], [[modulos/api]], [[modulos/api-client]], [[metricas/clima-oraculo]], [[produto/roadmap]]
---
# Módulo: clima

Weather data by Open-Meteo.com (licença CC BY 4.0, <https://open-meteo.com/>).

## Para que serve
Busca o clima da atividade (temperatura, sensação térmica, umidade e vento) na hora e no local do treino, para a Meta 4
([[decisoes/0007-clima-da-atividade]]). Tem o **cliente** (#112) e o **serviço que guarda e preenche o clima** (#113): tabela `clima_atividade`, estados e o
comando `worker.preencher_clima`. O clima na API (#114) é o `GET /atletas/{atleta_id}/atividades/{atividade_id}` (`buscarAtividade`), em [[modulos/api]].

## Entradas e saídas
- Código: `services/api/app/clima/cliente.py`. Interface `ClienteClima.buscar(lat, lon, inicio, duracao_s)`; a
  implementação real é `ClienteOpenMeteo(transporte=None, dormir=time.sleep)`. O transporte (`httpx.BaseTransport`) e a
  espera são injetáveis: os testes usam `httpx.MockTransport` e uma espera falsa.
- Entrada: posição de **início já arredondada** (2 casas, feita no leitor; o cliente só formata com 2 casas), `inicio`
  com fuso (convertido para UTC) e `duracao_s`.
- Saída: `ResultadoClima(estado, clima, erro, parar_rodada)`.
  - `ok`: `ClimaMedio` com `temperatura_c`, `sensacao_c`, `umidade_pct`, `vento_kmh`.
  - `pendente`: erro de rede, timeout, 5xx e 429 depois das tentativas, ou `null` em qualquer variável de qualquer hora
    da janela da atividade. Sem valores (nunca média parcial).
  - `falha`: HTTP 400 (e demais 4xx) ou resposta que não bate (não é JSON, variável faltando, `hourly` de tamanho
    diferente de `time`, valor que não é número, hora da atividade fora da resposta). Sem nova tentativa.
  - `parar_rodada` é `True` quando o 429 persistiu depois das tentativas (a rodada do comando deve parar, ADR item 6).
  - `erro` é um motivo curto, sem coordenada, URL nem corpo.

## A chamada
`GET https://archive-api.open-meteo.com/v1/archive` com **só**: `latitude`, `longitude`, `start_date`, `end_date`
(datas UTC do início e do fim), `hourly=temperature_2m,apparent_temperature,relative_humidity_2m,wind_speed_10m`,
`wind_speed_unit=kmh` e `timezone=GMT`. `User-Agent` fixo do produto (`treino-contexto/0.1 (...)`), sem identificador
do atleta, sem `atividade_id`, sem outro cabeçalho.

## Qual hora vale
Média **ponderada pelo tempo de sobreposição** de cada hora cheia UTC com `[inicio, inicio + duracao_s]`. Vento: média
das velocidades. Duração zero, ausente ou negativa: a hora do início. Uma atividade que termina em hora cheia não conta
a hora seguinte (peso zero). Atividade que cruza a meia-noite UTC pede duas datas (`start_date` e `end_date`). A conta
de referência, escrita à mão, está em [[metricas/clima-oraculo]].

## Falhas e tentativas
- Timeout de 10 s por chamada.
- Erro de rede, timeout, 5xx e 429: **valem 1 chamada mais até 3 repetições**, com espera de 1, 2 e 4 s. Até 4 chamadas
  no total. Com `Retry-After` (segundos), vale esse valor no lugar da espera padrão, no máximo 60 s; valor inválido ou
  data HTTP volta à espera padrão.
  (Decisão do Theo, 03/11, sobre o texto "3 tentativas" da ADR 0007, item 6: são 3 repetições, não 3 chamadas.)
- Log: só o código HTTP e o número de espera. Nunca coordenada, URL completa nem corpo. O `httpx` registra a URL completa
  em INFO; o módulo sobe o nível dos loggers `httpx` e `httpcore` para WARNING, e um teste confere o log (falha se isso
  for removido).

## O que a chamada real mostrou (uma chamada manual, 03/11/2026)
Uma única chamada à API gratuita com a posição inventada do "Parque do Exemplo" (12.35, -45.68), nunca com dado do
atleta. A resposta **não** foi gravada como fixture.
- **`apparent_temperature` vem preenchida** sem passar `models`: o padrão da API basta. Os campos e as unidades (°C, %, km/h)
  são os da fixture sintética; `timezone` volta `GMT` e `utc_offset_seconds` 0. A umidade vem inteira.
- **Custo:** cabeçalho `X-RateLimit-Cost: 1.0` para 1 dia e 4 variáveis (uma chamada = 1), com `X-RateLimit-Limit: 600`
  e `X-RateLimit-Window: 60` (600 por minuto, como na ADR). Dois dias no intervalo (atividade que cruza a meia-noite) não
  foi medido; a ADR manda tratar cada chamada como uma.
- A resposta devolve latitude e longitude do **ponto de grade** do modelo (alguns centésimos de grau de diferença do
  pedido), não as pedidas. O cliente não usa esses campos.
- Esse ponto inventado cai no mar (elevação 0), o que não muda nada para o cliente.
- Não houve erro, 429 nem `Retry-After` para ver; esses caminhos estão só nos testes com transporte falso.

## Tabela, estados e leitura (#113)
- Tabela `clima_atividade` (migração 0005; colunas em [[modulos/banco]]). `entrada` = SHA-256 de `inicio` (UTC, segundos),
  `duracao_s` (inteiro) e a posição (2 casas).
- `app.servicos.clima.clima_da_atividade(session, atividade_id)` devolve `ClimaDaAtividade(estado, temperatura_c,
  sensacao_c, umidade_pct, vento_kmh)`; `estado_clima(atividade, linha)` é a versão sem consulta, para listas. É o que a API
  (#114, `buscarAtividade`, [[modulos/api]]) usa. `indoor` (subtipo `esteira`, `piscina`, `virtual`) e `sem_posicao` são **calculados**, sem linha.
  Ao ar livre com posição: sem linha, ou linha de outra `entrada`, é `pendente`; senão vale o estado da linha. Valores só em `ok`.
- Posição e horário são tudo que vai ao Open-Meteo. Nenhum log ou relatório mostra coordenada.

## O comando `worker.preencher_clima`
Uso e opções em [[modulos/worker]]. Regras (ADR 0007, itens 6 a 8):
- **Entram** as atividades ao ar livre, com posição, com fim (`inicio + duração`) a mais de 7 dias e sem linha `ok` de mesma
  `entrada`. Dentro dos 7 dias: continuam `pendente`, sem chamada, sem linha e sem contar rodada.
- `ok` com `entrada` igual nunca é consultada de novo (rodar duas vezes não chama a API). `entrada` diferente refaz e
  zera `tentativas`.
- `pendente` (rede, timeout, 5xx, 429 ou `null` na janela) soma 1 em `tentativas` por rodada; ao chegar a 5 vira `falha`
  (`erro` guarda o motivo). `falha` do cliente (HTTP 400, resposta fora do esperado) vira `falha` na hora.
  `falha` só é refeita com `--refazer-falhas` (que zera `tentativas`), ou se a `entrada` mudou (nesse caso é refeita sem a flag).
  O 429 persistente, que para a rodada, também conta como uma tentativa da atividade em curso.
- Chamadas sequenciais, pausa de 0,25 s (injetável), teto de 500 por rodada (`--limite`), um `commit` por atividade.
  Com `parar_rodada` (429 persistente), a rodada para depois de gravar a atividade atual.
- **Posição do passado:** vem **primeiro da exportação** (`--exportacao`; o JSON vale mais que o FIT) e, se ela não tiver,
  do FIT guardado em `FIT_DIR` (`arquivo_bruto` no formato `<n>/<64 hex>.fit`). Só preenche `NULL`, nunca sobrescreve; indoor não recebe posição.
- **No fim de `importar` (linha de comando):** clima só das atividades que entraram ou mudaram (`RelatorioImportacao.ids_alterados`).
  `importar` e o endpoint de upload em si não usam a rede; erro de clima na linha de comando é aviso.

## Decisões do Theo (03/11)
Aprovadas na revisão da #113, sobre o que a [[decisoes/0007-clima-da-atividade]] deixou em aberto:
1. A guarda de socket dos testes do comando libera só loopback (`localhost`, `127.0.0.1`, `::1`) e `AF_UNIX`, para o Postgres local do CI. Qualquer outro destino falha.
2. Uma `falha` cuja `entrada` mudou é refeita sem a flag. `--refazer-falhas` zera `tentativas`.
3. `pendente` soma 1 por rodada e vira `falha` em 5. O 429 que para a rodada conta como tentativa.
4. A posição relida vem primeiro da exportação e depois do FIT em `FIT_DIR`.

## Arquivos principais
- `services/api/app/clima/cliente.py` e `services/api/app/clima/__init__.py`
- `services/api/app/servicos/clima.py` (tabela, estados, preenchimento) e `services/worker/worker/preencher_clima.py` (comando)
- `services/api/tests/clima/test_cliente_open_meteo.py` e `services/worker/tests/test_preencher_clima.py`
- Fixtures: `tests/fixtures/clima/` (resposta sintética, versão com `null`, `oraculo_clima.json`)

## Depende de
`httpx` (agora dependência de runtime da API, já estava no lock). O serviço usa o banco ([[modulos/banco]]) e o leitor ([[modulos/ingestao-garmin]]); o cliente em si não.

## Como testar
`uv run pytest services/api/tests/clima services/worker/tests/test_preencher_clima.py`. Nenhum teste abre conexão externa: um teste automático troca `socket.connect`,
`create_connection` e `getaddrinfo` por uma falha, e outro teste confere que a guarda pega o cliente com transporte
padrão. Nos testes do comando, a guarda deixa passar só loopback e `AF_UNIX` (decisão 1 acima). As esperas são falsas (nada dorme). Os valores batem com `oraculo_clima.json` (tolerância do oráculo).

## Pendências
- Cliente TypeScript: só tipos (`Atividade`, `ClimaAtividade`, `EstadoClima`, [[modulos/api-client]]); a função de busca nasce quando o app precisar.
- Atribuição "Weather data by Open-Meteo.com" na tela, se o clima aparecer um dia no app.
