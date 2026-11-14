---
tipo: metrica
status: em-uso
dono: caio
atualizado: 2026-11-15
links: [[decisoes/0013-feedback-automatico]], [[decisoes/0014-recuperacao-diaria]], [[metricas/recuperacao]], [[decisoes/0012-check-in-pos-treino]], [[metricas/fatos-treino-oraculo]], [[metricas/linha-base]], [[metricas/carga-treino]], [[metricas/carga-pse]], [[metricas/esforcos]], [[modulos/api]], [[produto/roadmap]], [[glossario]]
---
# Pacote de fatos `fatos_treino@2`

## O que mede
Não é uma métrica nova: é o **pacote de fatos** que o provedor de LLM recebe sobre um treino (ADR 0013, item 1). Reúne, lado a lado, o que o código **já calcula**
(`linha_base@2`, `carga@2`, `carga_pse@1`, `esforcos@1`, clima e check-in) e os textos prontos de cada número. Quem calcula é o código; a IA só redige a partir daqui.
**Nenhum número é novo, nenhuma conta é feita e nenhuma causa é afirmada**: o calor, por exemplo, aparece como dois fatos separados (a temperatura medida e o atalho "calor").

## Fórmula
Nenhuma. Função pura `fatos_treino(atividade, checkin, linha_base, motivos_sem_valor, clima, carga, esforcos, parte_de_transicao=False, recuperacao=None)` em
`services/api/app/explicacao/fatos_treino.py`: sem banco, sem rede, sem IA, sem log. Devolve um dicionário ou `None`.

- **`None`** (sem pacote): atividade **sem check-in** (o feedback só nasce depois dele) ou **não elegível** (`multiesporte_pai` e `troca`, ADR 0012 item 4).
- **Chaves sempre presentes**, na ordem da ADR: `versao`, `treino`, `linha_base`, `esforcos`, `clima`, `recuperacao`, `carga`, `carga_pse`, `checkin`. O que falta vem `null`, nunca omitido
  (`esforcos` e `clima` são `null` na natação; o clima fora de `ok` traz só o estado).
- **Textos prontos** (`*_texto`) com as funções que a API já usa: `_texto_valor` e `_diferenca` da linha de base, `duracao_pt` e `numero_pt` da carga pela PSE, `distancia_da_atividade`,
  as âncoras da PSE e os textos da sensação. A `carga@2` sai com 1 casa e vírgula ("38,5 pontos").
- **Atalhos do check-in**: só as chaves marcadas, **em ordem alfabética** (a ordem não depende de quem chama).
- **`linha_base.metricas[]`**: `sem_valor` traz `motivo` (do `valores_e_motivos`) e nenhum texto; `aprendendo` traz só `valor_texto`; `dentro` traz também a mediana; `fora`, também `diferenca_texto`.

## O que mudou na `@2` (ADR 0014, issue #374)
- **Bloco `recuperacao`**, depois de `clima`: a noite anterior ao treino comparada com o normal do atleta (`recuperacao@1`, [[metricas/recuperacao]]). Com `estado = ok`:
  `versao`, `estado`, `motivo` (`null`), `janela_noites` (28), `minimo_noites` (14) e `medidas[]` na ordem `sono`, `vfc`, `fc_repouso` (cada uma com `chave`, `estado`,
  `valor`, `valor_texto`, `normal_texto`, `diferenca_texto`, `n`). Com `sem_dado`: só `versao`, `estado` e `motivo` (`sem_noite`, `treino_de_madrugada`, `fora_do_periodo`). `null`
  quando quem chama não passa a recuperação. Textos: sono "5 h 45 min", VFC "41 ms", FC de repouso "58 bpm", **arredondados** (minuto, ms, bpm) antes de comparar; a diferença
  ("1 h 30 min abaixo", "6 bpm acima") é a conta entre os valores arredondados, então fecha à mão. Nunca entram a série diária, a data da noite, MAD, `z` nem a mediana numérica.
- **`checkin.pse_texto` é `null`** quando a PSE não tem âncora (6, 8 e 9). Só no pacote; a rota do check-in não muda.
- Os feedbacks gerados com a `@1` ficam desatualizados e são refeitos (ADR 0014, item 4); o texto antigo é substituído.

## Adaptador do banco (#374)
`app/servicos/feedback_fatos.py` passa a recuperação à função pura; `app/servicos/recuperacao_pacote.py` lê as noites gravadas pela #372 (`recuperacao_banco`) e converte cada
`NoiteGravada` em `rc.Noite`. A data e a hora locais do treino vêm de `inicio_local` (ADR 0003, sem `fuso_min` vale `America/Sao_Paulo`).
- **Sempre há bloco no pacote do adaptador**: atleta sem nenhuma noite (a busca nunca rodou) sai `sem_dado` com `sem_noite`, sem quebrar o feedback. `null` só quando quem chama a função pura não passa a recuperação.
- **`fora_do_periodo`** usa a **primeira noite do atleta** (`primeira_noite`, argumento de `noite_do_treino`), não a mais antiga da janela lida. Omitido, vale a mais antiga da lista.
- **Uma leitura por atleta** no worker (`carregar_do_atleta`); a API lê só a janela do treino (`D-28` a `D`) e a primeira noite.
- **Desatualizado** (ADR 0014, item 4b): `desatualizado(fb, checkin, versao_fatos, recuperacao_hoje)` compara `feedback_treino.recuperacao_importada_em` com o `importado_em` da noite que `noite_do_treino`
  devolve hoje, os dois em UTC. Madrugada, `fora_do_periodo` e sem noite valem `null` dos dois lados e **não** desatualizam. A mesma comparação vale para a fila e o `manter` do worker e para o cartão da API.
  O worker grava `recuperacao_importada_em` com a noite que o pacote usou. Não desatualiza porque o normal mudou.
- Teste: `services/api/tests/servicos/test_recuperacao_pacote.py` (bloco igual ao oráculo `tests/fixtures/meta10/oraculo_fatos_recuperacao.py` nos 6 casos; o pacote não leva série, data, identificador nem texto livre)
  e `services/worker/tests/test_gerar_feedback.py` (noite que chega refaz uma vez; apagar a recuperação apaga o feedback).

## Prompt e checagens da recuperação (#375)
O `feedback_prompt@8` e as `checagens_feedback@6` cobrem o bloco `recuperacao` ([[metricas/checagens-feedback]]). A rodada com o provedor de verdade é a #376.

## Dados de entrada
A recuperação da noite do treino (`recuperacao@1`, [[metricas/recuperacao]]), lida do banco pelo adaptador (veja acima); a função pura recebe o resultado pronto.
Os do `GET` da atividade, já calculados: a atividade (lê só `modalidade`, `subtipo`, `tipo_treino`, `duracao_s`, `distancia_m`, `fc_media`), o check-in (lê só `pse`, `sensacao`, `nada_a_relatar` e os atalhos),
o resultado da `linha_base@2`, o clima (`ClimaFatos`), a `carga@2` (`CargaFatos`) e os esforços (`EsforcosFatos`). A `carga_pse@1` é calculada dentro, com a função pura da Meta 8.

**Nunca entra no pacote** (a função lê só os atributos acima; o resto do objeto é ignorado): o **texto livre** da observação (nem o fato de existir), nome, `atleta_id`, `atividade_id` e qualquer identificador,
**data ou hora real**, posição, nome de arquivo e nome do professor. Dado de saúde: o pacote só vive na memória e no provedor (decisão 9 da ADR); nunca em log nem em arquivo.

## Referência
Regra própria do projeto, sem artigo (ADR 0013, "Fontes"). As fontes das métricas de dentro estão nas suas notas: [[metricas/linha-base]], [[metricas/carga-pse]], [[metricas/carga-treino]], [[metricas/esforcos]].

## Código e teste
- Código: `services/api/app/explicacao/fatos_treino.py` (`VERSAO = "fatos_treino@2"`; sobe quando mudar um campo, uma unidade, um estado, a lista de métricas ou o que fica de fora).
- Teste do bloco da recuperação: `services/api/tests/explicacao/test_fatos_treino_recuperacao.py` (oráculo `tests/fixtures/meta10/oraculo_fatos_recuperacao.py`).
- Teste: `services/api/tests/explicacao/test_fatos_treino.py`. Valor esperado calculado à mão no oráculo da #323 ([[metricas/fatos-treino-oraculo]], `tests/fixtures/meta9/oraculo.py`):
  o pacote é **igual ao oráculo** nos 8 casos com pacote (F01 a F06, F09 e F10); F07 (sem check-in) e F08 (pai do multiesporte) dão `None`.
  Confere também: o texto livre não entra (nem com um `CheckinTreino` de verdade); nenhum identificador, data ou posição de uma `Atividade` de verdade entra; nenhuma chave nem texto de causa;
  nenhum número além dos do oráculo; os argumentos não são alterados e o resultado se repete; o módulo não importa rede, LLM nem banco; clima fora de `ok` sem valores; carga pela PSE sem duração e com casa decimal (272,5 UA).

## Limitações e quando não usar
- Só descreve o treino: sem pace ajustado por calor ou subida, sem estimativa de quanto cada fator pesou, sem sono, HRV nem FC de repouso, sem séries de natação (ver "Fora desta ADR" na ADR 0013).
- A função **não busca** nada: quem a chama (o `worker.gerar_feedback`, #327) monta as entradas com a leitura que a API já faz. Os textos de linha de base usam funções internas (`_texto_valor`, `_diferenca`) de
  `linha_base_leitura.py`; se elas mudarem de formato, o pacote muda e o oráculo avisa.
- O método da `carga@2` (`rtss` ou `hrtss`) vem de quem chama; o oráculo da #323 não o tem na entrada, então o teste o toma do pacote esperado.
