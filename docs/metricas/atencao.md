---
tipo: metrica
status: rascunho
dono: caio
atualizado: 2026-11-16
links: [[decisoes/0015-caixa-do-dia-do-professor]], [[metricas/atencao-oraculo]], [[metricas/linha-base]], [[decisoes/0011-linha-de-base-e-semana-padrao]], [[decisoes/0012-check-in-pos-treino]], [[produto/roadmap]], [[glossario]]
---
# Atenção da caixa do dia (`atencao@1`)

## O que mede
Por que um treino de um aluno merece o olhar do professor, em **quatro motivos**, sem afirmar causa. Função pura em `services/api/app/metricas/atencao.py`:
`motivos_do_treino(treino, hoje)`, `atencao(treinos_por_atleta, hoje)` e `treinos_novos(treinos, hoje)`. Sem banco, sem rede, sem IA, sem relógio (`hoje` é a data
local de `America/Sao_Paulo`). Decisão: [[decisoes/0015-caixa-do-dia-do-professor]], item 4. Oráculo à mão: [[metricas/atencao-oraculo]].

## Entrada
Por treino (`TreinoAtencao`): `id`, `dia` (data local), `modalidade`, `subtipo`, tipo, origem e `tipo_confirmado`, `tipo_divergencia`, `metricas_fora` (pares
`(chave, z assinado)` das métricas da `linha_base@2` com estado `fora`) e `dor` (`True`/`False`; `None` = **sem check-in**). **Não há campo de observação nem de texto
livre** (ADR 0015, item 7). Nada é calculado aqui: quem chama (a API, #424) lê a linha de base e o check-in. `atencao()` **não filtra vínculo nem consentimento**: quem chama
só passa os atletas do professor (ADR 0015, item 3).

## Os quatro motivos
Janela: treinos de `hoje - 7` a `hoje` (`JANELA_DIAS = 7`). Fora dela, nenhum motivo. Ordem dos motivos num treino e prioridade entre atletas: 1 `dor`, 2 `fora_do_normal`,
3 `divergencia`, 4 `checkin_vencendo`.

| # | Motivo | Dispara quando | Linha (exemplo sintético) |
|---|---|---|---|
| 1 | `dor` | check-in com `dor` marcada | Treino de terça com dor marcada no check-in. |
| 2 | `fora_do_normal` | alguma métrica com \|z\| >= 2,5 (o limite da `linha_base@2`) | Treino de terça fora do normal: FC média acima do habitual. |
| 3 | `divergencia` | origem `semana_padrao`, `tipo_divergencia` preenchida e tipo **não** confirmado | Treino de sábado diferente da semana-padrão: previsto longo, com tiros detectados. |
| 4 | `checkin_vencendo` | sem check-in, elegível (não é `multiesporte_pai` nem `troca`), de 5 a 7 dias depois do treino | Treino de sexta sem check-in; o prazo termina em 2 dias. |

Vocabulário do motivo 2 (ordem da tabela; sinal do `z`; pace é s/km, `z > 0` é mais lento): FC média acima/abaixo do habitual; FC do melhor tiro acima/abaixo do habitual;
pace médio mais lento/mais rápido; melhor pace mais lento/mais rápido; carga por hora acima/abaixo do habitual. Várias medidas na mesma linha: "A, B e C".
**Proibido** na linha: causa, diagnóstico, conselho, número de saúde, comparação entre atletas, juízo.

## Ordem da lista
Atletas: motivo de maior prioridade presente; empate: treino com motivo mais recente; empate: chave do atleta. Dentro do atleta, treinos do mais recente ao mais antigo.
Sem motivo: depois de todos, com "Nada a destacar nos últimos 7 dias." (não é "está tudo bem").

## Treinos novos (não é motivo)
Tipo não nulo, origem `sugestao` ou `semana_padrao`, não confirmado, elegível, de `hoje - 14` a `hoje` (`JANELA_NOVOS_DIAS = 14`).

## Fontes e limites
Regra própria do projeto, sem artigo: janela de 7 dias, aviso a partir de 5, janela de 14 dias dos novos e a ordem dos motivos são **escolha nossa**. O limite de "fora do
normal" não é novo: é o da `linha_base@2` ([[decisoes/0011-linha-de-base-e-semana-padrao]]; mediana e MAD de Leys et al., 2013, citação ainda a conferir). Não é limiar clínico.
O motivo 4 some no oitavo dia (prazo vencido). Mudar qualquer coisa acima exige subir `VERSAO` (`atencao@1`).

Testes: `uv run pytest services/api/tests/metricas/test_atencao.py`.
