---
tipo: metrica
status: em-uso
dono: caio
atualizado: 2026-11-10
links: [[decisoes/0013-feedback-automatico]], [[decisoes/0012-check-in-pos-treino]], [[metricas/linha-base]], [[metricas/carga-pse]], [[metricas/carga-pse-oraculo]], [[produto/roadmap]], [[glossario]]
---
# Pacote de fatos `fatos_treino@1`: fixtures e oráculo

## O que é
O pacote de fatos esperado (ADR 0013, item 1) para **10 treinos sintéticos**, escrito **à mão**, e a conferência de que ele é coerente com o que o código **já calcula**.
É o oráculo que a função pura do pacote (#324) vai reproduzir. Nenhum número vem de IA nem de dado real, e **nenhum check-in é real**.
A segunda parte da #323, os **textos bons e ruins** das checagens, está na seção "Textos bons e ruins" abaixo (o tom foi aprovado pelo Angelo em 10/11).

Arquivos: `tests/fixtures/meta9/oraculo.py` (entradas, pacotes esperados e as contas à mão da linha de base) e `tests/test_fixtures_meta9.py`.
O teste desta nota confere o oráculo contra `linha_base@2`, `carga_pse@1`, os formatos de texto da API e as regras do que nunca vai ao provedor. A função pura do pacote (#324, [[metricas/fatos-treino]]) reproduz este oráculo nos 8 casos com pacote.

## Casos
| Caso | O que cobre |
|---|---|
| F01 | corrida leve, as três métricas **dentro** do normal (exemplo 1 da ADR) |
| F02 | intervalado, melhor pace **fora** (4:22/km contra a mediana de 4:09/km, 13 s/km mais lento, z = 2,61), com 5 tiros de 1 km (exemplo 2) |
| F03 | moderado com linha de base **aprendendo** (3 de 8 treinos) e o atalho sono ruim (exemplo 3) |
| F04 | longo com **calor** (33 °C, sensação 37 °C) e atalhos calor e cansaço; pace e FC **fora** (exemplo 4) |
| F05 | leve com o atalho **dor** e **texto livre** com marcador sintético; carga do relógio ainda pendente (exemplo 5) |
| F06 | **natação** sem tipo: `sem_linha_base`, `sem_carga`, carga pela PSE de 200 UA, sem clima (exemplo 6) |
| F07 | corrida **sem check-in**: sem pacote |
| F08 | pai do multiesporte: **não elegível**, sem pacote |
| F09 | **esteira**: clima `indoor`, pace médio `sem_valor` (esteira) |
| F10 | ciclismo sem tipo, clima e carga **pendentes**, PSE 0 (0 UA) |

Cada caso traz o histórico da janela de 12 semanas (um treino por semana), o valor da sessão e as contas. A conta de cada métrica está nos comentários de
`LINHA_BASE_ESPERADA` (mediana, MAD, desvio com o piso de 2% da mediana, z e o corte de 2,5). Exemplo, F04 pace: mediana 342 s/km, MAD 2 (1,4826 x 2 = 2,97), piso 0,02 x 342 = 6,84, desvio 6,84;
valor 5400/15000 x 1000 = 360; z = 18/6,84 = 2,63, **fora**.

## O que o teste confere
- Os 10 casos cobrem o que a #323 pede (sem check-in, aprendendo, fora, com e sem clima, natação, dor).
- As chaves de cada bloco do pacote são as do ADR 0013, na ordem, com `null` no lugar do que falta.
- **Nunca no pacote:** o texto livre (o marcador sintético não aparece), chaves de identificador, nome, data, posição ou professor, e nenhuma data nem hora real.
- A linha de base do pacote bate com `linha_base@2` (estado e `n` de cada métrica) e as contas à mão (mediana, desvio, z) com tolerância de 0,005.
- Os `*_texto` são os mesmos formatos da API (pace, FC, carga por hora, diferença, duração, distância, UA, âncoras da PSE e da sensação).
- A carga pela PSE do pacote é a da `carga_pse@1`; pai do multiesporte e atividade sem check-in não têm pacote.

## Ajuste na ADR 0013 vindo daqui
O exemplo 2 da ADR tinha 4:21/km (12 s/km): com o piso de 2% da mediana o z dava 2,41 e a métrica ficaria **dentro**. Passou a 4:22/km, 13 s/km (z = 2,61), que é **fora** de verdade.

## Textos bons e ruins para as checagens (#323, parte 2)
Arquivos: `tests/fixtures/meta9/textos.py` (a lista) e `tests/test_textos_meta9.py` (confere a lista). Quem decide se cada texto passa ou reprova são as checagens da #325 ([[metricas/checagens-feedback]]); esta lista é o que elas precisam acertar.

- **13 textos bons** (G01 a G13; o G10 passou a dizer "Você marcou esforço 3..." para ter verbo, `@2`), cada um ligado ao caso do oráculo (F01 a F10) cujo pacote o sustenta. G01 a G06 são os 6 exemplos da ADR 0013 palavra por palavra (o teste lê a ADR e compara). Os outros cobrem elogio sustentado por fato (G07), esteira (G08), ciclismo com PSE 0 e o rótulo "muito bem" da sensação, que não é elogio (G09), a frase da dor no meio do texto (G10) clima e calor lado a lado (G11), o rótulo da sensação fora de parênteses (G12) e "quente" com o atalho calor marcado e "mal" como rótulo da sensação 2 (G13).
- **82 textos ruins** (R01 a R82; R40 a R72 vieram da revisão da Nina em 11/11, um por termo ou família nova; R73 a R82 são da forma pedida pelo Angelo em 11/11, `checagens_feedback@2`: linha sem verbo, "pois", "dentro da mediana" e conclusão repetida). Cada um é um bom com **uma** troca e tem **um** motivo esperado, de um conjunto fechado (`MOTIVOS`, 20 códigos): `numero_fora_do_pacote` (inclui data real e conta nova), `numero_por_extenso`, `unidade_trocada`, `linguagem_diagnostico`, `linguagem_culpa`, `linguagem_promessa`, `linguagem_causa`, `linguagem_conselho` (inclui conselho sobre dor), `linguagem_quem_fala`, `elogio_sem_fato`, `forma_linhas`, `forma_tamanho_linha`, `forma_markdown`, `forma_sem_verbo`, `conclusao_repetida`, `comparacao_mediana`, `dor_regra`, `dor_nao_marcada`, `atalho_nao_marcado` e `nome_fora_do_pacote` (lugar e texto livre).
- O teste confere: os 6 primeiros bons são os da ADR; os bons têm 3 a 5 linhas de até 140 caracteres; todo ruim tem motivo do conjunto e uma explicação; todos os códigos têm ao menos um ruim; nenhum texto leva e-mail, link nem data (a data só no R04, que a reprova de propósito), e o marcador do texto livre só aparece no R39.
- Tudo sintético: nenhum texto é feedback real, e o lugar do R38 é inventado.
