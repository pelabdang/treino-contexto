---
tipo: metrica
status: rascunho
dono: caio
atualizado: 2026-11-17
links: [[decisoes/0011-linha-de-base-e-semana-padrao]], [[decisoes/0003-fuso-da-atividade]], [[metricas/tipo-treino]], [[metricas/tipo-linha-base-oraculo]], [[metricas/carga-treino]], [[metricas/tiros-1km]], [[produto/roadmap]], [[glossario]]
---
# Linha de base pessoal e desvio robusto (`linha_base@3`)

## O que mede
Compara uma sessão com o **normal do próprio atleta**, só na **mesma modalidade e no mesmo tipo de treino**, métrica por métrica.
Função pura em `services/api/app/metricas/linha_base.py`: `linha_base(sessao, historico, parametros)`. Sem banco, sem rede, sem IA.
Quem chama calcula os valores (pace, FC, carga por hora, melhor tiro) e a data local. Decisão: [[decisoes/0011-linha-de-base-e-semana-padrao]].
Sempre uma comparação com o histórico, nunca um julgamento de que o treino foi bom ou ruim.

## Regra
- **Janela:** treinos do mesmo atleta, modalidade e `tipo_treino`, com `inicio` anterior ao da sessão e data local de
  `sessao.dia - 84 dias` (12 semanas) em diante (primeiro dia incluído). A sessão nunca entra. Ficam fora os divergentes, o
  multiesporte e os sem tipo (parâmetro do "A confirmar" 2).
- **Base própria da transição (`@2`):** a parte de treino de transição compara só com outras partes de transição (mesma modalidade e
  tipo); a isolada, só com isoladas. Sem parte anterior, `aprendendo` com `n = 0`.
- **Por métrica:** só conta o treino que tem o valor. Menos de **8** valores: `aprendendo` (sem mediana nem desvio). Sessão sem o
  valor: `sem_valor`.
- **Medida:** `mediana`; `MAD = mediana(|x - mediana|)`; `desvio = max(1,4826 x MAD, piso da métrica)`; `z = (valor - mediana) / desvio`.
  **Piso por métrica (`@3`):** FC média e FC do melhor tiro, **4 bpm**; pace médio e melhor pace, **3%** da mediana; carga por hora, **5%** da
  mediana. Métrica sem piso próprio usa 2% (`piso_rel`, só a `@2` e a recuperação).
  `fora` quando `|z| >= 2,5` ("A confirmar" 3), senão `dentro`.
- **Métricas:** corrida `intervalado`: `melhor_pace`, `fc_melhor_tiro`, `fc_media`, `carga_hora`; `leve`, `longo`, `moderado`: `pace_medio`,
  `fc_media`, `carga_hora`; `fartlek`: `fc_media`, `carga_hora`; ciclismo: `fc_media`, `carga_hora`; natação: `fc_media`.
  `carga_hora` = carga da atividade (`carga@2`) / horas de `duracao_s`: mede intensidade, não duração. Sem série de 1 km o `intervalado`
  fica com `melhor_pace` e `fc_melhor_tiro` sem valor e é comparado pela FC média e pela carga por hora (o melhor esforço curto fica fora).
- **Sem linha de base** (primeiro motivo da ordem): `multiesporte`, `modalidade_sem_metricas`, `sem_tipo`, `divergente`.

## Fontes e versão
Mediana e MAD: Leys et al. (2013), J. Exp. Soc. Psychol. 49(4):764-766 (limite 2,5). Constante 1,4826: Rousseeuw e Croux (1993), JASA
88(424):1273-1283. Citações ainda a conferir nos textos. Janela, mínimo e piso: regra própria do projeto (Angelo, 09/11). `VERSAO = "linha_base@3"` (a @3 trocou o piso único de 2% pelo piso por métrica, issues #455 e #462, adendo 3 da ADR 0011; a @2 segue reproduzível por `PARAMETROS_V2`; a @1 tinha 56 dias, exclusão da transição e carga absoluta; decisão de 09/11, adendo 2 da ADR 0011); sobe
quando mudar janela, mínimo, medida, limite, condições de entrada ou lista de métricas.

## O que mudou da `@2` para a `@3`
Só o piso do desvio: de 2% da mediana para todas as métricas, para 4 bpm (FC), 3% (pace) e 5% (carga por hora). Por quê, em termos genéricos:
com dispersão muito pequena no tipo de treino (ou valores em dois grupos, com a mediana num deles) o `z` ficava grande por uma diferença que
o atleta não percebe. Janela de 12 semanas, mínimo de 8, limite 2,5, métricas e estados não mudaram. Quando `1,4826 x MAD` já passa do piso, o
resultado é igual ao da `@2`.

## Exemplo à mão
Oito treinos de pace: 330, 324, 336, 330, 342, 318, 330, 336. Mediana 330; MAD 6; `1,4826 x MAD` = 8,8956. `@2`: desvio `max(8,8956; 6,6)` =
8,8956; sessão a 306, `z = -2,698`, fora. `@3`: desvio `max(8,8956; 0,03 x 330 = 9,9)` = 9,9; a 306, `z = -2,424`, **dentro**; a 318, `z = -1,212`,
dentro. Com 7 treinos: aprendendo. Todos iguais a 330: desvio 9,9 (piso de pace).

Exemplo sintético de carga por hora, janela 50, 50, 52, 54, 61, 62, 62, 62, 62 (mediana 61, MAD 1): sessão a 55, `@2` desvio 1,4826 e `z = -4,05`
(fora); `@3` desvio 3,05 (5% x 61) e `z = -1,97` (dentro). FC com mediana 140 e MAD 1 (`1,4826`): piso `@2` 2,8, `@3` 4; sessão a 148, `z` 2,86
(fora) na `@2` e 2,0 (dentro) na `@3`. Mais casos e as sessões-alvo das fixtures
em [[metricas/tipo-linha-base-oraculo]] (nas fixtures, as janelas de 84 dias incluem mais treinos que o exemplo acima).

## Testes
`services/api/tests/metricas/test_linha_base.py` (oráculo da #261 na `@3`, exemplo da ADR na `@2` e na `@3`, e bordas: 84 dias, base própria da transição, anterior à sessão, limite 2,5, piso de cada métrica, 7 amostras `aprendendo`, igual à `@2` quando o piso não age).

## Limitações
Tipo feito menos de uma vez a cada 12 semanas por 8 vezes (quinzenal ou mais raro) segue em `aprendendo`. O melhor esforço curto do intervalado fica fora. Os pisos da `@3` (4 bpm, 3%, 5%) são escolha do projeto, sem fonte; um piso não resolve a distribuição em dois grupos (mediana num grupo e valor no outro). O texto do aviso e a
formatação são da API (`servicos/linha_base_leitura.py`, #266; contrato em [[modulos/api]]).
