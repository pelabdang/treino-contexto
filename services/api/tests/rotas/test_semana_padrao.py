"""GET e PUT da semana-padrao (issue #264, ADR 0011, itens 1 e 9). Dados inventados."""

from datetime import date, datetime, timezone

import pytest
from app.db.models import Atividade, Atleta, SemanaPadrao, SemanaPadraoItem
from app.db.session import get_session
from app.main import criar_app
from app.servicos import semana_padrao as sp
from fastapi.testclient import TestClient
from sqlalchemy import func, select


@pytest.fixture
def client(session):
    app = criar_app("http://localhost:8081")
    app.dependency_overrides[get_session] = lambda: session
    return TestClient(app)


@pytest.fixture
def atleta(session):
    a = Atleta(nome="Ana")
    session.add(a)
    session.commit()
    return a.id


def corpo(desde="2026-03-02", por="atleta", itens=None):
    if itens is None:
        itens = [
            {"dia_semana": 2, "modalidade": "corrida", "tipo_treino": "fartlek"},
            {"dia_semana": 1, "modalidade": "natacao", "tipo_treino": None},
        ]
    return {"vigente_desde": desde, "definido_por": por, "itens": itens}


def put(client, atleta_id, **kw):
    return client.put(f"/atletas/{atleta_id}/semana-padrao", json=corpo(**kw))


def get(client, atleta_id, em=None):
    return client.get(f"/atletas/{atleta_id}/semana-padrao", params={"em": em} if em else None)


def test_put_grava_e_devolve_itens_ordenados_com_texto_do_dia(client, atleta):
    r = put(client, atleta)
    assert r.status_code == 200
    j = r.json()
    assert j["vigente_desde"] == "2026-03-02" and j["definido_por"] == "atleta"
    assert j["atividades_reaplicadas"] == 0
    assert j["itens"] == [
        {"dia_semana": 1, "dia_semana_texto": "segunda", "modalidade": "natacao", "tipo_treino": None},
        {"dia_semana": 2, "dia_semana_texto": "terça", "modalidade": "corrida", "tipo_treino": "fartlek"},
    ]
    assert j["definido_em"].endswith("-03:00")  # America/Sao_Paulo, como o exemplo da ADR


def test_get_devolve_vigente_e_historico_em_ordem_decrescente(client, atleta):
    put(client, atleta, desde="2026-02-02", itens=[{"dia_semana": d, "modalidade": "corrida"} for d in range(1, 8)])
    put(client, atleta, desde="2026-03-02")
    j = get(client, atleta, "2026-03-10").json()
    assert j["atleta_id"] == atleta and j["em"] == "2026-03-10"
    assert j["vigente"]["vigente_desde"] == "2026-03-02" and len(j["vigente"]["itens"]) == 2
    assert j["vigencias"] == [
        {"vigente_desde": "2026-03-02", "definido_por": "atleta", "total_itens": 2},
        {"vigente_desde": "2026-02-02", "definido_por": "atleta", "total_itens": 7},
    ]


def test_vigencia_vale_no_proprio_dia_e_termina_quando_a_proxima_comeca(client, atleta):
    put(client, atleta, desde="2026-02-02", itens=[{"dia_semana": 2, "modalidade": "corrida", "tipo_treino": "intervalado"}])
    put(client, atleta, desde="2026-03-02")
    assert get(client, atleta, "2026-03-01").json()["vigente"]["vigente_desde"] == "2026-02-02"
    assert get(client, atleta, "2026-03-02").json()["vigente"]["vigente_desde"] == "2026-03-02"
    assert get(client, atleta, "2026-02-02").json()["vigente"]["itens"][0]["tipo_treino"] == "intervalado"


def test_antes_da_primeira_vigencia_nao_ha_plano_e_nao_olha_a_seguinte(client, atleta):
    put(client, atleta, desde="2026-02-02")
    j = get(client, atleta, "2026-01-27").json()
    assert j["vigente"] is None
    assert len(j["vigencias"]) == 1  # o historico segue inteiro


def test_atleta_sem_semana_padrao(client, atleta):
    j = get(client, atleta, "2026-03-10").json()
    assert j["vigente"] is None and j["vigencias"] == []


def test_vigencia_vazia_e_valida_e_encerra_o_plano(client, atleta):
    put(client, atleta, desde="2026-02-02")
    r = put(client, atleta, desde="2026-04-06", por="professor", itens=[])
    assert r.status_code == 200 and r.json()["itens"] == []
    j = get(client, atleta, "2026-04-10").json()
    assert j["vigente"]["itens"] == [] and j["vigente"]["definido_por"] == "professor"
    assert j["vigencias"][0] == {"vigente_desde": "2026-04-06", "definido_por": "professor", "total_itens": 0}
    assert get(client, atleta, "2026-04-05").json()["vigente"]["vigente_desde"] == "2026-02-02"


def test_put_repetido_substitui_os_itens_e_nao_duplica_a_vigencia(client, atleta, session):
    put(client, atleta)
    r = put(client, atleta, por="professor", itens=[{"dia_semana": 5, "modalidade": "ciclismo", "tipo_treino": "leve"}])
    assert r.status_code == 200
    assert [i["dia_semana"] for i in r.json()["itens"]] == [5]
    assert session.scalar(select(func.count()).select_from(SemanaPadrao)) == 1
    assert session.scalar(select(func.count()).select_from(SemanaPadraoItem)) == 1  # os itens antigos sumiram
    assert get(client, atleta, "2026-03-02").json()["vigente"]["definido_por"] == "professor"


def test_put_idempotente(client, atleta):
    a, b = put(client, atleta).json(), put(client, atleta).json()
    assert a["itens"] == b["itens"] and b["atividades_reaplicadas"] == 0


def test_vigencia_no_futuro_e_aceita(client, atleta):
    assert put(client, atleta, desde="2999-01-01").status_code == 200
    assert get(client, atleta, "2026-03-10").json()["vigente"] is None


def test_em_padrao_e_hoje_em_sao_paulo(client, atleta, monkeypatch):
    put(client, atleta, desde="2026-03-02")
    put(client, atleta, desde="2026-03-09", itens=[])
    # 01:00 UTC de 2026-03-09 ainda e 2026-03-08 em Sao Paulo: vale a vigencia de 03-02
    class Relogio:
        @staticmethod
        def now(tz=None):
            return datetime(2026, 3, 9, 1, 0, tzinfo=timezone.utc).astimezone(tz)

    monkeypatch.setattr(sp, "datetime", Relogio)
    j = get(client, atleta).json()
    assert j["em"] == "2026-03-08" and j["vigente"]["vigente_desde"] == "2026-03-02"


def test_404_atleta_inexistente(client):
    assert get(client, 999).status_code == 404
    assert put(client, 999).status_code == 404


@pytest.mark.parametrize("mudanca", [
    {"itens": [{"dia_semana": 0, "modalidade": "corrida"}]},
    {"itens": [{"dia_semana": 8, "modalidade": "corrida"}]},
    {"itens": [{"dia_semana": 1, "modalidade": "outra"}]},
    {"itens": [{"dia_semana": 1, "modalidade": "remo"}]},
    {"itens": [{"dia_semana": 1, "modalidade": "corrida", "tipo_treino": "tiros"}]},
    {"itens": [{"dia_semana": 1, "modalidade": "corrida"}, {"dia_semana": 1, "modalidade": "corrida", "tipo_treino": "leve"}]},
    {"definido_por": "robo"},
    {"definido_por": None},
    {"vigente_desde": "2026-13-45"},
    {"vigente_desde": None},
])
def test_put_422_para_corpo_invalido(client, atleta, session, mudanca):
    c = {**corpo(), **mudanca}
    c = {k: v for k, v in c.items() if v is not None}
    assert client.put(f"/atletas/{atleta}/semana-padrao", json=c).status_code == 422
    assert session.scalar(select(func.count()).select_from(SemanaPadrao)) == 0


@pytest.mark.parametrize("faltando", ["definido_por", "vigente_desde", "itens"])
def test_put_422_com_campo_ausente(client, atleta, faltando):
    c = corpo()
    del c[faltando]
    assert client.put(f"/atletas/{atleta}/semana-padrao", json=c).status_code == 422


def test_get_422_para_em_invalido(client, atleta):
    assert get(client, atleta, "ontem").status_code == 422


def test_mesma_modalidade_em_dias_diferentes_e_modalidades_diferentes_no_mesmo_dia_valem(client, atleta):
    itens = [
        {"dia_semana": 6, "modalidade": "corrida", "tipo_treino": "longo"},
        {"dia_semana": 6, "modalidade": "ciclismo", "tipo_treino": "moderado"},
        {"dia_semana": 7, "modalidade": "corrida"},
    ]
    assert put(client, atleta, itens=itens).status_code == 200


def test_atletas_nao_se_misturam(client, atleta, session):
    outro = Atleta(nome="Bia")
    session.add(outro)
    session.commit()
    put(client, atleta)
    assert get(client, outro.id, "2026-03-10").json()["vigencias"] == []


def test_put_nao_toca_nas_atividades_enquanto_a_reaplicacao_e_da_265(client, atleta, session):
    session.add(Atividade(
        atleta_id=atleta, fonte="teste", fonte_id="1", modalidade="corrida", duracao_s=1800.0,
        inicio=datetime(2026, 3, 3, 10, tzinfo=timezone.utc), tipo_treino="leve", tipo_origem="sugestao"))
    session.commit()
    assert put(client, atleta, itens=[{"dia_semana": 2, "modalidade": "corrida", "tipo_treino": "fartlek"}]).json()[
        "atividades_reaplicadas"] == 0
    a = session.scalars(select(Atividade)).one()
    assert (a.tipo_treino, a.tipo_origem) == ("leve", "sugestao")


def test_reaplicacao_roda_na_transacao_do_put_e_o_numero_vai_na_resposta(client, atleta, monkeypatch):
    chamadas = []

    def falsa(session, atleta_id, vigente_desde):
        chamadas.append((atleta_id, vigente_desde))
        return 3

    monkeypatch.setattr(sp, "reaplicar_tipos", falsa)
    assert put(client, atleta).json()["atividades_reaplicadas"] == 3
    assert chamadas == [(atleta, date(2026, 3, 2))]


def test_se_a_reaplicacao_falha_a_vigencia_nao_fica_gravada(client, atleta, session, monkeypatch):
    put(client, atleta, desde="2026-02-02")

    def quebra(*a, **k):
        raise RuntimeError("falhou")

    monkeypatch.setattr(sp, "reaplicar_tipos", quebra)
    nova = client_sem_excecao(client)
    r = nova.put(f"/atletas/{atleta}/semana-padrao", json=corpo(desde="2026-03-02"))
    assert r.status_code == 500
    assert [v.vigente_desde for v in session.scalars(select(SemanaPadrao))] == [date(2026, 2, 2)]
    # e a edicao de uma vigencia existente tambem volta ao que era
    r = nova.put(f"/atletas/{atleta}/semana-padrao", json=corpo(desde="2026-02-02", itens=[]))
    assert r.status_code == 500
    assert session.scalar(select(func.count()).select_from(SemanaPadraoItem)) == 2


def client_sem_excecao(client):
    return TestClient(client.app, raise_server_exceptions=False)


def test_put_concorrente_da_mesma_vigencia_repete_como_atualizacao(atleta, session, monkeypatch):
    """O outro PUT ganhou a corrida: o INSERT viola o UNIQUE, o upsert busca a linha e atualiza."""
    primeira = sp._buscar
    estado = {"n": 0}

    def buscar(sess, atleta_id, desde):
        estado["n"] += 1
        if estado["n"] == 1:  # a leitura diz que nao existe...
            outro = SemanaPadrao(atleta_id=atleta_id, vigente_desde=desde, definido_por="professor")
            sess.add(outro)  # ...mas o PUT concorrente ja gravou
            sess.flush()
            outro.itens = [SemanaPadraoItem(dia_semana=3, modalidade="ciclismo", tipo_treino="leve")]
            sess.flush()
            return None
        return primeira(sess, atleta_id, desde)

    monkeypatch.setattr(sp, "_buscar", buscar)
    linha, n = sp.gravar_vigencia(
        session, atleta, date(2026, 3, 2), "atleta", [sp.ItemNovo(2, "corrida", "fartlek")])
    assert n == 0 and linha.definido_por == "atleta"
    assert [(i.dia_semana, i.modalidade) for i in linha.itens] == [(2, "corrida")]
    assert session.scalar(select(func.count()).select_from(SemanaPadrao)) == 1
    assert session.scalar(select(func.count()).select_from(SemanaPadraoItem)) == 1


def test_dois_put_de_verdade_ao_mesmo_tempo_no_postgres(engine, atleta):
    """Clique duplo: duas sessoes gravam a mesma vigencia juntas. Nenhuma pode falhar e fica uma vigencia so."""
    if engine.dialect.name != "postgresql":
        pytest.skip("concorrencia real so no Postgres (o SQLite em memoria tem conexao unica)")
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    from sqlalchemy.orm import Session

    largada = Barrier(2)

    def grava(dia):
        with Session(engine) as s:
            largada.wait()
            return sp.gravar_vigencia(s, atleta, date(2026, 3, 2), "atleta", [sp.ItemNovo(dia, "corrida", "leve")])[1]

    with ThreadPoolExecutor(2) as pool:
        assert list(pool.map(grava, [1, 2])) == [0, 0]
    with Session(engine) as s:
        assert s.scalar(select(func.count()).select_from(SemanaPadrao)) == 1
        assert s.scalar(select(func.count()).select_from(SemanaPadraoItem)) == 1  # a de quem terminou por ultimo
