"""Filtro do ritmo habitual na série de tiros (issue #53, tiros_1km@6). Dados sintéticos, contas à mão.

Ritmo habitual: mediana do pace das corridas de mais de 3 km (sem esteira) anteriores à sessão, 84 dias;
< 10 na janela usa todo o histórico; sem histórico não filtra. Os tiros valem se pace <= habitual x 0,90.
Com o histórico a 330 s/km: limite = 330 x 0,90 = 297 s/km.
"""

import itertools
from datetime import datetime, timedelta, timezone

import pytest

from app.db.models import Atividade, Atleta, Segmento
from app.servicos.evolucao_tiros import classificar_atividades, serie_tiros_1km

BASE = datetime(2025, 3, 1, 9, 0, tzinfo=timezone.utc)
_ids = itertools.count(1)


def _corrida(session, atleta, dias, pace, km=8.0, subtipo=None, voltas=None):
    """Corrida `dias` depois de BASE. Sem `voltas`, é uma rodagem sem segmentos."""
    voltas = voltas or []
    dur = pace * km if not voltas else sum(v[2] for v in voltas)
    dist = km * 1000 if not voltas else sum(v[1] for v in voltas)
    a = Atividade(atleta_id=atleta.id, fonte="garmin_export", fonte_id=str(next(_ids)),
                  modalidade="corrida", subtipo=subtipo, inicio=BASE + timedelta(days=dias), fuso_min=0,
                  duracao_s=dur, distancia_m=dist)
    t = 0.0
    for i, (intens, d, du) in enumerate(voltas):
        a.segmentos.append(Segmento(ordem=i, tipo="volta", inicio_offset_s=t, duracao_s=du, distancia_m=d,
                                    fc_media=150, pace_s_km=du / d * 1000, intensidade=intens))
        t += du
    session.add(a)
    session.flush()
    return a


def _tiros(pace):
    """Aquec. 2000 m + 4 x (1000 m a `pace` s/km, 400 m de recuperação a 450) + desaq. 1000 m."""
    voltas = [("warmup", 2000, 2000 * 0.36)]
    for k in range(4):
        voltas.append(("active", 1000, pace))
        if k < 3:
            voltas.append(("rest", 400, 180))
    voltas.append(("cooldown", 1000, 380))
    return voltas


@pytest.fixture
def atleta(session):
    at = Atleta(nome="Ficticio")
    session.add(at)
    session.flush()
    return at


def _historico_facil(session, atleta, n=10, pace=330):
    for i in range(n):
        _corrida(session, atleta, dias=i * 3, pace=pace)


def _serie(session, atleta):
    classificar_atividades(session, atleta.id)
    return serie_tiros_1km(session, atleta.id)


def test_tiros_reais_ficam_dentro(session, atleta):
    _historico_facil(session, atleta)
    _corrida(session, atleta, dias=40, pace=0, voltas=_tiros(270))  # 270 <= 297
    serie = _serie(session, atleta)
    assert len(serie) == 1
    assert serie[0].pace_s_km == pytest.approx(270.0)
    assert serie[0].versao == "tiros_1km@6"


def test_rodagem_com_voltas_separadas_por_paradas_fica_fora(session, atleta):
    # "tiros" a 330 s/km (o ritmo habitual): desde a @5 o esforço já pede pace <= 330 x 0,90 = 297 (esforcos@1,
    # mesmo ritmo habitual), então nenhuma volta vira tiro. Na @4 o detector os marcava e só o filtro da série os tirava.
    _historico_facil(session, atleta)
    a = _corrida(session, atleta, dias=40, pace=0, voltas=_tiros(330))
    classificar_atividades(session, atleta.id)
    assert sum(1 for s in a.segmentos if s.tipo == "tiro") == 0
    assert serie_tiros_1km(session, atleta.id) == []  # a série não aceita


def test_limite_exato_entra_na_serie(session, atleta):
    _historico_facil(session, atleta)
    _corrida(session, atleta, dias=40, pace=0, voltas=_tiros(297.0))  # 330 x 0,90 = 297
    assert len(_serie(session, atleta)) == 1


def test_logo_acima_do_limite_fica_fora(session, atleta):
    _historico_facil(session, atleta)
    _corrida(session, atleta, dias=40, pace=0, voltas=_tiros(297.1))
    assert _serie(session, atleta) == []


def test_sem_historico_nao_filtra(session, atleta):
    # Única corrida, sem histórico: não há ritmo habitual para filtrar a sessão. A referência do esforço é a mediana
    # ponderada da própria atividade (esforcos@1, ``ref_origem = atividade``): aquec. 720 s a 360, 4 tiros de 270
    # (1080 s), 3 recuperações de 180 s a 450 (540 s) e desaq. 380 s a 380. Total 2720 s; metade 1360 s; ordenando
    # por pace, 270 chega a 1080 s e 360 a 1800 s: a mediana é 360, limiar 324. Os tiros de 270 entram.
    _corrida(session, atleta, dias=0, pace=0, voltas=_tiros(270))
    assert len(_serie(session, atleta)) == 1


def test_sem_historico_tiros_no_ritmo_da_propria_atividade_nao_aparecem(session, atleta):
    # Mesma sessão com "tiros" a 330 s/km: a mediana da atividade fica em 330 (limiar 297), nenhum bloco é esforço.
    # É a limitação da referência de reserva (ADR 0008, "Limitações"), que na @4 não existia: a série não filtrava.
    _corrida(session, atleta, dias=0, pace=0, voltas=_tiros(330))
    assert _serie(session, atleta) == []


def _historico_antigo(session, atleta):
    # 4 corridas antigas a 300 e 3 a 330, todas a mais de 84 dias da sessão em dias=200.
    # Na janela de 84 dias só ficam 3 (a 330): < 10, então usa as 7: ordenadas 300 x4, 330 x3,
    # mediana = 4a = 300; limite = 300 x 0,90 = 270.
    for d in (0, 5, 10, 15):
        _corrida(session, atleta, dias=d, pace=300)
    for d in (190, 192, 194):
        _corrida(session, atleta, dias=d, pace=330)


def test_menos_de_10_corridas_na_janela_usa_o_historico_todo(session, atleta):
    _historico_antigo(session, atleta)
    _corrida(session, atleta, dias=200, pace=0, voltas=_tiros(290))  # 290 > 270: fora
    assert _serie(session, atleta) == []


def test_menos_de_10_na_janela_e_tiros_abaixo_do_limite_entram(session, atleta):
    _historico_antigo(session, atleta)
    _corrida(session, atleta, dias=200, pace=0, voltas=_tiros(265))  # 265 <= 270: dentro
    assert len(_serie(session, atleta)) == 1


def test_esteira_e_corridas_curtas_nao_entram_no_habitual(session, atleta):
    # 10 corridas válidas a 330 s/km (habitual 330, limite 297) e 15 de esteira e 15 de 3 km, todas
    # a 500 s/km. Se entrassem, a mediana iria a 500 (limite 475) e uns "tiros" a 400 passariam.
    # Sem elas, 400 > 297: fora.
    _historico_facil(session, atleta)
    for i in range(15):
        _corrida(session, atleta, dias=i, pace=500, subtipo="esteira")
        _corrida(session, atleta, dias=i, pace=500, km=3.0)
    _corrida(session, atleta, dias=40, pace=0, voltas=_tiros(400))
    assert _serie(session, atleta) == []


def test_historico_fora_do_periodo_pedido_conta(session, atleta):
    _historico_facil(session, atleta)
    _corrida(session, atleta, dias=40, pace=0, voltas=_tiros(330))
    _corrida(session, atleta, dias=45, pace=0, voltas=_tiros(270))
    classificar_atividades(session, atleta.id)
    dia = (BASE + timedelta(days=45)).date()
    serie = serie_tiros_1km(session, atleta.id, inicio=dia, fim=dia)
    assert [p.data for p in serie] == [dia]  # só a de 270; o histórico anterior (fora do período) foi usado


# ---------------------------------------------------------------------------
# #168: a série lê os esforços (bloco_atividade). Exemplos da issue, no banco, com histórico de 330 s/km.
# ---------------------------------------------------------------------------


def test_sessao_com_2_tiros_entra_na_serie(session, atleta):
    # 2 x 1000 m a 250 s/km com 400 m a 420 s/km (168 s): 250 <= 297 e <= 420 x 0,92. Pace da sessão = 250 s/km.
    _historico_facil(session, atleta)
    voltas = [("warmup", 2000, 720), ("active", 1000, 250), ("rest", 400, 168), ("active", 1000, 250),
              ("cooldown", 1000, 380)]
    _corrida(session, atleta, dias=40, pace=0, voltas=voltas)
    (ponto,) = _serie(session, atleta)
    assert ponto.n_tiros == 2 and ponto.pace_s_km == pytest.approx(250.0)
    assert ponto.melhor_pace_s_km == pytest.approx(250.0)


def test_treino_misto_conta_so_os_tiros_de_1km(session, atleta):
    # 5 x (1000 m a 250 + 400 m a 420) e depois 8 x (400 m a 230 + 200 m a 450): os 5 de 1 km, pace 250 s/km.
    _historico_facil(session, atleta)
    voltas = [("warmup", 2000, 720)]
    for _ in range(5):
        voltas += [("active", 1000, 250), ("rest", 400, 168)]
    for _ in range(8):
        voltas += [("active", 400, 92), ("rest", 200, 90)]
    a = _corrida(session, atleta, dias=40, pace=0, voltas=voltas)
    (ponto,) = _serie(session, atleta)
    assert ponto.n_tiros == 5 and ponto.pace_s_km == pytest.approx(250.0)
    assert sum(s.tipo == "tiro" for s in a.segmentos) == 5  # os 400 m não são tiro de 1 km
    assert (a.tipo_treino, a.tipo_origem) == ("intervalado", "sugestao")


def test_tiros_curtos_com_km_de_aquecimento_e_desaquecimento_ficam_fora(session, atleta):
    _historico_facil(session, atleta)
    voltas = [("warmup", 1000, 335)]
    for _ in range(8):
        voltas += [("active", 400, 92), ("rest", 200, 90)]
    voltas += [("cooldown", 1000, 340)]
    _corrida(session, atleta, dias=40, pace=0, voltas=voltas)
    assert _serie(session, atleta) == []


def test_rodagem_com_autolap_fica_fora(session, atleta):
    _historico_facil(session, atleta)
    _corrida(session, atleta, dias=40, pace=0, voltas=[("active", 1000, d) for d in (330, 335, 328, 340, 332)])
    assert _serie(session, atleta) == []
