---
tipo: modulo
status: em-uso
dono: duda
atualizado: 2026-11-03
links: [[decisoes/0007-clima-da-atividade]], [[modulos/ingestao-garmin]], [[modulos/banco]], [[modulos/worker]], [[metricas/clima-oraculo]], [[produto/roadmap]]
---
# Módulo: clima

Weather data by Open-Meteo.com (licença CC BY 4.0, <https://open-meteo.com/>).

## Para que serve
Busca o clima da atividade (temperatura, sensação térmica, umidade e vento) na hora e no local do treino, para a Meta 4
([[decisoes/0007-clima-da-atividade]]). Hoje existe só o **cliente**; o comando que preenche o banco e a tabela
`clima_atividade` vêm nas issues seguintes da Meta 4.

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
- Erro de rede, timeout, 5xx e 429: 1 chamada e até 3 repetições, com espera de 1, 2 e 4 s. Com `Retry-After` (segundos),
  vale esse valor no lugar da espera padrão, no máximo 60 s; valor inválido ou data HTTP volta à espera padrão.
  (Leitura do ADR: "3 tentativas com espera de 1, 2 e 4 s" = 3 esperas, então até 4 chamadas.)
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

## Arquivos principais
- `services/api/app/clima/cliente.py` e `services/api/app/clima/__init__.py`
- `services/api/tests/clima/test_cliente_open_meteo.py`
- Fixtures: `tests/fixtures/clima/` (resposta sintética, versão com `null`, `oraculo_clima.json`)

## Depende de
`httpx` (agora dependência de runtime da API, já estava no lock). Não toca o banco nem o leitor.

## Como testar
`uv run pytest services/api/tests/clima`. Nenhum teste abre conexão: um teste automático troca `socket.connect`,
`create_connection` e `getaddrinfo` por uma falha, e outro teste confere que a guarda pega o cliente com transporte
padrão. As esperas são falsas (nada dorme). Os valores batem com `oraculo_clima.json` (tolerância do oráculo).

## Pendências
- Tabela `clima_atividade`, comando `worker.preencher_clima` e clima na API: issues seguintes da Meta 4.
- Atribuição "Weather data by Open-Meteo.com" na tela, se o clima aparecer um dia no app.
