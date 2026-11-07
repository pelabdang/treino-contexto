"""Gera as fixtures sinteticas de algumas semanas para o oraculo da carga (Meta 6, issue #137; ADR 0010).

Tudo aqui e inventado: valores, ids, nomes e datas. Rode:

    uv run python tests/fixtures/garmin/gerar_fixtures_carga.py

Saida deterministica, em ``carga/``:

- ``exportacao_carga.zip``: as atividades abaixo (JSON + FIT por volta) mais os arquivos de saude de
  ``gerar_fixtures_saude.py`` (limiar comecando no meio do periodo e mudando duas vezes).
- ``exportacao_carga_sem_saude.zip``: as mesmas atividades, de um atleta sem nenhum dado de saude.

Os valores esperados de cada atividade e a conta a mao estao em ``docs/metricas/carga-oraculo.md`` e em
``services/api/tests/metricas/test_carga_oraculo.py`` (constante ``ESPERADO``).

LINHA DO TEMPO DO LIMIAR (de ``gerar_fixtures_saude.py``; a velocidade vem do arquivo como m/s dividido por 10)

    ate 04/03   sem limiar
    05/03       FC 158 bpm, velocidade 3,70 m/s
    08/03       FC 159 bpm (a velocidade continua 3,70 m/s: o registro e so de FC)
    10/03       FC 163 bpm, velocidade 3,85 m/s

CASOS COBERTOS (data local; entre parenteses o resultado esperado)
    03/03 corrida antes de qualquer limiar (sem_limiar_na_data)
    04/03 corrida as 22h locais, 05/03 01h UTC: vale o dia LOCAL, ainda sem limiar (sem_limiar_na_data)
    05/03 corrida no dia em que o limiar comeca (calculada, rTSS; hrTSS tambem gravado)
    06/03 natacao (modalidade_sem_carga)
    07/03 ciclismo sem potencia, so FC (calculada, hrTSS)
    08/03 corrida sem FC (calculada, rTSS) e esteira sem FC no mesmo dia (sem_fc)
    09/03 dia sem treino
    10/03 corrida no dia em que o limiar muda (calculada, rTSS com o limiar novo)
    11/03 ciclismo as 23h locais, 12/03 02h UTC (calculada, hrTSS, dia local 11/03)
    12/03 esteira com 10 voltas, uma sem FC: cobertura 90% (cobertura_insuficiente)
    13/03 esteira com 20 voltas, uma sem FC: cobertura 95% (calculada, hrTSS)
    14/03 corrida sem distancia e sem FC (sem_pace)
    15/03 triatlo: pai e duas trocas (ignoradas) mais natacao (modalidade_sem_carga), ciclismo e corrida
    16/03 corrida com FC e sem distancia (calculada, hrTSS)
    20/03 corrida so no JSON, sem voltas: volta unica (calculada, rTSS, granularidade atividade)
    05/04, 15/04 e 16/04 corridas leves: 15/04 e o dia 41 da serie (aprendendo) e 16/04 o dia 42 (nao)
"""

from __future__ import annotations

import importlib.util
import json
import sys
from datetime import datetime
from pathlib import Path

from fit_tool.fit_file_builder import FitFileBuilder
from fit_tool.profile.messages.file_id_message import FileIdMessage
from fit_tool.profile.messages.lap_message import LapMessage
from fit_tool.profile.messages.session_message import SessionMessage
from fit_tool.profile.profile_type import FileType, Intensity, Manufacturer, Sport, SubSport

_AQUI = Path(__file__).resolve().parent


def _carregar(nome: str):
    spec = importlib.util.spec_from_file_location(nome, _AQUI / f"{nome}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


base = _carregar("gerar_fixtures")
saude = _carregar("gerar_fixtures_saude")

AQUEC, TIRO, RECUP, DESAQ = base.AQUEC, base.TIRO, base.RECUP, base.DESAQ
_utc = base._utc
Atividade = base.Atividade

_RUN = ("running", "RUNNING", Sport.RUNNING, SubSport.GENERIC)
_ESTEIRA = ("treadmill_running", "RUNNING", Sport.RUNNING, SubSport.TREADMILL)
_CICLO = ("cycling", "CYCLING", Sport.CYCLING, SubSport.ROAD)
_NADO = ("lap_swimming", "SWIMMING", Sport.SWIMMING, SubSport.LAP_SWIMMING)
_AGUAS = ("open_water_swimming", "SWIMMING", Sport.SWIMMING, SubSport.OPEN_WATER)
_PAI = ("multi_sport", "MULTI_SPORT", Sport.MULTISPORT, SubSport.GENERIC)
_TROCA = ("transition", "TRANSITION", Sport.TRANSITION, SubSport.GENERIC)

# --------------------------------------------------------------------------
# TABELA DAS VOLTAS (valores inventados). Cada volta: (intensidade, distancia_m, duracao_s, fc_media | None)
# --------------------------------------------------------------------------
V_0303 = [(TIRO, 1000, d, fc) for d, fc in [(330, 140), (326, 142), (322, 144), (324, 145), (320, 146)]]
V_0404 = [(TIRO, 1000, 300, fc) for fc in (150, 152, 153, 154)]
V_0503 = [
    (AQUEC, 2000, 720, 130),
    (TIRO, 1000, 255, 165), (RECUP, 400, 150, 150),
    (TIRO, 1000, 252, 168), (RECUP, 400, 150, 152),
    (DESAQ, 1000, 360, 140),
]
V_0603 = [(TIRO, 100, d, hr) for d, hr in [(110, 120), (112, 124), (115, 126), (118, 128)]]
V_0703 = [(AQUEC, 10000, 1500, 120), (TIRO, 20000, 2400, 150), (DESAQ, 5000, 900, 125)]
V_0803_CORRIDA = [(TIRO, 1000, d, None) for d in (300, 298, 296, 294, 292, 290)]
V_0803_ESTEIRA = [(TIRO, 1000, 330, None)] * 4
V_1003 = [
    (AQUEC, 1500, 540, 135),
    (TIRO, 1000, 240, 170), (RECUP, 400, 160, 150),
    (TIRO, 1000, 238, 172), (RECUP, 400, 160, 152),
    (TIRO, 1000, 236, 174),
    (DESAQ, 1000, 380, 138),
]
V_1103 = [(AQUEC, 8000, 1200, 125), (TIRO, 15000, 1800, 148), (DESAQ, 4000, 600, 120)]
V_1203 = [(TIRO, 300, 100, None if i == 4 else 150 + i) for i in range(10)]  # 900 s de 1000 s com FC
V_1303 = [(TIRO, 150, 50, None if i == 7 else 150 + (i % 5)) for i in range(20)]  # 950 s de 1000 s com FC
V_1403 = [(TIRO, 0, 600, None)] * 4
V_1503_CICLO = [(AQUEC, 6000, 900, 125), (TIRO, 12000, 1500, 150)]
V_1503_CORRIDA = [(TIRO, 1000, 250, 168), (TIRO, 1000, 248, 170), (TIRO, 1000, 246, 172)]
V_1603 = [(TIRO, 0, 600, fc) for fc in (140, 145, 150, 155)]
V_0504 = [(TIRO, 1000, d, 140 + i) for i, d in enumerate((360, 358, 356, 354))]
V_1504 = [(TIRO, 1000, d, 142 + i) for i, d in enumerate((350, 348, 346))]
V_1604 = [(TIRO, 1000, d, 144 + i) for i, d in enumerate((345, 343, 341, 339))]


def _a(id_: int, nome: str, tipo, inicio: datetime, voltas, fuso_h: int = -3, json_total=None):
    return Atividade(id_, nome, *tipo, inicio, voltas, json_total=json_total, fuso_h=fuso_h)


# Ordem cronologica. ``inicio`` em UTC; o fuso e -3 h, entao a data local pode ser a do dia anterior.
ATIVIDADES = [
    _a(4000000001, "Corrida 5 km", _RUN, _utc(2025, 3, 3, 9, 0), V_0303),
    _a(4000000002, "Corrida noturna 4 km", _RUN, _utc(2025, 3, 5, 1, 0), V_0404),  # local 04/03 22:00
    _a(4000000003, "Intervalado 2 x 1 km", _RUN, _utc(2025, 3, 5, 9, 0), V_0503),
    _a(4000000004, "Natacao 400 m", _NADO, _utc(2025, 3, 6, 7, 0), V_0603),
    _a(4000000005, "Pedal 35 km", _CICLO, _utc(2025, 3, 7, 8, 0), V_0703),
    _a(4000000006, "Corrida sem FC", _RUN, _utc(2025, 3, 8, 8, 0), V_0803_CORRIDA),
    _a(4000000007, "Esteira sem FC", _ESTEIRA, _utc(2025, 3, 8, 18, 0), V_0803_ESTEIRA),
    _a(4000000008, "Intervalado 3 x 1 km", _RUN, _utc(2025, 3, 10, 9, 0), V_1003),
    _a(4000000009, "Pedal noturno", _CICLO, _utc(2025, 3, 12, 2, 0), V_1103),  # local 11/03 23:00
    _a(4000000010, "Esteira 10 voltas", _ESTEIRA, _utc(2025, 3, 12, 18, 0), V_1203),
    _a(4000000011, "Esteira 20 voltas", _ESTEIRA, _utc(2025, 3, 13, 18, 0), V_1303),
    _a(4000000012, "Corrida sem GPS e sem FC", _RUN, _utc(2025, 3, 14, 8, 0), V_1403),
    # triatlo de 15/03: pai e trocas so no JSON (sem FIT); as partes tem a sua propria linha
    _a(4000000013, "Triatlo sprint", _PAI, _utc(2025, 3, 15, 7, 0), None, json_total=(12300.0, 2700.0, None)),
    _a(4000000014, "Triatlo: natacao", _AGUAS, _utc(2025, 3, 15, 7, 0), None, json_total=(750.0, 900.0, 140)),
    _a(4000000015, "Triatlo: troca 1", _TROCA, _utc(2025, 3, 15, 7, 16), None, json_total=(0.0, 60.0, None)),
    _a(4000000016, "Triatlo: ciclismo", _CICLO, _utc(2025, 3, 15, 7, 17), V_1503_CICLO),
    _a(4000000017, "Triatlo: troca 2", _TROCA, _utc(2025, 3, 15, 7, 43), None, json_total=(0.0, 45.0, None)),
    _a(4000000018, "Triatlo: corrida", _RUN, _utc(2025, 3, 15, 7, 44), V_1503_CORRIDA),
    _a(4000000019, "Corrida com FC sem distancia", _RUN, _utc(2025, 3, 16, 8, 0), V_1603),
    # corrida so no JSON (sem FIT, sem voltas): vira uma volta unica, granularidade "atividade"
    _a(4000000023, "Corrida so JSON 5 km", _RUN, _utc(2025, 3, 20, 8, 0), None, json_total=(5000.0, 1500.0, 150)),
    _a(4000000020, "Rodagem 4 km", _RUN, _utc(2025, 4, 5, 9, 0), V_0504),
    _a(4000000021, "Rodagem 3 km", _RUN, _utc(2025, 4, 15, 9, 0), V_1504),
    _a(4000000022, "Rodagem 4 km", _RUN, _utc(2025, 4, 16, 9, 0), V_1604),
]
# Pai e trocas do triatlo: o importador as marca com subtipo multiesporte_pai / troca e a carga as ignora
IGNORADAS_MULTIESPORTE = (4000000013, 4000000015, 4000000017)


def _fc_media(voltas) -> int | None:
    com = [(v[2], v[3]) for v in voltas if v[3] is not None]
    if not com:
        return None
    return round(sum(d * f for d, f in com) / sum(d for d, _ in com))


def totais(a: Atividade) -> tuple[float, float, int | None]:
    if a.voltas is None:
        return a.json_total
    return sum(v[1] for v in a.voltas), sum(v[2] for v in a.voltas), _fc_media(a.voltas)


def montar_fit(a: Atividade) -> bytes:
    inicio = base._ms(a.inicio)
    b = FitFileBuilder(auto_define=True, min_string_size=50)
    fid = FileIdMessage()
    fid.type = FileType.ACTIVITY
    fid.manufacturer = Manufacturer.GARMIN.value
    fid.product = 1
    fid.serial_number = a.id % 1_000_000
    fid.time_created = inicio
    b.add(fid)
    t = inicio
    for i, (intens, dist, dur, fc) in enumerate(a.voltas):
        lap = LapMessage()
        lap.message_index = i
        lap.start_time = t
        lap.timestamp = t + int(dur * 1000)
        lap.total_elapsed_time = dur
        lap.total_timer_time = dur
        lap.total_distance = dist
        if fc is not None:
            lap.avg_heart_rate = fc
        lap.sport = a.sport_fit
        lap.sub_sport = a.sub_sport_fit
        lap.intensity = {AQUEC: Intensity.WARMUP, TIRO: Intensity.ACTIVE,
                         RECUP: Intensity.REST, DESAQ: Intensity.COOLDOWN}[intens]
        b.add(lap)
        t += int(dur * 1000)
    dist, dur, fc = totais(a)
    s = SessionMessage()
    s.message_index = 0
    s.start_time = inicio
    s.timestamp = t
    s.total_elapsed_time = dur
    s.total_timer_time = dur
    s.total_distance = dist
    if fc is not None:
        s.avg_heart_rate = fc
    s.num_laps = len(a.voltas)
    s.sport = a.sport_fit
    s.sub_sport = a.sub_sport_fit
    b.add(s)
    return b.build().to_bytes()


def montar_json() -> bytes:
    itens = []
    for a in ATIVIDADES:
        dist, dur, fc = totais(a)
        item = {
            "activityId": a.id,
            "name": a.nome,
            "activityType": a.activity_type,
            "sportType": a.sport_type,
            "startTimeGmt": base._ms(a.inicio),
            "startTimeLocal": base._ms(a.inicio) + a.fuso_h * 3_600_000,
            "beginTimestamp": base._ms(a.inicio),
            "duration": dur * 1000,
            "elapsedDuration": dur * 1000,
            "distance": dist * 100,
        }
        if fc is not None:
            item["avgHr"] = fc
        itens.append(item)
    return json.dumps([{"summarizedActivitiesExport": itens}], indent=1).encode()


def _membros_atividades() -> dict[str, bytes]:
    fits = {f"atleta-ficticio_{a.id}.fit": montar_fit(a) for a in ATIVIDADES if a.voltas is not None}
    return {base.CAMINHO_JSON: montar_json(), base.CAMINHO_UPLOADS: base._zip(fits)}


def montar_exportacao_carga() -> bytes:
    membros = _membros_atividades()
    membros.update(saude.membros_saude())
    return base._zip(membros)


def montar_exportacao_carga_sem_saude() -> bytes:
    return base._zip(_membros_atividades())


def main(destino: Path) -> None:
    pasta = destino / "carga"
    pasta.mkdir(parents=True, exist_ok=True)
    (pasta / "exportacao_carga.zip").write_bytes(montar_exportacao_carga())
    (pasta / "exportacao_carga_sem_saude.zip").write_bytes(montar_exportacao_carga_sem_saude())
    print(f"gerados: exportacao_carga.zip e exportacao_carga_sem_saude.zip em {pasta}")


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else _AQUI)
