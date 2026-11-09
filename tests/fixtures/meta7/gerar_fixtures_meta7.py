"""Gera as fixtures sintéticas da Meta 7 (issue #261, ADR 0011): 12 semanas de treino e a semana-padrão.

Tudo sintético: nenhum dado real. Escreve `atividades.json` e `semana_padrao.json` ao lado deste arquivo.
Uso: `python tests/fixtures/meta7/gerar_fixtures_meta7.py` (o teste confere que o JSON versionado é a saída deste gerador).

Período: domingo 2026-01-04 a domingo 2026-03-29 (12 semanas). Fuso -180 (UTC-3) salvo onde dito.
Cada atividade traz o que as funções puras precisam, sem voltas nem FIT: `estrutura` resume os blocos da ADR 0008
(`sem_esforco` = todos os blocos `leve`; `esforco` = tem esforço mas não é série de tiros; `tiros` = série de tiros;
`null` = sem blocos gravados) e `tiros` traz o melhor tiro da série `tiros_1km@6`.
Os valores das séries (pace, FC, carga) são literais escolhidos para a conta à mão de `oraculo.py`.
"""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

PASTA = Path(__file__).parent
INICIO, FIM = date(2026, 1, 4), date(2026, 3, 29)
FUSO_SP = -180  # UTC-3; "fuso nulo" usa America/Sao_Paulo (ADR 0003), que em 2026 é o mesmo deslocamento


def _itens(natacao_tipo, quinta_tipo):
    return [
        {"dia_semana": 1, "modalidade": "natacao", "tipo_treino": natacao_tipo},
        {"dia_semana": 2, "modalidade": "corrida", "tipo_treino": "intervalado"},
        {"dia_semana": 3, "modalidade": "ciclismo", "tipo_treino": "leve"},
        {"dia_semana": 4, "modalidade": "corrida", "tipo_treino": quinta_tipo},
        {"dia_semana": 6, "modalidade": "corrida", "tipo_treino": "longo"},
        {"dia_semana": 6, "modalidade": "ciclismo", "tipo_treino": "moderado"},
        {"dia_semana": 7, "modalidade": "corrida", "tipo_treino": None},
    ]


# Vigência A: natação sem tipo, quinta fartlek. Vigência B (02/03): natação leve, quinta moderado.
SEMANA_PADRAO = [
    {"vigente_desde": "2026-01-05", "definido_por": "atleta", "itens": _itens(None, "fartlek")},
    {"vigente_desde": "2026-03-02", "definido_por": "professor", "itens": _itens("leve", "moderado")},
]

SIGLA = {"corrida": "cor", "natacao": "nat", "ciclismo": "cic", "outra": "out"}
_regs: list[dict] = []


def d(mes_dia: str) -> date:
    m, dia = mes_dia.split("-")
    return date(2026, int(m), int(dia))


def add(dia, hora, modalidade, duracao_s, distancia_m, fc, *, subtipo=None, fuso=FUSO_SP, estrutura=None,
        tiros=None, carga=None, inicial=None, transicao=False):
    h, mi = map(int, hora.split(":"))
    local = datetime(dia.year, dia.month, dia.day, h, mi)
    deslocamento = fuso if fuso is not None else FUSO_SP
    utc = (local - timedelta(minutes=deslocamento)).replace(tzinfo=timezone.utc)
    ini = inicial or {}
    _regs.append({
        "modalidade": modalidade, "subtipo": subtipo, "inicio": utc.isoformat(), "fuso_min": fuso,
        "duracao_s": duracao_s, "distancia_m": distancia_m, "fc_media": fc, "carga": carga,
        "estrutura": estrutura, "tiros": tiros, "transicao": transicao,
        "tipo_treino": ini.get("tipo"), "tipo_origem": ini.get("origem"), "tipo_confirmado": ini.get("confirmado", False),
        "_local": local.isoformat(),
    })


def tiros(n, melhor_pace, fc):
    return {"n": n, "melhor_pace_s_km": melhor_pace, "fc_melhor_tiro": fc}


def gerar() -> dict:
    _regs.clear()
    # Segunda: natação de 2000 m, FC 125.
    for m_d in ["01-05", "01-12", "01-19", "01-26", "02-02", "02-09", "02-16", "02-23", "03-02", "03-09", "03-16", "03-23"]:
        add(d(m_d), "06:30", "natacao", 2400, 2000, 125, subtipo="piscina")

    # Terça: série de tiros. Melhor pace (s/km) por data; FC do melhor tiro 172 (02-24 sem FC; 02-24 às 23:10,
    # já quarta em UTC).
    ter = {"01-20": 270, "01-27": 264, "02-03": 267, "02-10": 261, "02-17": 264, "02-24": 258,
           "03-03": 261, "03-10": 255, "03-17": 249, "03-24": 252}
    add(d("01-06"), "07:30", "corrida", 3000, 9000, 160, subtipo="esteira", estrutura="tiros", tiros=tiros(6, 276, 172))
    add(d("01-13"), "07:30", "corrida", 1800, 5000, 150, estrutura="sem_esforco")  # plano intervalado, sem esforço
    add(d("01-13"), "18:00", "corrida", 1800, 5000, 150, estrutura="sem_esforco")  # segunda do dia, mesma duração
    add(d("01-20"), "07:00", "corrida", 900, 2500, 130, estrutura="sem_esforco")  # solta, antes da sessão
    for m_d, pace in ter.items():
        hora = "23:10" if m_d == "02-24" else "07:30"
        fc = None if m_d == "02-24" else 172
        add(d(m_d), hora, "corrida", 3000, 9000, 160, estrutura="tiros", tiros=tiros(6, pace, fc))

    # Quarta: ciclismo de 1 h. Carga (hrTSS) por data; FC 130 (03-18: 133). 01-14 é pedal virtual.
    qua = {"01-07": 41, "01-14": 41, "01-21": 40, "01-28": 44, "02-04": 42, "02-11": 46, "02-18": 38,
           "02-25": 44, "03-04": 42, "03-11": 48, "03-18": 55, "03-25": 45}
    for m_d, carga in qua.items():
        add(d(m_d), "06:00", "ciclismo", 3600, 25000, 133 if m_d == "03-18" else 130, carga=float(carga),
            subtipo="virtual" if m_d == "01-14" else None)

    # Quinta: corrida com esforço que não é série de tiros (333 s/km). Tipos prévios em três datas; 02-12 sem fuso.
    previo = {
        "01-08": {"tipo": "longo", "origem": "professor"},
        "01-15": {"tipo": "moderado", "confirmado": True},
        "01-29": {"tipo": "moderado", "origem": "trainingpeaks"},
    }
    for m_d in ["01-08", "01-15", "01-22", "01-29", "02-05", "02-12", "02-19", "02-26", "03-05", "03-12", "03-19", "03-26"]:
        add(d(m_d), "07:00", "corrida", 3000, 9000, 155, estrutura="esforco", inicial=previo.get(m_d),
            fuso=None if m_d == "02-12" else FUSO_SP)

    # Sexta: corrida de 8 km sem esforço, sem item no plano. 01-09 é série de tiros (reserva: intervalado).
    add(d("01-09"), "07:00", "corrida", 3000, 9000, 160, estrutura="tiros", tiros=tiros(6, 270, 172))
    sex = {"01-16": (330, 150), "01-23": (324, 148), "01-30": (336, None), "02-06": (330, 152), "02-13": (342, None),
           "02-20": (318, 146), "02-27": (330, None), "03-06": (336, 151), "03-13": (306, 160), "03-20": (330, 150),
           "03-27": (330, 150)}
    for m_d, (pace, fc) in sex.items():
        add(d(m_d), "07:00", "corrida", pace * 8, 8000, fc, estrutura="sem_esforco")

    # Sábado: treino multiesporte em 01-10; depois longo de 15 km (pace por data); 03-28 é longo com tiros.
    sab = {"01-17": 342, "01-24": 336, "01-31": 339, "02-07": 333, "02-14": 330, "02-21": 336, "02-28": 330,
           "03-07": 333, "03-14": 324, "03-21": 315}
    add(d("01-10"), "07:55", "outra", 6300, None, None, subtipo="multiesporte_pai")
    add(d("01-10"), "08:00", "natacao", 1800, 1500, 130, subtipo="aguas_abertas", transicao=True)
    add(d("01-10"), "08:30", "outra", 120, None, None, subtipo="troca")
    add(d("01-10"), "08:33", "ciclismo", 2700, 20000, 140, carga=30.0, transicao=True)
    add(d("01-10"), "09:18", "outra", 120, None, None, subtipo="troca")
    add(d("01-10"), "09:20", "corrida", 1200, 4000, 160, estrutura="sem_esforco", transicao=True)
    for m_d, pace in sab.items():
        add(d(m_d), "07:00", "corrida", pace * 15, 15000, 145, estrutura="sem_esforco")
    add(d("03-28"), "07:00", "corrida", 5400, 15000, 150, estrutura="tiros", tiros=tiros(6, 300, 170))

    # Domingo: 40 min sem esforço; 01-04 é antes da primeira vigência, 01-11 tem item sem tipo.
    add(d("01-04"), "08:00", "corrida", 2400, 7000, 148, estrutura="sem_esforco")
    add(d("01-11"), "08:00", "corrida", 2400, 7000, 148, estrutura="sem_esforco")

    # ids estáveis: data/sigla+n, com n na ordem do horário local do dia
    _regs.sort(key=lambda r: (r["_local"], r["modalidade"]))
    cont: dict[tuple[str, str], int] = {}
    saida = []
    for r in _regs:
        dia = r["_local"][:10]
        chave = (dia, SIGLA[r["modalidade"]])
        cont[chave] = cont.get(chave, 0) + 1
        saida.append({"id": f"{dia}/{chave[1]}{cont[chave]}", **{k: v for k, v in r.items() if k != "_local"}})
    return {"periodo": [INICIO.isoformat(), FIM.isoformat()], "atividades": saida}


def main() -> None:
    (PASTA / "atividades.json").write_text(json.dumps(gerar(), ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    (PASTA / "semana_padrao.json").write_text(
        json.dumps({"vigencias": SEMANA_PADRAO}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
