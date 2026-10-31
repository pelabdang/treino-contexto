"""Testes da detecção de tiros de 1 km. Todos os valores esperados foram
calculados à mão (o cálculo está no comentário de cada caso).

Regra (docs/metricas/tiros-1km.md): corrida; candidata = 950 a 1050 m;
com intensidade contrastante, tiro = candidata active/interval; sem
intensidade, tiro = candidata com pace <= 0,92 x mediana dos paces.
"""

from app.metricas.tiros_1km import VERSAO, VoltaEntrada, detectar_tiros


def volta(ordem, dist, dur, intens=None, fc=None):
    return VoltaEntrada(ordem, dist, dur, fc_media=fc, intensidade=intens)


def seis_x_1km(com_intensidade: bool):
    """Aquecimento + 6 x (1000 m tiro, 400 m recuperação) + desaquecimento.

    Ordens: 1 aquecimento; tiros 2,4,6,8,10,12; recuperações 3,5,7,9,11;
    13 desaquecimento (a última recuperação seria 13, mas o treino termina
    em tiro + desaquecimento).
    """
    i = (lambda x: x) if com_intensidade else (lambda x: None)
    voltas = [volta(1, 2000, 720, i("warmup"))]
    ordem = 2
    for k in range(6):
        voltas.append(volta(ordem, 1000, 240, i("active")))
        ordem += 1
        if k < 5:
            voltas.append(volta(ordem, 400, 180, i("recovery")))
            ordem += 1
    voltas.append(volta(ordem, 1500, 570, i("cooldown")))
    return voltas


def test_seis_tiros_com_intensidade():
    r = detectar_tiros(seis_x_1km(True), "corrida")
    assert r.tiros == (2, 4, 6, 8, 10, 12)
    assert r.recuperacoes == (3, 5, 7, 9, 11)
    assert r.eh_intervalado is True
    assert r.versao == VERSAO == "tiros_1km@1"


def test_seis_tiros_sem_intensidade_por_pace():
    # 13 voltas: paces s/km = 360 (aquec.), 6 x 240 (tiros),
    # 5 x 450 (400 m em 180 s), 380 (1500 m em 570 s).
    # Ordenados: 240x6, 360, 380, 450x5 -> 13 valores, mediana = 7o = 360.
    # Limite = 360 x 0,92 = 331,2. Tiros (240) passam; aquecimento 2000 m
    # nem é candidato.
    r = detectar_tiros(seis_x_1km(False), "corrida")
    assert r.tiros == (2, 4, 6, 8, 10, 12)
    assert r.recuperacoes == (3, 5, 7, 9, 11)
    assert r.eh_intervalado is True


def _com_trote_de_1km(intens):
    # aquec. 2000 m/720 s (360); 4 x [tiro 1000/240 (240), trote 1000/360 (360)];
    # desaq. 1000/370 (370). Ordem: 1; tiros 2,4,6,8; trotes 3,5,7,9; 10.
    voltas = [volta(1, 2000, 720, "warmup" if intens else None)]
    o = 2
    for _ in range(4):
        voltas.append(volta(o, 1000, 240, "active" if intens else None))
        voltas.append(volta(o + 1, 1000, 360, "rest" if intens else None))
        o += 2
    voltas.append(volta(o, 1000, 370, "cooldown" if intens else None))
    return voltas


def test_trote_de_1km_marcado_rest_nao_e_tiro():
    r = detectar_tiros(_com_trote_de_1km(True), "corrida")
    assert r.tiros == (2, 4, 6, 8)
    assert r.recuperacoes == (3, 5, 7)


def test_trote_de_1km_sem_intensidade_nao_e_tiro_por_pace():
    # Paces: 360, 4 x 240, 4 x 360, 370. Ordenados: 240x4, 360x5, 370.
    # 10 valores: mediana = (5o + 6o)/2 = (360 + 360)/2 = 360.
    # Limite 331,2: trote (360) e desaquecimento (370) ficam de fora.
    r = detectar_tiros(_com_trote_de_1km(False), "corrida")
    assert r.tiros == (2, 4, 6, 8)


def test_rodagem_leve_com_autolap_sem_intensidade():
    # 8 voltas de 1000 m, durações 328..340 s. Mediana = (332+334)/2 = 333;
    # limite = 333 x 0,92 = 306,4; a mais rápida (328) não chega perto.
    duracoes = [330, 335, 328, 340, 332, 336, 331, 334]
    voltas = [volta(i + 1, 1000, d) for i, d in enumerate(duracoes)]
    r = detectar_tiros(voltas, "corrida")
    assert r.tiros == ()
    assert r.eh_intervalado is False


def test_rodagem_leve_com_autolap_todo_active_cai_para_pace():
    # Garmin marca todas as voltas como active: sem contraste, a intensidade
    # é ignorada e vale a regra por pace (mesmas contas do caso anterior).
    duracoes = [330, 335, 328, 340, 332, 336, 331, 334]
    voltas = [volta(i + 1, 1000, d, "active") for i, d in enumerate(duracoes)]
    r = detectar_tiros(voltas, "corrida")
    assert r.tiros == ()
    assert r.eh_intervalado is False


def test_volta_de_1200_m_nao_e_tiro():
    # 1200 m está fora de 950-1050, mesmo rápida (pace 200 s/km).
    voltas = [
        volta(1, 1200, 240, "active"),
        volta(2, 400, 180, "rest"),
        volta(3, 1000, 240, "active"),
    ]
    assert detectar_tiros(voltas).tiros == (3,)
    sem = [volta(1, 1200, 240), volta(2, 400, 180), volta(3, 1000, 240),
           volta(4, 1000, 400)]
    # paces 200, 450, 240, 400 -> mediana (240+400)/2 = 320; limite 294,4.
    assert detectar_tiros(sem).tiros == (3,)


def test_volta_de_980_m_e_tiro():
    # 980 m em 235 s -> pace 239,8 s/km. Mediana das 5 voltas (240, 239,8,
    # 450, 450, 450) = 450; limite 414 -> as duas primeiras são tiros.
    voltas = [
        volta(1, 1000, 240),
        volta(2, 980, 235),
        volta(3, 400, 180),
        volta(4, 400, 180),
        volta(5, 400, 180),
    ]
    assert detectar_tiros(voltas).tiros == (1, 2)
    com = [volta(1, 980, 235, "active"), volta(2, 400, 180, "rest")]
    assert detectar_tiros(com).tiros == (1,)


def test_limites_da_tolerancia():
    # 950 e 1050 entram; 949 e 1051 não.
    com = [volta(i + 1, d, 240, "active") for i, d in enumerate([950, 1050, 949, 1051])]
    com.append(volta(5, 400, 180, "rest"))
    assert detectar_tiros(com).tiros == (1, 2)


def test_limite_de_pace_8_por_cento():
    # 4 voltas de 1000 m a 300 s/km, uma a 270 e uma a 285 (as 6 formam
    # mediana (300+300)/2 = 300). Limite = 300 x 0,92 = 276.
    # 270 <= 276 é tiro; 285 > 276 não é.
    voltas = [volta(i, 1000, 300) for i in range(1, 5)]
    voltas += [volta(5, 1000, 270), volta(6, 1000, 285)]
    assert detectar_tiros(voltas).tiros == (5,)


def test_dois_tiros_nao_e_intervalado():
    voltas = [
        volta(1, 1000, 240, "active"),
        volta(2, 400, 180, "rest"),
        volta(3, 1000, 240, "active"),
    ]
    r = detectar_tiros(voltas)
    assert r.tiros == (1, 3)
    assert r.eh_intervalado is False  # 2 < 3


def test_intensidade_warmup_cooldown_nunca_sao_tiro():
    voltas = [
        volta(1, 1000, 300, "warmup"),
        volta(2, 1000, 240, "active"),
        volta(3, 1000, 300, "cooldown"),
    ]
    assert detectar_tiros(voltas).tiros == (2,)


def test_intensidade_desconhecida_conta_como_ausente():
    # "other" não é reconhecida: sem contraste, usa pace.
    # paces 240, 450, 450 -> mediana 450, limite 414 -> só a volta 1.
    voltas = [volta(1, 1000, 240, "other"), volta(2, 400, 180, "other"),
              volta(3, 400, 180, "other")]
    assert detectar_tiros(voltas).tiros == (1,)


def test_natacao_nao_tem_tiros():
    voltas = [volta(i, 1000, 900, "active") for i in range(1, 5)]
    voltas.append(volta(5, 400, 600, "rest"))
    r = detectar_tiros(voltas, "natacao")
    assert r.tiros == ()
    assert r.eh_intervalado is False


def test_sem_voltas_e_voltas_sem_distancia():
    assert detectar_tiros([]).eh_intervalado is False
    assert detectar_tiros([volta(1, 0, 0)]).tiros == ()


def test_ordem_de_entrada_nao_importa():
    voltas = list(reversed(seis_x_1km(True)))
    assert detectar_tiros(voltas).tiros == (2, 4, 6, 8, 10, 12)
