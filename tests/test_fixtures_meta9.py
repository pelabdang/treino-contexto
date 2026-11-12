"""Oráculo do pacote de fatos `fatos_treino@2` (issue #323, ADR 0013): confere o oráculo escrito à mão.

NÃO roda a função pura do pacote (#324, ainda não existe): confere que o oráculo é coerente com o que o código **já calcula**
(`linha_base@2`, `carga_pse@1`, formatos de texto da API) e que nenhum caso carrega dado pessoal que não deve ir ao provedor
(texto livre, identificador, data, posição). A #324 passa a comparar a função pura com ``PACOTES``.
Tudo sintético; nenhum check-in é real.
"""

import importlib.util
import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from app.metricas import carga_pse as cp
from app.metricas import linha_base as lb
from app.servicos import checkin as svc_checkin
from app.servicos import linha_base_leitura as lbl
from app.servicos.carga_pse_leitura import duracao_pt, numero_pt
from app.servicos.distancia_texto import distancia_da_atividade

PASTA = Path(__file__).parent / "fixtures" / "meta9"


def _oraculo():
    spec = importlib.util.spec_from_file_location("oraculo_meta9", PASTA / "oraculo.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


O = _oraculo()
IDS = list(O.ENTRADAS)
COM_PACOTE = [i for i in IDS if O.PACOTES[i] is not None]
HOJE = datetime(2026, 11, 9, 9, 0, tzinfo=UTC)


def _chaves_ok(nome, bloco):
    assert tuple(bloco) == O.CHAVES[nome], nome


def test_o_oraculo_cobre_os_casos_da_issue():
    ents = O.ENTRADAS
    assert any(e["checkin"] is None for e in ents.values())  # sem check-in
    assert any(e["atividade"]["modalidade"] == "natacao" for e in ents.values())
    assert any(e["checkin"] and "dor" in e["checkin"]["atalhos"] for e in ents.values())
    assert any(e["clima"] is not None and e["clima"] not in ("indoor", "pendente") for e in ents.values())  # com clima
    assert any(e["clima"] in (None, "indoor", "pendente") for e in ents.values())  # sem clima
    estados = {m["estado"] for p in O.PACOTES.values() if p for m in p["linha_base"]["metricas"]}
    assert {"fora", "dentro", "aprendendo", "sem_valor"} <= estados
    assert set(O.SEM_PACOTE) == {i for i in IDS if O.PACOTES[i] is None}


@pytest.mark.parametrize("i", COM_PACOTE)
def test_estrutura_do_pacote(i):
    p = O.PACOTES[i]
    _chaves_ok("pacote", p)
    _chaves_ok("treino", p["treino"])
    _chaves_ok("linha_base", p["linha_base"])
    for m in p["linha_base"]["metricas"]:
        _chaves_ok("metrica", m)
    if p["esforcos"] is not None:
        _chaves_ok("esforcos", p["esforcos"])
    if p["clima"] is not None:
        _chaves_ok("clima", p["clima"])
    _chaves_ok("carga", p["carga"])
    _chaves_ok("carga_pse", p["carga_pse"])
    _chaves_ok("checkin", p["checkin"])
    assert p["versao"] == "fatos_treino@2"
    assert p["linha_base"]["versao"] == lb.VERSAO and p["carga_pse"]["versao"] == cp.VERSAO


def _todas_as_chaves(x):
    if isinstance(x, dict):
        for k, v in x.items():
            yield k
            yield from _todas_as_chaves(v)
    elif isinstance(x, list):
        for v in x:
            yield from _todas_as_chaves(v)


@pytest.mark.parametrize("i", COM_PACOTE)
def test_pacote_sem_dado_pessoal(i):
    """Nunca vai ao provedor: texto livre, identificador, data real, posição, nome."""
    p = O.PACOTES[i]
    bruto = json.dumps(p, ensure_ascii=False)
    assert O.MARCADOR_TEXTO_LIVRE not in bruto
    assert not set(_todas_as_chaves(p)) & set(O.NOMES_PROIBIDOS_NO_PACOTE)
    assert "2026" not in bruto and "T0" not in bruto  # nenhuma data nem hora real
    json.loads(bruto)  # serializável


def test_o_texto_livre_so_existe_na_entrada():
    assert O.ENTRADAS["F05"]["checkin"]["texto"] == O.MARCADOR_TEXTO_LIVRE
    assert sum(1 for e in O.ENTRADAS.values() if e["checkin"] and e["checkin"]["texto"]) == 1


def test_nao_ha_pacote_sem_checkin_nem_para_nao_elegivel():
    assert O.ENTRADAS["F07"]["checkin"] is None and O.PACOTES["F07"] is None
    a = O.ENTRADAS["F08"]["atividade"]
    assert not cp.elegivel(a["subtipo"]) and O.PACOTES["F08"] is None


def _valores_da_sessao(e):
    a = e["atividade"]
    v = {"fc_media": float(a["fc_media"])}
    esteira = a["subtipo"] == "esteira"
    v["pace_medio"] = None if esteira else a["duracao_s"] / a["distancia_m"] * 1000
    v["carga_hora"] = None if e["carga"] is None else e["carga"] / (a["duracao_s"] / 3600)
    if "melhor_tiro" in e:
        v["melhor_pace"] = float(e["melhor_tiro"]["pace_s_km"])
        v["fc_melhor_tiro"] = float(e["melhor_tiro"]["fc_bpm"])
    return v


def _linha_base(e):
    a = e["atividade"]
    sessao = lb.Treino(id="s", inicio=HOJE, dia=HOJE.date(), modalidade=a["modalidade"], tipo_treino=a["tipo_treino"],
                       valores=_valores_da_sessao(e), subtipo=a["subtipo"])
    n = max((len(x) for x in e["historico"].values()), default=0)
    historico = []
    for k in range(n):  # um treino por semana, do mais antigo ao mais recente; a janela é de 84 dias
        dt = HOJE - timedelta(days=7 * (n - k))
        historico.append(lb.Treino(
            id=f"h{k}", inicio=dt, dia=dt.date(), modalidade=a["modalidade"], tipo_treino=a["tipo_treino"],
            valores={c: (xs[k] if k < len(xs) else None) for c, xs in e["historico"].items()}))
    return lb.linha_base(sessao, historico)


@pytest.mark.parametrize("i", COM_PACOTE)
def test_linha_base_do_pacote_bate_com_a_linha_base_v2(i):
    esperado = O.PACOTES[i]["linha_base"]
    r = _linha_base(O.ENTRADAS[i])
    assert r.estado == esperado["estado"] and r.motivo == esperado["motivo"]
    assert [m.chave for m in r.metricas] == [m["chave"] for m in esperado["metricas"]]
    for m, esp in zip(r.metricas, esperado["metricas"], strict=True):
        assert (m.estado, m.n) == (esp["estado"], esp["n"]), m.chave


@pytest.mark.parametrize(("i", "chave"), list(O.LINHA_BASE_ESPERADA))
def test_contas_a_mao_da_linha_base(i, chave):
    estado, n, mediana, desvio, z = O.LINHA_BASE_ESPERADA[(i, chave)]
    m = next(m for m in _linha_base(O.ENTRADAS[i]).metricas if m.chave == chave)
    assert (m.estado, m.n) == (estado, n)
    if mediana is not None:
        assert m.mediana == pytest.approx(mediana, abs=1e-9)
        assert m.desvio == pytest.approx(desvio, abs=0.005)
        assert m.z == pytest.approx(z, abs=0.005)


@pytest.mark.parametrize("i", COM_PACOTE)
def test_textos_das_metricas_sao_os_da_api(i):
    e = O.ENTRADAS[i]
    r = _linha_base(e)
    valores = _valores_da_sessao(e)
    for m, esp in zip(r.metricas, O.PACOTES[i]["linha_base"]["metricas"], strict=True):
        tipo = lbl.METRICAS[m.chave][2]
        if m.estado == "sem_valor":
            assert esp["valor_texto"] is None and esp["mediana_texto"] is None and esp["motivo"]
            continue
        assert esp["valor_texto"] == lbl._texto_valor(tipo, valores[m.chave]), m.chave
        if m.estado in ("dentro", "fora"):
            assert esp["mediana_texto"] == lbl._texto_valor(tipo, m.mediana), m.chave
        else:
            assert esp["mediana_texto"] is None
        if m.estado == "fora":
            assert esp["diferenca_texto"] == lbl._diferenca(tipo, valores[m.chave], m.mediana), m.chave
        else:
            assert esp["diferenca_texto"] is None


@pytest.mark.parametrize("i", COM_PACOTE)
def test_treino_carga_e_checkin_do_pacote(i):
    e = O.ENTRADAS[i]
    a, ck, p = e["atividade"], e["checkin"], O.PACOTES[i]
    t = p["treino"]
    assert (t["modalidade"], t["tipo_treino"], t["duracao_s"], t["distancia_m"], t["fc_media_bpm"]) == (
        a["modalidade"], a["tipo_treino"], a["duracao_s"], a["distancia_m"], a["fc_media"])
    assert t["ambiente"] == ("esteira" if a["subtipo"] == "esteira" else None)
    assert t["duracao_texto"] == duracao_pt(a["duracao_s"] / 60)
    assert t["distancia_texto"] == distancia_da_atividade(a["modalidade"], a["distancia_m"])
    # carga pela PSE: a função pura da Meta 8
    r = cp.carga_pse(ck["pse"], a["duracao_s"], a["subtipo"])
    assert p["carga_pse"]["estado"] == r.estado == "calculada"
    assert p["carga_pse"]["valor"] == pytest.approx(r.valor)
    assert p["carga_pse"]["valor_texto"] == f"{numero_pt(r.valor)} UA"
    # check-in: só escalas e atalhos, nunca o texto
    c = p["checkin"]
    assert (c["pse"], c["sensacao_nivel"], c["nada_a_relatar"], c["atalhos"]) == (
        ck["pse"], ck["sensacao"], ck["nada_a_relatar"], ck["atalhos"])
    assert c["pse_texto"] == svc_checkin.PSE_ANCORA.get(ck["pse"])  # sem âncora: null (ADR 0014)
    assert c["sensacao_texto"] == svc_checkin.SENSACAO_TEXTO[ck["sensacao"]]
    # carga@2 (calculada): o texto é o valor com 1 casa e vírgula
    if p["carga"]["estado"] == "calculada":
        assert p["carga"]["valor"] == e["carga"]
        assert p["carga"]["valor_texto"] == f"{e['carga']:.1f}".replace(".", ",") + " pontos"
    # clima
    cl = e["clima"]
    if isinstance(cl, tuple):
        assert p["clima"] == {"estado": "ok", "temperatura_c": cl[0], "sensacao_termica_c": cl[1], "umidade_pct": cl[2], "vento_kmh": cl[3]}
    elif cl is None:
        assert p["clima"] is None
    else:
        assert p["clima"]["estado"] == cl and p["clima"]["temperatura_c"] is None
