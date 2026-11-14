"""Textos à mão para a checagem do estado do clima (`checagens_feedback@6`, issue #405). Tudo SINTÉTICO.

Cada caso é conferido contra o pacote F01 da meta 9 com o bloco `clima` trocado pelo estado do caso (``CLIMAS``). ``BONS``: (estado, texto) que
precisa passar; ``RUINS``: (estado, texto, motivo esperado) que precisa reprovar. As linhas fixas são as do G01 da meta 9.
"""

L1 = "Seu pace médio foi 5:44/km, perto da mediana de 5:48/km nos 11 treinos leves das últimas 12 semanas."
L2 = "A FC média foi 146 bpm e a carga por hora, 49,1 pontos/h: ambas dentro do seu normal."
CK = "Você marcou esforço 4 (um pouco difícil), sensação 4 (bem) e nada a relatar."


def _sem(estado):
    return {"estado": estado, "temperatura_c": None, "sensacao_termica_c": None, "umidade_pct": None, "vento_kmh": None}


CLIMAS = {
    "ok": {"estado": "ok", "temperatura_c": 19, "sensacao_termica_c": 19, "umidade_pct": 62, "vento_kmh": 9},
    "indoor": _sem("indoor"), "pendente": _sem("pendente"), "sem_posicao": _sem("sem_posicao"), "falha": _sem("falha"),
}


def _t(*linhas):
    return "\n".join(linhas)


BONS = {
    "C01": ("ok", _t(L1, L2, CK, "Foram 47 min a 19 °C, com umidade de 62%.")),
    "C02": ("ok", _t(L1, L2, CK, "O clima registrado foi 19 °C e a carga do relógio ainda está pendente.")),
    "C03": ("indoor", _t(L1, L2, CK, "O treino foi indoor, sem dados de clima.")),
    "C04": ("indoor", _t(L1, L2, CK, "Foram 47 min no treino indoor.")),  # "indoor" descreve o treino, sem falar de clima
    "C05": ("pendente", _t(L1, L2, CK, "O clima ainda está pendente.")),
    "C06": ("pendente", _t(L1, L2, CK, "O clima e a carga do relógio ainda estão pendentes.")),
    "C07": ("sem_posicao", _t(L1, L2, CK, "Sem a posição de início, sem dados de clima.")),
    "C08": ("falha", _t(L1, L2, CK, "Não foi possível obter o clima.")),
    "C09": ("indoor", _t(L1, L2, CK)),  # omitir o clima é permitido
}

RUINS = {
    # pacote com `clima.estado = indoor` e texto que diz "pendente"
    "X01": ("indoor", _t(L1, L2, CK, "O clima ainda está pendente."), "clima_estado"),
    "X02": ("indoor", _t(L1, L2, CK, "O clima e a carga do relógio ainda estão pendentes."), "clima_estado"),
    "X03": ("pendente", _t(L1, L2, CK, "O clima foi indoor."), "clima_estado"),
    "X04": ("ok", _t(L1, L2, CK, "O clima ainda está pendente."), "clima_estado"),
    "X05": ("pendente", _t(L1, L2, CK, "Foram 47 min a 19 °C."), "clima_estado"),
    "X06": ("indoor", _t(L1, L2, CK, "Foram 47 min a 19 °C, com umidade de 62%."), "clima_estado"),
    "X07": ("falha", _t(L1, L2, CK, "O clima ainda está pendente."), "clima_estado"),
    "X08": ("sem_posicao", _t(L1, L2, CK, "O clima falhou."), "clima_estado"),
    "X09": ("ok", _t(L1, L2, CK, "O clima está indisponível."), "clima_estado"),
    "X10": ("indoor", _t(L1, L2, CK, "O clima do treino indoor ainda está pendente."), "clima_estado"),
    "X12": ("indoor", _t(L1, L2, CK, "Sem a posição de início, sem dados de clima."), "clima_estado"),
    "X11": ("indoor", _t(L1, L2, CK, "Sensação térmica de 19 °C."), "clima_estado"),
}
