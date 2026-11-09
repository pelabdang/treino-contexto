"""Oráculo da Meta 7 (issue #261, ADR 0011): tipo de treino, divergência e linha de base, calculados à mão.

As funções puras `tipo_treino@1` (#262) e `linha_base@1` (#263), a API (#264 a #266) e o QA reaproveitam
`PARAMETROS`, `TIPO_ESPERADO`, `SEM_LINHA_BASE` e `LINHA_BASE_ESPERADA`. A tabela legível está em
`docs/metricas/tipo-linha-base-oraculo.md`. Cada conta está comentada. Nenhum número vem de IA nem de dado real.

Fontes das fórmulas (ADR 0011, item 6): mediana e MAD no lugar de média e desvio padrão (Leys et al., 2013, J. Exp.
Soc. Psychol. 49(4):764-766); constante 1,4826 (Rousseeuw e Croux, 1993, JASA 88(424):1273-1283). Citações ainda a
conferir nos textos (ADR 0011, "Fontes").
"""

# Valores que dependem de "A confirmar" ou de calibração ficam aqui, um lugar só (ADR 0011).
PARAMETROS = {
    "JANELA_DIAS": 56,  # 8 semanas (Angelo, 09/11)
    "MINIMO_TREINOS": 8,  # (Angelo, 09/11)
    "LIMITE_FORA": 2.5,  # A confirmar 3
    "PISO_REL": 0.02,  # calibração #269
    "MAD_ESCALA": 1.4826,
    "LEVE_MIN_S": 1200,  # calibração #269
    "LONGO_MIN_S": 4500,  # calibração #269
    "DIVERGENTE_FORA_DA_BASE": True,  # A confirmar 2
    "TRANSICAO_FORA_DA_BASE": True,  # A confirmar 5
    "ATIVIDADE_DO_DIA": "maior_duracao",  # A confirmar 6
}

# (tipo, origem, divergência). `origem` None com tipo preenchido = tipo confirmado pelo atleta.
SEM = (None, None, None)
_T = {}


def _g(ids, valor):
    for i in ids:
        _T[i] = valor


def _datas(sigla, dias, n=1):
    return [f"2026-{d}/{sigla}{n}" for d in dias.split()]


# Segunda: natação 2000 m. Vigência A (item sem tipo) sem tipo; vigência B (desde 02/03) leve pelo plano. (E4)
_g(_datas("nat", "01-05 01-12 01-19 01-26 02-02 02-09 02-16 02-23"), SEM)
_g(_datas("nat", "03-02 03-09 03-16 03-23"), ("leve", "semana_padrao", None))

# Terça: intervalado pelo plano (E1). 01-06 é esteira (E8). 02-24 começa 23:10 local, quarta em UTC (E11).
_g(_datas("cor", "01-06 01-27 02-03 02-10 02-17 02-24 03-03 03-10 03-17 03-24"), ("intervalado", "semana_padrao", None))
_g(["2026-01-13/cor1"], ("intervalado", "semana_padrao", "sem_esforco"))  # plano diz intervalado, sem esforço (E3)
_g(["2026-01-13/cor2"], ("leve", "sugestao", None))  # 30 min sem esforço, perdeu o item (empate: a mais cedo leva)
_g(["2026-01-20/cor1"], SEM)  # 15 min solta, abaixo de LEVE_MIN_S; o item foi para a sessão de 50 min (E2)
_g(["2026-01-20/cor2"], ("intervalado", "semana_padrao", None))

# Quarta: ciclismo leve pelo plano (E9: 01-14 é pedal virtual).
_g(_datas("cic", "01-07 01-14 01-21 01-28 02-04 02-11 02-18 02-25 03-04 03-11 03-18 03-25"), ("leve", "semana_padrao", None))

# Quinta: fartlek pela vigência A, moderado pela B (E15). Tipos prévios não mudam (E13).
_g(["2026-01-08/cor1"], ("longo", "professor", None))
_g(["2026-01-15/cor1"], ("moderado", None, None))  # tipo confirmado pelo atleta
_g(["2026-01-29/cor1"], ("moderado", "trainingpeaks", None))
_g(_datas("cor", "01-22 02-05 02-12 02-19 02-26"), ("fartlek", "semana_padrao", None))  # 02-12 sem fuso_min (E12)
_g(_datas("cor", "03-05 03-12 03-19 03-26"), ("moderado", "semana_padrao", None))

# Sexta: sem item no plano. 01-09 tem tiros (E7); as demais, 8 km sem esforço, 40 min ou mais (E6).
_g(["2026-01-09/cor1"], ("intervalado", "sugestao", None))
_g(_datas("cor", "01-16 01-23 01-30 02-06 02-13 02-20 02-27 03-06 03-13 03-20 03-27"), ("leve", "sugestao", None))

# Sábado 01-10: multiesporte (E10). Pai e trocas nunca recebem tipo; cada parte encaixa pela sua modalidade.
_g(["2026-01-10/out1", "2026-01-10/out2", "2026-01-10/out3"], SEM)
_g(["2026-01-10/nat1"], SEM)  # sábado não tem item de natação
_g(["2026-01-10/cic1"], ("moderado", "semana_padrao", None))
_g(["2026-01-10/cor1"], ("longo", "semana_padrao", None))  # 20 min, mas o plano manda
# Sábados seguintes: longo pelo plano. 03-28 tem tiros: tipo do plano fica, divergência tem_tiros.
_g(_datas("cor", "01-17 01-24 01-31 02-07 02-14 02-21 02-28 03-07 03-14 03-21"), ("longo", "semana_padrao", None))
_g(["2026-03-28/cor1"], ("longo", "semana_padrao", "tem_tiros"))

# Domingo: 01-04 é antes da primeira vigência (E14); 01-11 tem item "corrida sem tipo" (E5). Ambos: reserva leve.
_g(["2026-01-04/cor1", "2026-01-11/cor1"], ("leve", "sugestao", None))

TIPO_ESPERADO = dict(_T)

# Atividades sem linha de base, com o motivo (ordem dos motivos: ADR 0011, item 7).
SEM_LINHA_BASE = {
    "2026-01-10/out1": "multiesporte",
    "2026-01-10/out2": "multiesporte",
    "2026-01-10/out3": "multiesporte",
    "2026-01-10/nat1": "sem_tipo",  # sem tipo e também transição: vale o primeiro motivo da ordem
    "2026-01-10/cic1": "transicao",
    "2026-01-10/cor1": "transicao",
    "2026-01-19/nat1": "sem_tipo",
    "2026-01-13/cor1": "divergente",
    "2026-03-28/cor1": "divergente",
    "2026-01-20/cor1": "sem_tipo",
}

# Linha de base esperada nas sessões-alvo: id -> métrica -> (estado, n, mediana, desvio, z).
# estado: fora | dentro | aprendendo | sem_valor. Para aprendendo e sem_valor, mediana, desvio e z são None.
# Contas (desvio = max(1,4826 x MAD, 0,02 x |mediana|); z = (valor - mediana) / desvio); janela de 56 dias, só antes da sessão.
LINHA_BASE_ESPERADA = {
    # E-L1: corrida leve 13/03 (306 s/km). Janela 16/01 a 13/03, 8 sextas: 330, 324, 336, 330, 342, 318, 330, 336.
    #   ordenados 318 324 330 330 330 336 336 342 -> mediana 330. |x - 330|: 0 0 0 6 6 6 12 12 -> MAD 6.
    #   desvio = max(8,8956; 6,6) = 8,8956. z = (306 - 330) / 8,8956 = -2,6980 -> fora.
    #   FC: só 5 das 8 têm FC (150, 148, 152, 146, 151) -> aprendendo (5 de 8). Carga: sem dados de saúde.
    "2026-03-13/cor1": {
        "pace_medio": ("fora", 8, 330.0, 8.8956, -2.69803),
        "fc_media": ("aprendendo", 5, None, None, None),
        "carga": ("sem_valor", 0, None, None, None),
    },
    # E-L2: corrida leve 20/03 (330 s/km). Janela 23/01 a 20/03: 324, 336, 330, 342, 318, 330, 336, 306.
    #   ordenados 306 318 324 330 330 336 336 342 -> mediana 330. |x - 330|: 24 12 6 0 0 6 6 12 -> ordenados 0 0 6 6 6 12 12 24 -> MAD 6.
    #   desvio 8,8956; z = 0 -> dentro. FC: 148, 152, 146, 151, 160 (5) -> aprendendo.
    "2026-03-20/cor1": {
        "pace_medio": ("dentro", 8, 330.0, 8.8956, 0.0),
        "fc_media": ("aprendendo", 5, None, None, None),
        "carga": ("sem_valor", 0, None, None, None),
    },
    # E-L3: corrida longa 14/03 (324 s/km). Janela 17/01 a 14/03, 8 sábados: 342, 336, 339, 333, 330, 336, 330, 333.
    #   ordenados 330 330 333 333 336 336 339 342 -> mediana (333 + 336) / 2 = 334,5.
    #   |x - 334,5|: 7,5 1,5 4,5 1,5 4,5 1,5 4,5 1,5 -> ordenados 1,5 1,5 1,5 1,5 4,5 4,5 4,5 7,5 -> MAD (1,5 + 4,5) / 2 = 3.
    #   1,4826 x 3 = 4,4478; piso 0,02 x 334,5 = 6,69 -> desvio 6,69 (o piso vale). z = (324 - 334,5) / 6,69 = -1,56951 -> dentro.
    #   FC: oito valores 145, MAD 0, desvio = 0,02 x 145 = 2,9; sessão 145 -> z 0.
    "2026-03-14/cor1": {
        "pace_medio": ("dentro", 8, 334.5, 6.69, -1.56951),
        "fc_media": ("dentro", 8, 145.0, 2.9, 0.0),
        "carga": ("sem_valor", 0, None, None, None),
    },
    # E-L4: corrida longa 21/03 (315 s/km). Janela 24/01 a 21/03: 336, 339, 333, 330, 336, 330, 333, 324.
    #   ordenados 324 330 330 333 333 336 336 339 -> mediana 333. |x - 333|: 3 6 0 3 3 3 0 9 -> ordenados 0 0 3 3 3 3 6 9 -> MAD 3.
    #   desvio = max(4,4478; 6,66) = 6,66. z = (315 - 333) / 6,66 = -2,70270 -> fora.
    "2026-03-21/cor1": {
        "pace_medio": ("fora", 8, 333.0, 6.66, -2.7027),
        "fc_media": ("dentro", 8, 145.0, 2.9, 0.0),
        "carga": ("sem_valor", 0, None, None, None),
    },
    # E-L5: intervalado 17/03, melhor tiro 249 s/km. Janela 20/01 a 17/03, 8 terças: 270, 264, 267, 261, 264, 258, 261, 255
    #   (01-13 é divergente e 01-06 está fora da janela).
    #   ordenados 255 258 261 261 264 264 267 270 -> mediana (261 + 264) / 2 = 262,5.
    #   |x - 262,5|: 7,5 1,5 4,5 1,5 1,5 4,5 1,5 7,5 -> ordenados 1,5 1,5 1,5 1,5 4,5 4,5 7,5 7,5 -> MAD 3.
    #   desvio = max(4,4478; 5,25) = 5,25. z = (249 - 262,5) / 5,25 = -2,57143 -> fora.
    #   FC do melhor tiro: 02-24 não tem FC -> 7 valores (172) -> aprendendo.
    "2026-03-17/cor1": {
        "melhor_pace": ("fora", 8, 262.5, 5.25, -2.57143),
        "fc_melhor_tiro": ("aprendendo", 7, None, None, None),
        "carga": ("sem_valor", 0, None, None, None),
    },
    # E-L6: intervalado 10/03. Janela 13/01 a 10/03: a de 13/01 é divergente (fora); sobram 01-20, 01-27, 02-03, 02-10,
    #   02-17, 02-24, 03-03 = 7 -> aprendendo.
    "2026-03-10/cor1": {
        "melhor_pace": ("aprendendo", 7, None, None, None),
        "fc_melhor_tiro": ("aprendendo", 6, None, None, None),
        "carga": ("sem_valor", 0, None, None, None),
    },
    # E-L7: ciclismo leve 18/03, carga 55, FC 133. Janela 21/01 a 18/03, 8 quartas: carga 40, 44, 42, 46, 38, 44, 42, 48.
    #   ordenados 38 40 42 42 44 44 46 48 -> mediana (42 + 44) / 2 = 43.
    #   |x - 43|: 3 1 1 3 5 1 1 5 -> ordenados 1 1 1 1 3 3 5 5 -> MAD (1 + 3) / 2 = 2. desvio = max(2,9652; 0,86) = 2,9652.
    #   z = (55 - 43) / 2,9652 = 4,04694 -> fora. FC: oito 130, MAD 0, desvio 0,02 x 130 = 2,6; z = 3 / 2,6 = 1,15385 -> dentro.
    #   O pedal virtual (01-14) e o brick (tipo moderado) não entram: o primeiro está fora da janela, o segundo é outro tipo.
    "2026-03-18/cic1": {
        "carga": ("fora", 8, 43.0, 2.9652, 4.04694),
        "fc_media": ("dentro", 8, 130.0, 2.6, 1.15385),
    },
    # E-L8: natação leve 16/03 (vigência B). Só 02/03 e 09/03 estão no tipo -> aprendendo (2 de 8).
    "2026-03-16/nat1": {
        "fc_media": ("aprendendo", 2, None, None, None),
    },
    # E-L9: corrida moderada 19/03. Janela 22/01 a 19/03, moderado antes da sessão: 29/01 (TrainingPeaks), 05/03, 12/03 = 3.
    #   (15/01 confirmado está fora da janela.) Pace 333 e FC 155 em todos, mas n = 3 < 8 -> aprendendo.
    "2026-03-19/cor1": {
        "pace_medio": ("aprendendo", 3, None, None, None),
        "fc_media": ("aprendendo", 3, None, None, None),
        "carga": ("sem_valor", 0, None, None, None),
    },
    # E-L10: esteira na vigência A (01-06): intervalado pelo plano; pace do melhor tiro não vale na esteira; sem treinos
    #   anteriores no tipo para a FC do melhor tiro.
    "2026-01-06/cor1": {
        "melhor_pace": ("sem_valor", 0, None, None, None),
        "fc_melhor_tiro": ("aprendendo", 0, None, None, None),
        "carga": ("sem_valor", 0, None, None, None),
    },
}
