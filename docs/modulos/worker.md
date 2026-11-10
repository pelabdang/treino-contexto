---
tipo: modulo
status: em-uso
dono: theo
atualizado: 2026-11-10
links: [[decisoes/0013-feedback-automatico]], [[modulos/camada-llm]], [decisoes/0012-check-in-pos-treino]], [[decisoes/0006-upload-de-fit]], [[modulos/api]], [[modulos/grafico-tiros]], [[modulos/grafico-carga]], [[metricas/conferencia-carga]], [[modulos/infra]], [[modulos/ingestao-garmin]], [[modulos/banco]], [[modulos/clima]], [[decisoes/0008-deteccao-de-esforcos]], [[decisoes/0009-treino-de-transicao]], [[decisoes/0010-carga-de-treino]], [[metricas/transicao]], [[metricas/esforcos]], [[decisoes/0007-clima-da-atividade]], [[produto/meta-4-como-rodar]]
---
# Módulo: worker

## Para que serve
Serviço de processamento em segundo plano (FastAPI). Hoje tem `/health` e a importação da exportação Garmin no banco (`worker/importar_garmin.py`, linha de comando; o parser e a gravação moram na API, em `app/ingestao/`, desde a #92 e a #94). Vai rodar tarefas pesadas
da importação e do cálculo de métricas, fora da [[modulos/api]].

## Entradas e saídas
- Saída: `GET /health` devolve `{"status": "ok"}`.
- Parser (na API desde a #92, [[decisoes/0006-upload-de-fit]]): `app.ingestao.garmin.ler_exportacao(caminho)` lê zip, pasta, `summarizedActivities.json` ou `.fit` e devolve atividades com voltas. Detalhes em [[modulos/ingestao-garmin]].
- Importação: `uv run python -m worker.importar_garmin <caminho> --atleta "<nome>" [--com-clima]` grava atividades e voltas no banco ([[modulos/banco]]), de forma idempotente. **Sem rede por padrão** (#132): sem `--com-clima` nenhuma conexão é aberta e o fim da importação imprime `clima: nao buscado` com o comando a rodar.
- Saúde (#140, [[decisoes/0010-carga-de-treino]]): `uv run python -m worker.importar_saude <caminho> --atleta "<nome>"` grava o limiar, as zonas de FC, os recordes pessoais e a carga do Garmin da exportação no banco, idempotente e **sem rede**; imprime só contagens por tabela (`saude limiar: inseridas=... atualizadas=... ignoradas=...`) e avisos, nunca valores (dado fisiológico). O `importar_garmin` chama a mesma função no fim das atividades; erro ali vira aviso em stderr e **não derruba** a importação (rode `worker.importar_saude` depois). Exportação sem dados de saúde: nada gravado. `uv run python -m worker.apagar_saude --atleta "<nome>"` (LGPD, #174) apaga as quatro tabelas de saúde do atleta (sem apagar o atleta, as atividades nem os FIT) e imprime só contagens. Detalhes em [[modulos/ingestao-garmin]].
- Buscar no Garmin Connect (#335, piloto local da Meta 9, **biblioteca não oficial**): `uv run python -m worker.buscar_garmin --atleta "<nome>" [--desde AAAA-MM-DD] [--ate AAAA-MM-DD] [--sem-clima]` entra na conta Garmin do atleta, lista as atividades do intervalo (padrão: hoje, data local), pula as que já estão no banco e baixa o FIT original das outras, que passa por `importar_fit`, o mesmo caminho do upload de FIT (identidade, guarda do arquivo, esforços, tipo), e depois pela carga e pelo clima, como a importação da exportação. Idempotente; o atleta precisa existir. Credenciais só em `GARMIN_EMAIL` e `GARMIN_PASSWORD` do `.env` local; token salvo em `GARMINTOKENS` (padrão `dados-garmin/token`, fora do git). Uma tentativa de login por execução; erro vira mensagem e código de saída (1 configuração, 2 login, 3 MFA, 4 limite, 5 rede, 6 outro). **Usa a rede** (Garmin e, sem `--sem-clima`, Open-Meteo). Detalhes e limitações em [[modulos/ingestao-garmin]].
- Gráfico: `uv run python -m worker.grafico_tiros_1km --atleta-id <id> [--inicio AAAA-MM-DD] [--fim AAAA-MM-DD] [--saida <pasta>]`
  lê a série do banco e grava `entregas/meta-1/tiros-1km-atleta-<id>.png` e `.csv` (pasta criada se faltar; fora do
  git). Atleta inexistente: mensagem em stderr e código de saída 1. Formato em [[modulos/grafico-tiros]].
  Exemplo com as fixtures: ![[_anexos/tiros-1km-atleta-fixtures.png]]
- Gráfico da carga: `uv run python -m worker.grafico_carga --atleta-id <id> [--inicio ..] [--fim ..] [--saida <pasta>]` (#143) grava `entregas/meta-6/carga-atleta-<id>.png` e `.csv` (CTL, ATL, TSB e carga do dia; estimativa). Só lê o banco, sem rede. Formato em [[modulos/grafico-carga]].
- Conferência da carga: `uv run python -m worker.conferir_carga --atleta-id <id> [--saida <pasta>]` (#144, [[metricas/conferencia-carga]]) compara a nossa ATL/CTL com a carga aguda/crônica do Garmin (`carga_garmin_dia`) e grava em `entregas/meta-6/` três CSVs (dia a dia, resumo com Spearman por medida, cobertura). Só descritivo, sem faixa de aprovação. Só lê o banco, sem rede; o terminal mostra só contagens.

- Apagar FIT enviados: `uv run python -m worker.apagar_fit --atleta-id <id>` apaga os arquivos de `FIT_DIR/<id>/` e limpa `arquivo_bruto`, sem apagar as atividades ([[decisoes/0006-upload-de-fit]]; uso na prática em [[produto/meta-3-como-rodar]]).
- Reclassificação: `uv run python -m worker.reclassificar --atleta-id <id>` roda `classificar_atividades` e mostra
  quantas corridas processou. Idempotente. Use quando a API devolve `reclassificacao_pendente: true`
  (passo a passo em "Reclassificar" de [[modulos/api]]). Atleta inexistente: stderr e saída 1. Desde a #265 também regrava o tipo de
  **todas** as atividades pela `tipo_treino@1` ([[decisoes/0011-linha-de-base-e-semana-padrao]]): semana-padrão vigente e regra de reserva, com
  `tipo_versao` e `tipo_divergencia`, só nas linhas que mudam e sem tocar tipo confirmado, `professor` nem `trainingpeaks`. Sugestão de antes da 0011
  (`tipo_versao` nulo) conta como desatualizada e é regravada aqui ou na importação (`classificar_atividades`).
- Feedback (#327, [[decisoes/0013-feedback-automatico]], [[modulos/camada-llm]]): `uv run python -m worker.gerar_feedback --atleta "<nome>" [--limite N] [--refazer]` gera o feedback automático dos treinos do atleta: para cada check-in da atividade elegível, monta o pacote de fatos (`fatos_treino@1`), pede o texto à camada de LLM, passa pelas checagens (`checagens_feedback@1`) e grava em `feedback_treino` ([[modulos/banco]]). **É a única execução que chama o provedor**; nunca dentro do `PUT` do check-in. **Fila:** check-ins sem linha, com `sem_feedback` ou desatualizados (o check-in foi editado, inclusive um `PUT` idêntico, ou a versão do pacote mudou); quem **nunca foi tentado vem primeiro**, depois os de menos `tentativas` (um treino que sempre reprova não gasta o limite dos outros), empate pelo mais recente. **Limite:** no máximo N chamadas ao provedor por execução (`--limite`, senão `LLM_LIMITE_CHAMADAS`, padrão 20); o que sobra fica para a próxima (`adiados`). **Idempotente:** sem mudança nova não há fila nem chamada. **Texto reprovado nunca é gravado**: a linha fica `sem_feedback` com `motivo = texto_reprovado` e a próxima execução tenta de novo; `provedor_erro`, `provedor_tempo_limite` e `provedor_nao_configurado` também viram motivo, nunca exceção. `--refazer` refaz também o que está pronto e em dia (dentro do limite). Imprime só contagens e códigos: `feedback: gerados=a sem_feedback=b ignorados=c adiados=d erros=e` e, se houver, `motivos:` e `reprovacoes:`; nunca texto nem pacote, nem em log. Nome repetido usa o menor id; nome inexistente sai com 1. **Com `LLM_PROVIDER=groq` o pacote (dado de saúde) sai da máquina**: só no computador do próprio atleta, com o "sim" dele (ADR 0013, decisão 9); testes e CI usam o provedor falso (`LLM_PROVIDER=falso`). O pacote e as checagens entram por injeção (assinaturas na nota [[modulos/camada-llm]] e em `app/servicos/feedback.py`).
- Check-in: `uv run python -m worker.apagar_checkin --atleta "<nome>"` (LGPD, #296, [[decisoes/0012-check-in-pos-treino]]) apaga **todos** os check-ins pós-treino do atleta (PSE, sensação, atalhos e texto) sem apagar o atleta nem as atividades, e **os feedbacks deles** (ADR 0013) e imprime só `checkins: apagados=N` e `feedbacks: apagados=M`, nunca valores. Idempotente (a segunda rodada dá 0). Nome repetido: o de menor id, com aviso em stderr de que os outros ficam; nome inexistente: erro e saída 1.
- Treino de transição: `uv run python -m worker.sugerir_transicao --atleta-id <id>` (#157, [[decisoes/0009-treino-de-transicao]]) aplica a regra
  `transicao@1` ([[metricas/transicao]]) às atividades do atleta e grava em `rotulo_transicao` ([[modulos/banco]]). **Sem rede.**
  A regra só grava "sim" (origem `sugerido`): insere as sugeridas sem linha, atualiza `versao_regra` e `definido_em` só quando a
  versão mudou, apaga as `sugerido` que a regra não sugere mais e **nunca toca numa linha `atleta`** (correção do atleta).
  Idempotente: a 2ª rodada não muda linha nenhuma (nem `definido_em`). Roda sobre o atleta inteiro, porque uma atividade nova
  pode formar par com uma antiga. Imprime atividades (elegíveis), sugeridas, inseridas, atualizadas, removidas, sem mudança e
  quantas correções do atleta existem (e em quantas a regra sugere "sim"). Atleta inexistente: stderr e saída 1. A importação
  e o upload de FIT já chamam a mesma função (ver [[modulos/ingestao-garmin]]); o comando serve para o histórico e para uma versão nova da regra.
- Carga: `uv run python -m worker.calcular_carga --atleta-id <id>` (#141, [[decisoes/0010-carga-de-treino]], [[metricas/carga-treino]]) calcula a carga (rTSS/hrTSS por volta) de cada atividade do atleta e grava em `carga_atividade` ([[modulos/banco]]). **Sem rede.** O limiar de cada atividade é o vigente no **dia local** dela (`limiar_vigente`, ADR 0003). **Idempotente:** calcula a `entrada` (SHA-256 do que entra na conta) e a `versao` e só regrava a linha quando um dos dois mudou; subir a `VERSAO` de `app.metricas.carga` recalcula tudo, e um limiar novo recalcula só as atividades cujo limiar usado mudou. `multiesporte_pai` e `troca` não têm linha (e perdem a que tinham, se a atividade foi reclassificada). Relatório só com contagens: processadas, gravadas, já atualizadas, calculadas, sem carga por motivo e ignoradas. O `importar_garmin` chama o mesmo cálculo depois dos dados de saúde; erro ali vira aviso em stderr e não derruba a importação (rode `worker.calcular_carga` depois). Atleta sem dados de saúde: tudo `sem_dados_saude` (natação e `outra`: `modalidade_sem_carga`), nada estimado.
- Esforços: `uv run python -m worker.detectar_esforcos --atleta-id <id>` (#166, [[decisoes/0008-deteccao-de-esforcos]]) lê as voltas
  de cada corrida e pedalada do atleta, monta os blocos ([[metricas/esforcos]]) e grava em `bloco_atividade` ([[modulos/banco]]).
  **Sem rede.** Idempotente: calcula os blocos de cada atividade e só regrava os que mudaram (valores ou
  `versao_deteccao`); a 2ª rodada muda 0 e os `id` ficam. Mudar `VERSAO` em `app/metricas/esforcos.py` (ou qualquer
  constante da regra) faz a rodada seguinte redetectar tudo. A referência é o ritmo habitual (corrida) ou a velocidade
  habitual (ciclismo: mediana das pedaladas de mais de 30 min, fora do trainer, 12 semanas antes, ou todo o histórico
  com menos de 10); sem histórico vale a mediana da própria atividade. Imprime atividades processadas (regravadas,
  sem mudança, sem blocos), esforços e treinos-chave por modalidade, esforços por faixa e quantas atividades usaram a
  referência de reserva. Atleta inexistente: stderr e saída 1. A importação (`importar`) e o upload de FIT
  (`importar_fit`) não chamam a detecção direto: ela roda dentro de `classificar_atividades` (#168), que é o único ponto de
  detecção da importação; um erro nela vira aviso no log e nunca derruba a importação (rode o comando para refazer).
  A API só lê o que ele grava (#167, [[modulos/api]]).
- Clima: `uv run python -m worker.preencher_clima [--atleta-id N] [--exportacao CAMINHO] [--limite N] [--refazer-falhas] [--so-posicao]`.
  Primeiro relê a posição, da exportação (se dada) e, na falta dela, do FIT de `FIT_DIR`, para preencher `inicio_lat/lon` onde está `NULL`; depois busca
  o clima das atividades ao ar livre, com posição, sem `ok` válido e com fim a mais de 7 dias. Sequencial, pausa de 0,25 s,
  teto de 500 chamadas por rodada, um `commit` por atividade, para se o Open-Meteo limitar (429). Imprime posições
  preenchidas e atividades por estado. `--so-posicao` não usa a rede. Regras e estados em [[modulos/clima]]; passo a passo rodado em [[produto/meta-4-como-rodar]].
- Multiesporte: `uv run python -m worker.reclassificar_multiesporte --exportacao CAMINHO [--atleta-id N] [--dry-run]` marca
  `subtipo = multiesporte_pai` ou `troca` nas linhas `garmin_export` com `modalidade = outra` e subtipo vazio (valores e fonte
  pública em [[modulos/ingestao-garmin]], #230). Nunca sobrescreve outro subtipo nem muda modalidade. Idempotente; `--dry-run`
  imprime `NULL -> troca: N` e as linhas fora da exportação lida, sem gravar.
- Subtipo: `uv run python -m worker.reclassificar_subtipo --exportacao CAMINHO [--atleta-id N] [--dry-run]` relê o tipo da
  exportação (sem rede) e grava o `subtipo` pelo `tipos.py` atual só onde está `NULL` ou diverge, nas linhas `garmin_export`
  (casa por `fonte_id`). Para bancos importados antes de um mapeamento existir (ex.: `virtual_ride` -> `virtual`, #183).
  Só mexe em `subtipo`; se o novo for indoor, apaga `inicio_lat/lon` (ADR 0007). Subtipo `None` na exportação nunca apaga
  o gravado. Idempotente (2ª rodada muda 0); `--dry-run` imprime `antigo -> novo: N` sem gravar. Reimportar a exportação
  também atualiza o subtipo, mas relê as voltas e reclassifica as corridas; este comando é o caminho estreito.
  **Limitações:** (1) se a atividade que vira indoor já tinha linha em `clima_atividade`, a linha fica órfã (não é apagada);
  a API mostra `indoor` pelo subtipo antes de olhar a linha, então nada aparece errado, só sobra um registro velho.
  (2) O caminho inverso (indoor que vira ao ar livre) não recupera a posição; `worker.preencher_clima --so-posicao` resolve.
- Com `--com-clima`, no fim de `worker.importar_garmin` o clima é buscado **com a rede de verdade**, só das atividades que entraram ou mudaram (posições arredondadas vão ao Open-Meteo); erro de clima vira aviso
  e nunca derruba a importação. Sem a opção, rode `worker.preencher_clima` quando quiser. O upload de FIT (endpoint) não chama a rede: o clima fica `pendente` até a próxima rodada.

## Arquivos principais
- `services/worker/worker/main.py`
- O parser (`leitor.py`, `fit.py`, `tipos.py`, `unidades.py`, `modelos.py`) está em `services/api/app/ingestao/garmin/`; o worker importa de lá
- `services/worker/worker/importar_garmin.py` (importação no banco, CLI `python -m worker.importar_garmin`)
- `services/worker/worker/importar_saude.py` (limiar, zonas, recordes e carga do Garmin no banco, CLI `python -m worker.importar_saude`)
- `services/worker/worker/apagar_checkin.py` (apaga os check-ins de um atleta, CLI `python -m worker.apagar_checkin`)
- `services/worker/worker/apagar_saude.py` (apaga os dados de saúde de um atleta, CLI `python -m worker.apagar_saude`)
- `services/worker/worker/grafico_tiros_1km.py` (gráfico e CSV, CLI `python -m worker.grafico_tiros_1km`)
- `services/worker/worker/grafico_carga.py` (gráfico e CSV da carga, CLI `python -m worker.grafico_carga`); teste `services/worker/tests/test_grafico_carga.py`
- `services/worker/worker/conferir_carga.py` (CLI `python -m worker.conferir_carga`); a lógica está em `services/api/app/metricas/conferencia_carga.py` e `services/api/app/servicos/conferencia_carga.py`; teste `services/worker/tests/test_conferir_carga.py`
- `services/worker/worker/apagar_fit.py` (CLI `python -m worker.apagar_fit`)
- `services/worker/worker/reclassificar.py` (CLI `python -m worker.reclassificar`)
- `services/worker/worker/reclassificar_subtipo.py` (CLI `python -m worker.reclassificar_subtipo`)
- `services/worker/worker/reclassificar_multiesporte.py` (CLI `python -m worker.reclassificar_multiesporte`)
- `services/worker/worker/calcular_carga.py` (CLI `python -m worker.calcular_carga`); a lógica está em `services/api/app/servicos/carga.py`
- `services/worker/tests/test_calcular_carga.py` (ponta a ponta com as fixtures de `tests/fixtures/garmin/carga/` contra o oráculo [[metricas/carga-oraculo]])
- `services/worker/worker/detectar_esforcos.py` (CLI `python -m worker.detectar_esforcos`); a lógica está em `services/api/app/servicos/esforcos.py`
- `services/worker/tests/test_detectar_esforcos.py`
- `services/worker/worker/sugerir_transicao.py` (CLI `python -m worker.sugerir_transicao`); a lógica está em `services/api/app/servicos/transicao.py`
- `services/worker/tests/test_sugerir_transicao.py`
- `services/worker/worker/preencher_clima.py` (CLI `python -m worker.preencher_clima`); a lógica está em `services/api/app/servicos/clima.py`
- `services/worker/tests/test_preencher_clima.py`
- `services/worker/tests/test_reclassificar.py`
- `services/worker/tests/test_reclassificar_subtipo.py`
- `services/worker/tests/test_reclassificar_multiesporte.py`
- `services/worker/tests/test_grafico_tiros_1km.py`
- `services/worker/tests/test_health.py`
- `services/api/tests/ingestao/test_garmin_parser.py` (testes do parser, na API)

## Depende de
- Mesmo workspace uv da [[modulos/api]]; a importação usa o parser de `app.ingestao.garmin` e chama `classificar_atividades` de `app.servicos` (ver "Série de tiros no banco" em [[modulos/api]]). Banco em [[modulos/banco]] quando houver tarefas.

## Como testar
`uv run pytest -q` na raiz.

## Pendências
- Definir fila e tarefas na Meta 1. Quando definir, abrir ADR em [[decisoes/]].
