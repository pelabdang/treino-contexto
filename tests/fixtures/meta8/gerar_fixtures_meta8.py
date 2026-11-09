"""Gera as fixtures sintéticas da Meta 8 (issue #294, ADR 0012): atividades e check-ins.

Tudo sintético: nenhum dado real, nenhum check-in real. Escreve `atividades.json` e `checkins.json` ao lado deste arquivo.
Uso: `python tests/fixtures/meta8/gerar_fixtures_meta8.py` (o teste confere que o JSON versionado é a saída deste gerador).

"Agora" das fixtures: 2026-11-09 às 15:00 locais (UTC-3). A janela de criação e de pendentes é [hoje - 7, hoje] = 02/11 a 09/11.
`fuso_min` -180 salvo onde dito (`null` cai em America/Sao_Paulo, ADR 0003).
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

PASTA = Path(__file__).parent
AGORA = "2026-11-09T15:00:00-03:00"
FUSO_SP = -180
SIGLA = {"corrida": "cor", "natacao": "nat", "ciclismo": "cic", "outra": "out"}
_regs: list[dict] = []


def add(dia: str, hora: str, modalidade: str, duracao_s: float, *, subtipo=None, fuso=FUSO_SP):
    ano, mes, d = map(int, dia.split("-"))
    h, mi = map(int, hora.split(":"))
    local = datetime(ano, mes, d, h, mi)
    utc = (local - timedelta(minutes=fuso if fuso is not None else FUSO_SP)).replace(tzinfo=UTC)
    _regs.append({"_local": local.isoformat(), "modalidade": modalidade, "subtipo": subtipo, "inicio": utc.isoformat(),
                  "fuso_min": fuso, "duracao_s": duracao_s})


def gerar() -> dict:
    _regs.clear()
    add("2026-11-09", "06:00", "corrida", 0)  # duração zero, com check-in: sem_duracao
    add("2026-11-09", "07:00", "corrida", 2700)
    add("2026-11-08", "06:30", "natacao", 2400, subtipo="piscina")
    add("2026-11-08", "17:00", "ciclismo", 3000, subtipo="virtual")
    add("2026-11-07", "07:00", "corrida", 2725)
    add("2026-11-06", "08:00", "outra", 1800)  # força: elegível, sem carga@2, com carga pela PSE
    add("2026-11-05", "07:00", "corrida", 2700)  # sem check-in: pendente
    add("2026-11-04", "06:00", "ciclismo", 3600)  # sem check-in, subtipo nulo: pendente (NOT IN não pode excluí-la)
    # multiesporte de 03/11: pai, natação, troca, ciclismo, troca, corrida
    add("2026-11-03", "07:55", "outra", 6300, subtipo="multiesporte_pai")
    add("2026-11-03", "08:00", "natacao", 1800, subtipo="aguas_abertas")
    add("2026-11-03", "08:30", "outra", 120, subtipo="troca")
    add("2026-11-03", "08:33", "ciclismo", 2700)
    add("2026-11-03", "09:18", "outra", 120, subtipo="troca")
    add("2026-11-03", "09:20", "corrida", 1200)  # sem check-in: pendente
    add("2026-11-02", "07:00", "corrida", 3000, fuso=None)  # no limite da janela (hoje - 7); fuso nulo
    add("2026-11-01", "23:30", "corrida", 3000)  # local 01/11, UTC já é 02/11: fora do prazo
    add("2026-11-01", "07:00", "corrida", 3000)  # fora do prazo
    add("2026-10-15", "07:00", "corrida", 2700)  # antiga, com check-in (editar vale sem prazo)

    _regs.sort(key=lambda r: (r["_local"], r["modalidade"]))
    cont: dict[tuple[str, str], int] = {}
    saida = []
    for r in _regs:
        dia = r["_local"][:10]
        chave = (dia, SIGLA[r["modalidade"]])
        cont[chave] = cont.get(chave, 0) + 1
        saida.append({"id": f"{dia}/{chave[1]}{cont[chave]}", **{k: v for k, v in r.items() if k != "_local"}})
    return {"agora": AGORA, "atividades": saida}


# Check-ins por id de atividade. Texto livre sintético.
CHECKINS = {
    "2026-11-09/cor1": {"pse": 5, "sensacao": 3, "nada_a_relatar": True, "atalhos": [], "texto": None},  # duração zero
    "2026-11-09/cor2": {"pse": 6, "sensacao": 4, "nada_a_relatar": False, "atalhos": ["cansaco", "trabalho_estresse"],
                        "texto": "Semana puxada no trabalho."},
    "2026-11-08/nat1": {"pse": 4, "sensacao": 3, "nada_a_relatar": True, "atalhos": [], "texto": None},
    "2026-11-08/cic1": {"pse": 7, "sensacao": 2, "nada_a_relatar": False, "atalhos": ["calor"], "texto": None},
    "2026-11-07/cor1": {"pse": 6, "sensacao": 2, "nada_a_relatar": False, "atalhos": [], "texto": "Incômodo no fim do treino."},
    "2026-11-06/out1": {"pse": 0, "sensacao": 3, "nada_a_relatar": True, "atalhos": [], "texto": None},
    "2026-11-03/nat1": {"pse": 5, "sensacao": 4, "nada_a_relatar": True, "atalhos": [], "texto": None},
    "2026-11-03/cic1": {"pse": 6, "sensacao": 3, "nada_a_relatar": False, "atalhos": ["dor", "sono_ruim"], "texto": None},
    "2026-10-15/cor1": {"pse": 5, "sensacao": 4, "nada_a_relatar": True, "atalhos": [], "texto": None},
}


def main() -> None:
    (PASTA / "atividades.json").write_text(json.dumps(gerar(), ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    (PASTA / "checkins.json").write_text(json.dumps(CHECKINS, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
