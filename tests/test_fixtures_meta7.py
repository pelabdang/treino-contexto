"""Confere as fixtures sintéticas da Meta 7 e o oráculo à mão (issue #261, ADR 0011).

NÃO roda o código de produção da `tipo_treino@1` nem da `linha_base@1` (que ainda não existem, #262 e #263): confere que as
fixtures são a saída do gerador, que cobrem cada caso do encaixe (E1 a E16) e que o oráculo escrito à mão é coerente
com uma referência curta e independente das regras da ADR (`_tipo_referencia`, `_linha_base_referencia`).
Os valores que dependem do "A confirmar" vêm de `PARAMETROS` em `oraculo.py`.
"""

import importlib.util
import json
import statistics
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import pytest
from app.servicos.fuso import data_local

PASTA = Path(__file__).parent / "fixtures" / "meta7"


def _carregar(nome):
    spec = importlib.util.spec_from_file_location(nome, PASTA / f"{nome}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[nome] = mod
    spec.loader.exec_module(mod)
    return mod


gerador = _carregar("gerar_fixtures_meta7")
oraculo = _carregar("oraculo")
P = oraculo.PARAMETROS

ATIVIDADES = json.loads((PASTA / "atividades.json").read_text(encoding="utf-8"))["atividades"]
VIGENCIAS = json.loads((PASTA / "semana_padrao.json").read_text(encoding="utf-8"))["vigencias"]
POR_ID = {a["id"]: a for a in ATIVIDADES}
IGNORADAS = ("multiesporte_pai", "troca")
PROTEGIDAS = ("professor", "trainingpeaks")


def _inicio(a):
    return datetime.fromisoformat(a["inicio"])


def _dia(a):
    return data_local(_inicio(a), a["fuso_min"])


def _itens_na_data(dia):
    """Vigência de maior `vigente_desde` <= dia (nunca a seguinte); sem vigência, sem plano."""
    vig = [v for v in VIGENCIAS if date.fromisoformat(v["vigente_desde"]) <= dia]
    if not vig:
        return None
    v = max(vig, key=lambda x: x["vigente_desde"])
    return {(i["dia_semana"], i["modalidade"]): i["tipo_treino"] for i in v["itens"]}


def _tipo_referencia():
    """Reimplementação curta da precedência da ADR 0011, itens 2 a 5."""
    grupos = {}
    for a in ATIVIDADES:
        if a["subtipo"] not in IGNORADAS:
            grupos.setdefault((_dia(a), a["modalidade"]), []).append(a)
    dono = {k: min(v, key=lambda a: (-a["duracao_s"], a["inicio"], a["id"]))["id"] for k, v in grupos.items()}
    saida = {}
    for a in ATIVIDADES:
        if a["subtipo"] in IGNORADAS:
            saida[a["id"]] = (None, None, None)
            continue
        if a["tipo_confirmado"] or a["tipo_origem"] in PROTEGIDAS:
            saida[a["id"]] = (a["tipo_treino"], a["tipo_origem"], None)
            continue
        dia = _dia(a)
        itens = _itens_na_data(dia)
        plano = itens.get((dia.isoweekday(), a["modalidade"])) if itens else None
        est, t = a["estrutura"], a["tiros"]
        com_tiros = est == "tiros" and t["n"] >= 2
        if plano and dono[(dia, a["modalidade"])] == a["id"]:
            div = None
            if a["modalidade"] == "corrida":
                if plano == "intervalado" and est == "sem_esforco":
                    div = "sem_esforco"
                elif plano in ("leve", "longo") and com_tiros:
                    div = "tem_tiros"
            saida[a["id"]] = (plano, "semana_padrao", div)
        elif a["modalidade"] == "corrida" and com_tiros:
            saida[a["id"]] = ("intervalado", "sugestao", None)
        elif a["modalidade"] == "corrida" and est == "sem_esforco":
            if a["duracao_s"] >= P["LONGO_MIN_S"]:
                saida[a["id"]] = ("longo", "sugestao", None)
            elif a["duracao_s"] >= P["LEVE_MIN_S"]:
                saida[a["id"]] = ("leve", "sugestao", None)
            else:
                saida[a["id"]] = (None, None, None)
        else:
            saida[a["id"]] = (None, None, None)
    return saida


METRICAS = {
    ("corrida", "intervalado"): ("melhor_pace", "fc_melhor_tiro", "carga"),
    ("corrida", "leve"): ("pace_medio", "fc_media", "carga"),
    ("corrida", "longo"): ("pace_medio", "fc_media", "carga"),
    ("corrida", "moderado"): ("pace_medio", "fc_media", "carga"),
    ("corrida", "fartlek"): ("fc_media", "carga"),
}


def _valor(a, chave):
    if chave in ("pace_medio", "melhor_pace") and a["subtipo"] == "esteira":
        return None  # esteira fora das métricas de pace
    if chave == "pace_medio":
        return a["duracao_s"] / a["distancia_m"] * 1000 if a["distancia_m"] else None
    if chave == "melhor_pace":
        return a["tiros"]["melhor_pace_s_km"] if a["tiros"] else None
    if chave == "fc_melhor_tiro":
        return a["tiros"]["fc_melhor_tiro"] if a["tiros"] else None
    if chave == "fc_media":
        return a["fc_media"]
    return a["carga"]  # carga@2 (corrida e natação sem dados de saúde ficam None)


def _chaves(modalidade, tipo):
    if modalidade == "ciclismo":
        return ("fc_media", "carga")
    if modalidade == "natacao":
        return ("fc_media",)
    return METRICAS[(modalidade, tipo)]


def _motivo_sem_base(a, tipos):
    if a["subtipo"] in IGNORADAS:
        return "multiesporte"
    if a["modalidade"] == "outra":
        return "modalidade_sem_metricas"
    if tipos[a["id"]][0] is None:
        return "sem_tipo"
    if P["DIVERGENTE_FORA_DA_BASE"] and tipos[a["id"]][2]:
        return "divergente"
    if P["TRANSICAO_FORA_DA_BASE"] and a["transicao"]:
        return "transicao"
    return None


def _linha_base_referencia(sessao_id, tipos):
    s = POR_ID[sessao_id]
    tipo = tipos[sessao_id][0]
    inicio_dia = _dia(s) - timedelta(days=P["JANELA_DIAS"])
    pool = [
        a for a in ATIVIDADES
        if a["id"] != sessao_id and a["modalidade"] == s["modalidade"] and tipos[a["id"]][0] == tipo
        and _motivo_sem_base(a, tipos) is None and _inicio(a) < _inicio(s) and _dia(a) >= inicio_dia
    ]
    saida = {}
    for chave in _chaves(s["modalidade"], tipo):
        xs = [v for v in (_valor(a, chave) for a in pool) if v is not None]
        n = len(xs)
        v = _valor(s, chave)
        if v is None:
            saida[chave] = ("sem_valor", n, None, None, None)
        elif n < P["MINIMO_TREINOS"]:
            saida[chave] = ("aprendendo", n, None, None, None)
        else:
            med = statistics.median(xs)
            mad = statistics.median(abs(x - med) for x in xs)
            desvio = max(P["MAD_ESCALA"] * mad, P["PISO_REL"] * abs(med))
            z = (v - med) / desvio
            saida[chave] = ("fora" if abs(z) >= P["LIMITE_FORA"] else "dentro", n, med, desvio, z)
    return saida


# ---- fixtures -----------------------------------------------------------------------------------------------------

def test_json_versionado_e_a_saida_do_gerador():
    assert json.loads(json.dumps(gerador.gerar())) == json.loads((PASTA / "atividades.json").read_text(encoding="utf-8"))
    assert json.loads(json.dumps({"vigencias": gerador.SEMANA_PADRAO})) == {"vigencias": VIGENCIAS}


def test_doze_semanas_ids_unicos_e_dentro_do_periodo():
    assert len({a["id"] for a in ATIVIDADES}) == len(ATIVIDADES)
    dias = [_dia(a) for a in ATIVIDADES]
    assert min(dias) == date(2026, 1, 4) and max(dias) == date(2026, 3, 28)
    assert (date(2026, 3, 29) - date(2026, 1, 4)).days == 12 * 7  # domingo a domingo: 12 semanas completas
    assert {a["modalidade"] for a in ATIVIDADES} == {"corrida", "ciclismo", "natacao", "outra"}
    for a in ATIVIDADES:
        assert a["id"].startswith(_dia(a).isoformat())
        assert a["duracao_s"] > 0


def test_semana_padrao_muda_de_vigencia_no_meio_do_periodo():
    assert [v["vigente_desde"] for v in VIGENCIAS] == ["2026-01-05", "2026-03-02"]
    assert date(2026, 1, 5).isoweekday() == 1 and date(2026, 3, 2).isoweekday() == 1
    for v in VIGENCIAS:
        chaves = [(i["dia_semana"], i["modalidade"]) for i in v["itens"]]
        assert len(chaves) == len(set(chaves)), "um item por modalidade por dia"
        assert all(1 <= i["dia_semana"] <= 7 and i["modalidade"] != "outra" for i in v["itens"])
    assert _itens_na_data(date(2026, 1, 4)) is None  # antes da primeira vigência: sem plano, não olha a seguinte
    assert _itens_na_data(date(2026, 3, 1))[(4, "corrida")] == "fartlek"
    assert _itens_na_data(date(2026, 3, 2))[(4, "corrida")] == "moderado"


def test_cada_caso_do_encaixe_tem_ao_menos_uma_atividade():
    ids = set(POR_ID)
    casos = {
        "E1 formato coerente": "2026-01-27/cor1",
        "E2 duas corridas, solta antes": "2026-01-20/cor1",
        "E3 plano diverge do formato, empate de duração": "2026-01-13/cor2",
        "E4 item sem tipo (natação)": "2026-01-05/nat1",
        "E5 item corrida sem tipo": "2026-01-11/cor1",
        "E6 dia sem item": "2026-01-16/cor1",
        "E7 reserva intervalado": "2026-01-09/cor1",
        "E8 esteira": "2026-01-06/cor1",
        "E9 pedal virtual": "2026-01-14/cic1",
        "E10 multiesporte": "2026-01-10/out2",
        "E11 data local difere da UTC": "2026-02-24/cor1",
        "E12 fuso nulo": "2026-02-12/cor1",
        "E13 confirmado/professor/TP": "2026-01-15/cor1",
        "E14 antes da primeira vigência": "2026-01-04/cor1",
        "E15 troca de vigência": "2026-03-05/cor1",
        "tem_tiros": "2026-03-28/cor1",
    }
    assert set(casos.values()) <= ids
    assert POR_ID["2026-02-24/cor1"]["inicio"].startswith("2026-02-25")  # UTC já é quarta
    assert POR_ID["2026-02-12/cor1"]["fuso_min"] is None
    assert POR_ID["2026-01-06/cor1"]["subtipo"] == "esteira" and POR_ID["2026-01-14/cic1"]["subtipo"] == "virtual"
    assert {POR_ID[i]["tipo_origem"] for i in ("2026-01-08/cor1", "2026-01-29/cor1")} == {"professor", "trainingpeaks"}
    assert POR_ID["2026-01-15/cor1"]["tipo_confirmado"] is True


# ---- oráculo -------------------------------------------------------------------------------------------------------

def test_oraculo_do_tipo_cobre_toda_atividade():
    assert set(oraculo.TIPO_ESPERADO) == set(POR_ID)


def test_oraculo_do_tipo_bate_com_a_referencia_da_adr():
    ref = _tipo_referencia()
    diferentes = {i: (ref[i], oraculo.TIPO_ESPERADO[i]) for i in ref if ref[i] != oraculo.TIPO_ESPERADO[i]}
    assert not diferentes


def test_divergencias_e_origens_esperadas():
    contagem = {}
    for _, origem, div in oraculo.TIPO_ESPERADO.values():
        contagem[(origem, div)] = contagem.get((origem, div), 0) + 1
    assert contagem[("semana_padrao", "sem_esforco")] == 1
    assert contagem[("semana_padrao", "tem_tiros")] == 1
    assert all(div is None for (origem, div) in contagem if origem != "semana_padrao")


def test_reaplicar_a_vigencia_nova_nao_muda_o_passado():
    # E15: quinta antes de 02/03 é fartlek (vigência A); de 02/03 em diante, moderado (B).
    antes = [i for i, t in oraculo.TIPO_ESPERADO.items() if t == ("fartlek", "semana_padrao", None)]
    depois = [i for i, t in oraculo.TIPO_ESPERADO.items() if t[0] == "moderado" and t[1] == "semana_padrao" and POR_ID[i]["modalidade"] == "corrida"]
    assert antes and all(_dia(POR_ID[i]) < date(2026, 3, 2) for i in antes)
    assert depois and all(_dia(POR_ID[i]) >= date(2026, 3, 2) for i in depois)


def test_atividades_sem_linha_de_base_e_o_motivo():
    tipos = oraculo.TIPO_ESPERADO
    for i, motivo in oraculo.SEM_LINHA_BASE.items():
        assert _motivo_sem_base(POR_ID[i], tipos) == motivo, i


@pytest.mark.parametrize("sessao", sorted(oraculo.LINHA_BASE_ESPERADA))
def test_linha_base_do_oraculo_bate_com_a_referencia(sessao):
    ref = _linha_base_referencia(sessao, oraculo.TIPO_ESPERADO)
    esperado = oraculo.LINHA_BASE_ESPERADA[sessao]
    assert set(ref) == set(esperado)
    for chave, (estado, n, med, desvio, z) in esperado.items():
        r = ref[chave]
        assert (r[0], r[1]) == (estado, n), (sessao, chave, r)
        if med is None:
            assert r[2:] == (None, None, None)
        else:
            assert r[2] == pytest.approx(med, abs=1e-6), (sessao, chave)
            assert r[3] == pytest.approx(desvio, abs=5e-4), (sessao, chave)
            assert r[4] == pytest.approx(z, abs=5e-4), (sessao, chave)


def test_a_sessao_nunca_entra_na_propria_linha_de_base_e_tipos_nao_se_misturam():
    # 13/03 (leve, 306) fora da própria janela; ciclismo e natação leves não entram na linha da corrida leve.
    ref = _linha_base_referencia("2026-03-20/cor1", oraculo.TIPO_ESPERADO)
    assert ref["pace_medio"][2] == 330.0  # inclui os 306 de 13/03, não os 330 da própria sessão de 20/03
    assert _linha_base_referencia("2026-03-13/cor1", oraculo.TIPO_ESPERADO)["pace_medio"][1] == 8
