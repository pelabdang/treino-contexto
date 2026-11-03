---
tipo: decisao
status: aceita
dono: theo
atualizado: 2026-11-03
links: [[modulos/ingestao-garmin]], [[modulos/api]], [[modulos/worker]], [[modulos/banco]], [[decisoes/0001-modelo-de-dados-minimo]], [[decisoes/0003-fuso-da-atividade]], [[decisoes/0004-contrato-tela-evolucao]], [[decisoes/0006-upload-de-fit]], [[produto/roadmap]], [[produto/plano-mvp-execucao]]
---
# ADR: 0007 Clima da atividade (Meta 4)

**Status: aceita (Theo, 03/11).** Só documentação: nenhum código muda aqui. As issues da Meta 4
(posição no leitor, cliente Open-Meteo, comando, API) seguem esta ADR a partir daqui.

## Contexto
Cada atividade ao ar livre deve ganhar temperatura, umidade, vento e sensação térmica na hora e no local do treino
(tabela `clima_atividade` do [[produto/plano-mvp-execucao]]). Isso exige guardar um dado novo e pessoal (onde o atleta
treina), mandar parte dele a um serviço de terceiro e mexer em leitor, banco, worker e API. Por isso é ADR.

Decisões do Angelo (03/11), registradas na issue #109: guardar só a posição de **início**, **arredondada a cerca de
1 km** (2 casas decimais), nunca o trajeto; ao Open-Meteo vão só a posição arredondada e o horário, sem identificador
do atleta, na API gratuita do desenvolvimento; o passado é preenchido relendo os arquivos locais, sem pedir nada ao atleta.

### O que o código do `main` mostra (conferido antes de escrever)
- **Nenhuma atividade guarda posição.** O modelo `Atividade` (`services/api/app/db/models.py`) não tem latitude nem
  longitude. Não existe tabela de clima nem código do Open-Meteo.
- **O leitor FIT não lê posição.** `ler_fit` (`services/api/app/ingestao/garmin/fit.py`) guarda só `file_id`, a primeira
  `session` e as `lap`; `FitLido` não tem posição. As fixtures sintéticas existentes conferem que `position_lat/long`
  são vazios (`tests/test_fixtures_garmin.py`, `tests/test_fixtures_fit_upload.py`).
- **O repositório não tem o nome das chaves de posição do JSON.** `startLatitude` e `startLongitude` são o nome esperado
  (formato da exportação da Garmin), mas nenhum código, fixture ou nota do `main` os usa ainda. A issue do leitor confirma
  o nome com uma fixture sintética. Fim do trajeto, caixa do trajeto e nome do lugar **não serão lidos**: são mais dado
  pessoal do que o clima precisa.
- **Quem tem posição não é só ao ar livre.** Tipos virtuais, como `virtual_ride`, podem trazer posição de um mundo
  virtual, que não é o lugar do atleta. `tipos._por_texto` só marca `esteira` para ciclismo se o texto tem `indoor`,
  então `virtual_ride` sai com `subtipo = NULL`. Sem tratar isso, o clima dessas atividades seria inventado.
  O código não depende de atividade indoor vir sem posição.
- **Indoor já tem base:** `subtipo` `esteira` (JSON `treadmill_running`; FIT `sub_sport = treadmill`; ciclismo indoor, que
  hoje também vira `esteira`) e `piscina` (`lap_swim`/`lap_swimming`). `aguas_abertas`, `pista` e `trilha` são ao ar livre.
- **O FIT do upload não traz horário local** (ADR 0003): para o clima basta o `inicio` em UTC.
- **Os arquivos para o passado existem:** FIT enviados em `FIT_DIR/<atleta_id>/<sha256>.fit`, com o caminho relativo em
  `atividade.arquivo_bruto` (ADR 0006), e a exportação em `dados-teste/`. FIT da exportação ficam como caminho com `!/`.
- **Campo novo na importação:** `importar` compara os campos da atividade e atualiza o que mudou (ADR 0006, item 2),
  então a posição entra nessa comparação como os demais campos.

### O que a documentação pública do Open-Meteo diz (consultada em 03/11/2026)
- **Historical Weather API** (`https://archive-api.open-meteo.com/v1/archive`): parâmetros `latitude`, `longitude`,
  `start_date` e `end_date` (`yyyy-mm-dd`). Modelos: ERA5 desde 1940, atraso de **5 dias**, ~25 km; ERA5-Land desde 1950,
  atraso de 5 dias, ~11 km; ECMWF IFS desde 2017, sem atraso, 9 km. Variáveis horárias: `temperature_2m`,
  `relative_humidity_2m`, `apparent_temperature`, `wind_speed_10m`, `wind_gusts_10m`, `wind_direction_10m`. A sensação
  térmica só existe no ERA5 via o modelo "seamless". Vento em km/h por padrão (`wind_speed_unit`: `kmh`, `ms`, `mph`, `kn`).
  `timezone` padrão GMT; `auto` ou nome tz também aceitos, mas mudanças de horário de verão dentro do intervalo são
  ignoradas. Fonte: <https://open-meteo.com/en/docs/historical-weather-api>.
- **Forecast API** (`/v1/forecast`): `past_days` de 0 a **92**; é previsão com os dias recentes. Erro de parâmetro:
  HTTP 400 com `{"error": true, "reason": "..."}`. Fonte: <https://open-meteo.com/en/docs>.
- **Historical Forecast API** (`https://historical-forecast-api.open-meteo.com/v1/forecast`): início em torno de 2022, vários
  modelos, sem atraso informado; a própria página avisa que **não serve para séries longas**, porque as versões dos
  modelos mudam. Fonte: <https://open-meteo.com/en/docs/historical-forecast-api>.
- **Limites da API gratuita:** menos de 600 chamadas por minuto, 5 000 por hora, 10 000 por dia (a página de preços
  também cita 300 000 por mês); **só uso não comercial**; atribuição CC BY 4.0; sem garantia de disponibilidade; podem
  bloquear IP ou aplicação que abusar. Fontes: <https://open-meteo.com/en/pricing> e <https://open-meteo.com/en/terms>.
- **Privacidade:** os logs do servidor ficam 90 dias e "podem conter coordenadas geográficas"; não são
  compartilhados com terceiros (<https://open-meteo.com/en/terms>).
- **Não encontrei na documentação** como o custo de uma chamada muda com o número de dias ou de variáveis; as páginas
  falam em "chamadas". Pior caso: tratar cada chamada como uma. A issue do cliente deve conferir cabeçalhos e erros reais.

## Decisão

### 1. Posição de início no banco: duas colunas na `atividade`
- `inicio_lat` e `inicio_lon`, `Float`, ambas anuláveis, em **graus decimais com 2 casas** (~1,1 km de latitude),
  `CHECK` de faixa (`-90..90` e `-180..180`) e `CHECK` de que as duas são nulas ou as duas preenchidas. Migração
  `0004`, só adiciona colunas nulas (as linhas antigas ficam `NULL`).
- **O arredondamento acontece no leitor**, antes de a coordenada sair da função que a lê: `round(valor, 2)`. A
  coordenada exata nunca chega a objeto de importação, banco, log nem teste. `AtividadeImportada` ganha `inicio_lat` e
  `inicio_lon` já arredondados.
- **FIT:** `session.start_position_lat/long`; se faltarem, `start_position_lat/long` da **primeira** `lap`. Não lê
  `record`, nem fim, nem trajeto. O FIT guarda semicírculos (inteiro de 32 bits): graus = `semicírculos * 180 / 2^31`
  (a issue do leitor confere o que o `fitdecode` devolve e o valor inválido `0x7FFFFFFF`, que vira "sem posição").
- **JSON:** `startLatitude` / `startLongitude`. Quando o JSON e o FIT casam (60 s, ADR 0006), vale a posição do JSON; se o
  JSON não tiver, a do FIT.
- **Valor descartado** (vira `NULL` nas duas): fora da faixa, não numérico ou **`(0, 0)`** depois do arredondamento
  (ponto "sem GPS" comum em dispositivos).
- **A posição não sai pela API.** O contrato devolve o clima (item 5), nunca `inicio_lat/lon`.
- **Atividade indoor não guarda posição** (item 2): a importação grava `NULL` mesmo que o arquivo traga coordenada.

### 2. O que é indoor e o que fazer sem posição
Estado calculado na leitura, sem linha na tabela de clima:
- **`indoor`:** `subtipo` em `{esteira, piscina, virtual}`. Novo subtipo **`virtual`** para `virtual_ride` no JSON e
  `sub_sport = virtual_activity` no FIT (mudança pequena em `tipos.py`; o ciclismo virtual hoje sai sem subtipo).
  `aguas_abertas`, `pista`, `trilha` e subtipo vazio são ao ar livre.
- **`sem_posicao`:** ao ar livre mas sem `inicio_lat/lon` (FIT sem GPS, JSON sem coordenada). Nunca se busca clima para ela.
- Atividade `outra` **com** posição (por exemplo multiesporte) pede clima como as demais.

### 3. Tabela `clima_atividade` (modelo de dados: aprovação do Theo, ADR 0001)
Uma linha por atividade **que foi consultada** (`atividade_id` único, `ON DELETE CASCADE`). Não há linha para
`indoor` nem `sem_posicao`.

| Coluna | Tipo | Observação |
|---|---|---|
| `id` | inteiro, chave | |
| `atividade_id` | FK única | `atividade.id`, cascata |
| `estado` | texto | `ok`, `pendente` ou `falha` (`CHECK`) |
| `temperatura_c` | float, nulo | °C |
| `sensacao_c` | float, nulo | °C (`apparent_temperature`) |
| `umidade_pct` | float, nulo | % (`relative_humidity_2m`) |
| `vento_kmh` | float, nulo | km/h (`wind_speed_10m`, unidade padrão) |
| `fonte` | texto, nulo | `open-meteo-archive`; vazio enquanto `pendente` sem resposta |
| `entrada` | texto (64) | SHA-256 de `inicio` (UTC, segundos), `duracao_s` (inteiro), `inicio_lat`, `inicio_lon` |
| `tentativas` | inteiro | quantas rodadas já tentaram |
| `erro` | texto (200), nulo | motivo curto, sem coordenada nem corpo da resposta |
| `consultado_em` | datetime com fuso | última tentativa |

Fora desta primeira versão (podem entrar depois, sem quebrar): rajada, direção do vento, precipitação, versão do modelo.
As colunas de valor são nulas fora de `ok`.

### 4. Qual API e que hora
- **Passado: Historical Weather API** (`archive-api.open-meteo.com/v1/archive`). Foi feita para isso, cobre desde 1940
  (o histórico pode ter vários anos, o que exclui a Historical Forecast como padrão) e é estável entre consultas.
  O modelo é o padrão da API; a issue do cliente confere na resposta real que `apparent_temperature` vem preenchida e,
  se precisar, passa o parâmetro `models` (a documentação cita o "seamless" para a sensação térmica). Resolução de 11 a
  25 km: o arredondamento a 1 km não perde nada que o modelo enxergue.
- **Atraso de 5 dias:** atividade cujo **fim** (`inicio + duracao`) ainda está dentro de **7 dias** (5 do atraso, mais 2
  de folga) não é consultada: fica `pendente` e entra na próxima rodada. **Não** usamos o Forecast com `past_days` nem
  o Historical Forecast para tapar o buraco, porque são outros modelos e misturariam fontes numa mesma coluna; fica
  como alternativa (abaixo). Se a resposta vier com `null` em qualquer hora da janela da atividade, a linha fica
  `pendente` (nunca `ok` com zero ou média parcial).
- **Chamada:** `GET .../v1/archive` com **só** `latitude`, `longitude` (já arredondadas), `start_date` e `end_date` (as
  datas UTC do início e do fim), `hourly=temperature_2m,apparent_temperature,relative_humidity_2m,wind_speed_10m`,
  `wind_speed_unit=kmh` e `timezone=GMT`. Em GMT os horários são UTC, sem horário de verão, e casam direto com
  `atividade.inicio`. Sem identificador do atleta, sem `atividade_id`, sem cabeçalho que identifique a pessoa (o
  `User-Agent` é o fixo do produto).
- **Qual hora vale:** a **média ponderada pelo tempo de sobreposição** de cada hora cheia com `[inicio, inicio +
  duracao_s]`. Uma atividade de 40 minutos que cruza duas horas usa as duas, cada uma com seu peso; uma de 3 h usa as 3
  ou 4 horas que toca. A média do vento é a das velocidades (não vetorial). Duração zero ou ausente: usa a hora do
  início. O oráculo da Meta 4 (Caio) reproduz essa conta a partir da resposta gravada.
- **Atribuição:** o dado é CC BY 4.0. A nota do módulo e, se o clima aparecer um dia na tela, a tela, citam
  "Weather data by Open-Meteo.com".

### 5. Contrato da API (resumo; os detalhes saem na issue da API, com cliente regerado)
Cada atividade na resposta ganha um objeto `clima`:
```json
{"estado": "ok", "temperatura_c": 24.3, "sensacao_c": 25.1, "umidade_pct": 61, "vento_kmh": 8.2}
{"estado": "indoor"}
{"estado": "sem_posicao"}
{"estado": "pendente"}
{"estado": "falha"}
```
`estado` é um de `ok`, `indoor`, `sem_posicao`, `pendente`, `falha`. Os campos de valor só aparecem em `ok`. Nunca
`inicio_lat/lon`. É campo novo e opcional no schema; nada que o app usa hoje muda.

### 6. Falhas, novas tentativas e limites
- **Dentro de uma consulta:** timeout de 10 s; até **3 tentativas** com espera crescente (1 s, 2 s, 4 s) para erro de
  rede, timeout, HTTP 5xx e 429. Com `Retry-After`, respeita o valor (até 60 s). Depois disso o estado fica `pendente`
  e o motivo vai para a coluna `erro`.
- **HTTP 400 ou resposta que não bate com o esperado** (variável faltando, tamanho do `hourly` diferente de `time`):
  estado `falha`, **sem nova tentativa** automática (é bug ou parâmetro, não instabilidade). O comando só refaz `falha`
  com `--refazer-falhas`.
- **Entre rodadas:** `pendente` é tentada de novo a cada rodada; depois de **5 rodadas** seguidas sem sucesso (coluna
  `tentativas`), vira `falha`. As rodadas "ainda dentro dos 7 dias" não contam como tentativa.
- **Limites de chamada:** uma chamada por atividade, **sequencial**, com pausa de 0,25 s entre elas (no máximo ~240 por
  minuto, abaixo dos 600 do limite). Teto de **500 atividades por rodada** (`--limite`, padrão 500), abaixo dos 5 000 por
  hora e dos 10 000 por dia mesmo no pior caso de custo por chamada. Em 429 depois das tentativas, **a rodada para**.
  O passado inteiro se preenche em algumas rodadas.
- **Os testes nunca chamam a rede.** O cliente recebe um transporte injetável; os testes usam respostas gravadas em
  `tests/fixtures/` (sintéticas, com lugar inventado) e um teste falha se algo abrir conexão.
- **Registro (log):** nunca imprime coordenada, URL completa nem corpo da resposta; só `atividade_id`, estado e contagens.

### 7. Idempotência e quando refazer
- A unicidade de `atividade_id` e a coluna `entrada` tornam a rodada idempotente: uma atividade `ok` com `entrada` igual à
  de hoje **não é consultada de novo**. Se `inicio`, `duracao_s` ou a posição mudam (um upload casou e atualizou, ou a
  importação corrigiu), a `entrada` muda e a linha é refeita na próxima rodada.
- Conjunto a consultar: atividades **ao ar livre, com posição, sem linha `ok` válida**, fim a mais de 7 dias.
  Um `commit` por atividade, então parar no meio não perde o que já foi feito.
- **Dois jeitos de rodar o mesmo código:** (a) no fim de `importar` e de `importar_fit`, só para as atividades que acabaram
  de entrar ou mudar (erro de clima **nunca** derruba a importação); (b) o comando abaixo.
- **O upload não espera a rede.** O `POST /atletas/{id}/atividades/fit` grava, responde e deixa o clima `pendente` para a
  próxima rodada; o endpoint não chama o Open-Meteo na requisição. Então (a) vale só para o `importar` de linha de comando.

### 8. Passado: um comando só
`uv run python -m worker.preencher_clima [--atleta-id N] [--exportacao CAMINHO] [--limite N] [--refazer-falhas]
[--so-posicao]`:
1. **Posição:** para cada atividade ao ar livre sem posição, relê o arquivo local: o FIT em `FIT_DIR` (quando
   `arquivo_bruto` tem o formato `<n>/<64 hex>.fit`) e, com `--exportacao`, a exportação (JSON e FIT dela). Só preenche
   onde está `NULL`: nunca sobrescreve. Reimportar a exportação normal (`importar`) também grava a posição, porque ela
   entra na comparação de campos. O comando não pede nada ao atleta.
2. **Clima:** o item 7.
Imprime quantas posições preencheu e quantas atividades ficaram em cada estado. Rodar de novo não repete nada.
`--so-posicao` não chama a rede.

### Exemplo sintético
Uma corrida fictícia no "Parque do Exemplo" (lugar inventado), `inicio` 2026-05-10 09:20 UTC, 50 minutos:
```
Posição no arquivo (nunca guardada exata) -> leitor guarda inicio_lat = 12.35, inicio_lon = -45.68
Pedido:  latitude=12.35  longitude=-45.68  start_date=2026-05-10  end_date=2026-05-10
         hourly=temperature_2m,apparent_temperature,relative_humidity_2m,wind_speed_10m  timezone=GMT
Horas:   09:20 a 10:10 toca a hora de 09h (40 min) e a de 10h (10 min)
Clima:   0,8 * valor(09h) + 0,2 * valor(10h)
Rodar de novo: entrada igual -> nenhuma chamada
Esteira fictícia com coordenada no arquivo: subtipo esteira -> estado "indoor", posição não gravada
```

## Alternativas consideradas
- **Forecast API com `past_days` (até 92 dias):** só cobre cerca de 3 meses para trás, então não preenche a exportação
  inteira, e mistura modelo de previsão com reanálise. Fica como opção só para fechar o atraso de 5 dias, se o Angelo
  quiser clima da mesma semana (decisão futura).
- **Historical Forecast API:** boa para os últimos anos, mas a própria documentação a desaconselha para séries longas
  (versões de modelo mudam), e só começa em torno de 2022.
- **Fixar o `models` do archive agora:** adiado para a issue do cliente, que vê a resposta real; esta tarefa não chamou
  a rede e não trava um nome que não pude testar.
- **Guardar a posição exata e arredondar ao enviar:** descartado pelo Angelo (só 1 km é guardado).
- **Guardar o trajeto, o fim ou o nome do lugar:** descartado; mais dado pessoal sem ganho para o clima.
- **Linha em `clima_atividade` também para indoor e sem posição:** gera estado duplicado, que fica errado quando o subtipo
  ou a posição mudam. Calcular na leitura é sempre coerente.
- **Colunas de clima direto na `atividade`:** mistura dado de terceiro, com tentativas e erro, com o dado do atleta; e o
  plano MVP já prevê a tabela.
- **Chamar o Open-Meteo dentro do endpoint de upload:** deixa a requisição lenta e dependente de terceiro.
- **Média simples das horas ou só a hora do início:** o início sozinho erra em treino longo; a ponderada é a conta mais
  direta de explicar.

## Consequências
- **Mudança de modelo:** 2 colunas em `atividade` e 1 tabela nova (`clima_atividade`), migração `0004`; precisa da
  aprovação do Theo.
- **Dado pessoal novo:** a posição de início, arredondada, passa a existir no banco local. O repositório é público: testes e
  fixtures só com posição fictícia; nenhuma coordenada real em issue, PR, nota ou log. `dados-upload/` e `dados-teste/`
  seguem fora do git.
- **Terceiro:** o Open-Meteo recebe posição arredondada e horário, e guarda coordenadas em log por 90 dias. O endereço de
  IP da máquina chega a ele (inevitável em qualquer chamada); entra no texto de consentimento quando houver login e deploy.
- **Uso não comercial:** a API gratuita vale para o desenvolvimento e o piloto sem cobrança. Para produto pago o plano
  comercial é necessário (em aberto no roadmap).
- **Subtipo `virtual`** novo no vocabulário (JSON e FIT); `piscina` e `esteira` não mudam. Atividades virtuais já
  gravadas ganham o subtipo na reimportação.
- **Importação:** a posição vira campo comparado (reimportar uma exportação antiga marca as atividades como `atualizada`
  uma vez, depois volta a `ignorada`).
- **Clima recente fica `pendente` por cerca de uma semana:** a API mostra isso como "pendente", não como erro.
- Ordem das issues: ADR (esta); posição no leitor com migração, e fixtures com posição fictícia com o oráculo (em
  paralelo); cliente Open-Meteo com resposta gravada; comando e chamada no fim da importação; clima na API e cliente
  regerado; documentação; QA; resultado.

## Pendências e perguntas
- **Theo:** aprovou o modelo (tabela e colunas, subtipo `virtual`, janela de 7 dias, 5 rodadas, teto de 500) em 03/11.
- **Angelo (só se discordar, já alinhado):** (1) ciclismo virtual é indoor, sem clima; (2) o clima da semana corrente fica
  pendente em vez de usar previsão.
- **A confirmar na implementação:** os nomes das chaves de posição do JSON; que o `fitdecode` devolve semicírculos; o `models` do archive para ter sensação
  térmica; o custo de uma chamada nos limites.

## Data e quem decidiu
2026-11-03. Posição de início arredondada a ~1 km, sem trajeto; envio ao Open-Meteo só de posição arredondada e horário,
na API gratuita; passado preenchido relendo os arquivos locais: Angelo. Tabela, estados, hora ponderada, falhas, limites,
idempotência, subtipo `virtual` e comando: proposta da Duda, aprovada pelo Theo em 03/11.
