---
tipo: design
status: em-uso
dono: lia
atualizado: 2026-11-16
links: [[design/telas/checkin]], [[design/telas/feedback]], [[design/telas/treino]], [[design/guia-visual]], [[produto/meta-9-como-rodar]], [[produto/meta-10-como-rodar]], [[modulos/mobile]], [[glossario]]
---
# Conferência visual do check-in e do cartão "Feedback" (#369)

Capturas da tela **rodando** no app web, em 16/11/2026, tema claro e escuro, em 390 px de largura (celular) e 1280 px (desktop). Só dado sintético:
as 18 atividades da Meta 8, os check-ins das fixtures, as noites de `tests/fixtures/meta10/noites_r01` e o provedor falso. Os arquivos estão em
`docs/design/telas/conferencia-369/`, numerados na ordem da conferência.

**Simulação no Chrome não é celular de verdade (Expo Go, iOS, Android, leitor de tela), e isso segue não verificado.**

## Como foi feito
- Postgres descartável, API com `LLM_PROVIDER=falso` e app web (Expo) apontando para ela, como em [[produto/meta-9-como-rodar]] e [[produto/meta-10-como-rodar]].
- A janela do Chrome não passa de 606 px de largura. Para ter 390 px de verdade, o app rodou dentro de um iframe de 390 x 690 px (largura de
  layout real; a altura de 690 é o que cabia na janela, não 844). O tema segue o do sistema; para ver o outro, o teste trocou a resposta de
  `prefers-color-scheme` do iframe antes de o app carregar. Nada disso mexe no código do app.
- O texto "pronto com linha de recuperação" (capturas 01, 02, 33 e 34) foi **escrito à mão** na linha do banco descartável, porque o provedor
  falso não escreve linha de recuperação. Os números são sintéticos e o selo "Texto de teste" aparece. Não é saída de provedor de verdade.

## Capturas
| Estado | 390 px claro | 390 px escuro | 1280 px |
|---|---|---|---|
| pronto, com linha de recuperação (texto à mão) | 01 | 02 | 33 (claro), 34 (escuro) |
| pronto (provedor falso) | 03 | 08 | |
| pendente | 04 | 09 | |
| indisponível | 05 | 10 | |
| sem check-in, no prazo | 06 | 11 | |
| sem check-in, prazo vencido | 07 | 12 | |
| desatualizado: check-in editado | 23 | 24 | |
| desatualizado: noite atualizada | 27 | 28 | 31 (claro), 32 (escuro) |
| desatualizado: clima atualizado | 29 | 30 | |

Fluxo do check-in (claro, 390 px): 13 pergunta 1, 14 pergunta 2, 15 pergunta 3 sem atalho, 16 pergunta 3 com atalho (#382), 17 salvo,
18 treino com o check-in criado e o cartão pendente, 19 depois de "Atualizar", 20 e 21 edição, 22 salvo, 25 e 26 apagar (escuro).
