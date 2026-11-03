"""Gera as fixtures sinteticas do clima da atividade (Meta 4, issue #111; ADR 0007).

Tudo aqui e inventado. O lugar e o "Parque do Exemplo" (lat 12.3456, long -45.6789): nao existe, nao e
posicao de ninguem. Nenhuma coordenada real entra no repositorio. Rode:

    uv run python tests/fixtures/clima/gerar_fixtures_clima.py

Saida deterministica. Gera aqui:
- ``fit/*.fit``: FIT avulsos com posicao de inicio (``session`` ou primeira ``lap``), esteira com coordenada
  e posicao invalida;
- ``exportacao_clima.json``: JSON minimo da exportacao com ``startLatitude``/``startLongitude``;
- ``open_meteo_archive_2026-05-10.json``: resposta gravada (MONTADA A MAO, ver ``_aviso`` no arquivo);
- ``open_meteo_archive_2026-05-10_com_null.json``: a mesma, com ``null`` em horas da janela.

O oraculo (``oraculo_clima.json``) NAO e gerado: foi escrito a mao, com a conta na nota
``docs/metricas/clima-oraculo.md``, e os testes conferem um contra o outro.
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

# Parque do Exemplo (inventado). Arredondado a 2 casas (ADR 0007): 12.35, -45.68.
LAT, LON = 12.3456, -45.6789
# Posicao de OUTRA volta, tambem inventada: o leitor nao pode le-la (so a primeira lap vale).
LAT_SEGUNDA_LAP, LON_SEGUNDA_LAP = 12.9012, -45.1234
FIT_INVALIDO = 0x7FFFFFFF  # sint32 invalido do FIT: "sem posicao"


def _utc(*a) -> datetime:
    return datetime(*a, tzinfo=timezone.utc)


def _ms(dt: datetime) -> int:
    return int(dt.timestamp() * 1000)


# --------------------------------------------------------------------------
# RESPOSTA GRAVADA DO OPEN-METEO (montada a mao; nao veio da rede)
# --------------------------------------------------------------------------
# Formato conforme https://open-meteo.com/en/docs/historical-weather-api (consultada em 03/11/2026):
# hourly.time em "yyyy-mm-ddThh:mm" (timezone=GMT, logo UTC), vento em km/h. Valores inventados, plausiveis
# para um dia quente de maio a ~12 graus de latitude. Indice = hora UTC (0 a 23).
TEMPERATURA = [24.1, 23.8, 23.6, 23.4, 23.2, 23.1, 23.3, 24.2, 25.6, 26.8, 27.9, 28.7,
               29.4, 29.9, 30.1, 29.8, 29.2, 28.3, 27.2, 26.4, 25.8, 25.3, 24.9, 24.5]
SENSACAO = [26.0, 25.6, 25.3, 25.1, 24.9, 24.8, 25.2, 26.7, 28.5, 30.1, 31.6, 32.8,
            33.9, 34.7, 35.0, 34.4, 33.5, 32.0, 30.4, 29.2, 28.3, 27.6, 27.0, 26.5]
UMIDADE = [82, 83, 84, 85, 86, 86, 85, 81, 76, 71, 67, 63,
           60, 58, 57, 58, 61, 65, 70, 74, 77, 79, 80, 81]
VENTO = [7.2, 6.8, 6.5, 6.1, 5.9, 6.0, 6.4, 7.3, 8.5, 9.6, 10.8, 11.5,
         12.2, 12.9, 13.1, 12.6, 11.7, 10.4, 9.1, 8.2, 7.9, 7.6, 7.4, 7.3]

AVISO = ("Resposta SINTETICA montada a mao a partir da documentacao publica do Open-Meteo "
         "(Historical Weather API). Nao foi gravada da rede. Lugar e valores inventados (Parque do "
         "Exemplo). Chave _aviso nao existe na resposta real. Weather data by Open-Meteo.com (CC BY 4.0).")


def montar_resposta(com_null: bool = False) -> dict:
    temperatura: list = list(TEMPERATURA)
    sensacao: list = list(SENSACAO)
    if com_null:
        # null na temperatura das 10h (janela de A e B) e na sensacao das 11h (janela de B).
        # F (13h a 16h) nao toca nenhuma das duas e continua "ok".
        temperatura[10] = None
        sensacao[11] = None
    return {
        "_aviso": AVISO,
        "latitude": 12.35,
        "longitude": -45.68,
        "generationtime_ms": 0.5,
        "utc_offset_seconds": 0,
        "timezone": "GMT",
        "timezone_abbreviation": "GMT",
        "elevation": 38.0,
        "hourly_units": {"time": "iso8601", "temperature_2m": "°C", "apparent_temperature": "°C",
                         "relative_humidity_2m": "%", "wind_speed_10m": "km/h"},
        "hourly": {
            "time": [f"2026-05-10T{h:02d}:00" for h in range(24)],
            "temperature_2m": temperatura,
            "apparent_temperature": sensacao,
            "relative_humidity_2m": list(UMIDADE),
            "wind_speed_10m": list(VENTO),
        },
    }


# --------------------------------------------------------------------------
# FIT
# --------------------------------------------------------------------------
# nome -> (id, sport, sub_sport, inicio, duracao_s, posicao_session, posicao_lap1)
# posicao = (lat_graus, lon_graus) ou FIT_INVALIDO (valor cru), ou None (campo ausente)
FITS = {
    # A: 09:20 a 10:10 -> 40 min na hora 09h e 10 min na 10h. Posicao na session.
    "corrida_ar_livre.fit": (3000000001, Sport.RUNNING, SubSport.GENERIC,
                             _utc(2026, 5, 10, 9, 20, 0), 3000, (LAT, LON), None),
    # B: 10:45 a 11:15 -> 15 min em 10h e 15 min em 11h. Session SEM posicao; so a primeira lap tem.
    "corrida_posicao_na_lap.fit": (3000000002, Sport.RUNNING, SubSport.GENERIC,
                                   _utc(2026, 5, 10, 10, 45, 0), 1800, None, (LAT, LON)),
    # C: esteira com coordenada no arquivo (17:50 a 18:30). Deve virar indoor e sem posicao gravada.
    "esteira_com_posicao.fit": (3000000003, Sport.RUNNING, SubSport.TREADMILL,
                                _utc(2026, 5, 10, 17, 50, 0), 2400, (LAT, LON), None),
    # D1: (0, 0) depois do arredondamento: "sem GPS" comum em dispositivos.
    "corrida_posicao_zero.fit": (3000000004, Sport.RUNNING, SubSport.GENERIC,
                                 _utc(2026, 5, 10, 12, 30, 0), 3600, (0.0, 0.0), None),
    # D2: valor invalido do FIT (0x7FFFFFFF) nos dois campos.
    "corrida_posicao_invalida.fit": (3000000005, Sport.RUNNING, SubSport.GENERIC,
                                     _utc(2026, 5, 10, 6, 40, 0), 2400, FIT_INVALIDO, None),
    # F: 13:40 a 16:10 (2 h 30) -> toca 4 horas: 20, 60, 60 e 10 min.
    "corrida_longa_4_horas.fit": (3000000006, Sport.RUNNING, SubSport.GENERIC,
                                  _utc(2026, 5, 10, 13, 40, 0), 9000, (LAT, LON), None),
}


def _pos(msg, posicao) -> None:
    if posicao is None:
        return
    for i, campo in enumerate(("start_position_lat", "start_position_long")):
        f = next(x for x in msg.fields if x.name == campo)
        if posicao == FIT_INVALIDO:
            f.set_encoded_value(0, FIT_INVALIDO)
        else:
            f.set_value(0, posicao[i])


def montar_fit(id_: int, sport, sub_sport, inicio: datetime, duracao_s: int, pos_session, pos_lap) -> bytes:
    t0 = _ms(inicio)
    b = FitFileBuilder(auto_define=True, min_string_size=50)
    fid = FileIdMessage()
    fid.type = FileType.ACTIVITY
    fid.manufacturer = Manufacturer.GARMIN.value
    fid.product = 1
    fid.serial_number = id_ % 1_000_000
    fid.time_created = t0
    b.add(fid)

    # Duas voltas (metade cada). So a PRIMEIRA pode ter posicao valida; a segunda, quando existe
    # posicao na lap, traz outra posicao inventada que o leitor nao deve usar.
    metade = duracao_s // 2
    for i, (ini, dur) in enumerate([(t0, metade), (t0 + metade * 1000, duracao_s - metade)]):
        lap = LapMessage()
        lap.message_index = i
        lap.start_time = ini
        lap.timestamp = ini + dur * 1000
        lap.total_elapsed_time = dur
        lap.total_timer_time = dur
        lap.total_distance = dur * 3.0  # 3 m/s, inventado
        lap.sport = sport
        lap.sub_sport = sub_sport
        if pos_lap is not None:
            _pos(lap, pos_lap if i == 0 else (LAT_SEGUNDA_LAP, LON_SEGUNDA_LAP))
        b.add(lap)

    s = SessionMessage()
    s.message_index = 0
    s.start_time = t0
    s.timestamp = t0 + duracao_s * 1000
    s.total_elapsed_time = duracao_s
    s.total_timer_time = duracao_s
    s.total_distance = duracao_s * 3.0
    s.num_laps = 2
    s.sport = sport
    s.sub_sport = sub_sport
    _pos(s, pos_session)
    b.add(s)
    return b.build().to_bytes()


def montar_fits() -> dict[str, bytes]:
    return {nome: montar_fit(*args) for nome, args in FITS.items()}


# --------------------------------------------------------------------------
# JSON MINIMO DA EXPORTACAO (mesmo formato de tests/fixtures/garmin, com posicao de inicio)
# --------------------------------------------------------------------------
def _item_json(id_, nome, activity_type, sport_type, inicio, duracao_s, lat=None, lon=None) -> dict:
    item = {
        "activityId": id_, "name": nome, "activityType": activity_type, "sportType": sport_type,
        "startTimeGmt": _ms(inicio), "beginTimestamp": _ms(inicio),
        "duration": duracao_s * 1000, "elapsedDuration": duracao_s * 1000,
        "distance": duracao_s * 3.0 * 100, "avgHr": 140,
    }
    if lat is not None:
        item["startLatitude"] = lat
        item["startLongitude"] = lon
    return item


def montar_json() -> bytes:
    itens = [
        _item_json(3000000101, "Corrida no Parque do Exemplo", "running", "RUNNING",
                   _utc(2026, 5, 10, 9, 20, 0), 3000, LAT, LON),
        _item_json(3000000102, "Esteira com coordenada", "treadmill_running", "RUNNING",
                   _utc(2026, 5, 10, 17, 50, 0), 2400, LAT, LON),
        _item_json(3000000103, "Corrida com ponto zero", "running", "RUNNING",
                   _utc(2026, 5, 10, 12, 30, 0), 3600, 0.0, 0.0),
        _item_json(3000000104, "Pedal virtual com coordenada", "virtual_ride", "CYCLING",
                   _utc(2026, 5, 10, 15, 30, 0), 3600, LAT, LON),
        _item_json(3000000105, "Corrida sem coordenada", "running", "RUNNING",
                   _utc(2026, 5, 10, 6, 40, 0), 2400),
    ]
    return json.dumps([{"summarizedActivitiesExport": itens}], indent=1).encode()


def _json_bytes(obj: dict) -> bytes:
    return (json.dumps(obj, indent=1, ensure_ascii=False) + "\n").encode()


def montar_tudo() -> dict[str, bytes]:
    """Caminho relativo a pasta clima/ -> conteudo."""
    saida = {f"fit/{n}": c for n, c in montar_fits().items()}
    saida["exportacao_clima.json"] = montar_json()
    saida["open_meteo_archive_2026-05-10.json"] = _json_bytes(montar_resposta())
    saida["open_meteo_archive_2026-05-10_com_null.json"] = _json_bytes(montar_resposta(com_null=True))
    return saida


def main(destino: Path) -> None:
    for rel, conteudo in montar_tudo().items():
        alvo = destino / rel
        alvo.parent.mkdir(parents=True, exist_ok=True)
        alvo.write_bytes(conteudo)
        print(f"gerado: {alvo}")


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent)
