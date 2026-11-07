"""Testes dos tiros de 1 km como visão dos esforços (issue #168; ADR 0008, item 8). Valores à mão.

Regra tiros_1km@5 (docs/metricas/tiros-1km.md): tiro = bloco ``esforco`` da faixa ``d1000`` (950 a 1050 m) de uma
corrida, depois do ritmo parecido (20% sobre a mediana, com 3 ou mais) e do bloco contínuo (menos de 15% mais
rápido que um bloco vizinho de corrida). Pelo menos 2 tiros formam a sessão.

As voltas sintéticas passam por ``montar_blocos`` (esforcos@1) com ritmo habitual de 330 s/km: esforço = pace
<= 330 x 0,90 = 297 s/km. Cada caso diz as contas. Os casos do ``test_tiros_1km.py`` da @4 que continuam valendo
(progressivo, fartlek, bloco contínuo, ritmo parecido) estão na seção "regressão da @4" com o mesmo resultado; os
que mudam estão na seção "o que mudou" com a justificativa.
"""

import importlib.util
from pathlib import Path

import pytest

from app.metricas.tiros_1km import VERSAO, agregar_sessao, tiro_de_bloco, tiros_de_blocos

_spec = importlib.util.spec_from_file_location("_tiros_blocos", Path(__file__).with_name("_tiros_blocos.py"))
_ajuda = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_ajuda)
blocos_de = _ajuda.blocos_de


def tiros(specs, ref=330.0):
    return tiros_de_blocos(blocos_de(specs, ref))


def paces_dos_tiros(specs, ref=330.0):
    blocos = {b.ordem: b for b in blocos_de(specs, ref)}
    return [round(blocos[o].duracao_s / blocos[o].distancia_m * 1000, 6) for o in tiros(specs, ref).tiros]


def test_versao():
    assert VERSAO == "tiros_1km@6"
    assert tiros([(1000, 250), (400, 168, 0)] * 2).versao == VERSAO


# ---------------------------------------------------------------------------
# Exemplos da #168 e da ADR 0008, item 8 (regressão pedida na issue)
# ---------------------------------------------------------------------------


def test_dois_tiros_com_recuperacao_entram():
    # 2 x 1000 m a 250 s/km, recuperação de 400 m a 420 s/km (168 s). Limiar 297: 250 é esforço, 420 não.
    # Blocos: 0 tiro, 1 recuperação, 2 tiro. Os vizinhos de 400 m não passam de 950 m: o bloco contínuo não olha.
    r = tiros([(1000, 250), (400, 168), (1000, 250)])
    assert (r.tiros, r.recuperacoes, r.eh_intervalado) == ((0, 2), (1,), True)
    assert paces_dos_tiros([(1000, 250), (400, 168), (1000, 250)]) == [250.0, 250.0]


def test_um_tiro_so_nao_e_sessao():
    r = tiros([(1000, 250), (400, 168), (1000, 330)])
    assert r.tiros == (0,) and r.eh_intervalado is False  # 1 < 2


def _cinco_km_e_oito_400():
    # 5 x (1000 m a 250 s/km + 400 m a 420 s/km), depois 8 x (400 m a 230 s/km = 92 s + 200 m a 450 s/km = 90 s).
    specs = []
    for _ in range(5):
        specs += [(1000, 250), (400, 168)]
    for _ in range(8):
        specs += [(400, 92), (200, 90)]
    return specs


def test_cinco_km_e_oito_400_so_contam_os_cinco_km():
    # Os d400 (230 s/km) são esforços, mas não da faixa d1000. Tiros = blocos 0,2,4,6,8; pace da sessão:
    # 5 x 250 s / 5 x 1000 m x 1000 = 250 s/km.
    specs = _cinco_km_e_oito_400()
    r = tiros(specs)
    assert r.tiros == (0, 2, 4, 6, 8) and r.eh_intervalado is True
    blocos = {b.ordem: b for b in blocos_de(specs)}
    ponto = agregar_sessao("x", None, [tiro_de_bloco(blocos[o]) for o in r.tiros])
    assert ponto.n_tiros == 5 and ponto.pace_s_km == pytest.approx(250.0)


def test_tiros_curtos_com_km_de_aquecimento_e_desaquecimento_lentos_ficam_fora():
    # aquec. 1000 m a 335 s/km (> 297: não é esforço), 8 x (400 m a 230 + 200 m a 450), desaq. 1000 m a 340.
    specs = [(1000, 335)]
    for _ in range(8):
        specs += [(400, 92), (200, 90)]
    specs += [(1000, 340)]
    r = tiros(specs)
    assert r.tiros == () and r.eh_intervalado is False
    cats = [b.categoria for b in blocos_de(specs)]
    assert cats[0] == "aquecimento" and cats[-1] == "desaquecimento"


def test_rodagem_com_autolap_de_1km_fica_fora():
    # 8 voltas de 1000 m, 328 a 340 s: cada uma dentro de 5% do bloco, viram um bloco leve de 8000 m.
    specs = [(1000, d) for d in (330, 335, 328, 340, 332, 336, 331, 334)]
    blocos = blocos_de(specs)
    assert [b.categoria for b in blocos] == ["leve"]
    assert tiros(specs).tiros == ()


def test_um_esforco_de_1500_m_nao_e_tiro_de_1km():
    # 1000 m a 250 s + 500 m a 125 s (250 s/km): sem pausa e no mesmo ritmo, um bloco d1500. Duas vezes: 0 tiros.
    specs = [(1000, 250), (500, 125), (400, 168), (1000, 250), (500, 125)]
    blocos = blocos_de(specs)
    assert [b.faixa for b in blocos] == ["d1500", None, "d1500"]
    assert tiros(specs).tiros == ()


def test_dois_km_seguidos_no_mesmo_ritmo_sao_um_esforco_de_2000_m():
    # Um bloco d2000: a regra "vizinha de 1 km no mesmo ritmo não separa" da @4 sai pela própria junção.
    specs = [(1000, 250), (1000, 250), (400, 168), (1000, 250), (1000, 250)]
    assert tiros(specs).tiros == ()


def test_lap_automatico_cortando_o_tiro_ao_meio_ainda_e_um_tiro():
    # 2 x [500 m a 125 s + 500 m a 125 s] com 90 s parado entre os tiros: cada par vira um bloco de 1000 m.
    specs = [(500, 125), (500, 125, 90), (500, 125), (500, 125)]
    blocos = blocos_de(specs)
    assert [(b.volta_inicial, b.volta_final, b.faixa) for b in blocos] == [(0, 1, "d1000"), (2, 3, "d1000")]
    r = tiros_de_blocos(blocos)
    assert r.tiros == (0, 1) and r.eh_intervalado is True
    assert tiro_de_bloco(blocos[1]).ordem == 2  # `ordem` do tiro = primeira volta do bloco (segmento.ordem)


def test_esforco_vizinho_que_a_regra_de_5_nao_junta_conta_como_dois_esforcos():
    # Decisão do Angelo (04/11): 1000 m a 250 e 500 m a 270 (8% mais lento) ficam d1000 e d500, não d1500.
    # O d1000 vale como tiro (o vizinho de 500 m não chega a 950 m, o bloco contínuo não olha). 2 repetições com
    # 90 s parados: 2 tiros.
    specs = [(1000, 250), (500, 135, 90), (1000, 250), (500, 135)]
    blocos = blocos_de(specs)
    assert [b.faixa for b in blocos] == ["d1000", "d500", "d1000", "d500"]
    assert tiros_de_blocos(blocos).tiros == (0, 2)


def test_tiros_de_1km_com_descanso_parado_nao_viram_bloco_continuo():
    # 5 x 1000 m a 250 s/km, 90 s parado entre eles (sem volta de recuperação): 5 blocos d1000 em fila. Vizinhos
    # candidatos separados por parada de 90 s (>= 15 s) não são bloco contínuo: 5 tiros.
    specs = [(1000, 250, 90)] * 4 + [(1000, 250)]
    assert tiros(specs).tiros == (0, 1, 2, 3, 4)


def test_parada_curta_entre_km_em_ritmos_diferentes_e_bloco_continuo():
    # 1000 m a 250 e 1000 m a 266 (6,4% mais lento: não junta), parada de 10 s (< 15 s): 250 > 266 x 0,85 = 226,1
    # e 266 > 250 x 0,85 = 212,5, os dois saem: é corrida contínua em ritmos próximos, não repetição.
    specs = [(1000, 250, 10), (1000, 266, 10), (1000, 250, 10), (1000, 266)]
    assert tiros(specs).tiros == ()


def test_so_corrida_e_blocos_vazios():
    assert tiros_de_blocos(blocos_de([(1000, 250), (400, 168), (1000, 250)]), "natacao").tiros == ()
    assert tiros_de_blocos([]).eh_intervalado is False


# ---------------------------------------------------------------------------
# Regressão da @4: mesmo resultado (tiros_1km@4 -> @5)
# ---------------------------------------------------------------------------


def seis_x_1km():
    # aquec. 2000 m/720 s (360), 6 x (1000 m a 240 + 400 m/180 s, 450 s/km, entre eles), desaq. 1500 m/570 s (380).
    specs = [(2000, 720)]
    for k in range(6):
        specs.append((1000, 240))
        if k < 5:
            specs.append((400, 180))
    specs.append((1500, 570))
    return specs


def test_seis_tiros_com_aquecimento_e_desaquecimento():
    # Blocos: 0 aquecimento, 1,3,5,7,9,11 tiros, 2,4,6,8,10 recuperações, 12 desaquecimento.
    r = tiros(seis_x_1km())
    assert r.tiros == (1, 3, 5, 7, 9, 11)
    assert r.recuperacoes == (2, 4, 6, 8, 10)
    assert r.eh_intervalado is True


def _fartlek_1km(duracao_trote):
    # aquec. 2000 m/720 s; 4 x [1000 m a 240 s/km, 1000 m de trote em duracao_trote s]; desaq. 1000 m/370 s.
    specs = [(2000, 720)]
    for _ in range(4):
        specs += [(1000, 240), (1000, duracao_trote)]
    specs.append((1000, 370))
    return specs


def test_fartlek_de_1km_forte_e_1km_moderado_nao_e_tiro():
    # Trote a 270 s/km: é esforço (270 <= 297) e vizinho colado de ~1 km; 240 > 270 x 0,85 = 229,5 (menos de 15%
    # mais rápido): bloco contínuo. O trote também sai (270 > 240 x 0,85). Nenhum tiro, como na @4.
    r = tiros(_fartlek_1km(270))
    assert r.tiros == () and r.eh_intervalado is False


def test_trote_de_1km_bem_mais_lento_continua_sendo_recuperacao():
    # Trote a 330 s/km (não é esforço): 240 <= 330 x 0,85 = 280,5. Os 4 seguem tiros. Blocos: 0 aq., tiros 1,3,5,7.
    r = tiros(_fartlek_1km(330))
    assert r.tiros == (1, 3, 5, 7)
    assert r.recuperacoes == (2, 4, 6)
    assert r.eh_intervalado is True


def test_limite_do_bloco_continuo_15_por_cento():
    # Tiro a 240 s/km. Trote a 282: 282 x 0,85 = 239,7 < 240, bloco contínuo, fora.
    # Trote a 283: 283 x 0,85 = 240,55 >= 240, o tiro fica (o trote, esforço colado a 240, sai: 283 > 204).
    assert tiros(_fartlek_1km(282)).tiros == ()
    assert tiros(_fartlek_1km(283)).tiros == (1, 3, 5, 7)


def _blocos_com_parada(ritmo):
    # 3 x [1000 m a ritmo, 1000 m a ritmo - 10, parada de 20 m/90 s, 1000 m a 275, parada de 20 m/90 s]. Os dois
    # primeiros km se juntam (diferença menor que 5%): um bloco de 2000 m; o km de 275 fica entre as paradas.
    specs = []
    for _ in range(3):
        specs += [(1000, ritmo), (1000, ritmo - 10), (20, 90), (1000, 275), (20, 90)]
    return specs


def test_progressivo_com_paradas_de_90_s_passa_a_ter_tiros_na_arroba_6():
    # Blocos de 2000 m a 305 s/km (310 e 300; 305 > 297, não são esforço) ao lado do km de 275 (275 <= 297, esforço).
    # @4 e @5: 275 > 305 x 0,85 = 259,25, o bloco de rodagem "continua por cima da parada" e nenhum km era tiro.
    # @6 (#243): a parada de 90 s >= 15 s entre o km e o vizinho tira o vizinho da conta; os 3 km de 275 são tiros.
    # É a limitação (c) da nota (série moderada com paradas, mesma estrutura de tiros), agora aceita como regra.
    r = tiros(_blocos_com_parada(310))
    assert len(r.tiros) == 3 and r.eh_intervalado is True
    assert paces_dos_tiros(_blocos_com_parada(310)) == [275.0] * 3


def test_km_forte_depois_de_rodagem_lenta_com_parada_e_tiro():
    # Rodagem a 340/330 (bloco a 335): 275 <= 335 x 0,85 = 284,75. Os 3 km de 275 ficam. Na @4 eram as voltas 4, 9, 14.
    specs = _blocos_com_parada(340)
    r = tiros(specs)
    assert len(r.tiros) == 3 and r.eh_intervalado is True
    assert paces_dos_tiros(specs) == [275.0] * 3


def _tiros_e_volta_final(duracao_final):
    # aquec. 2000 m/720 s; 3 x [1000 m a 240 s/km + parada de 40 m/30 s]; volta final de 1000 m em duracao_final s
    # e uma sobra de 10 m. (40 m e 10 m são voltas de pausa.)
    specs = [(2000, 720)]
    for _ in range(3):
        specs += [(1000, 240), (40, 30)]
    specs += [(1000, duracao_final), (10, 5)]
    return specs


def test_desaquecimento_de_1km_lento_nao_conta_como_tiro():
    # Volta final a 290 s/km ainda é esforço (290 <= 297). Mediana de (240, 240, 240, 290) = 240; limite 288.
    # 290 > 288: sai. Sobram 3 tiros de 240, como na @4.
    r = tiros(_tiros_e_volta_final(290))
    assert len(r.tiros) == 3
    assert paces_dos_tiros(_tiros_e_volta_final(290)) == [240.0] * 3


def test_volta_no_limite_do_ritmo_parecido_fica():
    # 288 <= 240 x 1,20 = 288: o limite entra, a volta final é o 4o tiro.
    assert len(tiros(_tiros_e_volta_final(288)).tiros) == 4


def test_desaquecimento_acima_do_limiar_de_esforco_sai_pela_categoria():
    # 300 s/km > 297: não é esforço, é desaquecimento. Os 3 tiros ficam.
    assert len(tiros(_tiros_e_volta_final(300)).tiros) == 3


def test_progressivo_autolap_inteiro_nao_e_tiro():
    # 6 x 1000 m a 407, 405, 420, 395, 392, 365 s/km e uma sobra de 45 m: acima de 297, nada é esforço. (@4: também 0.)
    specs = [(1000, p) for p in (407, 405, 420, 395, 392, 365)] + [(45, 17)]
    assert tiros(specs).tiros == ()


def test_bloco_continuo_de_3_km_com_parada_curta_nao_e_tiro_de_1km():
    # 4 x (3 voltas de 1000 m a 280 s/km + parada de 7 m): 3 km juntos a 280 s/km (esforço, 297) formam um bloco
    # d3000. A parada de 7 m vira volta de pausa (< 50 m) mas dura 120 s: separa os blocos. Nenhum d1000.
    specs = []
    for _ in range(4):
        specs += [(1000, 280), (1000, 280), (1000, 280), (7, 120)]
    assert tiros(specs).tiros == ()


def test_volta_de_980_m_e_tiro_e_de_949_m_nao():
    # 980 m em 235 s (239,8 s/km) e 400 m de recuperação a 450 s/km: d1000 (950 a 1050).
    assert len(tiros([(980, 235), (400, 180), (980, 235)]).tiros) == 2
    # 949 m e 1051 m ficam fora da faixa (d1000), como na @4.
    assert tiros([(949, 228), (400, 180), (1051, 252), (400, 180), (949, 228)]).tiros == ()
    # 950 m e 1050 m entram.
    assert len(tiros([(950, 228), (400, 180), (1050, 252)]).tiros) == 2


def test_volta_de_1200_m_nao_e_tiro():
    # 1200 m a 200 s/km é d1200. Com dois km de 240: só os dois entram.
    assert len(tiros([(1200, 240), (400, 180), (1000, 240), (400, 180), (1000, 240)]).tiros) == 2


def test_intensidade_do_fit_nao_decide():
    # A intensidade do relógio é só dica (ADR 0008, item 1): a visão não a lê. Voltas ``rest`` ou ``active`` dão o
    # mesmo resultado que sem rótulo, porque o pace e a estrutura decidem.
    from app.metricas.esforcos import VoltaTreino, montar_blocos

    sem = [VoltaTreino(0, 0, 240, 1000), VoltaTreino(1, 240, 180, 400), VoltaTreino(2, 420, 240, 1000)]
    com = [VoltaTreino(v.ordem, v.inicio_offset_s, v.duracao_s, v.distancia_m, None, i)
           for v, i in zip(sem, ("rest", "active", "rest"))]
    assert montar_blocos(sem, "corrida", referencia=330).blocos == montar_blocos(com, "corrida", referencia=330).blocos


# ---------------------------------------------------------------------------
# O que mudou da @4 para a @5 (cada caso com a justificativa)
# ---------------------------------------------------------------------------


def _misto(n_1km, n_curtos):
    # aquec. 2000 m/720 s; n_1km x (1000 m a 250 s/km + 400 m/180 s); n_curtos x (400 m a 225 s/km + 40 m parado/30 s).
    specs = [(2000, 720)]
    for _ in range(n_1km):
        specs += [(1000, 250), (400, 180)]
    for _ in range(n_curtos):
        specs += [(400, 90), (40, 30)]
    specs.append((1500, 570))
    return specs


def test_misto_3x1km_e_8x400m_agora_conta_os_3_tiros():
    # @4: 3000 m de tiros < 3200 m de curtos, a sessão saía inteira (regra do volume do bloco principal).
    # @5: decisão do Angelo (04/11): os 3-4 x 1 km dos treinos mistos contam. Os d400 não são de 1 km.
    r = tiros(_misto(3, 8))
    assert len(r.tiros) == 3 and r.eh_intervalado is True


def test_misto_2x1km_e_8x400m_agora_entra_com_2_tiros():
    # @4: fora, por ter menos de 3 tiros. @5: o mínimo é 2 (decisão do Angelo, 04/11).
    r = tiros(_misto(2, 8))
    assert len(r.tiros) == 2 and r.eh_intervalado is True


def test_misto_6x1km_e_4x400m_segue_dentro():
    r = tiros(_misto(6, 4))
    assert len(r.tiros) == 6 and r.eh_intervalado is True


def test_dois_tiros_e_um_desaquecimento_agora_e_sessao():
    # @4: dois tiros < 3, não era intervalado. @5: 2 tiros bastam; a volta final de 300 s/km (> 297) é desaquecimento.
    specs = [(2000, 720), (1000, 240), (40, 30), (1000, 240), (40, 30), (1000, 300), (10, 5)]
    r = tiros(specs)
    assert len(r.tiros) == 2 and r.eh_intervalado is True


def test_dois_tiros_sem_recuperacao_marcada_entram():
    # @4: dois tiros sem aquecimento e uma recuperação de 400 m: 2 < 3, fora. @5: entra (2 tiros).
    r = tiros([(1000, 240), (400, 180), (1000, 240)])
    assert r.tiros == (0, 2) and r.eh_intervalado is True


def test_nao_ha_mais_volume_do_bloco_principal():
    # 3 x 1000 m e 10 x 300 m (3000 m contra 3000 m) e mais uma volta de 150 m: na @4 a última linha saía da série
    # (3000 < 3150). Na @5 o volume dos curtos não pesa: 3 tiros nos dois casos.
    specs = [(2000, 720)]
    for _ in range(3):
        specs += [(1000, 250), (400, 180)]
    for _ in range(10):
        specs += [(300, 69), (40, 30)]
    assert len(tiros(specs).tiros) == 3
    specs += [(150, 35), (40, 30)]
    assert len(tiros(specs).tiros) == 3


def test_tiro_colado_a_um_km_so_um_pouco_mais_lento_perde_a_separacao_por_pausa():
    # 1 km a 240 e 1 km a 280 ficam juntos (parada 0): fartlek. Igual à @4. (Sem pausa, sem repetição.)
    specs = [(1000, 240), (1000, 280), (1000, 240), (1000, 280)]
    assert tiros(specs).tiros == ()



# ---------------------------------------------------------------------------
# @6: vizinho separado por parada de 15 s ou mais não corta o tiro (issue #243). Ref 330 s/km (limiar 297).
# ---------------------------------------------------------------------------


def test_piramide_1_3_2_1_km_com_descanso_parado_tem_dois_tiros_de_1_km():
    # 1 km a 250 s/km (250 s), 3 km a 250 (750 s), 2 km a 250 (500 s), 1 km a 250, com 90 s parados entre eles.
    # Todos são esforço; os de 3 e 2 km são vizinhos de 950 m ou mais, e 250 > 250 x 0,85 = 212,5 os cortaria na @5
    # (nenhum dos dois é d1000). Na @6 a parada de 90 s >= 15 s tira o vizinho da conta: os dois km são tiros.
    specs = [(1000, 250, 90), (3000, 750, 90), (2000, 500, 90), (1000, 250)]
    blocos = blocos_de(specs)
    assert [b.faixa for b in blocos] == ["d1000", "d3000", "d2000", "d1000"]
    r = tiros_de_blocos(blocos)
    assert r.tiros == (0, 3) and r.eh_intervalado is True
    assert r.recuperacoes == (1, 2)


def test_vizinho_colado_com_parada_menor_que_15_s_continua_cortando():
    # 1 km a 250 s/km, 10 s parados, 2 km a 275 s/km (550 s): 275 / 250 = 10% > 5%, não junta; ambos são esforço (< 297).
    # 250 > 275 x 0,85 = 233,75: o tiro é continuação do bloco de 2 km e sai. Com 15 s parados passa a valer.
    # O último km vem depois de 90 s parados: o vizinho de 2 km não o corta, nos dois casos.
    for parada, tiros_esperados in ((10, (2,)), (15, (0, 2))):
        blocos = blocos_de([(1000, 250, parada), (2000, 550, 90), (1000, 250)])
        assert tiros_de_blocos(blocos).tiros == tiros_esperados, parada
