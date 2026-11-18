"""A correcao do professor vence tudo que vem depois (#425, ADR 0015, item 5): dia com duas atividades, reimportacao do mesmo FIT,
semana-padrao editada e reaplicacao. Atletas FICTICIOS."""

from datetime import date, datetime, timezone
from pathlib import Path

from app.servicos.consentimento import TERMO_VIGENTE
from app.db.models import Atividade, Atleta, Professor, Assessoria, SemanaPadrao, VinculoProfessorAtleta, SemanaPadraoItem
from app.ingestao.importacao import importar_fit
from app.metricas import tipo_treino as tt
from app.servicos.semana_padrao import ItemNovo, gravar_vigencia
from app.servicos.tipo_professor import ItemLote, confirmar_ou_corrigir
from app.servicos.tipo_treino import aplicar_tipos
from sqlalchemy import select

AGORA = datetime(2026, 11, 16, 15, 0, tzinfo=timezone.utc)
FITS = Path(__file__).resolve().parents[4] / "tests" / "fixtures" / "garmin" / "fit"
QUARTA = (2026, 11, 11)  # quarta-feira


def _professor(session):
    session.add(Assessoria(id=1, nome="Assessoria Teste"))
    session.add(Professor(id=1, assessoria_id=1, nome="Professor Um"))
    session.flush()


def _estado(a):
    return (a.tipo_treino, a.tipo_origem, a.tipo_versao, a.tipo_divergencia, a.tipo_confirmado, a.tipo_confirmado_por, a.tipo_confirmado_em)


def test_origens_protegidas_e_uma_so_constante():
    from app.servicos import evolucao_tiros

    assert tt.ORIGENS_PROTEGIDAS == frozenset({"professor", "trainingpeaks"})
    assert not hasattr(evolucao_tiros, "ORIGENS_PROTEGIDAS")


def test_dia_com_duas_atividades_corrigir_a_dona_nao_libera_o_item_para_a_irma(session):
    _professor(session)
    atleta = Atleta(nome="Ficticio")
    session.add(atleta)
    session.flush()
    session.add(VinculoProfessorAtleta(professor_id=1, atleta_id=atleta.id, consentimento_em=datetime(2026, 11, 1, tzinfo=timezone.utc), termo_versao=TERMO_VIGENTE))
    manha = Atividade(atleta_id=atleta.id, fonte="t", fonte_id="1", modalidade="corrida", inicio=datetime(*QUARTA, 9, tzinfo=timezone.utc),
                      duracao_s=3600, fuso_min=0)
    tarde = Atividade(atleta_id=atleta.id, fonte="t", fonte_id="2", modalidade="corrida", inicio=datetime(*QUARTA, 18, tzinfo=timezone.utc),
                      duracao_s=3000, fuso_min=0)
    session.add_all([manha, tarde])
    session.add(SemanaPadrao(atleta_id=atleta.id, vigente_desde=date(2026, 11, 1), definido_por="atleta",
                             itens=[SemanaPadraoItem(dia_semana=3, modalidade="corrida", tipo_treino="longo")]))
    session.commit()
    aplicar_tipos(session, atleta.id)
    session.commit()
    donas = [a for a in (manha, tarde) if a.tipo_origem == "semana_padrao"]
    assert len(donas) == 1  # so uma consome o item do dia
    dona = donas[0]
    irma = tarde if dona is manha else manha
    irma_antes = _estado(irma)

    r = confirmar_ou_corrigir(session, 1, [ItemLote(dona.id, "leve")], AGORA)
    session.commit()
    assert (r.confirmados, r.corrigidos) == (0, 1)
    dona_depois = _estado(dona)
    assert dona_depois[:5] == ("leve", "professor", None, None, True)

    # semana editada (item novo) e reaplicada: nem a dona nem a irma mudam; a irma nao ganha o item do dia
    gravar_vigencia(session, atleta.id, date(2026, 11, 2), "professor", [ItemNovo(3, "corrida", "moderado")])
    aplicar_tipos(session, atleta.id)
    session.commit()
    session.refresh(dona)
    session.refresh(irma)
    assert _estado(dona) == dona_depois
    assert irma.tipo_origem != "semana_padrao"  # a irma nao ganha o item do dia
    assert _estado(irma) == irma_antes


def test_reimportar_o_mesmo_fit_nao_desfaz_a_correcao(session, tmp_path):
    _professor(session)
    atleta = Atleta(nome="Ficticio")
    session.add(atleta)
    session.flush()
    session.add(VinculoProfessorAtleta(professor_id=1, atleta_id=atleta.id, consentimento_em=datetime(2026, 11, 1, tzinfo=timezone.utc), termo_versao=TERMO_VIGENTE))
    session.commit()
    dados = (FITS / "upload_rodagem_6km.fit").read_bytes()
    pasta = tmp_path / "fit"
    r1 = importar_fit(session, atleta.id, dados, pasta)
    a = session.get(Atividade, r1.atividade_id)
    novo = "longo" if a.tipo_treino != "longo" else "leve"
    confirmar_ou_corrigir(session, 1, [ItemLote(a.id, novo)], AGORA)
    session.commit()
    depois = _estado(a)
    r2 = importar_fit(session, atleta.id, dados, pasta)
    assert r2.atividade_id == a.id
    session.expire_all()
    assert _estado(session.get(Atividade, a.id)) == depois
    assert depois[:5] == (novo, "professor", None, None, True)
    assert session.scalars(select(Atividade)).all() == [a]
