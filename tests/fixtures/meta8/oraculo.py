"""Oráculo da Meta 8 (issue #294, ADR 0012): `carga_pse@1`, prazo, pendentes e validação do check-in, calculados à mão.

A função pura `carga_pse@1` (#297), o banco e a API (#296, #298) e o QA reaproveitam `PARAMETROS`, `CARGA_PSE_ESPERADA`,
`ELEGIVEL`, `PRAZO_CRIAR`, `PENDENTES` e `VALIDACAO`. Tabela legível em `docs/metricas/carga-pse-oraculo.md`. Nenhum número
vem de IA nem de dado real; os check-ins são sintéticos.

Fórmula (ADR 0012, item 6; regra própria do projeto sobre a sRPE de Foster et al., 2001, J. Strength Cond. Res. 15(1):109-115,
citação ainda a conferir): carga_pse = PSE x minutos, com minutos = duracao_s / 60 (tempo de cronômetro), em UA.
"""

PARAMETROS = {
    "PRAZO_DIAS": 7,  # A confirmar 1: criar até 7 dias depois do dia local do treino; janela [hoje - 7, hoje]
    "AGORA": "2026-11-09T15:00:00-03:00",
    "HOJE": "2026-11-09",
    "TEXTO_MAX": 500,
}

# Atividades que pedem check-in: toda modalidade, menos pai e troca do multiesporte.
NAO_ELEGIVEIS = {"2026-11-03/out1", "2026-11-03/out2", "2026-11-03/out3"}

# carga_pse@1 por atividade: (estado, minutos, valor). Estados: calculada | sem_checkin | sem_duracao | None (não elegível).
# Contas: valor = PSE x duracao_s / 60.
CARGA_PSE_ESPERADA = {
    "2026-10-15/cor1": ("calculada", 45.0, 225.0),  # PSE 5, 2700 s = 45 min -> 5 x 45 = 225 (editável sem prazo)
    "2026-11-01/cor1": ("sem_checkin", 50.0, None),
    "2026-11-01/cor2": ("sem_checkin", 50.0, None),
    "2026-11-02/cor1": ("sem_checkin", 50.0, None),
    "2026-11-03/cor1": ("sem_checkin", 20.0, None),
    "2026-11-03/nat1": ("calculada", 30.0, 150.0),  # PSE 5, 1800 s = 30 min -> 5 x 30 = 150 (natação: sem carga@2)
    "2026-11-03/cic1": ("calculada", 45.0, 270.0),  # PSE 6, 2700 s = 45 min -> 6 x 45 = 270
    "2026-11-04/cic1": ("sem_checkin", 60.0, None),
    "2026-11-05/cor1": ("sem_checkin", 45.0, None),
    "2026-11-06/out1": ("calculada", 30.0, 0.0),  # PSE 0 (repouso): carga 0, 1800 s = 30 min -> 0 x 30 = 0
    "2026-11-07/cor1": ("calculada", 2725 / 60, 272.5),  # PSE 6, 2725 s -> 45,41667 min -> 6 x 45,41667 = 272,5
    "2026-11-08/nat1": ("calculada", 40.0, 160.0),  # PSE 4, 2400 s = 40 min -> 4 x 40 = 160 (natação)
    "2026-11-08/cic1": ("calculada", 50.0, 350.0),  # PSE 7, 3000 s = 50 min -> 7 x 50 = 350 (pedal virtual)
    "2026-11-09/cor1": ("sem_duracao", 0.0, None),  # check-in com duracao_s = 0
    "2026-11-09/cor2": ("calculada", 45.0, 270.0),  # PSE 6, 2700 s = 45 min -> 6 x 45 = 270
    "2026-11-03/out1": None,  # multiesporte_pai
    "2026-11-03/out2": None,  # troca
    "2026-11-03/out3": None,  # troca
}

# Criar check-in em atividade sem check-in, às 15:00 de 09/11 (hoje = 09/11, janela de data local 02/11 a 09/11).
# A de 01/11 às 23:30 local já é 02/11 em UTC: vale a data local, então está fora do prazo.
PRAZO_CRIAR = {
    "2026-11-01/cor1": False,  # 01/11 < 02/11
    "2026-11-01/cor2": False,  # 23:30 local de 01/11 (02/11 em UTC): fora
    "2026-11-02/cor1": True,   # 02/11 = hoje - 7: dentro, e tem fuso nulo (America/Sao_Paulo)
    "2026-11-03/cor1": True,
    "2026-11-04/cic1": True,
    "2026-11-05/cor1": True,
    "2026-11-03/out1": None,   # não elegível: 422 atividade_sem_checkin
    "2026-11-03/out2": None,
    "2026-11-03/out3": None,
}

# Pendentes: elegíveis, sem check-in, data local >= hoje - dias, mais recentes primeiro. (relógio, dias) -> ids.
# Às 15:00 de 09/11, dias = 7: janela 02/11 a 09/11 -> 05/11, 04/11, 03/11 (corrida das 09:20) e 02/11.
# Às 00:01 de 10/11 (hoje = 10/11), dias = 7: janela 03/11 a 10/11 -> a de 02/11 sai.
# Com dias = 5 às 15:00 de 09/11: janela 04/11 a 09/11 -> 05/11 e 04/11. Com dias = 3: janela 06/11 a 09/11 -> nenhuma.
PENDENTES = {
    ("2026-11-09T15:00:00-03:00", 7): ["2026-11-05/cor1", "2026-11-04/cic1", "2026-11-03/cor1", "2026-11-02/cor1"],
    ("2026-11-10T00:01:00-03:00", 7): ["2026-11-05/cor1", "2026-11-04/cic1", "2026-11-03/cor1"],
    ("2026-11-09T15:00:00-03:00", 5): ["2026-11-05/cor1", "2026-11-04/cic1"],
    ("2026-11-09T15:00:00-03:00", 3): [],
}

# Validação do corpo do PUT (ADR 0012, itens 1, 2 e 7): (descrição, corpo, válido, motivo do 422).
_T = "Texto sintético."
VALIDACAO = [
    ("completo com atalhos e texto", {"pse": 6, "sensacao": 4, "nada_a_relatar": False, "atalhos": ["cansaco"], "texto": _T}, True, None),
    ("nada a relatar", {"pse": 3, "sensacao": 3, "nada_a_relatar": True, "atalhos": [], "texto": None}, True, None),
    ("só texto", {"pse": 3, "sensacao": 3, "nada_a_relatar": False, "atalhos": [], "texto": _T}, True, None),
    ("só atalho", {"pse": 10, "sensacao": 1, "nada_a_relatar": False, "atalhos": ["dor"], "texto": None}, True, None),
    ("PSE 0 e sensação 5", {"pse": 0, "sensacao": 5, "nada_a_relatar": True, "atalhos": [], "texto": None}, True, None),
    ("texto com exatamente 500 caracteres", {"pse": 5, "sensacao": 3, "nada_a_relatar": False, "atalhos": [], "texto": "a" * 500}, True, None),
    ("os cinco atalhos", {"pse": 5, "sensacao": 3, "nada_a_relatar": False,
                          "atalhos": ["dor", "cansaco", "sono_ruim", "calor", "trabalho_estresse"], "texto": None}, True, None),
    ("PSE 11", {"pse": 11, "sensacao": 3, "nada_a_relatar": True, "atalhos": [], "texto": None}, False, "pse"),
    ("PSE -1", {"pse": -1, "sensacao": 3, "nada_a_relatar": True, "atalhos": [], "texto": None}, False, "pse"),
    ("sensação 0", {"pse": 5, "sensacao": 0, "nada_a_relatar": True, "atalhos": [], "texto": None}, False, "sensacao"),
    ("sensação 6", {"pse": 5, "sensacao": 6, "nada_a_relatar": True, "atalhos": [], "texto": None}, False, "sensacao"),
    ("nada a relatar com atalho", {"pse": 5, "sensacao": 3, "nada_a_relatar": True, "atalhos": ["dor"], "texto": None}, False, "observacao"),
    ("nada a relatar com texto", {"pse": 5, "sensacao": 3, "nada_a_relatar": True, "atalhos": [], "texto": _T}, False, "observacao"),
    ("sem nada a relatar e sem atalho nem texto", {"pse": 5, "sensacao": 3, "nada_a_relatar": False, "atalhos": [], "texto": None}, False, "observacao"),
    ("texto só de espaços vira vazio", {"pse": 5, "sensacao": 3, "nada_a_relatar": False, "atalhos": [], "texto": "   "}, False, "observacao"),
    ("atalho desconhecido", {"pse": 5, "sensacao": 3, "nada_a_relatar": False, "atalhos": ["fome"], "texto": None}, False, "atalho"),
    ("atalho repetido", {"pse": 5, "sensacao": 3, "nada_a_relatar": False, "atalhos": ["dor", "dor"], "texto": None}, False, "atalho"),
    ("texto com 501 caracteres", {"pse": 5, "sensacao": 3, "nada_a_relatar": False, "atalhos": [], "texto": "a" * 501}, False, "texto"),
    ("sem PSE", {"sensacao": 3, "nada_a_relatar": True, "atalhos": [], "texto": None}, False, "obrigatorio"),
    ("sem sensação", {"pse": 3, "nada_a_relatar": True, "atalhos": [], "texto": None}, False, "obrigatorio"),
    ("sem nada_a_relatar", {"pse": 3, "sensacao": 3, "atalhos": [], "texto": None}, False, "obrigatorio"),
]
