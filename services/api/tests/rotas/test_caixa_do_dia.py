"""`GET /professores/{professor_id}/caixa-do-dia` (#424, ADR 0015). Atletas, professores e textos FICTICIOS."""

from __future__ import annotations

import json
import logging
from datetime import date, datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.db.models import Assessoria, Atividade, Atleta, CheckinTreino, Professor, VinculoProfessorAtleta
from app.db.session import get_session
from app.main import criar_app
from app.servicos import professor as svc_prof

HOJE = date(2026, 11, 18)  # quarta-feira
AGORA = datetime(2026, 11, 18, 15, 0, tzinfo=timezone.utc)
PROF, OUTRO = 1, 2
URL = f"/professores/{PROF}/caixa-do-dia"
OBS = "OBSERVACAO-SINTETICA-NAO-VAZAR"


def _quando(dias_atras: int, hora: int = 10) -> datetime:
    d = HOJE - timedelta(days=dias_atras)
    return datetime(d.year, d.month, d.day, hora, tzinfo=timezone.utc)


def _ativ(session, id_, atleta, dias_atras, *, tipo="leve", origem="professor", confirmado=True, divergencia=None, fc=None, **kw):
    session.add(Atividade(id=id_, atleta_id=atleta, fonte="t", fonte_id=str(id_), modalidade=kw.pop("modalidade", "corrida"),
                          inicio=_quando(dias_atras), fuso_min=0, duracao_s=kw.pop("duracao_s", 2700), tipo_treino=tipo, tipo_origem=origem,
                          tipo_versao="tipo_treino@1" if origem in ("sugestao", "semana_padrao") else None, tipo_confirmado=confirmado,
                          tipo_divergencia=divergencia, fc_media=fc, **kw))
    session.flush()


def _checkin(session, atividade, *, dor=False, texto=None, pse=7):
    session.add(CheckinTreino(
        atividade_id=atividade, pse=pse, sensacao=3, nada_a_relatar=not dor and texto is None, dor=dor, cansaco=False, sono_ruim=False,
        calor=False, trabalho_estresse=False, texto=texto, versao="checkin@1", registrado_em=AGORA, atualizado_em=AGORA))


@pytest.fixture
def mundo(session):
    session.add(Assessoria(id=1, nome="Assessoria Teste"))
    session.add_all([Professor(id=PROF, assessoria_id=1, nome="Professor Um"), Professor(id=OUTRO, assessoria_id=1, nome="Professor Dois")])
    session.flush()
    nomes = {1: "Ana Teste", 2: "Bruno Teste", 3: "Carla Teste", 4: "Davi Teste", 5: "Eva Sem Consentimento", 6: "Fabio De Outro",
             7: "Gil Sem Vinculo", 8: "Hugo Consentimento Futuro"}
    for i, n in nomes.items():
        session.add(Atleta(id=i, assessoria_id=1, nome=n))
    session.flush()
    ok = AGORA - timedelta(days=30)
    for i, cons in {1: ok, 2: ok, 3: ok, 4: ok, 5: None, 8: AGORA + timedelta(days=1)}.items():
        session.add(VinculoProfessorAtleta(professor_id=PROF, atleta_id=i, consentimento_em=cons))
    session.add(VinculoProfessorAtleta(professor_id=OUTRO, atleta_id=6, consentimento_em=ok))
    # Ana: dor (ha 2 dias), com observacao; confirmada (nao e novo)
    _ativ(session, 10, 1, 2)
    _checkin(session, 10, dor=True, texto=OBS)
    # Bruno: divergencia da semana-padrao (ha 3 dias), nao confirmada (tambem aparece em "novos")
    _ativ(session, 20, 2, 3, tipo="longo", origem="semana_padrao", confirmado=False, divergencia="tem_tiros")
    _checkin(session, 20)
    # Carla: sem check-in ha 5 dias (prazo termina em 2 dias); sem tipo
    _ativ(session, 30, 3, 5, tipo=None, origem=None, confirmado=False)
    # Davi: nada a destacar (treino de 10 dias, fora da janela da atencao; com tipo sugerido: so em "novos")
    _ativ(session, 40, 4, 10, tipo="moderado", origem="sugestao", confirmado=False)
    _checkin(session, 40)
    # quem nunca pode aparecer: todos com dor marcada e tipo sugerido
    for atleta, atividade in ((5, 50), (6, 60), (7, 70), (8, 80)):
        _ativ(session, atividade, atleta, 1, tipo="intervalado", origem="sugestao", confirmado=False)
        _checkin(session, atividade, dor=True, texto=OBS)
    session.commit()
    return {"consentido": 1, "consentimento_nulo": 5, "so_de_outro_professor": 6, "sem_vinculo": 7, "consentimento_no_futuro": 8}


@pytest.fixture
def client(session, mundo, monkeypatch):
    monkeypatch.setattr(settings, "professor_id", PROF)
    app = criar_app("http://localhost:8081")
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[svc_prof.agora_utc] = lambda: AGORA
    return TestClient(app, raise_server_exceptions=False)


def _caixa(client):
    r = client.get(URL)
    assert r.status_code == 200, r.text
    return r.json()


def test_forma_da_resposta_e_ordem_dos_alunos(client):
    j = _caixa(client)
    assert (j["versao"], j["hoje"], j["janela_atencao_dias"], j["janela_novos_dias"]) == ("atencao@2", "2026-11-18", 7, 14)
    assert [a["nome"] for a in j["alunos"]] == ["Ana Teste", "Bruno Teste", "Carla Teste", "Davi Teste"]  # dor, divergencia, checkin; depois sem motivo
    ana, bruno, carla, davi = j["alunos"]
    assert [m["codigo"] for m in ana["treinos"][0]["motivos"]] == ["dor"]
    assert ana["treinos"][0]["motivos"][0]["texto"] == "Treino de segunda com dor marcada no check-in."
    assert bruno["treinos"][0]["motivos"][0]["codigo"] == "divergencia"
    assert carla["treinos"][0]["motivos"] == [{"codigo": "checkin_vencendo", "texto": "Treino de sexta sem check-in; o prazo termina em 2 dias."}]
    assert (davi["sem_motivo"], davi["texto_sem_motivo"], davi["treinos"]) == (True, "Nada a destacar nos últimos 7 dias.", [])
    assert not ana["sem_motivo"] and ana["texto_sem_motivo"] is None
    t = ana["treinos"][0]
    assert (t["atividade_id"], t["modalidade"], t["data_local"], t["hora_local"], t["duracao_texto"]) == (10, "corrida", "2026-11-16", "10:00", "45 min")


def test_novos_mais_recente_primeiro_com_nome_tipo_e_origem(client):
    novos = _caixa(client)["novos"]
    assert [(n["atividade_id"], n["atleta_nome"]) for n in novos] == [(20, "Bruno Teste"), (40, "Davi Teste")]
    n = novos[0]
    assert (n["atleta_id"], n["tipo_sugerido"], n["tipo_sugerido_texto"], n["origem_texto"]) == (2, "longo", "Longo", "sugerido pela semana-padrão")
    assert novos[1]["origem_texto"] == "sugerido pela regra"
    assert novos[1]["detalhe"]["tipo_confirmado"] is False


def test_detalhe_traz_tipo_checkin_e_feedback(client):
    t = _caixa(client)["alunos"][0]["treinos"][0]["detalhe"]
    assert (t["tipo_texto"], t["tipo_origem_texto"], t["tipo_confirmado"]) == ("Leve", "definido pelo professor", True)
    c = t["checkin"]
    assert c["pse_texto"] and c["sensacao"] == 3 and c["observacao"] == OBS and [x["chave"] for x in c["atalhos"]] == ["dor"]
    assert t["feedback"]["estado"] == "pendente"
    carla = _caixa(client)["alunos"][2]["treinos"][0]["detalhe"]
    assert carla["checkin"] is None and carla["tipo_texto"] is None


def test_observacao_so_aparece_em_detalhe_checkin_observacao(client):
    j = _caixa(client)

    def achados(o, caminho=""):
        if isinstance(o, dict):
            for k, v in o.items():
                yield from achados(v, f"{caminho}/{k}")
        elif isinstance(o, list):
            for i, v in enumerate(o):
                yield from achados(v, f"{caminho}/{i}")
        elif isinstance(o, str) and OBS in o:
            yield caminho

    caminhos = list(achados(j))
    assert caminhos and all(c.endswith("/detalhe/checkin/observacao") for c in caminhos)
    # nenhum motivo (nem texto de motivo) leva a observacao
    assert all(OBS not in m["texto"] for a in j["alunos"] for t in a["treinos"] for m in t["motivos"])


def test_nao_guarda_em_cache_e_log_sem_dado_de_saude(client, caplog):
    caplog.set_level(logging.DEBUG)
    r = client.get(URL)
    assert r.headers["cache-control"] == "no-store"
    texto = " ".join(x.getMessage() for x in caplog.records if x.name.startswith("app"))
    assert OBS not in texto and "Ana" not in texto and "dor" not in texto.lower()
    assert "professor=1" in texto


@pytest.mark.parametrize("situacao", ["consentimento_nulo", "so_de_outro_professor", "sem_vinculo", "consentimento_no_futuro"])
def test_matriz_get_atleta_fora_do_filtro_nunca_aparece(client, mundo, situacao):
    r = client.get(URL)
    corpo = r.text
    atleta = mundo[situacao]
    j = r.json()
    assert atleta not in [a["atleta_id"] for a in j["alunos"]]
    assert atleta not in [n["atleta_id"] for n in j["novos"]]
    ids_atividade = {t["atividade_id"] for a in j["alunos"] for t in a["treinos"]} | {n["atividade_id"] for n in j["novos"]}
    assert atleta * 10 not in ids_atividade
    for nome in ("Sem Consentimento", "De Outro", "Sem Vinculo", "Consentimento Futuro"):
        assert nome not in corpo
    assert OBS in corpo  # so o da Ana, que consentiu


def test_matriz_get_consentido_aparece(client, mundo):
    assert mundo["consentido"] in [a["atleta_id"] for a in _caixa(client)["alunos"]]


def test_consentimento_retirado_some_na_leitura_seguinte(client, session):
    assert "Ana Teste" in [a["nome"] for a in _caixa(client)["alunos"]]
    session.get(VinculoProfessorAtleta, (PROF, 1)).consentimento_em = None
    session.commit()
    j = _caixa(client)
    assert "Ana Teste" not in [a["nome"] for a in j["alunos"]] and OBS not in client.get(URL).text


def test_consentimento_no_futuro_entra_quando_chega_a_hora(client, session):
    session.get(VinculoProfessorAtleta, (PROF, 8)).consentimento_em = AGORA
    session.commit()
    assert "Hugo Consentimento Futuro" in [a["nome"] for a in _caixa(client)["alunos"]]


def test_404_do_professor_igual_nos_tres_casos(client, monkeypatch):
    diferente = client.get(f"/professores/{OUTRO}/caixa-do-dia")
    monkeypatch.setattr(settings, "professor_id", 99)
    sem_linha = client.get("/professores/99/caixa-do-dia")
    monkeypatch.setattr(settings, "professor_id", None)
    sem_config = client.get(URL)
    assert diferente.status_code == sem_linha.status_code == sem_config.status_code == 404
    assert diferente.content == sem_linha.content == sem_config.content
    assert diferente.json() == svc_prof.PROFESSOR_INEXISTENTE


def test_multiesporte_nao_gera_motivo_nem_novo(client, session):
    _ativ(session, 90, 4, 6, tipo="leve", origem="sugestao", confirmado=False, subtipo="multiesporte_pai")
    session.commit()
    j = _caixa(client)
    assert 90 not in {n["atividade_id"] for n in j["novos"]}
    assert j["alunos"][-1]["nome"] == "Davi Teste" and j["alunos"][-1]["sem_motivo"]


def test_fora_do_normal_pela_linha_de_base(client, session):
    for k, fc in enumerate((138, 140, 141, 139, 142, 140, 141, 139)):  # 8 treinos leves do mesmo atleta, antes da janela
        _ativ(session, 100 + k, 4, 20 + k, tipo="leve", origem="professor", confirmado=True, fc=fc)
    _ativ(session, 110, 4, 1, tipo="leve", origem="professor", confirmado=True, fc=178)
    session.commit()
    j = _caixa(client)
    davi = next(a for a in j["alunos"] if a["nome"] == "Davi Teste")
    assert not davi["sem_motivo"]
    m = davi["treinos"][0]["motivos"][0]
    assert (m["codigo"], m["texto"]) == ("fora_do_normal", "Treino de terça fora do normal: FC média acima do habitual.")
    assert [a["nome"] for a in j["alunos"]][:3] == ["Ana Teste", "Davi Teste", "Bruno Teste"]  # dor, fora_do_normal, divergencia


def test_confirmar_pelo_put_tira_o_treino_de_novos_e_a_divergencia(client, session):
    assert 20 in {n["atividade_id"] for n in _caixa(client)["novos"]}
    r = client.put(f"/professores/{PROF}/tipos-de-treino", json=[{"atividade_id": 20}])
    assert r.json() == {"confirmados": 1, "corrigidos": 0}
    j = _caixa(client)
    assert 20 not in {n["atividade_id"] for n in j["novos"]}
    bruno = next(a for a in j["alunos"] if a["nome"] == "Bruno Teste")
    assert bruno["sem_motivo"]  # o motivo 3 para de disparar


def test_a_rota_nao_chama_modelo_de_linguagem():
    """A observacao livre nunca vai a um LLM: o modulo da caixa nem importa a camada de LLM."""
    import app.rotas.caixa_do_dia as m
    from pathlib import Path

    fonte = Path(m.__file__).read_text(encoding="utf-8")
    assert "app.llm" not in fonte and "litellm" not in fonte and "redator" not in fonte.lower()


@pytest.mark.parametrize("metodo,url,corpo,alvo", [
    ("get", URL, None, "app.rotas.caixa_do_dia.montar_caixa"),
    ("put", f"/professores/{PROF}/tipos-de-treino", [{"atividade_id": 10}], "app.servicos.tipo_professor.confirmar_ou_corrigir"),
])
def test_500_das_rotas_do_professor_tem_texto_neutro_e_sem_detalhe(client, monkeypatch, caplog, metodo, url, corpo, alvo):
    def quebra(*a, **k):
        raise RuntimeError(f"detalhe com {OBS}")

    monkeypatch.setattr(alvo, quebra)
    caplog.set_level(logging.DEBUG)
    r = client.request(metodo.upper(), url, json=corpo)
    assert r.status_code == 500 and r.json() == {"detail": "erro ao processar o pedido"}
    assert "check-in" not in r.text and OBS not in r.text
    assert OBS not in " ".join(x.getMessage() for x in caplog.records)


def test_500_das_rotas_de_checkin_continua_com_o_texto_do_checkin():
    from app.rotas.checkin import RotaCheckin
    from app.rotas.professor import RotaProfessor

    assert RotaCheckin.MSG_500 == "erro ao processar o check-in" and RotaProfessor.MSG_500 == "erro ao processar o pedido"
