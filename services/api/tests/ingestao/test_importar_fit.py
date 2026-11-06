"""Upload de FIT (issue #94, ADR 0006) com os FIT sinteticos da #93. `FIT_DIR` sempre em `tmp_path`."""

import hashlib
import re
from pathlib import Path

import pytest
from app.config import RAIZ_REPOSITORIO, pasta_fit
from app.db.models import Atividade, Atleta
from app.ingestao import fit_guardado
from app.ingestao.fit_guardado import AtletaInexistente, apagar_do_atleta
from app.ingestao.garmin.fit import ler_fit
from app.ingestao.importacao import (
    TAMANHO_MAX_FIT,
    FitGrande,
    FitInvalido,
    FitNaoEAtividade,
    importar,
    importar_fit,
)
from app.servicos.evolucao_tiros import serie_tiros_1km
from sqlalchemy import func, select

RAIZ = Path(__file__).resolve().parents[4]
FITS = RAIZ / "tests" / "fixtures" / "garmin" / "fit"
ZIP = RAIZ / "tests" / "fixtures" / "garmin" / "exportacao_minima.zip"


def _fit(nome: str) -> bytes:
    return (FITS / nome).read_bytes()


def _rel(atleta_id: int, conteudo: bytes) -> str:
    return f"{atleta_id}/{hashlib.sha256(conteudo).hexdigest()}.fit"


@pytest.fixture
def atleta(session):
    a = Atleta(nome="Atleta Ficticio")
    session.add(a)
    session.commit()
    return a


@pytest.fixture
def pasta(tmp_path):
    return tmp_path / "fit"


def _n_atividades(session) -> int:
    return session.scalar(select(func.count()).select_from(Atividade))


def _arquivos(pasta: Path) -> list[Path]:
    return sorted(pasta.rglob("*.fit")) if pasta.exists() else []


# ---------- insercao, guarda e serie ----------

def test_intervalado_e_inserido_guardado_e_entra_na_serie(session, atleta, pasta):
    dados = _fit("upload_intervalado_5x1km.fit")
    r = importar_fit(session, atleta.id, dados, pasta)
    assert r.resultado == "inserida" and r.avisos == []
    ativ = session.get(Atividade, r.atividade_id)
    assert (ativ.fonte, ativ.modalidade, ativ.subtipo) == ("fit_upload", "corrida", None)
    assert ativ.fonte_id.startswith("fit-") and ativ.fuso_min is None
    assert (ativ.duracao_s, ativ.distancia_m) == (3135, 10100)
    assert len(ativ.segmentos) == 11
    # guarda: <atleta_id>/<sha256>.fit, caminho relativo em arquivo_bruto, conteudo intacto
    esperado = _rel(atleta.id, dados)
    assert ativ.arquivo_bruto == esperado
    assert _arquivos(pasta) == [pasta / esperado]
    assert (pasta / esperado).read_bytes() == dados
    # a classificacao rodou: a serie da Meta 2 ganha o ponto (pace 246,0 s/km; FC 210282 / 1230)
    (ponto,) = serie_tiros_1km(session, atleta.id)
    assert ponto.n_tiros == 5
    assert ponto.pace_s_km == pytest.approx(246.0)
    assert ponto.fc_media == pytest.approx(210282 / 1230)


def test_nome_do_arquivo_nao_tem_dado_pessoal(session, atleta, pasta):
    importar_fit(session, atleta.id, _fit("upload_intervalado_5x1km.fit"), pasta)
    (arq,) = _arquivos(pasta)
    assert re.fullmatch(r"\d+/[0-9a-f]{64}\.fit", arq.relative_to(pasta).as_posix())
    assert "ficticio" not in arq.as_posix().lower()


def test_reenvio_do_mesmo_arquivo_e_ignorado_e_nao_regrava(session, atleta, pasta):
    dados = _fit("upload_intervalado_5x1km.fit")
    primeiro = importar_fit(session, atleta.id, dados, pasta)
    (arq,) = _arquivos(pasta)
    mtime = arq.stat().st_mtime_ns
    segundo = importar_fit(session, atleta.id, dados, pasta)
    assert segundo.resultado == "ignorada" and segundo.atividade_id == primeiro.atividade_id
    assert _n_atividades(session) == 1
    assert _arquivos(pasta) == [arq] and arq.stat().st_mtime_ns == mtime


def test_reenvio_com_o_arquivo_apagado_regrava_e_conta_como_atualizada(session, atleta, pasta):
    dados = _fit("upload_intervalado_5x1km.fit")
    importar_fit(session, atleta.id, dados, pasta)
    (arq,) = _arquivos(pasta)
    arq.unlink()
    r = importar_fit(session, atleta.id, dados, pasta)
    assert r.resultado == "atualizada" and _arquivos(pasta) == [arq]
    assert _n_atividades(session) == 1


@pytest.mark.parametrize("nome,modalidade,subtipo", [
    ("upload_rodagem_6km.fit", "corrida", None),
    ("upload_esteira_4x1km.fit", "corrida", "esteira"),
    ("upload_natacao_400m.fit", "natacao", "piscina"),
])
def test_rodagem_esteira_e_natacao_ficam_no_banco_e_fora_da_serie(session, atleta, pasta, nome, modalidade, subtipo):
    importar_fit(session, atleta.id, _fit("upload_intervalado_5x1km.fit"), pasta)
    r = importar_fit(session, atleta.id, _fit(nome), pasta)
    assert r.resultado == "inserida"
    ativ = session.get(Atividade, r.atividade_id)
    assert (ativ.modalidade, ativ.subtipo) == (modalidade, subtipo)
    assert ativ.arquivo_bruto == _rel(atleta.id, _fit(nome))
    assert [p.atividade_id for p in serie_tiros_1km(session, atleta.id)] != [] and \
        r.atividade_id not in [p.atividade_id for p in serie_tiros_1km(session, atleta.id)]
    assert len(serie_tiros_1km(session, atleta.id)) == 1  # so o intervalado


# ---------- invalidos: nada no banco nem em FIT_DIR ----------

@pytest.mark.parametrize("nome,erro", [
    ("upload_truncado.fit", FitInvalido),
    ("upload_nao_atividade.fit", FitNaoEAtividade),
])
def test_fit_invalido_ou_que_nao_e_atividade_nao_grava_nada(session, atleta, pasta, nome, erro):
    with pytest.raises(erro) as e:
        importar_fit(session, atleta.id, _fit(nome), pasta)
    assert type(e.value) is erro
    assert _n_atividades(session) == 0 and not pasta.exists()


def test_lixo_que_nao_e_fit(session, atleta, pasta):
    with pytest.raises(FitInvalido):
        importar_fit(session, atleta.id, b"isto nao e um fit", pasta)
    assert _n_atividades(session) == 0 and not pasta.exists()


def test_arquivo_grande_demais(session, atleta, pasta):
    with pytest.raises(FitGrande):
        importar_fit(session, atleta.id, b"\0" * (TAMANHO_MAX_FIT + 1), pasta)
    assert _n_atividades(session) == 0 and not pasta.exists()


def test_atleta_inexistente(session, pasta):
    with pytest.raises(AtletaInexistente):
        importar_fit(session, 9999, _fit("upload_intervalado_5x1km.fit"), pasta)
    assert _n_atividades(session) == 0 and not pasta.exists()


def test_falha_no_commit_nao_deixa_arquivo_nem_atividade(session, atleta, pasta, monkeypatch):
    def quebra():
        raise RuntimeError("banco caiu")
    monkeypatch.setattr(session, "commit", quebra)
    with pytest.raises(RuntimeError):
        importar_fit(session, atleta.id, _fit("upload_intervalado_5x1km.fit"), pasta)
    monkeypatch.undo()
    assert _n_atividades(session) == 0 and _arquivos(pasta) == []


# ---------- identidade: regra dos 60 s nos dois sentidos ----------

def test_exportacao_e_depois_upload_da_mesma_atividade_nao_duplica(session, pasta):
    importar(session, ZIP, "Ana")
    atleta = session.scalars(select(Atleta)).one()
    antes = _n_atividades(session)
    original = session.scalars(select(Atividade).where(Atividade.fonte_id == "1000000001")).one()
    inicio, duracao = original.inicio, original.duracao_s
    dados = _fit("upload_mesma_atividade_1000000001.fit")
    r = importar_fit(session, atleta.id, dados, pasta)
    assert r.resultado == "atualizada" and r.atividade_id == original.id
    assert _n_atividades(session) == antes
    session.refresh(original)
    # a linha da exportacao nao muda de fonte nem de campos; so aponta para o FIT guardado
    assert (original.fonte, original.fonte_id) == ("garmin_export", "1000000001")
    assert (original.inicio, original.duracao_s) == (inicio, duracao)
    assert original.fuso_min == -180
    assert original.arquivo_bruto == _rel(atleta.id, dados)
    assert len(original.segmentos) == 13
    # reenviar: nada muda
    assert importar_fit(session, atleta.id, dados, pasta).resultado == "ignorada"


def test_upload_e_depois_exportacao_adota_a_linha_sem_duplicar(session, atleta, pasta):
    dados = _fit("upload_mesma_atividade_1000000001.fit")
    up = importar_fit(session, atleta.id, dados, pasta)
    assert up.resultado == "inserida"
    session.get(Atleta, atleta.id).nome = "Ana"
    session.commit()
    rel = importar(session, ZIP, "Ana")  # o atleta "Ana" e o mesmo
    assert _n_atividades(session) == 4 + 1  # as 5 da exportacao; a do upload foi adotada, nao duplicada
    assert (rel.inseridas, rel.atualizadas) == (4, 1)
    linha = session.get(Atividade, up.atividade_id)
    assert (linha.fonte, linha.fonte_id) == ("garmin_export", "1000000001")
    assert linha.fuso_min == -180  # veio do JSON da exportacao
    assert linha.arquivo_bruto == _rel(atleta.id, dados)  # a exportacao mantem o FIT guardado
    assert _arquivos(pasta) == [pasta / _rel(atleta.id, dados)]
    # reimportar a exportacao continua idempotente
    rel2 = importar(session, ZIP, "Ana")
    assert (rel2.inseridas, rel2.atualizadas, rel2.ignoradas) == (0, 0, 5)
    assert _n_atividades(session) == 5


def test_outra_modalidade_a_20_s_nao_casa(session, atleta, pasta):
    importar_fit(session, atleta.id, _fit("empate_candidata_a.fit"), pasta)
    session.scalars(select(Atividade)).one().modalidade = "ciclismo"
    session.commit()
    r = importar_fit(session, atleta.id, _fit("empate_chegada_equidistante.fit"), pasta)  # corrida, 20 s depois
    assert r.resultado == "inserida" and r.avisos == []
    assert _n_atividades(session) == 2


def test_exportacao_de_outro_atleta_nao_casa(session, pasta):
    outra = Atleta(nome="Outra Pessoa")
    session.add(outra)
    session.commit()
    importar_fit(session, outra.id, _fit("upload_mesma_atividade_1000000001.fit"), pasta)
    importar(session, ZIP, "Ana")  # atleta diferente: as 5 entram, sem adotar a linha da outra
    assert _n_atividades(session) == 6


def _insere_candidatas(session, atleta_id):
    a, b = ler_fit(_fit("empate_candidata_a.fit")), ler_fit(_fit("empate_candidata_b.fit"))
    linhas = []
    for nome, fit in (("a", a), ("b", b)):  # ids crescentes: A primeiro
        linha = Atividade(atleta_id=atleta_id, fonte="teste", fonte_id=f"cand-{nome}", modalidade="corrida",
                          inicio=fit.inicio, duracao_s=fit.duracao_s, distancia_m=fit.distancia_m)
        session.add(linha)
        session.flush()
        linhas.append(linha)
    session.commit()
    return linhas


def test_empate_equidistante_usa_o_menor_id_com_aviso(session, atleta, pasta):
    a, b = _insere_candidatas(session, atleta.id)
    assert a.id < b.id
    r = importar_fit(session, atleta.id, _fit("empate_chegada_equidistante.fit"), pasta)  # 20 s de A e de B
    assert r.resultado == "atualizada" and r.atividade_id == a.id
    assert any(f"candidatas {a.id}, {b.id}" in av and f"usada a {a.id}" in av for av in r.avisos)
    assert _n_atividades(session) == 2


def test_empate_vale_o_inicio_mais_proximo(session, atleta, pasta):
    a, b = _insere_candidatas(session, atleta.id)
    r = importar_fit(session, atleta.id, _fit("empate_chegada_mais_perto_de_b.fit"), pasta)  # 30 s de A, 10 s de B
    assert r.atividade_id == b.id and any(f"usada a {b.id}" in av for av in r.avisos)
    assert _n_atividades(session) == 2


def test_uma_candidata_so_nao_gera_aviso(session, atleta, pasta):
    importar_fit(session, atleta.id, _fit("empate_candidata_a.fit"), pasta)
    r = importar_fit(session, atleta.id, _fit("empate_chegada_equidistante.fit"), pasta)  # 20 s depois de A
    assert r.resultado == "atualizada" and r.avisos == []
    assert _n_atividades(session) == 1


# ---------- FIT substituido ----------

def test_fit_substituido_e_apagado_quando_fica_orfao(session, atleta, pasta):
    velho, novo = _fit("empate_candidata_a.fit"), _fit("empate_chegada_equidistante.fit")
    r1 = importar_fit(session, atleta.id, velho, pasta)
    r2 = importar_fit(session, atleta.id, novo, pasta)  # casa com a mesma atividade (20 s)
    assert r2.atividade_id == r1.atividade_id and r2.resultado == "atualizada"
    assert session.get(Atividade, r1.atividade_id).arquivo_bruto == _rel(atleta.id, novo)
    assert _arquivos(pasta) == [pasta / _rel(atleta.id, novo)]  # o velho saiu da pasta


def test_fit_substituido_fica_se_outra_atividade_o_referencia(session, atleta, pasta):
    velho, novo = _fit("empate_candidata_a.fit"), _fit("empate_chegada_equidistante.fit")
    r1 = importar_fit(session, atleta.id, velho, pasta)
    outra = Atividade(atleta_id=atleta.id, fonte="teste", fonte_id="x", modalidade="outra",
                      inicio=ler_fit(velho).inicio.replace(year=2024), duracao_s=1.0,
                      arquivo_bruto=_rel(atleta.id, velho))
    session.add(outra)
    session.commit()
    importar_fit(session, atleta.id, novo, pasta)
    assert {p.name for p in _arquivos(pasta)} == {
        _rel(atleta.id, velho).split("/")[1], _rel(atleta.id, novo).split("/")[1]}
    assert r1.atividade_id != outra.id


def test_erro_ao_apagar_o_antigo_vira_aviso(session, atleta, pasta, monkeypatch):
    velho, novo = _fit("empate_candidata_a.fit"), _fit("empate_chegada_equidistante.fit")
    importar_fit(session, atleta.id, velho, pasta)

    def nao_apaga(*a, **k):
        raise PermissionError("sem permissao")
    monkeypatch.setattr(fit_guardado, "remover", nao_apaga)
    r = importar_fit(session, atleta.id, novo, pasta)
    assert r.resultado == "atualizada" and any("não foi possível apagar" in av for av in r.avisos)


# ---------- apagar ----------

def test_apagar_remove_arquivos_e_limpa_arquivo_bruto_sem_apagar_atividades(session, atleta, pasta):
    outro = Atleta(nome="Outra Pessoa")
    session.add(outro)
    session.commit()
    importar_fit(session, atleta.id, _fit("upload_intervalado_5x1km.fit"), pasta)
    importar_fit(session, atleta.id, _fit("upload_rodagem_6km.fit"), pasta)
    importar_fit(session, outro.id, _fit("upload_natacao_400m.fit"), pasta)
    assert apagar_do_atleta(session, atleta.id, pasta) == (2, 2)
    assert _n_atividades(session) == 3
    assert [p.parent.name for p in _arquivos(pasta)] == [str(outro.id)]  # o do outro atleta ficou
    assert all(a.arquivo_bruto is None for a in session.scalars(select(Atividade).where(Atividade.atleta_id == atleta.id)))
    assert session.scalars(select(Atividade).where(Atividade.atleta_id == outro.id)).one().arquivo_bruto is not None
    assert len(serie_tiros_1km(session, atleta.id)) == 1  # a serie continua
    assert apagar_do_atleta(session, atleta.id, pasta) == (0, 0)  # idempotente


def test_apagar_nao_mexe_em_caminho_de_exportacao(session, pasta):
    importar(session, ZIP, "Ana")
    atleta = session.scalars(select(Atleta)).one()
    antes = {a.id: a.arquivo_bruto for a in session.scalars(select(Atividade))}
    assert apagar_do_atleta(session, atleta.id, pasta) == (0, 0)
    assert {a.id: a.arquivo_bruto for a in session.scalars(select(Atividade))} == antes


def test_apagar_atleta_inexistente(session, pasta):
    with pytest.raises(AtletaInexistente):
        apagar_do_atleta(session, 9999, pasta)


def test_apagar_cli(session, atleta, pasta, monkeypatch, capsys):
    import app.db.session as sess
    from worker import apagar_fit
    importar_fit(session, atleta.id, _fit("upload_intervalado_5x1km.fit"), pasta)
    monkeypatch.setattr(sess, "SessionLocal", lambda: session.__class__(session.get_bind()))
    monkeypatch.setattr(fit_guardado, "pasta_fit", lambda valor=None: pasta)
    assert apagar_fit.main(["--atleta-id", str(atleta.id)]) == 0
    assert capsys.readouterr().out.strip() == (
        f"apagados 1 arquivos; arquivo_bruto limpo em 1 atividades do atleta {atleta.id}")
    assert apagar_fit.main(["--atleta-id", "9999"]) == 1
    assert "não encontrado" in capsys.readouterr().err
    assert _arquivos(pasta) == []


# ---------- configuracao e .gitignore ----------

def test_pasta_padrao_esta_no_gitignore_e_fora_do_codigo():
    padrao = pasta_fit()
    assert padrao == RAIZ_REPOSITORIO / "dados-upload" / "fit"
    linhas = (RAIZ_REPOSITORIO / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert "dados-upload/" in linhas
    assert "FIT_DIR=dados-upload/fit" in (RAIZ_REPOSITORIO / ".env.example").read_text(encoding="utf-8")


def test_pasta_fit_relativa_conta_da_raiz_e_absoluta_fica(tmp_path):
    assert pasta_fit("outra/pasta") == RAIZ_REPOSITORIO / "outra" / "pasta"
    assert pasta_fit(tmp_path) == tmp_path


def test_falha_na_deteccao_de_esforcos_nao_derruba_a_importacao(session, atleta, pasta, monkeypatch, caplog):
    """#168: um unico ponto de deteccao (classificar_atividades), tolerante a erro: a atividade entra, fica o aviso."""
    def quebra(*a, **k):
        raise RuntimeError("falha simulada")

    monkeypatch.setattr("app.servicos.evolucao_tiros.detectar_esforcos", quebra)
    r = importar_fit(session, atleta.id, _fit("upload_intervalado_5x1km.fit"), pasta)
    assert r.resultado == "inserida"
    assert session.get(Atividade, r.atividade_id) is not None
    assert "esforcos nao detectados" in caplog.text
