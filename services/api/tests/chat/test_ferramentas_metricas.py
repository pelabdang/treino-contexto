"""Ferramentas de métricas no registro do chat (#594, ADR 0017, itens 1 e 2). Atletas sintéticos; sem rede.

Escopo: o atleta B tem treinos, carga e linha de base; a sessão do A, que não tem nada, não vê um número do B por nenhuma das quatro ferramentas, com e sem
`atleta_id` no argumento. Papel: o professor não recebe a Evolução (`ler_serie`, `comparar_periodos`), só a carga e a linha de base."""

import json
from datetime import date, datetime, timedelta, timezone

import pytest
from app.chat.registro import REGISTRO, Consulta, Quem, esquemas_para, executar
from app.db.models import Atividade, Atleta, CargaAtividade

HOJE = date(2030, 3, 15)
AGORA = datetime(2030, 3, 15, 12, 0, tzinfo=timezone.utc)
NOVAS = {"ler_serie", "comparar_periodos", "ler_carga_forma", "ler_linha_base", "ler_recuperacao"}


def _consulta(atleta_id, papel="atleta"):
    return Consulta(Quem(papel, 1), atleta_id, HOJE)


@pytest.fixture
def mundo(session):
    a, b = Atleta(nome="Atleta A"), Atleta(nome="Atleta B")
    session.add_all([a, b])
    session.flush()
    for i, (d, dur) in enumerate([(5, 1700), (12, 1710), (19, 1720), (30, 1800), (40, 1810), (50, 1830)]):  # os mesmos treinos dos casos à mão
        x = Atividade(atleta_id=b.id, fonte="t", fonte_id=f"b{i}", modalidade="corrida", inicio=AGORA - timedelta(days=d), duracao_s=dur, distancia_m=5000.0,
                      fuso_min=-180, tipo_treino="leve", fc_media=140.0)
        session.add(x)
        session.flush()
        session.add(CargaAtividade(atividade_id=x.id, estado="calculada", carga=60.0, metodo="hrtss", cobertura_pct=100.0, granularidade="atividade",
                                   entrada="x" * 64, versao="carga@2", calculado_em=AGORA))
    session.commit()
    return a, b


CHAMADAS = {
    "ler_serie": {"serie_id": "corrida.pace.leve"},
    "comparar_periodos": {"serie_id": "corrida.pace.leve"},
    "ler_carga_forma": {},
    "ler_linha_base": {"modalidade": "corrida", "tipo_treino": "leve"},
    "ler_recuperacao": {},
}


def test_as_quatro_estao_no_registro():
    assert NOVAS <= set(REGISTRO)
    for nome in NOVAS:
        assert not {"atleta_id", "conta_id", "professor_id"} & set(REGISTRO[nome].esquema["properties"])
        assert REGISTRO[nome].esquema["additionalProperties"] is False


def test_o_dono_ve_os_numeros_e_o_outro_atleta_nada(session, mundo):
    a, b = mundo
    r = executar(session, _consulta(b.id), "comparar_periodos", CHAMADAS["comparar_periodos"])
    assert r["estado"] == "ok" and r["a"]["valor_texto"] == "5:42/km" and r["b"]["valor_texto"] == "6:02/km"  # a mão, em test_ferramentas_chat.py
    assert executar(session, _consulta(b.id), "ler_serie", CHAMADAS["ler_serie"])["estado"] == "ok"
    assert executar(session, _consulta(b.id), "ler_carga_forma", {})["estado"] in ("ok", "parcial")
    assert executar(session, _consulta(b.id), "ler_linha_base", CHAMADAS["ler_linha_base"])["estado"] == "parcial"
    # a sessão do A: nada do B, com e sem `atleta_id` no argumento (que é recusado, nunca aceito em silêncio)
    for nome, args in CHAMADAS.items():
        r = executar(session, _consulta(a.id), nome, args)
        assert r["estado"] == "sem_dados", nome
        assert not {"pontos", "metricas"} & set(r) and "5:4" not in json.dumps(r) and "6:0" not in json.dumps(r), nome
        assert executar(session, _consulta(a.id), nome, {**args, "atleta_id": b.id}) == {"estado": "erro", "codigo": "argumento_invalido", "argumento": "atleta_id"}


def test_o_professor_nao_recebe_a_evolucao_nem_a_recuperacao(session, mundo):
    _, b = mundo
    nomes = {e["function"]["name"] for e in esquemas_para("professor")}
    assert {"ler_carga_forma", "ler_linha_base"} <= nomes and not {"ler_serie", "comparar_periodos", "ler_recuperacao"} & nomes
    for nome in ("ler_serie", "comparar_periodos", "ler_recuperacao"):
        assert executar(session, _consulta(b.id, "professor"), nome, CHAMADAS[nome]) == {"estado": "erro", "codigo": "ferramenta_nao_permitida"}
    assert executar(session, _consulta(b.id, "professor"), "ler_linha_base", CHAMADAS["ler_linha_base"])["estado"] == "parcial"


@pytest.mark.parametrize("nome,args,campo", [
    ("ler_serie", {"serie_id": "corrida.inexistente"}, "serie_id"),
    ("ler_serie", {"serie_id": "corrida.pace.leve", "periodo": "ontem"}, "periodo"),
    ("comparar_periodos", {"serie_id": "corrida.pace.leve", "periodo_a": "outubro"}, "periodo_a"),
    ("comparar_periodos", {"serie_id": "corrida.pace.leve", "periodo_a": "2030-1"}, "periodo_a"),
    ("ler_carga_forma", {"data": "15/03"}, "data"),
    ("ler_linha_base", {"modalidade": "corrida"}, "tipo_treino"),
    ("ler_linha_base", {"modalidade": "futebol", "tipo_treino": "leve"}, "modalidade"),
    ("ler_recuperacao", {"periodo": "ontem"}, "periodo"),
    ("ler_recuperacao", {"de": "01/03"}, "de"),
])
def test_argumentos_invalidos_voltam_como_erro_sem_rodar(session, mundo, nome, args, campo):
    assert executar(session, _consulta(mundo[1].id), nome, args) == {"estado": "erro", "codigo": "argumento_invalido", "argumento": campo}


def test_comparar_semana_pelo_registro(session, mundo):
    r = executar(session, _consulta(mundo[1].id), "comparar_periodos", {"serie_id": "corrida.pace.leve", "periodo_a": "2030-02", "periodo_b": "2030-01"})
    assert r["estado"] in ("ok", "parcial") and r["periodo_a_texto"].startswith("mês 02/2030")


def test_recuperacao_pelo_registro_so_do_dono(session, mundo):
    from app.servicos.recuperacao_banco import gravar_noite

    a, b = mundo
    gravar_noite(session, b.id, date(2030, 3, 14), 25200, 48.0, 52, "rec@1", AGORA)
    session.commit()
    r = executar(session, _consulta(b.id), "ler_recuperacao", {})
    assert r["estado"] == "ok" and r["noites"][0]["data_texto"] == "qui 14/03" and r["noites"][0]["medidas"][0]["valor_texto"] == "7 h"
    r = executar(session, _consulta(a.id), "ler_recuperacao", {})
    assert r["estado"] == "sem_dados" and "noites" not in r  # a sessão do A nunca vê a noite do B


def test_os_resultados_trazem_o_serie_id_que_a_rota_usa_para_o_link_da_evolucao(session, mundo):
    """A rota do chat (#618) monta o "Abrir na Evolução" a partir do `serie_id` que aparece em qualquer nível do resultado: as duas ferramentas da Evolução o devolvem, em `ok` e em `sem_dados`."""
    _, b = mundo
    for nome in ("ler_serie", "comparar_periodos"):
        for serie in ("corrida.pace.leve", "natacao.ritmo"):  # a segunda não tem treino: sem_dados
            r = executar(session, _consulta(b.id), nome, {"serie_id": serie})
            assert r.get("serie_id") == serie, (nome, serie, r["estado"])
