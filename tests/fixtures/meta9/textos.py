"""Textos bons e ruins para as checagens do feedback (issue #323, parte 2; ADR 0013, itens 4 e 5). 100% sintéticos.

``BONS``: texto que precisa passar nas checagens, com o caso (F01...F10) do oráculo cujo pacote o sustenta. Os seis primeiros são
os exemplos da ADR, palavra por palavra (um teste confere contra a ADR); o tom está aprovado pelo Angelo (10/11).
``RUINS``: texto que precisa reprovar, com o caso e o **motivo esperado** (um código fechado, ver ``MOTIVOS``). Cada ruim é um bom com UMA
troca (``_troca``) e foi escrito para ter um único motivo. Os códigos são os que a função pura das checagens (#325) devolve; texto reprovado
nunca é guardado nem mostrado, só o código. Nenhum texto aqui é feedback real, e nenhum número vem de dado real.
"""

from __future__ import annotations

# Motivos de reprovação (código fechado). A descrição de cada um está em docs/metricas/checagens-feedback.md.
MOTIVOS = (
    "numero_fora_do_pacote",  # número (ou data) que não é valor nem texto do pacote
    "numero_por_extenso",  # "cinco", "metade", "dobro": o número escaparia da conferência escrito em palavras
    "unidade_trocada",  # o número está no pacote, mas com outra unidade ("5:44 bpm")
    "linguagem_diagnostico",
    "linguagem_culpa",
    "linguagem_promessa",
    "linguagem_causa",
    "linguagem_conselho",
    "linguagem_quem_fala",  # primeira pessoa, professor, IA, exclamação, emoji
    "elogio_sem_fato",  # elogio que nenhum fato do pacote sustenta
    "forma_linhas",  # fora de 3 a 5 linhas
    "forma_tamanho_linha",  # linha com mais de 140 caracteres (ou texto com mais de 700)
    "forma_markdown",  # lista, título ou Markdown
    "forma_sem_verbo",  # linha que é só uma lista de valores, sem verbo conjugado (#355)
    "conclusao_repetida",  # a mesma conclusão ("dentro do seu normal") em duas linhas (#355)
    "comparacao_mediana",  # "dentro da mediana de X": o certo é "perto da mediana" ou "dentro do seu normal" (#355)
    "numero_repetido",  # o mesmo número repetido entre parênteses: "esforço 6 (6)" (#367)
    "dor_regra",  # com o atalho dor: falta a frase exata, ou há outra menção a dor ou a parte do corpo
    "dor_nao_marcada",  # fala em dor sem o atalho
    "atalho_nao_marcado",  # cita um atalho (calor, cansaço, sono ruim, trabalho ou estresse) que o atleta não marcou
    "nome_fora_do_pacote",  # nome próprio ou texto que não vem do pacote
)

BONS: dict[str, tuple[str, str]] = {
    # --- os 6 exemplos da ADR 0013, palavra por palavra ---
    "G01": ("F01", """Seu pace médio foi 5:44/km, perto da mediana de 5:48/km nos 11 treinos leves das últimas 12 semanas.
A FC média foi 146 bpm e a carga por hora, 49,1 pontos/h: ambas dentro do seu normal.
Você marcou esforço 4 (um pouco difícil), sensação 4 (bem) e nada a relatar.
Foram 47 min a 19 °C, com carga pela PSE de 188 UA."""),
    "G02": ("F02", """Seu melhor tiro foi 4:22/km, 13 s/km mais lento que a mediana de 4:09/km nos 10 treinos intervalados das últimas 12 semanas.
É uma comparação com o seu histórico, não um julgamento do treino.
A FC do melhor tiro foi 171 bpm, dentro do seu normal (mediana de 172 bpm).
Você registrou esforço 8 e sensação 3 (normal), sem nada a relatar.
Foram 5 tiros de 1 km e 416 UA de carga pela PSE."""),
    "G03": ("F03", """Ainda aprendendo o seu normal em treino moderado: 3 de 8 treinos nas últimas 12 semanas.
Sem comparação com o seu histórico por enquanto.
Seu pace médio foi 5:43/km e a FC média, 152 bpm.
Você marcou esforço 6, sensação 4 (bem) e sono ruim.
A carga pela PSE foi 240 UA em 40 min."""),
    "G04": ("F04", """Seu pace médio foi 6:00/km, 18 s/km mais lento que a mediana de 5:42/km nos 9 treinos longos das últimas 12 semanas.
A FC média foi 158 bpm, 8 bpm acima da mediana de 150 bpm.
O clima registrado foi 33 °C, com sensação térmica de 37 °C e umidade de 58%.
Você marcou calor e cansaço, esforço 7 (muito difícil) e sensação 2 (mal).
A carga pela PSE foi 630 UA em 90 min."""),
    "G05": ("F05", """Seu pace médio foi 6:00/km, perto da mediana de 5:56/km nos 10 treinos leves das últimas 12 semanas.
A FC média foi 139 bpm, dentro do seu normal.
Você registrou dor neste treino.
Esforço 3 (moderado) e sensação 3 (normal); a carga pela PSE foi 90 UA em 30 min."""),
    "G06": ("F06", """Natação de 1.600 m em 40 min, com FC média de 128 bpm.
Sem comparação com o seu histórico: o treino não tem tipo.
A natação não tem carga do relógio; a carga pela PSE foi 200 UA.
Você marcou esforço 5 (difícil), sensação 4 (bem) e nada a relatar."""),
    # --- outros bons ---
    # elogio sustentado por um fato (todas as métricas com valor estão dentro do normal), sem palavra de elogio
    "G07": ("F01", """Seu pace médio foi 5:44/km, perto da mediana de 5:48/km nos 11 treinos leves das últimas 12 semanas.
Todas as métricas de comparação ficaram dentro do seu normal.
Você marcou esforço 4 (um pouco difícil) e sensação 4 (bem), sem nada a relatar.
A carga pela PSE foi 188 UA em 47 min."""),
    # esteira: sem pace, clima não se aplica
    "G08": ("F09", """Treino leve na esteira de 30 min e 5,00 km, com FC média de 140 bpm.
Sem pace médio para comparar: o treino foi na esteira.
A FC média ficou dentro do seu normal (mediana de 142 bpm) e a carga por hora, em 40,0 pontos/h.
Você marcou esforço 5 (difícil), sensação 3 (normal) e trabalho ou estresse."""),
    # ciclismo sem tipo, clima e carga pendentes, PSE 0; o rótulo "muito bem" da sensação não é elogio
    "G09": ("F10", """Ciclismo de 28,00 km em 60 min, com FC média de 135 bpm.
Sem comparação com o seu histórico: o treino não tem tipo.
O clima e a carga do relógio ainda estão pendentes.
Você marcou esforço 0 (repouso), sensação 5 (muito bem) e nada a relatar; a carga pela PSE foi 0 UA."""),
    # dor: a frase exata no meio, sem conselho nem elogio em volta
    "G10": ("F05", """Seu pace médio foi 6:00/km, perto da mediana de 5:56/km nos 10 treinos leves das últimas 12 semanas.
Você registrou dor neste treino.
Você marcou esforço 3 (moderado) e sensação 3 (normal).
A carga pela PSE foi 90 UA em 30 min; a carga do relógio ainda está pendente."""),
    # clima e atalho calor lado a lado, sem ligação
    "G11": ("F04", """Seu pace médio foi 6:00/km, 18 s/km mais lento que a mediana de 5:42/km nos 9 treinos longos das últimas 12 semanas.
A FC média foi 158 bpm, 8 bpm acima da mediana de 150 bpm.
O clima registrado foi 33 °C e você marcou calor; os fatos aparecem lado a lado.
A carga pela PSE foi 630 UA em 90 min."""),
    # o rótulo da sensação do pacote ("muito bem") passa também fora de parênteses
    "G12": ("F10", """Ciclismo de 28,00 km em 60 min, com FC média de 135 bpm.
Sem comparação com o seu histórico: o treino não tem tipo.
Você marcou esforço 0 (repouso), sensação 5, muito bem, e nada a relatar.
A carga pela PSE foi 0 UA."""),
    # "quente" é o mesmo fato do atalho calor: passa quando o calor foi marcado; "mal" é o rótulo da sensação 2 do pacote
    "G13": ("F04", """Seu pace médio foi 6:00/km, 18 s/km mais lento que a mediana de 5:42/km nos 9 treinos longos das últimas 12 semanas.
A FC média foi 158 bpm, 8 bpm acima da mediana de 150 bpm.
Você marcou dia quente e cansaço, esforço 7 (muito difícil) e sensação 2, mal.
A carga pela PSE foi 630 UA em 90 min."""),
}


def _troca(bom: str, antigo: str, novo: str) -> str:
    texto = BONS[bom][1]
    assert texto.count(antigo) == 1, (bom, antigo)
    return texto.replace(antigo, novo)


def _ruim(bom: str, antigo: str, novo: str, motivo: str, porque: str) -> tuple[str, str, str, str]:
    assert motivo in MOTIVOS
    return (BONS[bom][0], _troca(bom, antigo, novo), motivo, porque)


# id -> (caso, texto, motivo esperado, por que reprova)
RUINS: dict[str, tuple[str, str, str, str]] = {
    # --- número fora do pacote ---
    "R01": _ruim("G01", "mediana de 5:48/km", "mediana de 5:30/km", "numero_fora_do_pacote", "5:30 não é valor nem texto do pacote"),
    "R02": _ruim("G01", "A FC média foi 146 bpm e a carga por hora, 49,1 pontos/h: ambas dentro do seu normal.",
                 "A FC média foi 146 bpm, 2 bpm abaixo da mediana de 148 bpm; a carga por hora foi 49,1 pontos/h.",
                 "numero_fora_do_pacote", "conta nova: o pacote não traz diferença para a FC dentro do normal"),
    "R03": _ruim("G04", "33 °C, com sensação térmica de 37 °C", "35 °C, com sensação térmica de 37 °C", "numero_fora_do_pacote", "temperatura inventada"),
    "R04": _ruim("G01", "Foram 47 min a 19 °C", "Foram 47 min a 19 °C, em 08/11/2026", "numero_fora_do_pacote", "data real (2026) não vai ao pacote nem ao texto"),
    # --- número por extenso ---
    "R05": _ruim("G02", "Foram 5 tiros de 1 km", "Foram cinco tiros de 1 km", "numero_por_extenso", "'cinco' escapa da conferência de números"),
    "R06": _ruim("G04", "A FC média foi 158 bpm, 8 bpm acima da mediana de 150 bpm.",
                 "A FC média foi 158 bpm, 8 bpm acima da mediana de 150 bpm, quase o dobro do normal.",
                 "numero_por_extenso", "'dobro' é uma conta escrita em palavras"),
    # --- unidade trocada ---
    "R07": _ruim("G01", "Seu pace médio foi 5:44/km", "Seu pace médio foi 5:44 bpm", "unidade_trocada", "5:44 está no pacote, mas em /km"),
    "R08": _ruim("G04", "umidade de 58%", "umidade de 58 km/h", "unidade_trocada", "58 é umidade (%), não vento"),
    # --- diagnóstico ---
    "R09": _ruim("G05", "Você registrou dor neste treino.", "Você registrou dor neste treino. Sinal de tendinite.", "linguagem_diagnostico", "'tendinite' é diagnóstico"),
    "R10": _ruim("G04", "A carga pela PSE foi 630 UA em 90 min.", "A carga pela PSE foi 630 UA em 90 min, sinal de desidratação.", "linguagem_diagnostico", "'desidratação' é diagnóstico"),
    # --- culpa e juízo ---
    "R11": _ruim("G04", "Seu pace médio foi 6:00/km,", "Foi um treino ruim: seu pace médio foi 6:00/km,", "linguagem_culpa", "'treino ruim' é juízo"),
    "R12": _ruim("G02", "É uma comparação com o seu histórico, não um julgamento do treino.", "Você falhou no melhor tiro.", "linguagem_culpa", "'falhou' é culpa"),
    # --- promessa ---
    "R13": _ruim("G01", "Foram 47 min a 19 °C, com carga pela PSE de 188 UA.", "Foram 47 min a 19 °C e no próximo treino você vai melhorar.", "linguagem_promessa", "'vai melhorar' é promessa"),
    "R14": _ruim("G02", "É uma comparação com o seu histórico, não um julgamento do treino.", "Com certeza o próximo treino é mais rápido.", "linguagem_promessa", "'com certeza' é promessa"),
    # --- causa afirmada ou sugerida ---
    "R15": _ruim("G04", "O clima registrado foi 33 °C, com sensação térmica de 37 °C e umidade de 58%.",
                 "O pace foi mais lento por causa do calor de 33 °C, com sensação térmica de 37 °C e umidade de 58%.",
                 "linguagem_causa", "'por causa do calor' liga o clima ao resultado"),
    "R16": _ruim("G04", "O clima registrado foi 33 °C, com sensação térmica de 37 °C e umidade de 58%.",
                 "O calor foi o que explica a FC mais alta: 33 °C, com sensação térmica de 37 °C e umidade de 58%.", "linguagem_causa", "'explica' afirma causa"),
    "R17": _ruim("G04", "O clima registrado foi 33 °C, com sensação térmica de 37 °C e umidade de 58%.",
                 "Provavelmente o clima pesou: 33 °C, com sensação térmica de 37 °C e umidade de 58%.", "linguagem_causa", "'provavelmente' sugere causa"),
    "R18": _ruim("G04", "Você marcou calor e cansaço,", "O pace ficou mais lento porque você marcou calor e cansaço,", "linguagem_causa", "'porque' liga o check-in ao resultado"),
    # --- conselho (inclusive sobre dor) ---
    "R19": _ruim("G05", "Você registrou dor neste treino.", "Você registrou dor neste treino. Descanse e procure um médico.", "linguagem_conselho", "conselho sobre dor"),
    "R20": _ruim("G04", "A carga pela PSE foi 630 UA em 90 min.", "A carga pela PSE foi 630 UA em 90 min; evite correr em dia quente.", "linguagem_conselho", "'evite' é conselho"),
    "R21": _ruim("G02", "É uma comparação com o seu histórico, não um julgamento do treino.", "O próximo intervalado é no mesmo ritmo, então tente manter.", "linguagem_conselho", "'tente' é conselho"),
    # --- quem fala ---
    "R22": _ruim("G01", "Foram 47 min a 19 °C, com carga pela PSE de 188 UA.", "Eu vi que foram 47 min a 19 °C, com carga pela PSE de 188 UA.", "linguagem_quem_fala", "primeira pessoa"),
    "R23": _ruim("G01", "Foram 47 min a 19 °C, com carga pela PSE de 188 UA.", "O treinador diz que foram 47 min a 19 °C, com carga pela PSE de 188 UA.", "linguagem_quem_fala", "o nome do professor só entra na Meta 10"),
    "R24": _ruim("G01", "Foram 47 min a 19 °C, com carga pela PSE de 188 UA.", "Foram 47 min a 19 °C, com carga pela PSE de 188 UA! 🏃", "linguagem_quem_fala", "exclamação e emoji"),
    # --- elogio sem fato ---
    "R25": _ruim("G04", "A carga pela PSE foi 630 UA em 90 min.", "Ótimo treino, e a carga pela PSE foi 630 UA em 90 min.", "elogio_sem_fato", "há métricas fora do normal: nenhum fato sustenta o elogio"),
    "R26": _ruim("G05", "A FC média foi 139 bpm, dentro do seu normal.", "A FC média foi 139 bpm, dentro do seu normal. Parabéns pelo treino.", "elogio_sem_fato", "com dor registrada não há elogio em volta"),
    "R27": _ruim("G03", "Sem comparação com o seu histórico por enquanto.", "Sem comparação com o seu histórico por enquanto, parabéns.", "elogio_sem_fato", "linha de base aprendendo: nada sustenta o elogio"),
    "R28": _ruim("G02", "É uma comparação com o seu histórico, não um julgamento do treino.", "O desempenho nos tiros foi excelente.", "elogio_sem_fato", "o melhor pace está fora do normal"),
    # --- forma ---
    "R29": ("F01", "Seu pace médio foi 5:44/km, perto da mediana de 5:48/km nos 11 treinos leves das últimas 12 semanas.\nVocê marcou esforço 4 (um pouco difícil).",
            "forma_linhas", "só 2 linhas"),
    "R30": _ruim("G01", "Foram 47 min a 19 °C, com carga pela PSE de 188 UA.",
                 "Foram 47 min a 19 °C.\nA carga pela PSE foi 188 UA.\nA carga por hora foi 49,1 pontos/h.", "forma_linhas", "6 linhas"),
    "R31": _ruim("G01", "Você marcou esforço 4 (um pouco difícil), sensação 4 (bem) e nada a relatar.",
                 "Você marcou esforço 4 (um pouco difícil), sensação 4 (bem) e nada a relatar, e a FC média foi 146 bpm, a carga por hora foi 49,1 pontos/h e foram 47 min.",
                 "forma_tamanho_linha", "linha com mais de 140 caracteres"),
    "R32": _ruim("G01", "Seu pace médio foi 5:44/km,", "**Seu pace médio** foi 5:44/km,", "forma_markdown", "Markdown em negrito"),
    "R33": _ruim("G01", "Foram 47 min a 19 °C, com carga pela PSE de 188 UA.", "- Foram 47 min a 19 °C, com carga pela PSE de 188 UA.", "forma_markdown", "item de lista"),
    # --- dor ---
    "R34": _ruim("G05", "Você registrou dor neste treino.", "Você registrou o treino.", "dor_regra", "o atalho dor está marcado e a frase exata não aparece"),
    "R35": _ruim("G05", "Você registrou dor neste treino.", "Você registrou dor no joelho neste treino.", "dor_regra", "parte do corpo; a frase tem de ser exata"),
    "R36": _ruim("G01", "Foram 47 min a 19 °C, com carga pela PSE de 188 UA.", "Você registrou dor neste treino.", "dor_nao_marcada", "fala em dor sem o atalho"),
    # --- atalho não marcado ---
    "R37": _ruim("G01", "Você marcou esforço 4 (um pouco difícil), sensação 4 (bem) e nada a relatar.",
                 "Você marcou esforço 4 (um pouco difícil), sensação 4 (bem) e cansaço.", "atalho_nao_marcado", "cansaço não foi marcado"),
    # --- nome ou texto que não vem do pacote ---
    "R38": _ruim("G01", "Foram 47 min a 19 °C, com carga pela PSE de 188 UA.", "Foram 47 min a 19 °C no Parque Exemplo, com carga pela PSE de 188 UA.", "nome_fora_do_pacote", "lugar: o pacote não traz posição nem nome de lugar"),
    "R39": _ruim("G05", "Esforço 3 (moderado) e sensação 3 (normal);", "Esforço 3 (moderado), sensação 3 (normal) e MARCADOR-SINTETICO-TEXTO-LIVRE;", "nome_fora_do_pacote", "repete o texto livre do check-in, que nunca vai ao pacote"),
    # --- revisão da Nina (11/11): termos e famílias que faltavam; um ruim por termo ---
    "R40": _ruim("G04", "A carga pela PSE foi 630 UA em 90 min.", "Fique atento: o ritmo foi esse.", "linguagem_conselho", "'fique atento'"),
    "R41": _ruim("G01", "Foram 47 min a 19 °C, com carga pela PSE de 188 UA.", "O treino foi longo, prefira treinos mais curtos.", "linguagem_conselho", "'prefira'"),
    "R42": _ruim("G01", "Foram 47 min a 19 °C, com carga pela PSE de 188 UA.", "O ritmo foi forte, considere poupar.", "linguagem_conselho", "'considere'"),
    "R43": _ruim("G01", "Foram 47 min a 19 °C, com carga pela PSE de 188 UA.", "O treino foi cedo, lembre-se de dormir mais.", "linguagem_conselho", "'lembre-se'"),
    "R44": _ruim("G01", "Foram 47 min a 19 °C, com carga pela PSE de 188 UA.", "O ritmo foi forte, priorize o leve.", "linguagem_conselho", "'priorize'"),
    "R45": _ruim("G01", "Foram 47 min a 19 °C, com carga pela PSE de 188 UA.", "O descanso é agora.", "linguagem_conselho", "'descanso'"),
    "R46": _ruim("G01", "Foram 47 min a 19 °C, com carga pela PSE de 188 UA.", "A recuperação é agora.", "linguagem_conselho", "'recuperação'"),
    "R47": _ruim("G01", "Foram 47 min a 19 °C, com carga pela PSE de 188 UA.", "Isso indica que o ritmo foi alto.", "linguagem_causa", "'indica que' liga fatos"),
    "R48": _ruim("G01", "Foram 47 min a 19 °C, com carga pela PSE de 188 UA.", "Isso mostra que o ritmo foi alto.", "linguagem_causa", "'mostra que' liga fatos"),
    "R49": _ruim("G01", "Foram 47 min a 19 °C, com carga pela PSE de 188 UA.", "Isso significa mais esforço e foi isso.", "linguagem_causa", "'significa'"),
    "R50": _ruim("G01", "Foram 47 min a 19 °C, com carga pela PSE de 188 UA.", "A FC é reflexo do esforço.", "linguagem_causa", "'reflete'"),
    "R51": _ruim("G04", "A carga pela PSE foi 630 UA em 90 min.", "Foi reflexo do cansaço.", "linguagem_causa", "'reflexo'"),
    "R52": _ruim("G01", "Foram 47 min a 19 °C, com carga pela PSE de 188 UA.", "Em razão do vento, o ritmo foi menor.", "linguagem_causa", "'em razão'"),
    "R53": _ruim("G01", "Foram 47 min a 19 °C, com carga pela PSE de 188 UA.", "Esse é o motivo do pace.", "linguagem_causa", "'motivo'"),
    "R54": _ruim("G01", "Foram 47 min a 19 °C, com carga pela PSE de 188 UA.", "O efeito apareceu na FC.", "linguagem_causa", "'efeito'"),
    "R55": _ruim("G04", "A carga pela PSE foi 630 UA em 90 min.", "Foi sinal de fadiga.", "linguagem_diagnostico", "'fadiga'"),
    "R56": _ruim("G04", "A carga pela PSE foi 630 UA em 90 min.", "Foi sinal de esgotamento.", "linguagem_diagnostico", "'esgotamento'"),
    "R57": _ruim("G04", "A carga pela PSE foi 630 UA em 90 min.", "Foi sinal de exaustão.", "linguagem_diagnostico", "'exaustão'"),
    "R58": _ruim("G04", "A carga pela PSE foi 630 UA em 90 min.", "Foi risco no ritmo.", "linguagem_diagnostico", "'risco'"),
    "R59": _ruim("G04", "A carga pela PSE foi 630 UA em 90 min.", "O pace é preocupante.", "linguagem_culpa", "'preocupante' é juízo"),
    "R60": _ruim("G04", "A carga pela PSE foi 630 UA em 90 min.", "Foi um alerta.", "linguagem_culpa", "'alerta' é juízo"),
    "R61": _ruim("G04", "A carga pela PSE foi 630 UA em 90 min.", "Foi um problema no pace.", "linguagem_culpa", "'problema' é juízo"),
    "R62": _ruim("G04", "A carga pela PSE foi 630 UA em 90 min.", "Foi um pior treino.", "linguagem_culpa", "'pior' é juízo"),
    "R63": _ruim("G04", "A carga pela PSE foi 630 UA em 90 min.", "Foi um erro de ritmo.", "linguagem_culpa", "'erro' é juízo"),
    "R64": _ruim("G01", "Foram 47 min a 19 °C, com carga pela PSE de 188 UA.", "O treino foi mal.", "linguagem_culpa", "'mal' só passa como rótulo da sensação do pacote (aqui a sensação é 'bem')"),
    "R65": _ruim("G02", "É uma comparação com o seu histórico, não um julgamento do treino.", "Você evoluiu nos tiros.", "elogio_sem_fato", "'evoluiu' sem fato (melhor pace fora do normal)"),
    "R66": _ruim("G02", "É uma comparação com o seu histórico, não um julgamento do treino.", "É hora de superar o normal.", "elogio_sem_fato", "'superar' sem fato"),
    "R67": _ruim("G02", "É uma comparação com o seu histórico, não um julgamento do treino.", "É hora de melhorar o tiro.", "elogio_sem_fato", "'melhorar' sem fato"),
    "R68": _ruim("G04", "A carga pela PSE foi 630 UA em 90 min.", "Você foi muito bem.", "elogio_sem_fato", "'muito bem' que não é o rótulo da sensação do pacote (aqui 'mal')"),
    "R69": _ruim("G01", "Foram 47 min a 19 °C, com carga pela PSE de 188 UA.", "Vamos ver o que foi o treino.", "linguagem_quem_fala", "'vamos' é primeira pessoa"),
    "R70": _ruim("G01", "Foram 47 min a 19 °C, com carga pela PSE de 188 UA.", "Estou vendo o treino.", "linguagem_quem_fala", "'estou' é primeira pessoa"),
    "R71": _ruim("G01", "Foram 47 min a 19 °C, com carga pela PSE de 188 UA.", "Foi um dia quente.", "atalho_nao_marcado", "'quente' é o fato do atalho calor, que não foi marcado"),
    "R72": _ruim("G01", "Foram 47 min a 19 °C, com carga pela PSE de 188 UA.", "Foi um dia frio.", "nome_fora_do_pacote", "'frio' não está no pacote (ele traz só o °C)"),
    # --- checagens_feedback@2 (#355): forma pedida pelo Angelo em 11/11; formatos vistos no provedor, escritos com números do oráculo ---
    "R73": _ruim("G08", "A FC média ficou dentro do seu normal (mediana de 142 bpm) e a carga por hora, em 40,0 pontos/h.", "Treino indoor, carga do relógio 20,0 pontos e 150 UA pela PSE.", "forma_sem_verbo", "linha só com valores, sem verbo conjugado (formato visto no provedor)"),
    "R74": _ruim("G01", "Foram 47 min a 19 °C, com carga pela PSE de 188 UA.", "Duração de 47 min, distância de 8,20 km e FC média de 146 bpm.", "forma_sem_verbo", "lista de valores sem verbo"),
    "R75": _ruim("G04", "A carga pela PSE foi 630 UA em 90 min.", "Carga pela PSE de 630 UA, 90 min e 33 °C.", "forma_sem_verbo", "lista de valores sem verbo"),
    "R76": _ruim("G06", "Sem comparação com o seu histórico: o treino não tem tipo.", "Sem comparação com o seu histórico, pois o treino não tem tipo.", "linguagem_causa", "'pois' é palavra de causa"),
    "R77": _ruim("G08", "Sem pace médio para comparar: o treino foi na esteira.", "Sem pace médio para comparar, já que o treino foi na esteira.", "linguagem_causa", "'já que' é palavra de causa"),
    "R78": _ruim("G01", "A FC média foi 146 bpm e a carga por hora, 49,1 pontos/h: ambas dentro do seu normal.", "A FC média foi 146 bpm, dentro da mediana de 148 bpm.", "comparacao_mediana", "estado dentro: o certo é 'perto da mediana' ou 'dentro do seu normal'"),
    "R79": _ruim("G02", "A FC do melhor tiro foi 171 bpm, dentro do seu normal (mediana de 172 bpm).", "A FC do melhor tiro foi 171 bpm, dentro da mediana de 172 bpm.", "comparacao_mediana", "idem, na FC do melhor tiro"),
    "R80": _ruim("G01", "Foram 47 min a 19 °C, com carga pela PSE de 188 UA.", "Tudo ficou dentro do seu normal.", "conclusao_repetida", "'dentro do seu normal' na linha 2 e de novo na última"),
    "R81": _ruim("G01", "Foram 47 min a 19 °C, com carga pela PSE de 188 UA.", "A FC média ficou perto da mediana de 148 bpm.", "conclusao_repetida", "'perto da mediana' na linha 1 e de novo na última"),
    "R82": _ruim("G06", "A natação não tem carga do relógio; a carga pela PSE foi 200 UA.", "Foi sem comparação com o seu histórico.", "conclusao_repetida", "'sem comparação' dita em duas linhas"),
    # --- checagens_feedback@3 (#367): o número da PSE sem âncora repetido entre parênteses ---
    "R83": _ruim("G03", "esforço 6,", "esforço 6 (6),", "numero_repetido", "PSE 6 não tem rótulo: 'esforço 6 (6)'"),
    "R84": _ruim("G02", "esforço 8 e", "esforço 8 (8) e", "numero_repetido", "PSE 8 não tem rótulo: 'esforço 8 (8)'"),
}
