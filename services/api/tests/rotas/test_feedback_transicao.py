"""Corrigir o rotulo de transicao deixa o feedback ja gerado `desatualizado` (issue #510, pergunta C da Meta 12). Dado sintetico.

Nao ha escrita no feedback: o `PUT`/`DELETE` da transicao so muda o rotulo; o `GET` compara o que o pacote viu (`transicao_visto`) com o rotulo
de hoje, pelo mesmo caminho do tipo e do clima. O `worker.gerar_feedback` refaz como hoje (teste em `services/worker/tests/test_gerar_feedback.py`).
"""

from datetime import datetime, timedelta, timezone

import pytest
from app.db.models import Atividade, Atleta, CheckinTreino, FeedbackTreino
from app.db.session import get_session
from app.main import criar_app
from app.servicos.feedback_leitura import MSG_DESATUALIZADO, MSG_DESATUALIZADO_TRANSICAO
from app.servicos.transicao import aplicar_sugestao
from fastapi.testclient import TestClient
from tests.acesso_de_teste import sem_login

AGORA = datetime.now(timezone.utc) - timedelta(days=1)  # dentro de qualquer janela de leitura


@pytest.fixture
def client(session):
    app = sem_login(criar_app("http://localhost:8081"))
    app.dependency_overrides[get_session] = lambda: session
    return TestClient(app)


@pytest.fixture
def brick(session):
    """Um atleta com um brick (ciclismo + corrida, a regra sugere "sim" nos dois) e uma corrida avulsa sem check-in."""
    at = Atleta(nome="Atleta Ficticio")
    session.add(at)
    session.flush()

    def ativ(n, mod, ini, dur, dist):
        a = Atividade(atleta_id=at.id, fonte="t", fonte_id=str(n), modalidade=mod, inicio=ini, duracao_s=dur, distancia_m=dist, fuso_min=-180)
        session.add(a)
        session.flush()
        return a

    a1 = ativ(1, "ciclismo", AGORA, 3600, 30000)
    a2 = ativ(2, "corrida", AGORA + timedelta(seconds=3720), 1500, 5000)
    avulsa = ativ(3, "corrida", AGORA - timedelta(days=3), 1800, 5000)
    session.commit()
    aplicar_sugestao(session, at.id)
    return at, a1, a2, avulsa


def _feedback(session, atividade, transicao_visto):
    ck = CheckinTreino(atividade_id=atividade.id, pse=5, sensacao=3, nada_a_relatar=True, dor=False, cansaco=False, sono_ruim=False,
                       calor=False, trabalho_estresse=False, versao="checkin@1", registrado_em=AGORA, atualizado_em=AGORA)
    session.add(ck)
    session.flush()
    session.add(FeedbackTreino(checkin_id=ck.id, estado="pronto", texto="tres linhas", versao_fatos="fatos_treino@2", versao_prompt="p",
                               versao_checagens="c", provedor="falso", modelo="falso", tentativas=1, checkin_atualizado_em=AGORA,
                               transicao_visto=transicao_visto, tentado_em=AGORA))
    session.commit()


def _estado(client, at, a):
    j = client.get(f"/atletas/{at.id}/atividades/{a.id}").json()["feedback"]
    return j["estado"], j.get("mensagem")


def test_corrigir_e_desfazer_marca_o_feedback_desatualizado_e_depois_em_dia(client, session, brick):
    at, a1, a2, _ = brick
    _feedback(session, a1, transicao_visto=True)  # o pacote viu "parte de transicao"
    _feedback(session, a2, transicao_visto=True)
    assert _estado(client, at, a1)[0] == "pronto"
    client.put(f"/atletas/{at.id}/atividades/{a1.id}/transicao", json={"transicao": False})
    estado, msg = _estado(client, at, a1)
    assert estado == "desatualizado" and msg == MSG_DESATUALIZADO_TRANSICAO
    assert "check-in" not in msg and msg != MSG_DESATUALIZADO  # nao diz "Voce editou o check-in"
    assert _estado(client, at, a2)[0] == "pronto"  # o pacote da outra parte so le o proprio rotulo
    client.delete(f"/atletas/{at.id}/atividades/{a1.id}/transicao")  # desfaz: a regra volta a sugerir "sim"
    assert _estado(client, at, a1)[0] == "pronto"


def test_confirmar_o_mesmo_valor_nao_desatualiza(client, session, brick):
    at, a1, *_ = brick
    _feedback(session, a1, transicao_visto=True)
    client.put(f"/atletas/{at.id}/atividades/{a1.id}/transicao", json={"transicao": True})
    assert _estado(client, at, a1)[0] == "pronto"


def test_treino_sem_feedback_nao_muda(client, session, brick):
    at, a1, a2, avulsa = brick
    antes = [_estado(client, at, a)[0] for a in (a1, avulsa)]
    client.put(f"/atletas/{at.id}/atividades/{a1.id}/transicao", json={"transicao": False})
    client.put(f"/atletas/{at.id}/atividades/{avulsa.id}/transicao", json={"transicao": True})
    assert [_estado(client, at, a)[0] for a in (a1, avulsa)] == antes == ["sem_checkin", "sem_checkin"]
    assert session.query(FeedbackTreino).count() == 0


def test_linha_anterior_a_migracao_nao_compara(client, session, brick):
    at, a1, *_ = brick
    _feedback(session, a1, transicao_visto=None)
    client.put(f"/atletas/{at.id}/atividades/{a1.id}/transicao", json={"transicao": False})
    assert _estado(client, at, a1)[0] == "pronto"


def test_marcar_sim_numa_corrida_avulsa_desatualiza(client, session, brick):
    at, _, _, avulsa = brick
    _feedback(session, avulsa, transicao_visto=False)
    assert _estado(client, at, avulsa)[0] == "pronto"
    client.put(f"/atletas/{at.id}/atividades/{avulsa.id}/transicao", json={"transicao": True})
    assert _estado(client, at, avulsa) == ("desatualizado", MSG_DESATUALIZADO_TRANSICAO)
