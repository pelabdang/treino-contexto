"""Textos à mão para as checagens da recuperação (`checagens_feedback@4`, issue #375, ADR 0014, item 6). Tudo SINTÉTICO.

Cada texto é conferido contra o pacote F01 da meta 9 (`tests/fixtures/meta9/oraculo.py`) com o bloco `recuperacao` trocado pelo de um caso do oráculo
da meta 10 (`oraculo_fatos_recuperacao.py`: R01 sono abaixo, VFC dentro, FC de repouso acima; R02 sono aprendendo; R04 sem noite; R05 madrugada).
``BONS``: (caso da recuperação, texto) que precisa passar. ``RUINS``: (caso, texto, motivo esperado) que precisa reprovar com aquele motivo.
Os números dos textos bons são os do pacote: 5 h 45 min, 7 h 15 min, 1 h 30 min abaixo; VFC 41 ms; FC de repouso 58 bpm, 6 bpm acima do normal de 52 bpm.
"""

L1 = "Seu pace médio foi 5:44/km, perto da mediana de 5:48/km nos 11 treinos leves das últimas 12 semanas."
L2 = "A FC média foi 146 bpm e a carga por hora, 49,1 pontos/h: ambas dentro do seu normal."
CK = "Você marcou esforço 4 (um pouco difícil), sensação 4 (bem) e nada a relatar."
CLIMA = "Foram 47 min a 19 °C, com carga pela PSE de 188 UA."
SONO = "Na noite anterior você dormiu 5 h 45 min, 1 h 30 min abaixo do seu normal de 7 h 15 min."
FC_VFC = "A FC de repouso foi 58 bpm, 6 bpm acima do seu normal de 52 bpm, e a VFC foi 41 ms, dentro do seu normal."


# Recuperação em DUAS linhas (feedback_prompt@6, #394): sono numa, FC de repouso e VFC na outra.
DUAS_LINHAS_FC_VFC = "A FC de repouso foi 58 bpm, 6 bpm acima do seu normal de 52 bpm, e a VFC, 41 ms, dentro do seu normal."
# Caso só com a VFC (sono e FC de repouso sem dado na noite): bloco à mão, números sintéticos (normal 47 ms, hoje 46 ms).
BLOCOS_EXTRA = {
    # U03: as três medidas aprendendo (9 de 14 noites): valores sem normal nem comparação
    "U03": {"versao": "recuperacao@1", "estado": "ok", "motivo": None, "janela_noites": 28, "minimo_noites": 14, "medidas": [
        {"chave": "sono", "estado": "aprendendo", "valor": 22800, "valor_texto": "6 h 20 min", "normal_texto": None, "diferenca_texto": None, "n": 9},
        {"chave": "vfc", "estado": "aprendendo", "valor": 47, "valor_texto": "47 ms", "normal_texto": None, "diferenca_texto": None, "n": 9},
        {"chave": "fc_repouso", "estado": "aprendendo", "valor": 52, "valor_texto": "52 bpm", "normal_texto": None, "diferenca_texto": None, "n": 9}]},
    # U02: as três dentro do normal (sono 7 h 20 min contra 7 h 15 min; VFC 46 ms contra 47 ms; FC de repouso 52 bpm contra 52 bpm)
    "U02": {"versao": "recuperacao@1", "estado": "ok", "motivo": None, "janela_noites": 28, "minimo_noites": 14, "medidas": [
        {"chave": "sono", "estado": "dentro", "valor": 26400, "valor_texto": "7 h 20 min", "normal_texto": "7 h 15 min", "diferenca_texto": None, "n": 14},
        {"chave": "vfc", "estado": "dentro", "valor": 46, "valor_texto": "46 ms", "normal_texto": "47 ms", "diferenca_texto": None, "n": 14},
        {"chave": "fc_repouso", "estado": "dentro", "valor": 52, "valor_texto": "52 bpm", "normal_texto": "52 bpm", "diferenca_texto": None, "n": 14}]},
    "U01": {"versao": "recuperacao@1", "estado": "ok", "motivo": None, "janela_noites": 28, "minimo_noites": 14, "medidas": [
        {"chave": "sono", "estado": "sem_dado", "valor": None, "valor_texto": None, "normal_texto": None, "diferenca_texto": None, "n": 0},
        {"chave": "vfc", "estado": "dentro", "valor": 46, "valor_texto": "46 ms", "normal_texto": "47 ms", "diferenca_texto": None, "n": 14},
        {"chave": "fc_repouso", "estado": "sem_dado", "valor": None, "valor_texto": None, "normal_texto": None, "diferenca_texto": None, "n": 0}]},
}


def _t(*linhas):
    return "\n".join(linhas)


BONS = {
    "B01": ("R01", _t(L1, L2, SONO, FC_VFC, CK)),
    "B02": ("R01", _t(L1, SONO, "Na noite anterior, a FC de repouso foi 58 bpm, 6 bpm acima do seu normal de 52 bpm.", L2, CK)),
    "B03": ("R02", _t(L1, L2, "Na noite anterior você dormiu 6 h 20 min. Ainda aprendendo o seu normal de sono: 13 de 14 noites.", CK)),
    "B04": ("R04", _t(L1, L2, "Sem dado de sono, VFC e FC de repouso da noite anterior.", CK)),
    "B05": ("R05", _t(L1, L2, CK, CLIMA)),  # madrugada: o texto omite a recuperação
    "B06": ("R01", _t(L1, L2, CK, CLIMA)),  # estado ok, mas o texto pode omitir
    # @6: três medidas em duas linhas, com 5 linhas no total (pace, métricas, sono, FC de repouso e VFC, check-in)
    "B07": ("R01", _t(L1, L2, SONO, DUAS_LINHAS_FC_VFC, CK)),
    # @6: uma medida, uma linha
    "B08": ("U01", _t(L1, L2, "Na noite anterior, a VFC foi 46 ms, dentro do seu normal.", CK)),
    # @6: as três dentro, uma linha só (rodada da #394: duas linhas com "dentro do seu normal" repetiam a conclusão)
    "B10": ("U02", _t(L1, L2, "Na noite anterior você dormiu 7 h 20 min, a FC de repouso foi 52 bpm e a VFC, 46 ms: todas dentro do seu normal.", CK)),
    # @5 (#403): as três medidas aprendendo, com a frase obrigatória (duas linhas)
    "B11": ("U03", _t(L1, L2, "Na noite anterior você dormiu 6 h 20 min.", "A FC de repouso foi 52 bpm e a VFC, 47 ms. Ainda aprendendo o seu normal: 9 de 14 noites.", CK)),
    # @7 (rodada da #403): as três aprendendo em duas linhas curtas (numa linha só passam de 140 caracteres)
    "B13": ("U03", _t(L1, L2, "Na noite anterior você dormiu 6 h 20 min, a FC de repouso foi 52 bpm e a VFC, 47 ms.", "Ainda aprendendo o seu normal de sono, FC de repouso e VFC: 9 de 14 noites.", CK)),
    # @5: adjetivos sem gênero depois da sigla não são defeito ("FC maior", "FC menor")
    "B14": ("R01", _t(L1, "A FC maior do treino foi 171 bpm e a menor, 120 bpm: ambas dentro do seu normal.", CK)),
    # @5: concordância certa
    "B12": ("R01", _t(L1, "Sua FC média foi 146 bpm e a carga por hora, 49,1 pontos/h: ambas dentro do seu normal.", CK)),
    # @6: aprendendo com a noite anterior antes, e n de minimo_noites
    "B09": ("R02", _t(L1, L2, "Na noite anterior você dormiu 6 h 20 min.", "Ainda aprendendo o seu normal de sono: 13 de 14 noites.", CK)),
}

RUINS = {
    "M01": ("R01", _t(L1, L2, "Você correu mais devagar porque dormiu pouco.", CK), "linguagem_causa"),
    "M02": ("R01", _t(L1, L2, "Por isso, na noite anterior você dormiu 5 h 45 min.", CK), "linguagem_causa"),
    "M03": ("R01", _t(L1, L2, "Dormir mais pode ajudar nos próximos treinos.", CK), "linguagem_conselho"),
    "M04": ("R01", _t(L1, L2, "Na noite anterior você dormiu 5 h 45 min, mas o pace foi 5:44/km.", CK), "linguagem_causa"),
    "M05": ("R01", _t(L1, L2, "Com 5 h 45 min de sono, o ritmo caiu.", CK), "recuperacao_mistura"),
    "M06": ("R01", _t(L1, L2, "Na noite anterior o sono de 5 h 45 min veio com FC média de 146 bpm.", CK), "recuperacao_mistura"),
    "M07": ("R01", _t(L1, L2, "Seu sono foi ruim e sua VFC está baixa.", CK), "linguagem_julgamento"),
    "M08": ("R01", _t(L1, L2, "Foi uma noite ruim, com 5 h 45 min de sono.", CK), "linguagem_julgamento"),
    "M09": ("R01", _t(L1, L2, "Na noite anterior a VFC foi 41 ms, melhor que o seu normal.", CK), "linguagem_julgamento"),
    "M10": ("R01", _t(L1, L2, "Seu sono ficou 1,5 h abaixo do normal.", CK), "numero_fora_do_pacote"),
    "M11": ("R01", _t(L1, L2, "Na noite anterior você dormiu 5 h 40 min, 1 h 30 min abaixo do seu normal de 7 h 15 min.", CK), "numero_fora_do_pacote"),
    "M12": ("R01", _t(L1, L2, "Na noite anterior você dormiu seis horas.", CK), "numero_por_extenso"),
    "M13": ("R01", _t(L1, L2, "Nos últimos dias você dormiu menos.", CK), "recuperacao_outro_dia"),
    "M14": ("R01", _t(L1, L2, "Ontem à noite você dormiu 5 h 45 min.", CK), "recuperacao_outro_dia"),
    "M15": ("R01", _t(L1, L2, "Na noite anterior você dormiu 5 h 45 min, bem abaixo do normal.", CK), "recuperacao_forma"),
    "M16": ("R01", _t(L1, L2, "Você dormiu 5 h 45 min, 1 h 30 min abaixo do seu normal de 7 h 15 min.", CK), "recuperacao_forma"),
    "M17": ("R01", _t(L1, L2, "Na noite anterior você dormiu 5 h 45 min, 1 h 30 min acima do seu normal de 7 h 15 min.", CK), "recuperacao_forma"),
    "M18": ("R02", _t(L1, L2, "Na noite anterior você dormiu 6 h 20 min, abaixo do seu normal.", CK), "recuperacao_forma"),
    "M19": ("R02", _t(L1, L2, "Na noite anterior você dormiu 6 h 20 min. A VFC foi 41 ms.", CK), "recuperacao_forma"),
    "M20": ("R04", _t(L1, L2, "Na noite anterior você dormiu 5 h 45 min.", CK), "recuperacao_sem_pacote"),
    "M21": ("R05", _t(L1, L2, SONO, CK), "recuperacao_sem_pacote"),
    "M22": ("R05", _t(L1, L2, "Sem dado de sono, VFC e FC de repouso da noite anterior.", CK), "recuperacao_sem_pacote"),
    "M23": ("R01", _t(L1, L2, "A VFC mostra o sistema nervoso em recuperação.", CK), "linguagem_diagnostico"),
    "M24": ("R01", _t(L1, L2, "Na noite anterior você dormiu 5 h 45 min, sem prontidão para treinar.", CK), "linguagem_diagnostico"),
    # feedback_prompt@5 (rodada da #376): as três medidas numa linha passam de 140 caracteres
    "M26": ("R01", _t(L1, L2, "Na noite anterior você dormiu 5 h 45 min, 1 h 30 min abaixo do seu normal de 7 h 15 min, VFC 41 ms dentro do seu normal e FC de repouso 58 bpm, 6 bpm acima do seu normal de 52 bpm.", CK), "forma_tamanho_linha"),
    # aprendendo sem "noite anterior" (rodada da #376): reprova, o prompt@6 manda a frase do sono antes
    "M27": ("R02", _t(L1, L2, "Ainda aprendendo o seu normal de sono: 6 h 20 min.", CK), "recuperacao_forma"),
    # duas linhas, mas a de sono mistura o resultado
    "M28": ("R01", _t(L1, L2, "Na noite anterior você dormiu 5 h 45 min e correu a 5:44/km.", DUAS_LINHAS_FC_VFC, CK), "recuperacao_mistura"),
    # rodada da #394: duas linhas da recuperação, cada uma com "dentro do seu normal"
    "M29": ("U02", _t(L1, L2, "Na noite anterior você dormiu 7 h 20 min, dentro do seu normal.", "A FC de repouso foi 52 bpm e a VFC, 46 ms, dentro do seu normal.", CK), "conclusao_repetida"),
    # rodada da #394: diferença inventada em medida dentro
    "M30": ("U02", _t(L1, L2, "Na noite anterior você dormiu 7 h 20 min, 5 min acima do seu normal de 7 h 15 min.", "A FC de repouso foi 52 bpm e a VFC, 46 ms.", CK), "recuperacao_forma"),
    # checagens_feedback@5 (#403): aprendendo sem a frase que explica a falta de comparação (caso do feedback real, com valores sintéticos)
    "M31": ("R02", _t(L1, L2, "Na noite anterior você dormiu 6 h 20 min.", CK), "recuperacao_sem_aprendendo"),
    "M32": ("U03", _t(L1, L2, "Na noite anterior você dormiu 6 h 20 min.", "Na noite anterior a FC de repouso foi 52 bpm e a VFC, 47 ms.", CK), "recuperacao_sem_aprendendo"),
    # concordância das siglas femininas
    "M33": ("R01", _t("Seu FC médio foi 146 bpm.", L1, L2, CK), "concordancia_sigla"),
    "M34": ("R01", _t(L1, "O FC médio foi 146 bpm e a carga por hora, 49,1 pontos/h: ambas dentro do seu normal.", CK), "concordancia_sigla"),
    "M35": ("R01", _t(L1, L2, SONO, "Na noite anterior o VFC foi 41 ms, dentro do seu normal.", CK), "concordancia_sigla"),
    "M36": ("R01", _t(L1, "Foi um FC alto de 146 bpm e a carga por hora, 49,1 pontos/h: ambas dentro do seu normal.", CK), "concordancia_sigla"),
    # rodada da #403: as três aprendendo numa linha só passam de 140 caracteres
    "M37": ("U03", _t(L1, L2, "Na noite anterior você dormiu 6 h 20 min, a VFC foi 47 ms e a FC de repouso foi 52 bpm. Ainda aprendendo o seu normal de sono, VFC e FC de repouso: 9 de 14 noites.", CK), "forma_tamanho_linha"),
    "M25": ("R01", _t(L1, L2, "Seu sono ruim marcado combina com 5 h 45 min na noite anterior.", CK), "linguagem_julgamento"),
}
