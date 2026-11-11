"""Adaptador do pacote de fatos (issue #327): o pacote que sai do BANCO de teste e igual ao do oraculo da #323.

Cada caso do oraculo (`tests/fixtures/meta9/oraculo.py`) e semeado no banco: a atividade, o historico da janela de 12 semanas (um
treino por semana, com os valores que o oraculo manda), a carga, o clima, os blocos dos tiros e o check-in. O adaptador le tudo
com os servicos da API (linha de base, clima, carga, esforcos) e chama a funcao pura. Tudo sintetico; o texto livre do check-in
e um marcador que nunca pode aparecer no pacote.
"""

import hashlib
import importlib.util
import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from app.db.models import Atividade, Atleta, BlocoAtividade, CargaAtividade, CheckinTreino, ClimaAtividade
from app.explicacao.fatos_treino import VERSAO
from app.metricas import carga as cg
from app.metricas import esforcos as esf
from app.servicos.clima import entrada_de
from app.servicos.feedback_fatos import _rotulo_faixa, fatos_da_atividade

PASTA = Path(__file__).parents[4] / "tests" / "fixtures" / "meta9"
_spec = importlib.util.spec_from_file_location("oraculo_meta9_adaptador", PASTA / "oraculo.py")
O = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = O
_spec.loader.exec_module(O)

HOJE = datetime(2026, 11, 9, 9, 0, tzinfo=UTC)
METODO = {"F01": "rtss", "F02": "rtss", "F03": "hrtss", "F04": "rtss", "F07": "rtss", "F08": "rtss", "F09": "hrtss"}
COM_PACOTE = [i for i in O.ENTRADAS if O.PACOTES[i] is not None]


def _carga(a_id, valor, metodo):
    return CargaAtividade(atividade_id=a_id, estado="calculada", carga=valor, metodo=metodo, cobertura_pct=100.0,
                          granularidade="atividade", entrada="x", versao=cg.VERSAO, calculado_em=HOJE)


def _blocos_de_tiros(a_id, pace, fc, n=5):
    """`n` tiros de 1 km (esforco, d1000) separados por recuperacao: o que `esforcos@1` grava numa sessao intervalada."""
    ordem = 0
    for k in range(n):
        ordem += 1
        yield BlocoAtividade(atividade_id=a_id, ordem=ordem, categoria="esforco", volta_inicial=ordem, volta_final=ordem,
                             inicio_offset_s=0.0, duracao_s=float(pace), parada_apos_s=60.0, distancia_m=1000.0,
                             fc_media=float(fc), pace_s_km=float(pace), faixa="d1000", treino_chave=False,
                             versao_deteccao=esf.VERSAO)
        if k < n - 1:
            ordem += 1
            yield BlocoAtividade(atividade_id=a_id, ordem=ordem, categoria="recuperacao", volta_inicial=ordem,
                                 volta_final=ordem, inicio_offset_s=0.0, duracao_s=90.0, parada_apos_s=0.0,
                                 distancia_m=200.0, fc_media=float(fc) - 20, pace_s_km=450.0, faixa=None,
                                 treino_chave=False, versao_deteccao=esf.VERSAO)


def _semear(session, caso):
    e = O.ENTRADAS[caso]
    a = e["atividade"]
    atleta = Atleta(nome="Atleta Ficticio")
    session.add(atleta)
    session.flush()
    esteira = a["subtipo"] == "esteira"
    hist = e["historico"]
    n = max((len(x) for x in hist.values()), default=0)
    for k in range(n):
        v = {c: (xs[k] if k < len(xs) else None) for c, xs in hist.items()}
        pace = v.get("pace_medio")
        dur = pace * 10 if pace else 3000.0
        dt = HOJE - timedelta(days=7 * (n - k))
        h = Atividade(atleta_id=atleta.id, fonte="t", fonte_id=f"h{k}", modalidade=a["modalidade"], subtipo=a["subtipo"],
                      tipo_treino=a["tipo_treino"], inicio=dt, fuso_min=0, duracao_s=dur, distancia_m=10000.0,
                      fc_media=v.get("fc_media"))
        session.add(h)
        session.flush()
        if v.get("carga_hora") is not None:
            session.add(_carga(h.id, v["carga_hora"] * dur / 3600, "rtss"))
        if v.get("melhor_pace") is not None:
            session.add_all(_blocos_de_tiros(h.id, v["melhor_pace"], v["fc_melhor_tiro"]))
    ativ = Atividade(atleta_id=atleta.id, fonte="t", fonte_id="s", modalidade=a["modalidade"], subtipo=a["subtipo"],
                     tipo_treino=a["tipo_treino"], inicio=HOJE, fuso_min=0, duracao_s=float(a["duracao_s"]),
                     distancia_m=float(a["distancia_m"]), fc_media=a["fc_media"],
                     inicio_lat=None if a["modalidade"] == "natacao" or esteira else -23.55,
                     inicio_lon=None if a["modalidade"] == "natacao" or esteira else -46.63)
    session.add(ativ)
    session.flush()
    if e["carga"] is not None:
        session.add(_carga(ativ.id, e["carga"], METODO[caso]))
    elif a["modalidade"] == "natacao":
        session.add(CargaAtividade(atividade_id=ativ.id, estado="sem_carga", motivo="modalidade_sem_carga",
                                   granularidade="atividade", entrada="x", versao=cg.VERSAO, calculado_em=HOJE))
    if "melhor_tiro" in e:
        session.add_all(_blocos_de_tiros(ativ.id, e["melhor_tiro"]["pace_s_km"], e["melhor_tiro"]["fc_bpm"]))
    if isinstance(e["clima"], tuple):
        t, s, u, v = e["clima"]
        session.add(ClimaAtividade(atividade_id=ativ.id, estado="ok", temperatura_c=t, sensacao_c=s, umidade_pct=u, vento_kmh=v,
                                   fonte="teste", entrada=entrada_de(ativ), tentativas=1, consultado_em=HOJE))
    elif e["clima"] == "pendente":
        ativ.inicio_lat, ativ.inicio_lon = -23.55, -46.63  # ao ar livre, nunca consultado
    c = e["checkin"]
    checkin = None
    if c is not None:
        checkin = CheckinTreino(
            atividade_id=ativ.id, pse=c["pse"], sensacao=c["sensacao"], nada_a_relatar=c["nada_a_relatar"],
            texto=c["texto"], versao="checkin@1", registrado_em=HOJE, atualizado_em=HOJE,
            **{k: k in c["atalhos"] for k in ("dor", "cansaco", "sono_ruim", "calor", "trabalho_estresse")})
        session.add(checkin)
    session.commit()
    return ativ, checkin


@pytest.mark.parametrize("caso", COM_PACOTE)
def test_o_pacote_do_banco_e_igual_ao_do_oraculo(session, caso):
    ativ, checkin = _semear(session, caso)
    assert fatos_da_atividade(session, ativ, checkin) == O.PACOTES[caso]


@pytest.mark.parametrize("caso", ["F07", "F08"])
def test_sem_checkin_ou_nao_elegivel_nao_ha_pacote(session, caso):
    ativ, checkin = _semear(session, caso)
    assert O.PACOTES[caso] is None and fatos_da_atividade(session, ativ, checkin) is None


def test_o_texto_livre_do_checkin_nunca_entra_no_pacote(session):
    ativ, checkin = _semear(session, "F05")
    assert checkin.texto == O.MARCADOR_TEXTO_LIVRE
    pacote = fatos_da_atividade(session, ativ, checkin)
    assert O.MARCADOR_TEXTO_LIVRE not in json.dumps(pacote, ensure_ascii=False)
    chaves = json.dumps(list(_chaves(pacote)))
    for proibida in ("atleta", "atividade_id", "inicio", "lat", "lon", "arquivo", "texto_livre", "observacao"):
        assert f'"{proibida}"' not in chaves
    assert pacote["versao"] == VERSAO


def _chaves(x):
    if isinstance(x, dict):
        for k, v in x.items():
            yield k
            yield from _chaves(v)
    elif isinstance(x, list):
        for v in x:
            yield from _chaves(v)


def test_adaptador_so_le_nao_grava(session):
    ativ, checkin = _semear(session, "F02")
    antes = hashlib.sha256(repr(sorted(
        session.connection().exec_driver_sql("SELECT * FROM carga_atividade").all())).encode()).hexdigest()
    fatos_da_atividade(session, ativ, checkin)
    session.rollback()
    depois = hashlib.sha256(repr(sorted(
        session.connection().exec_driver_sql("SELECT * FROM carga_atividade").all())).encode()).hexdigest()
    assert antes == depois


@pytest.mark.parametrize("faixa,rotulo", [("d200", "200 m"), ("d400", "400 m"), ("d1000", "1 km"), ("d1500", "1,5 km"),
                                          ("d5000", "5 km"), ("t4", "4 min"), ("t30", "30 min")])
def test_rotulo_da_faixa(faixa, rotulo):
    assert _rotulo_faixa(faixa) == rotulo
