"""Filtro do ritmo habitual na série de tiros (issue #53, tiros_1km@4). Dados sintéticos, contas à mão.

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
    assert serie[0].versao == "tiros_1km@4"


def test_rodagem_com_voltas_separadas_por_paradas_fica_fora(session, atleta):
    # "tiros" a 330 s/km (o ritmo habitual): o detector os acha (voltas separadas por recuperações),
    # mas 330 > 297: o filtro do ritmo habitual os tira da série.
    _historico_facil(session, atleta)
    a = _corrida(session, atleta, dias=40, pace=0, voltas=_tiros(330))
    classificar_atividades(session, atleta.id)
    assert sum(1 for s in a.segmentos if s.tipo == "tiro") == 4  # o detector marca
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
    # Sessão de tiros lentos (330) sendo a única corrida: sem histórico, não há filtro.
    _corrida(session, atleta, dias=0, pace=0, voltas=_tiros(330))
    assert len(_serie(session, atleta)) == 1


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
