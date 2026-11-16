---
tipo: meta
status: em-uso
dono: paulo
atualizado: 2026-11-16
links: [[produto/roadmap]], [[design/telas/conferencia-369]], [[produto/meta-10-como-rodar]], [[decisoes/0014-recuperacao-diaria]], [[decisoes/0013-feedback-automatico]], [[decisoes/0004-contrato-tela-evolucao]], [[metricas/recuperacao]], [[metricas/recuperacao-oraculo]], [[metricas/fatos-treino]], [[metricas/fatos-treino-oraculo]], [[metricas/checagens-feedback]], [[modulos/camada-llm]], [[modulos/banco]], [[modulos/worker]], [[modulos/ingestao-garmin]], [[produto/metas/meta-9-feedback-automatico]], [[diario/2026-11-12]], [[diario/2026-11-13]], [[diario/2026-11-16]], [[glossario]]
---
# Meta 10: sono, VFC e FC de repouso no contexto do treino

> **Situação: feita, com o celular de verdade não verificado.** Código, documentação, QA, conferência local e conferência visual no `main` ou em
> revisão (PRs #381 a #416, entre 12/11 e 16/11). A Bia conferiu o critério de pronto com `tests/test_e2e_meta10.py` (23 testes, um por
> item, só dado sintético, sem rede) e seguiu o [[produto/meta-10-como-rodar]] do zero com um Postgres descartável (#378, PR #413). A Lia
> fez a conferência visual no Chrome em 390 px, sem bloqueantes, com 34 capturas sintéticas (#369, PR #416, [[design/telas/conferencia-369]]). A
> [[decisoes/0014-recuperacao-diaria]] foi **aceita em 12/11** (PR #383), antes da migração 0014 (PR #388). Fechamento: #380.

## Objetivo
O pacote de fatos ganha a recuperação da noite anterior ao treino (duração do sono, VFC noturna e FC de repouso), comparada com o normal do
próprio atleta, e o feedback passa a pôr esse fato **lado a lado** com o resultado, sem afirmar causa e sem conselho.

## Entrega visível
- `worker.buscar_recuperacao` (busca e grava as noites; `--fixtures` carrega noites sintéticas) e `worker.apagar_recuperacao`
  ([[modulos/worker]], [[modulos/ingestao-garmin]]); tabela `recuperacao_dia` (migração 0014, [[modulos/banco]]).
- `recuperacao@1` ([[metricas/recuperacao]]) e o bloco `recuperacao` no `fatos_treino@2` ([[metricas/fatos-treino]]).
- No cartão "Feedback" que já existe, uma ou duas linhas sobre a noite anterior quando há dado (exemplo sintético: "Na noite anterior você
  dormiu 5 h 40 min, 1 h 30 min abaixo do seu normal de 7 h 10 min."). Sem tela nova e sem campo novo no contrato.
- O feedback fica `desatualizado` quando a noite chega ou muda (#396) e quando o clima chega depois (#409, migração 0015), cada caso com a
  sua mensagem.
- Passo a passo em [[produto/meta-10-como-rodar]].

## Critério de pronto
Resultado de cada item conforme a QA da Bia na #378 (PR #413), só com fixtures sintéticas. Os números entre parênteses são os testes de
`tests/test_e2e_meta10.py`.

| Item | Onde | Resultado |
|---|---|---|
| Conferência visual do cartão e do check-in no Chrome em tamanho de celular, com a API real e o provedor falso, e revisão da Lia sobre a tela rodando; registrado que a simulação não é celular de verdade | #369 | **ok, sem bloqueantes** (Lia, 16/11; revisão na #369, 34 capturas sintéticas no PR #416, [[design/telas/conferencia-369]]). Cobriu também o passo do navegador da QA #378: cartão `pronto` com a linha da recuperação e texto de teste rotulado. Limites: 390 px dentro de um iframe (altura 690), contraste só olhado, não medido; a simulação não é celular de verdade. Antes, a simulação do Theo de 12/11 (606 px, API falsa) |
| ADR 0014 aprovada pelo Theo antes da migração; "A confirmar" com padrões | #370 | **ok**. Modelo aprovado e ADR aceita em 12/11 (PR #383); o Angelo respondeu "ok para as cinco"; migração 0014 em 13/11 (PR #388) (e2e 01 e 21) |
| `recuperacao@1` como função pura, nota em `docs/metricas/` e oráculo sobre fixtures sintéticas escritas à mão | #371, #373 | **ok** ([[metricas/recuperacao]], [[metricas/recuperacao-oraculo]]; PRs #385 e #387; e2e 06 e 07) |
| `fatos_treino@2` com a recuperação; prompt e checagens com versão nova e textos bons e ruins novos; a checagem real roda sobre o texto do provedor falso | #374, #375 | **ok** (PRs #390 e #391; e2e 10 e 12). Hoje em `feedback_prompt@8` e `checagens_feedback@6`, depois das issues que entraram durante a meta |
| Testes e CI sem rede (cliente Garmin falso, provedor falso); a falta de dado de sono nunca vira número inventado | #372, #374 | **ok** (e2e 03, 04, 05 e 17) |
| Ao provedor vai só a comparação da noite, nunca a série nem datas; nada da recuperação em log; apagar leva as noites e os feedbacks que as usaram | #372, #374 | **ok** (e2e 11, 13, 18, 19 e 20) |
| QA com fixtures num clone limpo, seguindo só o guia | #377, #378 | **ok**. Passos 1 a 10 com os números do guia; a única diferença (passo 2, head 0014 no guia, 0015 no código) foi corrigida no PR #414 |
| Conferência local com a conta do Angelo, com nada no repositório | #379 | **ok** (PR #411). Regras da `recuperacao@1` mantidas, versão sem mudança; três limitações genéricas em [[metricas/recuperacao]] |
| Testes | todos | `uv run pytest` no `main` em `4773722`: 2682 verdes e 2 pulados (SQLite local, rodado no fechamento; 23 em `tests/test_e2e_meta10.py`) |

## O que foi entregue
| Issue | Entrega | PR |
|---|---|---|
| #368 | Roteiro com a Meta 10 em curso e as decisões do Angelo de 12/11 | #381 |
| #370 | ADR 0014 ([[decisoes/0014-recuperacao-diaria]]), aceita em 12/11 | #383 |
| #371 | Formato das respostas de sono, VFC e FC de repouso, fixtures sintéticas | #385 |
| #373 | `recuperacao@1` e o oráculo | #387 |
| #372, #386 | Migração 0014 (`recuperacao_dia`), `buscar_recuperacao`, `apagar_recuperacao`; o 429 das rotas de dados do Garmin vira limite | #388 |
| #374 | `fatos_treino@2` com o bloco `recuperacao` e o adaptador do banco; `feedback_prompt@4` | #390 |
| #375 | `feedback_prompt@5` e `checagens_feedback@4` com a recuperação | #391 |
| #376 | Rodada pequena com o provedor de verdade, só fixtures ([[modulos/camada-llm]]) | #393 |
| #377 | Guia [[produto/meta-10-como-rodar]], diários, [[00-inicio]] e glossário | #389, #392 |
| #394 | `feedback_prompt@6`: recuperação em duas linhas, dentro do máximo de 5 | #398 |
| #395 | Camada de LLM: teto de saída e esforço de raciocínio pelo `.env`; teste de tamanho do prompt fiel | #399 |
| #397 | `buscar_recuperacao --fixtures` (guia e QA sem trecho em Python) | #400 |
| #396 | Mensagem própria quando o desatualizado vem da noite que chegou | #401 |
| #403 | Frase do "aprendendo" obrigatória e concordância de "FC média" (`feedback_prompt@7`, `checagens_feedback@5`) | #404 |
| #405 | Estado do clima no texto e frase por estado (`feedback_prompt@8`, `checagens_feedback@6`) | #406 |
| #407 | `--refazer` só mantém o texto antigo se ele passar nas checagens atuais | #408 |
| #409 | O clima que chega depois desatualiza o feedback (migração 0015) | #410 |
| #379 | Conferência local da recuperação; limitações genéricas na nota da métrica | #411 |
| #378 | QA de ponta a ponta e `tests/test_e2e_meta10.py` | #413 |
| #369 | Conferência visual no Chrome em 390 px, revisão da Lia e 34 capturas sintéticas ([[design/telas/conferencia-369]]) | #416 |
| (sem issue) | Diário de 16/11; guias sem head fixo das migrações | #412, #414 |
| #380 | Resultado da meta e roteiro | este |

Paralela, fora do critério: #367 (espaços no fim da linha e "esforço N (N)" no texto, PR #384). Em aberto, fora do caminho: #402 (frase
quando só a versão do pacote desatualiza) (a #382, botão Salvar do check-in que subia quando a dica sumia, foi **feita** no PR #432).

## Decisões (regra de produto)
**Do Angelo (12/11, "ok para as nove"):** tema = recuperação; guardar só duração do sono, VFC noturna e FC de repouso, com a regra do dado de
saúde da Meta 6; fonte = a biblioteca não oficial, só no piloto local; ao provedor vai só a comparação da noite anterior; recuperação lado
a lado, sem causa e sem conselho; **decisão 6:** sem sessão do celular agora, conferência no Chrome em tamanho de celular no lugar; caixa
do professor = Meta 11; #213, #237, #74 e treinos planejados fora. **Na ADR 0014 (12/11):** "ok para as cinco" de "A confirmar".
**Depois da rodada da #376 (13/11):** a recuperação em duas linhas, mantendo o máximo de 5 (#394).

**Do Theo:** modelo de dados da ADR 0014; as decisões dos PRs #390 e #391 ([[diario/2026-11-13]]); teto de saída, esforço de raciocínio e
pausa sugerida na camada (#395); o desatualizado pela noite e pelo clima com mensagens próprias (#396, #409); `--refazer` que reconfere o
texto mantido (#407).

## O que não foi verificado
- **Largura de celular só por simulação:** a #369 viu a tela em 390 px dentro de um iframe (altura 690), no Chrome; não é a janela nem o
  aparelho. **Contraste** só olhado nas capturas, não medido.
- **Celular de verdade:** nenhuma tela foi aberta num iOS ou Android. Fora do critério por decisão do Angelo (decisão 6); é a **terceira
  meta seguida** com o item aberto (Metas 8, 9 e 10). A simulação não é celular de verdade.
- **Leitor de tela real** (VoiceOver, TalkBack).
- **Dado real no repositório:** por desenho, nada. A conferência local (#379) e o uso local do feedback ficaram só na máquina do Angelo.

## O que ficou de fora
Como planejado: tela própria da recuperação; estágios do sono, estresse, prontidão e estado de treino do Garmin; motor de explicação com o
peso de cada fator; treinos planejados do Garmin; a exportação Garmin como segunda fonte da recuperação; alerta de recuperação baixa;
outros atletas; sessão no celular de verdade.

## Limitações conhecidas
Detalhes na [[decisoes/0014-recuperacao-diaria]] ("Limitações") e em [[metricas/recuperacao]]. Todas em texto genérico.
- **Só piloto local, biblioteca não oficial:** pode quebrar quando o Garmin mudar o login ou os campos; a API oficial depende do CNPJ.
- **Corte das 06:00 aproximado:** a hora real do fim do sono não é guardada; treino de madrugada fica sem recuperação.
- **Normal instável em conta com buracos:** o normal exige metade das noites da janela com valor e pode alternar com "aprendendo".
- **Em medida muito estável, o piso relativo domina o desvio:** a leitura vale como direção ("acima", "abaixo"), não como tamanho.
- **A checagem de forma segue heurística** (`checagens_feedback@6`), agora com regras por estado do pacote (aprendendo, clima).
- **Feedback anterior à migração 0015 não entra na fila pelo clima:** o `--refazer` resolve.
- **O provedor falso não exercita a linha de recuperação**: o texto fixo não cita a noite; só o e2e com texto sintético e as rodadas com
  o provedor de verdade mostram essa linha.

## Achados
Todos genéricos; nada do dado real.
- **O limite do plano gratuito do provedor é parte do desenho.** Há limite por minuto e por dia; o prompt com a recuperação somado ao teto
  de saída padrão passava do limite por minuto, e o modelo de raciocínio devolvia texto vazio. Virou teto de saída e esforço de raciocínio
  pelo `.env`, teste de tamanho com 3,3 caracteres por token e pausa sugerida de 65 s entre chamadas (#395).
- **A linha com as três medidas passava de 140 caracteres** (rodada da #376: 4 de 10 aprovadas). Com a recuperação em duas linhas (#394),
  10 de 14.
- **O uso local achou o que as fixtures e as rodadas sintéticas não acharam:** a frase do "aprendendo" faltando, a concordância de "FC" e o
  estado do clima dito errado passavam nas checagens. Viraram checagens por estado do pacote (#403, #405).
- **O `--refazer` antigo podia manter um texto que a checagem nova reprovaria** (resolvido na #407).
- **O clima que chega depois não desatualizava o feedback** (resolvido na #409); a noite que chega desatualizava com a frase errada,
  "Você editou o check-in" (resolvido na #396; o caso só de versão do pacote é a #402, em aberto).
- **Teste e guia com o head da migração fixo quebram na migração seguinte:** o primeiro CI do #410 falhou por isso; os testes passaram a ler
  o head do alembic e os guias não fixam mais o número (#414).
- **A conferência visual dependeu de novo da extensão do navegador:** não estava disponível na sessão da QA, e a tela só foi vista no fim,
  pela Lia (#369), que cobriu o passo do navegador da QA.
- **O botão Salvar do check-in sobe quando a dica some (#382, resolvido no PR #432: a dica tem altura fixa de 2 linhas)**, confirmado na #369 e pior em 390 px: sobe 48 px e "Nada a relatar" fica
  onde ele estava (risco de toque errado).

## O que se aprendeu
- **Cada dado que chega depois do feedback precisa de regra de desatualizado e de mensagem própria**, decididas na ADR, não descobertas
  depois: check-in (Meta 9), noite (#396), clima (#409), versão do pacote (#402). Na próxima ADR que mexer no pacote, uma tabela "o que
  desatualiza e o que o `GET` diz".
- **Rodada com o provedor de verdade a cada versão do prompt.** A rodada antes da QA (aprendido na Meta 9) achou o tamanho; cada versão nova
  (`@6`, `@7`, `@8`) teve a sua, e todas acharam algo.
- **Uso local com o dado real, antes da QA, acha defeitos de forma** que o sintético não acha; vale prever a janela na largada (sem nada no
  repositório).
- **O `--refazer` é uma promessa:** o que ele mantém tem de passar nas checagens de hoje.
- **Nunca fixar o head da migração** em teste ou guia.
- **"A confirmar" com padrões funcionou pela quinta meta seguida** (ADR 0014, "ok para as cinco").
- **Conferência visual não pode depender da extensão do navegador.** Três metas seguidas com a tela vista tarde ou não vista; na Meta 10
  ela só foi vista no fim da meta. A próxima meta com tela precisa de capturas que rodem sem a extensão (proposta P1 da Meta 11).

## PRECISA DO ANGELO
- **Celular de verdade:** pendência das Metas 8, 9 e 10 (pergunta 10 da Meta 11 no [[produto/roadmap]]).
- **Termos do provedor sobre o uso dos dados para treinar modelos** (item 10 de "A confirmar" da ADR 0013): segue não conferido por nós.
- **Meta 11:** proposta e perguntas no [[produto/roadmap]] ("Meta 11, proposta"). Nenhuma issue da Meta 11 foi aberta.

## Resultado
**Meta 10 feita, com o celular de verdade não verificado.** A conferência visual no Chrome em 390 px (#369) não teve bloqueantes. Com fixtures sintéticas, o
`worker.buscar_recuperacao` grava as noites, a `recuperacao@1` compara a noite anterior ao treino com o normal do atleta, o `fatos_treino@2`
leva só essa comparação ao provedor, e o feedback põe a noite lado a lado com o resultado, sem causa nem conselho, passando por
`checagens_feedback@6`. Falta de dado nunca vira número; nada da recuperação vai a log; apagar leva as noites e os feedbacks que as usaram.
Versões no fechamento: `fatos_treino@2`, `recuperacao@1`, `feedback_prompt@8`, `checagens_feedback@6`; migrações até 0015.

Próxima: Meta 11 (caixa do dia do professor), **proposta**, esperando o "ok" do Angelo ([[produto/roadmap]]).
