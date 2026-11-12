---
tipo: metrica
status: rascunho
dono: caio
atualizado: 2026-11-12
links: [[decisoes/0014-recuperacao-diaria]], [[decisoes/0011-linha-de-base-e-semana-padrao]], [[decisoes/0003-fuso-da-atividade]], [[metricas/linha-base]], [[metricas/recuperacao-oraculo]], [[produto/roadmap]], [[glossario]]
---
# Recuperação da noite anterior (`recuperacao@1`)

## O que mede
Compara a **noite anterior ao treino** (duração do sono, VFC noturna e FC de repouso) com o **normal do próprio atleta**, medida por medida.
Função pura em `services/api/app/metricas/recuperacao.py`: `recuperacao(dia, hora, noites, parametros)`. Sem banco, sem rede, sem IA. Quem chama
carrega as linhas de `recuperacao_dia` (a tabela é da #372) e passa a data e a hora locais do treino ([[decisoes/0003-fuso-da-atividade]]).
Decisão: [[decisoes/0014-recuperacao-diaria]]. É só uma comparação com o histórico: "abaixo" e "acima" são **direção**, nunca bom ou ruim, e não há limiar clínico.

## Regra
- **Noite do treino** (`noite_do_treino`): a linha com `noite = dia` (data local de acordar), se o treino começa **às 06:00 ou depois**. Antes das 06:00:
  `sem_dado` / `treino_de_madrugada`. Treino anterior à noite mais antiga gravada: `sem_dado` / `fora_do_periodo`. Noite ausente ou sem nenhuma medida (ou
  nenhuma noite gravada): `sem_dado` / `sem_noite`. A ordem é essa. Dois treinos no mesmo dia usam a mesma noite.
- **Janela:** as noites de `dia - 28` a `dia - 1` (extremos incluídos); a noite do treino **não entra** no próprio normal.
- **Por medida:** só conta a noite que tem o valor. Menos de **14** valores: `aprendendo` (traz o valor e `n`, sem mediana nem desvio). Noite sem o valor da
  medida: `sem_dado`.
- **Medida:** `mediana`; `MAD = mediana(|x - mediana|)`; `desvio = max(1,4826 x MAD, 0,05 x |mediana|)`; `z = (valor - mediana) / desvio`.
  `abaixo` quando `z <= -2,0`, `acima` quando `z >= 2,0` (o limite pertence ao estado), senão `dentro`.
- **Bloco:** `ok` quando a noite tem ao menos uma medida; as três medidas sempre voltam, na ordem `sono`, `vfc`, `fc_repouso`. `aprendendo` é estado da medida:
  o bloco com as três `aprendendo` continua `ok`.
- **Unidades de entrada:** `sono_s` em segundos, `vfc_ms` em ms, `fc_repouso_bpm` em bpm. Os textos ("5 h 40 min", "1 h 30 min abaixo") são da API (#374), não da função.

## Fontes e versão
Mediana e MAD: Leys et al. (2013), J. Exp. Soc. Psychol. 49(4):764-766. Constante 1,4826: Rousseeuw e Croux (1993), JASA 88(424):1273-1283. Citações
**ainda a conferir nos textos** (a mesma pendência da [[metricas/linha-base]]). Janela de 28 noites, mínimo de 14, piso de 0,05, limite 2,0 e corte das 06:00 são
**escolha nossa**, sem artigo e sem calibração (Angelo, 12/11, "ok para as cinco"; rever depois de uns 30 dias olhando só contagens). `VERSAO = "recuperacao@1"`;
sobe quando mudar janela, mínimo, piso, limite, medida ou a regra da noite do treino.

## Exemplo à mão
Sono em minutos, 14 noites: 400, 410, 420, 420, 425, 430, 435, 435, 440, 440, 445, 450, 460, 470. Mediana 435; MAD 12,5; desvio `max(18,5325; 21,75) = 21,75`.
Noite de 345 min: `z = -4,138`, abaixo. A de 420 min: `z = -0,690`, dentro. Com 13 noites: aprendendo. Todos os casos, com a conta, em [[metricas/recuperacao-oraculo]].

## Testes
`services/api/tests/metricas/test_recuperacao.py` (19 testes: o oráculo à mão, os limites 2,0, o piso, as bordas da janela, as regras da noite do treino).

## Limitações
Os parâmetros são escolhas nossas, não calibradas. A janela de 28 noites acompanha mudanças lentas de rotina (uma fase longa fora do padrão vira o normal). Início
frio de cerca de duas semanas com o relógio no pulso. A função não sabe se uma noite foi recalculada pelo Garmin: isso é do `importado_em` (#372, #374).
