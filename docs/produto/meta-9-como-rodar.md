---
tipo: guia
status: em-uso
dono: nina
atualizado: 2026-11-11
links: [[produto/meta-8-como-rodar]], [[produto/roadmap]], [[decisoes/0013-feedback-automatico]], [[decisoes/0012-check-in-pos-treino]], [[decisoes/0004-contrato-tela-evolucao]], [[metricas/fatos-treino]], [[metricas/fatos-treino-oraculo]], [[metricas/checagens-feedback]], [[design/telas/feedback]], [[modulos/camada-llm]], [[modulos/banco]], [[modulos/api]], [[modulos/mobile]], [[modulos/worker]], [[modulos/ingestao-garmin]]
---
# Meta 9: como rodar o feedback automático por treino

Passo a passo da Meta 9 com as fixtures: Postgres próprio, migrações até a 0013, as 18 atividades sintéticas da Meta 8 com
check-in, o `worker.gerar_feedback` com o **provedor falso**, o campo `feedback` no `GET` da atividade em cada estado e o cartão
"Feedback" no app. **Só dado sintético, sem rede e sem provedor de verdade.** As regras estão na
[[decisoes/0013-feedback-automatico]], aceita em 10/11 (PR #345). **Check-in e feedback são dado de saúde:** use só estes valores
sintéticos.

**Situação da verificação (#331, Theo, 11/11):** os passos 1 a 9 e o 12 foram rodados de verdade num clone limpo do `main`
(`87a9049`, depois do #352), com o banco `treino-meta9` (Postgres na 5456, API na 8059). Os números abaixo são os que saíram.
Banco e API foram derrubados no fim e nada usou a rede. **Não rodado aqui:** o app (passos 10 e 11; ficam para a QA, #332), o
provedor de verdade (passo 13) e o `worker.buscar_garmin` (passo 14, que entra numa conta real).

## Antes de começar
- As mesmas ferramentas e cuidados do [[produto/meta-8-como-rodar]] ("Antes de começar"): comandos na **raiz** do repositório,
  pasta de trabalho fora do git (abaixo, `/caminho/saida`), portas livres.
- **Não use o banco do seu dia a dia** (porta 5433) nem as portas 8000 e 8081. Rode sempre com `-p treino-meta9`. Abaixo: 5456
  (Postgres), 8059 (API), 8056 (API falsa) e 8083 (app web).
- **O relógio importa**, como na Meta 8: o `carregar.py` desloca as datas das fixtures para "hoje". Rodado em 11/11, imprimiu
  `deslocamento 2 dias`.
- **Quem gera o feedback é só o `worker.gerar_feedback`.** Salvar o check-in não chama o provedor: o treino fica `pendente` até
  o comando rodar ([[decisoes/0013-feedback-automatico]], item 9 de "A confirmar", aceito para o piloto local).

## Passo a passo
1. **Subir o Postgres.** Como no passo 1 do [[produto/meta-8-como-rodar]], trocando o projeto e a porta: `porta.yml` com
   `"5456:5432"` e
   ```
   docker compose -p treino-meta9 -f infra/docker-compose.yml -f /caminho/saida/porta.yml up -d
   export DATABASE_URL="postgresql+psycopg://treino:treino@localhost:5456/treino"
   ```
2. **Instalar e migrar:**
   ```
   uv sync
   (cd services/api && uv run alembic upgrade head && uv run alembic current)
   ```
   Esperado: treze linhas `Running upgrade` e `0013 (head)`. A `0013` cria `feedback_treino` ([[modulos/banco]]).
3. **Carregar as 18 atividades sintéticas.** Use o `carregar.py` do passo 3 do [[produto/meta-8-como-rodar]], sem mudar nada:
   `uv run python - < /caminho/saida/carregar.py`. Esperado: `atleta 1: 18 atividades, 1 check-in, deslocamento N dias`. A tabela
   de ids é a mesma daquele guia.
4. **Subir a API com o provedor falso**, em outro terminal, com a mesma `DATABASE_URL`:
   ```
   LLM_PROVIDER=falso CORS_ORIGENS=http://localhost:8083 FIT_DIR="$(mktemp -d)" uv run uvicorn app.main:app --app-dir services/api --port 8059
   ```
   Confira: `curl -s localhost:8059/health` dá `{"status":"ok"}`. A API **nunca** chama o provedor; a variável aqui só mantém
   o terminal igual ao do worker.
5. **Registrar os outros oito check-ins pela API.** Use o `gravar_checkins.py` do passo 5 do [[produto/meta-8-como-rodar]]:
   `API=http://localhost:8059 uv run python - < /caminho/saida/gravar_checkins.py`. Esperado: oito linhas com `200`, nas
   atividades 17, 18, 15, 16, 14, 13, 6 e 8. Com a de 15/10, são 9 check-ins.
6. **O `feedback` antes do worker** ([[modulos/api]]; adendo 10 da [[decisoes/0004-contrato-tela-evolucao]]):
   ```
   for i in 18 12 2 5; do curl -s localhost:8059/atletas/1/atividades/$i | python3 -c "import json,sys; print($i, json.load(sys.stdin)['feedback'])"; done
   ```
   Esperado:
   - 18 (com check-in): `estado` `pendente`, `mensagem` "O feedback deste treino ainda não foi gerado. Toque em Atualizar para
     ver se já está pronto.";
   - 12 (sem check-in, no prazo): `sem_checkin`, `checkin_aberto` `true`, "Faça o check-in para ver o feedback.";
   - 2 (fora do prazo): `sem_checkin`, `checkin_aberto` `false`, "O prazo do check-in deste treino acabou, então ele fica sem
     feedback.";
   - 5 (`multiesporte_pai`): `None` (o campo vem nulo e o app não mostra o cartão).
   Em todos, `texto`, `origem` e `motivo` vêm nulos fora do estado que os usa.
7. **Sem provedor configurado.** Na raiz, com a mesma `DATABASE_URL`:
   ```
   (cd services/worker && LLM_PROVIDER= LLM_MODEL= uv run python -m worker.gerar_feedback --atleta "Atleta Fictício")
   ```
   Esperado: `aviso: provedor de LLM nao configurado (LLM_PROVIDER, LLM_MODEL e a chave no .env)`,
   `feedback: gerados=0 sem_feedback=9 ignorados=0 adiados=0 erros=0` e `motivos: provedor_nao_configurado=9`, saída 0. O `GET`
   da atividade 18 passa a `estado` `indisponivel`, `motivo` `provedor_nao_configurado`, `mensagem` "O feedback automático não
   está ligado neste app.". O comando imprime só contagens e códigos, nunca texto nem pacote ([[modulos/worker]]).
8. **Gerar com o provedor falso, em duas rodadas** (o limite de chamadas é por execução):
   ```
   cd services/worker
   LLM_PROVIDER=falso uv run python -m worker.gerar_feedback --atleta "Atleta Fictício" --limite 3
   LLM_PROVIDER=falso uv run python -m worker.gerar_feedback --atleta "Atleta Fictício"
   LLM_PROVIDER=falso uv run python -m worker.gerar_feedback --atleta "Atleta Fictício"
   ```
   Esperado, nesta ordem:
   - `gerados=3 sem_feedback=0 ignorados=0 adiados=6 erros=0` (três chamadas; o resto fica para a próxima);
   - `gerados=5 sem_feedback=1 ignorados=3 adiados=0 erros=0`, `motivos: texto_reprovado=1`, `reprovacoes: dor_regra=1`;
   - `gerados=0 sem_feedback=1 ignorados=8 adiados=0 erros=0` com a mesma reprovação (idempotente: o que está pronto e em dia
     não gasta chamada; o reprovado é tentado de novo a cada execução).

   A reprovação é a atividade 8, cujo check-in tem o atalho **Dor**: o texto fixo do provedor falso não traz a frase neutra da
   dor, então as checagens o barram ([[metricas/checagens-feedback]]). É o comportamento certo: **texto reprovado nunca é
   gravado nem chega ao app**. No `GET`:
   - atividades 1, 6, 13 a 18: `estado` `pronto`, `origem` `teste`, `texto` "Treino de teste do provedor falso.\nEsta linha
     existe so nos testes.\nNenhum dado real passa por aqui.";
   - atividade 8: `indisponivel`, `motivo` `texto_reprovado`, "Ainda não foi possível gerar o feedback deste treino. Uma nova
     tentativa será feita mais tarde.".
   No banco: `docker exec treino-meta9-postgres-1 psql -U treino -d treino -At -c "select estado, motivo, count(*) from feedback_treino group by 1,2 order by 1"`
   dá `pronto||8` e `sem_feedback|texto_reprovado|1` (a linha reprovada guarda só o código do motivo).
9. **Editar e apagar o check-in** (o feedback acompanha):
   ```
   H='content-type: application/json'
   curl -s -o /dev/null -w '%{http_code}\n' -X PUT -H "$H" localhost:8059/atletas/1/atividades/18/checkin -d '{"pse":6,"sensacao":3,"nada_a_relatar":true,"atalhos":[]}'
   curl -s localhost:8059/atletas/1/atividades/18 | python3 -c "import json,sys; print(json.load(sys.stdin)['feedback'])"
   ```
   Esperado: `200` e `estado` `desatualizado`, `texto` **nulo** (o texto antigo não é devolvido), "Você editou o check-in. O
   feedback será refeito.". Rode o `gerar_feedback` de novo: `gerados=1 ...` e a atividade 18 volta a `pronto`.
   `curl -s -o /dev/null -w '%{http_code}\n' -X DELETE localhost:8059/atletas/1/atividades/17/checkin` dá `204`, e o `GET` da 17
   volta a `sem_checkin` com `checkin_aberto` `true`: apagar o check-in apaga o feedback (cascata no banco).
   `--refazer` refaz também o que está pronto, ainda dentro do limite: com `--refazer --limite 2`, `gerados=2 ... adiados=6`.
10. **O cartão no app web** (não rodado nesta verificação). Como no passo 11 do [[produto/meta-8-como-rodar]], apontando para a
    API do passo 4: em `apps/mobile`, `npm ci` e
    `CI=1 EXPO_PUBLIC_API_URL=http://localhost:8059 EXPO_PUBLIC_ATLETA_ID=1 npx expo start --web --port 8083`. Em `/treino/18` o
    cartão "Feedback" aparece entre "Check-in" e "Carga pela PSE", com o selo "Texto de teste"; em `/treino/12`, "Faça o check-in
    para ver o feedback." e o botão "Fazer check-in"; em `/treino/8`, a frase do indisponível; em `/treino/5`, sem cartão. Nos
    estados pendente e desatualizado o botão "Atualizar" busca a atividade de novo ([[design/telas/feedback]], [[modulos/mobile]]).
11. **Estados forçados com a API falsa** (não rodado nesta verificação). `node scripts/api-falsa.mjs 8056` em `apps/mobile` e o
    app com `EXPO_PUBLIC_API_URL=http://localhost:8056 EXPO_PUBLIC_ATLETA_ID=1`. Atividades: `107` pronto, `111` pronto de teste,
    `112` pendente, `113` desatualizado, `114` indisponível, `115` indisponível sem provedor, `101` e `106` sem check-in no
    prazo, `108` prazo vencido, `110` sem cartão ([[modulos/mobile]]).
12. **`worker.apagar_checkin`** (LGPD; [[modulos/worker]]):
    ```
    uv run python -m worker.apagar_checkin --atleta "Atleta Fictício"
    ```
    Esperado: `checkins: apagados=8` e `feedbacks: apagados=8` (os números são os que existem na hora; aqui, depois do `DELETE`
    do passo 9), e `0|0` em
    `select (select count(*) from checkin_treino), (select count(*) from feedback_treino)`. As atividades e o atleta ficam.
13. **Provedor de verdade** (não rodado nesta verificação; **só com fixtures**, a menos que o atleta autorize o dado dele). No
    `.env`: `LLM_PROVIDER=groq`, `LLM_MODEL=<modelo da sua conta>` e `GROQ_API_KEY=<chave>`; rode o `gerar_feedback` com
    `--limite` pequeno. Ao provedor vai **só o pacote de fatos** ([[metricas/fatos-treino]]): nunca o texto livre da observação,
    nome, data real, posição ou identificador. O que foi e o que **não** foi conferido sobre retenção de dados no provedor está
    no item 10 de "A confirmar" da [[decisoes/0013-feedback-automatico]]; leia antes de mandar dado real. Erro, tempo limite e
    limite de requisições do provedor viram `sem_feedback` com o motivo e entram na próxima execução ([[modulos/camada-llm]]).
14. **`worker.buscar_garmin`** (opcional; **entra numa conta real do Garmin Connect**, só no computador do próprio atleta; não
    faz parte da verificação com fixtures). Com `GARMIN_EMAIL` e `GARMIN_PASSWORD` no `.env` local:
    `(cd services/worker && uv run python -m worker.buscar_garmin --atleta "<nome>")`. Busca as atividades de hoje (ou
    `--desde`/`--ate`), baixa o FIT original das que ainda não estão no banco e usa o mesmo caminho do upload. Token e ids já
    importados ficam em `dados-garmin/`, fora do git. Rode da raiz do repositório principal ou com `FIT_DIR` e `GARMINTOKENS`
    absolutos. A biblioteca não é oficial e pode parar de funcionar quando o Garmin mudar o login ([[modulos/ingestao-garmin]]).
15. **Testes da meta.** Na raiz, sem a `DATABASE_URL`:
    `uv run pytest -q tests/test_fixtures_meta9.py tests/test_textos_meta9.py services/api/tests/explicacao services/api/tests/llm services/api/tests/servicos/test_feedback_fatos.py services/api/tests/rotas/test_atividade_feedback.py services/worker/tests/test_gerar_feedback.py`.
    Em `apps/mobile`: `npx jest __tests__/CartaoFeedback.test.tsx`. Esperado no primeiro comando: `528 passed` (rodado em 11/11 no `87a9049`). O do app entra aqui quando a QA (#332) rodar.

## Encerrar e limpar
- `Ctrl+C` na API (e no `expo start` e na API falsa, se subiram); apague a pasta de `FIT_DIR` e a `/caminho/saida`.
- `docker compose -p treino-meta9 -f infra/docker-compose.yml -f /caminho/saida/porta.yml down -v` e confira com `docker ps`.
- Se rodou o app: `git checkout apps/mobile/tsconfig.json`.

## Problemas comuns
- Os do [[produto/meta-8-como-rodar]] (porta ocupada, CORS, relógio, banco errado, aviso do `VIRTUAL_ENV`) valem aqui.
- **O cartão fica em "ainda não foi gerado":** ninguém rodou o `worker.gerar_feedback` depois do check-in. É assim no piloto local.
- **`sem_feedback` com `provedor_nao_configurado`:** falta `LLM_PROVIDER`, `LLM_MODEL` ou a chave no ambiente do **worker** (a
  API não precisa deles).
- **Um treino sempre reprova com o provedor falso:** o check-in tem o atalho Dor (passo 8). Com o provedor de verdade, veja o
  código em `reprovacoes:` e a lista em [[metricas/checagens-feedback]].
- **`gerar_feedback` trava ou falha esperando o banco:** outra sessão está com transação aberta; os testes usam
  `lock_timeout` de 60 s no Postgres para falhar em vez de travar.

## Fora ou depois (pendências conhecidas)
- **App em celular** (check-in da Meta 8 e o cartão de feedback): na QA (#332), com o Angelo, numa só sessão. O anúncio do
  "Atualizar" ao leitor de tela não foi conferido em leitor de tela de verdade.
- **Feedback gerado na hora do check-in:** fora da meta; hoje só o comando gera.
- **Sono, VFC, estado de treino e treinos planejados do Garmin Connect:** candidatos a meta futura ([[produto/roadmap]]).
