"""`GET /atletas/{id}/evolucao/series/{serie_id}`: pontos, período, faixa do normal, destaques e frase (issue #574). Dados inventados; contas à mão."""

from datetime import UTC, datetime, time, timedelta, timezone

import pytest
from app.db.models import Atividade, Atleta, CargaAtividade
from app.db.session import get_session
from app.main import criar_app
from app.metricas import carga as cg
from fastapi.testclient import TestClient
from sqlalchemy import event
from tests.acesso_de_teste import sem_login

HOJE = datetime.now(timezone.utc).date()
SEMANA = ("seg", "ter", "qua", "qui", "sex", "sáb", "dom")


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


def _ativ(session, atleta, dias_atras, pace=None, modalidade="corrida", tipo="leve", fc=150.0, dist=5000.0, subtipo=None, dur=None):
    inicio = datetime.combine(HOJE - timedelta(days=dias_atras), time(12, 0), tzinfo=timezone.utc)
    a = Atividade(atleta_id=atleta.id, fonte="t", fonte_id=str(next(_n)), modalidade=modalidade, subtipo=subtipo, inicio=inicio, fuso_min=0,
                  duracao_s=dur if dur else (pace * dist / 1000 if pace else 1800.0), distancia_m=dist, fc_media=fc, tipo_treino=tipo)
    session.add(a)
    session.flush()
    return a


def _get(client, atleta, serie, q=""):
    r = client.get(f"/atletas/{atleta.id}/evolucao/series/{serie}{q}")
    assert r.status_code == 200, r.text
    return r.json()


def _dt(d):
    return f"{SEMANA[d.weekday()]} {d:%d/%m}"


def _seis_do_oraculo(session, atleta):
    """R (1 a 28 dias atrás): 342, 336, 348 -> mediana 342; A (29 a 56): 354, 348, 360 -> mediana 354 (nota do Caio)."""
    return {d: _ativ(session, atleta, d, pace=p) for d, p in ((2, 342), (10, 336), (20, 348), (30, 354), (40, 348), (50, 360))}


def test_pace_leve_oraculo_do_caio(client, session, atleta):
    ativs = _seis_do_oraculo(session, atleta)
    j = _get(client, atleta, "corrida.pace.leve")
    assert (j["id"], j["periodo"], j["unidade"], j["modalidade"], j["grupo"]) == ("corrida.pace.leve", "12s", "/km", "corrida", "Ritmo")
    assert j["fim"] == HOJE.isoformat() and j["inicio"] == (HOJE - timedelta(days=83)).isoformat()
    assert [p["atividade_id"] for p in j["pontos"]] == [ativs[d].id for d in (50, 40, 30, 20, 10, 2)]  # do mais antigo ao mais recente
    ultimo = j["pontos"][-1]
    assert (ultimo["valor"], ultimo["valor_texto"], ultimo["data_texto"]) == (342.0, "5:42", _dt(HOJE - timedelta(days=2)))
    assert ultimo["rotulo"] == f"Treino de {HOJE - timedelta(days=2):%d/%m}, 5:42 por quilômetro"
    assert (j["ultimo_valor_texto"], j["ultimo_rotulo"]) == ("5:42", f"último treino, {_dt(HOJE - timedelta(days=2))}")
    assert [p["melhor"] for p in j["pontos"]] == [False, False, False, False, True, False]  # 336 é o menor pace
    f = j["frase"]
    assert f["versao"] == "frase_evolucao@1" and f["tipo"] == "comparada" and f["mudanca"] == "menor" and f["a_favor"] is True
    assert f["texto"] == ("Pace dos seus treinos leves nas últimas 4 semanas: 5:42/km (mediana de 3 treinos), 12 s/km mais rápido que nas "
                          "4 semanas anteriores (5:54/km, 3 treinos).")
    assert (f["valor_atual"], f["valor_anterior"], f["n_atual"], f["n_anterior"]) == (342.0, 354.0, 3, 3)
    # 6 treinos: ainda aprendendo o normal (mínimo 8), sem faixa e sem "fora do normal"
    assert j["referencia"] is None and all(p["fora_do_normal"] is None for p in j["pontos"])  # 6 treinos: todos aprendendo
    assert j["aprendendo_texto"] == "Ainda estamos aprendendo o seu normal: faltam 2 treinos para mostrar a faixa."
    assert j["eixo"]["invertido"] is True and j["eixo"]["minimo"] <= 336 and j["eixo"]["maximo"] >= 360


def test_faixa_do_normal_e_triangulo_e_o_selo_do_treino(client, session, atleta):
    # 10 treinos a 342 (5:42) nos dias 1 a 10 e um a 420 (7:00) hoje. Faixa de agora (12 semanas até ontem): mediana 342, MAD 0, desvio = piso de 3%
    # = 10,26; faixa 342 ± 2,5 x 10,26 = 316,35 a 367,65. O triângulo é o selo do PRÓPRIO treino (linha_base@3 dele): o de hoje tem 10 antes, a 342: fora.
    for d in range(1, 11):
        _ativ(session, atleta, d, pace=342)
    lento = _ativ(session, atleta, 0, pace=420)
    j = _get(client, atleta, "corrida.pace.leve")
    r = j["referencia"]
    assert (r["mediana"], r["n"], r["texto"]) == (342.0, 10, "Seu normal 5:16 a 6:08")
    assert r["minimo"] == pytest.approx(316.35) and r["maximo"] == pytest.approx(367.65)
    assert j["aprendendo_texto"] is None
    por = {p["atividade_id"]: p for p in j["pontos"]}
    assert (por[lento.id]["fora_do_normal"], por[lento.id]["normal_estado"]) == (True, "fora")
    assert "fora do seu normal" in por[lento.id]["rotulo"]
    mais_antigo = j["pontos"][0]  # 10 dias atrás: sem treino antes dele
    assert (mais_antigo["normal_estado"], mais_antigo["fora_do_normal"]) == ("aprendendo", None)
    dia1 = next(p for p in j["pontos"] if p["data"] == (HOJE - timedelta(days=1)).isoformat())  # 9 antes, a 342: dentro
    assert (dia1["normal_estado"], dia1["fora_do_normal"]) == ("dentro", False)
    assert j["eixo"]["maximo"] >= 420  # o eixo cobre os pontos e a faixa


def test_triangulo_nao_depende_da_faixa_de_agora(client, session, atleta):
    # Um treino antigo lento (400) tem 8 antes mais rápidos: o selo dele é "fora", mesmo que a faixa de hoje (a 342 e 400 juntos) o inclua.
    for d in range(20, 30):
        _ativ(session, atleta, d, pace=342)
    antigo = _ativ(session, atleta, 12, pace=400)
    for d in range(1, 6):
        _ativ(session, atleta, d, pace=400)  # o normal de hoje fica mais lento
    j = _get(client, atleta, "corrida.pace.leve")
    p = next(x for x in j["pontos"] if x["atividade_id"] == antigo.id)
    assert (p["normal_estado"], p["fora_do_normal"]) == ("fora", True)  # o estado do treino NO DIA DELE
    assert j["referencia"] is not None  # a faixa de agora (12 semanas até ontem) existe, mas não decide o triângulo


def test_periodo_muda_o_grafico_e_nao_a_frase(client, session, atleta):
    _seis_do_oraculo(session, atleta)
    velho = _ativ(session, atleta, 150, pace=500)
    curto, medio, longo = (_get(client, atleta, "corrida.pace.leve", f"?periodo={p}") for p in ("12s", "6m", "1a"))
    assert len(curto["pontos"]) == 6 and len(medio["pontos"]) == 7 and len(longo["pontos"]) == 7
    assert medio["pontos"][0]["atividade_id"] == velho.id
    assert curto["frase"] == medio["frase"] == longo["frase"]
    assert medio["inicio"] == (HOJE - timedelta(days=181)).isoformat() and longo["inicio"] == (HOJE - timedelta(days=364)).isoformat()


def test_fc_texto_inteiro_e_ponto_sem_fc(client, session, atleta):
    for d, fc in ((2, 150.0), (10, 148.0), (20, 152.0), (30, 146.0), (40, 148.0), (50, 150.0)):
        _ativ(session, atleta, d, fc=fc)
    sem = _ativ(session, atleta, 5, fc=None)
    j = _get(client, atleta, "corrida.fc.leve")
    assert j["unidade"] == "bpm" and j["eixo"]["invertido"] is False
    p = next(x for x in j["pontos"] if x["atividade_id"] == sem.id)
    assert (p["valor"], p["valor_texto"], p["rotulo"]) == (None, None, f"{_dt(HOJE - timedelta(days=5))}, sem valor")
    assert all(not x["melhor"] for x in j["pontos"])  # FC não tem "melhor"
    # R: 150, 148, 152 (FC de 5 dias atrás sem valor) -> 150; A: 146, 148, 150 -> 148; d = 2 < 4 bpm: parecida
    assert j["frase"]["texto"].startswith("Frequência cardíaca dos seus treinos leves nas últimas 4 semanas: 150 bpm (mediana de 3 treinos), parecida com")
    assert j["frase"]["mudanca"] == "parecido"


def test_esteira_fora_do_pace(client, session, atleta):
    for d in range(1, 9):
        _ativ(session, atleta, d, pace=342, subtipo="esteira")
    assert _get(client, atleta, "corrida.pace.leve")["pontos"] == []
    assert len(_get(client, atleta, "corrida.fc.leve")["pontos"]) == 8


def test_volume_por_semana_e_frase_a_mao(client, session, atleta):
    seg = HOJE - timedelta(days=HOJE.weekday())
    for k in range(1, 5):  # 4 semanas completas (R), 10 km cada
        _ativ(session, atleta, (HOJE - seg).days + 7 * k, tipo=None, dist=10000.0)
    for k in range(5, 9):  # as 4 antes (A), 8 km cada
        _ativ(session, atleta, (HOJE - seg).days + 7 * k, tipo=None, dist=8000.0)
    j = _get(client, atleta, "corrida.volume_km")
    assert j["unidade"] == "km" and len(j["pontos"]) == 12
    assert [p["data"] for p in j["pontos"]][-1] == seg.isoformat()
    assert j["pontos"][-1]["parcial"] is True and j["pontos"][-1]["valor"] == 0.0 and j["pontos"][-1]["atividade_id"] is None
    assert [p["valor"] for p in j["pontos"][-9:-1]] == [8.0] * 4 + [10.0] * 4
    assert j["pontos"][0]["valor"] == 0.0 and j["pontos"][-2]["data_texto"] == f"semana de {seg - timedelta(days=7):%d/%m}"
    assert (j["ultimo_valor_texto"], j["ultimo_rotulo"]) == ("10", f"semana de {seg - timedelta(days=7):%d/%m}")  # a semana em curso não é "último"
    assert j["frase"]["texto"] == ("Volume de corrida nas últimas 4 semanas: 10 km por semana (mediana), 2 km a mais (25%) que nas 4 semanas "
                                   "anteriores (8 km por semana).")
    assert j["referencia"] is None and j["eixo"]["minimo"] <= 0


def test_condicionamento(client, session, atleta):
    for d in (3, 2, 1):
        a = _ativ(session, atleta, d, tipo=None)
        a.carga = CargaAtividade(estado="calculada", carga=60.0, metodo="hrtss", cobertura_pct=100.0, granularidade="atividade",
                                 entrada="x" * 64, versao=cg.VERSAO, calculado_em=datetime(2026, 4, 1, tzinfo=UTC))
    session.commit()
    j = _get(client, atleta, "geral.ctl")
    assert j["unidade"] == "" and j["pontos"] and all(p["atividade_id"] is None for p in j["pontos"])
    assert all(p["aprendendo"] for p in j["pontos"]) and all(p["valor_texto"] is None for p in j["pontos"])  # menos de 42 dias: sem número
    assert j["frase"]["tipo"] in ("so_valor", "sem_dado")
    assert j["ultimo_valor_texto"] is None


def test_serie_do_catalogo_sem_treino_nao_e_erro(client, atleta):
    j = _get(client, atleta, "corrida.pace.leve")
    assert j["pontos"] == [] and j["eixo"] is None and j["referencia"] is None and j["ultimo_valor_texto"] is None
    assert j["frase"]["tipo"] == "sem_treino" and j["frase"]["texto"] == "Sem treinos desse tipo nas últimas 4 semanas."


def test_tiros_sem_sessao_na_janela(client, atleta):
    j = _get(client, atleta, "corrida.tiros")
    assert j["pontos"] == [] and j["frase"]["tipo"] == "sem_treino"


def test_outro_atleta_nao_entra(client, session, atleta):
    outro = Atleta(nome="Outro")
    session.add(outro)
    session.commit()
    _seis_do_oraculo(session, outro)
    assert _get(client, atleta, "corrida.pace.leve")["pontos"] == []


def test_erros(client, atleta):
    assert client.get("/atletas/9999/evolucao/series/corrida.pace.leve").status_code == 404
    r = client.get(f"/atletas/{atleta.id}/evolucao/series/nao.existe")
    assert r.status_code == 404 and r.json() == {"detail": "série não encontrada"}
    assert client.get(f"/atletas/{atleta.id}/evolucao/series/corrida.pace.leve?periodo=2a").status_code == 422


def test_numero_de_consultas_nao_depende_dos_pontos(client, session, atleta):
    for d in range(1, 60):
        _ativ(session, atleta, d, pace=340 + d % 7)
    session.commit()
    n = []
    event.listen(session.get_bind(), "before_cursor_execute", lambda *a: n.append(1))
    assert len(_get(client, atleta, "corrida.pace.leve")["pontos"]) == 59
    assert len(n) <= 10


def test_openapi_descreve_a_serie(client):
    esquema = client.get("/openapi.json").json()
    assert "/atletas/{atleta_id}/evolucao/series/{serie_id}" in esquema["paths"]
    ponto = esquema["components"]["schemas"]["PontoSerieOut"]
    assert {"atividade_id", "data", "data_texto", "valor", "valor_texto", "melhor", "fora_do_normal", "rotulo"} <= set(ponto["required"])
