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
    para_apresentacao,
    serie_por_sessao,
    sessao_de_voltas,
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


def test_rodagem_leve_nao_entra_na_serie():
    # 8 voltas de 1000 m a ~333 s/km: nenhum tiro (ver test_tiros_1km).
    duracoes = [330, 335, 328, 340, 332, 336, 331, 334]
    leve = sessao_de_voltas(
        "leve", date(2026, 3, 5), [VoltaEntrada(i + 1, 1000, d, 140) for i, d in enumerate(duracoes)]
    )
    assert leve.eh_intervalado is False and leve.tiros == ()
    # 4 tiros: 1000 m/240 s, intercalados com 400 m/180 s.
    voltas = []
    o = 1
    for _ in range(4):
        voltas += [VoltaEntrada(o, 1000, 240, 170, "active"), VoltaEntrada(o + 1, 400, 180, 130, "recovery")]
        o += 2
    inter = sessao_de_voltas("int", date(2026, 3, 8), voltas)
    serie = serie_por_sessao([leve, inter])
    assert [p.atividade_id for p in serie] == ["int"]
    # pace = 4 x 240 / 4000 x 1000 = 240 s/km; FC = 170 (todos iguais).
    assert serie[0].n_tiros == 4
    assert serie[0].pace_s_km == pytest.approx(240.0)
    assert serie[0].fc_media == pytest.approx(170.0)


def test_serie_vazia():
    assert serie_por_sessao([]) == []


def test_versao_da_deteccao_chega_ao_ponto_da_serie():
    # 3 tiros de 1000 m com contraste de intensidade: a sessão é intervalada e
    # a versão da regra (tiros_1km@1) viaja da detecção até o ponto agregado.
    voltas = [
        VoltaEntrada(0, 1000, 250, 160, "active"),
        VoltaEntrada(1, 400, 150, 140, "rest"),
        VoltaEntrada(2, 1000, 250, 162, "active"),
        VoltaEntrada(3, 400, 150, 141, "rest"),
        VoltaEntrada(4, 1000, 250, 164, "active"),
    ]
    sessao = sessao_de_voltas("a1", date(2025, 3, 4), voltas)
    assert sessao.versao == "tiros_1km@1"
    (ponto,) = serie_por_sessao([sessao])
    assert ponto.versao == "tiros_1km@1"
    assert agregar_sessao("a1", date(2025, 3, 4), sessao.tiros).versao == "tiros_1km@1"
