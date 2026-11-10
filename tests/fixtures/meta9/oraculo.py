"""Oráculo do pacote de fatos `fatos_treino@1` (issue #323, ADR 0013), escrito à mão, com dados 100% sintéticos.

Cada caso tem uma ENTRADA (o que o código já calcula: atividade, histórico por métrica, clima, carga, check-in) e o PACOTE esperado.
Nenhum número vem de IA nem de dado real, e nenhum check-in é real. O texto livre do check-in só existe na ENTRADA (com um marcador
sintético) e **nunca** pode aparecer no pacote.

As contas à mão da linha de base (`linha_base@2`: mediana, MAD, desvio = max(1,4826 x MAD, 2% x |mediana|), z = (valor - mediana) / desvio,
"fora" com |z| >= 2,5, mínimo de 8 treinos) estão nos comentários de ``LINHA_BASE_ESPERADA``. Os textos prontos (`*_texto`) usam os
mesmos formatos que a API já tem. Rascunho até a função pura (#324) existir.
"""

from __future__ import annotations

MARCADOR_TEXTO_LIVRE = "MARCADOR-SINTETICO-TEXTO-LIVRE"

# Chaves que nunca podem aparecer no pacote (nenhum identificador, data, posição ou texto livre).
NOMES_PROIBIDOS_NO_PACOTE = ("atleta", "atividade_id", "id", "nome", "inicio", "data", "lat", "lon", "posicao", "arquivo", "professor", "texto", "observacao")

# Chaves de cada bloco do pacote, na ordem do ADR 0013 (item 1). Ausente = None, nunca omitida.
CHAVES = {
    "pacote": ("versao", "treino", "linha_base", "esforcos", "clima", "carga", "carga_pse", "checkin"),
    "treino": ("modalidade", "tipo_treino", "parte_de_transicao", "ambiente", "duracao_s", "duracao_texto", "distancia_m", "distancia_texto", "fc_media_bpm"),
    "linha_base": ("versao", "estado", "motivo", "janela_semanas", "minimo_treinos", "metricas"),
    "metrica": ("chave", "estado", "valor_texto", "mediana_texto", "diferenca_texto", "n", "motivo"),
    "esforcos": ("versao", "treino_chave", "series"),
    "clima": ("estado", "temperatura_c", "sensacao_termica_c", "umidade_pct", "vento_kmh"),
    "carga": ("versao", "estado", "valor", "valor_texto", "metodo", "motivo"),
    "carga_pse": ("versao", "estado", "valor", "valor_texto"),
    "checkin": ("pse", "pse_texto", "sensacao_nivel", "sensacao_texto", "nada_a_relatar", "atalhos"),
}


def _m(chave, estado, valor_texto=None, mediana_texto=None, n=0, diferenca_texto=None, motivo=None):
    return {"chave": chave, "estado": estado, "valor_texto": valor_texto, "mediana_texto": mediana_texto,
            "diferenca_texto": diferenca_texto, "n": n, "motivo": motivo}


def _lb(metricas, estado="ok", motivo=None):
    return {"versao": "linha_base@2", "estado": estado, "motivo": motivo, "janela_semanas": 12, "minimo_treinos": 8,
            "metricas": metricas}


def _treino(modalidade, tipo, dur_s, dur_t, dist_m, dist_t, fc, ambiente=None):
    return {"modalidade": modalidade, "tipo_treino": tipo, "parte_de_transicao": False, "ambiente": ambiente,
            "duracao_s": dur_s, "duracao_texto": dur_t, "distancia_m": dist_m, "distancia_texto": dist_t, "fc_media_bpm": fc}


def _esf(series=(), chave=False):
    return {"versao": "esforcos@1", "treino_chave": chave, "series": [{"faixa_rotulo": r, "quantidade": q} for r, q in series]}


def _clima(t, s, u, v):
    return {"estado": "ok", "temperatura_c": t, "sensacao_termica_c": s, "umidade_pct": u, "vento_kmh": v}


def _clima_sem(estado):
    return {"estado": estado, "temperatura_c": None, "sensacao_termica_c": None, "umidade_pct": None, "vento_kmh": None}


def _carga(valor, texto, metodo):
    return {"versao": "carga@2", "estado": "calculada", "valor": valor, "valor_texto": texto, "metodo": metodo, "motivo": None}


CARGA_PENDENTE = {"versao": None, "estado": "pendente", "valor": None, "valor_texto": None, "metodo": None, "motivo": None}
CARGA_SEM_NATACAO = {"versao": "carga@2", "estado": "sem_carga", "valor": None, "valor_texto": None, "metodo": None,
                     "motivo": "modalidade_sem_carga"}


def _pse(valor):
    return {"versao": "carga_pse@1", "estado": "calculada", "valor": valor, "valor_texto": f"{valor} UA"}


def _ck(pse, pse_t, sens, sens_t, nada, atalhos=()):
    return {"pse": pse, "pse_texto": pse_t, "sensacao_nivel": sens, "sensacao_texto": sens_t, "nada_a_relatar": nada,
            "atalhos": list(atalhos)}


# --- ENTRADAS ---------------------------------------------------------------------------------------------------------------
# `historico`: valores da janela (um por treino anterior do mesmo tipo, um por semana). `melhor_tiro`: da tiros_1km@6.
# `clima`: (temperatura, sensação térmica, umidade, vento), ou o estado ("indoor", "pendente"), ou None (sem clima, natação).
# `checkin.texto` existe só aqui e NUNCA vai ao pacote.
ENTRADAS = {
    "F01": {"descricao": "corrida leve, tudo dentro do normal (exemplo 1 da ADR)",
            "atividade": {"modalidade": "corrida", "subtipo": None, "tipo_treino": "leve", "duracao_s": 2820, "distancia_m": 8200, "fc_media": 146},
            "historico": {"pace_medio": [336, 340, 344, 346, 348, 348, 350, 352, 354, 358, 362],
                          "fc_media": [144, 145, 146, 147, 148, 148, 149, 150, 151, 152, 153],
                          "carga_hora": [47.3, 48.1, 48.9, 49.5, 50.0, 50.3, 50.6, 51.0, 51.6, 52.2, 53.0]},
            "carga": 38.5, "clima": (19, 19, 62, 9),
            "checkin": {"pse": 4, "sensacao": 4, "nada_a_relatar": True, "atalhos": [], "texto": None}},
    "F02": {"descricao": "intervalado, melhor pace fora do normal (exemplo 2)",
            "atividade": {"modalidade": "corrida", "subtipo": None, "tipo_treino": "intervalado", "duracao_s": 3120, "distancia_m": 9500, "fc_media": 158},
            "melhor_tiro": {"pace_s_km": 262, "fc_bpm": 171}, "tiros": [("1 km", 5)],
            "historico": {"melhor_pace": [245, 246, 247, 248, 249, 249, 250, 251, 252, 253],
                          "fc_melhor_tiro": [168, 169, 170, 171, 172, 172, 173, 174, 175, 176],
                          "fc_media": [154, 155, 156, 157, 157, 157, 158, 159, 160, 161],
                          "carga_hora": [67.0, 68.0, 68.8, 69.4, 70.0, 70.0, 70.6, 71.2, 72.0, 73.0]},
            "carga": 61.3, "clima": (22, 23, 55, 12),
            "checkin": {"pse": 8, "sensacao": 3, "nada_a_relatar": True, "atalhos": [], "texto": None}},
    "F03": {"descricao": "moderado com linha de base aprendendo, 3 de 8 treinos (exemplo 3)",
            "atividade": {"modalidade": "corrida", "subtipo": None, "tipo_treino": "moderado", "duracao_s": 2400, "distancia_m": 7000, "fc_media": 152},
            "historico": {"pace_medio": [340, 345, 350], "fc_media": [150, 152, 154], "carga_hora": [50.0, 51.0, 53.0]},
            "carga": 34.8, "clima": (24, 25, 60, 7),
            "checkin": {"pse": 6, "sensacao": 4, "nada_a_relatar": False, "atalhos": ["sono_ruim"], "texto": None}},
    "F04": {"descricao": "longo com calor: pace e FC fora do normal, calor marcado (exemplo 4)",
            "atividade": {"modalidade": "corrida", "subtipo": None, "tipo_treino": "longo", "duracao_s": 5400, "distancia_m": 15000, "fc_media": 158},
            "historico": {"pace_medio": [338, 339, 340, 341, 342, 342, 343, 345, 346],
                          "fc_media": [147, 148, 149, 150, 150, 150, 151, 152, 153],
                          "carga_hora": [58.5, 59.0, 59.6, 60.2, 60.5, 60.9, 61.4, 62.0, 62.6]},
            "carga": 93.0, "clima": (33, 37, 58, 6),
            "checkin": {"pse": 7, "sensacao": 2, "nada_a_relatar": False, "atalhos": ["calor", "cansaco"], "texto": None}},
    "F05": {"descricao": "leve com o atalho dor e texto livre; carga ainda pendente (exemplo 5)",
            "atividade": {"modalidade": "corrida", "subtipo": None, "tipo_treino": "leve", "duracao_s": 1800, "distancia_m": 5000, "fc_media": 139},
            "historico": {"pace_medio": [350, 352, 353, 355, 356, 356, 357, 358, 360, 362],
                          "fc_media": [137, 138, 139, 140, 141, 141, 142, 143, 144, 145],
                          "carga_hora": [40.0, 41.0, 42.0, 40.5, 41.5, 39.5, 42.5, 41.2, 40.8, 41.8]},
            "carga": None, "clima": (21, 21, 50, 8),
            "checkin": {"pse": 3, "sensacao": 3, "nada_a_relatar": False, "atalhos": ["dor"], "texto": MARCADOR_TEXTO_LIVRE}},
    "F06": {"descricao": "natação sem tipo: sem linha de base, sem carga do relógio (exemplo 6)",
            "atividade": {"modalidade": "natacao", "subtipo": None, "tipo_treino": None, "duracao_s": 2400, "distancia_m": 1600, "fc_media": 128},
            "historico": {}, "carga": None, "clima": None,
            "checkin": {"pse": 5, "sensacao": 4, "nada_a_relatar": True, "atalhos": [], "texto": None}},
    "F07": {"descricao": "corrida sem check-in: não há pacote (o feedback só nasce depois do check-in)",
            "atividade": {"modalidade": "corrida", "subtipo": None, "tipo_treino": "leve", "duracao_s": 2700, "distancia_m": 7500, "fc_media": 140},
            "historico": {}, "carga": 30.0, "clima": (20, 20, 60, 5), "checkin": None},
    "F08": {"descricao": "pai de treino multiesporte: não elegível, sem pacote",
            "atividade": {"modalidade": "corrida", "subtipo": "multiesporte_pai", "tipo_treino": None, "duracao_s": 5400, "distancia_m": 20000, "fc_media": 150},
            "historico": {}, "carga": None, "clima": None,
            "checkin": {"pse": 5, "sensacao": 3, "nada_a_relatar": True, "atalhos": [], "texto": None}},
    "F09": {"descricao": "esteira: clima indoor, pace médio sem valor",
            "atividade": {"modalidade": "corrida", "subtipo": "esteira", "tipo_treino": "leve", "duracao_s": 1800, "distancia_m": 5000, "fc_media": 140},
            "historico": {"pace_medio": [], "fc_media": [138, 139, 140, 141, 142, 142, 143, 144, 145],
                          "carga_hora": [38.0, 38.8, 39.4, 40.0, 40.5, 41.0, 41.6, 42.2, 43.0]},
            "carga": 20.0, "clima": "indoor",
            "checkin": {"pse": 5, "sensacao": 3, "nada_a_relatar": False, "atalhos": ["trabalho_estresse"], "texto": None}},
    "F10": {"descricao": "ciclismo sem tipo, clima e carga pendentes, PSE 0",
            "atividade": {"modalidade": "ciclismo", "subtipo": None, "tipo_treino": None, "duracao_s": 3600, "distancia_m": 28000, "fc_media": 135},
            "historico": {}, "carga": None, "clima": "pendente",
            "checkin": {"pse": 0, "sensacao": 5, "nada_a_relatar": True, "atalhos": [], "texto": None}},
}

# Quem não tem pacote: sem check-in ou não elegível.
SEM_PACOTE = ("F07", "F08")

# --- LINHA DE BASE ESPERADA, contas à mão ---------------------------------------------------------------------------------
# (id, chave) -> (estado, n, mediana, desvio, z). Mediana e MAD do histórico acima; desvio = max(1,4826 x MAD, 0,02 x mediana).
# F01 pace: mediana 348, MAD 4 (5,93), piso 6,96 -> desvio 6,96; valor 2820/8200 x 1000 = 343,902; z = -4,098/6,96 = -0,589.
# F01 fc: mediana 148, MAD 2 (2,965), piso 2,96 -> 2,965; z = -2/2,965 = -0,675.
# F01 carga/h: valor 38,5/(2820/3600) = 49,149; mediana 50,3, MAD 1,3 (1,927); z = -1,151/1,927 = -0,597.
# F02 melhor pace: mediana 249, MAD 2 (2,965), piso 4,98 -> 4,98; z = 13/4,98 = 2,610 -> fora.
# F02 fc melhor tiro: mediana 172, MAD 2, piso 3,44 -> 3,44; z = -1/3,44 = -0,291.
# F02 fc media: mediana 157, MAD 1,5 (2,224), piso 3,14 -> 3,14; z = 1/3,14 = 0,318.
# F02 carga/h: valor 61,3/(3120/3600) = 70,731; mediana 70, MAD 1,2 (1,779), piso 1,4; z = 0,731/1,779 = 0,411.
# F04 pace: mediana 342, MAD 2 (2,965), piso 6,84 -> 6,84; valor 360; z = 18/6,84 = 2,632 -> fora.
# F04 fc: mediana 150, MAD 1 (1,483), piso 3,0 -> 3,0; z = 8/3 = 2,667 -> fora.
# F04 carga/h: valor 93/1,5 = 62,0; mediana 60,5, MAD 0,9 (1,334), piso 1,21; z = 1,5/1,334 = 1,124.
# F05 pace: valor 360; mediana 356, MAD 2,5 (3,707), piso 7,12 -> 7,12; z = 4/7,12 = 0,562.
# F05 fc: valor 139; mediana 141, MAD 2 (2,965), piso 2,82; z = -2/2,965 = -0,675.
# F09 fc: valor 140; mediana 142, MAD 2 (2,965), piso 2,84; z = -0,675. F09 carga/h: valor 20/0,5 = 40,0; mediana 40,5, MAD 1,1 (1,631); z = -0,307.
LINHA_BASE_ESPERADA = {
    ("F01", "pace_medio"): ("dentro", 11, 348.0, 6.96, -0.589),
    ("F01", "fc_media"): ("dentro", 11, 148.0, 2.965, -0.675),
    ("F01", "carga_hora"): ("dentro", 11, 50.3, 1.927, -0.597),
    ("F02", "melhor_pace"): ("fora", 10, 249.0, 4.98, 2.610),
    ("F02", "fc_melhor_tiro"): ("dentro", 10, 172.0, 3.44, -0.291),
    ("F02", "fc_media"): ("dentro", 10, 157.0, 3.14, 0.318),
    ("F02", "carga_hora"): ("dentro", 10, 70.0, 1.779, 0.411),
    ("F03", "pace_medio"): ("aprendendo", 3, None, None, None),
    ("F03", "fc_media"): ("aprendendo", 3, None, None, None),
    ("F03", "carga_hora"): ("aprendendo", 3, None, None, None),
    ("F04", "pace_medio"): ("fora", 9, 342.0, 6.84, 2.632),
    ("F04", "fc_media"): ("fora", 9, 150.0, 3.0, 2.667),
    ("F04", "carga_hora"): ("dentro", 9, 60.5, 1.334, 1.124),
    ("F05", "pace_medio"): ("dentro", 10, 356.0, 7.12, 0.562),
    ("F05", "fc_media"): ("dentro", 10, 141.0, 2.965, -0.675),
    ("F05", "carga_hora"): ("sem_valor", 10, None, None, None),  # carga pendente
    ("F09", "pace_medio"): ("sem_valor", 0, None, None, None),  # esteira
    ("F09", "fc_media"): ("dentro", 9, 142.0, 2.965, -0.675),
    ("F09", "carga_hora"): ("dentro", 9, 40.5, 1.631, -0.307),
}

_V = "fatos_treino@1"

# --- PACOTES ESPERADOS ------------------------------------------------------------------------------------------------------
PACOTES = {
    "F01": {"versao": _V,
            "treino": _treino("corrida", "leve", 2820, "47 min", 8200, "8,20 km", 146),
            "linha_base": _lb([_m("pace_medio", "dentro", "5:44/km", "5:48/km", 11),
                               _m("fc_media", "dentro", "146 bpm", "148 bpm", 11),
                               _m("carga_hora", "dentro", "49,1 pontos/h", "50,3 pontos/h", 11)]),
            "esforcos": _esf(), "clima": _clima(19, 19, 62, 9), "carga": _carga(38.5, "38,5 pontos", "rtss"),
            "carga_pse": _pse(188), "checkin": _ck(4, "um pouco difícil", 4, "bem", True)},
    "F02": {"versao": _V,
            "treino": _treino("corrida", "intervalado", 3120, "52 min", 9500, "9,50 km", 158),
            "linha_base": _lb([_m("melhor_pace", "fora", "4:22/km", "4:09/km", 10, diferenca_texto="13 s/km mais lento"),
                               _m("fc_melhor_tiro", "dentro", "171 bpm", "172 bpm", 10),
                               _m("fc_media", "dentro", "158 bpm", "157 bpm", 10),
                               _m("carga_hora", "dentro", "70,7 pontos/h", "70,0 pontos/h", 10)]),
            "esforcos": _esf([("1 km", 5)]), "clima": _clima(22, 23, 55, 12), "carga": _carga(61.3, "61,3 pontos", "rtss"),
            "carga_pse": _pse(416), "checkin": _ck(8, "8", 3, "normal", True)},
    "F03": {"versao": _V,
            "treino": _treino("corrida", "moderado", 2400, "40 min", 7000, "7,00 km", 152),
            "linha_base": _lb([_m("pace_medio", "aprendendo", "5:43/km", None, 3),
                               _m("fc_media", "aprendendo", "152 bpm", None, 3),
                               _m("carga_hora", "aprendendo", "52,2 pontos/h", None, 3)]),
            "esforcos": _esf(), "clima": _clima(24, 25, 60, 7), "carga": _carga(34.8, "34,8 pontos", "hrtss"),
            "carga_pse": _pse(240), "checkin": _ck(6, "6", 4, "bem", False, ["sono_ruim"])},
    "F04": {"versao": _V,
            "treino": _treino("corrida", "longo", 5400, "90 min", 15000, "15,00 km", 158),
            "linha_base": _lb([_m("pace_medio", "fora", "6:00/km", "5:42/km", 9, diferenca_texto="18 s/km mais lento"),
                               _m("fc_media", "fora", "158 bpm", "150 bpm", 9, diferenca_texto="8 bpm acima"),
                               _m("carga_hora", "dentro", "62,0 pontos/h", "60,5 pontos/h", 9)]),
            "esforcos": _esf(), "clima": _clima(33, 37, 58, 6), "carga": _carga(93.0, "93,0 pontos", "rtss"),
            "carga_pse": _pse(630), "checkin": _ck(7, "muito difícil", 2, "mal", False, ["calor", "cansaco"])},
    "F05": {"versao": _V,
            "treino": _treino("corrida", "leve", 1800, "30 min", 5000, "5,00 km", 139),
            "linha_base": _lb([_m("pace_medio", "dentro", "6:00/km", "5:56/km", 10),
                               _m("fc_media", "dentro", "139 bpm", "141 bpm", 10),
                               _m("carga_hora", "sem_valor", None, None, 10, motivo="carga_pendente")]),
            "esforcos": _esf(), "clima": _clima(21, 21, 50, 8), "carga": CARGA_PENDENTE,
            "carga_pse": _pse(90), "checkin": _ck(3, "moderado", 3, "normal", False, ["dor"])},
    "F06": {"versao": _V,
            "treino": _treino("natacao", None, 2400, "40 min", 1600, "1.600 m", 128),
            "linha_base": _lb([], estado="sem_linha_base", motivo="sem_tipo"),
            "esforcos": None, "clima": None, "carga": CARGA_SEM_NATACAO,
            "carga_pse": _pse(200), "checkin": _ck(5, "difícil", 4, "bem", True)},
    "F07": None,
    "F08": None,
    "F09": {"versao": _V,
            "treino": _treino("corrida", "leve", 1800, "30 min", 5000, "5,00 km", 140, ambiente="esteira"),
            "linha_base": _lb([_m("pace_medio", "sem_valor", None, None, 0, motivo="esteira"),
                               _m("fc_media", "dentro", "140 bpm", "142 bpm", 9),
                               _m("carga_hora", "dentro", "40,0 pontos/h", "40,5 pontos/h", 9)]),
            "esforcos": _esf(), "clima": _clima_sem("indoor"), "carga": _carga(20.0, "20,0 pontos", "hrtss"),
            "carga_pse": _pse(150), "checkin": _ck(5, "difícil", 3, "normal", False, ["trabalho_estresse"])},
    "F10": {"versao": _V,
            "treino": _treino("ciclismo", None, 3600, "60 min", 28000, "28,00 km", 135),
            "linha_base": _lb([], estado="sem_linha_base", motivo="sem_tipo"),
            "esforcos": _esf(), "clima": _clima_sem("pendente"), "carga": CARGA_PENDENTE,
            "carga_pse": _pse(0), "checkin": _ck(0, "repouso", 5, "muito bem", True)},
}
