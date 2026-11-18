"""O "hoje" da caixa do dia e o prazo do check-in sao da data LOCAL (America/Sao_Paulo), nao UTC (#458). Dados sinteticos.

A virada do dia UTC acontece as 21h locais; a do dia local, a meia-noite local. Horario fixo (a dependencia `agora_utc`)."""

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.servicos.consentimento import TERMO_VIGENTE
from app.db.models import Assessoria, Atividade, Atleta, Professor, VinculoProfessorAtleta
from app.db.session import get_session
from app.main import criar_app
from tests.acesso_de_teste import sem_login
from app.servicos import professor as svc_prof
from app.servicos.feedback_leitura import MSG_PRAZO_VENCIDO, MSG_SEM_CHECKIN

URL = "/professores/1/caixa-do-dia"
UTC = timezone.utc


def _utc(dia, hora, minuto=0):
    return datetime(2026, 11, dia, hora, minuto, tzinfo=UTC)


@pytest.fixture
def app(session, monkeypatch):
    monkeypatch.setattr(settings, "professor_id", 1)
    session.add(Assessoria(id=1, nome="Assessoria Teste"))
    session.add(Professor(id=1, assessoria_id=1, nome="Professor Um"))
    session.add(Atleta(id=1, assessoria_id=1, nome="Ana Teste"))
    session.flush()
    session.add(VinculoProfessorAtleta(professor_id=1, atleta_id=1, consentimento_em=_utc(1, 12), termo_versao=TERMO_VIGENTE))
    # sexta 13/11 (10h locais), sem check-in e sem tipo: no dia 18 faltam 2 dias para o fim do prazo
    session.add(Atividade(id=1, atleta_id=1, fonte="t", fonte_id="1", modalidade="corrida", inicio=_utc(13, 13), fuso_min=-180, duracao_s=2700))
    # quarta 11/11, sem check-in, com tipo sugerido (entra em "novos"): no dia 18 o prazo termina hoje; no dia 19 venceu
    session.add(Atividade(id=2, atleta_id=1, fonte="t", fonte_id="2", modalidade="corrida", inicio=_utc(11, 13), fuso_min=-180, duracao_s=2700,
                          tipo_treino="leve", tipo_origem="sugestao", tipo_versao="tipo_treino@1"))
    session.commit()
    a = sem_login(criar_app("http://localhost:8081"))
    a.dependency_overrides[get_session] = lambda: session
    return a


def _get(app, agora):
    app.dependency_overrides[svc_prof.agora_utc] = lambda: agora
    r = TestClient(app, raise_server_exceptions=False).get(URL)
    assert r.status_code == 200
    return r.json()


def _motivo(j, atividade_id):
    treinos = [t for a in j["alunos"] for t in a["treinos"] if t["atividade_id"] == atividade_id]
    return [m["texto"] for t in treinos for m in t["motivos"]]


# atencao@2 junta os treinos sem check-in da janela do aviso num motivo so, no mais antigo (o de quarta, atividade 2).
# (instante UTC, hoje local esperado, motivo na atividade de sexta (1), motivo na atividade de quarta (2))
JUNTO = "2 treinos sem check-in; o prazo do mais antigo termina hoje."
CASOS = {
    "20h locais, antes da virada UTC": (_utc(18, 23), "2026-11-18", [], [JUNTO]),
    "23h locais, depois da virada UTC e antes da local": (_utc(19, 2), "2026-11-18", [], [JUNTO]),
    # o treino de quarta ja venceu (8 dias): so o de sexta avisa, e faltam 1 dia (e nao 2: a data e a local)
    "01h locais, depois das duas viradas": (_utc(19, 4), "2026-11-19", ["Treino de sexta sem check-in; o prazo termina em 1 dia."], []),
}


@pytest.mark.parametrize("nome", list(CASOS))
def test_hoje_e_prazo_do_checkin_seguem_a_data_local(app, nome):
    agora, hoje, sexta, quarta = CASOS[nome]
    j = _get(app, agora)
    assert j["hoje"] == hoje
    assert _motivo(j, 1) == sexta
    assert _motivo(j, 2) == quarta


def test_mensagem_de_prazo_do_feedback_usa_a_mesma_data_local(app):
    def mensagem(agora):
        novos = {n["atividade_id"]: n for n in _get(app, agora)["novos"]}
        return novos[2]["detalhe"]["feedback"]["mensagem"]

    assert mensagem(_utc(19, 2)) == MSG_SEM_CHECKIN  # 23h do dia 18: o treino de 11/11 ainda esta no 7o dia
    assert mensagem(_utc(19, 4)) == MSG_PRAZO_VENCIDO  # 01h do dia 19: venceu


@pytest.mark.parametrize("agora,texto", [
    (_utc(18, 23), "Treino de sexta sem check-in; o prazo termina em 2 dias."),  # 20h locais
    (_utc(19, 2), "Treino de sexta sem check-in; o prazo termina em 2 dias."),  # 23h locais: o dia UTC ja virou, o local nao
    (_utc(19, 4), "Treino de sexta sem check-in; o prazo termina em 1 dia."),  # 01h locais
])
def test_um_treino_so_sem_checkin_texto_exato_antes_e_depois_da_virada(app, session, agora, texto):
    session.delete(session.get(Atividade, 2))
    session.commit()
    assert _motivo(_get(app, agora), 1) == [texto]
