---
tipo: guia
status: em-uso
dono: nina
atualizado: 2026-11-09
links: [[produto/meta-6-como-rodar]], [[produto/meta-5-como-rodar]], [[produto/roadmap]], [[decisoes/0011-linha-de-base-e-semana-padrao]], [[decisoes/0004-contrato-tela-evolucao]], [[decisoes/0003-fuso-da-atividade]], [[metricas/tipo-treino]], [[metricas/linha-base]], [[metricas/tipo-linha-base-oraculo]], [[design/telas/semana-padrao]], [[modulos/banco]], [[modulos/api]], [[modulos/api-client]], [[modulos/mobile]], [[modulos/worker]], [[diario/2026-11-09]]
---
# Meta 7: como rodar a semana-padrão, o tipo de treino e a linha de base

Passo a passo da Meta 7 com as fixtures: Postgres próprio, migrações até a 0011, as 81 atividades sintéticas de 12 semanas,
a semana-padrão gravada pela API e pela tela, o tipo de cada treino (origem e divergência), a `linha_base` no
`GET` da atividade e o `worker.reclassificar`. **Só dado sintético, sem rede.** As regras estão na
[[decisoes/0011-linha-de-base-e-semana-padrao]] (com o adendo 2, `linha_base@2`); os números esperados, no oráculo
[[metricas/tipo-linha-base-oraculo]]. A linha de base **compara com o histórico do atleta; não diz se o treino foi bom ou ruim.**

**Situação da verificação (#270, Nina, 09/11):** os passos 1 a 9 foram rodados de verdade num clone de trabalho a partir do `main`
(`d4ec053`, com a `linha_base@2`), com banco `treino-meta7` (Postgres na 5447, API na 8047, app web na 8082). Os números abaixo
são os que saíram. Os 81 tipos do banco, depois do passo 6, ficaram **iguais ao `TIPO_ESPERADO` do oráculo** (0 diferenças). O banco, a API e
o app foram derrubados no fim. **Nada usou a rede.** **Não rodado aqui:** o app em celular (só a web); rodei só os testes da meta (passo 10). A Bia (#271) seguiu o guia do zero sem achar bug e rodou também
`uv run pytest -q` completo (1434 passed, 1 skipped) e `npm test` (13 suítes, 154 testes).

## Antes de começar
- `git`, `uv`, Docker (Compose 2.24 ou mais novo), `curl`, `python3` e, para a tela, `node` com `npm`. Comandos na **raiz** do repositório.
- **Não use o banco do seu dia a dia** (`treino-contexto-postgres-1`). Rode sempre com `-p treino-meta7` (volume `treino-meta7_pgdata`).
- Escolha **portas livres** (`docker ps` e `lsof -iTCP:<porta> -sTCP:LISTEN`). Abaixo: 5447 (Postgres), 8047 (API) e 8082 (app web).
  A API só libera CORS para as origens de `CORS_ORIGENS` (padrão `http://localhost:8081`). Se a 8081 estiver livre, use-a no app e
  ignore o `CORS_ORIGENS` do passo 4.
- Uma pasta de trabalho fora do git, para o `porta.yml` e os JSON do passo 6 (abaixo, `/caminho/saida`).

## Passo a passo
1. **Subir o Postgres.** Salve `/caminho/saida/porta.yml` com
   ```
   services:
     postgres:
       ports: !override
         - "5447:5432"
   ```
   e rode:
   ```
   docker compose -p treino-meta7 -f infra/docker-compose.yml -f /caminho/saida/porta.yml up -d
   export DATABASE_URL="postgresql+psycopg://treino:treino@localhost:5447/treino"
   ```
   Esperado: `treino-meta7-postgres-1` `healthy`. Sem o `export`, ponha `env DATABASE_URL=...` antes de cada comando.
2. **Instalar e migrar:**
   ```
   uv sync
   (cd services/api && uv run alembic upgrade head && uv run alembic current)
   ```
   Esperado: onze linhas `Running upgrade` e `0011 (head)`. A `0011` cria `semana_padrao` e `semana_padrao_item` e põe
   `tipo_versao` e `tipo_divergencia` em `atividade` ([[modulos/banco]]).
3. **Carregar as 81 atividades sintéticas** de `tests/fixtures/meta7/atividades.json` (04/01 a 28/03/2026; o oráculo é o
   [[metricas/tipo-linha-base-oraculo]]). As fixtures resumem os blocos em `estrutura`; este trecho os transforma em blocos de
   verdade, grava a carga e o rótulo de transição, e dá o tipo pela **regra de reserva** (`aplicar_tipos`), como numa
   importação, **ainda sem semana-padrão**. Salve como `/caminho/saida/carregar.py` (o bloco abaixo está sem recuo; copie como está):
```python
import json
from datetime import UTC, datetime
from pathlib import Path

from app.db.models import Atividade, Atleta, BlocoAtividade, CargaAtividade, RotuloTransicao
from app.db.session import SessionLocal
from app.metricas import carga as cg
from app.metricas import esforcos as ef
from app.servicos.tipo_treino import aplicar_tipos

dados = json.loads(Path("tests/fixtures/meta7/atividades.json").read_text(encoding="utf-8"))["atividades"]


def blocos(a, estrutura, tiros):
    def b(ordem, cat, dur, dist, fc=None, faixa=None):
        a.blocos.append(BlocoAtividade(
            ordem=ordem, categoria=cat, volta_inicial=ordem, volta_final=ordem, inicio_offset_s=0.0, duracao_s=dur,
            distancia_m=dist, fc_media=fc, pace_s_km=dur / dist * 1000, faixa=faixa, versao_deteccao=ef.VERSAO))

    if estrutura == "sem_esforco":
        b(0, "leve", a.duracao_s, a.distancia_m)
    elif estrutura == "esforco":
        b(0, "aquecimento", 600, 1500)
        b(1, "esforco", 300, 1000, None, "d1500")
        b(2, "desaquecimento", 600, 1500)
    elif estrutura == "tiros":
        b(0, "aquecimento", 600, 1500)
        ordem = 1
        for _ in range(tiros["n"]):
            b(ordem, "esforco", tiros["melhor_pace_s_km"], 1000, tiros["fc_melhor_tiro"], "d1000")
            b(ordem + 1, "recuperacao", 200, 500)
            ordem += 2
        b(ordem, "desaquecimento", 600, 1500)


with SessionLocal() as s:
    atleta = Atleta(nome="Atleta Fictício")
    s.add(atleta)
    s.flush()
    for f in dados:
        a = Atividade(
            atleta_id=atleta.id, fonte="fixture", fonte_id=f["id"], modalidade=f["modalidade"], subtipo=f["subtipo"],
            inicio=datetime.fromisoformat(f["inicio"]), fuso_min=f["fuso_min"], duracao_s=f["duracao_s"],
            distancia_m=f["distancia_m"], fc_media=f["fc_media"], tipo_treino=f["tipo_treino"],
            tipo_origem=f["tipo_origem"], tipo_confirmado=f["tipo_confirmado"])
        s.add(a)
        blocos(a, f["estrutura"], f["tiros"])
        if f["carga"] is not None:
            a.carga = CargaAtividade(
                estado="calculada", carga=f["carga"], metodo="hrtss", cobertura_pct=100.0, granularidade="atividade",
                entrada="x" * 64, versao=cg.VERSAO, calculado_em=datetime(2026, 4, 1, tzinfo=UTC))
        if f["transicao"]:
            a.rotulo_transicao = RotuloTransicao(
                transicao=True, origem="atleta", definido_em=datetime(2026, 4, 1, tzinfo=UTC))
    s.flush()
    aplicar_tipos(s, atleta.id)  # a regra de reserva, como numa importação
    s.commit()
    print(f"atleta {atleta.id}: {len(dados)} atividades")
```
   Rode (na raiz): `uv run python - < /caminho/saida/carregar.py`. Esperado: `atleta 1: 81 atividades`. Confira:
   ```
   docker exec treino-meta7-postgres-1 psql -U treino -d treino -c "select coalesce(tipo_origem,'(sem)') o, count(*) from atividade group by 1 order by 1"
   ```
   Esperado: `(sem)` 40, `professor` 1, `sugestao` 39 e `trainingpeaks` 1. (O `professor` e o `trainingpeaks` são tipos confirmados das
   fixtures, caso E13 do oráculo; o resto é só a regra de reserva.)
4. **Subir a API** em outro terminal, com a mesma `DATABASE_URL`:
   ```
   CORS_ORIGENS=http://localhost:8082 FIT_DIR="$(mktemp -d)" uv run uvicorn app.main:app --app-dir services/api --port 8047
   ```
5. **Antes da semana-padrão: só a reserva.** Sem plano, `GET /atletas/1/semana-padrao` volta `"vigente": null` e `"vigencias": []`.
   Veja duas atividades (13/03, a de id 68, e 17/03, a de id 71):
   ```
   curl -s localhost:8047/atletas/1/semana-padrao
   curl -s localhost:8047/atletas/1/atividades/68
   curl -s localhost:8047/atletas/1/atividades/71
   ```
   Esperado: ambas com `tipo_origem: "sugestao"` (a 68 é `leve`, a 71 é `intervalado`, pelos 6 tiros) e `linha_base` com `versao: "linha_base@2"`,
   `estado: "ok"`, `janela_semanas: 12` e `minimo_treinos: 8`. Na 68 o pace médio sai `fora` com 12 treinos e a FC média `fora` com 9;
   na 71 o melhor pace sai `fora` com 9 treinos. **Os números ainda não são os do oráculo**: falta o plano.
6. **Gravar a semana-padrão pela API** ([[modulos/api]], "Semana-padrão"; [[decisoes/0011-linha-de-base-e-semana-padrao]], itens 1, 8 e 9).
   O `semana_padrao.json` das fixtures tem as duas vigências do oráculo (A desde 05/01, B desde 02/03). Separe cada uma em um corpo de `PUT`:
   ```
   python3 - <<'E'
   import json
   for i, v in enumerate(json.load(open("tests/fixtures/meta7/semana_padrao.json"))["vigencias"]):
       json.dump(v, open(f"/caminho/saida/vigencia{i}.json", "w"))
   E
   curl -s -X PUT -H 'content-type: application/json' --data @/caminho/saida/vigencia0.json localhost:8047/atletas/1/semana-padrao
   curl -s -X PUT -H 'content-type: application/json' --data @/caminho/saida/vigencia1.json localhost:8047/atletas/1/semana-padrao
   ```
   Esperado: o primeiro `PUT` devolve `vigente_desde: "2026-01-05"`, `definido_por: "atleta"`, sete `itens` e `atividades_reaplicadas: 46`;
   o segundo, `vigente_desde: "2026-03-02"`, `definido_por: "professor"` e `atividades_reaplicadas: 8` (só as de 02/03 em diante).
   `GET /atletas/1/semana-padrao` mostra a vigência de 02/03 como `vigente` (`em` é hoje) e as duas em `vigencias`, a mais nova primeiro. Cada
   item traz `dia_semana_texto` pronto (`segunda`, `terça`...). Regravar o mesmo corpo dá `atividades_reaplicadas: 0`. Repita a contagem do passo 3:
   `(sem)` 14, `professor` 1, `semana_padrao` 50, `sugestao` 15 e `trainingpeaks` 1.
7. **O tipo, a origem, a divergência e a `linha_base` no `GET` da atividade** ([[modulos/api]]; [[decisoes/0004-contrato-tela-evolucao]], adendo 6 e 7):
   ```
   curl -s localhost:8047/atletas/1/atividades/68
   curl -s localhost:8047/atletas/1/atividades/71
   curl -s localhost:8047/atletas/1/atividades/72
   curl -s localhost:8047/atletas/1/atividades/15
   curl -s localhost:8047/atletas/1/atividades/81
   ```
   Esperado (os valores batem com o [[metricas/tipo-linha-base-oraculo]]; `z` sem arredondar na API):
   - **68** (corrida de 13/03, 306 s/km): `leve`, origem `sugestao` (sexta, sem item no plano). `pace_medio` **`fora`**: `valor_texto` `5:06/km`, mediana
     `5:30/km`, 11 treinos, `z` -2,698, `texto` "Pace médio fora do seu normal para treino leve: 5:06/km, 24 s/km mais rápido que a mediana de
     5:30/km (11 treinos nas últimas 12 semanas). Isto compara com o seu histórico; não diz se o treino foi bom ou ruim." `fc_media` **`fora`** (160 bpm, 8 treinos, `z` 3,691).
     `carga_hora` **`sem_valor`** com `motivo` `carga_pendente`: a fixture de corrida não tem carga gravada, e o texto diz "a carga ainda não foi calculada".
   - **71** (terça, `intervalado` pelo plano, origem `semana_padrao`): `melhor_pace` **`fora`** (`4:09/km` contra a mediana `4:24/km`, 9 treinos, `z` -2,841,
     "15 s/km mais rápido"); `fc_melhor_tiro` **`dentro`** (172 bpm, `z` 0); `fc_media` **`dentro`** (160 bpm, 10 treinos).
   - **72** (ciclismo de 18/03, quarta, `leve` pelo plano): `fc_media` **`dentro`** (133 bpm contra 130, `z` 1,154) e `carga_hora` **`fora`**: `55,0 pontos/h`,
     mediana `42,0 pontos/h`, `z` 4,384, "13,0 pontos/h maior".
   - **15** (13/01, plano `intervalado`, mas duas corridas de 28 min sem esforço): `tipo_divergencia` `{"motivo": "sem_esforco", "texto": "O plano diz
     intervalado, mas o treino não teve esforço detectado."}` e `linha_base` `sem_linha_base` com `motivo` `divergente` ("Sem linha de base: treino com formato
     diferente do plano."). O plano vence: o tipo fica `intervalado`.
   - **81** (28/03, sábado, plano `longo`, mas 6 tiros): divergência `tem_tiros` ("O plano diz longo, mas o treino teve 6 tiros de 1 km."), também `sem_linha_base`.
   O tipo confirmado (`professor`, `trainingpeaks`) nunca muda: o `GET` traz `tipo_confirmado: true`. A API **calcula a linha de base na leitura e nunca grava**.
   Corrida em esteira não entra no pace; natação só tem `fc_media`.
8. **A tela da semana-padrão** ([[design/telas/semana-padrao]], [[modulos/mobile]]). Em outro terminal:
   ```
   cd apps/mobile
   npm ci
   CI=1 EXPO_PUBLIC_API_URL=http://localhost:8047 EXPO_PUBLIC_ATLETA_ID=1 npx expo start --web --port 8082
   ```
   (`CI=1` evita perguntas interativas do Expo.) Abra `http://localhost:8082/semana-padrao` (ou o botão "Semana-padrão" na tela inicial). Esperado: o título "Semana-padrão", o campo "Vale a partir de"
   (hoje, em `dd/mm/aaaa`, com os atalhos "Hoje" e "Próxima segunda"), "Quem definiu" com **Treinador** marcado (a vigente é a de 02/03, `professor`),
   os sete dias com os itens do plano (segunda natação `Leve`; terça corrida `Intervalado`; quarta ciclismo `Leve`; quinta corrida `Moderado`; sexta "Sem treino"; sábado ciclismo
   `Moderado` e corrida `Longo`; domingo corrida `Sem tipo`) e o botão "Salvar semana" desligado ("Nada mudou ainda."). Toque no tipo da natação de segunda, escolha **Moderado**
   e toque em "Salvar semana". Esperado: o botão liga ("Salvar semana") e, depois de salvar, aparece "Semana salva. Nenhum treino mudou de tipo. Treinos anteriores a 09/11/26 não foram alterados.",
a data passa a mostrar o aviso "Já existe uma semana que vale desde esta data. Salvar vai substituí-la." (a vigência de hoje agora existe) e "Semanas anteriores" lista três vigências
("Desde 09/11/26", "Em vigor", "Treinador · 7 treinos por semana"; "Desde 02/03/26", "Treinador · 7 treinos por semana"; "Desde 05/01/26", "Eu · 7 treinos por semana"). Na API, `GET /atletas/1/semana-padrao` mostra a nova vigência. Nenhum treino muda porque nenhum treino sintético é de hoje em diante.
   Para forçar os outros estados (vazio, erro de rede, 404, 422), use a API falsa com `EXPO_PUBLIC_ATLETA_ID` de 2 a 6, como em [[modulos/mobile]].
9. **`worker.reclassificar` e a `reclassificacao_pendente`** (com blocos de verdade, de FIT). Este passo usa os FIT sintéticos de esforços e um **segundo atleta**
   (o id 2; o atleta 1 continua o das fixtures da Meta 7). **Não rode `reclassificar` no atleta 1**: veja o aviso abaixo.
   ```
   uv run python -m worker.importar_garmin tests/fixtures/garmin/esforcos --atleta "Atleta Esforços"
   ```
   Esperado: `inseridas=7`. As cinco corridas (ids 82 a 86, de 05 a 12/05/2025) entram; duas delas (84 e 85) já ganham `leve`, origem `sugestao`, pela reserva. Grave um plano para ele:
   ```
   curl -s -X PUT -H 'content-type: application/json' localhost:8047/atletas/2/semana-padrao -d '{"vigente_desde":"2025-05-01","definido_por":"atleta","itens":[{"dia_semana":1,"modalidade":"corrida","tipo_treino":"longo"},{"dia_semana":3,"modalidade":"corrida","tipo_treino":"moderado"},{"dia_semana":5,"modalidade":"corrida","tipo_treino":"intervalado"}]}'
   ```
   Esperado: `atividades_reaplicadas: 4`. A segunda-feira (82 e 86) vira `longo`, a quarta (83) `moderado` e a sexta (84, uma rodagem leve) `intervalado` com `tipo_divergencia: "sem_esforco"`; a 85 (sábado) segue `leve`,
   `sugestao`. `GET /atletas/2/atividades/84` traz a divergência e `sem_linha_base` por `divergente`; `GET /atletas/2/atividades/82` tem `linha_base` `ok` com `pace_medio` e
   `fc_media` `aprendendo` (0 de 8 treinos). As duas pedaladas (87 e 88, ciclismo sem plano e sem reserva para ciclismo) ficam sem tipo e `sem_linha_base` com o motivo `sem_tipo`.
   Agora simule uma sugestão de antes da regra atual e reclassifique:
   ```
   docker exec treino-meta7-postgres-1 psql -U treino -d treino -c "update atividade set tipo_versao=null where id=85"
   curl -s localhost:8047/atletas/2/evolucao/tiros-1km        # "reclassificacao_pendente": true
   uv run python -m worker.reclassificar --atleta-id 2
   curl -s localhost:8047/atletas/2/evolucao/tiros-1km        # "reclassificacao_pendente": false
   ```
   Esperado: `reclassificadas 5 corridas do atleta 2`, e a segunda rodada igual (idempotente). Atleta que não existe: `erro: atleta 99 não encontrado`, saída 1.
   **Aviso: o `reclassificar` refaz os blocos das corridas a partir das voltas gravadas** (`detectar_esforcos`). As atividades sintéticas do passo 3 não têm voltas, então
   rodar `uv run python -m worker.reclassificar --atleta-id 1` apaga os blocos delas (`bloco_atividade` do atleta 1 vai a 0), perde as 15 sugestões e as duas divergências, e deixa
   a linha de base sem sentido (visto: `sugestao` 15 -> 0, `(sem)` 14 -> 29). Para refazer, derrube o banco e comece do passo 1.
10. **Testes da meta.** Na raiz: `uv run pytest -q tests/test_fixtures_meta7.py services/api/tests/metricas/test_tipo_treino.py services/api/tests/metricas/test_linha_base.py
    services/api/tests/rotas/test_semana_padrao.py services/api/tests/rotas/test_linha_base_atividade.py services/api/tests/servicos/test_tipo_treino_banco.py`
    (sem a `DATABASE_URL`; usam SQLite e as fixtures). Esperado: `129 passed, 1 skipped`. Em `apps/mobile`:
    `npx jest __tests__/TelaSemanaPadrao.test.tsx __tests__/rotaSemanaPadrao.test.tsx __tests__/semanaPadraoDatas.test.ts`, esperado 3 suítes e 48 testes verdes.

## Encerrar e limpar
- `Ctrl+C` na API e no `expo start`; apague a pasta de `FIT_DIR` e a pasta `/caminho/saida` (o `porta.yml`, o `carregar.py` e os JSON).
- Apagar o banco de vez (só o projeto `treino-meta7`): `docker compose -p treino-meta7 -f infra/docker-compose.yml -f /caminho/saida/porta.yml down -v`.
- Confira com `docker ps`: só devem sobrar os containers que já existiam. Em `apps/mobile`, o `npm ci` deixa uma `node_modules/` (ignorada pelo git), e o `expo start` reescreve o `apps/mobile/tsconfig.json`, que é versionado: rode `git checkout apps/mobile/tsconfig.json` para deixar a árvore limpa.

## Problemas comuns
- **Porta ocupada:** troque a porta no override (e na `DATABASE_URL`), na API ou no `--port` do app. Se trocar a do app, ajuste o `CORS_ORIGENS`.
- **O app abre, mas não carrega a semana (erro de rede):** a origem do app não está no `CORS_ORIGENS` da API, ou o `EXPO_PUBLIC_API_URL` não aponta para ela. Reinicie o `expo start` ao mudar uma variável `EXPO_PUBLIC_*`.
- **Tudo cai no banco errado:** faltou o `-p treino-meta7` ou o `export DATABASE_URL` neste terminal.
- **`uv` avisa que `VIRTUAL_ENV` não bate com o ambiente do projeto:** é só aviso; rode `unset VIRTUAL_ENV`.
- **`linha_base` `sem_linha_base` com `sem_tipo`:** a atividade não tem tipo (natação do item sem tipo, corrida solta de menos de 20 min, ciclismo sem plano). A reserva só tipa corrida.
- **Todas as métricas `aprendendo`:** menos de 8 treinos do mesmo tipo nas últimas 12 semanas. Tipo quinzenal ou mais raro tende a ficar aqui (limitação aceita, adendo 2 da ADR 0011).
- **A atividade anterior à primeira vigência não muda ao gravar o plano:** o `PUT` só reaplica o tipo de `vigente_desde` em diante. A regra de reserva dela vem da importação ou do `worker.reclassificar`.
- **Os números do oráculo não batem:** confira que o passo 6 gravou as **duas** vigências e que o banco é o das fixtures (atleta 1, 81 atividades). Os valores de linha de base mudam quando chega treino novo.
- **Fuso:** o dia da semana vem da data local da atividade (`inicio + fuso_min`; sem `fuso_min`, `America/Sao_Paulo`), como em [[decisoes/0003-fuso-da-atividade]]. A atividade de 24/02 às 23:10 local é terça, mesmo já sendo quarta em UTC.

## Fora ou depois (pendências conhecidas)
- **Hífen sem quebra em "semana-padrão" no estado vazio:** o título do estado vazio quebra a linha no hífen ("semana-" / "padrão"). Detalhe visual da tela, para o Rafa.
- **Esforço curto no intervalado:** sem a série de 1 km, o melhor esforço curto (por faixa de distância) fica fora da `linha_base@2`; o intervalado compara por FC média e carga por hora.
- **Tipos raros ainda em "aprendendo":** tipo feito menos de 8 vezes em 12 semanas (quinzenal ou mais raro).
- **Taxa de "fora" a revisar:** com o limite `|z| >= 2,5` e o piso de 2%, a proporção de treinos marcados "fora do normal" precisa ser revista depois da Meta 7.
- **Conferência com o histórico real (#269):** não entra neste guia (o dado real fica fora do git).
