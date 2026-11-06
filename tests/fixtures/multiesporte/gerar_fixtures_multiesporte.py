"""Gera as fixtures sinteticas do multiesporte (issue #230, ADR 0009). Tudo inventado: sem GPS, nome ou id real.

    uv run python tests/fixtures/multiesporte/gerar_fixtures_multiesporte.py

Saida deterministica. Gera:
- ``exportacao_multiesporte.json``: um treino de 3 partes inventado (natacao, ciclismo, corrida) com a atividade
  que agrupa (`multi_sport`), duas trocas (`transition`) e uma corrida solta. O pai repete o tempo e a distancia
  das partes (e das trocas), como descrito na issue #230.
- ``fit/multiesporte_pai.fit`` e ``fit/troca.fit``: FIT com `sport` = `multisport` e `transition`, valores do enum
  `sport` do Profile do FIT SDK (https://developer.garmin.com/fit/), onde multisport = 18 e transition = 3.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from fit_tool.fit_file_builder import FitFileBuilder
from fit_tool.profile.messages.file_id_message import FileIdMessage
from fit_tool.profile.messages.lap_message import LapMessage
from fit_tool.profile.messages.session_message import SessionMessage
from fit_tool.profile.profile_type import FileType, Manufacturer, Sport, SubSport


def _utc(*a) -> datetime:
    return datetime(*a, tzinfo=timezone.utc)


def _ms(dt: datetime) -> int:
    return int(dt.timestamp() * 1000)


# (id, nome, activityType, sportType, inicio, duracao_s, distancia_m)
ITENS = [
    (3000000201, "Treino multiesporte ficticio", "multi_sport", "MULTI_SPORT", _utc(2030, 3, 2, 7, 0, 0), 5400, 36000),
    (3000000202, "Natacao do multiesporte", "open_water_swimming", "SWIMMING", _utc(2030, 3, 2, 7, 0, 0), 1200, 1000),
    (3000000203, "Troca 1", "transition", "TRANSITION", _utc(2030, 3, 2, 7, 20, 0), 120, 0),
    (3000000204, "Pedal do multiesporte", "road_biking", "CYCLING", _utc(2030, 3, 2, 7, 22, 0), 2700, 30000),
    (3000000205, "Troca 2", "transition", "TRANSITION", _utc(2030, 3, 2, 8, 7, 0), 60, 0),
    (3000000206, "Corrida do multiesporte", "running", "RUNNING", _utc(2030, 3, 2, 8, 8, 0), 1320, 5000),
    (3000000207, "Corrida solta ficticia", "running", "RUNNING", _utc(2030, 3, 5, 7, 0, 0), 1800, 5000),
]


def montar_json() -> bytes:
    itens = [{
        "activityId": i, "name": nome, "activityType": at, "sportType": st,
        "startTimeGmt": _ms(ini), "beginTimestamp": _ms(ini),
        "duration": dur * 1000, "elapsedDuration": dur * 1000, "distance": dist * 100.0, "avgHr": 140,
    } for i, nome, at, st, ini, dur, dist in ITENS]
    return json.dumps([{"summarizedActivitiesExport": itens}], indent=1).encode()


def montar_fit(id_: int, sport, inicio: datetime, duracao_s: int) -> bytes:
    t0 = _ms(inicio)
    b = FitFileBuilder(auto_define=True, min_string_size=50)
    fid = FileIdMessage()
    fid.type = FileType.ACTIVITY
    fid.manufacturer = Manufacturer.GARMIN.value
    fid.product = 1
    fid.serial_number = id_ % 1_000_000
    fid.time_created = t0
    b.add(fid)
    lap = LapMessage()
    lap.message_index = 0
    lap.start_time = t0
    lap.timestamp = t0 + duracao_s * 1000
    lap.total_elapsed_time = duracao_s
    lap.total_timer_time = duracao_s
    lap.total_distance = duracao_s * 3.0
    lap.sport = sport
    lap.sub_sport = SubSport.GENERIC
    b.add(lap)
    s = SessionMessage()
    s.message_index = 0
    s.start_time = t0
    s.timestamp = t0 + duracao_s * 1000
    s.total_elapsed_time = duracao_s
    s.total_timer_time = duracao_s
    s.total_distance = duracao_s * 3.0
    s.num_laps = 1
    s.sport = sport
    s.sub_sport = SubSport.GENERIC
    b.add(s)
    return b.build().to_bytes()


def montar_tudo() -> dict[str, bytes]:
    return {
        "exportacao_multiesporte.json": montar_json(),
        "fit/multiesporte_pai.fit": montar_fit(3000000301, Sport.MULTISPORT, _utc(2030, 3, 9, 7, 0, 0), 5400),
        "fit/troca.fit": montar_fit(3000000302, Sport.TRANSITION, _utc(2030, 3, 9, 7, 20, 0), 120),
    }


def main(destino: Path) -> None:
    for rel, conteudo in montar_tudo().items():
        alvo = destino / rel
        alvo.parent.mkdir(parents=True, exist_ok=True)
        alvo.write_bytes(conteudo)
        print(f"gerado: {alvo}")


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent)
