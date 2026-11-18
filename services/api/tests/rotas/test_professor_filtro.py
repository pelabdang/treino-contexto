"""Professor do piloto e filtro de vinculo e consentimento (#423, ADR 0015, itens 2 e 3). Atletas e professores FICTICIOS."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import Depends, FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.autenticacao import professor_da_sessao
from app.config import Settings, settings
from app.servicos.consentimento import TERMO_VIGENTE
from app.db.models import (
    Assessoria, Atividade, Atleta, CheckinTreino, Professor, VinculoProfessorAtleta,
)
from app.db.session import get_session
from app.servicos import professor as svc

AGORA = datetime(2026, 11, 16, 15, 0, tzinfo=timezone.utc)
PROF, OUTRO = 1, 2

# situacao -> (consentimento do vinculo com PROF, tem vinculo com PROF, vinculo com OUTRO, deve aparecer)
SITUACOES = {
    "consentido": dict(vinculo=True, consentimento=AGORA - timedelta(days=3), aparece=True),
    "consentimento_nulo": dict(vinculo=True, consentimento=None, aparece=False),
    "consentimento_no_futuro": dict(vinculo=True, consentimento=AGORA + timedelta(minutes=1), aparece=False),
    "so_de_outro_professor": dict(vinculo=False, consentimento=None, aparece=False, outro=True),
    "sem_vinculo": dict(vinculo=False, consentimento=None, aparece=False),
}


@pytest.fixture
def mundo(session: Session):
    """Um atleta por situacao, cada um com um treino e um check-in. Devolve {situacao: atleta_id}."""
    session.add(Assessoria(id=1, nome="Assessoria Teste"))
    session.add_all([Professor(id=PROF, assessoria_id=1, nome="Professor Um"), Professor(id=OUTRO, assessoria_id=1, nome="Professor Dois")])
    session.flush()
    ids = {}
    for i, (nome, s) in enumerate(SITUACOES.items(), start=1):
        session.add(Atleta(id=i, assessoria_id=1, nome=f"Atleta {nome}"))  # mesma assessoria: nao pode dar atalho
        session.flush()
        session.add(Atividade(id=i, atleta_id=i, fonte="t", fonte_id=str(i), modalidade="corrida", inicio=AGORA - timedelta(days=1), duracao_s=1800))
        session.flush()
        session.add(CheckinTreino(
            atividade_id=i, pse=5, sensacao=3, nada_a_relatar=True, dor=False, cansaco=False, sono_ruim=False, calor=False,
            trabalho_estresse=False, versao="checkin@1", registrado_em=AGORA, atualizado_em=AGORA))
        if s["vinculo"]:
            session.add(VinculoProfessorAtleta(professor_id=PROF, atleta_id=i, consentimento_em=s["consentimento"], termo_versao=TERMO_VIGENTE))
        if s.get("outro"):
            session.add(VinculoProfessorAtleta(professor_id=OUTRO, atleta_id=i, consentimento_em=AGORA - timedelta(days=9), termo_versao=TERMO_VIGENTE))
        ids[nome] = i
    session.flush()  # sem commit: a conexao fica com a sessao e a thread do TestClient ve o mesmo SQLite em memoria
    return ids


def _visiveis(session, professor_id=PROF, agora=AGORA):
    return set(session.scalars(select(Atleta.id).where(Atleta.id.in_(svc.atletas_do_professor(professor_id, agora)))))


# ---------- configuracao ----------

@pytest.fixture
def sem_ambiente(monkeypatch, tmp_path):
    monkeypatch.delenv("PROFESSOR_ID", raising=False)

    class S(Settings):
        model_config = {**Settings.model_config, "env_file": tmp_path / ".env"}

    return S, tmp_path / ".env"


def test_configuracao_sobe_com_a_variavel_ausente(sem_ambiente):
    S, _ = sem_ambiente
    assert S().professor_id is None


@pytest.mark.parametrize("valor", ["", "   "])
def test_configuracao_sobe_com_a_variavel_vazia_no_ambiente_e_no_arquivo(sem_ambiente, monkeypatch, valor):
    S, env = sem_ambiente
    monkeypatch.setenv("PROFESSOR_ID", valor)
    assert S().professor_id is None
    monkeypatch.delenv("PROFESSOR_ID")
    env.write_text(f"PROFESSOR_ID={valor}\n", encoding="utf-8")
    assert S().professor_id is None


def test_configuracao_le_o_inteiro(sem_ambiente, monkeypatch):
    S, _ = sem_ambiente
    monkeypatch.setenv("PROFESSOR_ID", "3")
    assert S().professor_id == 3


def test_env_example_traz_a_variavel_comentada():
    from app.config import RAIZ_REPOSITORIO

    linhas = (RAIZ_REPOSITORIO / ".env.example").read_text(encoding="utf-8").splitlines()
    assert "# PROFESSOR_ID=1" in linhas
    assert not any(l.startswith("PROFESSOR_ID") for l in linhas)


# ---------- o filtro ----------

def test_filtro_devolve_so_vinculo_com_consentimento_ate_agora(session, mundo):
    esperado = {mundo[n] for n, s in SITUACOES.items() if s["aparece"]}
    assert esperado == {mundo["consentido"]}
    assert _visiveis(session) == esperado


def test_o_outro_professor_ve_so_o_dele(session, mundo):
    assert _visiveis(session, OUTRO) == {mundo["so_de_outro_professor"]}


def test_consentimento_no_futuro_entra_quando_a_hora_chega(session, mundo):
    futuro = mundo["consentimento_no_futuro"]
    limite = AGORA + timedelta(minutes=1)
    assert futuro not in _visiveis(session, agora=limite - timedelta(seconds=1))
    assert futuro in _visiveis(session, agora=limite)  # `<=`: no instante exato ja vale


def test_consentimento_retirado_some_sem_apagar_o_atleta(session, mundo):
    ana = mundo["consentido"]
    session.get(VinculoProfessorAtleta, (PROF, ana)).consentimento_em = None
    session.commit()
    assert ana not in _visiveis(session)
    assert session.get(Atleta, ana) is not None and session.get(VinculoProfessorAtleta, (PROF, ana)) is not None


def test_filtro_e_expressao_sql_e_exige_fuso():
    assert not isinstance(svc.atletas_do_professor(PROF, AGORA), (list, set, tuple))
    with pytest.raises(ValueError):
        svc.atletas_do_professor(PROF, datetime(2026, 11, 16, 15, 0))


def test_filtro_nao_usa_now_no_sql():
    sql = str(svc.atletas_do_professor(PROF, AGORA).compile()).lower()
    assert "now" not in sql and "current_timestamp" not in sql


def test_so_atletas_visiveis_vale_para_atividade_e_checkin(session, mundo):
    visivel = mundo["consentido"]
    ativ = session.scalars(svc.so_atletas_visiveis(select(Atividade), Atividade.atleta_id, PROF, AGORA)).all()
    assert [a.atleta_id for a in ativ] == [visivel]
    check = session.scalars(
        svc.so_atletas_visiveis(select(CheckinTreino).join(Atividade), Atividade.atleta_id, PROF, AGORA)).all()
    assert [c.atividade_id for c in check] == [visivel]


# ---------- a matriz rota x situacao (rota de teste: as reais da Meta 11 usam as mesmas pecas) ----------

@pytest.fixture
def cliente(session, mundo, monkeypatch):
    app = FastAPI()

    def _professor_da_sessao(professor_id: int) -> int:  # a "sessao" deste teste e o professor PROF
        if professor_id != PROF:
            raise HTTPException(status_code=404, detail=svc.PROFESSOR_INEXISTENTE["detail"])
        return PROF

    def _sessao():
        yield session

    @app.get("/professores/{professor_id}/atletas/{atleta_id}")
    def ler_atleta(atleta_id: int, pid: int = Depends(svc.professor_da_rota), s: Session = Depends(_sessao),
                   agora: datetime = Depends(svc.agora_utc)):
        return {"id": svc.atleta_visivel(s, pid, atleta_id, agora).id}

    @app.get("/professores/{professor_id}/treinos")
    def listar(pid: int = Depends(svc.professor_da_rota), s: Session = Depends(_sessao), agora: datetime = Depends(svc.agora_utc)):
        q = svc.so_atletas_visiveis(select(Atividade.atleta_id), Atividade.atleta_id, pid, agora)
        return {"atletas": sorted(s.scalars(q))}

    app.dependency_overrides[get_session] = _sessao
    app.dependency_overrides[professor_da_sessao] = _professor_da_sessao
    app.dependency_overrides[svc.agora_utc] = lambda: AGORA
    return TestClient(app)


@pytest.mark.parametrize("situacao", list(SITUACOES))
def test_matriz_rota_por_situacao(cliente, mundo, situacao):
    aparece = SITUACOES[situacao]["aparece"]
    atleta = mundo[situacao]
    r = cliente.get(f"/professores/{PROF}/atletas/{atleta}")
    assert (r.status_code, r.json()) == ((200, {"id": atleta}) if aparece else (404, svc.ATLETA_NAO_ENCONTRADO))
    lista = cliente.get(f"/professores/{PROF}/treinos").json()["atletas"]
    assert (atleta in lista) is aparece


def test_atleta_inexistente_tem_o_mesmo_404_de_atleta_fora_do_filtro(cliente, mundo):
    fora = cliente.get(f"/professores/{PROF}/atletas/{mundo['consentimento_nulo']}")
    nao_existe = cliente.get(f"/professores/{PROF}/atletas/9999")
    assert fora.status_code == nao_existe.status_code == 404
    assert fora.content == nao_existe.content


def test_o_filtro_usa_o_id_da_sessao_nao_o_do_caminho(cliente, monkeypatch):
    ok = cliente.get(f"/professores/{PROF}/treinos")
    assert ok.status_code == 200 and ok.json()["atletas"] == [1]
    # o id do outro professor no caminho nunca troca a identidade: 404, nao a lista do outro
    assert cliente.get(f"/professores/{OUTRO}/treinos").status_code == 404
