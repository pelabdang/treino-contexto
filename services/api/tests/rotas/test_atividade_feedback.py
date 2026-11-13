"""`feedback` no GET da atividade (issue #328, ADR 0013 item 2): os cinco estados, a `mensagem` pronta e o que nunca sai.

O texto do feedback pronto e o G01 das fixtures da #323 (exemplo 1 da ADR). Tudo sintetico.
"""

import importlib.util
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest
from app.db.models import Atividade, Atleta, CheckinTreino, FeedbackTreino
from app.db.session import get_session
from app.main import criar_app
from app.servicos import checkin as svc
from app.servicos import feedback_leitura as fl
from fastapi.testclient import TestClient

PASTA = Path(__file__).parents[4] / "tests" / "fixtures" / "meta9"
_spec = importlib.util.spec_from_file_location("textos_meta9_api", PASTA / "textos.py")
T = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = T
_spec.loader.exec_module(T)
TEXTO = T.BONS["G01"][1]

HOJE = date(2026, 11, 10)
AGORA = datetime(2026, 11, 10, 12, 0, tzinfo=timezone.utc)
V = "fatos_treino@2"
FRASES = {
    "sem_checkin": "Faça o check-in para ver o feedback.",
    "prazo": "O prazo do check-in deste treino acabou, então ele fica sem feedback.",
    "pendente": "O feedback deste treino ainda não foi gerado. Toque em Atualizar para ver se já está pronto.",
    "desatualizado": "Você editou o check-in. O feedback será refeito.",
    "indisponivel": "Ainda não foi possível gerar o feedback deste treino. Uma nova tentativa será feita mais tarde.",
    "sem_provedor": "O feedback automático não está ligado neste app.",
}


@pytest.fixture(autouse=True)
def relogio(monkeypatch):
    monkeypatch.setattr(svc, "hoje_local", lambda: HOJE)


@pytest.fixture
def client(session):
    app = criar_app("http://localhost:8081")
    app.dependency_overrides[get_session] = lambda: session
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def atleta(session):
    a = Atleta(nome="Ana")
    session.add(a)
    session.commit()
    return a


def _atividade(session, atleta, dias_atras=1, subtipo=None, fid="1"):
    a = Atividade(atleta_id=atleta.id, fonte="t", fonte_id=fid, modalidade="corrida", subtipo=subtipo, fuso_min=0,
                  inicio=AGORA - timedelta(days=dias_atras), duracao_s=1800.0, distancia_m=5000.0)
    session.add(a)
    session.commit()
    return a


def _checkin(session, a, em=AGORA):
    c = CheckinTreino(atividade_id=a.id, pse=4, sensacao=4, nada_a_relatar=True, versao="checkin@1", registrado_em=em,
                      atualizado_em=em)
    session.add(c)
    session.commit()
    return c


def _feedback(session, c, **kw):
    campos = dict(checkin_id=c.id, estado="pronto", motivo=None, texto=TEXTO, versao_fatos=V, versao_prompt="feedback_prompt@1",
                  versao_checagens="checagens_feedback@1", provedor="groq", modelo="modelo-x", tentativas=1,
                  checkin_atualizado_em=c.atualizado_em, tentado_em=AGORA)
    campos.update(kw)
    session.add(FeedbackTreino(**campos))
    session.commit()


def _get(client, atleta, a):
    r = client.get(f"/atletas/{atleta.id}/atividades/{a.id}")
    assert r.status_code == 200
    return r.json()


def test_sem_checkin_com_prazo_aberto(session, client, atleta):
    j = _get(client, atleta, _atividade(session, atleta))
    assert j["feedback"] == {"estado": "sem_checkin", "texto": None, "origem": None, "mensagem": FRASES["sem_checkin"],
                             "checkin_aberto": True, "motivo": None}


def test_sem_checkin_com_prazo_vencido_tem_frase_propria_e_sem_botao(session, client, atleta):
    j = _get(client, atleta, _atividade(session, atleta, dias_atras=30))
    assert j["feedback"]["estado"] == "sem_checkin" and j["feedback"]["checkin_aberto"] is False
    assert j["feedback"]["mensagem"] == FRASES["prazo"] and j["checkin_aberto"] is False


def test_pendente_com_checkin_e_sem_linha(session, client, atleta):
    a = _atividade(session, atleta)
    _checkin(session, a)
    f = _get(client, atleta, a)["feedback"]
    assert f["estado"] == "pendente" and f["mensagem"] == FRASES["pendente"] and f["texto"] is None


def test_pronto_automatico(session, client, atleta):
    a = _atividade(session, atleta)
    _feedback(session, _checkin(session, a))
    f = _get(client, atleta, a)["feedback"]
    assert (f["estado"], f["texto"], f["origem"], f["mensagem"]) == ("pronto", TEXTO, "automatico", None)
    assert 3 <= len(f["texto"].splitlines()) <= 5


def test_pronto_do_provedor_falso_e_origem_teste(session, client, atleta):
    a = _atividade(session, atleta)
    _feedback(session, _checkin(session, a), provedor="falso", modelo="falso")
    f = _get(client, atleta, a)["feedback"]
    assert f["estado"] == "pronto" and f["origem"] == "teste"


def test_check_in_editado_deixa_desatualizado_e_nao_devolve_o_texto_antigo(session, client, atleta):
    a = _atividade(session, atleta)
    c = _checkin(session, a)
    _feedback(session, c)
    c.atualizado_em = AGORA + timedelta(minutes=5)  # ate um PUT identico muda `atualizado_em`
    session.commit()
    j = _get(client, atleta, a)
    assert j["feedback"]["estado"] == "desatualizado" and j["feedback"]["mensagem"] == FRASES["desatualizado"]
    assert j["feedback"]["texto"] is None and TEXTO not in str(j)


def test_versao_nova_dos_fatos_deixa_desatualizado(session, client, atleta):
    a = _atividade(session, atleta)
    _feedback(session, _checkin(session, a))
    f = fl.feedback_da_atividade(a, a.checkin, True, versao_fatos="fatos_treino@3")
    assert f.estado == "desatualizado" and f.texto is None


@pytest.mark.parametrize("motivo,frase", [
    ("texto_reprovado", "indisponivel"), ("provedor_erro", "indisponivel"), ("provedor_tempo_limite", "indisponivel"),
    ("limite_de_chamadas", "indisponivel"), ("provedor_nao_configurado", "sem_provedor"),
])
def test_indisponivel_por_qualquer_motivo(session, client, atleta, motivo, frase):
    a = _atividade(session, atleta)
    _feedback(session, _checkin(session, a), estado="sem_feedback", motivo=motivo, texto=None, provedor=None, modelo=None)
    f = _get(client, atleta, a)["feedback"]
    assert (f["estado"], f["mensagem"], f["motivo"], f["texto"]) == ("indisponivel", FRASES[frase], motivo, None)


@pytest.mark.parametrize("subtipo", ["multiesporte_pai", "troca"])
def test_nao_elegivel_tem_feedback_nulo(session, client, atleta, subtipo):
    assert _get(client, atleta, _atividade(session, atleta, subtipo=subtipo))["feedback"] is None


def test_a_api_nao_devolve_provedor_modelo_nem_versoes(session, client, atleta):
    a = _atividade(session, atleta)
    _feedback(session, _checkin(session, a), modelo="modelo-secreto-x")
    corpo = client.get(f"/atletas/{atleta.id}/atividades/{a.id}").text
    for nome in ("modelo-secreto-x", "groq", "versao_fatos", "versao_prompt", "versao_checagens", "tentativas", "checkin_atualizado_em"):
        assert nome not in corpo


def test_feedback_de_outro_atleta_da_404(session, client, atleta):
    a = _atividade(session, atleta)
    _feedback(session, _checkin(session, a))
    outro = Atleta(nome="Beto")
    session.add(outro)
    session.commit()
    assert client.get(f"/atletas/{outro.id}/atividades/{a.id}").status_code == 404


def test_nao_ha_feedback_nas_listas(session, client, atleta):
    a = _atividade(session, atleta)
    _feedback(session, _checkin(session, a))
    for url in (f"/atletas/{atleta.id}/checkins/pendentes", f"/atletas/{atleta.id}/treinos-de-transicao"):
        assert TEXTO not in client.get(url).text
