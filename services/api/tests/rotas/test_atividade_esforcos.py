"""`esforcos` em GET /atletas/{id}/atividades/{id} (issue #167, ADR 0008). Só as fixtures sintéticas da #161."""

import importlib.util
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest
from app.db.models import Atividade, Atleta
from app.db.session import get_session
from app.ingestao.garmin import ler_atividade_fit
from app.ingestao.importacao import duracao_da, gravar_atividade
from app.main import criar_app
from app.metricas import esforcos as ef
from app.metricas.tiros_1km import formatar_pace
from app.servicos.esforcos import detectar_esforcos
from fastapi.testclient import TestClient

RAIZ = Path(__file__).parents[4]
PASTA_FIT = RAIZ / "tests" / "fixtures" / "garmin" / "esforcos"
ORACULO = Path(__file__).parents[1] / "metricas" / "test_esforcos_oraculo.py"
URL = "/atletas/{}/atividades/{}"


@pytest.fixture(scope="module")
def oraculo():
    spec = importlib.util.spec_from_file_location("test_esforcos_oraculo", ORACULO)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def client(session):
    app = criar_app("http://localhost:8081")
    app.dependency_overrides[get_session] = lambda: session
    return TestClient(app)


@pytest.fixture
def atleta(session):
    a = Atleta(nome="Atleta Ficticio")
    session.add(a)
    session.commit()
    return a


def _historico(session, atleta, modalidade, ref):
    if modalidade == "corrida":
        dist, dur = 5000.0, 5000.0 * ref / 1000
    else:
        dur = 3600.0
        dist = ref * dur / 3.6
    session.add(Atividade(
        atleta_id=atleta.id, fonte="teste", fonte_id=f"hist-{modalidade}", modalidade=modalidade,
        inicio=datetime(2020, 1, 1, 8, tzinfo=timezone.utc), duracao_s=dur, distancia_m=dist,
    ))
    session.commit()


def _fit(session, atleta, nome):
    a = ler_atividade_fit((PASTA_FIT / nome).read_bytes(), fonte="fit_upload")
    _, ativ, _ = gravar_atividade(session, atleta.id, a, duracao_da(a), [])
    session.commit()
    return ativ


def _carregar(session, atleta, oraculo, nome, com_historico=True):
    modalidade, ref, _ = oraculo.ESPERADO[nome]
    if com_historico:
        _historico(session, atleta, modalidade, ref)
    ativ = _fit(session, atleta, nome)
    detectar_esforcos(session, atleta.id)
    return ativ


def _m_ss(s):
    return formatar_pace(s)


@pytest.mark.parametrize("nome", [
    "esforcos_corrida_400_com_pausa.fit", "esforcos_corrida_1500_lap_automatico.fit",
    "esforcos_corrida_continuo_forte.fit", "esforcos_corrida_rodagem_leve.fit", "esforcos_corrida_misto.fit",
    "esforcos_ciclismo_blocos_4min.fit", "esforcos_ciclismo_lap_automatico.fit",
])
def test_resposta_bate_com_o_oraculo(client, session, atleta, oraculo, nome):
    modalidade, _ref, esperado = oraculo.ESPERADO[nome]
    ativ = _carregar(session, atleta, oraculo, nome)
    r = client.get(URL.format(atleta.id, ativ.id))
    assert r.status_code == 200
    e = r.json()["esforcos"]
    assert e["versao"] == ef.VERSAO
    assert e["referencia_da_atividade"] is False
    assert e["treino_chave"] == any(x.treino_chave for x in esperado)
    assert [b["ordem"] for b in e["blocos"]] == list(range(len(esperado)))
    for b, x in zip(e["blocos"], esperado):
        assert (b["categoria"], b["faixa"], b["treino_chave"]) == (x.categoria, x.faixa, x.treino_chave)
        assert b["distancia_m"] == pytest.approx(x.distancia_m, abs=0.1)
        assert b["duracao_s"] == pytest.approx(x.duracao_s, abs=0.1)
        assert b["duracao"] == _m_ss(x.duracao_s)
        if x.fc_media is None:
            assert b["fc_media"] is None
        else:
            assert b["fc_media"] == pytest.approx(x.fc_media, abs=0.1)
        if modalidade == "corrida":
            assert b["pace_s_km"] == pytest.approx(x.intensidade, abs=0.1)
            assert b["pace"] == _m_ss(x.intensidade)
            assert "velocidade" not in b and "velocidade_kmh" not in b
        else:
            assert b["velocidade_kmh"] == pytest.approx(x.intensidade, abs=0.1)
            assert b["velocidade"] == f"{x.intensidade:.1f}".replace(".", ",") + " km/h"
            assert "pace" not in b and "pace_s_km" not in b


def test_textos_prontos_de_um_bloco(client, session, atleta, oraculo):
    ativ = _carregar(session, atleta, oraculo, "esforcos_corrida_400_com_pausa.fit")
    blocos = client.get(URL.format(atleta.id, ativ.id)).json()["esforcos"]["blocos"]
    quatrocentos = next(b for b in blocos if b["faixa"] == "d400")
    assert quatrocentos["faixa_rotulo"] == "400 m"
    assert quatrocentos["distancia"].endswith(" m")
    assert ":" in quatrocentos["pace"]
    assert blocos[-1]["parada_apos"] is None  # o ultimo bloco nao tem parada depois


def test_sem_historico_avisa_que_a_referencia_e_da_atividade(client, session, atleta, oraculo):
    ativ = _carregar(session, atleta, oraculo, "esforcos_corrida_misto.fit", com_historico=False)
    e = client.get(URL.format(atleta.id, ativ.id)).json()["esforcos"]
    assert e["referencia_da_atividade"] is True and e["blocos"]


def test_ciclismo_sem_historico_tambem_avisa(client, session, atleta, oraculo):
    ativ = _carregar(session, atleta, oraculo, "esforcos_ciclismo_blocos_4min.fit", com_historico=False)
    assert client.get(URL.format(atleta.id, ativ.id)).json()["esforcos"]["referencia_da_atividade"] is True


def test_atividade_sem_esforcos_detectados_da_lista_vazia_com_a_versao(client, session, atleta):
    a = Atividade(
        atleta_id=atleta.id, fonte="teste", fonte_id="1", modalidade="corrida",
        inicio=datetime(2025, 3, 4, 9, tzinfo=timezone.utc), duracao_s=1800.0, distancia_m=5000.0,
    )
    session.add(a)
    session.commit()
    detectar_esforcos(session, atleta.id)
    assert client.get(URL.format(atleta.id, a.id)).json()["esforcos"] == {
        "versao": ef.VERSAO, "referencia_da_atividade": False, "treino_chave": False, "blocos": [],
    }


def test_natacao_nao_tem_esforcos(client, session, atleta):
    a = Atividade(
        atleta_id=atleta.id, fonte="teste", fonte_id="n", modalidade="natacao",
        inicio=datetime(2025, 3, 4, 9, tzinfo=timezone.utc), duracao_s=1800.0, distancia_m=1000.0,
    )
    session.add(a)
    session.commit()
    assert client.get(URL.format(atleta.id, a.id)).json()["esforcos"] is None


def test_404_continua_declarado(client, session, atleta):
    assert client.get(URL.format(999, 1)).status_code == 404
    assert client.get(URL.format(atleta.id, 999)).status_code == 404
    resp = criar_app("http://localhost:8081").openapi()["paths"]["/atletas/{atleta_id}/atividades/{atividade_id}"]["get"]
    assert "404" in resp["responses"]


def test_a_leitura_nao_detecta(client, session, atleta, oraculo):
    """Sem rodar `detectar_esforcos` a resposta vem vazia: a API só lê o que foi gravado."""
    modalidade, ref, _ = oraculo.ESPERADO["esforcos_corrida_misto.fit"]
    _historico(session, atleta, modalidade, ref)
    ativ = _fit(session, atleta, "esforcos_corrida_misto.fit")
    from app.db.models import BlocoAtividade
    session.query(BlocoAtividade).delete()
    session.commit()
    assert client.get(URL.format(atleta.id, ativ.id)).json()["esforcos"]["blocos"] == []


def test_openapi_descreve_esforcos():
    schemas = criar_app("http://localhost:8081").openapi()["components"]["schemas"]
    assert {"EsforcosOut", "BlocoOut"} <= set(schemas)
    assert "esforcos" in schemas["AtividadeOut"]["properties"]
    assert "esforcos" not in schemas["AtividadeOut"].get("required", [])
