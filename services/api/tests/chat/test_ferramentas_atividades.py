"""Ferramentas de atividades e check-ins do chat (#593, ADR 0017). Atletas e numeros sinteticos, sem rede.

Escopo: para CADA ferramenta registrada, dois atletas; a sessao do A pedindo o id do B, com e sem `atleta_id` no argumento, nao devolve
nada do B. Um teste de cobertura percorre o registro e falha para ferramenta nova sem o caso.
"""

import json
from datetime import date, datetime, timezone

import pytest
from app.chat import registro as reg
from app.chat.registro import REGISTRO, Consulta, Quem, esquemas_para, executar
from app.db.models import Atividade, Atleta, CheckinTreino

HOJE = date(2030, 3, 15)
MARCA_B = "MARCA-SINTETICA-DO-ATLETA-B"


def _consulta(atleta_id, papel="atleta"):
    return Consulta(Quem(papel, 1), atleta_id, HOJE)


def _atividade(session, atleta, dia, fonte_id, distancia=8200.0, duracao=2820.0, modalidade="corrida", tipo="leve", fc=146.0):
    a = Atividade(atleta_id=atleta.id, fonte="garmin_export", fonte_id=fonte_id, modalidade=modalidade, inicio=datetime(2030, 3, dia, 9, 0, tzinfo=timezone.utc),
                  fuso_min=-180, duracao_s=duracao, distancia_m=distancia, fc_media=fc, tipo_treino=tipo)
    session.add(a)
    session.flush()
    return a


def _checkin(session, a, pse=4, sensacao=4, texto=None, dor=False):
    c = CheckinTreino(atividade_id=a.id, pse=pse, sensacao=sensacao, nada_a_relatar=texto is None and not dor, dor=dor, texto=texto,
                      versao="checkin@1", registrado_em=datetime(2030, 3, 15, tzinfo=timezone.utc), atualizado_em=datetime(2030, 3, 15, tzinfo=timezone.utc))
    session.add(c)
    session.flush()
    return c


@pytest.fixture
def dois(session):
    a, b = Atleta(nome="Atleta A"), Atleta(nome="Atleta B")
    session.add_all([a, b])
    session.flush()
    return a, b


@pytest.fixture
def mundo(session, dois):
    a, b = dois
    a1 = _atividade(session, a, 14, "a1")
    a2 = _atividade(session, a, 2, "a2", distancia=21400.0, duracao=7500.0, tipo="longo", fc=152.0)
    a3 = _atividade(session, a, 10, "a3", modalidade="ciclismo", distancia=40000.0, duracao=5400.0, tipo=None, fc=None)
    b1 = _atividade(session, b, 14, "b1", distancia=5000.0, duracao=1500.0)
    _checkin(session, a1, pse=4, sensacao=4)
    _checkin(session, a2, pse=7, sensacao=2, texto="Dormi pouco e saí tarde.", dor=True)
    _checkin(session, b1, pse=9, sensacao=1, texto=MARCA_B)
    session.commit()
    return a, b, a1, a2, a3, b1


def test_listar_atividades_devolve_texto_pronto_e_so_do_atleta(session, mundo):
    a, _, a1, a2, a3, _ = mundo
    r = executar(session, _consulta(a.id), "listar_atividades", {"periodo": "ultimos_7_dias", "ordem": "recentes", "limite": 1})
    assert r["versao"] == "lista_atividades@1" and r["estado"] == "ok" and r["total"] == 2  # a1 (14/03) e a3 (10/03)
    [item] = r["atividades"]
    assert item == {"atividade_id": a1.id, "data_texto": "14/03", "modalidade": "corrida", "tipo_treino": "leve", "distancia_texto": "8,20 km",
                    "duracao_texto": "47 min", "pace_texto": "5:44/km", "fc_media_texto": "146 bpm", "checkin": "feito"}
    assert r["periodo_texto"] == "últimos 7 dias"


def test_listar_atividades_filtros_e_ordem(session, mundo):
    a, _, a1, a2, a3, _ = mundo
    maiores = executar(session, _consulta(a.id), "listar_atividades", {"ordem": "maiores", "limite": 1})["atividades"][0]
    assert maiores["atividade_id"] == a3.id and maiores["velocidade_texto"] == "26,7 km/h" and "pace_texto" not in maiores
    corrida = executar(session, _consulta(a.id), "listar_atividades", {"modalidade": "corrida", "periodo": "ultimo_ano"})
    assert [x["atividade_id"] for x in corrida["atividades"]] == [a1.id, a2.id]
    longos = executar(session, _consulta(a.id), "listar_atividades", {"tipo_treino": "longo"})
    assert [x["atividade_id"] for x in longos["atividades"]] == [a2.id]
    de_ate = executar(session, _consulta(a.id), "listar_atividades", {"de": "2030-03-01", "ate": "2030-03-09"})
    assert de_ate["total"] == 1 and de_ate["atividades"][0]["data_texto"] == "02/03"


def test_listar_atividades_sem_resultado_diz_o_motivo(session, mundo):
    a = mundo[0]
    r = executar(session, _consulta(a.id), "listar_atividades", {"modalidade": "natacao"})
    assert r["estado"] == "sem_dados" and r["total"] == 0 and r["atividades"] == [] and r["motivo_texto"]


@pytest.mark.parametrize("args", [
    {"periodo": "ontem"}, {"limite": 0}, {"limite": 21}, {"modalidade": "remo"}, {"tipo_treino": "x"}, {"ordem": "aleatoria"},
    {"periodo": "ultimo_ano", "de": "2030-01-01", "ate": "2030-02-01"}, {"de": "2030-01-01"}, {"de": "2030-02-31", "ate": "2030-03-01"},
    {"de": "2030-03-10", "ate": "2030-03-01"}, {"limite": "10"}, {"limite": True}, {"inventado": 1},
])
def test_argumentos_invalidos_viram_erro_sem_rodar(session, mundo, args):
    r = executar(session, _consulta(mundo[0].id), "listar_atividades", args)
    assert r["estado"] == "erro" and r["codigo"] == "argumento_invalido"


def test_ver_atividade_traz_o_pacote_e_a_observacao(session, mundo):
    a, _, a1, a2, a3, _ = mundo
    r = executar(session, _consulta(a.id), "ver_atividade", {"atividade_id": a2.id})
    assert r["estado"] == "ok" and r["atividade_id"] == a2.id and r["data_texto"] == "02/03"
    assert r["treino"]["distancia_texto"] == "21,40 km" and r["treino"]["pace_texto"] == "5:50/km"
    assert r["checkin"]["pse"] == 7 and r["checkin"]["sensacao_texto"] == "mal" and r["checkin"]["atalhos"] == ["dor"]
    assert r["checkin"]["observacao_texto"] == "Dormi pouco e saí tarde."
    assert set(r) >= {"treino", "linha_base", "esforcos", "clima", "carga", "carga_pse", "checkin"}
    sem = executar(session, _consulta(a.id), "ver_atividade", {"atividade_id": a3.id})
    assert sem["estado"] == "ok" and sem["checkin"] is None and sem["carga_pse"] is None and sem["motivo_texto"]


def test_atividade_de_outro_e_inexistente_dao_o_mesmo_resultado(session, mundo):
    a, _, _, _, _, b1 = mundo
    de_outro = executar(session, _consulta(a.id), "ver_atividade", {"atividade_id": b1.id})
    inexistente = executar(session, _consulta(a.id), "ver_atividade", {"atividade_id": 987654})
    assert json.dumps(de_outro, sort_keys=True) == json.dumps(inexistente, sort_keys=True)
    assert de_outro == {"estado": "erro", "codigo": "nao_encontrada"}


def test_listar_checkins_com_observacao_e_atalhos(session, mundo):
    a, _, a1, a2, *_ = mundo
    r = executar(session, _consulta(a.id), "listar_checkins", {"periodo": "ultimas_12_semanas"})
    assert r["versao"] == "checkin@1" and r["estado"] == "ok" and r["total"] == 2
    assert [x["atividade_id"] for x in r["checkins"]] == [a2.id, a1.id]  # do mais antigo ao mais novo
    assert r["checkins"][0] == {"data_texto": "02/03", "atividade_id": a2.id, "pse_texto": "7", "sensacao_texto": "mal", "atalhos": ["dor"],
                                "observacao_texto": "Dormi pouco e saí tarde."}
    assert "observacao_texto" not in r["checkins"][1]
    assert executar(session, _consulta(a.id), "listar_checkins", {"periodo": "ultimos_7_dias", "limite": 1})["checkins"][0]["atividade_id"] == a1.id
    vazio = executar(session, _consulta(a.id), "listar_checkins", {"de": "2029-01-01", "ate": "2029-01-31"})
    assert vazio["estado"] == "sem_dados" and vazio["checkins"] == [] and vazio["motivo_texto"]


# --- escopo e papel -------------------------------------------------------------------------------------------------------------------

def _chamadas_de_escopo(b1):
    """Para cada ferramenta registrada: argumentos que apontam para dados do atleta B (por id) ou so pedem tudo."""
    return {
        "listar_atividades": [{}, {"periodo": "ultimo_ano"}],
        "ver_atividade": [{"atividade_id": b1.id}],
        "listar_checkins": [{}, {"periodo": "ultimo_ano"}],
        # as ferramentas de métricas (#594) têm o escopo provado em `test_ferramentas_metricas.py`; aqui só entram para o teste de cobertura
        "ler_serie": [{"serie_id": "corrida.pace.leve"}],
        "comparar_periodos": [{"serie_id": "corrida.pace.leve"}],
        "ler_carga_forma": [{}],
        "ler_linha_base": [{"modalidade": "corrida", "tipo_treino": "leve"}],
    }


def test_nenhuma_ferramenta_devolve_dado_do_outro_atleta(session, mundo):
    a, b, *_, b1 = mundo
    casos = _chamadas_de_escopo(b1)
    for nome, lista in casos.items():
        for args in lista:
            for extra in ({}, {"atleta_id": b.id}):  # com `atleta_id` o argumento e RECUSADO, nunca aceito em silencio
                r = executar(session, _consulta(a.id), nome, {**args, **extra})
                texto = json.dumps(r, ensure_ascii=False)
                assert MARCA_B not in texto and str(b1.id) not in json.dumps([x.get("atividade_id") for x in r.get("atividades", r.get("checkins", []))]), (nome, args, extra)
                if extra:
                    assert r == {"estado": "erro", "codigo": "argumento_invalido", "argumento": "atleta_id"}


def test_toda_ferramenta_registrada_tem_caso_de_escopo(session, mundo):
    """Ferramenta nova sem caso em `_chamadas_de_escopo` falha aqui (ADR 0017, item 2)."""
    *_, b1 = mundo
    assert set(REGISTRO) == set(_chamadas_de_escopo(b1)), "ferramenta registrada sem teste de escopo"


def test_esquemas_nao_tem_campo_de_atleta_e_recusam_extra():
    for f in REGISTRO.values():
        assert f.esquema["additionalProperties"] is False
        assert not {"atleta_id", "conta_id", "professor_id"} & set(f.esquema["properties"])


def test_esquemas_enviados_ao_provedor_so_do_papel():
    nomes = {e["function"]["name"] for e in esquemas_para("atleta")}
    assert {"listar_atividades", "ver_atividade", "listar_checkins"} <= nomes
    assert esquemas_para("outro_papel") == []


def test_executor_confere_papel_e_nome(session, mundo):
    a = mundo[0]
    assert executar(session, _consulta(a.id, papel="outro"), "listar_atividades", {}) == {"estado": "erro", "codigo": "ferramenta_nao_permitida"}
    assert executar(session, _consulta(a.id), "apagar_tudo", {}) == {"estado": "erro", "codigo": "ferramenta_desconhecida"}
    assert executar(session, _consulta(a.id), "ver_atividade", {})["codigo"] == "argumento_invalido"  # falta atividade_id


def test_falha_da_ferramenta_vira_codigo_sem_a_mensagem(session, mundo, monkeypatch):
    def quebra(*_a, **_k):
        raise RuntimeError(f"segredo {MARCA_B}")
    f = REGISTRO["listar_atividades"]
    monkeypatch.setitem(REGISTRO, "listar_atividades", reg.Ferramenta(f.nome, f.descricao, f.esquema, f.papeis, quebra))
    r = executar(session, _consulta(mundo[0].id), "listar_atividades", {})
    assert r == {"estado": "erro", "codigo": "ferramenta_erro", "tipo": "RuntimeError"} and MARCA_B not in json.dumps(r)
