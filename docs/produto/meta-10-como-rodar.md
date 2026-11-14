---
tipo: guia
status: em-uso
dono: nina
atualizado: 2026-11-14
links: [[produto/meta-9-como-rodar]], [[produto/meta-8-como-rodar]], [[produto/roadmap]], [[decisoes/0014-recuperacao-diaria]], [[decisoes/0013-feedback-automatico]], [[metricas/recuperacao]], [[metricas/recuperacao-oraculo]], [[metricas/fatos-treino]], [[metricas/fatos-treino-oraculo]], [[metricas/checagens-feedback]], [[modulos/banco]], [[modulos/worker]], [[modulos/api]], [[modulos/camada-llm]], [[modulos/ingestao-garmin]], [[diario/2026-11-13]], [[glossario]]
---
# Meta 10: como rodar a recuperação da noite no feedback

Passo a passo da Meta 10 com as fixtures: Postgres próprio, migrações até a 0014, as 18 atividades sintéticas da Meta 8 com check-in,
as noites sintéticas de recuperação (`recuperacao_dia`), o pacote `fatos_treino@2` com o bloco `recuperacao`, o `worker.gerar_feedback`
com o **provedor falso**, o feedback refeito quando a noite chega, a busca com o **cliente Garmin falso** e o `worker.apagar_recuperacao`.
**Só dado sintético, sem rede e sem conta do Garmin.** As regras estão na [[decisoes/0014-recuperacao-diaria]], aceita em 12/11.
**Sono, VFC, FC de repouso, check-in e feedback são dado de saúde:** use só os valores sintéticos daqui e das fixtures.

**Situação da verificação (#377, Nina, 13/11):** os passos 1 a 10 foram rodados de verdade num clone limpo do `main` (`616d0c0`, depois do
#391), com o banco `treino-meta10` (Postgres na 5457, API na 8060). Os números abaixo são os que saíram. Banco e API foram derrubados no fim
e nada usou a rede. **Não rodado aqui:**
- o app (o cartão "Feedback" em tela e a tela do treino): conferência visual no Chrome em tamanho de celular é a #369; o celular de
  verdade segue pendente, sem data;
- o **provedor de verdade** com a recuperação no prompt (`feedback_prompt@5`): a rodada da #376 (Caio, 13/11, só fixtures) está na
  seção "Rodada com o provedor de verdade, Meta 10" de [[modulos/camada-llm]] (PR #393).
  **Hoje o provedor de verdade com a recuperação não fecha** sem os ajustes propostos lá: a linha com as três medidas passa de 140
  caracteres, e a camada não fecha no limite por minuto do plano gratuito. Este guia não repete a rodada;
- a busca com **conta real** do Garmin (`worker.buscar_recuperacao` sem `--fixtures`): passo 11, opcional e só local;
- a conferência local (#379), a QA (#378) e o resultado da meta (#380).

## Antes de começar
- As mesmas ferramentas e cuidados do [[produto/meta-8-como-rodar]] ("Antes de começar") e do [[produto/meta-9-como-rodar]]: comandos na
  **raiz** do repositório, pasta de trabalho fora do git (abaixo, `/caminho/saida`), portas livres.
- **Não use o banco do seu dia a dia** (porta 5433) nem as portas 8000 e 8081. Rode sempre com `-p treino-meta10`. Abaixo: 5457
  (Postgres) e 8060 (API).
- **Qual `.env` vale:** só o da **raiz do repositório** (de qualquer pasta de onde o comando rode; variável de ambiente vale mais que
  o arquivo). Numa worktree a raiz é a da worktree, que não tem `.env`. Este guia não precisa de `.env`: o provedor falso vem de
  `LLM_PROVIDER=falso` e a `DATABASE_URL` vai no ambiente.
- **O relógio importa**, como na Meta 8: o `carregar.py` desloca as datas das fixtures para "hoje". Rodado em 13/11, imprimiu
  `deslocamento 4 dias`. As noites do passo 6 são escritas em torno do dia do treino 18, então não dependem do relógio.
- **Quem gera o feedback é só o `worker.gerar_feedback`.** Salvar o check-in ou gravar noites não chama o provedor.

## Passo a passo
1. **Subir o Postgres.** Salve `/caminho/saida/porta.yml` com
   ```
   services:
     postgres:
       ports: !override
         - "5457:5432"
   ```
   e rode:
   ```
   docker compose -p treino-meta10 -f infra/docker-compose.yml -f /caminho/saida/porta.yml up -d
   export DATABASE_URL="postgresql+psycopg://treino:treino@localhost:5457/treino"
   ```
   Esperado: `treino-meta10-postgres-1` `healthy`.
2. **Instalar e migrar:**
   ```
   uv sync
   (cd services/api && uv run alembic upgrade head && uv run alembic current)
   ```
   Esperado: catorze linhas `Running upgrade` e `0014 (head)`. A `0014` cria `recuperacao_dia` e a coluna
   `feedback_treino.recuperacao_importada_em` ([[modulos/banco]]).
3. **Carregar as 18 atividades sintéticas.** Use o `carregar.py` do passo 3 do [[produto/meta-8-como-rodar]], sem mudar nada:
   `uv run python - < /caminho/saida/carregar.py`. Esperado: `atleta 1: 18 atividades, 1 check-in, deslocamento N dias`. A tabela
   de ids é a mesma daquele guia (a 18 é a corrida de 45 min do dia 09/11 da fixture, deslocada para o seu "hoje").
4. **Subir a API com o provedor falso**, em outro terminal, com a mesma `DATABASE_URL`:
   ```
   LLM_PROVIDER=falso CORS_ORIGENS=http://localhost:8083 FIT_DIR="$(mktemp -d)" uv run uvicorn app.main:app --app-dir services/api --port 8060
   ```
   Confira: `curl -s localhost:8060/health` dá `{"status":"ok"}`.
5. **Registrar os outros oito check-ins pela API** e **gerar o feedback sem nenhuma noite** (o atleta ainda não tem recuperação):
   ```
   API=http://localhost:8060 uv run python - < /caminho/saida/gravar_checkins.py
   LLM_PROVIDER=falso uv run python -m worker.gerar_feedback --atleta "Atleta Fictício"
   ```
   O `gravar_checkins.py` é o do passo 5 do [[produto/meta-8-como-rodar]]. Esperado: oito linhas com `200` e, do worker,
   `feedback: gerados=8 sem_feedback=1 ignorados=0 adiados=0 erros=0` com `motivos: texto_reprovado=1` e `reprovacoes: dor_regra=1`
   (a atividade 8 tem o atalho Dor e o texto fixo do provedor falso não traz a frase da dor, como na Meta 9).
   Salve `/caminho/saida/pacote.py` para ver o **bloco `recuperacao` do pacote** (só o bloco, nunca o texto livre):
   ```python
   import json

   from app.db.models import Atividade
   from app.db.session import SessionLocal
   from app.servicos.feedback_fatos import fatos_da_atividade
   from sqlalchemy import select

   with SessionLocal() as s:
       a = s.scalars(select(Atividade).where(Atividade.fonte_id == "2026-11-09/cor2")).one()
       pacote = fatos_da_atividade(s, a, a.checkin)
       print(pacote["versao"])
       print(json.dumps(pacote["recuperacao"], ensure_ascii=False, indent=1))
   ```
   Rode `uv run python - < /caminho/saida/pacote.py`. Esperado: `fatos_treino@2` e um bloco com `versao` `recuperacao@1`,
   `estado` `sem_dado` e `motivo` `sem_noite`. Atleta sem nenhuma noite **não quebra o feedback**: o bloco existe e diz que não há dado
   ([[metricas/fatos-treino]]). No banco, `recuperacao_importada_em` está vazio nos nove feedbacks:
   `docker exec treino-meta10-postgres-1 psql -U treino -d treino -At -c "select count(*) filter (where recuperacao_importada_em is not null), count(*) from feedback_treino"` dá `0|9`.
6. **Carregar as noites sintéticas.** São as 14 noites de normal e a noite do treino do caso R01 do oráculo à mão
   (`tests/fixtures/meta10/oraculo_fatos_recuperacao.py`), escritas como respostas do sono em `tests/fixtures/meta10/noites_r01/`. O
   `worker.buscar_recuperacao --fixtures` lê essa pasta com o leitor de verdade (`ler_noite`), **sem rede, sem login e sem token**, e leva a
   última noite para o dia do treino 18 (`--alinhar-ao-treino`), então as datas acompanham o relógio do passo 3:
   ```
   uv run python -m worker.buscar_recuperacao --atleta "Atleta Fictício" --fixtures tests/fixtures/meta10/noites_r01 --alinhar-ao-treino 2026-11-09/cor2
   ```
   Esperado: `recuperacao: noites_novas=15 atualizadas=0 iguais=0 sem_dado=0 falhas=0` e, rodando de novo, `noites_novas=0 atualizadas=0 iguais=15`
   (idempotente). As noites ficam com `versao_leitura` `fixture`, e o comando **recusa** (código 1) um atleta que já tem noites que não são de
   fixture, para nunca misturar dado sintético com dado real. Rode o `pacote.py` de novo. Esperado: o bloco da
   atividade 18 com `estado` `ok`, `janela_noites` 28, `minimo_noites` 14 e três medidas, nesta ordem:
   - `sono` `abaixo`: valor "5 h 45 min", normal "7 h 15 min", diferença "1 h 30 min abaixo", `n` 14;
   - `vfc` `dentro`: valor "41 ms", normal "47 ms", sem diferença, `n` 14;
   - `fc_repouso` `acima`: valor "58 bpm", normal "52 bpm", diferença "6 bpm acima", `n` 14.
   Mudando o `fonte_id` do `pacote.py`, vê-se os outros estados: `2026-11-07/cor1` (dois dias antes) tem as três medidas
   `aprendendo` com `n` 12 (menos de 14 noites), e `2026-10-15/cor1` (antes da primeira noite gravada) dá `sem_dado` com `fora_do_periodo`.
7. **O feedback é refeito quando a noite chega** (ADR 0014, item 4b). Sem rodar o worker ainda:
   ```
   for i in 1 8 18; do curl -s localhost:8060/atletas/1/atividades/$i | python3 -c "import json,sys; f=json.load(sys.stdin)['feedback']; print($i, f['estado'], f['motivo'])"; done
   ```
   Esperado: `1 pronto None` (o treino de 15/10 fica antes da primeira noite: `fora_do_periodo` vale nulo dos dois lados e não desatualiza),
   `8 indisponivel texto_reprovado` e `18 desatualizado None`. As outras seis com noite na janela (6, 13, 14, 15, 16 e 17) também ficam
   `desatualizado`. Depois rode duas vezes:
   ```
   LLM_PROVIDER=falso uv run python -m worker.gerar_feedback --atleta "Atleta Fictício"
   LLM_PROVIDER=falso uv run python -m worker.gerar_feedback --atleta "Atleta Fictício"
   ```
   Esperado, nesta ordem:
   - `gerados=7 sem_feedback=1 ignorados=1 adiados=0 erros=0` (sete refeitos: a 18 e as outras seis, o reprovado tentado de novo, o de 15/10 em dia);
   - `gerados=0 sem_feedback=1 ignorados=8 adiados=0 erros=0` (idempotente: sem mudança nova não há chamada).
   No banco: `select estado, motivo, recuperacao_importada_em is not null, count(*), max(tentativas) from feedback_treino group by 1,2,3 order by 1`
   dá `pronto||f|1|1`, `pronto||t|7|2` e `sem_feedback|texto_reprovado|t|1|3`. Noite que chega **soma 1 em `tentativas`** (só ordena a fila, não
   barra o treino). O worker lê as noites do atleta **uma vez** por execução.
   **O que este passo não mostra:** o texto fixo do provedor falso não fala de sono, então o `GET` e o cartão não ganham uma linha de
   recuperação aqui. A linha da recuperação no texto só aparece com o provedor de verdade e o `feedback_prompt@5`, e hoje o texto com as três medidas reprova por tamanho (rodada da #376).
8. **Sem dado, sem recuperação no texto.** As `checagens_feedback@4` barram o texto que fala de sono, VFC ou FC de repouso quando o bloco é
   `sem_dado` (a frase pronta só passa em `sem_dado` com `sem_noite`) e usam cinco códigos novos de motivo
   ([[metricas/checagens-feedback]]). Texto reprovado nunca é gravado. Rodar isso à mão exige o provedor de verdade, e hoje ele não fecha com a recuperação (a rodada e os ajustes propostos estão na seção da
   [[modulos/camada-llm]], citada no começo); sem ele, a conferência é o conjunto de frases de teste do passo 12 (6 boas e 25 ruins, cada ruim com o motivo esperado).
9. **Busca com o cliente Garmin falso** (sem rede e sem conta; as respostas são as fixtures de `tests/fixtures/meta10`). O
   `--fixtures` passa as respostas sintéticas do sono pelo leitor de verdade (`ler_noite`); as de março de 2026 são as noites 10 a 13 (as
   outras fixtures da pasta, de faixa, não são respostas do sono e são ignoradas). Rode duas vezes:
   ```
   uv run python -m worker.buscar_recuperacao --atleta "Atleta Fictício" --fixtures tests/fixtures/meta10 --desde 2026-03-10 --ate 2026-03-13
   ```
   Esperado: `recuperacao: noites_novas=4 atualizadas=0 iguais=0 sem_dado=0 falhas=0` e, na segunda vez, `noites_novas=0 atualizadas=0 iguais=4`
   (idempotente). A saída é só de contagens, nunca valores nem datas. Em seguida o `gerar_feedback` dá `gerados=0 ... ignorados=8`: essas
   noites estão fora da janela de todos os treinos, e nenhum feedback é refeito à toa.
10. **`worker.apagar_recuperacao`** (LGPD; [[modulos/worker]]):
    ```
    uv run python -m worker.apagar_recuperacao --atleta "Atleta Fictício"
    ```
    Esperado: `recuperacao: apagadas=19` (as 15 do passo 6 e as 4 do passo 9) e `feedbacks: apagados=8` (os que usaram a recuperação, porque o
    texto pode trazer os valores da noite). O feedback do treino de 15/10, sem recuperação, fica. Rodando de novo: `apagadas=0` e
    `apagados=0`. No banco, `select (select count(*) from recuperacao_dia), (select count(*) from feedback_treino), (select count(*) from checkin_treino), (select count(*) from atividade)`
    dá `0|1|9|18`: check-ins e atividades ficam. O `GET` da atividade 18 volta a `pendente`; o `gerar_feedback` refaz os sete sem recuperação
    (`gerados=7`).
11. **Busca com conta real do Garmin** (opcional; **entra numa conta real**, só no computador do próprio atleta; não faz parte da
    verificação com fixtures). Com o token ou `GARMIN_EMAIL` e `GARMIN_PASSWORD` no `.env` da raiz:
    `uv run python -m worker.buscar_recuperacao --atleta "<nome>" [--desde AAAA-MM-DD] [--ate AAAA-MM-DD]`.
    Usa a mesma biblioteca não oficial e o mesmo token do `worker.buscar_garmin`: **um login, não rode os dois juntos**. A primeira
    rodada faz cerca de 130 chamadas com pausa de 1,5 s (uns minutos); o teto é de 130 chamadas por execução, e um 429 do Garmin para a
    execução e guarda o que já veio. A saída tem **só contagens** (`recuperacao: noites_novas=a atualizadas=b iguais=c sem_dado=d falhas=e`
    e `aviso: rebuscadas=N`); não cole valores, datas de noite nem a quantidade de noites que vieram em issue, PR, nota nem captura.
    O dado fica só no banco local ([[modulos/worker]], [[modulos/ingestao-garmin]], [[decisoes/0014-recuperacao-diaria]]).
12. **Testes da meta.** Na raiz, sem a `DATABASE_URL`:
    `uv run pytest -q tests/test_fixtures_meta10.py services/api/tests/metricas/test_recuperacao.py services/api/tests/explicacao services/api/tests/llm services/api/tests/servicos/test_recuperacao_pacote.py services/api/tests/servicos/test_recuperacao_banco.py services/worker/tests/test_buscar_recuperacao.py services/worker/tests/test_apagar_recuperacao.py services/worker/tests/test_gerar_feedback.py`.
    Rodado em 13/11 no `616d0c0`, todos passaram. Não fixe a contagem aqui: ela muda a cada meta. O oráculo do bloco `recuperacao`
    é `tests/fixtures/meta10/oraculo_fatos_recuperacao.py` ([[metricas/fatos-treino-oraculo]], [[metricas/recuperacao-oraculo]]) e os textos das
    checagens, `tests/fixtures/meta10/textos_recuperacao.py`.

## Derrubar tudo
```
docker compose -p treino-meta10 -f infra/docker-compose.yml -f /caminho/saida/porta.yml down -v
```
e pare a API (Ctrl+C no terminal do passo 4). Isso apaga o banco `treino-meta10` e o volume; o seu banco do dia a dia não é tocado.

## Achados do guia
- **Sem comando para carregar as fixtures de recuperação (resolvido na #397).** Os passos 6 e 9 usavam trechos em Python; agora são o `worker.buscar_recuperacao --fixtures`. Os passos 6 a 10 foram rodados de verdade com ele (14/11, Duda, Postgres temporário na 5463, derrubado no fim) e deram os mesmos números.
- **A mensagem do `GET` não diz que foi a noite.** Quando a noite chega e o feedback fica `desatualizado`, o `mensagem` é a mesma da
  edição do check-in: "Você editou o check-in. O feedback será refeito.". Está certo no estado, mas o texto fala de uma ação que o atleta
  não fez.
- **O provedor falso não exercita a linha de recuperação.** O texto fixo não cita a noite; só o provedor de verdade mostra o texto, e a rodada da #376 mostrou que ele ainda reprova por tamanho com as três medidas.
