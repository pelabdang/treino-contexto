---
tipo: guia
status: em-uso
dono: nina
atualizado: 2026-11-09
links: [[produto/meta-7-como-rodar]], [[produto/meta-6-como-rodar]], [[produto/roadmap]], [[produto/metas/meta-8-check-in]], [[decisoes/0012-check-in-pos-treino]], [[decisoes/0004-contrato-tela-evolucao]], [[decisoes/0003-fuso-da-atividade]], [[metricas/carga-pse]], [[metricas/carga-pse-oraculo]], [[design/telas/checkin]], [[modulos/banco]], [[modulos/api]], [[modulos/api-client]], [[modulos/mobile]], [[modulos/worker]], [[diario/2026-11-09]]
---
# Meta 8: como rodar o check-in pós-treino e a carga pela PSE

Passo a passo da Meta 8 com as fixtures: Postgres próprio, migrações até a 0012, 18 atividades sintéticas, o check-in (`PUT`, `GET`,
`DELETE`) pela API, a carga pela PSE (`carga_pse@1`), a lista de pendentes, o `GET` da atividade com `checkin`, `checkin_aberto` e
`pse_sugerida`, a tela no app web e o `worker.apagar_checkin`. **Só dado sintético, sem rede.** As regras estão na
[[decisoes/0012-check-in-pos-treino]], que ainda é **proposta** (PR #305, esperando o Angelo); este guia segue o que está no `main`.
Os números esperados vêm do oráculo [[metricas/carga-pse-oraculo]]. **Check-in é dado de saúde:** use só estes valores sintéticos.

**Situação da verificação (#300, Nina, 09/11):** os passos 1 a 11, 13 e 14 foram rodados de verdade num clone limpo do `main`
(`b8f7cf2`, depois do #313), com o banco `treino-meta8` (Postgres na 5455, API na 8055, app web na 8083). Os números abaixo são os que
saíram. Banco, API e app foram derrubados no fim e **nada usou a rede** (o `npm ci` baixa pacotes; o resto, não).
**Não rodado aqui:** o app em celular (só a web, no tema escuro do navegador); **os estados forçados com a API falsa (passo 12)**: a
extensão do navegador caiu antes, então só conferi as respostas da API falsa com `curl` e os testes do app (passo 14); a Bia os abriu na tela depois, na revisão independente (todos com o texto certo); nada de leitor de tela.
A Bia segue o guia como revisão independente.

## Antes de começar
- `git`, `uv`, Docker (Compose 2.24 ou mais novo), `curl`, `python3` e, para a tela, `node` com `npm`. Comandos na **raiz** do repositório.
- **Não use o banco do seu dia a dia** (`treino-contexto-postgres-1`, porta 5433). Rode sempre com `-p treino-meta8`
  (volume `treino-meta8_pgdata`). Não use as portas 5433, 8000 e 8081 (banco e servidores de uso diário).
- Escolha **portas livres** (`docker ps` e `lsof -iTCP:<porta> -sTCP:LISTEN`). Abaixo: 5455 (Postgres), 8055 (API), 8056 (API falsa) e 8083 (app web).
- Uma pasta de trabalho fora do git, para o `porta.yml` e os scripts (abaixo, `/caminho/saida`).
- **O relógio importa.** O prazo do check-in (7 dias) e a lista de pendentes usam o "hoje" real (`America/Sao_Paulo`). As fixtures foram escritas para
  **hoje = 09/11/2026**. O `carregar.py` do passo 3 desloca todas as datas pelo mesmo número de dias quando você roda em outro dia
  (imprime `deslocamento N dias`); os números e a ordem dos pendentes ficam iguais, só as **datas na tela** mudam (abaixo, as de 09/11). Rodado em 09/11, deslocamento 0.
  Rode tudo no mesmo dia: passar da meia-noite (Brasília) tira um dia da janela.

## Passo a passo
1. **Subir o Postgres.** Salve `/caminho/saida/porta.yml` com
   ```
   services:
     postgres:
       ports: !override
         - "5455:5432"
   ```
   e rode:
   ```
   docker compose -p treino-meta8 -f infra/docker-compose.yml -f /caminho/saida/porta.yml up -d
   export DATABASE_URL="postgresql+psycopg://treino:treino@localhost:5455/treino"
   ```
   Esperado: `treino-meta8-postgres-1` `healthy`. Sem o `export`, ponha `env DATABASE_URL=...` antes de cada comando.
2. **Instalar e migrar:**
   ```
   uv sync
   (cd services/api && uv run alembic upgrade head && uv run alembic current)
   ```
   Esperado: doze linhas `Running upgrade` e `0012 (head)`. A `0012` cria `checkin_treino` ([[modulos/banco]]).
3. **Carregar as 18 atividades sintéticas** de `tests/fixtures/meta8/atividades.json` (15/10 a 09/11/2026: corrida, natação, ciclismo, `outra`, um
   multiesporte com pai e duas trocas, um treino de 0 s). Este trecho grava as atividades e **um** check-in: o de 15/10, que está
   **fora do prazo de criação**, então a API o recusaria (passo 6); os outros oito entram pela API no passo 4. Salve como `/caminho/saida/carregar.py`
   (o bloco abaixo está sem recuo no começo; copie como está):
```python
import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from app.db.models import Atividade, Atleta, CheckinTreino
from app.db.session import SessionLocal
from app.servicos.checkin import hoje_local

pasta = Path("tests/fixtures/meta8")
dados = json.loads((pasta / "atividades.json").read_text(encoding="utf-8"))
checkins = json.loads((pasta / "checkins.json").read_text(encoding="utf-8"))

# As fixtures foram escritas para "hoje = 09/11/2026". Em outro dia, desloca todas as datas
# pelo mesmo número de dias, para o prazo e os pendentes continuarem iguais ao oráculo.
desloc = (hoje_local() - date(2026, 11, 9)).days
agora = datetime.now(UTC)
FORA_DO_PRAZO = "2026-10-15/cor1"

with SessionLocal() as s:
    atleta = Atleta(nome="Atleta Fictício")
    s.add(atleta)
    s.flush()
    for f in dados["atividades"]:
        a = Atividade(
            atleta_id=atleta.id, fonte="fixture", fonte_id=f["id"], modalidade=f["modalidade"], subtipo=f["subtipo"],
            inicio=datetime.fromisoformat(f["inicio"]) + timedelta(days=desloc), fuso_min=f["fuso_min"],
            duracao_s=f["duracao_s"])
        s.add(a)
        s.flush()
        c = checkins.get(f["id"])
        if c and f["id"] == FORA_DO_PRAZO:
            s.add(CheckinTreino(
                atividade_id=a.id, pse=c["pse"], sensacao=c["sensacao"], nada_a_relatar=c["nada_a_relatar"],
                texto=c["texto"], versao="checkin@1", registrado_em=agora, atualizado_em=agora,
                **{k: k in c["atalhos"] for k in ("dor", "cansaco", "sono_ruim", "calor", "trabalho_estresse")}))
    s.commit()
    print(f"atleta {atleta.id}: {len(dados['atividades'])} atividades, 1 check-in, deslocamento {desloc} dias")
```
   Rode (na raiz): `uv run python - < /caminho/saida/carregar.py`. Esperado: `atleta 1: 18 atividades, 1 check-in, deslocamento 0 dias`.
   Os ids saem na ordem do arquivo. **Tabela de ids usada daqui em diante:**

   | id | fixture | o que é |
   |---|---|---|
   | 1 | 2026-10-15/cor1 | corrida de 45 min, tem check-in (fora do prazo) |
   | 2, 3 | 2026-11-01/cor1 e cor2 | corridas de 01/11 (a 3 às 23:30 local, já 02/11 em UTC), fora do prazo |
   | 4 | 2026-11-02/cor1 | corrida de 02/11, `fuso_min` nulo, no limite do prazo |
   | 5 | 2026-11-03/out1 | `multiesporte_pai` |
   | 6, 8, 10 | 2026-11-03/nat1, cic1, cor1 | as três partes do multiesporte (natação, ciclismo, corrida) |
   | 7, 9 | 2026-11-03/out2 e out3 | `troca` |
   | 11 | 2026-11-04/cic1 | ciclismo, subtipo nulo |
   | 12 | 2026-11-05/cor1 | corrida de 45 min, sem check-in |
   | 13 | 2026-11-06/out1 | `outra` de 30 min |
   | 14 | 2026-11-07/cor1 | corrida de 2725 s |
   | 15, 16 | 2026-11-08/nat1 e cic1 | natação (piscina) e ciclismo virtual |
   | 17 | 2026-11-09/cor1 | corrida com `duracao_s = 0` |
   | 18 | 2026-11-09/cor2 | corrida de 45 min |
4. **Subir a API** em outro terminal, com a mesma `DATABASE_URL`:
   ```
   CORS_ORIGENS=http://localhost:8083 FIT_DIR="$(mktemp -d)" uv run uvicorn app.main:app --app-dir services/api --port 8055
   ```
   Confira: `curl -s localhost:8055/health` dá `{"status":"ok"}`.
5. **Registrar os outros oito check-ins pela API** (`PUT`; [[modulos/api]], "Check-in pós-treino"). Salve `/caminho/saida/gravar_checkins.py`
   (copie como está; só usa a biblioteca padrão e o banco, para achar os ids):
```python
import json
import os
import urllib.error
import urllib.request
from pathlib import Path

from app.db.models import Atividade
from app.db.session import SessionLocal
from sqlalchemy import select

API = os.environ.get("API", "http://localhost:8055")  # outra porta: API=http://localhost:<porta>
ATLETA = 1
checkins = json.loads(Path("tests/fixtures/meta8/checkins.json").read_text(encoding="utf-8"))

with SessionLocal() as s:
    ids = {a.fonte_id: a.id for a in s.scalars(select(Atividade).where(Atividade.atleta_id == ATLETA))}

for fonte_id, corpo in checkins.items():
    if fonte_id == "2026-10-15/cor1":
        continue  # já está no banco: fora do prazo de criação
    req = urllib.request.Request(
        f"{API}/atletas/{ATLETA}/atividades/{ids[fonte_id]}/checkin",
        data=json.dumps(corpo).encode(), method="PUT", headers={"content-type": "application/json"})
    try:
        with urllib.request.urlopen(req) as r:
            print(fonte_id, "->", ids[fonte_id], r.status)
    except urllib.error.HTTPError as e:
        print(fonte_id, "->", ids[fonte_id], e.code)
```
   Rode `uv run python - < /caminho/saida/gravar_checkins.py` (com outra porta de API: `API=http://localhost:<porta> uv run python - < ...`; o mesmo vale para o `ver.py` do passo 8, e os `curl` dos passos 6 a 10 trazem `localhost:8055` escrito, troque também). Esperado: oito linhas com `200`, nas atividades 17, 18, 15, 16, 14, 13, 6 e 8.
6. **Os `422` do `PUT`** (sem repetir o que foi enviado; [[decisoes/0012-check-in-pos-treino]], itens 3 e 5):
   ```
   H='content-type: application/json'
   B='{"pse":5,"sensacao":3,"nada_a_relatar":true,"atalhos":[]}'
   curl -s -w ' [%{http_code}]\n' -X PUT -H "$H" localhost:8055/atletas/1/atividades/2/checkin -d "$B"
   curl -s -w ' [%{http_code}]\n' -X PUT -H "$H" localhost:8055/atletas/1/atividades/5/checkin -d "$B"
   curl -s -w ' [%{http_code}]\n' -X PUT -H "$H" localhost:8055/atletas/1/atividades/12/checkin -d '{"pse":11,"sensacao":3,"nada_a_relatar":true,"atalhos":[],"texto":"MARCADOR-SINTETICO-123"}'
   curl -s -w ' [%{http_code}]\n' -X PUT -H "$H" localhost:8055/atletas/1/atividades/12/checkin -d '{"pse":5,"sensacao":3,"nada_a_relatar":true,"atalhos":["dor"]}'
   ```
   Esperado, nesta ordem (todos `422`):
   - atividade 2 (fora do prazo): `{"detail":[{"loc":["path","atividade_id"],"msg":"o check-in só pode ser criado até 7 dias depois do treino","type":"fora_do_prazo"}]}`;
   - atividade 5 (`multiesporte_pai`): mesmo formato, `msg` "esta parte do treino multiesporte não pede check-in" e `type` `atividade_sem_checkin`;
   - PSE 11: `loc` `["body","pse"]`, `type` `less_than_equal`. **Sem o campo `input`** e **sem o texto marcador** (o `422` do check-in nunca repete a entrada, porque é dado de saúde);
   - "nada a relatar" com atalho: `loc` `["body"]`, `type` `value_error`, `msg` fixa "Value error, nada a relatar não combina com atalho nem texto".
   O `PUT` da atividade 1 (15/10), que já tem check-in, **seria aceito** (editar não tem prazo); a 3 (01/11 às 23:30 local) também dá `fora_do_prazo`: vale a data local, não a UTC.
7. **`GET`, edição, `DELETE` e os `404`** (use a atividade 12, sem check-in):
   ```
   U=localhost:8055/atletas/1/atividades/12/checkin
   curl -s -w ' [%{http_code}]\n' $U
   curl -s -w ' [%{http_code}]\n' -X PUT -H "$H" $U -d '{"pse":5,"sensacao":3,"nada_a_relatar":false,"atalhos":["dor","sono_ruim"],"texto":null}'
   curl -s -w ' [%{http_code}]\n' -X PUT -H "$H" $U -d '{"pse":8,"sensacao":2,"nada_a_relatar":false,"atalhos":["calor"],"texto":"  Dia quente.  "}'
   curl -s -o /dev/null -w '%{http_code}\n' -X DELETE $U
   curl -s -o /dev/null -w '%{http_code}\n' -X DELETE $U
   curl -s -w ' [%{http_code}]\n' $U
   curl -s -w ' [%{http_code}]\n' -X DELETE localhost:8055/atletas/2/atividades/12/checkin
   ```
   Esperado, linha a linha:
   1. `{"detail":"sem check-in"} [404]`;
   2. `200` com `pse` 5, `pse_texto` "difícil", `sensacao_texto` "normal", `atalhos` Dor e Sono ruim, `versao` `checkin@1`, `registrado_em` e `atualizado_em` iguais, com fuso;
   3. `200` com `pse` 8 (`pse_texto` "8": o 8 não tem âncora), `sensacao_texto` "mal", **só** Calor (os atalhos antigos saem: o `PUT` substitui tudo), `texto` "Dia quente." (aparado),
      `registrado_em` igual ao da criação e `atualizado_em` depois;
   4. `204`; 5. `204` de novo (idempotente); 6. `404` "sem check-in";
   7. `{"detail":"atleta não encontrado"} [404]` (atleta 2 não existe; atividade de outro atleta também dá `404`, inclusive no `DELETE`).
   `GET /atletas/1/checkins/pendentes?dias=8` dá `422` (`dias` vai de 1 a 7). Ao fim, a atividade 12 volta a ficar sem check-in.
8. **A carga pela PSE e o `GET` da atividade** ([[metricas/carga-pse]]; `carga_pse@1` = PSE x minutos, em UA, calculada na leitura e **não** somada à `carga@2`, que tem outra escala).
   Para ver as oito de uma vez, salve `/caminho/saida/ver.py`:
```python
import json
import os
import urllib.request

API = os.environ.get("API", "http://localhost:8055") + "/atletas/1"  # outra porta: API=http://localhost:<porta>


def get(rota):
    with urllib.request.urlopen(API + rota) as r:
        return json.load(r)


for i in (18, 15, 16, 14, 13, 12, 17, 5, 7, 6, 8, 10, 11, 4, 1):
    d = get(f"/atividades/{i}")
    c = d["carga_pse"]
    print(i, "aberto=", d["checkin_aberto"], "sug=", d["pse_sugerida"], "pse=", None if d["checkin"] is None else d["checkin"]["pse"], "|",
          None if c is None else (c["estado"], c["valor"], c["valor_texto"], c["texto"]))
p = get("/checkins/pendentes")
print(p["dias"], p["total"], [x["atividade_id"] for x in p["pendentes"]])
```
   Rode `python3 /caminho/saida/ver.py`. Esperado (igual ao oráculo):
   ```
   18 aberto= True sug= None pse= 6 | ('calculada', 270.0, '270 UA', 'Carga pela PSE: 6 x 45 min = 270 UA.')
   15 aberto= True sug= None pse= 4 | ('calculada', 160.0, '160 UA', 'Carga pela PSE: 4 x 40 min = 160 UA.')
   16 aberto= True sug= None pse= 7 | ('calculada', 350.0, '350 UA', 'Carga pela PSE: 7 x 50 min = 350 UA.')
   14 aberto= True sug= None pse= 6 | ('calculada', 272.5, '272,5 UA', 'Carga pela PSE: 6 x 45,4 min = 272,5 UA.')
   13 aberto= True sug= None pse= 0 | ('calculada', 0.0, '0 UA', 'Carga pela PSE: 0 x 30 min = 0 UA.')
   12 aberto= True sug= None pse= None | ('sem_checkin', None, None, 'Sem check-in: a carga pela PSE precisa da PSE do treino.')
   17 aberto= True sug= None pse= 5 | ('sem_duracao', None, None, 'Treino sem duração registrada: sem carga pela PSE.')
   5 aberto= False sug= None pse= None | None
   7 aberto= False sug= None pse= None | None
   6 aberto= True sug= None pse= 5 | ('calculada', 150.0, '150 UA', 'Carga pela PSE: 5 x 30 min = 150 UA.')
   8 aberto= True sug= 5 pse= 6 | ('calculada', 270.0, '270 UA', 'Carga pela PSE: 6 x 45 min = 270 UA.')
   10 aberto= True sug= 6 pse= None | ('sem_checkin', None, None, 'Sem check-in: a carga pela PSE precisa da PSE do treino.')
   11 aberto= True sug= None pse= None | ('sem_checkin', None, None, 'Sem check-in: a carga pela PSE precisa da PSE do treino.')
   4 aberto= True sug= None pse= None | ('sem_checkin', None, None, 'Sem check-in: a carga pela PSE precisa da PSE do treino.')
   1 aberto= True sug= None pse= 5 | ('calculada', 225.0, '225 UA', 'Carga pela PSE: 5 x 45 min = 225 UA.')
   7 4 [12, 11, 10, 4]
   ```
   Como ler: **270** (corrida 18, 6 x 45), **160** (natação 15, 4 x 40: a `carga@2` da natação é `sem_carga`, a PSE dá carga), **350** (ciclismo virtual 16, 7 x 50),
   **272,5** (14, 2725 s; o `valor` é 272,5 sem arredondar, e o `texto` mostra os minutos com 1 casa, "45,4 min"), **0 UA** (13, PSE 0 vale), `sem_checkin`
   (12), `sem_duracao` (17, com check-in e duração 0). Pai (5) e troca (7) têm `carga_pse` e `checkin` nulos e `checkin_aberto` `false`.
   Nas atividades 2 e 3 (fora do prazo, sem check-in), `checkin_aberto` é `false`. **`pse_sugerida`:** a parte 8 (ciclismo) sugere 5, a PSE da natação (id 6); a parte 10 (corrida) sugere 6, a do ciclismo (id 8); a primeira parte (6) não tem sugestão.
   É só um valor inicial: nada é copiado entre partes.
9. **Lista de pendentes** (última linha do passo 8; ou `curl -s localhost:8055/atletas/1/checkins/pendentes`). Esperado: `dias` 7, `total` 4, atividades **12, 11, 10 e 4**
   (05/11, 04/11, 03/11 às 09:20 e 02/11), as mais recentes primeiro. Cada item traz `atividade_id`, `modalidade`, `data_local`, `hora_local`, `duracao` e `titulo` ("Corrida, 45 min"),
   **nenhum campo do check-in**. Ficam de fora: o pai e as trocas, as atividades com check-in e as de 01/11 (fora da janela). A 11 tem `subtipo` nulo e aparece.
10. **Preparar a tela:** a atividade 12 já está sem check-in (passo 7). Confirme com `curl -s localhost:8055/atletas/1/checkins/pendentes` (`total` 4).
11. **A tela no app web com a API real** ([[design/telas/checkin]], [[modulos/mobile]]). Em outro terminal:
    ```
    cd apps/mobile
    npm ci
    CI=1 EXPO_PUBLIC_API_URL=http://localhost:8055 EXPO_PUBLIC_ATLETA_ID=1 npx expo start --web --port 8083
    ```
    Reinicie o `expo start` ao mudar qualquer `EXPO_PUBLIC_*`. Rodado numa janela larga de navegador, no tema escuro; as rotas abaixo abrem direto pela URL.
    - **Evolução** (`http://localhost:8083/`): a linha "Check-ins pendentes · 4".
    - **Pendentes** (`/checkins-pendentes`): "Treinos dos últimos 7 dias sem check-in", quatro linhas ("Corrida, 45 min / 05/11/26 às 07:00", "Ciclismo, 60 min / 04/11/26 às 06:00",
      "Corrida, 20 min / 03/11/26 às 09:20", "Corrida, 50 min / 02/11/26 às 07:00") e "4 treinos sem check-in". Nada do check-in aparece.
    - **Criar em 3 toques** (toque na primeira linha, `/checkin/12?origem=pendentes`): "Pergunta 1 de 3", "Qual foi o esforço do treino?", grade de 0 a 10 com as âncoras
      (6, 8 e 9 sem texto) e "A PSE é só sua: não se compara com a de outros atletas.". Toque **5 difícil** (avança sozinho). "Pergunta 2 de 3", "Como você se sentiu no treino?": toque **Normal**.
      "Pergunta 3 de 3", "Quer registrar mais alguma coisa?": os cinco atalhos, o campo opcional ("0 de 500") e "Nada a relatar" ("salva na hora"); "Salvar check-in" fica desligado até haver atalho ou texto.
      Toque **Nada a relatar**. Esperado: "Check-in salvo", "Esforço (PSE): 5 · difícil", "Sensação: normal", "Observação: Nada a relatar" e o botão "Voltar aos pendentes". Foram **3 toques** e um só `PUT`.
    - **Cartões** (`/treino/12`): "Check-in" com Esforço 5 · difícil, Sensação normal, Observação Nada a relatar, os botões "Editar" e "Apagar check-in", e "Carga pela PSE" **225 UA**,
      "Carga pela PSE: 5 x 45 min = 225 UA." e "Não se compara com a carga do relógio (pontos): são escalas diferentes.".
    - **Editar** (toque em "Editar", `/checkin/12`): "Editar check-in" em tela única, com "Nada a relatar" marcado e "Salvar alterações" desligado. Toque o atalho **Calor**: "Nada a relatar" desmarca e o botão liga.
      Salve: "Check-in salvo", "Observação: Calor" e o botão "Voltar ao treino" (na criação pelos pendentes o botão é "Voltar aos pendentes"). (Editar não tem prazo.)
    - **Apagar** (volte a `/treino/12`, "Apagar check-in"): diálogo "Apagar este check-in?" ("Isso não pode ser desfeito."); toque "Apagar". Esperado: "Check-in apagado.", "Você ainda não fez o check-in deste treino.",
      "Sem check-in: a carga pela PSE precisa da PSE do treino." e o botão "Fazer check-in". A atividade 12 volta aos pendentes.
    - **Outros cartões:** `/treino/2` (fora do prazo): "Você ainda não fez o check-in deste treino." e "O prazo para fazer o check-in deste treino acabou (7 dias depois do treino).", sem botão.
      `/treino/5` (pai): **sem cartão de check-in**. `/treino/17` (duração 0, com check-in): "Treino sem duração registrada: sem carga pela PSE.".
      `/checkin/10` (corrida do multiesporte): "Na parte anterior você marcou 6." e o botão "Usar 6".
    **Achado de uso:** o texto "Check-in apagado." só aparece quando se apaga pelo cartão; apagando pela tela de edição o treino volta com o cartão "sem check-in" (já descrito em [[modulos/mobile]]).
12. **Estados forçados com a API falsa** (dados sintéticos em memória, sem banco). Pare o `expo start` do passo 11 e rode, em outro terminal na pasta `apps/mobile`:
    ```
    node scripts/api-falsa.mjs 8056
    CI=1 EXPO_PUBLIC_API_URL=http://localhost:8056 EXPO_PUBLIC_ATLETA_ID=7 npx expo start --web --port 8083
    ```
    O `EXPO_PUBLIC_ATLETA_ID` escolhe o estado (reinicie o `expo start` a cada troca; os ids 2 a 6 são da semana-padrão): `7` pendentes vazio ("Nenhum check-in pendente"); `8` pendentes sem rede; `9` `GET` da atividade sem rede;
    `10` `PUT` com `422` genérico; `11` `PUT` com `422` `fora_do_prazo`; `12` `PUT` com `422` `atividade_sem_checkin`; `13` `PUT` sem rede; `14` `PUT` com `404`; `15` `DELETE` sem rede;
    `16` `PUT` demora 4 s ("Salvando..."); `17` pendentes com `500`; `18` `GET` da atividade demora 6 s (carregando). Atividades da API falsa: `101` e `106` sem check-in, `107` com check-in, `108` com o prazo vencido,
    `109` parte de multiesporte com sugestão 5, `110` treino inteiro de multiesporte.
    **Onde abrir cada estado** (a Bia os abriu na tela e todos mostram o texto certo):
    - `7`, `8` e `17`: `/checkins-pendentes` (7: "Nenhum check-in pendente"; 8: erro de rede; 17: "Não foi possível carregar os pendentes...").
    - `9` e `18`: `/treino/101` (9: erro ao carregar; 18: "Carregando o treino..." por 6 s).
    - `10`, `11`, `12`, `13`, `14` e `16`: `/checkin/101`; toque **5**, **Normal** e **Nada a relatar** e o `PUT` sai com o estado do atleta (16: "Salvando..." por 4 s;
      11: o aviso de prazo; 12: "Este treino não pede check-in."; 10: "Algum dado do check-in não foi aceito..."; 14: "Treino não encontrado.").
    - `15` (`DELETE` sem rede): a API falsa só tem check-in pronto para o atleta 1 (atividade 107). No atleta 15, **crie** o check-in em `/checkin/101` (o `PUT` funciona) e depois, em `/treino/101`, toque
      "Apagar check-in" e confirme: aparece "Não foi possível apagar. Tente de novo.".
    - **Estado 17 na evolução** (`/`): a linha "Check-ins pendentes" aparece **sem número e sem erro**; o erro só aparece em `/checkins-pendentes` (é de propósito).
    **O que conferi aqui:** só as respostas da API falsa, com `curl` (pendentes do atleta 7 vazios; `PUT` do 11 com `422` `fora_do_prazo`, do 12 com `atividade_sem_checkin`, do 10 com `value_error`, do 14 com `404`;
    pendentes do 17 com `500`). **A tela em cada estado não foi aberta nesta rodada.**
13. **`worker.apagar_checkin`** (LGPD; [[modulos/worker]]). Com o banco do passo 3 (nesta altura com 9 check-ins, nas atividades 1, 6, 8 e 13 a 18):
    ```
    uv run python -m worker.apagar_checkin --atleta "Atleta Fictício"
    uv run python -m worker.apagar_checkin --atleta "Atleta Fictício"
    uv run python -m worker.apagar_checkin --atleta "Ninguém"
    docker exec treino-meta8-postgres-1 psql -U treino -d treino -At -c "select (select count(*) from checkin_treino), (select count(*) from atividade)"
    ```
    Esperado: `checkins: apagados=9` (rodado com 9: as oito do passo 5 mais a de 15/10; o número é o de check-ins que existem na hora), depois `checkins: apagados=0` (idempotente),
    depois `erro: atleta nao encontrado` com saída 1 (sem acento na mensagem), e a contagem `0|18`: os check-ins somem, **as atividades e o atleta ficam**. O comando imprime só contagens, nunca valores.
    Os pendentes voltam a listar 12 atividades.
14. **Testes da meta.** Na raiz, sem a `DATABASE_URL` (SQLite e as fixtures): `uv run pytest -q tests/test_fixtures_meta8.py services/api/tests/metricas/test_carga_pse.py services/api/tests/rotas/test_checkin.py
    services/api/tests/rotas/test_checkin_get_pendentes.py services/worker/tests/test_apagar_checkin.py`. Esperado: `214 passed, 1 skipped`. A suíte inteira (`uv run pytest -q`): `1690 passed, 2 skipped`.
    Em `apps/mobile`: `npx jest __tests__/TelaCheckin.test.tsx __tests__/TelaCheckinsPendentes.test.tsx __tests__/CartoesCheckin.test.tsx __tests__/evolucaoPendentes.test.tsx __tests__/rotasCheckin.test.tsx __tests__/checkinApi.test.ts`,
    esperado 6 suítes e 71 testes verdes; `npm test` inteiro: 19 suítes e 225 testes.

## Encerrar e limpar
- `Ctrl+C` na API, no `expo start` e na API falsa; apague a pasta de `FIT_DIR` e a pasta `/caminho/saida`.
- Apagar o banco de vez (só o projeto `treino-meta8`): `docker compose -p treino-meta8 -f infra/docker-compose.yml -f /caminho/saida/porta.yml down -v`.
- Confira com `docker ps`: só devem sobrar os containers que já existiam. Em `apps/mobile`, o `npm ci` deixa uma `node_modules/` (ignorada pelo git), e o `expo start` reescreve o `apps/mobile/tsconfig.json`, que é versionado:
  rode `git checkout apps/mobile/tsconfig.json` para deixar a árvore limpa.

## Problemas comuns
- **Porta ocupada:** troque a porta no override (e na `DATABASE_URL`), na API ou no `--port` do app. Se trocar a do app, ajuste o `CORS_ORIGENS`. Lembre: 5433, 8000 e 8081 são do uso diário.
- **O app abre, mas não carrega (erro de rede):** a origem do app não está no `CORS_ORIGENS` da API, ou o `EXPO_PUBLIC_API_URL` não aponta para ela. Reinicie o `expo start` ao mudar uma variável `EXPO_PUBLIC_*`.
- **Os pendentes ou o prazo não batem com o oráculo:** o dia mudou desde o passo 3 (o relógio é o real). Derrube o banco e comece de novo no mesmo dia, ou rode o `carregar.py` de novo num banco limpo.
- **Atividade de ontem aparece `fora_do_prazo`:** a janela é a data local de `America/Sao_Paulo` de hoje menos 7 dias, não a hora UTC.
- **Tudo cai no banco errado:** faltou o `-p treino-meta8` ou o `export DATABASE_URL` neste terminal.
- **`uv` avisa que `VIRTUAL_ENV` não bate com o ambiente do projeto:** é só aviso; rode `unset VIRTUAL_ENV`.
- **`PUT` devolve `422` sem dizer o que enviei:** é de propósito. O check-in é dado de saúde; veja `loc` e `type`.

## Fora ou depois (pendências conhecidas)
- **ADR 0012 ainda proposta** (PR #305): limites como o prazo de 7 dias e os textos podem mudar quando o Angelo responder; o guia vale para o que está no `main`.
- **App em celular (#301):** o Angelo abre a tela no celular dele no fim da meta; aqui só a web.
- **Texto da carga com minutos arredondados:** "6 x 45,4 min = 272,5 UA" (o `valor` é exato; o `texto` arredonda os minutos a 1 casa, então a conta à mão parece não fechar). Anotado para o Caio e o Rafa.
- **Sem série diária da carga pela PSE, sem comparação com a `carga@2`** (fora da meta).
- **Estados de erro da tela** (API falsa) sem captura de tela e sem conferência visual neste guia.
