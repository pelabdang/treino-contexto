"""`linha_base@3` (e a `@2`, reproduzível por `PARAMETROS_V2`): mediana, desvio robusto e estados (issue #263, ADR 0011).

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
        assert res.estado == "ok" and res.versao == "linha_base@3"
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
    # exemplo da ADR (@2): o piso de 2% (6,6) não age; MAD 6 x 1,4826 = 8,8956
    mediana, desvio = lb.medida_robusta(JANELA, lb.PARAMETROS_V2)
    assert mediana == 330 and desvio == pytest.approx(8.8956)
    fora = lb.linha_base(_sessao(306), _leves(JANELA), lb.PARAMETROS_V2)
    assert fora.versao == "linha_base@2"
    assert fora.metricas[0].estado == "fora" and fora.metricas[0].z == pytest.approx(-24 / 8.8956)
    dentro = lb.linha_base(_sessao(318), _leves(JANELA), lb.PARAMETROS_V2).metricas[0]
    assert dentro.estado == "dentro" and dentro.z == pytest.approx(-12 / 8.8956)
    # @3: o piso de pace (3% x 330 = 9,9) passa de 8,8956 e vira o desvio; 306 deixa de ser fora (z = -24 / 9,9 = -2,424)
    v3 = lb.linha_base(_sessao(306), _leves(JANELA)).metricas[0]
    assert v3.desvio == pytest.approx(9.9) and v3.z == pytest.approx(-24 / 9.9) and v3.estado == "dentro"


def test_sete_treinos_ainda_aprendendo_sem_mediana():
    m = lb.linha_base(_sessao(306), _leves(JANELA[:7])).metricas[0]
    assert (m.estado, m.n, m.valor, m.mediana, m.desvio, m.z) == ("aprendendo", 7, 306, None, None, None)


def test_piso_quando_todos_iguais():
    # @3: pace tem piso de 3% da mediana = 9,9 (na @2 era 2% = 6,6)
    mediana, desvio = lb.medida_robusta([330.0] * 8, chave="pace_medio")
    assert (mediana, desvio) == (330.0, pytest.approx(9.9))
    m = lb.linha_base(_sessao(340), _leves([330] * 8)).metricas[0]
    assert m.estado == "dentro" and m.z == pytest.approx(10 / 9.9)


def test_limite_fora_inclui_exatamente_2_5():
    # @2: mediana 330, desvio de piso 6,6: 330 + 2,5 x 6,6 = 346,5
    v2 = lb.PARAMETROS_V2
    assert lb.linha_base(_sessao(346.5), _leves([330] * 8), v2).metricas[0].estado == "fora"
    assert lb.linha_base(_sessao(346.4), _leves([330] * 8), v2).metricas[0].estado == "dentro"
    # @3: piso 9,9: 330 + 2,5 x 9,9 = 354,75
    assert lb.linha_base(_sessao(354.75), _leves([330] * 8)).metricas[0].estado == "fora"
    assert lb.linha_base(_sessao(354.7), _leves([330] * 8)).metricas[0].estado == "dentro"


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


# ---- linha_base@3: piso por métrica (issues #455 e #462, ADR 0011 adendo 3). Exemplos sintéticos escritos à mão. ----------

def _t(i, valores, tipo="leve", modalidade="corrida"):
    ini = datetime(2026, 1, 2, 7, tzinfo=UTC) + timedelta(days=7 * i)
    return lb.Treino(id=i, inicio=ini, dia=ini.date(), modalidade=modalidade, tipo_treino=tipo, valores=valores)


def _s(valores, tipo="leve", modalidade="corrida"):
    ini = datetime(2026, 1, 2, 7, tzinfo=UTC) + timedelta(days=7 * 9)
    return lb.Treino(id="s", inicio=ini, dia=ini.date(), modalidade=modalidade, tipo_treino=tipo, valores=valores)


def _unica(res, chave):
    return next(m for m in res.metricas if m.chave == chave)


CARGA_HORA_9 = [50, 50, 52, 54, 61, 62, 62, 62, 62]  # dois grupos; mediana 61, MAD 1


def test_versoes_e_parametros_da_v3_e_da_v2():
    assert lb.VERSAO == "linha_base@3" and lb.PADRAO.versao == "linha_base@3"
    assert lb.PARAMETROS_V2.versao == "linha_base@2"
    for p in (lb.PADRAO, lb.PARAMETROS_V2):  # janela, mínimo e limite não mudaram da @2 para a @3
        assert (p.janela_dias, p.minimo_treinos, p.limite_fora) == (84, 8, 2.5)


def test_caso_da_investigacao_v2_marca_fora_so_pela_dispersao_pequena_e_v3_nao():
    # janela de 9: 50 50 52 54 61 62 62 62 62; mediana 61; |x - 61| = 11 11 9 7 0 1 1 1 1 -> ordenados
    # 0 1 1 1 1 7 9 11 11 -> MAD (5o) 1; 1,4826 x MAD = 1,4826.
    hist = [_t(i, {"carga_hora": v}) for i, v in enumerate(CARGA_HORA_9)]
    # sessão 55: @2 desvio max(1,4826; 2% x 61 = 1,22) = 1,4826; z = -6 / 1,4826 = -4,047 -> fora
    v2 = _unica(lb.linha_base(_s({"carga_hora": 55.0}), hist, lb.PARAMETROS_V2), "carga_hora")
    assert v2.desvio == pytest.approx(1.4826) and v2.z == pytest.approx(-6 / 1.4826) and v2.estado == "fora"
    # @3 desvio max(1,4826; 5% x 61 = 3,05) = 3,05; z = -6 / 3,05 = -1,967 -> dentro
    v3 = _unica(lb.linha_base(_s({"carga_hora": 55.0}), hist), "carga_hora")
    assert v3.desvio == pytest.approx(3.05) and v3.z == pytest.approx(-6 / 3.05) and v3.estado == "dentro"
    # um valor realmente distante continua fora na @3: 53 -> z = -8 / 3,05 = -2,623
    longe = _unica(lb.linha_base(_s({"carga_hora": 53.0}), hist), "carga_hora")
    assert longe.z == pytest.approx(-8 / 3.05) and longe.estado == "fora"


def test_piso_da_fc_e_4_bpm_absolutos():
    # FC 136 140 142 140 138 141 140 139 (8): ordenados 136 138 139 140 140 140 141 142 -> mediana 140; |x - 140|:
    # 4 0 2 0 2 1 0 1 -> ordenados 0 0 0 1 1 2 2 4 -> MAD (1 + 1) / 2 = 1 -> 1,4826. Piso @2: 2% x 140 = 2,8; @3: 4.
    hist = [_t(i, {"fc_media": v}) for i, v in enumerate([136, 140, 142, 140, 138, 141, 140, 139])]
    v2 = _unica(lb.linha_base(_s({"fc_media": 148.0}), hist, lb.PARAMETROS_V2), "fc_media")
    assert v2.desvio == pytest.approx(2.8) and v2.z == pytest.approx(8 / 2.8) and v2.estado == "fora"
    v3 = _unica(lb.linha_base(_s({"fc_media": 148.0}), hist), "fc_media")
    assert v3.desvio == pytest.approx(4.0) and v3.z == pytest.approx(2.0) and v3.estado == "dentro"
    # a FC ainda marca a partir de 2,5 x 4 = 10 bpm acima: 150 -> z = 10 / 4 = 2,5 -> fora (limite inclusivo)
    assert _unica(lb.linha_base(_s({"fc_media": 150.0}), hist), "fc_media").estado == "fora"


def test_piso_do_pace_e_3_por_cento_da_mediana_em_pace_medio_e_melhor_pace():
    # oito valores iguais a 300: MAD 0. @2: 2% x 300 = 6; @3: 3% x 300 = 9.
    for chave, tipo in (("pace_medio", "leve"), ("melhor_pace", "intervalado")):
        hist = [_t(i, {chave: 300.0}, tipo) for i in range(8)]
        m = _unica(lb.linha_base(_s({chave: 315.0}, tipo), hist), chave)
        assert m.desvio == pytest.approx(9.0) and m.z == pytest.approx(15 / 9) and m.estado == "dentro", chave
        m2 = _unica(lb.linha_base(_s({chave: 315.0}, tipo), hist, lb.PARAMETROS_V2), chave)
        assert m2.desvio == pytest.approx(6.0) and m2.z == pytest.approx(2.5) and m2.estado == "fora", chave


def test_fc_do_melhor_tiro_tem_o_piso_de_fc():
    # oito 170: MAD 0. @2: 2% x 170 = 3,4 -> 179 tem z = 9 / 3,4 = 2,647 (fora); @3: 4 bpm -> z = 9 / 4 = 2,25 (dentro)
    hist = [_t(i, {"fc_melhor_tiro": 170.0}, "intervalado") for i in range(8)]
    m = _unica(lb.linha_base(_s({"fc_melhor_tiro": 179.0}, "intervalado"), hist), "fc_melhor_tiro")
    assert m.desvio == pytest.approx(4.0) and m.z == pytest.approx(2.25) and m.estado == "dentro"
    m2 = _unica(lb.linha_base(_s({"fc_melhor_tiro": 179.0}, "intervalado"), hist, lb.PARAMETROS_V2), "fc_melhor_tiro")
    assert m2.desvio == pytest.approx(3.4) and m2.z == pytest.approx(9 / 3.4) and m2.estado == "fora"


def test_igual_a_v2_quando_o_piso_nao_age():
    # carga/h 30 36 42 48 54 60 66 72: mediana (48 + 54) / 2 = 51; |x - 51| = 21 15 9 3 3 9 15 21 -> ordenados
    # 3 3 9 9 15 15 21 21 -> MAD (9 + 15) / 2 = 12 -> desvio 1,4826 x 12 = 17,7912; piso 5% x 51 = 2,55 não age.
    hist = [_t(i, {"carga_hora": float(v)}, "leve") for i, v in enumerate([30, 36, 42, 48, 54, 60, 66, 72])]
    a = _unica(lb.linha_base(_s({"carga_hora": 80.0}), hist), "carga_hora")
    b = _unica(lb.linha_base(_s({"carga_hora": 80.0}), hist, lb.PARAMETROS_V2), "carga_hora")
    assert a.desvio == pytest.approx(17.7912) and a.z == pytest.approx(29 / 17.7912)  # 1,630 -> dentro
    assert (a.desvio, a.z, a.estado, a.mediana) == (b.desvio, b.z, b.estado, b.mediana)


def test_minimo_de_8_amostras_sete_e_aprendendo_oito_calcula():
    for chave, v in (("fc_media", 150.0), ("carga_hora", 60.0), ("pace_medio", 330.0)):
        sete = [_t(i, {chave: v}) for i in range(7)]
        m7 = _unica(lb.linha_base(_s({chave: v}), sete), chave)
        assert (m7.estado, m7.n, m7.mediana, m7.desvio, m7.z) == ("aprendendo", 7, None, None, None), chave
        oito = [_t(i, {chave: v}) for i in range(8)]
        m8 = _unica(lb.linha_base(_s({chave: v}), oito), chave)
        assert (m8.estado, m8.n, m8.z) == ("dentro", 8, 0.0), chave


def test_medida_robusta_sem_chave_usa_o_piso_geral_e_a_recuperacao_segue_igual():
    # parâmetros de outra regra (recuperação) só têm piso_rel: 5% x 52 = 2,6, como antes
    from app.metricas import recuperacao as rc
    assert lb.medida_robusta([52.0] * 14, rc.PADRAO) == (52.0, pytest.approx(2.6))
    assert lb.medida_robusta([330.0] * 8)[1] == pytest.approx(6.6)  # sem chave: piso geral de 2%
