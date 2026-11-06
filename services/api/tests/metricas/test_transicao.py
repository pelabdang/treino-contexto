"""Regra ``transicao@1`` (issue #156; ADR 0009, item 2; nota docs/metricas/transicao.md).

Tudo sintético. Os horários e as contas estão nos comentários; os valores esperados foram
calculados à mão. Convenção: ``ativ(id, modalidade, "HH:MM", duracao_min)``.
"""

from datetime import UTC, datetime, timedelta

from app.metricas.transicao import (
    INTERVALO_MAX_S,
    MODALIDADES_DE_TRANSICAO,
    SOBREPOSICAO_MAX_S,
    VERSAO,
    AtividadeLeve,
    sugerir_transicao,
)

DIA = datetime(2030, 1, 10, tzinfo=UTC)  # data fictícia


def ativ(id_, modalidade, hhmm, duracao_min, dias=0, seg=0):
    h, m = (int(x) for x in hhmm.split(":"))
    inicio = DIA + timedelta(days=dias, hours=h, minutes=m, seconds=seg)
    return AtividadeLeve(id_, modalidade, inicio, duracao_min * 60.0)


def test_constantes_e_versao():
    assert VERSAO == "transicao@1"
    assert INTERVALO_MAX_S == 1800
    assert SOBREPOSICAO_MAX_S == 60
    assert MODALIDADES_DE_TRANSICAO == {"corrida", "natacao", "ciclismo"}


def test_vazio_e_uma_so():
    assert sugerir_transicao([]) == set()
    assert sugerir_transicao([ativ(1, "corrida", "07:00", 30)]) == set()


def test_par_simples_intervalo_2_min():
    # A 07:00-08:00 (fim 08:00), B 08:02: intervalo 120 s, dentro de 1800.
    a = ativ(1, "ciclismo", "07:00", 60)
    b = ativ(2, "corrida", "08:02", 28)
    assert sugerir_transicao([a, b]) == {1, 2}
    assert sugerir_transicao([b, a]) == {1, 2}  # ordem de entrada não importa


def test_seis_horas_depois_nenhuma():
    # fim 08:00, B 14:00: intervalo 21600 s.
    assert sugerir_transicao([ativ(1, "ciclismo", "07:00", 60), ativ(2, "corrida", "14:00", 30)]) == set()


def test_limite_superior_exato_1800_s():
    # fim 08:00; B 08:30:00 -> intervalo 1800 s (inclusive).
    a = ativ(1, "ciclismo", "07:00", 60)
    assert sugerir_transicao([a, ativ(2, "corrida", "08:30", 20)]) == {1, 2}


def test_um_segundo_acima_do_limite():
    # B 08:30:01 -> intervalo 1801 s: fora.
    a = ativ(1, "ciclismo", "07:00", 60)
    assert sugerir_transicao([a, ativ(2, "corrida", "08:30", 20, seg=1)]) == set()


def test_quarenta_minutos_nenhuma():
    # fim 08:00; B 08:40 -> 2400 s.
    assert sugerir_transicao([ativ(1, "ciclismo", "07:00", 60), ativ(2, "corrida", "08:40", 20)]) == set()


def test_sobreposicao_exata_60_s():
    # fim 08:00; B 07:59:00 -> intervalo -60 s (inclusive).
    a = ativ(1, "ciclismo", "07:00", 60)
    assert sugerir_transicao([a, ativ(2, "corrida", "07:59", 20)]) == {1, 2}


def test_sobreposicao_61_s_fora():
    # B 07:58:59 -> intervalo -61 s: duplicata/dois aparelhos, não transição.
    a = ativ(1, "ciclismo", "07:00", 60)
    assert sugerir_transicao([a, ativ(2, "corrida", "07:58", 20, seg=59)]) == set()


def test_cadeia_de_tres():
    # A 07:00-08:00, B 08:02-08:30, A 08:34-09:10: intervalos 120 s e 240 s.
    r = sugerir_transicao(
        [ativ(1, "ciclismo", "07:00", 60), ativ(2, "corrida", "08:02", 28), ativ(3, "ciclismo", "08:34", 36)]
    )
    assert r == {1, 2, 3}


def test_triatlo_natacao_ciclismo_corrida():
    r = sugerir_transicao(
        [ativ(1, "natacao", "07:00", 30), ativ(2, "ciclismo", "07:35", 60), ativ(3, "corrida", "08:40", 30)]
    )
    assert r == {1, 2, 3}


def test_mesma_modalidade_seguida_nao_forma_par():
    # corrida 07:00-07:50 e corrida 07:52-08:20: intervalo 120 s, mesma modalidade.
    assert sugerir_transicao([ativ(1, "corrida", "07:00", 50), ativ(2, "corrida", "07:52", 28)]) == set()


def test_mesma_modalidade_no_meio_de_cadeia():
    # corrida, ciclismo, ciclismo, corrida (2 min entre cada): cada ciclismo pareia com a corrida do seu lado.
    r = sugerir_transicao(
        [
            ativ(1, "corrida", "07:00", 28),  # fim 07:28
            ativ(2, "ciclismo", "07:30", 28),  # fim 07:58
            ativ(3, "ciclismo", "08:00", 28),  # fim 08:28
            ativ(4, "corrida", "08:30", 20),
        ]
    )
    assert r == {1, 2, 3, 4}


def test_aninhada_nao_esconde_a_transicao():
    # A 07:00-08:00; A' (mesma modalidade) aninhada 07:10-07:20; B 08:02.
    # Vizinha imediata de B é A' (fim 07:20, intervalo 2520 s, fora); o maior fim visto é 08:00 (120 s): sugere A e B.
    r = sugerir_transicao(
        [ativ(1, "ciclismo", "07:00", 60), ativ(2, "ciclismo", "07:10", 10), ativ(3, "corrida", "08:02", 28)]
    )
    assert r == {1, 3}  # A' fica de fora: não é vizinha do par


def test_aninhada_de_outra_modalidade_nao_vira_par_e_nao_esconde():
    # A 07:00-08:00; B aninhada 07:10-07:20 (intervalo -3000 s: fora); A2 08:02 (mesma modalidade da dona do fim: sem par).
    r = sugerir_transicao(
        [ativ(1, "ciclismo", "07:00", 60), ativ(2, "corrida", "07:10", 10), ativ(3, "ciclismo", "08:02", 30)]
    )
    assert r == set()


def test_duplicada_nao_esconde_a_transicao():
    # A e uma duplicata de A (mesmo início e duração, id diferente), B 08:02: as duas A pareiam com B.
    r = sugerir_transicao(
        [ativ(1, "ciclismo", "07:00", 60), ativ(2, "ciclismo", "07:00", 60), ativ(3, "corrida", "08:02", 28)]
    )
    assert r == {1, 2, 3}


def test_duplicada_de_outra_modalidade_no_mesmo_instante():
    # A (ciclismo) e B (corrida) com o mesmo início e fim, depois A2 08:02: A2 pareia só com a B (modalidade diferente).
    r = sugerir_transicao(
        [ativ(1, "ciclismo", "07:00", 60), ativ(2, "corrida", "07:00", 60), ativ(3, "ciclismo", "08:02", 20)]
    )
    assert r == {2, 3}


def test_virada_da_meia_noite():
    # A 23:40 (15 min, fim 23:55), B 00:00 do dia seguinte: intervalo 300 s.
    r = sugerir_transicao([ativ(1, "ciclismo", "23:40", 15), ativ(2, "corrida", "00:00", 20, dias=1)])
    assert r == {1, 2}


def test_outra_fica_fora_e_nao_corta_a_vizinhanca():
    # corrida 07:00-07:30, 'outra' 07:31-07:40, ciclismo 07:45: a 'outra' é ignorada; corrida e ciclismo, 900 s.
    r = sugerir_transicao(
        [ativ(1, "corrida", "07:00", 30), ativ(2, "outra", "07:31", 9), ativ(3, "ciclismo", "07:45", 30)]
    )
    assert r == {1, 3}


def test_so_outra_nao_sugere():
    assert sugerir_transicao([ativ(1, "outra", "07:00", 30), ativ(2, "corrida", "07:32", 30)]) == set()


def test_duracao_zero_ou_negativa_nao_quebra():
    # Duração 0: fim = início; B 10 min depois pareia.
    r = sugerir_transicao([ativ(1, "corrida", "07:00", 0), ativ(2, "ciclismo", "07:10", 30)])
    assert r == {1, 2}
    r = sugerir_transicao([ativ(1, "corrida", "07:00", -5), ativ(2, "ciclismo", "07:10", 30)])
    assert r == {1, 2}


def test_so_sugere_sim_e_nao_depende_da_ordem_de_entrada():
    atividades = [
        ativ(3, "ciclismo", "08:34", 36),
        ativ(1, "ciclismo", "07:00", 60),
        ativ(9, "corrida", "14:00", 30),
        ativ(2, "corrida", "08:02", 28),
    ]
    assert sugerir_transicao(atividades) == {1, 2, 3}  # 9 não aparece
    assert sugerir_transicao(reversed(atividades)) == {1, 2, 3}


def test_mesmo_inicio_desempata_por_id():
    # Sem erro e determinístico quando duas atividades começam juntas.
    a = [ativ(2, "corrida", "07:00", 30), ativ(1, "ciclismo", "07:00", 30)]
    assert sugerir_transicao(a) == sugerir_transicao(list(reversed(a)))


def test_dias_diferentes_nao_pareiam():
    assert sugerir_transicao([ativ(1, "corrida", "07:00", 30), ativ(2, "ciclismo", "07:10", 30, dias=1)]) == set()
