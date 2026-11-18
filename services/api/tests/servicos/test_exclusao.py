"""Exclusao de conta e dos dados do atleta (issue #505, ADR 0016, item 9). Tudo sintetico.

O teste central percorre TODAS as tabelas do modelo: para cada uma que depende do atleta (por chave estrangeira, direta ou pelos filhos),
cria uma linha para o atleta A e uma para o atleta B, apaga o A e prova que nada do A sobrou e o B ficou inteiro. Tabela nova sem
tratamento em `exclusao.TABELAS_APAGADAS` (ou sem ser declarada em `TABELAS_QUE_FICAM`) faz o teste falhar.
"""

import json
import re
from datetime import date, datetime, timedelta, timezone

import pytest
from app.db.base import Base
from app.db.models import Assessoria, Atividade, Atleta, Conta, Professor, Sessao, TentativaLogin
from app.servicos import conta as svc_conta
from app.servicos import exclusao as ex
from sqlalchemy import Boolean, Date, DateTime, Float, Integer, JSON, String, Text, select, func
from sqlalchemy.orm import Session

AGORA = datetime(2026, 11, 18, 12, 0, tzinfo=timezone.utc)

# Valores que o filler generico nao adivinha (CHECKs que ligam colunas). Chave: (tabela, coluna).
AJUSTES = {
    ("carga_atividade", "estado"): "sem_carga",
    ("feedback_treino", "estado"): "sem_feedback",
    ("rotulo_transicao", "origem"): "atleta",
    ("checkin_treino", "nada_a_relatar"): True,
    ("checkin_treino", "pse"): 5,
    ("checkin_treino", "sensacao"): 3,
    ("semana_padrao_item", "dia_semana"): 1,
    ("limiar_atleta", "valor"): 100.0,
    ("recuperacao_dia", "sono_s"): 25000,
    ("consentimento_evento", "acao"): "aceito",
    ("atividade", "modalidade"): "corrida",
}
EXTRAS = {  # colunas anulaveis que o CHECK exige preenchidas
    "carga_atividade": {"motivo": "sem_fc"},
    "feedback_treino": {"motivo": "provedor_erro"},
    "rotulo_transicao": {},
}


def _valores_permitidos(tabela, coluna):
    """Primeiro valor de um CHECK `coluna IN ('a', 'b')` da tabela; None se nao houver."""
    for c in tabela.constraints:
        txt = str(getattr(c, "sqltext", ""))
        m = re.search(rf"\b{coluna}\b IN \(\s*'([^']+)'", txt)
        if m and f"{coluna} IS NULL OR" not in txt.split(m.group(0))[0][-40:]:
            return m.group(1)
        if m:
            return m.group(1)
    return None


def _linha(session, tabela, ids, **fixos):
    """Insere uma linha minima valida na tabela e devolve o id. `ids` mapeia tabela -> id da linha pai ja criada para o mesmo atleta."""
    valores = {}
    for col in tabela.columns:
        if col.name in fixos:
            valores[col.name] = fixos[col.name]
            continue
        if col.primary_key and isinstance(col.type, Integer) and not col.foreign_keys:
            continue
        if col.foreign_keys:
            alvo = list(col.foreign_keys)[0].column.table.name
            if alvo in ids:
                valores[col.name] = ids[alvo]
                continue
        chave = (tabela.name, col.name)
        if chave in AJUSTES:
            valores[col.name] = AJUSTES[chave]
            continue
        if col.nullable or col.server_default is not None or col.default is not None:
            continue
        permitido = _valores_permitidos(tabela, col.name)
        t = col.type
        if permitido is not None:
            valores[col.name] = permitido
        elif isinstance(t, Boolean):
            valores[col.name] = False
        elif isinstance(t, Integer):
            valores[col.name] = 1
        elif isinstance(t, Float):
            valores[col.name] = 1.0
        elif isinstance(t, DateTime):
            valores[col.name] = AGORA
        elif isinstance(t, Date):
            valores[col.name] = date(2026, 11, 1)
        elif isinstance(t, JSON):
            valores[col.name] = {}
        elif isinstance(t, (String, Text)):
            valores[col.name] = "x"
        else:
            raise AssertionError(f"tipo nao tratado: {tabela.name}.{col.name} {t}")
    valores.update(EXTRAS.get(tabela.name, {}))
    res = session.execute(tabela.insert().values(**valores))
    session.flush()
    return res.inserted_primary_key[0] if res.inserted_primary_key else None


def _dependentes_de_atleta():
    """Tabelas alcancaveis por chave estrangeira a partir de `atleta` (direta ou pelos filhos), na ordem de criacao."""
    tem = {"atleta"}
    mudou = True
    while mudou:
        mudou = False
        for t in Base.metadata.sorted_tables:
            if t.name in tem:
                continue
            if any(fk.column.table.name in tem for c in t.columns for fk in c.foreign_keys):
                tem.add(t.name)
                mudou = True
    return [t for t in Base.metadata.sorted_tables if t.name in tem and t.name != "atleta"]


def _povoar(session, atleta_id, professor_id, email):
    """Uma linha em cada tabela que depende do atleta. Devolve {tabela: id}."""
    ids = {"atleta": atleta_id, "professor": professor_id}
    for t in _dependentes_de_atleta():
        fixos = {}
        if t.name == "conta":
            fixos = {"email": email, "senha_hash": "hash-sintetico", "professor_id": None}
        if t.name == "atividade":
            fixos = {"fonte_id": f"f{atleta_id}", "tipo_confirmado_por": professor_id}
        if t.name == "sessao":
            fixos = {"token_hash": f"{atleta_id:064d}"}
        if t.name == "tentativa_login":
            continue
        ids[t.name] = _linha(session, t, ids, **fixos)
    # tentativa de login do e-mail da conta (so o hash dele)
    session.add(TentativaLogin(email_hash=svc_conta.hash_do_email(email), ocorrida_em=AGORA, ok=False))
    session.flush()
    return ids


def _contagens(session):
    return {t.name: session.scalar(select(func.count()).select_from(t)) for t in Base.metadata.sorted_tables}


@pytest.fixture
def dois_atletas(session):
    ass = Assessoria(nome="Assessoria Teste")
    session.add(ass)
    session.flush()
    prof = Professor(nome="Paulo Teste", assessoria_id=ass.id)
    a, b = Atleta(nome="Ana Teste", assessoria_id=ass.id), Atleta(nome="Bia Teste", assessoria_id=ass.id)
    session.add_all([prof, a, b])
    session.flush()
    ida = _povoar(session, a.id, prof.id, "ana@exemplo.com")
    idb = _povoar(session, b.id, prof.id, "bia@exemplo.com")
    session.commit()
    return a.id, b.id, prof.id


def test_todas_as_tabelas_estao_tratadas_ou_declaradas_que_ficam():
    todas = {t.name for t in Base.metadata.sorted_tables}
    tratadas = set(ex.TABELAS_APAGADAS)
    assert tratadas | ex.TABELAS_QUE_FICAM == todas, f"tabela nova sem tratamento: {sorted(todas - tratadas - ex.TABELAS_QUE_FICAM)}"
    assert not (tratadas & ex.TABELAS_QUE_FICAM)
    dependentes = {t.name for t in _dependentes_de_atleta()} | {"atleta"}
    # tudo que depende do atleta por chave estrangeira esta na lista (tentativa_login entra pelo hash do e-mail, nao por FK)
    assert dependentes <= tratadas
    assert tratadas - dependentes == {"tentativa_login"}


def test_a_ordem_de_apagar_respeita_as_chaves_estrangeiras():
    pos = {n: i for i, n in enumerate(ex.TABELAS_APAGADAS)}
    for t in Base.metadata.sorted_tables:
        if t.name not in pos:
            continue
        for c in t.columns:
            for fk in c.foreign_keys:
                pai = fk.column.table.name
                if pai in pos:
                    assert pos[t.name] < pos[pai], f"{t.name} deve sair antes de {pai}"


def test_excluir_apaga_tudo_do_atleta_e_nada_do_outro(session, dois_atletas):
    a, b, prof = dois_atletas
    antes = _contagens(session)
    # o filler povoou todas as tabelas que dependem do atleta, para os dois
    for t in _dependentes_de_atleta():
        assert antes[t.name] >= 2, f"o teste nao povoou {t.name}"
    r = ex.excluir_atleta(session, a)
    depois = _contagens(session)
    for t in ex.TABELAS_APAGADAS:
        esperado = antes[t] - r.linhas.get(t, 0)
        assert depois[t] == esperado
    # nada do A sobrou, em nenhuma tabela com atleta_id e nas que pendem dele
    for t in Base.metadata.sorted_tables:
        if "atleta_id" in t.columns:
            assert session.scalar(select(func.count()).select_from(t).where(t.c.atleta_id == a)) == 0, t.name
    assert session.get(Atleta, a) is None
    assert session.scalars(select(Conta).where(Conta.email == "ana@exemplo.com")).first() is None
    assert session.scalar(select(func.count()).select_from(TentativaLogin).where(
        TentativaLogin.email_hash == svc_conta.hash_do_email("ana@exemplo.com"))) == 0
    # o outro atleta ficou inteiro e o professor e a assessoria tambem
    for t in _dependentes_de_atleta():
        assert depois[t.name] == antes[t.name] - r.linhas.get(t.name, 0)
        assert depois[t.name] >= 1
    assert session.get(Atleta, b) is not None and session.get(Professor, prof) is not None
    assert depois["assessoria"] == antes["assessoria"] and depois["professor"] == antes["professor"]
    assert session.scalars(select(Conta).where(Conta.email == "bia@exemplo.com")).first() is not None
    assert r.total > 0


def test_excluir_e_idempotente_no_sentido_de_nao_achar_de_novo(session, dois_atletas):
    a, _, _ = dois_atletas
    ex.excluir_atleta(session, a)
    with pytest.raises(ex.AtletaNaoEncontrado):
        ex.excluir_atleta(session, a)


def test_excluir_atleta_inexistente(session):
    with pytest.raises(ex.AtletaNaoEncontrado):
        ex.excluir_atleta(session, 999)


def test_os_fit_guardados_do_atleta_saem_e_os_do_outro_ficam(session, dois_atletas, tmp_path):
    a, b, _ = dois_atletas
    for quem in (a, b):
        pasta = tmp_path / str(quem)
        pasta.mkdir()
        (pasta / "um.fit").write_bytes(b"sintetico")
    r = ex.excluir_atleta(session, a, tmp_path)
    assert r.arquivos_fit == 1 and not (tmp_path / str(a)).exists() and (tmp_path / str(b) / "um.fit").is_file()


def test_o_registro_guarda_so_id_e_data(tmp_path):
    reg = tmp_path / "fora" / "exclusoes.jsonl"
    ex.registrar_exclusao(reg, 7, AGORA)
    linha = json.loads(reg.read_text(encoding="utf-8"))
    assert linha == {"atleta_id": 7, "data": "2026-11-18"}
    assert ex.ler_registro(reg) == [7] and ex.ler_registro(tmp_path / "nao-existe") == []


def test_reaplicar_apaga_de_novo_quem_voltou_com_a_restauracao(session, dois_atletas, tmp_path):
    a, b, _ = dois_atletas
    reg = tmp_path / "exclusoes.jsonl"
    ex.registrar_exclusao(reg, a, AGORA)
    ex.registrar_exclusao(reg, 12345, AGORA)  # id que nao existe neste banco: ignorado
    # "o backup antigo ainda tem o atleta A": reaplicar apaga; so ele
    assert ex.reaplicar_exclusoes(session, reg) == [a]
    assert session.get(Atleta, a) is None and session.get(Atleta, b) is not None
    assert ex.reaplicar_exclusoes(session, reg) == []  # segunda vez: nada a fazer


def test_nada_da_conta_vai_a_saida_ou_ao_log(session, dois_atletas, caplog, capsys, tmp_path):
    import logging

    from worker import excluir_conta as cmd

    a, _, _ = dois_atletas
    caplog.set_level(logging.DEBUG)

    class Args:
        atleta, confirmar, registro, fit_dir = a, a, str(tmp_path / "e.jsonl"), None

    assert cmd.excluir(session, Args) == 0
    saida = capsys.readouterr().out + " ".join(r.getMessage() for r in caplog.records)
    assert "Ana Teste" not in saida and "ana@exemplo.com" not in saida
    assert "atividade: apagadas=1" in saida and "conta: apagadas=1" in saida


def test_confirmacao_errada_nao_apaga(session, dois_atletas, tmp_path, capsys):
    from worker import excluir_conta as cmd

    a, b, _ = dois_atletas

    class Args:
        atleta, confirmar, registro, fit_dir = a, b, str(tmp_path / "e.jsonl"), None

    assert cmd.excluir(session, Args) == 1
    assert session.get(Atleta, a) is not None and not (tmp_path / "e.jsonl").exists()
