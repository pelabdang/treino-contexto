---
tipo: guia
status: em-uso
dono: nina
atualizado: 2026-11-17
links: [[produto/meta-11-como-rodar]], [[produto/meta-7-como-rodar]], [[produto/meta-6-como-rodar]], [[produto/roadmap]], [[decisoes/0004-contrato-tela-evolucao]], [[decisoes/0011-linha-de-base-e-semana-padrao]], [[decisoes/0009-treino-de-transicao]], [[decisoes/0010-carga-de-treino]], [[decisoes/0013-feedback-automatico]], [[metricas/linha-base]], [[metricas/tipo-linha-base-oraculo]], [[metricas/carga-treino]], [[metricas/serie-carga]], [[metricas/transicao]], [[design/telas/treino]], [[modulos/api]], [[modulos/mobile]], [[glossario]]
---
# Meta 12: como rodar o treino inteiro na tela do atleta

Passo a passo da Meta 12 com dado sintético: Postgres próprio, migrações até a 0016, as 81 atividades fictícias da Meta 7 (12 semanas), o `GET` da
atividade com os blocos novos (`linha_base@3`, textos da carga, `forma_do_dia`, `transicao.editavel`), a correção do rótulo de transição e a tela do treino com
os cartões **Esforços**, **Comparado com o seu normal**, **Carga e forma do dia** e **Treino de transição**. **Só dado sintético, sem rede, sem conta do
Garmin e nunca o banco real.** A spec está em [[design/telas/treino]] (seção "Meta 12"); o contrato, no adendo 12 da [[decisoes/0004-contrato-tela-evolucao]].
**Linha de base, carga, esforços, check-in e feedback são dado de saúde:** use só os valores sintéticos daqui e das fixtures.

**Situação da verificação (#468, Nina, 17/11):** os passos 1 a 7 foram rodados de verdade num clone de trabalho do `main` (`e776191`, com as #479 a #485),
com o banco `treino-meta12` (Postgres na 5471, API na 8071). Os números abaixo são os que saíram. O banco e a API foram derrubados no fim e nada usou a rede.
**Não rodado aqui:**
- a **tela contra a API de verdade** (Expo web apontando para o banco do passo 1): o passo 8 usa as capturas por comando, que rodam sobre a **API falsa** do app
  (12 capturas rodadas, de 3 telas, em claro e escuro, 390 e 1280); a Bia roda a tela viva na QA (#469);
- o **`sem_carga` com motivo** e a carga `pendente` com a série cheia pelo banco: as fixtures da Meta 7 só gravam carga em 13 atividades; todos os estados estão
  nos testes (passo 9);
- **celular de verdade, leitor de tela real e login**: amarrados ao ensaio (Meta 13);
- **aluno real:** nada disso entra aqui. A conferência local da `linha_base@3` (#462) é feita só na máquina do Angelo, em `entregas/`.

## Antes de começar
- Mesmas ferramentas e cuidados do [[produto/meta-7-como-rodar]] e do [[produto/meta-11-como-rodar]]: comandos na **raiz** do repositório, pasta de trabalho
  fora do git (abaixo, `/caminho/saida`), `uv`, Docker, `curl`, `python3` e, para as capturas, `node` com `npm`.
- **Não use o banco do seu dia a dia** (porta 5433) nem as portas 8000 e 8081. Rode sempre com `-p treino-meta12`. Abaixo: 5471 (Postgres) e 8071 (API).
- **Sem login.** O rótulo de transição pode ser corrigido por quem abrir a tela; quem corrige sem login é a pergunta B, "a confirmar" no fim.

## Passo a passo
1. **Subir o Postgres.** Salve `/caminho/saida/porta.yml` com
   ```
   services:
     postgres:
       ports: !override
         - "5471:5432"
   ```
   e rode:
   ```
   docker compose -p treino-meta12 -f infra/docker-compose.yml -f /caminho/saida/porta.yml up -d
   export DATABASE_URL="postgresql+psycopg://treino:treino@localhost:5471/treino"
   ```
   Esperado: `treino-meta12-postgres-1` `healthy`.
2. **Instalar e migrar:**
   ```
   uv sync
   (cd services/api && uv run alembic upgrade head && uv run alembic current)
   ```
   Esperado: 16 linhas `Running upgrade` e `0016 (head)`. A Meta 12 não tem migração nova: a `linha_base@3` e o `forma_do_dia` são calculados na leitura.
3. **Carregar as 81 atividades sintéticas da Meta 7.** Use o trecho do passo 3 de [[produto/meta-7-como-rodar]] (salve-o em `/caminho/saida/carregar.py` e rode
   `uv run python - < /caminho/saida/carregar.py`). Esperado: `atleta 1: 81 atividades`, e na conferência do banco `(sem)` 40, `professor` 1, `sugestao` 39 e
   `trainingpeaks` 1. As atividades vão de janeiro a março de 2026 (datas fictícias) e 13 delas têm carga (`hrtss`, `carga@2`).
4. **Subir a API:**
   ```
   (cd services/api && uv run uvicorn app.main:app --port 8071)
   ```
   Esperado: `curl -s -o /dev/null -w '%{http_code}\n' localhost:8071/openapi.json` dá `200`.
5. **Ler um treino com a linha de base `@3`.** `curl -s localhost:8071/atletas/1/atividades/81`. É um intervalado de 28 de março com 11 e 12 treinos parecidos na
   janela. Esperado em `linha_base`: `estado` `ok`, `versao` `linha_base@3` e quatro métricas, cada uma com `valor_texto` e o `texto` pronto (o app não monta frase):
   - `melhor_pace` **fora** ("5:00/km, 39 s/km mais lento que a mediana de 4:21/km (11 treinos nas últimas 12 semanas)");
   - `fc_melhor_tiro` **dentro** ("170 bpm, perto da mediana de 172 bpm");
   - `fc_media` **fora** ("150 bpm, 10 bpm abaixo que a mediana de 160 bpm (12 treinos)");
   - `carga_hora` **sem_valor** ("Sem carga por hora neste treino: a carga ainda não foi calculada.").

   Os textos "fora" terminam com "Isto compara com o seu histórico; não diz se o treino foi bom ou ruim." Na mesma resposta: `carga.estado` `pendente` com `texto` "A carga deste treino ainda não foi calculada.",
   `forma_do_dia.estado` `sem_serie` (o dia não tem carga), `transicao` `{valor: false, origem: null, editavel: true}` e `esforcos` com um bloco `esforco` de 1000 m a 5:00.
   O piso por métrica (4 bpm, 3%, 5%) é o que separa a `@3` da `@2`; as contas à mão estão em [[metricas/tipo-linha-base-oraculo]] e no adendo 3 da [[decisoes/0011-linha-de-base-e-semana-padrao]].
6. **Carga e forma do dia em números.** `curl -s localhost:8071/atletas/1/atividades/78` (ciclismo de 25 de março, com carga). Esperado:
   - `carga`: `estado` `calculada`, `carga` 45.0 (sem arredondar), `valor_texto` "45,0", `metodo_texto` "Estimada pela FC." e `texto` `null`;
   - `forma_do_dia`: `estado` `calculada`, `ctl_texto` "6,1", `atl_texto` "10,0" e `tsb_texto` "−3,9" (o sinal de menos é o U+2212), `data_local` o dia do treino
     e `sem_carga_no_dia` 0.

   Um treino cedo na série, como `.../atividades/10` (ciclismo com carga de 30,0 em 10 de janeiro), dá `forma_do_dia.estado` `aprendendo`, **sem CTL, ATL nem TSB**, e
   `texto_aprendendo` "Ainda aprendendo a sua forma: faltam 39 dias de histórico para estimar." (menos de 42 dias de série). Se isso deve mudar é a pergunta A.
7. **Corrigir o rótulo de transição.** Uma corrida comum aceita a correção:
   ```
   curl -s -X PUT localhost:8071/atletas/1/atividades/81/transicao -H 'content-type: application/json' -d '{"transicao":true}' -w ' [%{http_code}]\n'
   ```
   Esperado: `{"valor":true,"origem":"atleta","editavel":true} [200]`. A correção do atleta vence a sugestão. Um `GET` de novo mostra que a linha de base mudou de grupo
   (transição compara só com transição: as três métricas com valor passam a `aprendendo`). Desfazer: `curl -s -X DELETE localhost:8071/atletas/1/atividades/81/transicao -w ' [%{http_code}]\n'`
   dá `{"valor":false,"origem":null,"editavel":true} [200]`. Onde a API não aceita rótulo (atividade `outra`, `troca` ou `multiesporte_pai`; aqui as de id 7, 9 e 11),
   o `GET` traz `editavel: false`, `carga` e `forma_do_dia` `null`, e o `PUT` e o `DELETE` respondem `409` com `{"detail":"Este treino não tem rótulo de transição."} [409]`, sem gravar nada.
   O app não decide pela modalidade: segue o `editavel`. Que o feedback fique `desatualizado` depois de corrigir a transição é a pergunta C.
8. **A tela (capturas por comando).** Em `apps/mobile`: `npm ci` e, na primeira vez, `npx playwright install chromium-headless-shell`. Depois:
   ```
   CAPTURAS_PASTA=/caminho/saida/capturas npm run capturas -- --so=treino-normal-fora,treino-forma-aprendendo,treino-esforcos-muitos
   ```
   Esperado: `OK: 12 capturas` (três telas, claro e escuro, 390 e 1280). **Isto usa a API falsa do app** (atletas e treinos fictícios do `apps/mobile/scripts/api-falsa.mjs`),
   não o banco deste guia. O que ver em cada uma (a spec é a [[design/telas/treino]]):
   - `treino-normal-fora`: o cartão "Comparado com o seu normal", com o estado em ícone **e** palavra ("Fora do seu normal", "Dentro do seu normal"), sem cor de alerta, e a nota fixa no fim;
   - `treino-forma-aprendendo`: "Carga e forma do dia" com o chip "estimativa", a carga em destaque e o aviso de aprendendo no lugar de CTL, ATL e TSB;
   - `treino-esforcos-muitos`: 12 esforços, a tabela mostra 8 e o botão "Ver todos os 12 esforços".

   Todas as outras (`treino-pronto`, `treino-carga-sem-fc`, `treino-carga-pendente`, `treino-normal-*`, `treino-esforcos-ciclismo`) saem com `npm run capturas` sem `--so`.
   Para ver a tela viva e o cartão de transição, `CI=1 EXPO_PUBLIC_API_URL=http://localhost:8071 npx expo start --web --port 8084` (com a API do passo 4 subida com
   `CORS_ORIGENS=http://localhost:8084`) e abrir `http://localhost:8084/treino/81`; a Bia confere isso na QA (#469).
9. **Os testes que não precisam de nada disso:** `uv run pytest services/api/tests/metricas/test_linha_base.py services/api/tests/rotas/test_atividade_carga_forma.py
   services/api/tests/rotas/test_treinos_de_transicao.py tests/test_e2e_meta7.py` (92 passaram: piso de cada métrica, 7 amostras `aprendendo`, estados da carga e da forma,
   o `409`) e, em `apps/mobile`, `npx jest __tests__/TelaTreino.test.tsx` (54 testes: um por estado de cada cartão, a correção com `PUT`, `DELETE`, releitura, erro e "Salvando...").
10. **Limpar.** Pare a API (Ctrl+C) e derrube o banco: `docker compose -p treino-meta12 -f infra/docker-compose.yml -f /caminho/saida/porta.yml down -v`. Isso apaga só o
    volume `treino-meta12_pgdata`; nada do banco do dia a dia é tocado.

## O que é novo na Meta 12
- **`linha_base@3`** ([[metricas/linha-base]], adendo 3 da ADR 0011): piso do desvio por métrica (FC 4 bpm, pace 3% da mediana, carga por hora 5% da mediana), mínimo de 8 treinos do mesmo tipo.
  A `@2` segue reproduzível. Nada é gravado: vale na hora.
- **Textos da carga e `forma_do_dia`** (adendo 12 da ADR 0004): `valor_texto`, `metodo_texto` e `texto` na `carga`; bloco `forma_do_dia` com CTL, ATL e TSB do fim do dia local do treino, em
  1 casa com vírgula e o menos U+2212, sempre como estimativa; em `aprendendo` os três números não saem.
- **`transicao.editavel`** e o `409`: a API decide quando o rótulo pode ser corrigido.
- **`feedback_prompt@9`** (ADR 0013, [[modulos/camada-llm]]): o prompt do feedback acompanha a `linha_base@3`; este guia não gera feedback ([[produto/meta-9-como-rodar]]).
- **Frase do feedback `desatualizado`** só pela versão do pacote: "O feedback será refeito." (#402, adendo 10 da ADR 0004).
- **`atencao@2` nas fixtures do app** (#471) e a distância e o pace em linhas iguais (#237).

## A confirmar com o Angelo
Nada aqui é decidido; a spec adotou a recomendação da Lia e o Paulo leva ao Angelo. Sem conteúdo do dado real.
- **A. Forma do dia em `aprendendo`.** A tela esconde CTL, ATL e TSB nas primeiras semanas e mostra o aviso, porque o TSB sai muito negativo por construção. Alternativa: mostrar os números com um selo "ainda aprendendo".
- **B. Quem corrige sem login.** Sem login, professor e atleta veem a mesma tela, então qualquer um pode corrigir o rótulo. Recomendação: aceitar na Meta 12 (a correção se desfaz com `DELETE`) e fechar com o login, na Meta 13.
- **C. Efeito da correção no feedback.** Corrigir a transição muda a linha de base, que entra no pacote de fatos. O feedback já gerado fica `desatualizado` (o atleta vê o aviso e o texto é refeito), como acontece com o check-in editado e com o tipo corrigido pelo professor?
- **D. Manter a `linha_base@3` ou buscar uma taxa menor de "fora do normal".** Só genérico: a `@3` reduz o "fora" por dispersão pequena; um piso maior ou um limite maior cortaria mais, ao custo de esconder desvios reais. Ela vale como está até haver uso real para calibrar (conferência local na máquina do Angelo, #462).

## Achados do guia
- **O texto de FC "abaixo que a mediana" tem concordância torta.** A frase da `fc_media` sai "10 bpm abaixo que a mediana de 160 bpm". Pequeno, do texto pronto da API; vira issue da Duda ou da Lia.
- **As fixtures da Meta 7 só têm carga em 13 das 81 atividades.** Por isso o `forma_do_dia` do passo 5 é `sem_serie` e o do passo 6 é `calculada`; o `sem_carga` com motivo só aparece nos testes e nas capturas.
- **As capturas e o app vivo usam a API falsa ou o banco**, não os dois ao mesmo tempo. A comparação entre as duas é da QA (#469).
