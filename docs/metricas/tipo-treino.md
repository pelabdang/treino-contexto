---
tipo: metrica
status: rascunho
dono: caio
atualizado: 2026-11-09
links: [[decisoes/0011-linha-de-base-e-semana-padrao]], [[decisoes/0003-fuso-da-atividade]], [[decisoes/0008-deteccao-de-esforcos]], [[metricas/tiros-1km]], [[metricas/tipo-linha-base-oraculo]], [[produto/roadmap]], [[glossario]]
---
# Tipo de treino: encaixe na semana-padrão e regra de reserva (`tipo_treino@1`)

## O que mede
Diz qual é o **tipo de treino** de cada atividade (`leve`, `moderado`, `longo`, `intervalado`, `fartlek`), de onde ele veio
(`semana_padrao`, `sugestao`; `professor` e `trainingpeaks` não mudam) e se o formato do treino **contradiz o plano**
(divergência, só como dado). Função pura em `services/api/app/metricas/tipo_treino.py`: `classificar(atividades, vigencias)`.
Sem banco, sem rede, sem IA. Decisão e casos: [[decisoes/0011-linha-de-base-e-semana-padrao]]. Fonte: regra própria do projeto
(decisões do Angelo e do Theo de 09/11); não há artigo.

## Regra, na ordem
1. Tipo **confirmado**, origem `professor` ou `trainingpeaks`: não muda, sem versão nem divergência. `multiesporte_pai` e `troca`
   nunca recebem tipo.
2. **Semana-padrão**: vigência de maior `vigente_desde <= data local` (nunca a seguinte). O item (dia da semana ISO e modalidade, com tipo)
   vale para **uma** atividade por modalidade e dia: a de maior `duracao_s`; empate, a de `inicio` mais cedo, depois a de menor `id`. A
   escolhida pode ser protegida (consome o item). Origem `semana_padrao`.
3. **Reserva** (sem tipo do plano: sem plano, sem item, item sem tipo, ou não escolhida), só corrida: 2 ou mais tiros = `intervalado`;
   sem esforço e `duracao_s >= LONGO_MIN_S` (4500 s) = `longo`; sem esforço e `>= LEVE_MIN_S` (1200 s) = `leve`; o resto, sem tipo.
   `moderado` e `fartlek` nunca saem da reserva.

## Divergência
Só origem `semana_padrao`, só corrida com blocos gravados: plano `intervalado` com todos os blocos `leve` = `sem_esforco`; plano `leve` ou
`longo` com série de tiros = `tem_tiros`. O tipo do plano fica.

## Constantes e versão
`VERSAO = "tipo_treino@1"`; `LEVE_MIN_S = 1200`, `LONGO_MIN_S = 4500`, `MIN_TIROS = 2`. Sobe a versão quando mudar a precedência, o
encaixe, uma constante, a tabela de reserva ou os critérios de divergência. As duas durações são propostas, a calibrar na #269.

## Exemplos e oráculo
Os 16 casos do encaixe (E1 a E16) com as fixtures de 12 semanas estão em [[metricas/tipo-linha-base-oraculo]]. Teste:
`services/api/tests/metricas/test_tipo_treino.py` (oráculo das 81 atividades e bordas).

## Limitações
Um item por modalidade por dia. Divergência só em corrida. A `estrutura` (blocos e tiros) é calculada por quem chama a função: no banco, `servicos/tipo_treino.estrutura_dos_blocos` resume os blocos gravados da corrida (`tiros` se `tiros_de_blocos` acha 2 ou mais tiros; `sem_esforco` se todos os blocos são `leve`; `esforco` nos demais; sem blocos, nada).

## No banco (#265)
`servicos/tipo_treino.aplicar_tipos(session, atleta_id, desde=None)` lê as atividades, as vigências e os blocos, chama `classificar` e grava `tipo_treino`, `tipo_origem`, `tipo_versao` e `tipo_divergencia` **só nas linhas que mudam**, sem tocar tipo confirmado, `professor` nem `trainingpeaks`. É chamada por `classificar_atividades` (importação, upload de FIT e `worker.reclassificar`; o atleta todo) e pelo `PUT` da semana-padrão (`desde = vigente_desde`, data local; sem `detectar_esforcos`). `reclassificacao_pendente` trata `sugestao` e `semana_padrao` com `tipo_versao` diferente de `tipo_treino@1` como desatualizadas. Teste com o oráculo das fixtures passando pelo banco: `services/api/tests/servicos/test_tipo_treino_banco.py`.
