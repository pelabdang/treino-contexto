"""`tipo_treino@1`: encaixe na semana-padrão e regra de reserva (issue #262, ADR 0011).

O oráculo à mão (`tests/fixtures/meta7/oraculo.py`, #261) cobre as 81 atividades das fixtures; os testes abaixo cobrem
os casos de borda com valores escritos aqui.
"""

import importlib.util
import json
import sys
from datetime import UTC, date, datetime
from pathlib import Path

import pytest
from app.metricas import tipo_treino as tt
from app.servicos.fuso import data_local

PASTA = Path(__file__).parents[4] / "tests" / "fixtures" / "meta7"


def _oraculo():
    spec = importlib.util.spec_from_file_location("oraculo_meta7", PASTA / "oraculo.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["oraculo_meta7"] = mod
    spec.loader.exec_module(mod)
    return mod


def _fixtures():
    brutas = json.loads((PASTA / "atividades.json").read_text(encoding="utf-8"))["atividades"]
    vigencias = [
        tt.Vigencia(date.fromisoformat(v["vigente_desde"]), tuple(tt.Item(i["dia_semana"], i["modalidade"], i["tipo_treino"]) for i in v["itens"]))
        for v in json.loads((PASTA / "semana_padrao.json").read_text(encoding="utf-8"))["vigencias"]
    ]
    atividades = []
    for a in brutas:
        ini = datetime.fromisoformat(a["inicio"])
        atividades.append(tt.Atividade(
            id=a["id"], dia=data_local(ini, a["fuso_min"]), modalidade=a["modalidade"], inicio=ini, duracao_s=a["duracao_s"],
            subtipo=a["subtipo"], tipo_treino=a["tipo_treino"], tipo_origem=a["tipo_origem"], tipo_confirmado=a["tipo_confirmado"],
            estrutura=a["estrutura"], n_tiros=(a["tiros"] or {}).get("n", 0),
        ))
    return atividades, vigencias


def test_oraculo_das_fixtures_de_12_semanas():
    atividades, vigencias = _fixtures()
    esperado = _oraculo().TIPO_ESPERADO
    res = tt.classificar(atividades, vigencias)
    assert {i: (r.tipo_treino, r.tipo_origem, r.divergencia) for i, r in res.items()} == esperado


def test_versao_so_quando_a_regra_escreveu():
    atividades, vigencias = _fixtures()
    res = tt.classificar(atividades, vigencias)
    for r in res.values():
        assert (r.versao == tt.VERSAO) == (r.tipo_origem in ("sugestao", "semana_padrao"))


def test_idempotente_e_nao_depende_do_tipo_sugerido_antes():
    atividades, vigencias = _fixtures()
    primeira = tt.classificar(atividades, vigencias)
    regravadas = [
        a if primeira[a.id].tipo_origem not in ("sugestao", "semana_padrao")
        else tt.Atividade(**{**a.__dict__, "tipo_treino": primeira[a.id].tipo_treino, "tipo_origem": primeira[a.id].tipo_origem})
        for a in atividades
    ]
    assert tt.classificar(regravadas, vigencias) == primeira


def test_vigencia_nunca_olha_a_seguinte():
    v = [tt.Vigencia(date(2026, 3, 2), ()), tt.Vigencia(date(2026, 1, 5), ())]
    assert tt.vigencia_na_data(v, date(2026, 1, 4)) is None
    assert tt.vigencia_na_data(v, date(2026, 1, 5)).vigente_desde == date(2026, 1, 5)  # vigência no dia já vale
    assert tt.vigencia_na_data(v, date(2026, 3, 1)).vigente_desde == date(2026, 1, 5)
    assert tt.vigencia_na_data(v, date(2026, 3, 2)).vigente_desde == date(2026, 3, 2)


def _corrida(id, dia, duracao, estrutura=tt.SEM_ESFORCO, n_tiros=0, hora=7, **kw):
    return tt.Atividade(id=id, dia=dia, modalidade="corrida", inicio=datetime(dia.year, dia.month, dia.day, hora, tzinfo=UTC),
                        duracao_s=duracao, estrutura=estrutura, n_tiros=n_tiros, **kw)


TERCA = date(2026, 2, 3)
PLANO = [tt.Vigencia(date(2026, 2, 2), (tt.Item(2, "corrida", "intervalado"),))]


def test_limites_da_reserva():
    leve_min = _corrida(1, date(2026, 2, 6), tt.LEVE_MIN_S)
    abaixo = _corrida(2, date(2026, 2, 7), tt.LEVE_MIN_S - 1)
    longo_min = _corrida(3, date(2026, 2, 8), tt.LONGO_MIN_S)
    quase_longo = _corrida(4, date(2026, 2, 9), tt.LONGO_MIN_S - 1)
    res = tt.classificar([leve_min, abaixo, longo_min, quase_longo], [])
    assert res[1].tipo_treino == "leve" and res[2].tipo_treino is None
    assert res[3].tipo_treino == "longo" and res[4].tipo_treino == "leve"


def test_reserva_nao_inventa_moderado_nem_fartlek_nem_tipa_outras_modalidades():
    esforco = _corrida(1, date(2026, 2, 6), 3000, estrutura=tt.ESFORCO)
    sem_blocos = _corrida(2, date(2026, 2, 7), 3000, estrutura=None)
    um_tiro = _corrida(3, date(2026, 2, 8), 3000, estrutura=tt.TIROS, n_tiros=1)
    bike = tt.Atividade(id=4, dia=date(2026, 2, 9), modalidade="ciclismo", inicio=datetime(2026, 2, 9, tzinfo=UTC), duracao_s=3600)
    res = tt.classificar([esforco, sem_blocos, um_tiro, bike], [])
    assert all(r == tt.SEM_TIPO for r in res.values())


def test_plano_vence_a_regra_e_marca_divergencia_sem_mudar_o_tipo():
    sem_esforco = _corrida(1, TERCA, 1800)
    r = tt.classificar([sem_esforco], PLANO)[1]
    assert (r.tipo_treino, r.tipo_origem, r.divergencia) == ("intervalado", "semana_padrao", "sem_esforco")
    sem_blocos = _corrida(2, TERCA, 1800, estrutura=None)  # sem blocos gravados não é "sem esforço"
    assert tt.classificar([sem_blocos], PLANO)[2].divergencia is None


def test_tem_tiros_so_com_plano_leve_ou_longo():
    plano = [tt.Vigencia(date(2026, 2, 2), (tt.Item(2, "corrida", "leve"), tt.Item(4, "corrida", "fartlek")))]
    com_tiros = _corrida(1, TERCA, 3000, estrutura=tt.TIROS, n_tiros=6)
    quinta = _corrida(2, date(2026, 2, 5), 3000, estrutura=tt.TIROS, n_tiros=6)
    res = tt.classificar([com_tiros, quinta], plano)
    assert res[1].divergencia == "tem_tiros" and res[1].tipo_treino == "leve"
    assert res[2].divergencia is None and res[2].tipo_treino == "fartlek"


def test_empate_de_duracao_vai_para_a_mais_cedo_e_depois_para_o_menor_id():
    manha = _corrida("b", TERCA, 1800, hora=7)
    tarde = _corrida("a", TERCA, 1800, hora=18)
    res = tt.classificar([tarde, manha], PLANO)
    assert res["b"].tipo_origem == "semana_padrao" and res["a"].tipo_origem == "sugestao"
    mesma_hora_1 = _corrida("x", TERCA, 1800)
    mesma_hora_2 = _corrida("y", TERCA, 1800)
    assert tt.classificar([mesma_hora_2, mesma_hora_1], PLANO)["x"].tipo_origem == "semana_padrao"


def test_atividade_protegida_escolhida_consome_o_item():
    confirmada = _corrida(1, TERCA, 3000, tipo_treino="fartlek", tipo_confirmado=True)
    outra = _corrida(2, TERCA, 1800)
    res = tt.classificar([confirmada, outra], PLANO)
    assert res[1] == tt.Resultado("fartlek", None, None, None)
    assert res[2].tipo_origem == "sugestao"  # reserva, não o plano


def test_item_sem_tipo_cai_na_reserva_e_multiesporte_nunca_recebe_tipo():
    plano = [tt.Vigencia(date(2026, 2, 2), (tt.Item(2, "corrida", None),))]
    r = tt.classificar([_corrida(1, TERCA, 2400)], plano)[1]
    assert (r.tipo_treino, r.tipo_origem) == ("leve", "sugestao")
    pai = _corrida(2, TERCA, 9000, subtipo="multiesporte_pai")
    troca = _corrida(3, TERCA, 100, subtipo="troca")
    res = tt.classificar([pai, troca, _corrida(4, TERCA, 3000)], PLANO)
    assert res[2] == tt.SEM_TIPO and res[3] == tt.SEM_TIPO
    assert res[4].tipo_origem == "semana_padrao"  # o pai não consome o item


@pytest.mark.parametrize("protegida", [{"tipo_origem": "professor"}, {"tipo_origem": "trainingpeaks"}, {"tipo_confirmado": True}])
def test_tipo_protegido_nunca_muda(protegida):
    a = _corrida(1, TERCA, 3000, tipo_treino="longo", **protegida)
    r = tt.classificar([a], PLANO)[1]
    assert r.tipo_treino == "longo" and r.divergencia is None and r.versao is None


def test_desempate_por_menor_id_ordena_inteiros_como_numeros():
    dez = _corrida(10, TERCA, 1800)
    nove = _corrida(9, TERCA, 1800)  # mesma duração e mesmo início
    res = tt.classificar([dez, nove], PLANO)
    assert res[9].tipo_origem == "semana_padrao" and res[10].tipo_origem == "sugestao"
