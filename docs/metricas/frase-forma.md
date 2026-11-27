---
tipo: metrica
status: em-uso
dono: caio
atualizado: 2026-11-27
links: [[metricas/serie-carga]], [[metricas/carga-treino]], [[decisoes/0010-carga-de-treino]], [[modulos/api]], [[glossario]]
---
# Frase da quinzena (`frase_forma@1`)

## O que mede
Uma frase fixa que **descreve** a fadiga (ATL) contra o condicionamento (CTL) de hoje e como o condicionamento andou em 14 dias.
Descrição, nunca recomendação: sem "deve", "evite", "descanse", sem adjetivo de valor e sem siglas no texto.

## Fórmula
Tudo decide sobre os **inteiros mostrados** (`int(x + 0,5)`). F = fadiga, C = condicionamento do último dia da série
(`max(ontem, última atividade)`, ver [[metricas/serie-carga]]). Aprovado pelo Caio com ajustes (#541).

- **Faixa**, com `lim = max(2, 0,10 x C)`: `|F - C| <= lim` → parecidos; `C >= 10` e `F >= 1,5 x C` → bem acima;
  `C >= 10` e `F <= C / 1,5` → bem abaixo; `F - C > lim` → acima; `C - F > lim` → abaixo.
- **Tendência** (só pela CTL): `C14` = CTL do primeiro dia dos 14 do gráfico; `limiar = max(2, 0,05 x C14)`;
  `C - C14 >= limiar` subiu; `<= -limiar` caiu; senão ficou perto. **Omitida** se esse dia estava `aprendendo` ou a série tem menos de 14 dias.
- **Aprendendo:** o último dia ainda aprende: só o texto de "aprendendo", sem comparação.
- **Sem treino recente:** nenhuma carga calculada nos 14 dias: texto próprio, sem faixa nem tendência.
- **Avisos:** "há treinos ainda sem carga calculada" (`pendentes > 0`, vem primeiro) e "treinos dos últimos 14 dias sem carga calculada".
  Este conta só os sem dado; o motivo `modalidade_sem_carga` **não** conta (esse tipo de treino não tem carga por definição).
- Série vazia: sem frase (`null`); vale o `aviso` da API.

## Dados de entrada
`SerieCarga` (de `serie_do_atleta`) e o número de `pendentes`. Função pura, sem banco, sem rede, sem IA.

## Referência
Banister et al., 1976 (impulso-resposta). Os limiares (10 %, 1,5x, 5 %, 2 pontos, 14 dias) são escolha de engenharia para descrever,
não valores publicados nem pontos de corte clínicos. A razão carga aguda/crônica é estudada como marcador de risco de lesão
(Impellizzeri et al., 2020, criticam o uso); por isso a faixa "bem acima" só descreve a diferença.

## Código e teste
- Código: `services/api/app/servicos/frase_forma.py` (`VERSAO = "frase_forma@1"`); rota em `app/rotas/carga.py`.
- Teste: `services/api/tests/servicos/test_frase_forma.py` e `services/api/tests/rotas/test_carga.py`.

## Limitações e quando não usar
Mudar um texto ou um limiar sobe a versão (`frase_forma@2`). Com poucos treinos a frase descreve números ainda instáveis (o aviso de `aprendendo` cobre isso).
