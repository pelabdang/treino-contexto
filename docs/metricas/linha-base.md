---
tipo: metrica
status: rascunho
dono: caio
atualizado: 2026-11-09
links: [[decisoes/0011-linha-de-base-e-semana-padrao]], [[decisoes/0003-fuso-da-atividade]], [[metricas/tipo-treino]], [[metricas/tipo-linha-base-oraculo]], [[metricas/carga-treino]], [[metricas/tiros-1km]], [[produto/roadmap]], [[glossario]]
---
# Linha de base pessoal e desvio robusto (`linha_base@2`)

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
- **Medida:** `mediana`; `MAD = mediana(|x - mediana|)`; `desvio = max(1,4826 x MAD, 0,02 x |mediana|)`; `z = (valor - mediana) / desvio`.
  `fora` quando `|z| >= 2,5` ("A confirmar" 3), senão `dentro`.
- **Métricas:** corrida `intervalado`: `melhor_pace`, `fc_melhor_tiro`, `fc_media`, `carga_hora`; `leve`, `longo`, `moderado`: `pace_medio`,
  `fc_media`, `carga_hora`; `fartlek`: `fc_media`, `carga_hora`; ciclismo: `fc_media`, `carga_hora`; natação: `fc_media`.
  `carga_hora` = carga da atividade (`carga@2`) / horas de `duracao_s`: mede intensidade, não duração. Sem série de 1 km o `intervalado`
  fica com `melhor_pace` e `fc_melhor_tiro` sem valor e é comparado pela FC média e pela carga por hora (o melhor esforço curto fica fora).
- **Sem linha de base** (primeiro motivo da ordem): `multiesporte`, `modalidade_sem_metricas`, `sem_tipo`, `divergente`.

## Fontes e versão
Mediana e MAD: Leys et al. (2013), J. Exp. Soc. Psychol. 49(4):764-766 (limite 2,5). Constante 1,4826: Rousseeuw e Croux (1993), JASA
88(424):1273-1283. Citações ainda a conferir nos textos. Janela, mínimo e piso: regra própria do projeto (Angelo, 09/11). `VERSAO = "linha_base@2"` (a @1 tinha 56 dias, exclusão da transição e carga absoluta; decisão de 09/11, adendo 2 da ADR 0011); sobe
quando mudar janela, mínimo, medida, limite, condições de entrada ou lista de métricas.

## Exemplo à mão
Oito treinos: 330, 324, 336, 330, 342, 318, 330, 336. Mediana 330; MAD 6; desvio `max(8,8956; 6,6) = 8,8956`. Sessão a 306: `z = -2,698`,
fora. A 318: `z = -1,349`, dentro. Com 7 treinos: aprendendo. Todos iguais a 330: desvio 6,6 (piso). Mais casos e as sessões-alvo das fixtures
em [[metricas/tipo-linha-base-oraculo]] (nas fixtures, as janelas de 84 dias incluem mais treinos que o exemplo acima).

## Testes
`services/api/tests/metricas/test_linha_base.py` (oráculo da #261, exemplo da ADR e bordas: 84 dias, base própria da transição, anterior à sessão, limite 2,5).

## Limitações
Tipo feito menos de uma vez a cada 12 semanas por 8 vezes (quinzenal ou mais raro) segue em `aprendendo`. O melhor esforço curto do intervalado fica fora. O piso de 2% é proposta, a calibrar na #269. O texto do aviso e a
formatação são da API (`servicos/linha_base_leitura.py`, #266; contrato em [[modulos/api]]).
