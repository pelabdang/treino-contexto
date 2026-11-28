"""Campos do Início v5 (adendo 18 da ADR 0004): `esta_semana.dias[]`, `apoio_curto`, `comparacao_texto` e `PendenteOut.pergunta_texto`. Dados inventados."""

from datetime import date, datetime, timedelta, timezone

import pytest
from app.db.models import Atividade, Atleta
from app.servicos.checkin import pergunta_do_checkin

from tests.rotas.test_inicio_cartoes import DIAS, HOJE, SEG, _ativ, _cartoes, _por_id, atleta, client  # noqa: F401


def _semana(client, atleta):
    return _por_id(_cartoes(client, atleta))["esta_semana"]


SEG_FIXA = date(2030, 3, 11)  # segunda-feira; o "hoje" e injetado (`agora`), entao os testes rodam igual em qualquer dia da semana


def _ativ_fixa(session, atleta, dia, hora, modalidade):
    a = Atividade(atleta_id=atleta.id, fonte="t", fonte_id=f"f{dia}{hora}{modalidade}", modalidade=modalidade, fuso_min=0, duracao_s=1800.0, distancia_m=5000.0,
                  inicio=datetime(2030, 3, dia, hora, 0, tzinfo=timezone.utc))
    session.add(a)
    session.flush()


def _dias_de(session, atleta, hoje_dia):
    """Segunda: corrida e natacao; terca: corrida e ciclismo; e, quando `hoje` nao e segunda nem terca, natacao hoje. `hoje` = 2030-03-`hoje_dia`, 15h UTC."""
    from app.servicos import inicio_cartoes as ic
    _ativ_fixa(session, atleta, 11, 8, "corrida")
    _ativ_fixa(session, atleta, 11, 18, "natacao")
    if hoje_dia >= 12:
        _ativ_fixa(session, atleta, 12, 8, "corrida")
        _ativ_fixa(session, atleta, 12, 18, "ciclismo")
    if hoje_dia == 13:
        _ativ_fixa(session, atleta, 13, 8, "natacao")
    session.commit()
    agora = datetime(2030, 3, hoje_dia, 23, 0, tzinfo=timezone.utc)
    esta = [c for c in ic.cartoes(session, atleta.id, agora).cartoes if c.id == "esta_semana"][0]
    return esta.dias


@pytest.mark.parametrize("hoje_dia,estados", [
    (11, ["hoje", "futuro", "futuro", "futuro", "futuro", "futuro", "futuro"]),   # segunda
    (13, ["feito", "feito", "hoje", "futuro", "futuro", "futuro", "futuro"]),     # quarta, com treino hoje
    (16, ["feito", "feito", "vazio", "vazio", "vazio", "hoje", "futuro"]),        # sabado, sem treino hoje
    (17, ["feito", "feito", "vazio", "vazio", "vazio", "vazio", "hoje"]),         # domingo: sem dia futuro
])
def test_dias_cobrem_feito_hoje_vazio_e_futuro_em_qualquer_dia_da_semana(session, atleta, hoje_dia, estados):
    dias = _dias_de(session, atleta, hoje_dia)
    assert [d.rotulo for d in dias] == ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"]
    assert [d.estado for d in dias] == estados
    assert all(d.modalidades == [] for d in dias if d.estado in ("vazio", "futuro"))


def test_textos_dos_dias_concordam_no_genero_e_no_numero_e_dizem_hoje_e_por_vir(session, atleta):
    d = _dias_de(session, atleta, 16)  # sabado
    assert d[0].modalidades == ["corrida", "natacao"] and d[0].rotulo_acessivel == "segunda, corrida e natação feitas"
    assert d[1].modalidades == ["corrida", "ciclismo"] and d[1].rotulo_acessivel == "terça, corrida e ciclismo feitos"  # misto: masculino
    assert d[2].rotulo_acessivel == "quarta, sem treino" and d[4].rotulo_acessivel == "sexta, sem treino"
    assert d[5].rotulo_acessivel == "sábado, hoje, sem treino ainda"
    assert d[6].rotulo_acessivel == "domingo, ainda por vir"


def test_hoje_com_treino_continua_hoje_com_as_modalidades(session, atleta):
    d = _dias_de(session, atleta, 13)
    assert d[2].estado == "hoje" and d[2].modalidades == ["natacao"] and d[2].rotulo_acessivel == "quarta, hoje, natação feita"
    outra = Atleta(nome="Outra Ficticia")
    session.add(outra)
    session.commit()
    d0 = _dias_de(session, outra, 11)[0]
    assert d0.estado == "hoje" and d0.rotulo_acessivel == "segunda, hoje, corrida e natação feitas"


def test_a_rota_traz_os_7_dias_com_os_mesmos_campos(client, session, atleta):
    _ativ(session, atleta, 0)
    session.commit()
    dias = _semana(client, atleta)["dias"]
    assert len(dias) == 7 and all(set(d) == {"rotulo", "estado", "modalidades", "rotulo_acessivel"} for d in dias)
    assert dias[HOJE.weekday()]["estado"] == "hoje" and all(d["estado"] in ("feito", "hoje", "vazio", "futuro") for d in dias)


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
    ("corrida", 4, "Como foi a corrida de segunda?"),     # 11/03/2030
    ("corrida", 5, "Como foi a corrida de domingo?"),
    ("corrida", 6, "Como foi a corrida de sábado?"),
    ("corrida", 7, "Como foi a corrida do dia 08/03?"),
    ("natacao", 14, "Como foi a natação do dia 01/03?"),   # a semana ja se repetiu: o dia da semana ficaria ambiguo
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
