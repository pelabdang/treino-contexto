"""`linha_base` e o tipo no GET da atividade (issue #266, ADR 0011), contra o oraculo das fixtures da Meta 7 (#261).

O tipo vem do oraculo (`TIPO_ESPERADO`, ja gravado como a #265 grava); a linha de base e calculada pela API na leitura.
Dados sinteticos: nenhum dado real.
"""

import importlib.util
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest
from app.db.models import (
    Atividade,
    Atleta,
    BlocoAtividade,
    CargaAtividade,
    RotuloTransicao,
)
from app.db.session import get_session
from app.main import criar_app
from app.metricas import carga as cg
from app.metricas import esforcos as ef
from fastapi.testclient import TestClient

PASTA = Path(__file__).parents[4] / "tests" / "fixtures" / "meta7"


def _oraculo():
    spec = importlib.util.spec_from_file_location("oraculo_meta7_api", PASTA / "oraculo.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


O = _oraculo()
FIXTURES = json.loads((PASTA / "atividades.json").read_text(encoding="utf-8"))["atividades"]


def _blocos(a, estrutura, tiros):
    def b(ordem, cat, dur, dist, fc=None, faixa=None):
        a.blocos.append(BlocoAtividade(
            ordem=ordem, categoria=cat, volta_inicial=ordem, volta_final=ordem, inicio_offset_s=0.0, duracao_s=dur,
            distancia_m=dist, fc_media=fc, pace_s_km=dur / dist * 1000, faixa=faixa, versao_deteccao=ef.VERSAO))

    if estrutura == "sem_esforco":
        b(0, "leve", a.duracao_s, a.distancia_m)
    elif estrutura == "tiros":
        b(0, "aquecimento", 600, 1500)
        ordem = 1
        for _ in range(tiros["n"]):  # todos no ritmo do melhor tiro; a FC do melhor tiro e a de todos
            b(ordem, "esforco", tiros["melhor_pace_s_km"], 1000, tiros["fc_melhor_tiro"], "d1000")
            b(ordem + 1, "recuperacao", 200, 500)
            ordem += 2
        b(ordem, "desaquecimento", 600, 1500)


@pytest.fixture
def client(session):
    app = criar_app("http://localhost:8081")
    app.dependency_overrides[get_session] = lambda: session
    return TestClient(app)


@pytest.fixture
def banco(session):
    """Atleta com as 81 atividades: tipos do oraculo, blocos dos tiros, cargas calculadas e rotulos de transicao."""
    atleta = Atleta(nome="Ficticio")
    session.add(atleta)
    session.flush()
    ids = {}
    for f in FIXTURES:
        tipo, origem, div = O.TIPO_ESPERADO[f["id"]]
        a = Atividade(
            atleta_id=atleta.id, fonte="fixture", fonte_id=f["id"], modalidade=f["modalidade"], subtipo=f["subtipo"],
            inicio=datetime.fromisoformat(f["inicio"]), fuso_min=f["fuso_min"], duracao_s=f["duracao_s"],
            distancia_m=f["distancia_m"], fc_media=f["fc_media"], tipo_treino=tipo, tipo_origem=origem,
            tipo_confirmado=f["tipo_confirmado"], tipo_divergencia=div,
            tipo_versao="tipo_treino@1" if origem in ("sugestao", "semana_padrao") else None)
        session.add(a)
        _blocos(a, f["estrutura"], f["tiros"])
        if f["carga"] is not None:
            a.carga = CargaAtividade(
                estado="calculada", carga=f["carga"], metodo="hrtss", cobertura_pct=100.0, granularidade="atividade",
                entrada="x" * 64, versao=cg.VERSAO, calculado_em=datetime(2026, 4, 1, tzinfo=UTC))
        if f["transicao"]:
            a.rotulo_transicao = RotuloTransicao(
                transicao=True, origem="atleta", definido_em=datetime(2026, 4, 1, tzinfo=UTC))
        ids[f["id"]] = a
    session.commit()
    return atleta.id, {k: v.id for k, v in ids.items()}


def _get(client, banco, chave):
    atleta_id, ids = banco
    r = client.get(f"/atletas/{atleta_id}/atividades/{ids[chave]}")
    assert r.status_code == 200, r.text
    return r.json()


@pytest.mark.parametrize("chave", sorted(O.LINHA_BASE_ESPERADA))
def test_linha_de_base_igual_ao_oraculo(client, banco, chave):
    lb = _get(client, banco, chave)["linha_base"]
    assert lb["versao"] == "linha_base@2" and lb["estado"] == "ok" and lb["motivo"] is None
    assert lb["janela_semanas"] == 12 and lb["minimo_treinos"] == 8
    esperado = O.LINHA_BASE_ESPERADA[chave]
    assert sorted(m["chave"] for m in lb["metricas"]) == sorted(esperado)  # as metricas do tipo
    for m in lb["metricas"]:
        estado, n, mediana, desvio, z = esperado[m["chave"]]
        assert (m["estado"], m["n"]) == (estado, n), m["chave"]
        for campo, v in (("mediana", mediana), ("desvio", desvio), ("z", z)):
            if v is None:
                assert m[campo] is None, (m["chave"], campo)
            else:
                assert m[campo] == pytest.approx(v, abs=1e-3), (m["chave"], campo)


@pytest.mark.parametrize("chave", sorted(O.SEM_LINHA_BASE))
def test_sem_linha_de_base_traz_o_motivo(client, banco, chave):
    lb = _get(client, banco, chave)["linha_base"]
    assert lb["estado"] == "sem_linha_base" and lb["motivo"] == O.SEM_LINHA_BASE[chave]
    assert lb["metricas"] == [] and lb["texto"].startswith("Sem linha de base: ")


def test_texto_de_fora_e_o_da_adr(client, banco):
    j = _get(client, banco, "2026-03-13/cor1")
    assert j["tipo_treino"] == "leve" and j["tipo_origem"] == "sugestao" and j["tipo_divergencia"] is None
    m = j["linha_base"]["metricas"][0]
    assert (m["valor"], m["valor_texto"], m["mediana_texto"], m["diferenca_texto"]) == (306.0, "5:06/km", "5:30/km", "24 s/km mais rápido")
    assert m["texto"] == (
        "Pace médio fora do seu normal para treino leve: 5:06/km, 24 s/km mais rápido que a mediana de 5:30/km "
        "(11 treinos nas últimas 12 semanas). Isto compara com o seu histórico; não diz se o treino foi bom ou ruim.")


def test_texto_de_dentro_e_de_aprendendo(client, banco):
    ms = {m["chave"]: m for m in _get(client, banco, "2026-03-20/cor1")["linha_base"]["metricas"]}
    assert ms["pace_medio"]["texto"] == (
        "Pace médio dentro do seu normal para treino leve: 5:30/km, perto da mediana de 5:30/km (12 treinos nas últimas 12 semanas).")
    assert ms["fc_media"]["estado"] == "dentro" and ms["fc_media"]["n"] == 9
    # aprendendo: a natação leve de 16/03 tem só 2 treinos do tipo na janela
    nat = _get(client, banco, "2026-03-16/nat1")["linha_base"]["metricas"][0]
    assert nat["estado"] == "aprendendo" and nat["mediana"] is None and nat["z"] is None and nat["mediana_texto"] is None
    assert nat["texto"] == "Ainda aprendendo o seu normal em treino leve: 2 de 8 treinos nas últimas 12 semanas."
    assert nat["valor_texto"].endswith(" bpm")


def test_sem_valor_explica_o_motivo(client, banco):
    ms = {m["chave"]: m for m in _get(client, banco, "2026-03-13/cor1")["linha_base"]["metricas"]}
    assert ms["carga_hora"]["estado"] == "sem_valor" and ms["carga_hora"]["motivo"] == "carga_pendente" and ms["carga_hora"]["valor"] is None
    assert ms["carga_hora"]["texto"] == "Sem carga por hora neste treino: a carga ainda não foi calculada."


def test_carga_por_hora_com_a_mesma_unidade_no_valor_e_na_diferenca(client, banco):
    m = {m["chave"]: m for m in _get(client, banco, "2026-03-18/cic1")["linha_base"]["metricas"]}["carga_hora"]
    assert m["estado"] == "fora" and m["rotulo"] == "Carga por hora" and m["unidade"] == "pontos/h"
    assert (m["valor_texto"], m["mediana_texto"], m["diferenca_texto"]) == ("55,0 pontos/h", "42,0 pontos/h", "13,0 pontos/h maior")
    assert m["texto"].startswith("Carga por hora fora do seu normal para treino leve: 55,0 pontos/h, 13,0 pontos/h maior que a mediana de 42,0 pontos/h (")


def test_carga_por_hora_divide_pela_duracao(client, banco):
    # brick de 10/01: carga 30 em 2700 s (0,75 h) = 40 pontos/h; aprendendo, sem mediana
    j = _get(client, banco, "2026-01-10/cic1")
    assert j["linha_base"]["estado"] == "ok"
    m = {m["chave"]: m for m in j["linha_base"]["metricas"]}["carga_hora"]
    assert (m["estado"], m["valor"], m["valor_texto"], m["n"]) == ("aprendendo", 40.0, "40,0 pontos/h", 0)
    assert m["texto"] == "Ainda aprendendo o seu normal em treino moderado (parte de transição): 0 de 8 treinos nas últimas 12 semanas."


def test_esteira_nao_entra_no_pace_mas_a_fc_segue(client, banco):
    ms = {m["chave"]: m for m in _get(client, banco, "2026-01-06/cor1")["linha_base"]["metricas"]}
    assert ms["melhor_pace"]["estado"] == "sem_valor" and ms["melhor_pace"]["motivo"] == "esteira"
    assert ms["fc_melhor_tiro"]["valor"] == 172.0 and ms["fc_melhor_tiro"]["estado"] == "aprendendo"


def test_sem_fc_na_sessao_e_sem_valor(client, banco, session):
    atleta_id, ids = banco
    session.get(Atividade, ids["2026-03-20/cor1"]).fc_media = None
    session.commit()
    ms = {m["chave"]: m for m in _get(client, banco, "2026-03-20/cor1")["linha_base"]["metricas"]}
    assert ms["fc_media"]["estado"] == "sem_valor" and ms["fc_media"]["motivo"] == "sem_fc"
    assert ms["fc_media"]["texto"] == "Sem FC média neste treino: o treino não tem frequência cardíaca."


def test_divergencias_com_texto_pronto(client, banco):
    j = _get(client, banco, "2026-01-13/cor1")
    assert j["tipo_treino"] == "intervalado" and j["tipo_origem"] == "semana_padrao"
    assert j["tipo_divergencia"] == {
        "motivo": "sem_esforco", "texto": "O plano diz intervalado, mas o treino não teve esforço detectado."}
    j = _get(client, banco, "2026-03-28/cor1")
    assert j["tipo_divergencia"]["motivo"] == "tem_tiros"
    assert j["tipo_divergencia"]["texto"] == "O plano diz longo, mas o treino teve 6 tiros de 1 km."
    assert j["linha_base"]["motivo"] == "divergente"
    assert _get(client, banco, "2026-03-13/cor1")["tipo_divergencia"] is None


def test_tipo_confirmado_e_origem_aparecem(client, banco):
    j = _get(client, banco, "2026-01-15/cor1")
    assert (j["tipo_treino"], j["tipo_origem"], j["tipo_confirmado"]) == ("moderado", None, True)
    assert _get(client, banco, "2026-01-29/cor1")["tipo_origem"] == "trainingpeaks"


def test_a_sessao_nao_entra_na_propria_linha_de_base_e_so_o_passado(client, banco):
    """Intervalado de 20/01 (n = 1: so a sexta 09/01; a esteira de 06/01 nao tem pace) e o de 27/01 (n = 2): cada um conta so o passado."""
    primeira = _get(client, banco, "2026-01-20/cor2")["linha_base"]["metricas"][0]
    assert primeira["chave"] == "melhor_pace" and primeira["n"] == 1
    segunda = _get(client, banco, "2026-01-27/cor1")["linha_base"]["metricas"][0]
    assert segunda["n"] == 2


def test_404_continua(client, banco):
    atleta_id, ids = banco
    assert client.get(f"/atletas/{atleta_id}/atividades/999999").status_code == 404


def test_campos_antigos_continuam(client, banco):
    j = _get(client, banco, "2026-03-13/cor1")
    for campo in ("atividade_id", "modalidade", "clima", "esforcos", "transicao", "carga", "data_local", "pace_medio", "distancia"):
        assert campo in j
