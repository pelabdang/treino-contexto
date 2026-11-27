---
tipo: metrica
status: rascunho
dono: caio
atualizado: 2026-11-27
links: [[metricas/linha-base]], [[metricas/checagens-feedback]], [[modulos/api]], [[glossario]]
---
# Selo "normal" por treino (`normal_treino@1`)

## O que mede
Resume em **um** estado as comparações por métrica da [[metricas/linha-base]] (`linha_base@3`) de um treino, para o selo da lista de treinos.
Função pura em `services/api/app/metricas/normal_treino.py`: `normal_treino(estado_linha_base, estados_metricas)`. Não recalcula nada: usa o
resultado da `linha_base@3` da mesma atividade. Descreve, nunca recomenda nem julga.

## Regra
Entrada: estado da linha de base (`ok` | `sem_linha_base`) e os estados por métrica (`fora`, `dentro`, `aprendendo`, `sem_valor`).
1. Linha de base `sem_linha_base` (multiesporte, sem tipo, divergente, modalidade sem métricas): sem selo (`None`).
2. Alguma métrica `fora`: **`fora`**. Uma só basta, sem peso por métrica (FC média e carga por hora andam juntas; exigir duas esconderia desvios).
3. Senão, alguma `dentro`: **`dentro`** (`dentro` + `aprendendo` dá `dentro`).
4. Senão, alguma `aprendendo`: **`aprendendo`**.
5. Senão (tudo `sem_valor` ou sem métricas): `None`.

Textos do selo na tela (spec v3): "Fora do normal", "No normal", "Aprendendo". "Sem check-in" tem prioridade sobre estes, mas é da API/tela, não métrica.
`fora` vale para os dois lados da mediana; o motivo (qual métrica) fica na tela do treino.

## Fontes e versão
Regra própria do projeto (decisão do Caio na #551), coerente com a regra do elogio da caixa do dia (ao menos uma `dentro`, nenhuma `fora`).
`VERSAO = "normal_treino@1"`; sobe quando mudar a regra ou a prioridade dos estados.

## Exemplo à mão
Corrida leve com `pace_medio` dentro, `fc_media` aprendendo, `carga_hora` dentro: `dentro`. Se a `fc_media` fosse `fora`: `fora`. Todas `aprendendo`: `aprendendo`. Multiesporte: sem selo.

## Testes
`services/api/tests/metricas/test_normal_treino.py`: cada ramo (fora, dentro, aprendendo, tudo sem valor, sem métricas, sem linha de base).

## Limitações
Com várias métricas, a chance de ao menos uma sair `fora` por acaso cresce (limite 2,5 por métrica). O selo não diz qual métrica nem o tamanho do desvio.
