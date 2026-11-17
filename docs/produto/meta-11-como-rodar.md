---
tipo: guia
status: em-uso
dono: nina
atualizado: 2026-11-16
links: [[produto/meta-10-como-rodar]], [[produto/meta-8-como-rodar]], [[produto/roadmap]], [[decisoes/0015-caixa-do-dia-do-professor]], [[decisoes/0004-contrato-tela-evolucao]], [[metricas/atencao]], [[metricas/atencao-oraculo]], [[design/telas/caixa-do-dia]], [[modulos/api]], [[modulos/banco]], [[modulos/worker]], [[modulos/mobile]], [[glossario]]
---
# Meta 11: como rodar a caixa do dia do professor

Passo a passo da Meta 11 com dado sintético: Postgres próprio, migrações até a 0016, o professor do piloto e oito atletas **fictícios** com vínculo e
consentimento (`worker.carregar_professor`), alguns treinos sintéticos, o `GET /professores/{id}/caixa-do-dia` com a `atencao@2`, o `PUT` em lote do
tipo e a tela `/caixa-do-dia`. **Só dado sintético, sem rede, sem conta do Garmin e sem dado de aluno real.** As regras estão na
[[decisoes/0015-caixa-do-dia-do-professor]] (aceita em 16/11) e a nota da regra em [[metricas/atencao]].
**Check-in, observação e feedback são dado de saúde:** use só os valores sintéticos daqui e das fixtures.

**Situação da verificação (#428, Nina, 16/11):** os passos 1 a 6 foram rodados de verdade num clone limpo do `main` (`b3b7f34`, depois do #447), com o
banco `treino-meta11` (Postgres na 5461, API na 8061). Os números abaixo são os que saíram. Banco e API foram derrubados no fim e nada usou a rede.
**Não rodado aqui:**
- a **tela** (`/caixa-do-dia` no Expo web) e o `npm run capturas`: não foram rodados por mim; a Bia rodou os passos 7 e 8 na QA (#429, PR #450) e achou a falha da CORS (#449, corrigida no passo 5);
- **dois dos quatro motivos** (`fora_do_normal` e `divergencia`): precisam de linha de base com treinos suficientes e de semana-padrão; este guia usa
  só `dor` e `checkin_vencendo`. Os quatro estão no oráculo à mão ([[metricas/atencao-oraculo]], `tests/test_fixtures_meta11.py`);
- **celular de verdade** (Expo Go, iOS, Android, toque, leitor de tela): amarrado ao ensaio com professor e atletas (decisão 10 da Meta 11);
- **aluno real:** nada disso entra aqui. A conferência local (#431) foi feita só na máquina do Angelo.

## Antes de começar
- As mesmas ferramentas e cuidados do [[produto/meta-8-como-rodar]] e do [[produto/meta-10-como-rodar]]: comandos na **raiz** do repositório,
  pasta de trabalho fora do git (abaixo, `/caminho/saida`), portas livres, `uv`, Docker, `curl`, `python3` e, para a tela, `node` com `npm`.
- **Não use o banco do seu dia a dia** (porta 5433) nem as portas 8000 e 8081. Rode sempre com `-p treino-meta11`. Abaixo: 5461 (Postgres) e 8061 (API).
- **Sem login.** O professor do piloto é o `PROFESSOR_ID` do ambiente; a rota leva o mesmo número (`/professores/{id}/...`). Qualquer outro número
  devolve o mesmo `404` (`professor_inexistente`): não é autenticação, só serve à máquina local.
- **O relógio importa.** A caixa olha os últimos 7 dias (atenção) e 14 dias (treinos novos) a partir de "hoje" em `America/Sao_Paulo`. O
  `carregar_treinos.py` do passo 4 escreve as datas **relativas a hoje**, então os números não dependem do dia; só os nomes dos dias ("sábado") mudam.
- **Qual `.env` vale:** só o da raiz do repositório; numa worktree ele não existe. Este guia põe `DATABASE_URL` e `PROFESSOR_ID` no ambiente.

## Passo a passo
1. **Subir o Postgres.** Salve `/caminho/saida/porta.yml` com
   ```
   services:
     postgres:
       ports: !override
         - "5461:5432"
   ```
   e rode:
   ```
   docker compose -p treino-meta11 -f infra/docker-compose.yml -f /caminho/saida/porta.yml up -d
   export DATABASE_URL="postgresql+psycopg://treino:treino@localhost:5461/treino"
   ```
   Esperado: o container `<projeto>-postgres-1` (aqui `treino-meta11-postgres-1`; o nome segue o `-p`) `healthy`.
2. **Instalar e migrar:**
   ```
   uv sync
   (cd services/api && uv run alembic upgrade head && uv run alembic current)
   ```
   Esperado: uma linha `Running upgrade` por migração, até o head atual (hoje 16 linhas e `0016 (head)`; confira com `ls services/api/alembic/versions`).
   A `0016` acrescenta `atividade.tipo_confirmado_por`, `atividade.tipo_confirmado_em` e `feedback_treino.tipo_visto` ([[modulos/banco]]).
3. **Carregar o professor e os atletas fictícios:**
   ```
   uv run python -m worker.carregar_professor --fixtures tests/fixtures/meta11
   ```
   Esperado: `professores=2 atletas=8 vinculos=8` e a linha `PROFESSOR_ID=1`. É o `identidade.json` da pasta: uma assessoria fictícia, dois
   professores, oito atletas (`Atleta Fixture Ana`, `Igor`, `Helena`, `Bruno`, `Carla`, `Davi`, um **sem consentimento** e um **de outro professor**).
   Rodar de novo não muda nada (idempotente). O comando só grava identidade e vínculos; recusa um atleta de mesmo nome que não veio desta carga, para
   nunca misturar dado sintético com dado real ([[modulos/worker]]).
   ```
   export PROFESSOR_ID=1
   ```
4. **Gravar alguns treinos sintéticos.** Salve como `/caminho/saida/carregar_treinos.py`:
```python
from datetime import UTC, datetime, timedelta

from app.db.models import Atividade, Atleta, CheckinTreino
from app.db.session import SessionLocal
from sqlalchemy import select

# (atleta, fonte_id, dias atrás, modalidade, minutos, tipo sugerido, check-in)
TREINOS = [
    ("Atleta Fixture Ana", "m11-ana-1", 2, "corrida", 45, "leve", {"pse": 6, "sensacao": 3, "dor": True}),
    ("Atleta Fixture Bruno", "m11-bru-1", 1, "corrida", 50, "intervalado", {"pse": 7, "sensacao": 4, "dor": False}),
    ("Atleta Fixture Carla", "m11-car-1", 6, "ciclismo", 70, None, None),
    ("Atleta Fixture Carla", "m11-car-2", 3, "corrida", 40, "moderado", {"pse": 5, "sensacao": 4, "dor": False}),
    ("Atleta Fixture Eva Sem Consentimento", "m11-eva-1", 2, "corrida", 45, "leve", {"pse": 6, "sensacao": 3, "dor": True}),
]

agora = datetime.now(UTC)
with SessionLocal() as s:
    n = 0
    for nome, fonte_id, dias, modalidade, minutos, tipo, checkin in TREINOS:
        atleta = s.scalars(select(Atleta).where(Atleta.nome == nome)).one()
        a = Atividade(
            atleta_id=atleta.id, fonte="fixture", fonte_id=fonte_id, modalidade=modalidade, subtipo=None,
            inicio=(agora - timedelta(days=dias)).replace(hour=10, minute=0, second=0, microsecond=0),
            fuso_min=-180, duracao_s=minutos * 60.0, tipo_treino=tipo, tipo_origem="sugestao" if tipo else None)
        s.add(a)
        s.flush()
        if checkin:
            s.add(CheckinTreino(
                atividade_id=a.id, pse=checkin["pse"], sensacao=checkin["sensacao"], nada_a_relatar=not checkin["dor"],
                texto=None, versao="checkin@1", registrado_em=agora, atualizado_em=agora,
                dor=checkin["dor"], cansaco=False, sono_ruim=False, calor=False, trabalho_estresse=False))
        n += 1
    s.commit()
    print(f"{n} treinos sinteticos gravados")
```
   Rode (na raiz): `uv run python - < /caminho/saida/carregar_treinos.py`. Esperado: `5 treinos sinteticos gravados`. Ids na ordem: 1 (Ana, dor), 2 (Bruno),
   3 (Carla, ciclismo de 6 dias atrás, **sem check-in e sem tipo**), 4 (Carla, corrida), 5 (o atleta **sem consentimento**, com dor).
5. **Subir a API e ler a caixa:**
   ```
   (cd services/api && CORS_ORIGENS=http://localhost:8084 uv run uvicorn app.main:app --port 8061)
   curl -s -i localhost:8061/professores/1/caixa-do-dia
   ```
   `CORS_ORIGENS` é a origem do Expo web do passo 7 (`http://localhost:8084`, a mesma porta): sem ela o navegador bloqueia o `GET` e a tela mostra "Não foi possível falar com o servidor". O `curl` não precisa dela. Esperado: `200`, `cache-control: no-store`, `versao` `atencao@1`, `hoje` com a data de hoje, `janela_atencao_dias` 7 e `janela_novos_dias` 14. Em `alunos[]`
   (a ordem é a da API; o app não reordena):
   - **Ana** (id 1), com o treino 1 e o motivo `dor`: "Treino de <dia> com dor marcada no check-in.";
   - **Carla** (id 5), com o treino 3 e o motivo `checkin_vencendo`: "Treino de <dia> sem check-in; o prazo termina em 1 dia." (6 dias atrás: restam
     `7 - 6 = 1`);
   - **Igor, Helena, Bruno e Davi** com `sem_motivo` `true` e a frase "Nada a destacar nos últimos 7 dias.";
   - o atleta **sem consentimento** e o **de outro professor não aparecem**, nem na lista nem nos novos, nem como erro.

   Em `novos[]` (o tipo sugerido a confirmar): o treino 2 (Bruno, `intervalado`), o 1 (Ana, `leve`) e o 4 (Carla, `moderado`), com `origem_texto`
   "sugerido pela regra". O treino 3 (sem tipo) não entra. A `observacao` só existe em `detalhe.checkin.observacao`.
   Os `404`: `curl -s -o /dev/null -w '%{http_code}\n' localhost:8061/professores/2/caixa-do-dia` e `.../professores/1/qualquer-coisa` dão `404`
   (o professor 2 existe no banco, mas não é o configurado: o corpo é o mesmo de um id sem linha).
6. **Confirmar e corrigir em lote:**
   ```
   curl -s -X PUT localhost:8061/professores/1/tipos-de-treino -H 'content-type: application/json' \
     -d '[{"atividade_id":2},{"atividade_id":4,"tipo_treino":"longo"}]'
   ```
   Esperado: `{"confirmados":1,"corrigidos":1}`. O treino 2 só foi **confirmado** (sem `tipo_treino` a API usa o atual: `tipo_confirmado` verdadeiro; origem
   `sugestao` fica) e o 4 foi **corrigido** para `longo` (origem `professor`, `tipo_versao` e divergência zerados, `tipo_confirmado_por` e `tipo_confirmado_em`
   preenchidos). Um `GET` de novo mostra em `novos[]` só o treino 1. Os erros, **todos sem gravar nada** (tudo ou nada):
   - `[{"atividade_id":5}]` (o treino do atleta sem consentimento): `404` `atividade_nao_encontrada`, o mesmo corpo de uma atividade que não existe;
   - `[]`: `422` (lote vazio); mais de 200 itens, `atividade_id` repetido ou tipo fora dos cinco também dão `422`;
   - `[{"atividade_id":3}]` (sem tipo para confirmar): `422` `atividade_sem_tipo`.

   Para ver o efeito no banco: `docker exec <projeto>-postgres-1 psql -U treino -d treino -c "select id, tipo_treino, tipo_origem, tipo_confirmado from atividade order by id"`.
   Esperado: a linha 2 `intervalado|sugestao|t`, a 4 `longo|professor|t` e as demais sem mudança. Repetir o mesmo `PUT` não muda nada e não renova o
   `tipo_confirmado_em`. O feedback de um treino cujo tipo foi corrigido fica `desatualizado` pelo motivo `tipo` ("O tipo do treino mudou depois deste
   feedback. O feedback será refeito."); este guia não gera feedback (é do `worker.gerar_feedback`, [[produto/meta-9-como-rodar]]).
7. **A tela** (rodada pela Bia na #429). Em `apps/mobile`, `npm ci` e, apontando para a API do passo 5:
   `CI=1 EXPO_PUBLIC_API_URL=http://localhost:8061 EXPO_PUBLIC_PROFESSOR_ID=1 npx expo start --web --port 8084`. A tela abre **só pelo endereço**
   `http://localhost:8084/caixa-do-dia` (o `/` continua sendo a home do atleta, sem link para a caixa). Se a tela mostrar "Não foi possível falar com o servidor", reinicie a API do passo 5 com `CORS_ORIGENS` igual à origem do Expo (esquema, host e porta). Sem `EXPO_PUBLIC_PROFESSOR_ID` a tela mostra
   "Caixa do dia não encontrada" sem chamar a API. O que ver: "Para olhar hoje" com um cartão por aluno com motivo, os alunos sem motivo em linha
   compacta, "Treinos novos" com a caixa de seleção, o botão "Mudar tipo" (folha "Tipo do treino") e a barra "N selecionados · N corrigidos" com "Salvar N tipos".
   Ao salvar, a tela anuncia "N treinos salvos: N confirmados e N corrigido." (números da resposta). Detalhe em [[modulos/mobile]] e na spec [[design/telas/caixa-do-dia]].
8. **Capturas por comando** (rodadas pela Bia na #429: 16 capturas das quatro telas). `npm run capturas` (em `apps/mobile`; `npx playwright install chromium-headless-shell` na
   primeira vez) usa a **API falsa** do app, com alunos "Atleta Fixture ...", e não o banco deste guia. Só as da caixa:
   `npm run capturas -- --so=caixa-do-dia,caixa-do-dia-selecao,caixa-do-dia-folha,caixa-do-dia-lote-salvo`. Saem em `apps/mobile/capturas/` (fora do git);
   as de referência estão em `docs/design/telas/caixa-do-dia/`.
9. **Os testes que não precisam de nada disso:** `uv run pytest tests/test_fixtures_meta11.py services/api/tests/metricas/test_atencao.py` (o oráculo dos
   quatro motivos, sem banco e sem rede) e `uv run pytest services/api/tests/rotas/test_caixa_do_dia.py services/api/tests/rotas/test_professor_tipos.py
   services/api/tests/rotas/test_professor_filtro.py` (a matriz rota x situação do filtro de vínculo e consentimento).
10. **Limpar.** Pare a API (Ctrl+C) e derrube o banco: `docker compose -p treino-meta11 -f infra/docker-compose.yml -f /caminho/saida/porta.yml down -v`.
    Isso apaga o volume `<projeto>_pgdata` (aqui `treino-meta11_pgdata`); nada do banco do dia a dia é tocado.

## Limitações da conferência local (#431)
A conferência local da caixa do dia (#431) foi feita só na máquina do Angelo, com nada no repositório. Em texto genérico (sem data, nome, número nem tipo de atividade de nenhum aluno):
1. **`fora_do_normal` depende da `linha_base@2`.** Com poucas amostras do tipo, ou com dispersão muito pequena, o `z` pode sair grande, e o limite de 2,5 não mede relevância esportiva. Investigação na #455.
2. **A regra só enxerga o que foi ingerido.** Sem treinos novos, a lista fica parada.
3. **`dor` e `divergencia` só têm teste sintético.** A conferência local não os exercitou.
4. **A regra de divergência fica como está até 4 semanas de uso.**

Resolvidas na `atencao@2` (#454): a modalidade `outra` saiu do aviso `checkin_vencendo`, e quem tem poucos check-ins agora recebe **uma linha por aluno** (preso ao treino mais antigo), não um aviso por treino. Um treino ainda diz "Treino de <dia> sem check-in; o prazo termina em N dia(s)."; vários dizem "N treinos sem check-in; o prazo do mais antigo termina hoje.". Mesma lista, junto da regra, em [[metricas/atencao]].

## Achados do guia
- **O `carregar_professor` só grava identidade.** Não existe comando que carregue os treinos de `tests/fixtures/meta11/treinos.json`: aquele arquivo é a
  **entrada da `atencao@2`** no oráculo, não linhas do banco. Por isso o passo 4 usa um script próprio (`carregar_treinos.py`). Um comando de carga dos treinos
  da Meta 11 seria uma issue à parte.
- **Só `dor` e `checkin_vencendo` aparecem pelo banco sintético deste guia.** `fora_do_normal` exige a linha de base (8 treinos do mesmo tipo) e
  `divergencia`, a semana-padrão do atleta; o oráculo cobre os quatro.
- **O passo 7 falhava sem `CORS_ORIGENS` (#449, achado da QA #429).** A API só libera `http://localhost:8081` por padrão; a tela em outra porta fica bloqueada pelo navegador. O passo 5 agora sobe a API com a origem do Expo, como os guias das Metas 9 e 10. iOS e Android não precisam de CORS.
- **A API falsa do app não é o banco.** A tela e as capturas do passo 8 usam a API falsa; o passo 7 aponta o app para a API de verdade.
