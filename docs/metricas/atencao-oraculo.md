---
tipo: metrica
status: rascunho
dono: caio
atualizado: 2026-11-17
links: [[decisoes/0015-caixa-do-dia-do-professor]], [[decisoes/0011-linha-de-base-e-semana-padrao]], [[decisoes/0012-check-in-pos-treino]], [[metricas/linha-base]], [[metricas/carga-pse-oraculo]], [[produto/roadmap]], [[glossario]]
---
# Caixa do dia: fixtures e oráculo à mão (`atencao@2`)

## O que mede
O resultado esperado da `atencao@2` ([[decisoes/0015-caixa-do-dia-do-professor]], item 4) sobre um professor e **8 atletas fictícios**, escrito à mão para uma data de
referência fixa: **hoje = 18/11/2026 (quarta)**. Nada vem de resposta do Garmin, de check-in real nem da conta de ninguém. A regra é a #422; este arquivo e as
fixtures são o **oráculo** dela. O teste é `tests/test_fixtures_meta11.py` (sem rede, sem banco): confere a forma, os casos e que o oráculo escrito à mão é igual
a uma referência curta e independente que vive só no teste.

Arquivos em `tests/fixtures/meta11/`:
- `identidade.json`: no **mesmo formato** do carregador `worker.carregar_professor` (#423): assessoria, dois professores, atletas com vínculo e `consentimento_em`.
- `treinos.json`: a **entrada da `atencao@2`** por treino, já resumida (tipo, origem, confirmado, divergência, métricas fora da linha de base com o `z` assinado,
  check-in como só `{dor}` ou `null`). **Sem texto livre nem observação**: o campo não existe na entrada (ADR 0015, item 7).
- `oraculo.json`: a lista esperada (quem aparece, em que ordem, com que linha), quem não aparece e por quê, o que não tem motivo e por quê, e os treinos novos.

Parâmetros (ADR 0015, item 4): janela de atenção 7 dias (`hoje - 7` a `hoje`), aviso de check-in a partir de 5 dias, janela dos novos 14 dias, limite de "fora"
2,5 (o da `linha_base@2`).

## Atletas e casos
| Atleta | Treino (dia) | Caso | Esperado |
|---|---|---|---|
| Ana | `ana-1` (terça 17/11) | dor marcada **e** FC média com `z = +3,1` | **dois motivos**, nesta ordem: `dor`, `fora_do_normal` ("FC média acima do habitual") |
| Ana | `ana-2` (domingo 15/11) | dentro do normal, check-in sem dor | sem motivo |
| Igor | `igor-1` (domingo 15/11) | dor marcada; ciclismo sem tipo | `dor`; empata com a Ana no motivo de maior prioridade; o treino da Ana é mais **recente**, então Ana vem antes |
| Helena | `hel-1` (segunda 16/11) | pace médio `z = +2,8` e FC média `z = -2,6` | `fora_do_normal`, uma linha, medidas **na ordem da tabela** do item 4: "FC média abaixo do habitual e pace médio mais lento" |
| Bruno | `bru-1` (sábado 14/11) | semana-padrão previa `longo`, tiros detectados, não confirmado | `divergencia` |
| Bruno | `bru-2` (domingo 15/11) | divergência `sem_esforco` gravada, mas **tipo confirmado** | sem motivo (o professor já decidiu; a coluna fica) |
| Carla | `car-1` (sexta 13/11) | sem check-in, 5 dias: restam 2 | **sem linha própria**: conta no resumo do `car-5` (uma linha por aluno) |
| Carla | `car-5` (quarta 11/11) | sem check-in, 7 dias: último dia, natação sem tipo; o **mais antigo** | `checkin_vencendo` com a linha única: "2 treinos sem check-in; o prazo do mais antigo termina hoje."; borda da janela |
| Carla | `car-6` (quinta 12/11) | sem check-in, 6 dias, modalidade `outra` | sem motivo e **fora da contagem** (por isso o resumo diz 2, não 3) |
| Carla | `car-2` (terça 17/11) | **treino de ontem** sem check-in | sem motivo (1 dia; o aviso começa com 5) |
| Carla | `car-3` (terça 10/11) | sem check-in, 8 dias | sem motivo (fora da janela e prazo vencido) |
| Carla | `car-4` (sexta 13/11) | `multiesporte_pai` sem check-in | sem motivo (não é elegível a check-in) |
| Davi | `dav-1` (segunda 16/11) | dentro do normal, check-in sem dor | sem motivo |
| Davi | `dav-0` (domingo 02/11) | dor marcada, **16 dias** | sem motivo (fora da janela); Davi vai para "Nada a destacar nos últimos 7 dias." |
| Eva Sem Consentimento | `eva-1` | dor marcada, vínculo com `consentimento_em` nulo | **não aparece** |
| Fabio De Outro Professor | `fab-1` | dor marcada, vínculo só com o outro professor | **não aparece** |

## Ordem esperada da lista
1. **Ana** (`dor`, treino mais recente, 17/11), 2. **Igor** (`dor`, 15/11), 3. **Helena** (`fora_do_normal`), 4. **Bruno** (`divergencia`), 5. **Carla** (`checkin_vencendo`, uma
linha só, no `car-5`). Depois, sem motivo: **Davi**.

Conta da prioridade: `dor` (1), `fora_do_normal` (2), `divergencia` (3), `checkin_vencendo` (4); desempate pelo treino com motivo mais recente, depois `atleta_id`.

## Treinos novos (tipo sugerido para confirmar)
`tipo_treino` não nulo, origem `sugestao` ou `semana_padrao`, não confirmado, elegível, de `hoje - 14` (04/11) a `hoje`: **`ana-1`, `ana-2`, `hel-1`, `bru-1`, `car-1`, `car-2`,
`car-3`, `dav-1`**. Ficam de fora: `bru-2` (confirmado), `igor-1`, `car-4` e `car-5` (sem tipo), `dav-0` (16 dias), `eva-1` e `fab-1` (fora do filtro).

## Como rodar
`uv run pytest tests/test_fixtures_meta11.py` (sem rede).
