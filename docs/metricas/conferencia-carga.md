---
tipo: metrica
status: em-uso
dono: caio
atualizado: 2026-11-08
links: [[decisoes/0010-carga-de-treino]], [[metricas/serie-carga]], [[metricas/carga-treino]], [[metricas/carga-oraculo]], [[modulos/worker]], [[modulos/ingestao-garmin]], [[modulos/grafico-carga]], [[produto/roadmap]], [[glossario]]
---
# Conferência da nossa carga com a carga do Garmin (`conferencia_carga@1`)

## O que mede
Se a nossa **ATL** e a nossa **CTL** andam junto com a carga aguda e a carga crônica que o Garmin calcula (guardadas pela #174 em
`carga_garmin_dia`). A escala do Garmin é outra (modelo próprio, não TSS), então **não se compara igualdade nem valor absoluto**:
só a ordem dos valores. A conferência é **só descritiva** (decisão do Angelo, 07/11): não há faixa de aprovação. O resultado diz o
que se observou, sempre com a cobertura. Regras da [[decisoes/0010-carga-de-treino]], item 8.

## Fórmula
Nos dias em que as duas séries existem e **nenhuma atividade do dia ficou sem carga** (`sem_carga = 0` na [[metricas/serie-carga]]):
- **Níveis:** Spearman entre ATL e carga aguda, e entre CTL e carga crônica.
- **Diferenças:** Spearman das variações dia a dia (`x[d] - x[d-1]`), só entre dias consecutivos que entraram. Tira a autocorrelação
  das médias móveis, que infla a correlação dos níveis.
- **Defasagem:** o Spearman dos níveis com o Garmin deslocado de -3 a +3 dias. Com `k > 0` compara-se a nossa série em `d` com a
  do Garmin em `d + k` (o Garmin "atrasado"); `k < 0`, o contrário. `k = 0` é igual aos níveis.
- **Razão:** nossa ATL/CTL (dia com CTL = 0 fica fora) contra a razão aguda/crônica do Garmin, em correlação, não em valor.
- **Cobertura:** dias de cada série, em comum, descartados por atividade sem carga e comparados.

**Spearman** é o coeficiente de Pearson entre os **postos** (Spearman, C., 1904, "The proof and measurement of association between
two things", *American Journal of Psychology* 15(1):72-101). Sem empates: `rho = 1 - 6 x soma(d^2) / (n x (n^2 - 1))`; com empates,
posto médio. Menos de 3 pares, ou uma série constante: sem valor (vazio).

**Exemplo à mão.** x = 1, 2, 3, 4, 5 e y = 2, 1, 4, 3, 5: `d = -1, 1, -1, 1, 0`, soma de `d^2` = 4, `rho = 1 - 6 x 4 / (5 x 24) = 0,8`.

**Leitura complementar.** A natação e o tipo `outra` nunca têm carga; um dia só com natação sai da comparação pela regra da ADR.
Por isso o comando grava também, na regra `todos_os_dias`, as mesmas medidas **sem** descartar esses dias (a cobertura diz
quantos são). É só uma segunda leitura; a regra da ADR é a `adr`.

## Dados de entrada
- Nossa série: `carga_atividade` somada por dia local ([[decisoes/0003-fuso-da-atividade]]), via `serie_carga_do_atleta`.
- Garmin: `carga_garmin_dia` (`carga_aguda`, `carga_cronica`, `razao`; o dia é o `calendarDate` da fonte, [[modulos/ingestao-garmin]]).
- Saída (comando `worker.conferir_carga`, [[modulos/worker]]): em `entregas/meta-6/` (fora do git), `conferencia-carga-atleta-<id>.csv`
  (dia a dia, as duas séries e se o dia entrou), `...-resumo.csv` (Spearman e n por medida e regra) e `...-cobertura.csv`.
  O terminal mostra só contagens.

## Referência
Spearman (1904), citado acima. Sem rede, sem IA: números só por código.

## Código e teste
- Código: `services/api/app/metricas/conferencia_carga.py`, `services/api/app/servicos/conferencia_carga.py`,
  `services/worker/worker/conferir_carga.py`.
- Testes: `services/api/tests/metricas/test_conferencia_carga.py` (Spearman, defasagem, diferenças, razão e descartes, tudo à mão)
  e `services/worker/tests/test_conferir_carga.py` (fixtures da #137 com uma carga do Garmin inventada: aguda = 3 x ATL + 7,
  crônica = 2 x CTL, razão = 2 x ATL/CTL; Spearman 1 em tudo; 43 dias, 5 descartados, 38 comparados).

## Limitações e quando não usar
O que a conferência **não** prova:
- **Não prova que a nossa carga está certa**, nem que a do Garmin está. Correlação de postos alta diz que as duas sobem e descem
  juntas, não que medem a mesma coisa nem que medem bem. As duas dependem da FC e do limiar de cada um.
- **Não compara valor.** Escalas diferentes: um número maior no Garmin não é "mais carga" que o nosso.
- **Correlação alta é esperada** por construção: ATL e CTL são médias móveis, e a carga do Garmin também. Por isso há as diferenças
  dia a dia e a defasagem. Mesmo assim ela não separa o método da simples rotina de treino do atleta (mais treino nos dois).
- **Dias descartados não são aleatórios:** quem treina natação ou `outra` tem dias fora. A cobertura vem sempre junto do resultado.
- **Dia do Garmin** é o da fonte (data UTC do `calendarDate`); o nosso é o dia local. Uma diferença de um dia em parte dos treinos
  noturnos é possível e aparece na defasagem.
- Os primeiros 42 dias da nossa série ("ainda aprendendo") entram na comparação; a CTL deles ainda está subindo da semente zero.
- Sem faixa de aprovação: nenhum valor "passa" ou "reprova".
