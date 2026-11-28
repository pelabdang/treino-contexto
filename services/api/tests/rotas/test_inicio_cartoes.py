"""`GET /atletas/{id}/inicio/cartoes`: os cartões "Seus números" do início v4 (issue #575). Dados inventados; contas à mão."""

from datetime import datetime, time, timedelta, timezone

import pytest
from app.db.models import Atividade, Atleta, RecordePessoal, SemanaPadrao, SemanaPadraoItem
from app.db.session import get_session
from app.main import criar_app
from fastapi.testclient import TestClient
from sqlalchemy import event
from tests.acesso_de_teste import sem_login

HOJE = datetime.now(timezone.utc).date()
DIAS = ("segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo")
SEG = HOJE - timedelta(days=HOJE.weekday())


@pytest.fixture
def client(session):
    a = criar_app("http://localhost:8081")
    a.dependency_overrides[get_session] = lambda: session
    return TestClient(sem_login(a))


@pytest.fixture
def atleta(session):
    a = Atleta(nome="Atleta Ficticio")
    session.add(a)
    session.commit()
    return a


_n = iter(range(1, 100_000))


def _ativ(session, atleta, dias_atras, pace=None, modalidade="corrida", tipo="leve", dist=5000.0, dur=None, fonte_id=None):
    inicio = datetime.combine(HOJE - timedelta(days=dias_atras), time(12, 0), tzinfo=timezone.utc)
    a = Atividade(atleta_id=atleta.id, fonte="t", fonte_id=fonte_id or str(next(_n)), modalidade=modalidade, inicio=inicio, fuso_min=0,
                  duracao_s=dur if dur else (pace * dist / 1000 if pace else 1800.0), distancia_m=dist, fc_media=150.0, tipo_treino=tipo)
    session.add(a)
    session.flush()
    return a


def _cartoes(client, atleta):
    r = client.get(f"/atletas/{atleta.id}/inicio/cartoes")
    assert r.status_code == 200, r.text
    return r.json()


def _por_id(j):
    return {c["id"]: c for c in j["cartoes"]}


def test_sem_treino_nao_tem_cartao(client, atleta):
    j = _cartoes(client, atleta)
    assert j["atleta_id"] == atleta.id and j["cartoes"] == []


def test_404_atleta_inexistente(client):
    assert client.get("/atletas/9999/inicio/cartoes").status_code == 404


def test_esta_semana_com_semana_passada(client, session, atleta):
    _ativ(session, atleta, HOJE.weekday())  # segunda desta semana, 30 min
    for k in range(1, 5):  # 4 treinos na semana passada
        _ativ(session, atleta, HOJE.weekday() + k)
    c = _por_id(_cartoes(client, atleta))["esta_semana"]
    assert (c["formato"], c["rotulo"], c["valor"], c["apoio"]) == ("pequeno", "Esta semana", "1 treino", "30 min · semana passada: 4")
    assert c["rotulo_acessivel"] == "Esta semana, 1 treino, 30 min, semana passada 4 treinos" and c["texto"] is None and c["barras"] == []
    assert c["destino"] == {"tela": "evolucao", "serie_id": "corrida.volume_km"}


def test_esta_semana_sem_semana_anterior(client, session, atleta):
    _ativ(session, atleta, HOJE.weekday(), dur=3600.0 * 2 + 37 * 60)
    c = _por_id(_cartoes(client, atleta))["esta_semana"]
    assert c["apoio"] == "2 h 37 min · sem semana anterior"


def test_esta_semana_some_sem_treino_na_semana(client, session, atleta):
    _ativ(session, atleta, HOJE.weekday() + 1)  # domingo passado
    assert "esta_semana" not in _por_id(_cartoes(client, atleta))


def test_hoje_na_semana(client, session, atleta):
    _ativ(session, atleta, 1)  # fixa o "hoje" no fuso 0
    sp = SemanaPadrao(atleta_id=atleta.id, vigente_desde=HOJE - timedelta(days=30), definido_por="atleta")
    sp.itens = [SemanaPadraoItem(dia_semana=HOJE.isoweekday(), modalidade="corrida", tipo_treino="leve"),
                SemanaPadraoItem(dia_semana=(HOJE.isoweekday() % 7) + 1, modalidade="natacao", tipo_treino=None)]
    session.add(sp)
    session.commit()
    c = _por_id(_cartoes(client, atleta))["hoje_na_semana"]
    assert (c["rotulo"], c["valor"], c["apoio"]) == (f"Hoje, {DIAS[HOJE.weekday()]}", "Corrida leve", "da sua rotina")
    assert c["destino"] == {"tela": "semana_padrao"}


def test_hoje_na_semana_some_sem_item_hoje_e_sem_semana(client, session, atleta):
    _ativ(session, atleta, 1)
    assert "hoje_na_semana" not in _por_id(_cartoes(client, atleta))
    sp = SemanaPadrao(atleta_id=atleta.id, vigente_desde=HOJE - timedelta(days=30), definido_por="atleta")
    sp.itens = [SemanaPadraoItem(dia_semana=(HOJE.isoweekday() % 7) + 1, modalidade="corrida", tipo_treino="leve")]
    session.add(sp)
    session.commit()
    assert "hoje_na_semana" not in _por_id(_cartoes(client, atleta))


def _volume_8_semanas(session, atleta):
    for k in range(1, 5):  # R: 4 semanas completas, 10 km cada
        _ativ(session, atleta, HOJE.weekday() + 7 * k, tipo=None, dist=10000.0)
    for k in range(5, 9):  # A: as 4 antes, 8 km cada
        _ativ(session, atleta, HOJE.weekday() + 7 * k, tipo=None, dist=8000.0)


def test_volume_das_4_semanas(client, session, atleta):
    _volume_8_semanas(session, atleta)
    c = _por_id(_cartoes(client, atleta))["volume_4_semanas"]
    assert (c["formato"], c["rotulo"], c["valor"], c["apoio"]) == ("largo", "Volume das 4 semanas", "10 km por semana", "2 km a mais que nas 4 anteriores")
    assert [(b["data_texto"], b["valor_texto"], b["destaque"], b["altura_pct"]) for b in c["barras"]] == [
        (f"{SEG - timedelta(days=7 * k):%d/%m}", "10", k == 1, 100) for k in (4, 3, 2, 1)]  # as 4 iguais: todas 100
    assert c["texto"] == ("Volume de corrida nas últimas 4 semanas: 10 km por semana (mediana), 2 km a mais (25%) que nas 4 semanas anteriores "
                          "(8 km por semana).")
    assert c["destino"] == {"tela": "evolucao", "serie_id": "corrida.volume_km"}
    assert c["rotulo_acessivel"].startswith("Volume das 4 semanas, 10 km por semana, 2 km a mais que nas 4 anteriores. Barras: semana de")


def test_volume_some_com_menos_de_3_semanas_com_volume(client, session, atleta):
    for k in (1, 2, 5, 6, 7, 8):  # só 2 das 4 semanas de R têm treino
        _ativ(session, atleta, HOJE.weekday() + 7 * k, tipo=None, dist=10000.0)
    assert "volume_4_semanas" not in _por_id(_cartoes(client, atleta))


def test_volume_some_sem_as_4_anteriores(client, session, atleta):
    for k in range(1, 5):
        _ativ(session, atleta, HOJE.weekday() + 7 * k, tipo=None, dist=10000.0)
    assert "volume_4_semanas" not in _por_id(_cartoes(client, atleta))


def test_em_movimento_escolhe_a_maior_mudanca_em_relacao_ao_piso(client, session, atleta):
    for d, p in ((2, 342), (10, 336), (20, 348), (30, 354), (40, 348), (50, 360)):  # leve: 5:42 contra 5:54, razão 12/10,62 = 1,13
        _ativ(session, atleta, d, pace=p)
    for d, p in ((3, 300), (11, 300), (21, 300), (31, 360), (41, 360), (51, 360)):  # moderado: 5:00 contra 6:00, razão 60/10,8 = 5,6
        _ativ(session, atleta, d, pace=p, tipo="moderado")
    c = _por_id(_cartoes(client, atleta))["em_movimento"]
    assert (c["formato"], c["rotulo"], c["valor"], c["apoio"]) == ("largo", "Em movimento", "Pace dos seus treinos moderados", None)
    assert c["texto"] == ("Pace dos seus treinos moderados nas últimas 4 semanas: 5:00/km (mediana de 3 treinos), 60 s/km mais rápido que nas "
                          "4 semanas anteriores (6:00/km, 3 treinos).")
    assert c["destino"] == {"tela": "evolucao", "serie_id": "corrida.pace.moderado"}


def test_em_movimento_some_com_mudanca_pequena(client, session, atleta):
    for d, p in ((2, 342), (10, 342), (20, 342), (30, 346), (40, 346), (50, 346)):  # 4 s/km < 10,38 (3% de 346)
        _ativ(session, atleta, d, pace=p)
    assert "em_movimento" not in _por_id(_cartoes(client, atleta))


def _recorde(session, atleta, categoria, valor, dias, ativ=None, unidade="s"):
    session.add(RecordePessoal(atleta_id=atleta.id, origem="garmin_export", modalidade="corrida", categoria=categoria, valor=valor, unidade=unidade,
                               alcancado_em=datetime.combine(HOJE - timedelta(days=dias), time(8, 0), tzinfo=timezone.utc),
                               atividade_fonte_id=ativ, versao_leitura="teste"))


def test_melhor_marca_novo_recorde_com_treino(client, session, atleta):
    a = _ativ(session, atleta, 10, fonte_id="g-123")
    _recorde(session, atleta, "Best 5km Run", 1300.0, 200)
    _recorde(session, atleta, "Best 5km Run", 1270.0, 10, ativ="g-123")  # 21:10
    session.commit()
    c = _por_id(_cartoes(client, atleta))["melhor_marca"]
    assert (c["formato"], c["rotulo"], c["valor"], c["apoio"]) == ("pequeno", "Melhor marca", "21:10 · 5 km", f"novo recorde · {HOJE - timedelta(days=10):%d/%m}")
    assert c["destino"] == {"tela": "treino", "atividade_id": a.id}


def test_melhor_marca_sem_treino_conhecido_e_primeira_marca(client, session, atleta):
    _ativ(session, atleta, 1)
    _recorde(session, atleta, "Best Half Marathon", 5025.0, 3)  # 1:23:45
    session.commit()
    c = _por_id(_cartoes(client, atleta))["melhor_marca"]
    assert (c["valor"], c["apoio"]) == ("1:23:45 · meia maratona", f"recorde do relógio · {HOJE - timedelta(days=3):%d/%m}")
    assert c["destino"] == {"tela": "evolucao"}


def test_melhor_marca_some_fora_dos_30_dias_ou_sem_nome_conhecido(client, session, atleta):
    _ativ(session, atleta, 1)
    _recorde(session, atleta, "Best 10km Run", 2700.0, 45)  # antigo
    _recorde(session, atleta, "Farthest Run", 21000.0, 2, unidade="m")  # não é tempo
    _recorde(session, atleta, "Best Tipo Novo", 800.0, 2)  # fora do formato dos recordes de tempo
    session.commit()
    assert "melhor_marca" not in _por_id(_cartoes(client, atleta))


def test_melhor_marca_o_recorde_vigente_e_o_ultimo_batido(client, session, atleta):
    _ativ(session, atleta, 1)
    _recorde(session, atleta, "Best 5km Run", 1200.0, 100)  # o melhor de antes, mais rápido
    _recorde(session, atleta, "Best 5km Run", 1290.0, 5)  # o último registrado vale (a fonte guarda o vigente)
    session.commit()
    assert _por_id(_cartoes(client, atleta))["melhor_marca"]["valor"] == "21:30 · 5 km"


def test_ordem_fixa_e_outro_atleta_nao_entra(client, session, atleta):
    outro = Atleta(nome="Outro")
    session.add(outro)
    session.commit()
    _ativ(session, outro, 0)
    assert _cartoes(client, atleta)["cartoes"] == []
    _ativ(session, atleta, HOJE.weekday())
    _recorde(session, atleta, "Best 5km Run", 1270.0, 2)
    session.commit()
    assert [c["id"] for c in _cartoes(client, atleta)["cartoes"]] == ["esta_semana", "melhor_marca"]


def test_numero_de_consultas(client, session, atleta):
    _volume_8_semanas(session, atleta)
    for d in range(1, 60):
        _ativ(session, atleta, d, pace=340 + d % 9, tipo=("leve", "moderado", "longo")[d % 3])
    session.commit()
    n = []
    event.listen(session.get_bind(), "before_cursor_execute", lambda *a: n.append(1))
    assert len(_cartoes(client, atleta)["cartoes"]) >= 2
    assert len(n) <= 8


def test_openapi(client):
    esquema = client.get("/openapi.json").json()
    assert "/atletas/{atleta_id}/inicio/cartoes" in esquema["paths"]
    assert {"id", "formato", "rotulo", "valor", "apoio", "texto", "barras", "destino", "rotulo_acessivel"} <= set(esquema["components"]["schemas"]["CartaoOut"]["required"])


def test_nome_da_marca_generico():
    from app.servicos.inicio_cartoes import _nome_da_marca as n

    assert [n(c) for c in ("Best 1km Run", "Best 1mile Run", "Best 3km Run", "Best 400m Pool Swim", "Best 40km Cycle", "Best Half Marathon",
                           "Best Marathon")] == ["1 km", "1 milha", "3 km", "400 m", "40 km", "meia maratona", "maratona"]
    assert [n(c) for c in ("Farthest Run", "Max Avg Power (20 min)", "Most Steps in a Day", "Best Tipo Novo", "Longest Pool Swim")] == [None] * 5


def test_altura_das_barras_relativa_a_maior(client, session, atleta):
    # R (4 semanas completas, da mais antiga à mais recente): 10, 5, 0, 3 km; A: 8 km nas 4 anteriores. Alturas: 100, 50, 0, 30 (3/10).
    for k, km in ((4, 10), (3, 5), (1, 3)):
        _ativ(session, atleta, HOJE.weekday() + 7 * k, tipo=None, dist=km * 1000.0)
    for k in range(5, 9):
        _ativ(session, atleta, HOJE.weekday() + 7 * k, tipo=None, dist=8000.0)
    c = _por_id(_cartoes(client, atleta))["volume_4_semanas"]
    assert [(b["valor_texto"], b["altura_pct"]) for b in c["barras"]] == [("10", 100), ("5", 50), ("0", 0), ("3", 30)]


def test_altura_arredonda_meio_para_cima_e_zero_sem_volume():
    from app.servicos.inicio_cartoes import altura_pct

    assert [altura_pct(v, 8) for v in (1, 3, 8, 0)] == [13, 38, 100, 0]  # 12,5 -> 13; 37,5 -> 38
    assert altura_pct(0, 0) == 0
