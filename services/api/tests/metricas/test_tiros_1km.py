"""Testes da detecção de tiros de 1 km. Todos os valores esperados foram
calculados à mão (o cálculo está no comentário de cada caso).

Regra tiros_1km@2 (docs/metricas/tiros-1km.md): corrida; candidata = 950 a 1050 m
que não seja rest/recovery/warmup/cooldown; é tiro se as DUAS voltas vizinhas a
separam: não existir vizinha, ser warmup/cooldown, ser pausa (< 200 m), ou ser
uma volta de recuperação (não candidata) ou pelo menos 8% mais lenta que o
tiro (tiro <= 0,92 x pace da vizinha). A intensidade só veta; o pace decide.
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
    assert r.versao == VERSAO == "tiros_1km@2"


def test_seis_tiros_sem_intensidade_por_pace():
    # Sem intensidade: paces s/km = 360 (aquec. 2000 m), 6 x 240 (tiros),
    # 5 x 450 (400 m em 180 s), 380 (1500 m em 570 s). Cada tiro tem vizinhas
    # de recuperação (400 m a 450: 240 <= 450 x 0,92 = 414) ou o aquecimento
    # (2000 m a 360: 240 <= 331,2) ou o desaquecimento (1500 m a 380: 240 <= 349,6).
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
    # Paces: 360, 4 x 240, 4 x 360 (trote de 1000 m), 370. Cada tiro (240) é
    # <= 360 x 0,92 = 331,2 em relação ao trote vizinho: o trote separa.
    # O trote (360) NÃO é tiro: sua vizinha (240) é mais rápida, então
    # 360 <= 240 x 0,92 = 220,8 é falso.
    r = detectar_tiros(_com_trote_de_1km(False), "corrida")
    assert r.tiros == (2, 4, 6, 8)


def test_rodagem_leve_com_autolap_sem_intensidade():
    # 8 voltas de 1000 m, 328 a 340 s. Vizinhas a ~333 s/km: para ser tiro a volta
    # precisaria de <= 333 x 0,92 = 306,4 s/km; a mais rápida (328) não chega perto.
    duracoes = [330, 335, 328, 340, 332, 336, 331, 334]
    voltas = [volta(i + 1, 1000, d) for i, d in enumerate(duracoes)]
    r = detectar_tiros(voltas, "corrida")
    assert r.tiros == ()
    assert r.eh_intervalado is False


def test_rodagem_leve_com_autolap_todo_active_cai_para_pace():
    # Garmin marca todas as voltas como active: a intensidade não basta para ser
    # tiro, o pace decide (mesmas contas do caso anterior).
    duracoes = [330, 335, 328, 340, 332, 336, 331, 334]
    voltas = [volta(i + 1, 1000, d, "active") for i, d in enumerate(duracoes)]
    r = detectar_tiros(voltas, "corrida")
    assert r.tiros == ()
    assert r.eh_intervalado is False


def test_volta_de_1200_m_nao_e_tiro():
    # 1200 m está fora de 950-1050, mesmo rápida (pace 200 s/km).
    # Vizinha de 400 m a 450 s/km: 240 <= 414, então a de 1000 m é tiro.
    for i in ("active", None):
        voltas = [
            volta(1, 1200, 240, i),
            volta(2, 400, 180, "rest" if i else None),
            volta(3, 1000, 240, i),
            volta(4, 400, 180, "rest" if i else None),
        ]
        assert detectar_tiros(voltas).tiros == (3,)


def test_volta_de_980_m_e_tiro():
    # 980 m em 235 s -> pace 239,8 s/km. Vizinhas: 400 m em 180 s = 450 s/km,
    # limite = 450 x 0,92 = 414 -> 239,8 <= 414 nas duas vizinhas: é tiro.
    for intens in (None, "active"):
        voltas = [
            volta(1, 400, 180),
            volta(2, 980, 235, intens),
            volta(3, 400, 180),
        ]
        assert detectar_tiros(voltas).tiros == (2,)


def test_limites_da_tolerancia():
    # 950 e 1050 entram; 949 e 1051 não (ficam sem ser candidatas).
    # Todas a 240 s/km (duração proporcional) entre recuperações de 400 m a 450 s/km.
    # 240 <= 450 x 0,92 = 414: as vizinhas separam.
    voltas, o = [volta(1, 400, 180)], 2
    for d in (950, 1050, 949, 1051):
        voltas += [volta(o, d, d * 0.24), volta(o + 1, 400, 180)]
        o += 2
    assert detectar_tiros(voltas).tiros == (2, 4)


def test_limite_de_pace_8_por_cento():
    # Vizinhas de 1000 m a 300 s/km: limite = 300 x 0,92 = 276.
    # 270 <= 276: a volta do meio é tiro (separada nas duas pontas).
    # 285 > 276: não é tiro (e as de 300 não são tiros: 300 > 285 x 0,92 = 262,2).
    rapido = [volta(1, 1000, 300), volta(2, 1000, 270), volta(3, 1000, 300)]
    assert detectar_tiros(rapido).tiros == (2,)
    quase = [volta(1, 1000, 300), volta(2, 1000, 285), volta(3, 1000, 300)]
    assert detectar_tiros(quase).tiros == ()


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
    # "other" não é reconhecida: vale como ausente. A volta 1 (240 s/km) tem como
    # única vizinha uma de 400 m a 450 s/km: 240 <= 414, é tiro.
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


# ---------------------------------------------------------------------------
# tiros_1km@2 (issue #48): falsos positivos da @1. Voltas montadas à mão.
# ---------------------------------------------------------------------------

DURACOES_LEVE = [330, 335, 328, 340, 332, 336, 331, 334]  # 1000 m cada


def _rodagem_com_parcial(intens_parcial, todas="active"):
    # 8 voltas de 1000 m (328 a 340 s) + volta final parcial de 350 m a ~335 s/km.
    # Nenhuma volta de 1 km tem vizinha 8% mais lenta (a menor razão possível é
    # 328/340 = 0,965 > 0,92) nem separada por pausa: não há tiro.
    voltas = [volta(i + 1, 1000, d, todas) for i, d in enumerate(DURACOES_LEVE)]
    voltas.append(volta(9, 350, 117, intens_parcial))
    return voltas


def test_rodagem_com_volta_final_parcial_nao_e_intervalado():
    # Caso que a @1 errava: a última volta (parcial) vinha rest/recovery/cooldown,
    # criava "contraste de intensidade" e todas as de 1 km viravam tiro.
    for parcial in ("rest", "recovery", "cooldown", "warmup", None):
        r = detectar_tiros(_rodagem_com_parcial(parcial), "corrida")
        assert r.tiros == (), parcial
        assert r.eh_intervalado is False


def test_parcial_final_de_pausa_nao_cria_tiro_na_ultima_volta_de_1km():
    # Volta final de 45 m (parado). A última de 1 km (334 s/km) agora tem a pausa
    # como vizinha, mas a vizinha anterior (331) não é 8% mais lenta: não é tiro.
    voltas = [volta(i + 1, 1000, d, "active") for i, d in enumerate(DURACOES_LEVE)]
    voltas.append(volta(9, 45, 60, "recovery"))
    assert detectar_tiros(voltas).tiros == ()


def test_autolap_inteiro_marcado_interval_nao_e_tiro():
    # Rodagem progressiva: 6 x 1000 m, 407, 405, 420, 395, 392, 365 s/km, todas
    # `interval`. Nenhuma vizinha é >= 8% mais lenta que a volta (a razão mais
    # baixa é 365/392 = 0,931 > 0,92) e a primeira/última têm vizinha de 1 km.
    paces = [407, 405, 420, 395, 392, 365]
    voltas = [volta(i + 1, 1000, p, "interval") for i, p in enumerate(paces)]
    voltas.append(volta(7, 45, 17, "interval"))
    assert detectar_tiros(voltas).tiros == ()


def test_intensidade_active_rest_sem_contraste_de_pace_nao_e_tiro():
    # 4 x (1000 m active a 300 s/km, 1000 m rest a 305 s/km): a intensidade
    # alterna, mas o pace não: 300 <= 305 x 0,92 = 280,6 é falso. Sem tiro.
    voltas = []
    for k in range(4):
        voltas += [volta(2 * k + 1, 1000, 300, "active"), volta(2 * k + 2, 1000, 305, "rest")]
    assert detectar_tiros(voltas).tiros == ()


def test_bloco_continuo_de_3_km_com_pausa_nao_e_tiro_de_1_km():
    # 4 x (3 voltas de 1000 m a 280 s/km + parada de 7 m): as voltas do meio têm
    # vizinhas de 1 km no mesmo ritmo, e as das pontas também de um lado. Nenhuma
    # fica separada nos dois lados.
    voltas, o = [], 1
    for _ in range(4):
        voltas += [volta(o, 1000, 280), volta(o + 1, 1000, 280), volta(o + 2, 1000, 280),
                   volta(o + 3, 7, 120)]
        o += 4
    assert detectar_tiros(voltas).tiros == ()


def test_quatro_tiros_com_recuperacao_parada():
    # 4 x 1000 m a 228 s/km com paradas de 60 m (60 s): pausa (< 200 m) separa
    # sem comparar pace. Sem aquecimento nem desaquecimento: as pontas não têm
    # vizinha, também separam.
    voltas, o = [], 1
    for k in range(4):
        voltas.append(volta(o, 1000, 228))
        o += 1
        if k < 3:
            voltas.append(volta(o, 60, 60))
            o += 1
    r = detectar_tiros(voltas)
    assert r.tiros == (1, 3, 5, 7)
    assert r.recuperacoes == (2, 4, 6)
    assert r.eh_intervalado is True


def test_tiros_curtos_e_de_1km_misturados_so_contam_os_de_1km():
    # aquec. 2 x 1000 m warmup a 330; 3 x (1000 m a 250 + 400 m a 450); 4 x (300 m
    # a 230 + 100 m de pausa). Os 3 de 1 km têm vizinha de recuperação (250 <=
    # 450 x 0,92 = 414); as voltas de 300 m nunca são candidatas.
    voltas = [volta(1, 1000, 330, "warmup"), volta(2, 1000, 330, "warmup")]
    o = 3
    for _ in range(3):
        voltas += [volta(o, 1000, 250, "active"), volta(o + 1, 400, 180, "rest")]
        o += 2
    for _ in range(4):
        voltas += [volta(o, 300, 69, "active"), volta(o + 1, 100, 60, "rest")]
        o += 2
    assert detectar_tiros(voltas).tiros == (3, 5, 7)


# ---------------------------------------------------------------------------
# Bloco principal (issue #48): treino misto com tiros curtos pesando mais.
# ---------------------------------------------------------------------------


def _misto(n_1km, n_curtos):
    # aquec. 2000 m; n_1km x (1000 m a 250 s/km + 400 m de trote a 450 s/km);
    # n_curtos x (400 m a 225 s/km + 100 m parado a 60 s). Desaq. 1500 m.
    voltas, o = [volta(1, 2000, 720, "warmup")], 2
    for _ in range(n_1km):
        voltas += [volta(o, 1000, 250, "active"), volta(o + 1, 400, 180, "rest")]
        o += 2
    for _ in range(n_curtos):
        voltas += [volta(o, 400, 90, "active"), volta(o + 1, 100, 60, "rest")]
        o += 2
    voltas.append(volta(o, 1500, 570, "cooldown"))
    return voltas


def test_6x1km_puro_e_de_1km():
    r = detectar_tiros(_misto(6, 0))
    assert len(r.tiros) == 6
    assert r.eh_intervalado is True


def test_misto_3x1km_e_8x400m_fica_fora():
    # Volume dos tiros de 1 km: 3 x 1000 = 3000 m. Voltas curtas active (400 m, a
    # 225 s/km): 8 x 400 = 3200 m. 3000 < 3200: o bloco principal são os tiros
    # curtos, então a sessão não é de tiros de 1 km.
    r = detectar_tiros(_misto(3, 8))
    assert r.tiros == () and r.recuperacoes == ()
    assert r.eh_intervalado is False


def test_misto_2x1km_e_8x400m_fica_fora():
    # Só 2 tiros de 1 km (< 3): fora, como pedido pela definição do treino.
    assert detectar_tiros(_misto(2, 8)).eh_intervalado is False


def test_misto_6x1km_e_4x400m_fica_dentro():
    # 6 x 1000 = 6000 m contra 4 x 400 = 1600 m: o bloco principal são os de 1 km.
    r = detectar_tiros(_misto(6, 4))
    assert len(r.tiros) == 6
    assert r.eh_intervalado is True


def test_trote_de_400_m_nao_conta_como_tiro_curto():
    # Sem intensidade, 5 trotes de 400 m pesam 2000 m contra 5000 m de tiros de 1 km:
    # 5 x 1 km sem aquecimento com trote de 400 m seguem de 1 km.
    voltas, o = [], 1
    for _ in range(5):
        voltas += [volta(o, 1000, 250), volta(o + 1, 400, 180)]
        o += 2
    assert detectar_tiros(voltas).eh_intervalado is True


def test_fronteira_volume_igual_dos_curtos_fica_dentro():
    # 3 x 1000 m = 3000 m de tiros de 1 km; 10 x 300 m = 3000 m de tiros curtos.
    # A regra é "maior ou igual" (3000 >= 3000): a sessão fica dentro.
    voltas, o = [volta(1, 2000, 720, "warmup")], 2
    for _ in range(3):
        voltas += [volta(o, 1000, 250, "active"), volta(o + 1, 400, 180, "rest")]
        o += 2
    for _ in range(10):
        voltas += [volta(o, 300, 69, "active"), volta(o + 1, 100, 60, "rest")]
        o += 2
    r = detectar_tiros(voltas)
    assert len(r.tiros) == 3
    assert r.eh_intervalado is True
    # Um metro a mais nas voltas curtas (10 x 300 m + 1 volta de 150 m = 3150 m) vira fora.
    voltas += [volta(o, 150, 35, "active"), volta(o + 1, 100, 60, "rest")]
    assert detectar_tiros(voltas).eh_intervalado is False
