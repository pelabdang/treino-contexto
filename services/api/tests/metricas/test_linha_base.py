"""`linha_base@1`: mediana, desvio robusto e estados (issue #263, ADR 0011).

O oráculo à mão (`tests/fixtures/meta7/oraculo.py`, #261) cobre as sessões-alvo das fixtures; os testes abaixo cobrem o exemplo
da ADR e as bordas com valores escritos aqui.
"""

import importlib.util
import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from app.metricas import linha_base as lb
from app.servicos.fuso import data_local

PASTA = Path(__file__).parents[4] / "tests" / "fixtures" / "meta7"


def _oraculo():
    spec = importlib.util.spec_from_file_location("oraculo_meta7_lb", PASTA / "oraculo.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["oraculo_meta7_lb"] = mod
    spec.loader.exec_module(mod)
    return mod


def _valores(a):
    esteira = a["subtipo"] == "esteira"
    tiros = a["tiros"]
    return {
        "pace_medio": None if esteira or not a["distancia_m"] else a["duracao_s"] / a["distancia_m"] * 1000,
        "melhor_pace": None if esteira or not tiros else tiros["melhor_pace_s_km"],
        "fc_melhor_tiro": tiros["fc_melhor_tiro"] if tiros else None,
        "fc_media": a["fc_media"],
        "carga_hora": None if a["carga"] is None else a["carga"] / (a["duracao_s"] / 3600),
    }


def _treinos(tipos):
    brutas = json.loads((PASTA / "atividades.json").read_text(encoding="utf-8"))["atividades"]
    saida = {}
    for a in brutas:
        ini = datetime.fromisoformat(a["inicio"])
        tipo, _, div = tipos[a["id"]]
        saida[a["id"]] = lb.Treino(
            id=a["id"], inicio=ini, dia=data_local(ini, a["fuso_min"]), modalidade=a["modalidade"], tipo_treino=tipo,
            valores=_valores(a), subtipo=a["subtipo"], divergente=div is not None, transicao=a["transicao"],
        )
    return saida


def test_sessoes_alvo_do_oraculo():
    orac = _oraculo()
    treinos = _treinos(orac.TIPO_ESPERADO)
    historico = list(treinos.values())
    for sessao, esperado in orac.LINHA_BASE_ESPERADA.items():
        res = lb.linha_base(treinos[sessao], historico)
        assert res.estado == "ok" and res.versao == "linha_base@2"
        assert {m.chave for m in res.metricas} == set(esperado), sessao
        for m in res.metricas:
            estado, n, med, desvio, z = esperado[m.chave]
            assert (m.estado, m.n) == (estado, n), (sessao, m.chave)
            if med is None:
                assert (m.mediana, m.desvio, m.z) == (None, None, None)
            else:
                assert m.mediana == pytest.approx(med, abs=1e-6)
                assert m.desvio == pytest.approx(desvio, abs=5e-4)
                assert m.z == pytest.approx(z, abs=5e-4)


def test_atividades_sem_linha_de_base_e_o_motivo():
    orac = _oraculo()
    treinos = _treinos(orac.TIPO_ESPERADO)
    historico = list(treinos.values())
    for i, motivo in orac.SEM_LINHA_BASE.items():
        res = lb.linha_base(treinos[i], historico)
        assert (res.estado, res.motivo, res.metricas) == ("sem_linha_base", motivo, ())


def test_parametros_do_a_confirmar_mudam_o_resultado():
    orac = _oraculo()
    treinos = _treinos(orac.TIPO_ESPERADO)
    historico = list(treinos.values())
    sem_div = lb.Parametros(divergente_fora_da_base=False)
    assert lb.linha_base(treinos["2026-01-13/cor1"], historico, sem_div).estado == "ok"
    # com limite mais alto, a sessão a -2,698 passa a "dentro"
    res = lb.linha_base(treinos["2026-03-13/cor1"], historico, lb.Parametros(limite_fora=3.0))
    assert {m.chave: m.estado for m in res.metricas}["pace_medio"] == "dentro"


# ---- exemplo da ADR 0011 (item 6) e bordas ----------------------------------------------------------------------

def _leves(paces, tipo="leve"):
    base = datetime(2026, 1, 2, 7, tzinfo=UTC)
    return [
        lb.Treino(id=i, inicio=base + timedelta(days=7 * i), dia=(base + timedelta(days=7 * i)).date(), modalidade="corrida",
                  tipo_treino=tipo, valores={"pace_medio": p})
        for i, p in enumerate(paces)
    ]


def _sessao(valor, id="s", dias=7 * 8, tipo="leve", modalidade="corrida"):
    ini = datetime(2026, 1, 2, 7, tzinfo=UTC) + timedelta(days=dias)
    return lb.Treino(id=id, inicio=ini, dia=ini.date(), modalidade=modalidade, tipo_treino=tipo, valores={"pace_medio": valor})


JANELA = [330, 324, 336, 330, 342, 318, 330, 336]


def test_exemplo_da_adr_mediana_330_mad_6():
    mediana, desvio = lb.medida_robusta(JANELA)
    assert mediana == 330 and desvio == pytest.approx(8.8956)
    fora = lb.linha_base(_sessao(306), _leves(JANELA)).metricas[0]
    assert fora.estado == "fora" and fora.z == pytest.approx(-24 / 8.8956)
    dentro = lb.linha_base(_sessao(318), _leves(JANELA)).metricas[0]
    assert dentro.estado == "dentro" and dentro.z == pytest.approx(-12 / 8.8956)


def test_sete_treinos_ainda_aprendendo_sem_mediana():
    m = lb.linha_base(_sessao(306), _leves(JANELA[:7])).metricas[0]
    assert (m.estado, m.n, m.valor, m.mediana, m.desvio, m.z) == ("aprendendo", 7, 306, None, None, None)


def test_piso_quando_todos_iguais():
    mediana, desvio = lb.medida_robusta([330.0] * 8)
    assert (mediana, desvio) == (330.0, pytest.approx(6.6))
    m = lb.linha_base(_sessao(340), _leves([330] * 8)).metricas[0]
    assert m.estado == "dentro" and m.z == pytest.approx(10 / 6.6)


def test_limite_fora_inclui_exatamente_2_5():
    # mediana 330, desvio de piso 6,6: 330 + 2,5 x 6,6 = 346,5
    assert lb.linha_base(_sessao(346.5), _leves([330] * 8)).metricas[0].estado == "fora"
    assert lb.linha_base(_sessao(346.4), _leves([330] * 8)).metricas[0].estado == "dentro"


def test_janela_de_84_dias_inclui_o_primeiro_dia_e_exclui_o_anterior():
    # sessão 84 dias depois de 2026-01-02 (2026-03-27): o treino de 01-02 ainda entra; um de 01-01 não.
    base = _leves([330] * 8)  # 01-02, 01-09, ... 02-20
    sessao = _sessao(330, dias=84)
    assert lb.linha_base(sessao, base).metricas[0].n == 8
    velho = lb.Treino(id="v", inicio=base[0].inicio - timedelta(days=1), dia=base[0].dia - timedelta(days=1), modalidade="corrida",
                      tipo_treino="leve", valores={"pace_medio": 330})
    assert lb.linha_base(sessao, [velho, *base[1:]]).metricas[0].n == 7
    assert lb.PADRAO.janela_dias == 84 and lb.PADRAO.minimo_treinos == 8


def test_parte_de_transicao_tem_base_propria_e_as_isoladas_nao_veem_as_partes():
    isoladas = _leves([330] * 8)
    partes = [lb.Treino(**{**t.__dict__, "id": f"t{t.id}", "transicao": True, "valores": {"pace_medio": 300}}) for t in _leves([300] * 8)]
    ini = _sessao(0).inicio
    parte = lb.Treino(id="p", inicio=ini, dia=ini.date(), modalidade="corrida", tipo_treino="leve", transicao=True, valores={"pace_medio": 300})
    isolada = _sessao(330)
    pace_parte = lb.linha_base(parte, [*isoladas, *partes]).metricas[0]
    assert (pace_parte.estado, pace_parte.n, pace_parte.mediana) == ("dentro", 8, 300)  # só as partes
    pace_isolada = lb.linha_base(isolada, [*isoladas, *partes]).metricas[0]
    assert (pace_isolada.estado, pace_isolada.n, pace_isolada.mediana) == ("dentro", 8, 330)  # só as isoladas
    # sem partes anteriores, a parte fica aprendendo (n = 0), não "sem linha de base"
    sozinha = lb.linha_base(parte, isoladas)
    assert sozinha.estado == "ok" and sozinha.metricas[0].estado == "aprendendo" and sozinha.metricas[0].n == 0


def test_so_treinos_anteriores_e_a_sessao_nunca_entra():
    base = _leves([330] * 8)
    sessao = _sessao(330)
    posterior = lb.Treino(id="p", inicio=sessao.inicio + timedelta(hours=1), dia=sessao.dia, modalidade="corrida",
                          tipo_treino="leve", valores={"pace_medio": 330})
    assert lb.linha_base(sessao, [*base, sessao, posterior]).metricas[0].n == 8


def test_tipos_e_modalidades_nunca_se_misturam():
    base = _leves([330] * 7)
    outro_tipo = _leves([330], tipo="longo")[0]
    ciclismo = lb.Treino(id="c", inicio=base[0].inicio, dia=base[0].dia, modalidade="ciclismo", tipo_treino="leve", valores={"pace_medio": 330})
    m = lb.linha_base(_sessao(330), [*base, outro_tipo, ciclismo]).metricas[0]
    assert (m.estado, m.n) == ("aprendendo", 7)


def test_metrica_sem_valor_na_sessao_explica_e_conta_n():
    sessao = lb.Treino(id="s", inicio=_sessao(0).inicio, dia=_sessao(0).dia, modalidade="corrida", tipo_treino="leve",
                       valores={"pace_medio": 330, "fc_media": None})
    base = [lb.Treino(**{**t.__dict__, "valores": {"pace_medio": 330, "fc_media": 150}}) for t in _leves([330] * 8)]
    por = {m.chave: m for m in lb.linha_base(sessao, base).metricas}
    assert (por["fc_media"].estado, por["fc_media"].n) == ("sem_valor", 8)
    assert por["pace_medio"].estado == "dentro"


def test_metricas_por_modalidade_e_tipo():
    assert lb.metricas_do_tipo("corrida", "intervalado") == ("melhor_pace", "fc_melhor_tiro", "fc_media", "carga_hora")
    assert lb.metricas_do_tipo("corrida", "fartlek") == ("fc_media", "carga_hora")
    assert lb.metricas_do_tipo("ciclismo", "leve") == ("fc_media", "carga_hora")
    assert lb.metricas_do_tipo("natacao", "leve") == ("fc_media",)
    assert lb.metricas_do_tipo("outra", None) == ()


@pytest.mark.parametrize("kw,motivo", [
    ({"subtipo": "troca"}, "multiesporte"),
    ({"modalidade": "outra"}, "modalidade_sem_metricas"),
    ({"tipo_treino": None}, "sem_tipo"),
    ({"divergente": True}, "divergente"),
    ({"tipo_treino": None, "divergente": True, "transicao": True}, "sem_tipo"),  # ordem da ADR
])
def test_motivos_na_ordem_da_adr(kw, motivo):
    t = lb.Treino(**{**_sessao(330).__dict__, **kw})
    res = lb.linha_base(t, [])
    assert (res.estado, res.motivo) == ("sem_linha_base", motivo)
