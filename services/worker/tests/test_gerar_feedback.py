"""`worker.gerar_feedback` (issue #327, ADR 0013): provedor FALSO, pacote e checagens injetados, sem rede e sem LiteLLM.

O pacote de fatos (#324) e as checagens (#325) entram por injecao: aqui usam-se funcoes falsas com a assinatura da ADR
(`montar_pacote(session, atividade, checkin) -> dict | None` e `checar(pacote, texto) -> str | None`). Dados sinteticos.
"""

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from app.db import models  # noqa: F401
from app.db.base import Base
from app.db.models import Atividade, Atleta, CheckinTreino, FeedbackTreino
from app.llm import ProvedorFalso, Redator
from app.llm.camada import MOTIVOS
from app.servicos.checkin import apagar_checkins_do_atleta
from app.servicos.feedback import Versoes, desatualizado
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker

from worker import apagar_checkin, gerar_feedback
from worker.importar_garmin import importar

MARCADOR = "MARCADOR-SINTETICO-123"
AGORA = datetime(2026, 11, 10, 12, 0, tzinfo=timezone.utc)
V = Versoes(fatos="fatos_treino@1", prompt="feedback_prompt@1", checagens="checagens_feedback@1")
ZIP = Path(__file__).resolve().parents[3] / "tests" / "fixtures" / "garmin" / "exportacao_minima.zip"


@pytest.fixture
def engine():
    eng = create_engine(os.environ.get("TEST_DATABASE_URL", "sqlite://"))
    Base.metadata.drop_all(eng)
    Base.metadata.create_all(eng)
    yield eng
    Base.metadata.drop_all(eng)
    eng.dispose()


@pytest.fixture
def fabrica(engine):
    return sessionmaker(bind=engine, expire_on_commit=False)


def _atleta(fabrica, n_checkins=3, nome="Ana", subtipo=None):
    """Um atleta com `n_checkins` treinos (um por dia) com check-in. Devolve o id do atleta."""
    with fabrica() as s:
        at = Atleta(nome=nome)
        s.add(at)
        s.flush()
        for i in range(n_checkins):
            a = Atividade(atleta_id=at.id, fonte="t", fonte_id=str(i), modalidade="corrida", subtipo=subtipo,
                          inicio=AGORA - timedelta(days=i), duracao_s=1800.0)
            s.add(a)
            s.flush()
            s.add(CheckinTreino(atividade_id=a.id, pse=5, sensacao=3, nada_a_relatar=False, dor=False, cansaco=True,
                                texto=MARCADOR, versao="checkin@1", registrado_em=AGORA, atualizado_em=AGORA))
        s.commit()
        return at.id


class Pacotes:
    """`montar_pacote` falso: registra a ordem dos check-ins e nunca poe o texto livre no pacote."""

    def __init__(self):
        self.ordem = []

    def __call__(self, session, atividade, checkin):
        self.ordem.append(checkin.id)
        return {"versao": V.fatos, "treino": {"modalidade": atividade.modalidade}, "campo": MARCADOR}


def _aprova(pacote, texto):
    return None


def _redator(**kw):
    falso = kw.pop("falso", None) or ProvedorFalso()
    return Redator(falso, "falso", "falso", **kw), falso


def _gerar(fabrica, atleta_id, redator, montar=None, checar=_aprova, **kw):
    from app.llm import prompt_feedback
    from app.servicos.feedback import gerar

    with fabrica() as s:
        return gerar(s, atleta_id, redator, montar or Pacotes(), checar, V, prompt_feedback.TEXTO, **kw)


def _linhas(fabrica):
    with fabrica() as s:
        return list(s.scalars(select(FeedbackTreino).order_by(FeedbackTreino.checkin_id)))


# ---------- gera e e idempotente ----------

def test_gera_o_feedback_com_o_provedor_falso(fabrica):
    at = _atleta(fabrica)
    r, falso = _redator()
    rel = _gerar(fabrica, at, r)
    assert (rel.gerados, rel.sem_feedback, rel.ignorados, rel.adiados) == (3, 0, 0, 0) and falso.chamadas == 3
    for fb in _linhas(fabrica):
        assert (fb.estado, fb.motivo, fb.texto) == ("pronto", None, ProvedorFalso.TEXTO_BOM)
        assert (fb.provedor, fb.modelo, fb.tentativas) == ("falso", "falso", 1)
        assert (fb.versao_fatos, fb.versao_prompt, fb.versao_checagens) == (V.fatos, V.prompt, V.checagens)


def test_segunda_rodada_nao_faz_nenhuma_chamada(fabrica):
    at = _atleta(fabrica)
    r, falso = _redator()
    _gerar(fabrica, at, r)
    r2, falso2 = _redator()
    rel = _gerar(fabrica, at, r2)
    assert (rel.gerados, rel.ignorados) == (0, 3) and falso2.chamadas == 0
    assert [f.tentativas for f in _linhas(fabrica)] == [1, 1, 1]


def test_atividade_nao_elegivel_fica_de_fora(fabrica):
    at = _atleta(fabrica, 2, subtipo="multiesporte_pai")
    r, falso = _redator()
    rel = _gerar(fabrica, at, r)
    assert (rel.gerados, rel.ignorados) == (0, 2) and falso.chamadas == 0 and _linhas(fabrica) == []


def test_pacote_none_nao_grava(fabrica):
    at = _atleta(fabrica, 1)
    r, falso = _redator()
    rel = _gerar(fabrica, at, r, montar=lambda *a: None)
    assert rel.ignorados == 1 and falso.chamadas == 0 and _linhas(fabrica) == []


# ---------- texto reprovado ----------

def test_texto_reprovado_nunca_e_gravado_e_a_proxima_rodada_tenta_de_novo(fabrica):
    at = _atleta(fabrica, 1)
    r, _ = _redator(falso=ProvedorFalso(texto=f"{MARCADOR} texto ruim"))
    rel = _gerar(fabrica, at, r, checar=lambda p, t: "linguagem_proibida")
    assert (rel.gerados, rel.sem_feedback) == (0, 1) and rel.motivos == {"texto_reprovado": 1}
    assert rel.reprovacoes == {"linguagem_proibida": 1}
    (fb,) = _linhas(fabrica)
    assert (fb.estado, fb.motivo, fb.texto, fb.tentativas) == ("sem_feedback", "texto_reprovado", None, 1)
    assert fb.provedor == "falso"
    # nada do texto reprovado em nenhuma coluna
    with fabrica() as s:
        bruto = s.connection().exec_driver_sql("SELECT * FROM feedback_treino").all()
    assert MARCADOR not in repr(bruto)

    r2, _ = _redator()  # nova tentativa na proxima execucao; agora passa
    rel2 = _gerar(fabrica, at, r2)
    assert (rel2.gerados, rel2.sem_feedback) == (1, 0)
    (fb,) = _linhas(fabrica)
    assert (fb.estado, fb.motivo, fb.texto, fb.tentativas) == ("pronto", None, ProvedorFalso.TEXTO_BOM, 2)


def test_codigo_da_checagem_so_aparece_se_for_um_codigo(fabrica):
    at = _atleta(fabrica, 1)
    r, _ = _redator(falso=ProvedorFalso(texto="x"))
    rel = _gerar(fabrica, at, r, checar=lambda p, t: f"o termo {MARCADOR} reprovou")
    assert rel.reprovacoes == {"outro": 1}


def test_texto_maior_que_700_e_reprovado_sem_gravar(fabrica):
    at = _atleta(fabrica, 1)
    r, _ = _redator(falso=ProvedorFalso(texto="a" * 701))
    rel = _gerar(fabrica, at, r)
    assert rel.motivos == {"texto_reprovado": 1} and _linhas(fabrica)[0].texto is None


def test_provedor_ruim_do_falso_reprova_pela_checagem(fabrica):
    at = _atleta(fabrica, 1)
    r, _ = _redator(falso=ProvedorFalso(modo="ruim"))
    rel = _gerar(fabrica, at, r, checar=lambda p, t: "numero_fora_do_pacote" if "99" in t else None)
    assert rel.motivos == {"texto_reprovado": 1}


# ---------- erro do provedor ----------

@pytest.mark.parametrize("modo,motivo", [("erro", "provedor_erro"), ("tempo", "provedor_tempo_limite"),
                                         ("vazio", "provedor_erro")])
def test_erro_do_provedor_vira_motivo_e_a_proxima_rodada_tenta_de_novo(fabrica, modo, motivo):
    at = _atleta(fabrica, 2)
    r, _ = _redator(falso=ProvedorFalso(modo=modo))
    rel = _gerar(fabrica, at, r)
    assert (rel.sem_feedback, rel.motivos) == (2, {motivo: 2})
    assert {(f.estado, f.motivo, f.texto) for f in _linhas(fabrica)} == {("sem_feedback", motivo, None)}
    r2, falso2 = _redator()
    assert _gerar(fabrica, at, r2).gerados == 2 and falso2.chamadas == 2


def test_provedor_nao_configurado_grava_o_motivo_e_nao_chama(fabrica):
    at = _atleta(fabrica, 2)
    r = Redator(None, "groq", None)
    rel = _gerar(fabrica, at, r)
    assert rel.motivos == {"provedor_nao_configurado": 2}
    assert {f.motivo for f in _linhas(fabrica)} == {"provedor_nao_configurado"}
    assert "provedor_nao_configurado" in MOTIVOS


def test_falha_ao_montar_o_pacote_nao_grava_e_nao_derruba(fabrica):
    at = _atleta(fabrica, 2)
    r, falso = _redator()

    def quebra(*a):
        raise RuntimeError(MARCADOR)

    rel = _gerar(fabrica, at, r, montar=quebra)
    assert (rel.erros, rel.gerados) == (2, 0) and falso.chamadas == 0 and _linhas(fabrica) == []


# ---------- limite e fila ----------

def test_limite_de_chamadas_por_execucao_e_a_proxima_completa(fabrica):
    at = _atleta(fabrica, 3)
    r, falso = _redator(limite_chamadas=2)
    rel = _gerar(fabrica, at, r)
    assert (rel.gerados, rel.adiados) == (2, 1) and falso.chamadas == 2 and len(_linhas(fabrica)) == 2
    r2, falso2 = _redator(limite_chamadas=2)
    rel2 = _gerar(fabrica, at, r2)
    assert (rel2.gerados, rel2.ignorados, rel2.adiados) == (1, 2, 0) and falso2.chamadas == 1


def test_fila_nunca_tentados_primeiro_depois_menos_tentativas(fabrica):
    at = _atleta(fabrica, 3)
    with fabrica() as s:  # check-ins 1 (mais recente), 2 e 3
        ids = [c.id for c in s.scalars(select(CheckinTreino).order_by(CheckinTreino.id))]
        agora = AGORA
        for cid, tent in ((ids[0], 3), (ids[1], 1)):  # tentados e reprovados antes
            s.add(FeedbackTreino(checkin_id=cid, estado="sem_feedback", motivo="texto_reprovado", versao_fatos=V.fatos,
                                 versao_prompt=V.prompt, versao_checagens=V.checagens, tentativas=tent,
                                 checkin_atualizado_em=agora, tentado_em=agora))
        s.commit()
    pacotes = Pacotes()
    r, _ = _redator()
    _gerar(fabrica, at, r, montar=pacotes)
    assert pacotes.ordem == [ids[2], ids[1], ids[0]]  # nunca tentado; 1 tentativa; 3 tentativas


def test_treino_que_sempre_reprova_nao_gasta_o_limite_dos_outros(fabrica):
    at = _atleta(fabrica, 2)
    with fabrica() as s:
        ids = [c.id for c in s.scalars(select(CheckinTreino).order_by(CheckinTreino.id))]
    reprova_o_primeiro = lambda p, t: "linguagem_proibida" if p["id_teste"] == ids[0] else None  # noqa: E731

    def montar(session, atividade, checkin):
        return {"id_teste": checkin.id}

    for _ in range(3):  # o primeiro reprova sempre; com limite 1 o segundo precisa ser atendido mesmo assim
        r, _ = _redator(limite_chamadas=1)
        _gerar(fabrica, at, r, montar=montar, checar=reprova_o_primeiro)
    por_id = {f.checkin_id: f for f in _linhas(fabrica)}
    assert por_id[ids[1]].estado == "pronto" and por_id[ids[0]].estado == "sem_feedback"


# ---------- desatualizado e refazer ----------

def test_editar_o_checkin_deixa_desatualizado_e_refaz_com_tentativas_1(fabrica):
    at = _atleta(fabrica, 1)
    r, _ = _redator()
    _gerar(fabrica, at, r)
    with fabrica() as s:
        c = s.scalars(select(CheckinTreino)).one()
        fb = c.feedback
        assert not desatualizado(fb, c, V.fatos)
        c.atualizado_em = AGORA + timedelta(minutes=5)  # `PUT` (ate o identico muda `atualizado_em`)
        s.commit()
        assert desatualizado(fb, c, V.fatos)
    r2, falso2 = _redator(falso=ProvedorFalso(texto="Texto novo."))
    rel = _gerar(fabrica, at, r2)
    assert rel.gerados == 1 and falso2.chamadas == 1
    (fb,) = _linhas(fabrica)
    assert fb.texto == "Texto novo." and fb.tentativas == 1  # o texto antigo se perde
    assert _gerar(fabrica, at, _redator()[0]).gerados == 0  # em dia de novo


def test_versao_de_fatos_nova_deixa_desatualizado(fabrica):
    from app.llm import prompt_feedback
    from app.servicos.feedback import gerar

    at = _atleta(fabrica, 1)
    _gerar(fabrica, at, _redator()[0])
    nova = Versoes(fatos="fatos_treino@2", prompt=V.prompt, checagens=V.checagens)
    with fabrica() as s:
        rel = gerar(s, at, _redator()[0], Pacotes(), _aprova, nova, prompt_feedback.TEXTO)
    assert rel.gerados == 1 and _linhas(fabrica)[0].versao_fatos == "fatos_treino@2"


def test_refazer_refaz_o_que_esta_pronto_dentro_do_limite(fabrica):
    at = _atleta(fabrica, 3)
    _gerar(fabrica, at, _redator()[0])
    r, falso = _redator(limite_chamadas=2)
    rel = _gerar(fabrica, at, r, refazer=True)
    assert (rel.gerados, rel.adiados) == (2, 1) and falso.chamadas == 2
    assert sorted(f.tentativas for f in _linhas(fabrica)) == [1, 2, 2]  # mesmo check-in: soma


# ---------- apagar ----------

def test_apagar_o_checkin_apaga_o_feedback_e_a_atividade_tambem(fabrica):
    at = _atleta(fabrica, 2)
    _gerar(fabrica, at, _redator()[0])
    with fabrica() as s:
        c1, c2 = s.scalars(select(CheckinTreino).order_by(CheckinTreino.id)).all()
        s.delete(c1)  # o check-in
        s.delete(c2.atividade)  # a atividade (cascata ate o feedback)
        s.commit()
    assert _linhas(fabrica) == []


def test_apagar_checkin_do_worker_cobre_o_feedback_e_imprime_so_contagens(fabrica, monkeypatch, capsys, caplog):
    from app.db import session as sessao

    monkeypatch.setattr(sessao, "SessionLocal", fabrica)
    at = _atleta(fabrica, 2)
    _atleta(fabrica, 1, nome="Beto")
    _gerar(fabrica, at, _redator()[0])
    caplog.set_level("DEBUG")
    assert apagar_checkin.main(["--atleta", "Ana"]) == 0
    saida = capsys.readouterr()
    assert saida.out == "checkins: apagados=2\nfeedbacks: apagados=2\n"
    assert MARCADOR not in saida.out + saida.err + caplog.text
    assert _linhas(fabrica) == []
    with fabrica() as s:  # fechar a sessao: uma aberta (idle in transaction) trava o DROP TABLE do teardown no Postgres
        assert len(list(s.scalars(select(CheckinTreino)))) == 1
    assert apagar_checkin.main(["--atleta", "Ana"]) == 0
    assert capsys.readouterr().out == "checkins: apagados=0\nfeedbacks: apagados=0\n"


def test_servico_de_apagar_devolve_o_int_de_sempre(fabrica):
    at = _atleta(fabrica, 2)
    _gerar(fabrica, at, _redator()[0])
    with fabrica() as s:
        assert apagar_checkins_do_atleta(s, at) == 2
        assert s.scalar(select(func.count()).select_from(FeedbackTreino)) == 0


def test_reimportar_a_atividade_mantem_checkin_e_feedback(fabrica):
    with fabrica() as s:
        importar(s, ZIP, "Atleta Ficticio")
        a = s.scalars(select(Atividade).order_by(Atividade.id)).first()
        s.add(CheckinTreino(atividade_id=a.id, pse=5, sensacao=3, nada_a_relatar=True, versao="checkin@1",
                            registrado_em=AGORA, atualizado_em=AGORA))
        s.commit()
        at = a.atleta_id
    _gerar(fabrica, at, _redator()[0], montar=lambda *x: {"a": 1})
    with fabrica() as s:
        importar(s, ZIP, "Atleta Ficticio")  # atualiza no lugar (ADR 0006)
    assert len(_linhas(fabrica)) == 1
    assert _gerar(fabrica, at, _redator()[0]).gerados == 0  # e nao refaz sozinho


# ---------- nada do conteudo em log, saida ou excecao ----------

def test_nada_do_pacote_nem_do_texto_vai_para_log_ou_saida(fabrica, monkeypatch, capsys, caplog):
    at = _atleta(fabrica, 3)
    caplog.set_level("DEBUG")
    casos = [ProvedorFalso(texto=f"{MARCADOR} ok"), ProvedorFalso(modo="erro"), ProvedorFalso(texto=f"{MARCADOR} ruim")]
    for falso in casos:
        rel = _gerar(fabrica, at, Redator(falso, "falso", "falso", limite_chamadas=1),
                     checar=lambda p, t: "linguagem_proibida" if "ruim" in t else None)
    saida = capsys.readouterr()
    assert MARCADOR not in saida.out + saida.err + caplog.text and rel is not None


# ---------- linha de comando ----------

def _main(fabrica, *args, redator=None, **kw):
    return gerar_feedback.main(["--atleta", "Ana", *args], redator=redator or _redator()[0], montar_pacote=Pacotes(),
                               checar=_aprova, versoes=V, session_factory=fabrica, **kw)


def test_comando_imprime_so_contagens(fabrica, capsys, caplog):
    _atleta(fabrica, 3)
    caplog.set_level("DEBUG")
    assert _main(fabrica, "--limite", "2") == 0
    saida = capsys.readouterr()
    assert saida.out == "feedback: gerados=2 sem_feedback=0 ignorados=0 adiados=1 erros=0\n"
    assert MARCADOR not in saida.out + saida.err + caplog.text
    assert _main(fabrica) == 0 and "gerados=1 sem_feedback=0 ignorados=2" in capsys.readouterr().out


def test_comando_mostra_motivos(fabrica, capsys):
    _atleta(fabrica, 1)
    assert _main(fabrica, redator=_redator(falso=ProvedorFalso(modo="tempo"))[0]) == 0
    assert "motivos: provedor_tempo_limite=1" in capsys.readouterr().out


def test_comando_atleta_inexistente_e_limite_negativo(fabrica, capsys):
    assert gerar_feedback.main(["--atleta", "Ninguem"], redator=_redator()[0], montar_pacote=Pacotes(), checar=_aprova,
                               versoes=V, session_factory=fabrica) == 1
    assert "atleta nao encontrado" in capsys.readouterr().err
    assert _main(fabrica, "--limite", "-1") == 1


def test_comando_nome_repetido_usa_o_de_menor_id_e_avisa(fabrica, capsys):
    primeiro = _atleta(fabrica, 1, nome="Ana")
    _atleta(fabrica, 1, nome="Ana")
    assert _main(fabrica) == 0
    assert "usado o de menor id" in capsys.readouterr().err
    with fabrica() as s:
        assert [f.checkin.atividade.atleta_id for f in s.scalars(select(FeedbackTreino))] == [primeiro]


def test_comando_sem_pacote_e_checagens_disponiveis(fabrica, monkeypatch, capsys):
    monkeypatch.setattr(gerar_feedback, "_padroes", lambda: None)
    assert gerar_feedback.main(["--atleta", "Ana"], redator=_redator()[0], session_factory=fabrica) == 1
    assert "ainda nao estao disponiveis" in capsys.readouterr().err


def test_comando_provedor_nao_configurado_avisa(fabrica, capsys):
    _atleta(fabrica, 1)
    assert _main(fabrica, redator=Redator(None, "groq", None)) == 0
    saida = capsys.readouterr()
    assert "motivos: provedor_nao_configurado=1" in saida.out and "nao configurado" in saida.err


# ---------- ponta a ponta com o pacote do banco e as checagens de verdade (padroes do comando) ----------

def _carrega_semeador():
    import importlib.util
    import sys

    arq = Path(__file__).resolve().parents[2] / "api" / "tests" / "servicos" / "test_feedback_fatos.py"
    spec = importlib.util.spec_from_file_location("semeador_feedback_fatos", arq)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_ponta_a_ponta_com_o_oraculo_no_banco_e_as_checagens_reais(fabrica, capsys):
    sem = _carrega_semeador()
    with fabrica() as s:
        sem._semear(s, "F01")
    bom = ProvedorFalso(texto=_texto_g01())
    assert gerar_feedback.main(["--atleta", "Atleta Ficticio"], redator=Redator(bom, "falso", "falso"),
                               session_factory=fabrica) == 0  # sem injecao: pacote do adaptador e checar real
    assert "gerados=1 sem_feedback=0" in capsys.readouterr().out
    (fb,) = _linhas(fabrica)
    assert (fb.estado, fb.texto, fb.versao_fatos, fb.versao_checagens) == (
        "pronto", _texto_g01(), "fatos_treino@1", "checagens_feedback@1")

    ruim = ProvedorFalso(modo="ruim")  # numero fora do pacote, causa, conselho...: reprova e nao grava o texto ruim
    assert gerar_feedback.main(["--atleta", "Atleta Ficticio", "--refazer"], redator=Redator(ruim, "falso", "falso"),
                               session_factory=fabrica) == 0
    saida = capsys.readouterr().out
    assert "sem_feedback=0" in saida and "mantidos=1" in saida and "texto_reprovado=1" in saida
    (fb,) = _linhas(fabrica)  # #357: o `--refazer` que falha mantem o texto pronto e em dia
    assert (fb.estado, fb.motivo, fb.texto, fb.tentativas) == ("pronto", None, _texto_g01(), 1)


def _texto_g01():
    from app.llm.exemplos_feedback import EXEMPLOS

    return next(e["texto"] for e in EXEMPLOS if e["id"] == "G01")


def test_padroes_do_comando_existem():
    assert gerar_feedback._padroes() is not None


# ---------- #357: limite por minuto do provedor, pausa entre chamadas e `--refazer` sem perder o texto pronto ----------

def test_limite_do_provedor_para_a_execucao_sem_gravar_linha(fabrica):
    at = _atleta(fabrica, 3)
    r, falso = _redator(falso=ProvedorFalso(modo="limite"))
    rel = _gerar(fabrica, at, r)
    assert (rel.gerados, rel.sem_feedback, rel.adiados, rel.limite_do_provedor) == (0, 0, 3, True)
    assert falso.chamadas == 1 and _linhas(fabrica) == []  # parou na primeira recusa, sem gastar as outras
    assert _gerar(fabrica, at, _redator()[0]).gerados == 3  # a proxima execucao completa


def test_pausa_so_entre_chamadas(fabrica):
    at = _atleta(fabrica, 3)
    pausas = []
    r = Redator(ProvedorFalso(), "falso", "falso", intervalo_s=30, dormir=pausas.append)
    assert _gerar(fabrica, at, r).gerados == 3
    assert pausas == [30, 30]  # nenhuma antes da primeira


def test_sem_intervalo_nao_dorme(fabrica):
    at = _atleta(fabrica, 2)
    pausas = []
    _gerar(fabrica, at, Redator(ProvedorFalso(), "falso", "falso", dormir=pausas.append))
    assert pausas == []


@pytest.mark.parametrize("modo", ["erro", "tempo", "checagem"])
def test_refazer_que_falha_mantem_o_texto_pronto(fabrica, modo):
    at = _atleta(fabrica, 1)
    _gerar(fabrica, at, _redator(falso=ProvedorFalso(texto="Texto bom."))[0])
    if modo == "checagem":
        rel = _gerar(fabrica, at, _redator(falso=ProvedorFalso(texto="Texto novo."))[0], checar=lambda p, t: "numero_fora_do_pacote",
                     refazer=True)
    else:
        rel = _gerar(fabrica, at, _redator(falso=ProvedorFalso(modo=modo))[0], refazer=True)
    assert (rel.gerados, rel.sem_feedback, rel.mantidos) == (0, 0, 1)
    (fb,) = _linhas(fabrica)
    assert (fb.estado, fb.texto, fb.tentativas) == ("pronto", "Texto bom.", 1)


def test_falha_em_checkin_editado_nao_mantem_o_texto_antigo(fabrica):
    at = _atleta(fabrica, 1)
    _gerar(fabrica, at, _redator(falso=ProvedorFalso(texto="Texto bom."))[0])
    with fabrica() as s:
        s.scalars(select(CheckinTreino)).one().atualizado_em = AGORA + timedelta(minutes=5)
        s.commit()
    rel = _gerar(fabrica, at, _redator(falso=ProvedorFalso(modo="erro"))[0])
    assert (rel.sem_feedback, rel.mantidos) == (1, 0)
    (fb,) = _linhas(fabrica)
    assert (fb.estado, fb.texto) == ("sem_feedback", None)  # o texto de um check-in editado nao vale mais


def test_comando_avisa_do_limite_do_provedor_e_mostra_mantidos(fabrica, capsys):
    at = _atleta(fabrica, 2, nome="Bia")
    r, _ = _redator(falso=ProvedorFalso(modo="limite"))
    assert gerar_feedback.main(["--atleta", "Bia"], redator=r, montar_pacote=Pacotes(), checar=_aprova, versoes=V,
                               session_factory=fabrica) == 0
    saida = capsys.readouterr()
    assert "adiados=2" in saida.out and "limite de requisicoes" in saida.err and "mantidos" not in saida.out
