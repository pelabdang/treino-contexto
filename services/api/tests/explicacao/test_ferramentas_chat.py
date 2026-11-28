"""Ferramentas de consulta do chat sobre as métricas (issue #594, ADR 0017, item 1). Atletas e treinos 100% sintéticos; o "hoje" é 15/03/2030.

Cada valor esperado está calculado à mão no comentário do caso; a ferramenta só lê o que a API já calcula (`frase_evolucao@1`, `serie_carga@2`,
`frase_forma@1`, `linha_base@3`) e entrega em texto pronto, igual ao da rota da Evolução para a mesma série."""

from datetime import datetime, timedelta, timezone

import pytest
from app.db.models import Atividade, Atleta, CargaAtividade
from app.explicacao import ferramentas_chat as fc
from app.servicos import evolucao_serie as ev

AGORA = datetime(2030, 3, 15, 12, 0, tzinfo=timezone.utc)  # hoje = 15/03/2030 (fuso -180)


def _ativ(session, atleta, n, dias_atras, dur, dist=5000.0, fc_media=140.0, tipo="leve", modalidade="corrida", carga=None):
    a = Atividade(atleta_id=atleta.id, fonte="t", fonte_id=str(n), modalidade=modalidade, inicio=AGORA - timedelta(days=dias_atras),
                  duracao_s=dur, distancia_m=dist, fuso_min=-180, tipo_treino=tipo, fc_media=fc_media)
    session.add(a)
    session.flush()
    if carga is not None:
        session.add(CargaAtividade(atividade_id=a.id, estado="calculada", carga=carga, metodo="hrtss", cobertura_pct=100.0, granularidade="atividade",
                                   entrada="x" * 64, versao="carga@2", calculado_em=AGORA))
    return a


@pytest.fixture
def atleta(session):
    x = Atleta(nome="Ficticio A")
    session.add(x)
    session.flush()
    return x


def _leves(session, x):
    """Janela R (15/02 a 14/03): treinos há 5, 12 e 19 dias, de 5 km em 1700, 1710 e 1720 s. Janela A (18/01 a 14/02): há 30, 40 e 50 dias, em 1800, 1810, 1830 s."""
    for i, (d, dur) in enumerate([(5, 1700), (12, 1710), (19, 1720), (30, 1800), (40, 1810), (50, 1830)]):
        _ativ(session, x, i, d, dur, fc_media=[142, 144, 146, 150, 152, 154][i])
    session.commit()


def test_comparar_periodos_pace_leve_a_mao(session, atleta):
    _leves(session, atleta)
    # pace por treino em s/km = dur / 5 km: R = 340, 342, 344 (mediana 342 = 5:42); A = 360, 362, 366 (mediana 362 = 6:02).
    # d = 342 - 362 = -20; limite = max(0, 3% x 362 = 10,86) = 10,86 -> |d| >= limite: "menor" (mais rápido), diferença 20 s/km, margem mostrada 11 s/km.
    r = fc.comparar_periodos(session, atleta.id, "corrida.pace.leve", agora=AGORA)
    assert r["estado"] == "ok" and r["direcao"] == "menor"
    assert r["a"] == {"n": 3, "valor_texto": "5:42/km"} and r["b"] == {"n": 3, "valor_texto": "6:02/km"}
    assert r["diferenca_texto"] == "20 s/km" and r["margem_texto"] == "11 s/km"
    assert r["periodo_a_texto"] == "últimos 28 dias (15/02 a 14/03)" and r["periodo_b_texto"] == "28 dias anteriores (18/01 a 14/02)"
    assert r["diferenca_pct_texto"] == "6%" and r["medida_texto"] == "mediana dos treinos"  # 20 / 362 = 5,5% -> 6%


def _pares(session, x, dias_atras_e_dur):
    for i, (d, dur) in enumerate(dias_atras_e_dur):
        _ativ(session, x, 100 + i, d, dur)
    session.commit()


def test_comparar_semana_com_a_passada_corta_nos_mesmos_dias(session, atleta):
    # Hoje é sexta, 15/03: esta semana = seg 11/03 a sex 15/03 (5 dias). A passada é cortada nos 5 primeiros dias: 04/03 a 08/03.
    # Esta semana (há 1, 2 e 4 dias): 1700, 1720, 1740 s em 5 km = 340, 344, 348 s/km, mediana 344 (5:44). Passada (há 7, 9 e 11 dias): 1800, 1780, 1820 = 360, 356, 364, mediana 360 (6:00).
    # d = 344 - 360 = -16; limite = 3% x 360 = 10,8 -> |d| >= limite: "menor", 16 s/km, 16 / 360 = 4,4% -> 4%; margem mostrada 11 s/km.
    _pares(session, atleta, [(1, 1700), (2, 1720), (4, 1740), (7, 1800), (9, 1780), (11, 1820)])
    r = fc.comparar_periodos(session, atleta.id, "corrida.pace.leve", "esta_semana", "semana_passada", agora=AGORA)
    assert r["estado"] == "ok" and r["direcao"] == "menor"
    assert r["a"] == {"n": 3, "valor_texto": "5:44/km"} and r["b"] == {"n": 3, "valor_texto": "6:00/km"}
    assert (r["diferenca_texto"], r["diferenca_pct_texto"], r["margem_texto"]) == ("16 s/km", "4%", "11 s/km")
    assert r["periodo_a_texto"] == "esta semana (11/03 a 15/03)" and r["periodo_b_texto"] == "semana passada, primeiros 5 dias (04/03 a 08/03)"
    assert "primeiros 5 dias" in r["corte_texto"]
    assert fc.comparar_periodos(session, atleta.id, "corrida.pace.leve", "semana_passada", "esta_semana", agora=AGORA)["direcao"] == "maior"  # trocar os lados inverte


def test_comparar_mes_em_curso_com_o_passado(session, atleta):
    # Este mês = 01/03 a 15/03 (15 dias); fevereiro de 2030 tem 28 dias e é cortado em 01/02 a 15/02.
    # Março (há 1, 5 e 12 dias): 1700, 1710, 1720 s = 340, 342, 344, mediana 342 (5:42). Fevereiro (há 28, 35 e 42 dias = 15/02, 08/02, 01/02): 1800, 1810, 1830 = 360, 362, 366, mediana 362 (6:02).
    # d = -20; limite = 10,86 -> "menor", 20 s/km, 20 / 362 = 5,5% -> 6%.
    _pares(session, atleta, [(1, 1700), (5, 1710), (12, 1720), (28, 1800), (35, 1810), (42, 1830)])
    r = fc.comparar_periodos(session, atleta.id, "corrida.pace.leve", "este_mes", "mes_passado", agora=AGORA)
    assert (r["a"]["valor_texto"], r["b"]["valor_texto"], r["direcao"], r["diferenca_texto"], r["diferenca_pct_texto"]) == ("5:42/km", "6:02/km", "menor", "20 s/km", "6%")
    assert r["periodo_b_texto"] == "mês passado, primeiros 15 dias (01/02 a 15/02)"


def test_comparar_dois_meses_de_calendario_no_volume(session, atleta):
    # Volume em km por semana = total / (dias / 7). Fevereiro de 2030 (28 dias; treinos há 19, 30 e 40 dias = 24/02, 13/02 e 03/02: 3 de 5 km = 15 km): 15 / 4 = 3,75 -> 3,8 km por semana.
    # Janeiro (31 dias, 24/01: 5 km): 5 / (31 / 7 = 4,4286) = 1,129 -> 1,1. d = 3,8 - 1,1 = 2,7; limite = 10% x 1,1 = 0,11 -> "maior"; 2,7 km, 2,7 / 1,1 = 245%.
    _leves(session, atleta)
    r = fc.comparar_periodos(session, atleta.id, "corrida.volume_km", "2030-02", "2030-01", agora=AGORA)
    assert r["estado"] == "ok" and r["medida_texto"] == "média por semana" and r["direcao"] == "maior"
    assert (r["a"]["valor_texto"], r["b"]["valor_texto"]) == ("3,8 km", "1,1 km")
    assert (r["diferenca_texto"], r["diferenca_pct_texto"]) == ("2,7 km", "245%")
    assert (r["a"]["n"], r["b"]["n"]) == (3, 1)


def test_comparar_com_poucos_treinos_traz_valores_sem_direcao(session, atleta):
    _leves(session, atleta)  # 7 dias até ontem (08/03 a 14/03): 1 treino (10/03); os 7 anteriores (01/03 a 07/03): 1 treino (03/03)
    r = fc.comparar_periodos(session, atleta.id, "corrida.pace.leve", "ultimos_7_dias", "ultimos_7_dias_anteriores", agora=AGORA)
    assert r["estado"] == "parcial" and "direcao" not in r and "diferenca_texto" not in r
    assert r["a"] == {"n": 1, "valor_texto": "5:40/km"} and r["b"] == {"n": 1, "valor_texto": "5:42/km"}
    assert r["motivo_texto"] == "Poucos treinos para comparar: 1 no primeiro período, 1 no segundo (o mínimo é 3)."


def test_comparar_so_aceita_periodos_do_mesmo_tamanho_e_sem_sobreposicao(session, atleta):
    _leves(session, atleta)
    e = fc.comparar_periodos(session, atleta.id, "corrida.pace.leve", "ultimos_7_dias", "ultimos_14_dias_anteriores", agora=AGORA)
    assert (e["codigo"], e["motivo"]) == ("comparacao_nao_suportada", "tamanhos_diferentes")
    e = fc.comparar_periodos(session, atleta.id, "corrida.pace.leve", "ultimos_28_dias", "ultimos_28_dias", agora=AGORA)
    assert (e["codigo"], e["motivo"]) == ("comparacao_nao_suportada", "periodos_sobrepostos")
    e = fc.comparar_periodos(session, atleta.id, "corrida.pace.leve", "ultimos_28_dias", "outubro", agora=AGORA)
    assert e["codigo"] == "argumento_invalido" and e["campo"] == "periodo_b" and "AAAA-MM" in e["periodos_validos"]
    assert fc.comparar_periodos(session, atleta.id, "corrida.pace.leve", "2031-01", "2030-01", agora=AGORA)["campo"] == "periodo_a"  # mês no futuro


def test_a_conta_geral_bate_com_a_da_frase_de_28_contra_28(session, atleta):
    """A estatística dos períodos livres é a da `frase_evolucao@1`: o mesmo valor mostrado para a janela de 28 dias."""
    from app.servicos.evolucao_series import POR_ID, carregar

    _leves(session, atleta)
    s = POR_ID["corrida.pace.leve"]
    m = carregar(session, atleta.id, AGORA, (s,))
    frase = ev.serie(session, atleta.id, "corrida.pace.leve", "12s", AGORA).frase
    for nome, esperado in (("ultimos_28_dias", frase.valor_atual), ("ultimos_28_dias_anteriores", frase.valor_anterior)):
        valor, n, _, _ = fc._estatistica(s, m.pontos_por_serie[s.id], fc._janela_de_comparacao(nome, m.hoje))
        assert n == 3 and valor == esperado


def test_comparar_periodos_fc_parecida_a_mao(session, atleta):
    _leves(session, atleta)
    # FC: R = 142, 144, 146 (mediana 144); A = 150, 152, 154 (mediana 152). d = -8; limite = 4 bpm -> "menor" 8 bpm. Troca A por 146, 148, 148: mediana 148, d = -4 -> parecido (|d| < 4 falso, = 4 entra como diferença).
    r = fc.comparar_periodos(session, atleta.id, "corrida.fc.leve", agora=AGORA)
    assert r["direcao"] == "menor" and r["diferenca_texto"] == "8 bpm" and r["margem_texto"] == "4 bpm"
    assert (r["a"]["valor_texto"], r["b"]["valor_texto"]) == ("144 bpm", "152 bpm")


def test_comparar_periodos_poucos_treinos_nao_inventa(session, atleta):
    _ativ(session, atleta, 1, 5, 1700)
    session.commit()
    r = fc.comparar_periodos(session, atleta.id, "corrida.pace.leve", agora=AGORA)
    assert r["estado"] == "parcial" and "direcao" not in r and "Poucos treinos" in r["motivo_texto"] and r["a"] == {"n": 1}


def test_comparar_periodos_serie_sem_treino(session, atleta):
    assert fc.comparar_periodos(session, atleta.id, "natacao.ritmo", agora=AGORA)["estado"] == "sem_dados"


def test_erros_voltam_como_resultado(session, atleta):
    e = fc.comparar_periodos(session, atleta.id, "corrida.inexistente", agora=AGORA)
    assert e["estado"] == "erro" and e["codigo"] == "serie_desconhecida" and "corrida.pace.leve" in e["ids_validos"]
    assert fc.serie_evolucao(session, atleta.id, "corrida.pace.leve", "ontem", agora=AGORA)["codigo"] == "argumento_invalido"
    assert fc.serie_evolucao(session, atleta.id, "corrida.pace.leve", de="2030-13-01", agora=AGORA)["codigo"] == "argumento_invalido"
    assert fc.carga_e_forma(session, atleta.id, "15/03", agora=AGORA)["codigo"] == "argumento_invalido"


def test_serie_evolucao_bate_com_a_da_rota(session, atleta):
    _leves(session, atleta)
    r = fc.serie_evolucao(session, atleta.id, "corrida.pace.leve", "ultimas_12_semanas", agora=AGORA)
    rota = ev.serie(session, atleta.id, "corrida.pace.leve", "12s", AGORA)
    assert r["estado"] == "ok" and r["versao"] == rota.versao_calculo
    assert [(p["atividade_id"], p["valor_texto"]) for p in r["pontos"]] == [(p.atividade_id, p.valor_texto + rota.unidade) for p in rota.pontos if p.valor_texto]
    assert [p["valor_texto"] for p in r["pontos"]] == ["6:06/km", "6:02/km", "6:00/km", "5:44/km", "5:42/km", "5:40/km"]  # 366,362,360,344,342,340 s/km
    assert r["frase_texto"] == rota.frase.texto and r.get("faixa_normal_texto") == (rota.referencia.texto if rota.referencia else None)
    assert r["ultimo_valor_texto"] == "5:40/km"


def test_serie_evolucao_recorta_o_periodo(session, atleta):
    _leves(session, atleta)
    r = fc.serie_evolucao(session, atleta.id, "corrida.pace.leve", "ultimos_28_dias", agora=AGORA)  # 16/02 a 15/03: só os 3 da janela R
    assert [p["valor_texto"] for p in r["pontos"]] == ["5:44/km", "5:42/km", "5:40/km"] and r["periodo_texto"] == "últimos 28 dias"
    r = fc.serie_evolucao(session, atleta.id, "corrida.pace.leve", de="2030-03-01", ate="2030-03-10", agora=AGORA)  # só o de há 12 e há 5 dias (03/03 e 10/03)
    assert [p["valor_texto"] for p in r["pontos"]] == ["5:42/km", "5:40/km"] and r["periodo_texto"] == "de 01/03 a 10/03"


def test_serie_sem_dados_diz_o_que_falta(session, atleta):
    r = fc.serie_evolucao(session, atleta.id, "natacao.ritmo", agora=AGORA)
    assert r["estado"] == "sem_dados" and r["motivo_texto"] and "pontos" not in r


def test_carga_e_forma_a_mao(session, atleta):
    # Um treino de carga 100 no dia 13/03; a série vai até ontem (14/03).
    # k_CTL = 1 - e^(-1/42) = 0,023528; k_ATL = 1 - e^(-1/7) = 0,133122.
    # Dia 13: CTL = 100 x 0,023533 = 2,3533; ATL = 13,3122. Dia 14 (carga 0): CTL = 2,3533 x 0,976467 = 2,2979; ATL = 13,3122 x 0,866878 = 11,5401; TSB = 2,2979 - 11,5401 = -9,2422.
    _ativ(session, atleta, 1, 2, 1800, carga=100.0)
    session.commit()
    r = fc.carga_e_forma(session, atleta.id, agora=AGORA)
    assert (r["ctl_texto"], r["atl_texto"], r["tsb_texto"], r["carga_dia_texto"]) == ("2,3", "11,5", "−9,2", "0,0")
    assert r["estado"] == "parcial" and r["estimativa"] is True and r["versao"] == "serie_carga@2"  # o 1.º dia com carga: ainda aprende (42 dias)
    assert r["motivo_texto"] == "Ainda aprendendo a sua forma: faltam 41 dias de histórico para estimar."
    d13 = fc.carga_e_forma(session, atleta.id, "2030-03-13", agora=AGORA)
    assert (d13["ctl_texto"], d13["atl_texto"], d13["tsb_texto"], d13["carga_dia_texto"]) == ("2,4", "13,3", "−11,0", "100,0")  # TSB = 2,3528 - 13,3122 = -10,9594
    assert d13["motivo_texto"].endswith("faltam 42 dias de histórico para estimar.")
    assert fc.carga_e_forma(session, atleta.id, "2030-03-01", agora=AGORA)["estado"] == "sem_dados"  # antes do primeiro dia com carga
    assert fc.carga_e_forma(session, atleta.id, "2030-04-01", agora=AGORA)["data_texto"] == r["data_texto"]  # depois de ontem: o último dia calculado


def test_carga_sem_nenhum_treino(session, atleta):
    r = fc.carga_e_forma(session, atleta.id, agora=AGORA)
    assert r["estado"] == "sem_dados" and "carga calculada" in r["motivo_texto"]


def test_linha_base_do_tipo(session, atleta):
    _leves(session, atleta)
    # O treino mais recente do tipo (há 5 dias) tem 5 treinos leves antes dele na janela de 12 semanas; o mínimo é 8: a métrica fica "aprendendo", n = 5, sem mediana.
    r = fc.linha_base(session, atleta.id, "corrida", "leve")
    assert r["estado"] == "parcial" and r["janela_semanas"] == 12 and r["minimo_treinos"] == 8
    pace = next(m for m in r["metricas"] if m["chave"] == "pace_medio")
    assert pace["estado"] == "aprendendo" and pace["n"] == 5 and pace["mediana_texto"] is None and pace["valor_do_treino_texto"] == "5:40/km"
    assert r["treino_de_referencia"]["atividade_id"]


def test_linha_base_com_normal_a_mao(session, atleta):
    # 9 leves de 5 km, 1 por semana, paces 340 a 348 s/km (dur 1700 a 1740), e o mais recente (há 2 dias) a 344. Os 9 anteriores: mediana 344 = 5:44/km, n = 9 >= 8.
    for i in range(9):
        _ativ(session, atleta, i, 70 - i * 7, 1700 + 5 * i)
    _ativ(session, atleta, 99, 2, 1720)
    session.commit()
    pace = next(m for m in fc.linha_base(session, atleta.id, "corrida", "leve")["metricas"] if m["chave"] == "pace_medio")
    assert pace["estado"] == "dentro" and pace["n"] == 9 and pace["mediana_texto"] == "5:44/km"


def test_linha_base_sem_treino_do_tipo(session, atleta):
    r = fc.linha_base(session, atleta.id, "corrida", "longo")
    assert r["estado"] == "sem_dados" and r["motivo_texto"]


def test_so_le_o_atleta_da_chamada(session, atleta):
    """O `atleta_id` é parâmetro do código: os treinos de outro atleta nunca entram (o registro da #593 passa o da sessão)."""
    outro = Atleta(nome="Ficticio B")
    session.add(outro)
    session.flush()
    _leves(session, outro)
    assert fc.comparar_periodos(session, atleta.id, "corrida.pace.leve", agora=AGORA)["estado"] == "sem_dados"
    assert fc.serie_evolucao(session, atleta.id, "corrida.pace.leve", agora=AGORA)["estado"] == "sem_dados"
    assert fc.carga_e_forma(session, atleta.id, agora=AGORA)["estado"] == "sem_dados"
    assert fc.linha_base(session, atleta.id, "corrida", "leve")["estado"] == "sem_dados"
