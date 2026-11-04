"""Blocos do treino (issue #162; ADR 0008, itens 1 a 5; nota docs/metricas/esforcos.md).

Todos os números são sintéticos e as contas estão nos comentários. O fim do arquivo compara os blocos com o
oráculo da #161 (``test_esforcos_oraculo.py``) usando os FIT sintéticos lidos por ``ler_fit``.
"""

import importlib.util
import sys
from pathlib import Path

import pytest

from app.ingestao.garmin.fit import ler_fit
from app.metricas.esforcos import (
    AQUECIMENTO,
    DESAQUECIMENTO,
    ESFORCO,
    LEVE,
    RECUPERACAO,
    REF_ATIVIDADE,
    REF_HABITUAL,
    VERSAO,
    VoltaTreino,
    eh_volta_de_pausa,
    montar_blocos,
    tempos_parados,
)

RAIZ = Path(__file__).parents[4]
ORACULO = Path(__file__).with_name("test_esforcos_oraculo.py")
PASTA_FIT = RAIZ / "tests" / "fixtures" / "garmin" / "esforcos"


def _voltas(specs):
    """specs: (distancia_m, duracao_s, parada_apos_s[, fc]); os inícios saem da soma das durações e paradas."""
    voltas, t = [], 0.0
    for i, s in enumerate(specs):
        dist, dur, parada = s[:3]
        voltas.append(VoltaTreino(i, t, dur, dist, s[3] if len(s) > 3 else None))
        t += dur + parada
    return voltas


def _cats(res):
    return [b.categoria for b in res.blocos]


def test_versao():
    assert VERSAO == "esforcos@1"


def test_1000_m_mais_500_m_no_mesmo_ritmo_viram_um_bloco_de_1500_m():
    # 1000 m em 240 s (240 s/km) + 500 m em 120,5 s (241 s/km): +0,42% < 5%, sem parada -> junta.
    # bloco: 1500 m, 360,5 s, pace = 360,5 / 1500 x 1000 = 240,3333 s/km; velocidade = 1500 / 360,5 x 3,6 = 14,9792.
    res = montar_blocos(_voltas([(1000, 240, 0), (500, 120.5, 0)]), "corrida", referencia=330)
    (b,) = res.blocos
    assert (b.volta_inicial, b.volta_final) == (0, 1)
    assert b.distancia_m == 1500 and b.duracao_s == 360.5
    assert b.pace_s_km == pytest.approx(240.3333, abs=1e-4)
    assert b.velocidade_kmh == pytest.approx(14.9792, abs=1e-4)
    assert b.categoria == ESFORCO  # 240,33 <= 330 x 0,90 = 297


def test_pace_do_bloco_nao_e_a_media_dos_paces():
    # 1000 m em 240 s + 200 m em 50 s (250 s/km): media dos paces 245; bloco 290 / 1200 x 1000 = 241,6667.
    (b,) = montar_blocos(_voltas([(1000, 240, 0), (200, 50, 0)]), "corrida", referencia=330).blocos
    assert b.pace_s_km == pytest.approx(241.6667, abs=1e-4)


def test_pausa_de_90_s_separa_dois_blocos():
    # dois km a 240 s/km com 90 s parados entre eles: 90 >= 15 -> dois blocos; parada_apos_s do primeiro = 90.
    res = montar_blocos(_voltas([(1000, 240, 90), (1000, 240, 0)]), "corrida", referencia=330)
    assert len(res.blocos) == 2
    assert [b.parada_apos_s for b in res.blocos] == [90, 0]
    assert res.blocos[1].inicio_offset_s == 330  # 240 + 90


def test_tempo_parado_vem_da_diferenca_dos_inicios():
    voltas = [VoltaTreino(0, 0, 240, 1000), VoltaTreino(1, 330, 240, 1000), VoltaTreino(2, 570, 240, 1000)]
    assert tempos_parados(voltas) == [90, 0, 0]  # (330 - 0) - 240 = 90; (570 - 330) - 240 = 0; ultima = 0


def test_limite_da_pausa_que_separa_na_corrida_15_s():
    # 14 s junta, 15 s separa (a pausa que separa e "maior ou igual a 15 s").
    assert len(montar_blocos(_voltas([(1000, 240, 14), (1000, 240, 0)]), "corrida", 330).blocos) == 1
    assert len(montar_blocos(_voltas([(1000, 240, 15), (1000, 240, 0)]), "corrida", 330).blocos) == 2


def test_limite_da_pausa_que_separa_no_ciclismo_30_s():
    # 25 km/h: 1500 m em 216 s. 29 s junta, 30 s separa; na corrida 29 s ja separaria.
    junta = montar_blocos(_voltas([(1500, 216, 29), (1500, 216, 0)]), "ciclismo", 20)
    separa = montar_blocos(_voltas([(1500, 216, 30), (1500, 216, 0)]), "ciclismo", 20)
    assert (len(junta.blocos), len(separa.blocos)) == (1, 2)
    # a parada dentro de um bloco juntado nao conta em parada_apos_s (ultimo bloco: 0)
    assert junta.blocos[0].parada_apos_s == 0


def test_limite_do_ritmo_parecido_5_por_cento():
    # 200 s/km vs 210 s/km: 10 / 200 = 5,0% -> junta (inclusivo). vs 211 s/km: 5,5% -> separa.
    assert len(montar_blocos(_voltas([(1000, 200, 0), (1000, 210, 0)]), "corrida", 330).blocos) == 1
    assert len(montar_blocos(_voltas([(1000, 200, 0), (1000, 211, 0)]), "corrida", 330).blocos) == 2


def test_compara_com_o_bloco_acumulado_e_nao_com_a_volta_anterior():
    # 300, 309 e 320 s/km. 309 vs 300 = 3,0% junta (bloco 609 / 2000 x 1000 = 304,5 s/km).
    # 320 vs 304,5 = 5,09% > 5% separa; contra a volta anterior seriam 3,56% e juntaria tudo.
    res = montar_blocos(_voltas([(1000, 300, 0), (1000, 309, 0), (1000, 320, 0)]), "corrida", 330)
    assert [(b.volta_inicial, b.volta_final) for b in res.blocos] == [(0, 1), (2, 2)]


def test_ciclismo_compara_a_velocidade():
    # 24 km/h e 25 km/h: 1 / 24 = 4,17% -> junta. 24 km/h e 26 km/h: 8,3% -> separa.
    v24, v25, v26 = (2400, 360, 0), (2500, 360, 0), (2600, 360, 0)
    assert len(montar_blocos(_voltas([v24, v25]), "ciclismo", 20).blocos) == 1
    assert len(montar_blocos(_voltas([v24, v26]), "ciclismo", 20).blocos) == 2


def test_primeiro_bloco_lento_e_aquecimento_e_ultimo_lento_e_desaquecimento():
    # ref 330 s/km, limiar 297. 2 km a 330 (aquecimento), 3 km a 250 (esforco), 1 km a 340 (desaquecimento).
    voltas = _voltas([(2000, 660, 0), (3000, 750, 0), (1000, 340, 0)])
    res = montar_blocos(voltas, "corrida", referencia=330)
    assert _cats(res) == [AQUECIMENTO, ESFORCO, DESAQUECIMENTO]
    assert res.referencia == 330 and res.ref_origem == REF_HABITUAL


def test_recuperacao_entre_esforcos():
    # 1000 m a 250, 400 m a 420 (recuperacao), 1000 m a 250.
    voltas = _voltas([(1000, 250, 0), (400, 168, 0), (1000, 250, 0)])
    assert _cats(montar_blocos(voltas, "corrida", 330)) == [ESFORCO, RECUPERACAO, ESFORCO]


def test_rodagem_com_lap_automatico_e_um_bloco_leve():
    # 6 km, 1 km por volta, 348 a 355 s/km: nenhum <= 297, todos a menos de 2% do bloco -> um bloco leve.
    # soma 2105 s; pace 2105 / 6000 x 1000 = 350,8333; FC (140 x 355 + 142 x 352 + 143 x 350 + 144 x 351 + 145 x 349
    # + 146 x 348) / 2105 = 301691 / 2105 = 143,3211.
    specs = [(1000, d, 0, fc) for d, fc in [(355, 140), (352, 142), (350, 143), (351, 144), (349, 145), (348, 146)]]
    res = montar_blocos(_voltas(specs), "corrida", referencia=330)
    (b,) = res.blocos
    assert b.categoria == LEVE and (b.volta_inicial, b.volta_final) == (0, 5)
    assert b.pace_s_km == pytest.approx(350.8333, abs=1e-4)
    assert b.fc_media == pytest.approx(143.3211, abs=1e-4)


def test_fc_do_bloco_e_ponderada_pela_duracao_so_sobre_voltas_com_fc():
    # (150 x 240 + 160 x 120) / 360 = 55200 / 360 = 153,3333; a volta sem FC fica fora da conta.
    specs = [(1000, 240, 0, 150), (500, 120, 0, 160), (500, 120, 0)]
    (b,) = montar_blocos(_voltas(specs), "corrida", 330).blocos
    assert b.fc_media == pytest.approx(153.3333, abs=1e-4)
    (sem,) = montar_blocos(_voltas([(1000, 240, 0)]), "corrida", 330).blocos
    assert sem.fc_media is None


def test_volta_de_pausa_pelo_pace_e_pela_distancia():
    corre = VoltaTreino(0, 0, 100, 400)
    assert not eh_volta_de_pausa(corre, "corrida")  # 250 s/km
    assert eh_volta_de_pausa(VoltaTreino(0, 0, 140, 200), "corrida")  # 700 s/km > 600
    assert not eh_volta_de_pausa(VoltaTreino(0, 0, 120, 200), "corrida")  # 600 s/km nao passa de 600
    assert eh_volta_de_pausa(VoltaTreino(0, 0, 30, 40), "corrida")  # 40 m < 50 m
    assert not eh_volta_de_pausa(VoltaTreino(0, 0, 30, 50), "corrida")  # 50 m nao e menor que 50 m
    assert eh_volta_de_pausa(VoltaTreino(0, 0, 60, 0), "corrida")  # sem distancia
    assert eh_volta_de_pausa(VoltaTreino(0, 0, 0, 100), "corrida")  # sem duracao
    # ciclismo: 5 km/h = 1,3889 m/s. 150 m em 120 s = 4,5 km/h pausa; 150 m em 108 s = 5,0 km/h nao.
    assert eh_volta_de_pausa(VoltaTreino(0, 0, 120, 150), "ciclismo")
    assert not eh_volta_de_pausa(VoltaTreino(0, 0, 108, 150), "ciclismo")


def test_volta_de_pausa_separa_e_o_tempo_dela_entra_na_parada():
    # 1 km a 240 s; volta parada de 40 m em 50 s (lap manual sem pausa automatica); 1 km a 240 s.
    # Sem a regra a volta de 40 m nao separaria nada (e nem seria bloco). parada_apos_s do 1o bloco = 50 s.
    res = montar_blocos(_voltas([(1000, 240, 0), (40, 50, 0), (1000, 240, 0)]), "corrida", 330)
    assert [(b.volta_inicial, b.volta_final) for b in res.blocos] == [(0, 0), (2, 2)]
    assert [b.parada_apos_s for b in res.blocos] == [50, 0]


def test_parada_do_relogio_mais_volta_de_pausa_somam():
    # 1 km, 20 s parado, volta de caminhada 100 m em 80 s (800 s/km), 10 s parado, 1 km.
    # parada_apos_s = 20 + 80 + 10 = 110 s.
    res = montar_blocos(_voltas([(1000, 240, 20), (100, 80, 10), (1000, 240, 0)]), "corrida", 330)
    assert [b.parada_apos_s for b in res.blocos] == [110, 0]


def test_pausa_no_inicio_ou_no_fim_nao_e_bloco():
    res = montar_blocos(_voltas([(20, 30, 0), (1000, 240, 0), (30, 40, 0)]), "corrida", 330)
    assert [(b.volta_inicial, b.volta_final) for b in res.blocos] == [(1, 1)]
    assert res.blocos[0].parada_apos_s == 0


def test_sem_esforco_tudo_e_leve():
    res = montar_blocos(_voltas([(1000, 340, 0), (400, 168, 0), (1000, 335, 0)]), "corrida", 330)
    assert _cats(res) == [LEVE, LEVE, LEVE]


def test_limiar_de_esforco_e_inclusivo():
    # ref 330 -> limiar 297 s/km: 297 e esforco, 298 nao.
    assert _cats(montar_blocos(_voltas([(1000, 297, 0)]), "corrida", 330)) == [ESFORCO]
    assert _cats(montar_blocos(_voltas([(1000, 298, 0)]), "corrida", 330)) == [LEVE]


def test_limiar_do_ciclismo_15_por_cento():
    # ref 20 km/h -> limiar 23 km/h: 2300 m em 360 s = 23,0 km/h e esforco; 2290 m em 360 s = 22,9 nao.
    assert _cats(montar_blocos(_voltas([(2300, 360, 0)]), "ciclismo", 20)) == [ESFORCO]
    assert _cats(montar_blocos(_voltas([(2290, 360, 0)]), "ciclismo", 20)) == [LEVE]


def test_referencia_da_atividade_e_a_mediana_ponderada_pela_duracao():
    # blocos: 1000 m em 300 s (300 s/km), 1000 m em 240 s, 1000 m em 300 s, separados por 60 s parados.
    # valores ordenados: (240, 240 s), (300, 300 s), (300, 300 s); total 840 s, metade 420 s;
    # acumulado 240 < 420, depois 540 >= 420 -> ref 300 s/km, limiar 270: so o de 240 e esforco.
    voltas = _voltas([(1000, 300, 60), (1000, 240, 60), (1000, 300, 0)])
    res = montar_blocos(voltas, "corrida")
    assert res.ref_origem == REF_ATIVIDADE and res.referencia == 300
    assert _cats(res) == [AQUECIMENTO, ESFORCO, DESAQUECIMENTO]


def test_referencia_da_atividade_com_esforco_dominante_perde_o_esforco():
    # Limitacao da ADR: 2 km lentos (330 s/km) e 4 km fortes (250 s/km) na mesma atividade; o esforco domina
    # o volume, a mediana ponderada e a dele (250) e nada passa de 250 x 0,90 = 225: tudo leve.
    voltas = _voltas([(2000, 660, 60), (4000, 1000, 0)])
    res = montar_blocos(voltas, "corrida")
    assert res.referencia == 250 and _cats(res) == [LEVE, LEVE]
    # com o ritmo habitual do atleta (330) o bloco de 250 s/km (<= 297) e esforco
    assert _cats(montar_blocos(voltas, "corrida", 330)) == [AQUECIMENTO, ESFORCO]


def test_ordena_pelas_ordens_e_nao_pela_posicao_na_lista():
    voltas = _voltas([(2000, 660, 0), (3000, 750, 0)])
    assert _cats(montar_blocos(list(reversed(voltas)), "corrida", 330)) == [AQUECIMENTO, ESFORCO]


def test_fit_sem_start_time_nao_tem_paradas():
    # todos os inicios em 0 (relogio sem start_time na lap): paradas 0, junta o que tem ritmo parecido.
    voltas = [VoltaTreino(i, 0.0, 240, 1000) for i in range(3)]
    assert tempos_parados(voltas) == [0, 0, 0]
    assert len(montar_blocos(voltas, "corrida", 330).blocos) == 1


def test_modalidade_sem_suporte_e_lista_vazia():
    voltas = _voltas([(100, 110, 0), (100, 112, 0)])
    res = montar_blocos(voltas, "natacao")
    assert res.blocos == () and res.referencia is None
    assert montar_blocos([], "corrida").blocos == ()


def test_intensidade_do_fit_nao_muda_a_categoria():
    # rotulada warmup mas a 240 s/km: a estrutura vence e o bloco e esforco (politica da ADR, item 1).
    v = [VoltaTreino(0, 0, 240, 1000, None, "warmup")]
    assert _cats(montar_blocos(v, "corrida", 330)) == [ESFORCO]


def test_blocos_numerados_em_sequencia():
    res = montar_blocos(_voltas([(2000, 660, 0), (3000, 750, 0), (1000, 340, 0)]), "corrida", 330)
    assert [b.ordem for b in res.blocos] == [0, 1, 2]


# --- Oráculo da #161 --------------------------------------------------------------------------------------


@pytest.fixture(scope="module")
def oraculo():
    spec = importlib.util.spec_from_file_location("test_esforcos_oraculo", ORACULO)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def _voltas_do_fit(nome):
    fit = ler_fit((PASTA_FIT / nome).read_bytes())
    return [VoltaTreino(v.ordem, v.inicio_offset_s, v.duracao_s, v.distancia_m, v.fc_media, v.intensidade)
            for v in fit.voltas]


NOMES = [
    "esforcos_corrida_400_com_pausa.fit",
    "esforcos_corrida_1500_lap_automatico.fit",
    "esforcos_corrida_continuo_forte.fit",
    "esforcos_corrida_rodagem_leve.fit",
    "esforcos_corrida_misto.fit",
    "esforcos_ciclismo_blocos_4min.fit",
    "esforcos_ciclismo_lap_automatico.fit",
]


@pytest.mark.parametrize("nome", NOMES)
def test_blocos_batem_com_o_oraculo(oraculo, nome):
    modalidade, ref, esperados = oraculo.ESPERADO[nome]
    res = montar_blocos(_voltas_do_fit(nome), modalidade, referencia=ref)
    assert len(res.blocos) == len(esperados)
    for b, e in zip(res.blocos, esperados):
        assert b.categoria == e.categoria, (nome, b.ordem)
        assert (b.volta_inicial, b.volta_final) == (e.volta_inicial, e.volta_final)
        assert b.distancia_m == pytest.approx(e.distancia_m, abs=0.01)
        assert b.duracao_s == pytest.approx(e.duracao_s, abs=1e-6)
        assert b.parada_apos_s == pytest.approx(e.parada_apos_s, abs=1e-6)
        assert b.fc_media == pytest.approx(e.fc_media, abs=1e-6)
        medida = b.pace_s_km if modalidade == "corrida" else b.velocidade_kmh
        assert medida == pytest.approx(e.intensidade, abs=1e-3)


@pytest.mark.parametrize("nome", NOMES)
def test_recuperacao_total_do_oraculo(oraculo, nome):
    # tempo parado entre dois esforcos = soma dos parada_apos_s dos blocos desse trecho (ADR, item 3).
    modalidade, ref, esperados = oraculo.ESPERADO[nome]
    res = montar_blocos(_voltas_do_fit(nome), modalidade, referencia=ref)
    assert sum(b.parada_apos_s for b in res.blocos) == pytest.approx(
        sum(e.parada_apos_s for e in esperados), abs=1e-6
    )


def test_tiros_de_400_com_90_s_dao_810_s_de_recuperacao():
    res = montar_blocos(_voltas_do_fit("esforcos_corrida_400_com_pausa.fit"), "corrida", 330)
    assert sum(b.parada_apos_s for b in res.blocos if b.categoria == ESFORCO) == 810  # 9 x 90 s


def test_referencia_da_atividade_nas_fixtures(oraculo):
    # Sem historico vale a mediana ponderada da propria atividade (ADR, "Limitacoes"). Contas a mao:
    # - 400 m com pausa: 880 s de esforco (220 s/km) contra 660 s (330) e 340 s (340); total 1880, metade 940;
    #   acumulado 880 < 940, depois 1540 >= 940 -> ref 330, igual ao oraculo.
    # - 1500 m: esforcos somam 361 + 363 + 365 = 1089 s de 2091 s (662 + 1089 + 340); o menor valor cujo
    #   acumulado chega a 1045,5 s e 243,33 s/km (o esforco): ref 243,33, limiar 219: nada e esforco, tudo leve.
    # - continuo forte e rodagem: um bloco so, ref = o proprio pace, nunca esforco: leve.
    # - misto: esforcos 5 x 250 + 8 x 92 = 1986 s; o resto 660 + 340 + 5 x 168 + 7 x 90 = 2470 s; total 4456, metade
    #   2228. Ordenado por pace: 230 (736 s), 250 (1250 s, acumulado 1986), 330 (660 s, acumulado 2646 >= 2228)
    #   -> ref 330, igual ao oraculo.
    # - ciclismo: a mediana (25 e 18 km/h) cai em bloco lento e o oraculo se mantem.
    esperado_leve = {
        "esforcos_corrida_1500_lap_automatico.fit",
        "esforcos_corrida_continuo_forte.fit",
        "esforcos_corrida_rodagem_leve.fit",
    }
    for nome in NOMES:
        modalidade, _ref, esperados = oraculo.ESPERADO[nome]
        res = montar_blocos(_voltas_do_fit(nome), modalidade)
        assert res.ref_origem == REF_ATIVIDADE
        cats = [b.categoria for b in res.blocos]
        if nome in esperado_leve:
            assert set(cats) == {LEVE}, nome
        else:
            assert cats == [e.categoria for e in esperados], nome
