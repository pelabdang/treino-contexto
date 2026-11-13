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


def _t(*linhas):
    return "\n".join(linhas)


BONS = {
    "B01": ("R01", _t(L1, L2, SONO, FC_VFC, CK)),
    "B02": ("R01", _t(L1, SONO, "Na noite anterior, a FC de repouso foi 58 bpm, 6 bpm acima do seu normal de 52 bpm.", L2, CK)),
    "B03": ("R02", _t(L1, L2, "Na noite anterior você dormiu 6 h 20 min. Ainda aprendendo o seu normal de sono: 13 de 14 noites.", CK)),
    "B04": ("R04", _t(L1, L2, "Sem dado de sono, VFC e FC de repouso da noite anterior.", CK)),
    "B05": ("R05", _t(L1, L2, CK, CLIMA)),  # madrugada: o texto omite a recuperação
    "B06": ("R01", _t(L1, L2, CK, CLIMA)),  # estado ok, mas o texto pode omitir
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
    "M25": ("R01", _t(L1, L2, "Seu sono ruim marcado combina com 5 h 45 min na noite anterior.", CK), "linguagem_julgamento"),
}
