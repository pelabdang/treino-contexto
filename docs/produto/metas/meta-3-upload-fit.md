---
tipo: meta
status: em-uso
dono: paulo
atualizado: 2026-11-03
links: [[produto/roadmap]], [[produto/meta-3-como-rodar]], [[decisoes/0006-upload-de-fit]], [[decisoes/0003-fuso-da-atividade]], [[decisoes/0005-serie-de-tiros-o-que-entra]], [[produto/metas/meta-2-evolucao-tiros-app]], [[modulos/ingestao-garmin]], [[modulos/api]], [[modulos/api-client]], [[modulos/mobile]], [[metricas/tiros-1km]], [[diario/2026-11-03]]
---
# Meta 3: upload de arquivo FIT

> **Situação: feita.** Código e QA no main (#91 a #98). A Bia rodou o envio pelo botão no Chrome, com FIT
> sintéticos, e conferiu cada resposta na tela e no banco (#98, PR #107). Fechamento: #99. Ficam registrados como
> não verificados iOS e Android (sem aparelho) e, na tela, o `404` e a falta de rede (vistos só pelo `npm test` e
> pelo `curl`).

## Objetivo
Plano B enquanto a API da Garmin não é aprovada: o atleta envia um `.fit` pelo app, a atividade entra no banco e,
se for um treino de tiros, aparece na série da Meta 2. Regras na [[decisoes/0006-upload-de-fit]].

## Entrega visível
`POST /atletas/{atleta_id}/atividades/fit` na API e o botão "Enviar arquivo FIT" no app. Depois do envio, a
atividade aparece na série. Tudo local, sem login, com o atleta fixo por configuração. Passo a passo, com um jeito
de forçar cada estado, em [[produto/meta-3-como-rodar]].

## Critério de pronto
Resultado de cada item conforme o relatório da Bia na #98 (PR #107), na web, com os FIT sintéticos de
`tests/fixtures/garmin/fit/`.

| Item | Onde | Resultado |
|---|---|---|
| Reaproveita o leitor FIT da Meta 1 | #92 | **ok**. O leitor saiu do worker para `services/api/app/ingestao/garmin/`, sem mudar o resultado; o worker importa de lá |
| Reenviar o mesmo arquivo não duplica | #94, #98 | **ok**. `200` com `ignorada`; nada gravado de novo |
| A mesma atividade vinda do upload e da exportação não duplica, nos dois sentidos | #94, #98 | **ok**. Regra dos 60 s nos dois caminhos; `200` com `atualizada` e o número de atividades no banco não muda |
| Arquivo inválido, que não é atividade, sem extensão `.fit` ou grande demais dá erro claro, declarado no OpenAPI | #95, #98 | **ok**. `400` (três mensagens próprias) e `413`, conferidos na tela; `404` e `422` declarados no OpenAPI |
| Cliente regerado e botão com os estados enviando, sucesso e erro no `npm test` | #95, #96 | **ok** ([[modulos/api-client]], [[modulos/mobile]]) |
| QA na web com FIT sintéticos, com um jeito documentado de forçar cada estado | #97, #98 | **ok, com ressalva.** `201`, `200` (reenvio e exportação), `400` e `413` vistos na tela. O `404` e a falta de rede **só nos testes** (`npm test` e `curl`), não na tela |
| FIT guardado sem dado pessoal no nome e fora do git | #94, #98 | **ok**. Só `<atleta_id>/<sha256>.fit` em `FIT_DIR`; `git status` limpo; teste do `.gitignore` |
| iOS e Android no Expo Go, ou registrados como não verificados | #98 | **não verificado**: sem simulador nem aparelho na máquina do QA |
| Testes | todos | `uv run pytest -q` e `npm test` verdes no QA; `tests/test_e2e_meta3.py` (10 testes) roda no CI |

## O que foi entregue
| Issue | Entrega | PR |
|---|---|---|
| #91 | ADR 0006: upload de FIT ([[decisoes/0006-upload-de-fit]]) | #100 |
| #92 | Leitor FIT num lugar que a API e o worker usam | #101 |
| #93 | FIT sintéticos para o upload | #102 |
| #94 | `importar_fit`: upload idempotente, regra dos 60 s, guarda em `FIT_DIR` e `worker.apagar_fit` | #103 |
| #95 | Endpoint `POST /atletas/{atleta_id}/atividades/fit` e cliente regerado | #104 |
| #96 | Botão "Enviar arquivo FIT" no app | #105 |
| #97 | Documentação: [[produto/meta-3-como-rodar]], notas dos módulos e diário | #106 |
| #98 | QA de ponta a ponta com FIT sintéticos e `tests/test_e2e_meta3.py` | #107 |
| #99 | Resultado da meta e roteiro | este |

## O que ficou de fora
Como planejado: GPX/TCX, webhook e API da Garmin, storage em nuvem, envio de vários arquivos de uma vez, login,
deploy, edição ou exclusão de atividade pelo app.

## Achados depois da meta
Não estão no critério de pronto, então não são pendências da Meta 3. Viram propostas (abaixo); nenhuma issue foi
criada, porque isso depende do "pode criar" do Angelo.

- **Tradutor do Chrome.** O `index.html` que o Expo gera para a web sai com `lang="en"`. O Chrome entende a página
  como inglês, oferece tradução e, com ela ligada, troca o texto das mensagens em português (na #96 aparecia só
  "Atividade"). O estado da tela fica certo; a frase, não. **Confirmado pela Bia na #98:** ela precisou de um proxy
  local que injeta `translate="no"` para ler as mensagens, e o guia [[produto/meta-3-como-rodar]] traz o aviso.
- **Arquivo temporário do upload.** O servidor (Starlette, por baixo do FastAPI) grava o corpo multipart inteiro
  num arquivo temporário antes de o endpoint aplicar o limite de 10 MB. O limite da ADR 0006 vale, mas um envio
  muito grande ainda ocupa disco por um instante. Para uso local, aceito. Antes do deploy na DigitalOcean, o
  tamanho tem de ser limitado no proxy (por exemplo, o limite de corpo do servidor web na frente da API).
- **Fluxo do docs-ok.** Duas vezes (PRs #105 e #107) o check `docs` ficou pendente porque o label docs-ok foi
  aplicado junto com o próprio commit da Nina, antes de o CI daquele commit rodar, e o merge ficou parado no
  check pendente. Causa provável: o workflow `docs` (`.github/workflows/docs.yml`) tira o label a cada commit novo
  (`synchronize`) e marca o status como pendente; se o label entra antes desse run, ele é apagado em seguida.
- **Série de tiros de 1 km com o histórico real.** Ao olhar a série com o próprio histórico, o Angelo achou que há
  resultados melhores do que os mostrados. Pode ser a classificação dos tiros ou as regras do que entra na série
  ([[decisoes/0005-serie-de-tiros-o-que-entra]], [[metricas/tiros-1km]]). Ainda não foi investigado. Os detalhes
  ficam só fora do repositório.

## Propostas (aguardando "pode criar")
1. **App web em `pt-BR`** (rafa-app, menos de 1 dia). Declarar `lang="pt-BR"` no HTML da web (no Expo Router, pelo
   HTML raiz do app) para o Chrome não oferecer tradução. Critério de pronto: o `index.html` servido pelo
   `expo start --web` tem `lang="pt-BR"`; teste que confere isso; o aviso do guia passa a dizer que não é mais
   preciso desligar a tradução.
2. **Limite de tamanho no proxy** (não é issue agora). Fica como item obrigatório da futura meta de deploy: o proxy
   recusa corpo acima de 10 MB antes de chegar à API. Registrado no roteiro.
3. **Regra do docs-ok** (processo, decisão do Theo). Depois de um commit dela, a Nina aplica o label só quando o CI
   daquele commit terminar. Se aprovada, entra em AGENTS.md, na seção "Documentação".
4. **Investigação da série de tiros com o dado real** (caio-ciencia, com duda-dados; até 1 dia, e o que sair dela
   vira issue própria). Rodar a série sobre o histórico real, listar as sessões que o atleta esperava ver melhores e dizer, para cada uma, se é
   classificação dos tiros, regra da série ou dado de origem. **Os dados reais, a lista e os números ficam só em
   `entregas/`**, fora do git; no repositório entram só a conclusão genérica e, se for o caso, uma nova versão da
   regra com teste sintético. Candidata a vir antes da Meta 4 ou junto com ela: ver "PRECISA DO ANGELO".

## O que se aprendeu
- **Conferir o código antes da ADR evitou surpresa.** A leitura do `main` antes da ADR 0006 achou o ciclo
  API-worker e a duplicação entre upload e exportação. As duas viraram decisão, não retrabalho.
- **Identidade de atividade é regra única.** A regra dos 60 s vale nos dois caminhos; sem ela, a ordem em que os
  dados chegam duplicaria treinos. Vale para toda fonte nova (webhook da Garmin, TrainingPeaks).
- **O FIT do upload é mais pobre que a exportação.** Não traz horário local (`fuso_min` fica vazio e a data cai no
  fallback de [[decisoes/0003-fuso-da-atividade]]) e o leitor não guarda posição. Isso pesa na Meta 4 (clima).
- **O navegador também é parte do QA.** O tradutor do Chrome mudou o texto da tela, e o seletor de arquivo nativo
  não é acessível à automação (a Bia montou o `File` em JavaScript). Prever isso no QA das próximas telas.
- **Estados difíceis de provocar na tela continuam só nos testes** (`404`, rede fora). Mesma lição da Meta 2: falta
  um jeito simples de forçá-los na tela, por exemplo um atleta inexistente na configuração e a API desligada.
- **Label aplicado antes do CI trava o merge.** Ver a proposta 3.

## PRECISA DO ANGELO
- **Ordem da investigação da série de tiros:** antes da Meta 4 (uma meta curta só para isso) ou junto com ela
  (issue paralela do Caio). Proposta do time: junto com a Meta 4, porque a investigação usa o Caio e o dado real e a
  Meta 4 é quase toda da Duda. Se a investigação mudar a regra, a série muda para o atleta.
- **"Pode criar"** para as propostas 1 e 4.
- As decisões da Meta 4 que envolvem dado de aluno estão em [[produto/roadmap]].

## Resultado
**Meta 3 feita.** Na web, com FIT sintéticos, o atleta envia um `.fit` pelo botão, a atividade entra no banco sem
duplicar (reenvio e exportação) e o treino de tiros aparece na série. Os erros são claros e estão no OpenAPI. Não
verificados: iOS e Android, e o `404` e a falta de rede na tela (cobertos pelos testes).

Próxima: Meta 4, clima de cada atividade ([[produto/roadmap]]), com a investigação da série de tiros esperando a
decisão do Angelo sobre a ordem.
