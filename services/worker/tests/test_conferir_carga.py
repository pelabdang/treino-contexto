"""worker.conferir_carga (issue #144) com as fixtures de ``tests/fixtures/garmin/carga/``.

A carga do Garmin é inventada, com relação conhecida com a nossa (oráculo da #137, ``SERIE``): aguda = 3 x ATL + 7,
crônica = 2 x CTL, razão = 2 x (ATL/CTL). Relação monotônica: Spearman 1 em tudo. Os dias sem carga do oráculo
(06/03 natação, 08/03 esteira sem FC, 12/03 cobertura, 14/03 sem pace, 15/03 natação em águas abertas) saem da comparação:
43 dias de 05/03 a 16/04, 5 descartados, 38 comparados.
"""

import csv
import importlib.util
import os
import sys
from datetime import date
from pathlib import Path

import pytest
from app.db import models  # noqa: F401
from app.db.base import Base
from app.db.models import Atleta, CargaGarminDia
from app.ingestao.importacao import importar
from app.ingestao.saude import importar_saude
from app.servicos.carga import calcular_carga_do_atleta
from app.servicos.serie_carga_banco import serie_carga_do_atleta
from sqlalchemy import create_engine, delete, select
from sqlalchemy.orm import Session

from worker import conferir_carga
from worker.conferir_carga import AtletaInexistente, conferir

RAIZ = Path(__file__).resolve().parents[3]
ZIP = RAIZ / "tests" / "fixtures" / "garmin" / "carga" / "exportacao_carga.zip"


@pytest.fixture
def session():
    eng = create_engine(os.environ.get("TEST_DATABASE_URL", "sqlite://"))
    Base.metadata.drop_all(eng)
    Base.metadata.create_all(eng)
    with Session(eng) as s:
        yield s
    Base.metadata.drop_all(eng)
    eng.dispose()


def _atleta(session, garmin_relacionado=True) -> int:
    importar(session, str(ZIP), "Ana")
    importar_saude(session, str(ZIP), "Ana")
    atleta_id = session.scalars(select(Atleta)).one().id
    calcular_carga_do_atleta(session, atleta_id)
    # a fixture de saúde pode trazer carga do Garmin própria: troca pela série inventada, com relação conhecida
    session.execute(delete(CargaGarminDia).where(CargaGarminDia.atleta_id == atleta_id))
    if garmin_relacionado:
        for d in serie_carga_do_atleta(session, atleta_id).serie.dias:
            session.add(CargaGarminDia(atleta_id=atleta_id, origem="garmin_export", dia=d.dia,
                                       carga_aguda=3 * d.atl + 7, carga_cronica=2 * d.ctl,
                                       razao=2 * d.atl / d.ctl, versao_leitura="teste@1"))
    session.commit()
    return atleta_id


def _ler(caminho):
    with open(caminho, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def test_relacao_conhecida_da_spearman_1_e_cobertura_declarada(session, tmp_path):
    atleta_id = _atleta(session)
    (dia_csv, resumo_csv, cob_csv), c, sem_linha = conferir(session, atleta_id, tmp_path)
    assert sem_linha == 0
    k = c.cobertura
    assert (k.dias_nossa, k.dias_garmin, k.dias_em_comum, k.descartados_sem_carga, k.dias_comparados) == (43, 43, 43, 5, 38)

    resumo = {(r["regra"], r["grupo"], r["comparacao"], int(r["defasagem_dias"])): r for r in _ler(resumo_csv)}
    assert float(resumo["adr", "niveis", "atl_aguda", 0]["spearman"]) == pytest.approx(1.0)
    assert resumo["adr", "niveis", "atl_aguda", 0]["n_pares"] == "38"
    assert float(resumo["adr", "niveis", "ctl_cronica", 0]["spearman"]) == pytest.approx(1.0)
    assert float(resumo["adr", "razao", "razao", 0]["spearman"]) == pytest.approx(1.0)
    # diferenças: 3 x diferença da ATL (o +7 some): mesmo posto
    assert float(resumo["adr", "diferencas", "atl_aguda", 0]["spearman"]) == pytest.approx(1.0)
    assert float(resumo["adr", "diferencas", "ctl_cronica", 0]["spearman"]) == pytest.approx(1.0)
    # defasagens de -3 a +3 presentes, e k = 0 igual aos níveis
    assert sorted(d for (r, g, cmp, d) in resumo if (r, g, cmp) == ("adr", "defasagem", "atl_aguda")) == list(range(-3, 4))
    assert resumo["adr", "defasagem", "atl_aguda", 0]["spearman"] == resumo["adr", "niveis", "atl_aguda", 0]["spearman"]
    # a leitura complementar mantém os 43 dias
    assert resumo["todos_os_dias", "niveis", "atl_aguda", 0]["n_pares"] == "43"

    cob = {r["regra"]: r for r in _ler(cob_csv)}
    assert cob["adr"]["dias_comparados"] == "38" and cob["adr"]["descartados_sem_carga"] == "5"
    assert cob["todos_os_dias"]["dias_comparados"] == "43"

    dias = _ler(dia_csv)
    por_dia = {date.fromisoformat(r["dia"]): r for r in dias}
    assert len(dias) == 43
    assert por_dia[date(2025, 3, 6)]["entrou_na_comparacao"] == "nao_atividade_sem_carga"
    assert por_dia[date(2025, 3, 5)]["entrou_na_comparacao"] == "sim"
    assert float(por_dia[date(2025, 3, 5)]["garmin_aguda"]) == pytest.approx(3 * 4.958312 + 7, abs=1e-5)  # 3 x ATL + 7


def test_garmin_sem_nenhum_dia_nao_quebra(session, tmp_path):
    atleta_id = _atleta(session, garmin_relacionado=False)
    (_, resumo_csv, cob_csv), c, _ = conferir(session, atleta_id, tmp_path)
    assert c.cobertura.dias_garmin == 0 and c.cobertura.dias_comparados == 0
    assert all(r["spearman"] == "" and r["n_pares"] == "0" for r in _ler(resumo_csv))
    assert _ler(cob_csv)[0]["dias_garmin"] == "0"


def test_atleta_inexistente(session, tmp_path):
    with pytest.raises(AtletaInexistente):
        conferir(session, 999, tmp_path)


def test_cli_imprime_so_contagens(monkeypatch, session, capsys, tmp_path):
    from app.db import session as sessao
    atleta_id = _atleta(session)
    monkeypatch.setattr(sessao, "SessionLocal", lambda: session)
    assert conferir_carga.main(["--atleta-id", str(atleta_id), "--saida", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "dias comparados 38 de 43 em comum (descartados por atividade sem carga: 5)" in out
    assert "spearman" not in out.lower()
    assert conferir_carga.main(["--atleta-id", "999", "--saida", str(tmp_path)]) == 1
