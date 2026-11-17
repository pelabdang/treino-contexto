---
tipo: modulo
status: em-uso
dono: nina
atualizado: 2026-11-17
links: [[decisoes/0015-caixa-do-dia-do-professor]], [[decisoes/0004-contrato-tela-evolucao]], [[metricas/atencao]], [[metricas/atencao-oraculo]], [[design/telas/caixa-do-dia]], [[produto/metas/meta-11-caixa-do-dia]], [[produto/meta-11-como-rodar]], [[modulos/api]], [[modulos/mobile]], [[modulos/banco]], [[modulos/worker]], [[glossario]]
---
# Módulo: caixa do dia do professor

## Para que serve
Mostra ao professor, numa tela só, quais alunos pedem atenção hoje e quais treinos novos esperam o tipo confirmado. É o piloto local da Meta 11: sem login e só com atletas sintéticos ([[decisoes/0015-caixa-do-dia-do-professor]]).

## Entradas e saídas
- Entrada: o `professor_id` da rota, que só vale se for o da configuração.
- Saída: `GET /professores/{professor_id}/caixa-do-dia` com os alunos ordenados pela `atencao@2` ([[metricas/atencao]]) e os treinos novos com tipo sugerido. A resposta é calculada a cada leitura e leva `Cache-Control: no-store`.
- Correção do tipo: `PUT` em lote, tudo ou nada. Só vale para atividades de atletas do filtro de vínculo.
- Quem formata é a API; o app só mostra ([[decisoes/0004-contrato-tela-evolucao]], adendos 2 e 11).

## Regra de privacidade
Um filtro só, `atletas_do_professor`: vínculo com consentimento já dado. Toda rota de professor passa por ele. Sem vínculo, sem consentimento ou com consentimento no futuro, o aluno some e a API responde `404`. Ver "Vínculo e consentimento" no [[glossario]].

## Arquivos principais
- `services/api/app/rotas/caixa_do_dia.py`: a rota e a montagem da caixa.
- `services/api/app/metricas/atencao.py`: a regra `atencao@2` (função pura).
- `services/api/app/rotas/professor.py`: o professor do piloto.
- `apps/mobile/src/componentes/TelaCaixaDoDia.tsx`: a tela `/caixa-do-dia` ([[design/telas/caixa-do-dia]]).
- `worker.carregar_professor`: carrega o professor, o vínculo e o consentimento sintéticos ([[modulos/worker]]).

## Depende de
[[modulos/banco]] (tabelas `professor` e `vinculo_professor_atleta`, migração 0016), [[metricas/linha-base]] (o motivo "fora do normal"), [[metricas/tipo-treino]] (tipo sugerido) e o check-in ([[decisoes/0012-check-in-pos-treino]]).

## Como testar
Passo a passo em [[produto/meta-11-como-rodar]]. Oráculo da regra em [[metricas/atencao-oraculo]]. A matriz de testes cruza rota e situação de consentimento.

## Pendências
- Login e controle de acesso: o `professor_id` configurado não é autenticação (Meta 13).
- Termo de consentimento, contrato com a assessoria e LGPD ficam com o Angelo.
- O "fora do normal" só vira leitura para o atleta depois da `linha_base@3` (Meta 12, #462).
