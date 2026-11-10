---
tipo: meta
status: em-uso
dono: paulo
atualizado: 2026-11-09
links: [[produto/roadmap]], [[produto/meta-8-como-rodar]], [[decisoes/0012-check-in-pos-treino]], [[decisoes/0010-carga-de-treino]], [[metricas/carga-pse]], [[metricas/carga-pse-oraculo]], [[design/telas/checkin]], [[modulos/banco]], [[modulos/api]], [[modulos/api-client]], [[modulos/mobile]], [[modulos/worker]], [[produto/metas/meta-7-linha-de-base-semana-padrao]], [[diario/2026-11-09]], [[glossario]]
---
# Meta 8: check-in pós-treino

> **Situação: em andamento.** Todo o código está no `main` (fixtures #307, `carga_pse@1` #308, banco e API #310, `GET` da atividade e pendentes #311,
> tela no app #313, desenho #309). A [[decisoes/0012-check-in-pos-treino]] segue **proposta** (PR #305), esperando o Angelo. Falta fechar a meta
> (resultado, QA da Bia e o celular do Angelo, #301 e #302; o Paulo completa esta nota no #302). Guia passo a passo: [[produto/meta-8-como-rodar]].

## Objetivo
Registrar o **check-in depois de cada treino em 3 toques**: esforço percebido (PSE de 0 a 10), sensação em 5 níveis e observação (atalhos ou texto, com
"nada a relatar" como resposta válida). Com a PSE, uma carga pela PSE (`carga_pse@1`, PSE x minutos, em UA), separada da carga do relógio, que dá carga também à natação.
O check-in é dado de saúde: só no banco local, nunca em log, e com comando para apagar.

## Entrega visível
- `PUT`, `GET` e `DELETE /atletas/{id}/atividades/{id}/checkin`; prazo de 7 dias para criar, edição e apagar sem prazo ([[modulos/api]]).
- `checkin`, `checkin_aberto`, `pse_sugerida` e `carga_pse` no `GET` da atividade, e `GET /atletas/{id}/checkins/pendentes`.
- A tela de check-in (criar em 3 toques, editar, apagar), a lista de pendentes e os cartões na tela do treino ([[design/telas/checkin]], [[modulos/mobile]]).
- `worker.apagar_checkin` ([[modulos/worker]]).
- Passo a passo, com as saídas esperadas, em [[produto/meta-8-como-rodar]].
