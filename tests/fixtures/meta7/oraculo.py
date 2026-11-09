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
    "JANELA_DIAS": 84,  # 12 semanas (linha_base@2, Angelo 09/11, #288)
    "MINIMO_TREINOS": 8,  # (Angelo, 09/11)
    "LIMITE_FORA": 2.5,  # A confirmar 3
    "PISO_REL": 0.02,  # calibração #269
    "MAD_ESCALA": 1.4826,
    "LEVE_MIN_S": 1200,  # calibração #269
    "LONGO_MIN_S": 4500,  # calibração #269
    "DIVERGENTE_FORA_DA_BASE": True,  # A confirmar 2
    "TRANSICAO_BASE_PROPRIA": True,  # linha_base@2: parte de transição compara só com parte de transição (substitui A confirmar 5)
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
_g(["2026-01-13/cor2"], ("leve", "sugestao", None))  # 28 min sem esforço, perdeu o item (empate: a mais cedo leva)
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

# Atividades sem linha de base, com o motivo (ordem dos motivos: ADR 0011, item 7). Na @2 a parte de transição tem base própria.
SEM_LINHA_BASE = {
    "2026-01-10/out1": "multiesporte",
    "2026-01-10/out2": "multiesporte",
    "2026-01-10/out3": "multiesporte",
    "2026-01-10/nat1": "sem_tipo",  # sem tipo (e também transição): vale o primeiro motivo da ordem
    "2026-01-19/nat1": "sem_tipo",
    "2026-01-13/cor1": "divergente",
    "2026-03-28/cor1": "divergente",
    "2026-01-20/cor1": "sem_tipo",
}

# Linha de base esperada nas sessões-alvo (linha_base@2): id -> métrica -> (estado, n, mediana, desvio, z).
# estado: fora | dentro | aprendendo | sem_valor. Para aprendendo e sem_valor, mediana, desvio e z são None.
# Janela de 84 dias, só treinos anteriores à sessão, mínimo 8, mesmo grupo (isolada x transição).
# desvio = max(1,4826 x MAD, 0,02 x |mediana|); z = (valor - mediana) / desvio. A carga por hora das fixtures é a carga da
# pedalada de 1 h (3600 s), então carga/h = carga; a corrida não tem carga (sem dados de saúde): carga_hora sem valor.
LINHA_BASE_ESPERADA = {
    # L1: corrida leve 13/03 (306 s/km). Janela 19/12 a 13/03, 11 leves isolados: domingos 04/01 (348) e 11/01 (318), terça
    #   13/01 às 18:00 (336) e as 8 sextas 330, 324, 336, 330, 342, 318, 330, 336.
    #   ordenados 318 318 324 330 330 330 336 336 336 342 348 -> mediana (6o) 330.
    #   |x - 330|: 12 12 6 0 0 0 6 6 6 12 18 -> ordenados 0 0 0 6 6 6 6 12 12 12 18 -> MAD (6o) 6.
    #   desvio = max(8,8956; 6,6) = 8,8956. z = (306 - 330) / 8,8956 = -2,69799 -> fora.
    #   FC: 8 valores (148, 148, 150, 150, 148, 152, 146, 151; as sextas 30/01, 13/02, 27/02 não têm FC):
    #   ordenados 146 148 148 148 150 150 151 152 -> mediana (148 + 150) / 2 = 149; |x - 149|: 1 1 1 1 1 2 3 3 -> MAD 1;
    #   desvio = max(1,4826; 2,98) = 2,98 (piso). z = (160 - 149) / 2,98 = 3,69128 -> fora.
    "2026-03-13/cor1": {
        "pace_medio": ("fora", 11, 330.0, 8.8956, -2.69799),
        "fc_media": ("fora", 8, 149.0, 2.98, 3.69128),
        "carga_hora": ("sem_valor", 0, None, None, None),
    },
    # L2: corrida leve 20/03 (330 s/km, FC 150). Janela 26/12 a 20/03, 12 leves (os 11 da L1 e o 306 de 13/03; 04/01 ainda entra):
    #   348, 318, 336, 330, 324, 336, 330, 342, 318, 330, 336, 306 (12) -> ordenados 306 318 318 324 330 330 330 336 336 336 342 348,
    #   mediana (330 + 330) / 2 = 330; |x - 330|: 0 0 0 6 6 6 6 12 12 12 18 24 -> MAD (6 + 6) / 2 = 6; desvio 8,8956; z = 0 -> dentro.
    #   FC: 148 148 150 150 148 152 146 151 160 (9) -> ordenados 146 148 148 148 150 150 151 152 160, mediana 150;
    #   |x - 150|: 0 0 1 2 2 2 2 4 10 -> MAD 2; desvio = max(2,9652; 3,0) = 3,0 (piso); z = 0 -> dentro.
    "2026-03-20/cor1": {
        "pace_medio": ("dentro", 12, 330.0, 8.8956, 0.0),
        "fc_media": ("dentro", 9, 150.0, 3.0, 0.0),
        "carga_hora": ("sem_valor", 0, None, None, None),
    },
    # L3: corrida longa 14/03 (324 s/km, FC 145). Janela 20/12 a 14/03, 9 longos isolados: quinta 08/01 do professor (335, FC 155)
    #   e os 8 sábados 342, 336, 339, 333, 330, 336, 330, 333 (o brick de 10/01 tem base própria e não entra).
    #   ordenados 330 330 333 333 335 336 336 339 342 -> mediana (5o) 335; |x - 335|: 5 5 2 2 0 1 1 4 7,
    #   ordenados 0 1 1 2 2 4 5 5 7 -> MAD (5o) 2; desvio = max(2,9652; 6,7) = 6,7 (piso). z = (324 - 335) / 6,7 = -1,64179 -> dentro.
    #   FC: oito 145 e um 155 -> mediana 145, MAD 0, desvio 2,9 (piso); a sessão 145: z 0.
    "2026-03-14/cor1": {
        "pace_medio": ("dentro", 9, 335.0, 6.7, -1.64179),
        "fc_media": ("dentro", 9, 145.0, 2.9, 0.0),
        "carga_hora": ("sem_valor", 0, None, None, None),
    },
    # L4: corrida longa 21/03 (315 s/km). Janela 27/12 a 21/03, 10 longos: 335 (08/01) e 342, 336, 339, 333, 330, 336, 330, 333, 324.
    #   ordenados 324 330 330 333 333 335 336 336 339 342 -> mediana (333 + 335) / 2 = 334;
    #   |x - 334|: 1 1 1 2 2 4 4 5 8 10 (ordenados) -> MAD (2 + 4) / 2 = 3; desvio = max(4,4478; 6,68) = 6,68 (piso).
    #   z = (315 - 334) / 6,68 = -2,84431 -> fora. FC: 155 e nove 145 -> mediana 145, desvio 2,9, z 0.
    "2026-03-21/cor1": {
        "pace_medio": ("fora", 10, 334.0, 6.68, -2.84431),
        "fc_media": ("dentro", 10, 145.0, 2.9, 0.0),
        "carga_hora": ("sem_valor", 0, None, None, None),
    },
    # L5: intervalado 17/03 (melhor tiro 249 s/km). Janela 23/12 a 17/03. melhor_pace: sexta 09/01 (270, reserva) e as terças
    #   270, 264, 267, 261, 264, 258, 261, 255 (a esteira de 06/01 não tem pace; a de 13/01 é divergente): 9 valores,
    #   ordenados 255 258 261 261 264 264 267 270 270 -> mediana 264; |x - 264|: 0 0 3 3 3 6 6 6 9 -> MAD 3;
    #   desvio = max(4,4478; 5,28) = 5,28 (piso). z = (249 - 264) / 5,28 = -2,84091 -> fora.
    #   fc_melhor_tiro: 06/01, 09/01 e 7 terças (a de 24/02 não tem FC), todas 172: 9 valores, desvio 3,44 (piso), z 0.
    #   fc_media: 06/01, 09/01 e 8 terças, todas 160: 10 valores, desvio 3,2, z 0.
    "2026-03-17/cor1": {
        "melhor_pace": ("fora", 9, 264.0, 5.28, -2.84091),
        "fc_melhor_tiro": ("dentro", 9, 172.0, 3.44, 0.0),
        "fc_media": ("dentro", 10, 160.0, 3.2, 0.0),
        "carga_hora": ("sem_valor", 0, None, None, None),
    },
    # L6: intervalado 10/03 (255 s/km). Janela 16/12 a 10/03; a terça de 13/01 é divergente e fica fora.
    #   melhor_pace: 270 (09/01), 270, 264, 267, 261, 264, 258, 261 (8) -> ordenados 258 261 261 264 264 267 270 270, mediana 264;
    #   |x - 264|: 0 0 3 3 3 6 6 6 -> MAD (3 + 3) / 2 = 3; desvio 5,28 (piso); z = (255 - 264) / 5,28 = -1,70455 -> dentro.
    #   fc_melhor_tiro: 06/01, 09/01 e 6 terças = 8 valores (172): dentro, z 0. fc_media: 9 valores (160): dentro, z 0.
    "2026-03-10/cor1": {
        "melhor_pace": ("dentro", 8, 264.0, 5.28, -1.70455),
        "fc_melhor_tiro": ("dentro", 8, 172.0, 3.44, 0.0),
        "fc_media": ("dentro", 9, 160.0, 3.2, 0.0),
        "carga_hora": ("sem_valor", 0, None, None, None),
    },
    # L7: ciclismo leve 18/03, carga 55 em 1 h, FC 133. Janela 24/12 a 18/03, 10 quartas (inclui o pedal virtual de 14/01):
    #   carga/h 41, 41, 40, 44, 42, 46, 38, 44, 42, 48 -> ordenados 38 40 41 41 42 42 44 44 46 48, mediana (42 + 42) / 2 = 42;
    #   |x - 42|: 4 2 1 1 0 0 2 2 4 6 -> ordenados 0 0 1 1 2 2 2 4 4 6 -> MAD (2 + 2) / 2 = 2; desvio = max(2,9652; 0,84) = 2,9652.
    #   z = (55 - 42) / 2,9652 = 4,38419 -> fora. FC: dez 130, MAD 0, desvio 2,6 (piso); z = 3 / 2,6 = 1,15385 -> dentro.
    #   O brick (ciclismo moderado) é outro tipo e outro grupo.
    "2026-03-18/cic1": {
        "carga_hora": ("fora", 10, 42.0, 2.9652, 4.38419),
        "fc_media": ("dentro", 10, 130.0, 2.6, 1.15385),
    },
    # L8: natação leve 16/03 (vigência B). Só 02/03 e 09/03 estão no tipo -> aprendendo (2 de 8).
    "2026-03-16/nat1": {
        "fc_media": ("aprendendo", 2, None, None, None),
    },
    # L9: corrida moderada 19/03. Janela 25/12 a 19/03, moderado isolado antes da sessão: 15/01 (confirmado), 29/01 (TrainingPeaks),
    #   05/03 e 12/03 = 4 < 8 -> aprendendo. (Os sábados de moderado não existem como isolados nas fixtures.)
    "2026-03-19/cor1": {
        "pace_medio": ("aprendendo", 4, None, None, None),
        "fc_media": ("aprendendo", 4, None, None, None),
        "carga_hora": ("sem_valor", 0, None, None, None),
    },
    # L10: esteira (06/01): intervalado pelo plano; o pace do melhor tiro não vale na esteira; sem treinos antes no tipo.
    "2026-01-06/cor1": {
        "melhor_pace": ("sem_valor", 0, None, None, None),
        "fc_melhor_tiro": ("aprendendo", 0, None, None, None),
        "fc_media": ("aprendendo", 0, None, None, None),
        "carga_hora": ("sem_valor", 0, None, None, None),
    },
    # L11: o brick de 10/01 tem base própria (parte de transição só com parte de transição) e não há outra antes: n = 0.
    #   Ciclismo: carga 30 em 2700 s = 0,75 h -> 40 pontos/h (valor da sessão; aprendendo não mostra mediana).
    "2026-01-10/cic1": {
        "fc_media": ("aprendendo", 0, None, None, None),
        "carga_hora": ("aprendendo", 0, None, None, None),
    },
    "2026-01-10/cor1": {
        "pace_medio": ("aprendendo", 0, None, None, None),
        "fc_media": ("aprendendo", 0, None, None, None),
        "carga_hora": ("sem_valor", 0, None, None, None),
    },
}
