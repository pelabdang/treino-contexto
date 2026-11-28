"""Campos do Início v5 (adendo 18 da ADR 0004): `esta_semana.dias[]`, `apoio_curto`, `comparacao_texto` e `PendenteOut.pergunta_texto`. Dados inventados."""

from datetime import date, datetime, timedelta, timezone

import pytest
from app.db.models import Atividade
from app.servicos.checkin import pergunta_do_checkin

from tests.rotas.test_inicio_cartoes import DIAS, HOJE, SEG, _ativ, _cartoes, _por_id, atleta, client  # noqa: F401


def _semana(client, atleta):
    return _por_id(_cartoes(client, atleta))["esta_semana"]


def test_dias_sao_7_de_segunda_a_domingo_com_estado_e_texto_pronto(client, session, atleta):
    hoje = HOJE.weekday()  # 0 = segunda
    _ativ(session, atleta, 0, modalidade="corrida")
    if hoje >= 2:  # um dia passado com corrida e natacao e outro sem treino
        _ativ(session, atleta, hoje, modalidade="corrida", dur=1800.0)
        _ativ(session, atleta, hoje, modalidade="natacao", dur=1800.0)
    session.commit()
    c = _semana(client, atleta)
    dias = c["dias"]
    assert [d["rotulo"] for d in dias] == ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"]
    assert all(set(d) == {"rotulo", "estado", "modalidades", "rotulo_acessivel"} for d in dias)
    for i, d in enumerate(dias):
        assert d["rotulo_acessivel"].startswith(DIAS[i] + ", ")
        if i == hoje:
            assert d["estado"] == "hoje" and d["modalidades"] == ["corrida"] if hoje != 0 else True
        elif i > hoje:
            assert d["estado"] == "futuro" and d["modalidades"] == [] and d["rotulo_acessivel"].endswith("ainda por vir")
    assert dias[hoje]["estado"] == "hoje"
    if hoje >= 2:
        assert dias[0]["estado"] == "feito" and dias[0]["modalidades"] == ["corrida", "natacao"]
        assert dias[0]["rotulo_acessivel"] == "segunda, corrida e natação feitas"
        assert dias[1]["estado"] == "vazio" and dias[1]["rotulo_acessivel"] == "terça, sem treino"
    assert dias[hoje]["rotulo_acessivel"] == f"{DIAS[hoje]}, hoje, corrida feita" if hoje == 0 else dias[hoje]["rotulo_acessivel"].startswith(f"{DIAS[hoje]}, hoje")


def test_estados_feito_hoje_vazio_e_futuro_sem_o_app_comparar_datas(client, session, atleta):
    hoje = HOJE.weekday()
    if hoje < 2 or hoje == 6:
        pytest.skip("precisa de um dia passado sem treino e de um dia futuro na semana")
    _ativ(session, atleta, 0)
    _ativ(session, atleta, hoje)  # segunda
    session.commit()
    estados = [d["estado"] for d in _semana(client, atleta)["dias"]]
    esperado = ["feito"] + ["vazio"] * (hoje - 1) + ["hoje"] + ["futuro"] * (6 - hoje)
    assert estados == esperado and set(estados) <= {"feito", "hoje", "vazio", "futuro"}


def test_dia_futuro_e_vazio_sao_diferentes_e_hoje_com_treino_continua_hoje(client, session, atleta):
    _ativ(session, atleta, 0, modalidade="natacao")
    session.commit()
    dias = _semana(client, atleta)["dias"]
    hoje = HOJE.weekday()
    assert dias[hoje]["estado"] == "hoje" and dias[hoje]["modalidades"] == ["natacao"]
    assert all(d["estado"] == "futuro" for d in dias[hoje + 1:]) and all(d["estado"] == "vazio" for d in dias[:hoje])


def test_texto_dos_dias_concorda_no_genero_e_no_numero(client, session, atleta):
    if HOJE.weekday() < 3:
        pytest.skip("precisa de pelo menos 3 dias na semana")
    _ativ(session, atleta, HOJE.weekday(), modalidade="ciclismo", tipo=None)      # segunda: ciclismo (masculino)
    _ativ(session, atleta, HOJE.weekday() - 1, modalidade="corrida")                 # terca: corrida
    _ativ(session, atleta, HOJE.weekday() - 1, modalidade="ciclismo", tipo=None)     # terca: corrida e ciclismo (misto: masculino)
    session.commit()
    d = _semana(client, atleta)["dias"]
    assert d[0]["rotulo_acessivel"] == "segunda, ciclismo feito"
    assert d[1]["rotulo_acessivel"] == "terça, corrida e ciclismo feitos"


def test_hoje_sem_treino_ainda(client, session, atleta):
    if HOJE.weekday() == 0:
        pytest.skip("segunda: o cartao so existe com treino na semana")
    _ativ(session, atleta, 1, modalidade="corrida")
    session.commit()
    d = _semana(client, atleta)["dias"][HOJE.weekday()]
    assert d["estado"] == "hoje" and d["modalidades"] == [] and d["rotulo_acessivel"] == f"{DIAS[HOJE.weekday()]}, hoje, sem treino ainda"


def test_apoio_curto_e_comparacao_separados_e_apoio_antigo_mantido(client, session, atleta):
    _ativ(session, atleta, 0, dur=3600.0)
    _ativ(session, atleta, 7, dur=1800.0)  # semana passada (mesmo dia da semana)
    _ativ(session, atleta, 8, dur=1800.0)
    session.commit()
    c = _semana(client, atleta)
    assert c["apoio_curto"] == f"1 treino · 1 h" and c["comparacao_texto"] == "semana passada: 2"
    assert c["apoio"] == "1 h · semana passada: 2"  # compatibilidade: o texto antigo nao muda
    assert c["valor"] == "1 treino"


def test_sem_semana_anterior(client, session, atleta):
    _ativ(session, atleta, 0, dur=1800.0)
    session.commit()
    c = _semana(client, atleta)
    assert c["comparacao_texto"] == "sem semana anterior" and c["apoio_curto"] == "1 treino · 30 min" and c["apoio"] == "30 min · sem semana anterior"


def test_os_outros_cartoes_nao_ganham_os_campos(client, session, atleta):
    _ativ(session, atleta, 0)
    session.commit()
    for c in _cartoes(client, atleta)["cartoes"]:
        if c["id"] != "esta_semana":
            assert c["dias"] == [] and c["apoio_curto"] is None and c["comparacao_texto"] is None


# --- pergunta_texto do check-in --------------------------------------------------------------------------------------------------------

HOJE_FIXO = date(2030, 3, 15)  # sexta-feira


def _ativ_em(modalidade, dias_atras):
    inicio = datetime(2030, 3, 15, 12, tzinfo=timezone.utc) - timedelta(days=dias_atras)
    return Atividade(atleta_id=1, fonte="t", fonte_id="x", modalidade=modalidade, inicio=inicio, fuso_min=0, duracao_s=1800.0)


@pytest.mark.parametrize("modalidade,dias_atras,esperado", [
    ("natacao", 1, "Como foi a natação de ontem?"),
    ("corrida", 0, "Como foi a corrida de hoje?"),
    ("corrida", 3, "Como foi a corrida de terça?"),       # 12/03/2030 foi terca
    ("ciclismo", 2, "Como foi o ciclismo de quarta?"),
    ("corrida", 6, "Como foi a corrida de sábado?"),
    ("corrida", 7, "Como foi a corrida do dia 08/03?"),   # a semana ja se repetiu: o dia da semana ficaria ambiguo
    ("outra", 1, "Como foi o treino de ontem?"),
])
def test_pergunta_do_checkin_com_data_relativa(modalidade, dias_atras, esperado):
    assert pergunta_do_checkin(_ativ_em(modalidade, dias_atras), HOJE_FIXO) == esperado


def test_pendente_traz_a_pergunta_pronta(client, session, atleta):
    a = _ativ(session, atleta, 1, modalidade="natacao", tipo=None)
    session.commit()
    j = client.get(f"/atletas/{atleta.id}/checkins/pendentes").json()
    [p] = [x for x in j["pendentes"] if x["atividade_id"] == a.id]
    assert p["pergunta_texto"] == "Como foi a natação de ontem?" and p["titulo"].startswith("Natação")
