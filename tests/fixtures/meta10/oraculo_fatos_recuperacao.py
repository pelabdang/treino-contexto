"""Oráculo à mão do bloco `recuperacao` do `fatos_treino@2` (issue #374, ADR 0014, item 4). Tudo SINTÉTICO.

Cada caso é a ENTRADA da `recuperacao@1` (as noites do atleta, a data e a hora locais do treino) e o BLOCO esperado. A conta da
`recuperacao@1` está em docs/metricas/recuperacao-oraculo.md; aqui só o texto pronto: o sono em "H h MM min", a VFC em ms, a FC de repouso
em bpm, **arredondados** (minuto, ms, bpm) antes de comparar, e a diferença é a conta entre os valores arredondados (fecha à mão).
Dia do treino sintético: 15/03/2030. Nada vem de resposta do Garmin nem da conta de ninguém.
"""

from __future__ import annotations

from datetime import date, time, timedelta

DIA = date(2030, 3, 15)
MANHA = time(8, 0)

# Janelas de 14 noites (D-14 a D-1) escritas à mão (as mesmas do oráculo da `recuperacao@1`, casos A, C e D).
SONO_MIN = [400, 410, 420, 420, 425, 430, 435, 435, 440, 440, 445, 450, 460, 470]  # mediana 435, MAD 12,5, desvio 21,75 min
VFC_MS = [40, 42, 44, 44, 45, 46, 47, 47, 48, 49, 50, 52, 54, 56]  # mediana 47, MAD 3, desvio 4,4478
FC_BPM = [52] * 14  # mediana 52, MAD 0, desvio = piso 0,05 x 52 = 2,6


def _janela(sono=None, vfc=None, fc=None, n=14):
    """Linhas (dict) de D-n a D-1; cada lista é a medida correspondente (None = sem a medida)."""
    linhas = []
    for i in range(n):
        linha = {"noite": DIA - timedelta(days=n - i)}
        linha["sono_s"] = None if sono is None else sono[i] * 60 if sono[i] is not None else None
        linha["vfc_ms"] = None if vfc is None else vfc[i]
        linha["fc_repouso_bpm"] = None if fc is None else fc[i]
        linhas.append(linha)
    return linhas


def _noite(sono_s=None, vfc_ms=None, fc_repouso_bpm=None):
    return {"noite": DIA, "sono_s": sono_s, "vfc_ms": vfc_ms, "fc_repouso_bpm": fc_repouso_bpm}


def _m(chave, estado, valor, valor_texto, normal_texto, diferenca_texto, n):
    return {"chave": chave, "estado": estado, "valor": valor, "valor_texto": valor_texto, "normal_texto": normal_texto,
            "diferenca_texto": diferenca_texto, "n": n}


def _ok(medidas):
    return {"versao": "recuperacao@1", "estado": "ok", "motivo": None, "janela_noites": 28, "minimo_noites": 14, "medidas": medidas}


def _sem(motivo):
    return {"versao": "recuperacao@1", "estado": "sem_dado", "motivo": motivo}


CASOS = {
    # R01: as três medidas, uma abaixo, uma dentro, uma acima.
    # Sono: 345 min contra a mediana de 435: z = -90 / 21,75 = -4,138 (abaixo). 345 min = 5 h 45 min; 435 min = 7 h 15 min; diferença 90 min.
    # VFC: 41 ms contra 47: z = -6 / 4,4478 = -1,349 (dentro). FC de repouso: 58 bpm contra 52: z = 6 / 2,6 = 2,308 (acima).
    "R01": {"descricao": "as três medidas: sono abaixo, VFC dentro, FC de repouso acima",
            "dia": DIA, "hora": MANHA,
            "noites": _janela(SONO_MIN, VFC_MS, FC_BPM) + [_noite(345 * 60, 41, 58)],
            "bloco": _ok([_m("sono", "abaixo", 20700, "5 h 45 min", "7 h 15 min", "1 h 30 min abaixo", 14),
                          _m("vfc", "dentro", 41, "41 ms", "47 ms", None, 14),
                          _m("fc_repouso", "acima", 58, "58 bpm", "52 bpm", "6 bpm acima", 14)])},
    # R02: só o sono tem histórico, e só 13 noites: aprendendo (sem normal nem diferença); VFC e FC de repouso sem valor na noite.
    # 22800 s = 380 min = 6 h 20 min.
    "R02": {"descricao": "sono aprendendo (13 noites); VFC e FC de repouso sem dado na noite",
            "dia": DIA, "hora": MANHA,
            "noites": _janela(SONO_MIN[1:], None, None, n=13) + [_noite(22800)],
            "bloco": _ok([_m("sono", "aprendendo", 22800, "6 h 20 min", None, None, 13),
                          _m("vfc", "sem_dado", None, None, None, None, 0),
                          _m("fc_repouso", "sem_dado", None, None, None, None, 0)])},
    # R03: arredondamento. 14 noites de 26130 s (435,5 min): mediana 26130, MAD 0, desvio = piso = 0,05 x 26130 = 1306,5 s.
    # Normal 435,5 min arredonda para 436 min = 7 h 16 min. Noite de 21600 s = 360 min = "6 h": z = -4530 / 1306,5 = -3,467 (abaixo).
    # Diferença entre os arredondados: 436 - 360 = 76 min = 1 h 16 min.
    "R03": {"descricao": "arredondamento do normal ao minuto e hora cheia",
            "dia": DIA, "hora": MANHA,
            "noites": [{"noite": DIA - timedelta(days=14 - i), "sono_s": 26130, "vfc_ms": None, "fc_repouso_bpm": None}
                       for i in range(14)] + [_noite(21600)],
            "bloco": _ok([_m("sono", "abaixo", 21600, "6 h", "7 h 16 min", "1 h 16 min abaixo", 14),
                          _m("vfc", "sem_dado", None, None, None, None, 0),
                          _m("fc_repouso", "sem_dado", None, None, None, None, 0)])},
    # R04: noite sem linha (a busca rodou, o relógio não enviou).
    "R04": {"descricao": "sem noite", "dia": DIA, "hora": MANHA, "noites": _janela(SONO_MIN),
            "bloco": _sem("sem_noite")},
    # R05: treino às 05:59 (antes do corte das 06:00), mesmo com a noite gravada.
    "R05": {"descricao": "treino de madrugada", "dia": DIA, "hora": time(5, 59),
            "noites": _janela(SONO_MIN) + [_noite(345 * 60, 41, 58)], "bloco": _sem("treino_de_madrugada")},
    # R06: treino anterior à noite mais antiga gravada (D-14).
    "R06": {"descricao": "fora do período", "dia": DIA - timedelta(days=20), "hora": MANHA,
            "noites": _janela(SONO_MIN) + [_noite(345 * 60, 41, 58)], "bloco": _sem("fora_do_periodo")},
}

# Só estas chaves podem aparecer no bloco (ADR 0014, item 4): nada de data, série, MAD, z ou mediana numérica.
CHAVES_BLOCO_OK = ("versao", "estado", "motivo", "janela_noites", "minimo_noites", "medidas")
CHAVES_BLOCO_SEM_DADO = ("versao", "estado", "motivo")
CHAVES_MEDIDA = ("chave", "estado", "valor", "valor_texto", "normal_texto", "diferenca_texto", "n")
