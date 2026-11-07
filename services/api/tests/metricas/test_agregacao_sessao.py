"""Testes da agregação por sessão (#12), valores calculados à mão.

pace = soma(duração) / soma(distância) x 1000 (s/km)
FC   = soma(FC x duração) / soma(duração), só tiros com FC
"""

from datetime import date

import pytest

from app.metricas.tiros_1km import (
    SessaoTiros,
    VoltaEntrada,
    agregar_sessao,
    formatar_pace,
    para_apresentacao,
    serie_por_sessao,
    sessao_de_blocos,
)


def t(ordem, dist, dur, fc=None):
    return VoltaEntrada(ordem, dist, dur, fc_media=fc, intensidade="active")


def test_sessao_do_exemplo_da_issue():
    # tiros: 1000 m/240 s/160 bpm; 1000 m/236 s/165 bpm; 990 m/238 s sem FC.
    # duração = 240 + 236 + 238 = 714 s; distância = 1000 + 1000 + 990 = 2990 m
    # pace = 714 / 2990 x 1000 = 238,795 s/km (o teste seguinte separa a
    # fórmula ponderada da média simples dos paces).
    # FC = (160 x 240 + 165 x 236) / (240 + 236) = 77340 / 476 = 162,479 bpm
    # (o tiro sem FC fica fora, inclusive do peso).
    p = agregar_sessao("a1", date(2026, 3, 1), [t(1, 1000, 240, 160), t(2, 1000, 236, 165), t(3, 990, 238)])
    assert p.n_tiros == 3
    assert p.pace_s_km == pytest.approx(714 / 2990 * 1000)
    assert para_apresentacao(p.pace_s_km) == 238.8
    assert p.fc_media == pytest.approx(77340 / 476)
    assert para_apresentacao(p.fc_media) == 162.5


def test_pace_ponderado_pela_distancia_nao_e_media_simples():
    # 1000 m em 250 s (250 s/km) e 500 m em 100 s (200 s/km).
    # ponderado: 350 / 1500 x 1000 = 233,333 s/km
    # média simples dos paces: (250 + 200)/2 = 225 (errada).
    p = agregar_sessao(1, date(2026, 3, 1), [t(1, 1000, 250), t(2, 500, 100)])
    assert p.pace_s_km == pytest.approx(233.3333333)
    assert p.pace_s_km != pytest.approx(225)


def test_fc_ponderada_pela_duracao():
    # 150 bpm por 100 s e 180 bpm por 300 s: (15000 + 54000)/400 = 172,5
    # (média simples seria 165).
    p = agregar_sessao(1, date(2026, 3, 1), [t(1, 400, 100, 150), t(2, 1200, 300, 180)])
    assert p.fc_media == pytest.approx(172.5)


def test_sessao_sem_nenhuma_fc():
    p = agregar_sessao(1, date(2026, 3, 1), [t(1, 1000, 240), t(2, 1000, 240)])
    assert p.fc_media is None
    assert p.pace_s_km == pytest.approx(240.0)  # 480 / 2000 x 1000


def test_arredondamento_so_na_apresentacao():
    p = agregar_sessao(1, date(2026, 3, 1), [t(1, 1000, 240, 160), t(2, 1000, 236, 165), t(3, 990, 238)])
    assert p.pace_s_km != 238.8  # valor cru preservado: 238,7959...
    assert para_apresentacao(None) is None


def test_sessao_sem_tiros_levanta_erro():
    with pytest.raises(ValueError):
        agregar_sessao(1, date(2026, 3, 1), [])


def _sessao(aid, dia, fc, dur):
    # 3 tiros iguais: pace = 3 x dur / 3000 x 1000 = dur s/km.
    return SessaoTiros(aid, dia, True, tuple(t(i, 1000, dur, fc) for i in range(1, 4)))


def test_serie_fora_de_ordem_sai_ordenada_por_data():
    sessoes = [
        _sessao("c", date(2026, 3, 20), 170, 230),
        _sessao("a", date(2026, 3, 1), 160, 250),
        _sessao("b", date(2026, 3, 10), 165, 240),
    ]
    serie = serie_por_sessao(sessoes)
    assert [p.atividade_id for p in serie] == ["a", "b", "c"]
    assert [p.pace_s_km for p in serie] == pytest.approx([250, 240, 230])
    assert [p.fc_media for p in serie] == pytest.approx([160, 165, 170])


def _blocos(specs):
    """Voltas sintéticas (dist, dur) -> blocos pelo esforcos@1, ritmo habitual de 330 s/km."""
    from app.metricas import esforcos as ef
    from app.metricas.tiros_1km import BlocoEntrada

    voltas, t = [], 0.0
    for i, (d, du, parada) in enumerate(specs):
        voltas.append(ef.VoltaTreino(i, t, du, d))
        t += du + parada
    r = ef.montar_blocos(voltas, "corrida", referencia=330.0)
    faixas = {e.bloco_ordem: e.faixa for e in ef.esforcos_corrida(r)}
    return [BlocoEntrada(b.ordem, b.categoria, b.volta_inicial, b.volta_final, b.distancia_m, b.duracao_s,
                         b.fc_media, faixas.get(b.ordem), b.parada_apos_s) for b in r.blocos]


def test_rodagem_leve_nao_entra_na_serie():
    # 8 voltas de 1000 m a ~333 s/km: um bloco leve, nenhum tiro (ver test_tiros_1km).
    duracoes = [330, 335, 328, 340, 332, 336, 331, 334]
    leve = sessao_de_blocos("leve", date(2026, 3, 5), _blocos([(1000, d, 0) for d in duracoes]))
    assert leve.eh_intervalado is False and leve.tiros == ()
    # 4 tiros: 1000 m/240 s, intercalados com 400 m/180 s.
    specs = []
    for _ in range(4):
        specs += [(1000, 240, 0), (400, 180, 0)]
    inter = sessao_de_blocos("int", date(2026, 3, 8), _blocos(specs))
    serie = serie_por_sessao([leve, inter])
    assert [p.atividade_id for p in serie] == ["int"]
    # pace = 4 x 240 / 4000 x 1000 = 240 s/km (os 4 tiros de 1000 m a 240 s).
    assert serie[0].n_tiros == 4
    assert serie[0].pace_s_km == pytest.approx(240.0)


def test_serie_vazia():
    assert serie_por_sessao([]) == []


def test_versao_da_deteccao_chega_ao_ponto_da_serie():
    # 3 tiros de 1000 m com recuperação de 400 m: a sessão é intervalada e a versão da regra
    # (tiros_1km@6) viaja da detecção até o ponto agregado.
    sessao = sessao_de_blocos("a1", date(2025, 3, 4), _blocos(
        [(1000, 250, 0), (400, 150, 0), (1000, 250, 0), (400, 150, 0), (1000, 250, 0)]))
    assert sessao.versao == "tiros_1km@6" and len(sessao.tiros) == 3
    (ponto,) = serie_por_sessao([sessao])
    assert ponto.versao == "tiros_1km@6"
    assert agregar_sessao("a1", date(2025, 3, 4), sessao.tiros).versao == "tiros_1km@6"


def test_melhor_tiro_do_exemplo_da_issue_151():
    # 1000 m/250 s/165 bpm; 1000 m/244 s/170 bpm; 990 m/247 s sem FC.
    # paces: 250,0; 244,0; 247 / 990 x 1000 = 249,495. Melhor: 244,0 s/km (4:04), FC 170.
    # média: (250 + 244 + 247) / (1000 + 1000 + 990) x 1000 = 741 / 2990 x 1000 = 247,826
    p = agregar_sessao("a1", date(2026, 3, 1), [t(1, 1000, 250, 165), t(2, 1000, 244, 170), t(3, 990, 247)])
    assert p.melhor_pace_s_km == pytest.approx(244.0)
    assert p.melhor_fc_media == 170
    assert p.melhor_ordem == 2
    assert p.pace_s_km == pytest.approx(741 / 2990 * 1000)
    assert para_apresentacao(p.pace_s_km) == 247.8
    assert formatar_pace(p.melhor_pace_s_km) == "4:04"


def test_melhor_tiro_empate_fica_com_o_primeiro():
    # 1000 m/240 s/160 bpm e 1000 m/240 s/170 bpm: mesmo pace (240), vale o primeiro (FC 160).
    p = agregar_sessao(1, date(2026, 3, 1), [t(1, 1000, 240, 160), t(2, 1000, 240, 170)])
    assert p.melhor_pace_s_km == pytest.approx(240.0)
    assert p.melhor_fc_media == 160
    assert p.melhor_ordem == 1


def test_melhor_tiro_empate_de_pace_com_distancias_diferentes():
    # 500 m/120 s = 240 s/km e 1000 m/240 s = 240 s/km: empate, vale o primeiro (500 m, sem FC).
    p = agregar_sessao(1, date(2026, 3, 1), [t(1, 500, 120), t(2, 1000, 240, 170)])
    assert p.melhor_ordem == 1
    assert p.melhor_fc_media is None


def test_melhor_tiro_sem_fc_nao_troca_por_outro_tiro():
    # melhor: 1000 m/236 s sem FC (236 s/km); os outros têm FC mas são mais lentos.
    # FC do melhor = None (não empresta a FC de outro); a FC média da sessão segue existindo:
    # (160 x 240 + 165 x 238) / 478 = 77670 / 478 = 162,490
    p = agregar_sessao(1, date(2026, 3, 1), [t(1, 1000, 240, 160), t(2, 1000, 236), t(3, 1000, 238, 165)])
    assert p.melhor_pace_s_km == pytest.approx(236.0)
    assert p.melhor_fc_media is None
    assert p.melhor_ordem == 2
    assert p.fc_media == pytest.approx(77670 / 478)


def test_melhor_tiro_de_um_unico_tiro_e_o_proprio_tiro():
    p = agregar_sessao(1, date(2026, 3, 1), [t(7, 1000, 245, 168)])
    assert (p.melhor_pace_s_km, p.melhor_fc_media, p.melhor_ordem) == (245.0, 168, 7)


def test_melhor_tiro_ignora_tiro_sem_distancia():
    # 0 m/10 s não tem pace: não pode ser o melhor. Vale o de 1000 m/245 s.
    p = agregar_sessao(1, date(2026, 3, 1), [t(1, 0, 10, 150), t(2, 1000, 245, 168)])
    assert (p.melhor_pace_s_km, p.melhor_ordem) == (245.0, 2)
