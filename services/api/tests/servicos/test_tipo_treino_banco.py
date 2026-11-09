"""`aplicar_tipos` e `reaplicar_tipos` no banco contra o oraculo das fixtures da Meta 7 (issue #265, ADR 0011).

As fixtures (tests/fixtures/meta7/, #261 e #278) resumem os blocos em `estrutura`; aqui cada resumo vira blocos de verdade
em `bloco_atividade` (esforcos@1) e o tipo passa pelo banco: leitura, `tipo_treino@1`, gravacao so do que muda.
"""

import importlib.util
import json
import sys
from datetime import date, datetime
from pathlib import Path

import pytest
from app.db.models import Atividade, Atleta, BlocoAtividade, SemanaPadrao, SemanaPadraoItem
from app.metricas import esforcos as ef
from app.metricas import tipo_treino as tt
from app.servicos.evolucao_tiros import classificar_atividades, reclassificacao_pendente, serie_tiros_1km
from app.servicos.semana_padrao import ItemNovo, gravar_vigencia, reaplicar_tipos
from app.servicos.tipo_treino import aplicar_tipos
from sqlalchemy import select

PASTA = Path(__file__).parents[4] / "tests" / "fixtures" / "meta7"


def _oraculo():
    spec = importlib.util.spec_from_file_location("oraculo_meta7_db", PASTA / "oraculo.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


TIPO_ESPERADO = _oraculo().TIPO_ESPERADO
FIXTURES = json.loads((PASTA / "atividades.json").read_text(encoding="utf-8"))["atividades"]
VIGENCIAS = json.loads((PASTA / "semana_padrao.json").read_text(encoding="utf-8"))["vigencias"]


def _blocos(a, estrutura, n_tiros):
    """Blocos de verdade (esforcos@1) para o resumo `estrutura` da fixture."""
    def b(ordem, cat, dur, dist, faixa=None):
        a.blocos.append(BlocoAtividade(
            ordem=ordem, categoria=cat, volta_inicial=ordem, volta_final=ordem, inicio_offset_s=0.0,
            duracao_s=dur, distancia_m=dist, pace_s_km=dur / dist * 1000, faixa=faixa, versao_deteccao=ef.VERSAO))

    if estrutura == "sem_esforco":
        b(0, "leve", a.duracao_s, a.distancia_m)
    elif estrutura == "esforco":
        b(0, "aquecimento", 600, 1500)
        b(1, "esforco", 300, 1000, "d1500")  # um esforco que nao e de 1 km: nao e serie de tiros
        b(2, "desaquecimento", 600, 1500)
    elif estrutura == "tiros":
        b(0, "aquecimento", 600, 1500)
        ordem = 1
        for i in range(n_tiros):
            b(ordem, "esforco", 250, 1000, "d1000")
            b(ordem + 1, "recuperacao", 200, 500)
            ordem += 2
        b(ordem, "desaquecimento", 600, 1500)


def _carregar(session, com_vigencias=VIGENCIAS):
    atleta = Atleta(nome="Ficticio")
    session.add(atleta)
    session.flush()
    por_id = {}
    for f in FIXTURES:
        a = Atividade(
            atleta_id=atleta.id, fonte="fixture", fonte_id=f["id"], modalidade=f["modalidade"], subtipo=f["subtipo"],
            inicio=datetime.fromisoformat(f["inicio"]), fuso_min=f["fuso_min"], duracao_s=f["duracao_s"],
            distancia_m=f["distancia_m"], fc_media=f["fc_media"], tipo_treino=f["tipo_treino"],
            tipo_origem=f["tipo_origem"], tipo_confirmado=f["tipo_confirmado"])
        session.add(a)
        _blocos(a, f["estrutura"], (f["tiros"] or {}).get("n", 0))
        por_id[f["id"]] = a
    for v in com_vigencias:
        session.add(SemanaPadrao(
            atleta_id=atleta.id, vigente_desde=date.fromisoformat(v["vigente_desde"]), definido_por=v["definido_por"],
            itens=[SemanaPadraoItem(dia_semana=i["dia_semana"], modalidade=i["modalidade"], tipo_treino=i["tipo_treino"])
                   for i in v["itens"]]))
    session.commit()
    return atleta, por_id


def _estado(por_id):
    return {i: (a.tipo_treino, a.tipo_origem, a.tipo_divergencia) for i, a in por_id.items()}


def _linha(a):
    return (a.tipo_treino, a.tipo_origem, a.tipo_versao, a.tipo_divergencia)


def test_oraculo_das_81_atividades_passando_pelo_banco(session):
    atleta, por_id = _carregar(session)
    mudaram = aplicar_tipos(session, atleta.id)
    session.commit()
    session.expire_all()
    assert _estado(por_id) == TIPO_ESPERADO
    # a versao so existe onde a regra escreveu (sugestao ou semana_padrao)
    for a in por_id.values():
        assert (a.tipo_versao == tt.VERSAO) == (a.tipo_origem in ("sugestao", "semana_padrao"))
    # so mudou o que precisava: as 2 protegidas por origem e a confirmada ficaram como estavam, e o resto foi gravado
    protegidos = {i for i, f in ((f["id"], f) for f in FIXTURES) if f["tipo_origem"] or f["tipo_confirmado"]}
    assert len(protegidos) == 3
    assert mudaram == sum(1 for i, e in TIPO_ESPERADO.items() if i not in protegidos and e != (None, None, None))
    # idempotente: a segunda passada nao toca em nada
    assert aplicar_tipos(session, atleta.id) == 0


def test_divergencias_do_oraculo_gravadas_como_dado(session):
    atleta, por_id = _carregar(session)
    aplicar_tipos(session, atleta.id)
    assert (por_id["2026-01-13/cor1"].tipo_treino, por_id["2026-01-13/cor1"].tipo_divergencia) == ("intervalado", "sem_esforco")
    assert (por_id["2026-03-28/cor1"].tipo_treino, por_id["2026-03-28/cor1"].tipo_divergencia) == ("longo", "tem_tiros")


def test_protegidos_nunca_mudam_nem_a_versao(session):
    atleta, por_id = _carregar(session)
    antes = {i: _linha(por_id[i]) for i in ("2026-01-08/cor1", "2026-01-15/cor1", "2026-01-29/cor1")}
    aplicar_tipos(session, atleta.id)
    assert {i: _linha(por_id[i]) for i in antes} == antes


def test_so_grava_o_que_muda(session):
    atleta, por_id = _carregar(session)
    aplicar_tipos(session, atleta.id)
    session.commit()
    session.expire_all()
    vistos = []
    from sqlalchemy import event

    def espia(conn, cursor, statement, *a):
        if statement.lstrip().upper().startswith("UPDATE ATIVIDADE"):
            vistos.append(statement)

    event.listen(session.get_bind(), "before_cursor_execute", espia)
    try:
        assert aplicar_tipos(session, atleta.id) == 0
        session.commit()
    finally:
        event.remove(session.get_bind(), "before_cursor_execute", espia)
    assert vistos == []


def test_reaplicacao_pela_semana_nova_nao_reescreve_o_passado(session):
    """So a vigencia A existe e foi aplicada; gravar a B (2026-03-02) mexe so em data local >= 2026-03-02 (item 8)."""
    atleta, por_id = _carregar(session, com_vigencias=VIGENCIAS[:1])
    aplicar_tipos(session, atleta.id)
    session.commit()
    antes = {i: _linha(a) for i, a in por_id.items()}

    b = VIGENCIAS[1]  # o PUT HTTP chama exatamente isto (a rota tem o teste dela em tests/rotas)
    _, reaplicadas = gravar_vigencia(
        session, atleta.id, date.fromisoformat(b["vigente_desde"]), b["definido_por"],
        [ItemNovo(i["dia_semana"], i["modalidade"], i["tipo_treino"]) for i in b["itens"]])
    session.expire_all()
    depois = {i: _linha(a) for i, a in por_id.items()}
    mudadas = {i for i in antes if antes[i] != depois[i]}
    assert mudadas and all(i >= "2026-03-02" for i in mudadas)  # o id comeca pela data
    assert reaplicadas == len(mudadas)
    assert _estado(por_id) == TIPO_ESPERADO  # e termina igual ao oraculo
    # a quinta 05/03 passou de fartlek para moderado; a de 26/02 continua fartlek (vigencia A)
    assert por_id["2026-03-05/cor1"].tipo_treino == "moderado" and por_id["2026-02-26/cor1"].tipo_treino == "fartlek"


def test_reaplicar_tipos_so_olha_a_partir_da_data_local(session):
    atleta, por_id = _carregar(session)
    n = reaplicar_tipos(session, atleta.id, date(2026, 3, 2))
    session.commit()
    assert n > 0
    assert all(a.tipo_origem is None for i, a in por_id.items() if i < "2026-03-02" and not FIXTURES_INICIAIS[i])
    assert por_id["2026-03-03/cor1"].tipo_origem == "semana_padrao"


FIXTURES_INICIAIS = {f["id"]: f["tipo_origem"] or f["tipo_confirmado"] for f in FIXTURES}


def test_borda_de_fuso_domingo_23_30_local(session):
    """A vigencia vale pela data local: 23:30 local de domingo (02:30 UTC de segunda) ainda e domingo (E11)."""
    atleta = Atleta(nome="F")
    session.add(atleta)
    session.flush()
    a = Atividade(atleta_id=atleta.id, fonte="x", fonte_id="1", modalidade="corrida", inicio=datetime.fromisoformat("2026-03-02T02:30:00+00:00"),
                  fuso_min=-180, duracao_s=1800.0)
    session.add_all([a, SemanaPadrao(atleta_id=atleta.id, vigente_desde=date(2026, 3, 1), definido_por="atleta",
                                     itens=[SemanaPadraoItem(dia_semana=7, modalidade="corrida", tipo_treino="longo")])])
    session.commit()
    # vigente_desde = domingo 01/03; a atividade e de domingo 01/03 local: reaplica a partir de 01/03 e pega
    assert reaplicar_tipos(session, atleta.id, date(2026, 3, 1)) == 1
    assert (a.tipo_treino, a.tipo_origem) == ("longo", "semana_padrao")
    # a partir de segunda 02/03 ela ja nao entra (data local 01/03)
    a.tipo_treino = a.tipo_origem = a.tipo_versao = None
    session.commit()
    assert reaplicar_tipos(session, atleta.id, date(2026, 3, 2)) == 0
    assert a.tipo_treino is None


def test_pendente_com_sugestao_antiga_sem_versao_e_volta_a_falso_depois(session):
    atleta, por_id = _carregar(session)
    aplicar_tipos(session, atleta.id)
    session.commit()
    assert reclassificacao_pendente(session, atleta.id) is False
    a = por_id["2026-01-16/cor1"]  # leve por sugestao
    assert a.tipo_origem == "sugestao"
    a.tipo_versao = None  # como as linhas anteriores a 0011
    session.commit()
    assert reclassificacao_pendente(session, atleta.id) is True
    a.tipo_versao = "tipo_treino@0"
    session.commit()
    assert reclassificacao_pendente(session, atleta.id) is True
    # e a semana_padrao de natacao (sem corrida) tambem conta
    aplicar_tipos(session, atleta.id)
    session.commit()
    assert reclassificacao_pendente(session, atleta.id) is False
    n = por_id["2026-03-02/nat1"]
    assert n.tipo_origem == "semana_padrao"
    n.tipo_versao = "tipo_treino@0"
    session.commit()
    assert reclassificacao_pendente(session, atleta.id) is True
    # o filtro de periodo vale: a atividade e de marco
    assert reclassificacao_pendente(session, atleta.id, fim=date(2026, 2, 28)) is False


def test_tipo_confirmado_e_protegidos_nao_deixam_pendente(session):
    atleta, por_id = _carregar(session)
    aplicar_tipos(session, atleta.id)
    a = por_id["2026-01-16/cor1"]
    a.tipo_confirmado, a.tipo_versao = True, None  # confirmado pelo atleta: a regra nunca o reescreve
    session.commit()
    assert reclassificacao_pendente(session, atleta.id) is False


def test_serie_de_tiros_nao_le_o_tipo_treino(session):
    """A serie de tiros e dos blocos: um plano que manda `leve` no dia dos tiros muda o tipo, nao a serie (ADR 0011)."""
    atleta = Atleta(nome="F")
    session.add(atleta)
    session.flush()
    for dia in (3, 10, 17):  # tres tercas de marco/2026
        a = Atividade(atleta_id=atleta.id, fonte="x", fonte_id=str(dia), modalidade="corrida", fuso_min=-180, distancia_m=9000.0,
                      inicio=datetime(2026, 3, dia, 10), duracao_s=3000.0)
        session.add(a)
        _blocos(a, "tiros", 6)
    session.commit()
    antes = serie_tiros_1km(session, atleta.id)
    session.add(SemanaPadrao(atleta_id=atleta.id, vigente_desde=date(2026, 1, 5), definido_por="atleta",
                             itens=[SemanaPadraoItem(dia_semana=2, modalidade="corrida", tipo_treino="leve")]))
    session.commit()
    aplicar_tipos(session, atleta.id)
    session.commit()
    ativs = session.scalars(select(Atividade)).all()
    assert {(a.tipo_treino, a.tipo_origem, a.tipo_divergencia) for a in ativs} == {("leve", "semana_padrao", "tem_tiros")}
    assert serie_tiros_1km(session, atleta.id) == antes


def test_classificar_atividades_aplica_o_plano_e_nao_apaga_o_tipo_de_quem_nao_e_corrida(session):
    """`classificar_atividades` (importacao e worker.reclassificar) passa pelo mesmo `aplicar_tipos`."""
    atleta = Atleta(nome="F")
    session.add(atleta)
    session.flush()
    nat = Atividade(atleta_id=atleta.id, fonte="x", fonte_id="n", modalidade="natacao", fuso_min=-180,
                    inicio=datetime(2026, 3, 2, 10), duracao_s=2400.0)  # segunda
    session.add_all([nat, SemanaPadrao(atleta_id=atleta.id, vigente_desde=date(2026, 3, 1), definido_por="atleta",
                                       itens=[SemanaPadraoItem(dia_semana=1, modalidade="natacao", tipo_treino="leve")])])
    session.commit()
    classificar_atividades(session, atleta.id)
    assert _linha(nat) == ("leve", "semana_padrao", "tipo_treino@1", None)
