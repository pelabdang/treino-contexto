"""Gera as fixtures sinteticas dos dados de saude e metricas da exportacao Garmin (Meta 6, issue #135).

Tudo aqui e inventado: valores, identificador de usuario, nomes e datas. Rode:

    uv run python tests/fixtures/garmin/gerar_fixtures_saude.py

Saida deterministica, em ``saude/``:

- ``exportacao_saude.zip``: as 5 atividades de ``exportacao_minima.zip`` (mesmos ``activityId`` e datas) mais os
  arquivos de saude e metricas, na estrutura de pastas da exportacao. Os FIT dessa exportacao trazem as mensagens
  ``time_in_zone`` e ``zones_target`` (zonas, FC maxima, de repouso e limiar vigentes na atividade).
- ``exportacao_sem_saude.zip``: o atleta sem nenhum dado de saude. So atividades e FIT comuns, nenhuma das pastas de
  saude e metricas.

LINHA DO TEMPO (a fonte da verdade dos valores, para conferir a mao). Atividades: A 04/03 (1000000001), C 06/03
(1000000003), D 07/03 (1000000004, natacao), B 11/03 (1000000002), E 13/03 (1000000005, sem FIT).

    ate 04/03   sem limiar de lactato (registros so de VO2 max e um registro de FC de limiar zero = sem limiar)
    05/03       1o limiar: FC 158 bpm, velocidade 0,370 (x10 = 3,70 m/s)
    08/03       limiar de FC alterado a mao para 159 bpm (registro so de FC, sem velocidade); FC maxima 190 -> 188
                (as zonas mudam; so os FIT de B em diante e o heartRateZones.json trazem a FC maxima nova)
    10/03       2o limiar: FC 163 bpm, velocidade 0,385 (x10 = 3,85 m/s)

    Atividade   data    FC limiar no FIT   FC maxima no FIT
    A           04/03   ausente            190
    C           06/03   158                190
    D           07/03   158                190
    B           11/03   163                188
    E           13/03   (sem FIT)

Carga aguda/cronica: um item por dia de 24/02 a 20/03 (alguns dias com mais de um item, vale o de maior
``timestamp``); o primeiro dia vem sem a razao (``acwrStatus`` NONE).
"""

from __future__ import annotations

import importlib.util
import io
import json
import sys
import zipfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from fit_tool.fit_file import FitFile
from fit_tool.fit_file_builder import FitFileBuilder
from fit_tool.profile.messages.time_in_zone_message import TimeInZoneMessage
from fit_tool.profile.messages.zones_target_message import ZonesTargetMessage
from fit_tool.profile.profile_type import HrZoneCalc, MesgNum

_AQUI = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("gerar_fixtures_base", _AQUI / "gerar_fixtures.py")
base = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = base
_spec.loader.exec_module(base)

ID_USUARIO = 7000001  # inventado
ID_DISPOSITIVO = 4100000001  # inventado
RAIZ = base.RAIZ_ZIP  # DI_CONNECT

# --------------------------------------------------------------------------
# LINHA DO TEMPO DO LIMIAR E DAS ZONAS (valores inventados)
# --------------------------------------------------------------------------
FC_REPOUSO = 52
FC_MAX_ANTES, FC_MAX_DEPOIS = 190, 188
DATA_MUDANCA_ZONAS = date(2025, 3, 8)  # a partir daqui a FC maxima vigente e a nova
# (data, FC limiar bpm | None, velocidade limiar | None). Velocidade como vem no arquivo: m/s dividido por 10.
LIMIARES = [
    (date(2025, 3, 5), 158, 0.370),
    (date(2025, 3, 8), 159, None),  # so FC, alterada a mao
    (date(2025, 3, 10), 163, 0.385),
]
PERCENTUAIS_ZONA = (0.5, 0.6, 0.7, 0.8, 0.9, 1.0)  # 6 limites superiores, como no FIT real (7 tempos)


def fc_max_em(dia: date) -> int:
    return FC_MAX_DEPOIS if dia >= DATA_MUDANCA_ZONAS else FC_MAX_ANTES


def fc_limiar_em(dia: date) -> int | None:
    """FC de limiar vigente no dia (o ultimo registro de limiar ate ele); ``None`` antes do primeiro."""
    vigente = None
    for d, fc, _ in LIMIARES:
        if d <= dia:
            vigente = fc
    return vigente


def limites_zona(fc_max: int) -> list[int]:
    return [round(fc_max * p) for p in PERCENTUAIS_ZONA]


# --------------------------------------------------------------------------
# FIT COM ZONAS (time_in_zone e zones_target)
# --------------------------------------------------------------------------
def _tempos_por_zona(voltas, limites: list[int]) -> list[float]:
    """7 tempos (s): indice = quantos limites a FC media da volta ultrapassa."""
    tempos = [0.0] * (len(limites) + 1)
    for _, _, dur, fc in voltas:
        tempos[sum(1 for lim in limites if fc > lim)] += dur
    return tempos


def montar_fit_com_zonas(a: base.Atividade) -> bytes:
    original = FitFile.from_bytes(base.montar_fit(a))
    dia = a.inicio.date()
    fc_max, limiar = fc_max_em(dia), fc_limiar_em(dia)
    limites = limites_zona(fc_max)

    b = FitFileBuilder(auto_define=True, min_string_size=50)
    for r in original.records:
        if r.message.__class__.__name__ == "DefinitionMessage":
            continue
        # time_in_zone e zones_target entram antes da session, como o relogio grava
        if r.message.__class__.__name__ == "SessionMessage":
            alvo = ZonesTargetMessage()
            alvo.max_heart_rate = fc_max
            alvo.hr_calc_type = HrZoneCalc.PERCENT_MAX_HR
            if limiar is not None:
                alvo.threshold_heart_rate = limiar
            b.add(alvo)

            tz = TimeInZoneMessage()
            tz.timestamp = r.message.timestamp
            tz.reference_mesg = MesgNum.SESSION
            tz.reference_index = 0
            tz.hr_calc_type = HrZoneCalc.PERCENT_MAX_HR
            tz.hr_zone_high_boundary = limites
            tz.time_in_hr_zone = _tempos_por_zona(a.voltas, limites)
            tz.max_heart_rate = fc_max
            tz.resting_heart_rate = FC_REPOUSO
            if limiar is not None:
                tz.threshold_heart_rate = limiar
            b.add(tz)
        b.add(r.message)
    return b.build().to_bytes()


# --------------------------------------------------------------------------
# JSON DE SAUDE
# --------------------------------------------------------------------------
def _ms(dt: datetime) -> int:
    return int(dt.replace(tzinfo=timezone.utc).timestamp() * 1000)


_FLAGS_USER_SET_NULL = [
    "userSetNullForHeight", "userSetNullForWeight", "userSetNullForActivityClass",
    "userSetNullForLactateThresholdSpeed", "userSetNullForLactateThresholdRowingPace",
    "userSetNullForLactateThresholdHR", "userSetNullForLactateThresholdRowingHR",
    "userSetNullForVO2MaxCycling", "userSetNullForVO2MaxRunning",
]
_EPOCA_GARMIN = datetime(1989, 12, 31)  # firstbeatRunningLtTimestamp: segundos desde aqui


def _registro_bio(quando: datetime, seq: int, **campos) -> dict:
    return {
        "version": _ms(quando) + 3_600_000 * 11 + seq,
        "metaData": {
            "userProfilePK": ID_USUARIO,
            "calendarDate": quando.strftime("%Y-%m-%dT%H:%M:%S.") + f"{quando.microsecond // 1000}",
            "sequence": _ms(quando) + seq,
        },
        **{f: False for f in _FLAGS_USER_SET_NULL},
        **campos,
    }


def _lt_ts(quando: datetime) -> int:
    return int((quando - _EPOCA_GARMIN).total_seconds())


def montar_user_bio_metrics() -> list[dict]:
    """Historico de alteracoes de limiar (e outros), na ordem em que o arquivo traz: NAO e estritamente cronologica."""
    r = _registro_bio
    d = datetime
    return [
        r(d(2025, 2, 18, 9, 0), 1, vo2MaxRunning=48.0),
        r(d(2025, 2, 25, 9, 0), 2, lactateThresholdHearRate=0, thresholdHeartRateAutoDetected=False),  # 0 = sem limiar
        r(d(2025, 3, 1, 9, 0), 3, vo2MaxRunning=48.5),
        r(d(2025, 2, 21, 9, 0, 0, 123000), 4, vo2MaxRunning=48.2),  # fora de ordem de proposito
        r(d(2025, 3, 5, 9, 0), 5, lactateThresholdHearRate=158, lactateThresholdSpeed=0.370,
          thresholdHeartRateAutoDetected=True, firstbeatRunningLtTimestamp=_lt_ts(d(2025, 3, 5, 9, 0)),
          vo2MaxRunning=49.0),
        r(d(2025, 3, 8, 9, 0), 6, lactateThresholdHearRate=159, thresholdHeartRateAutoDetected=False),
        r(d(2025, 3, 10, 9, 0), 7, lactateThresholdHearRate=163, lactateThresholdSpeed=0.385,
          thresholdHeartRateAutoDetected=True, firstbeatRunningLtTimestamp=_lt_ts(d(2025, 3, 10, 9, 0)),
          vo2MaxRunning=49.5),
        r(d(2025, 3, 12, 9, 0), 8, vo2MaxRunning=49.6),
    ]


def montar_heart_rate_zones() -> list[dict]:
    """Retrato atual (sem data): uma entrada por esporte."""
    def entrada(esporte: str, fc_max: int, limiar: int) -> dict:
        pisos = limites_zona(fc_max)
        return {
            "trainingMethod": "HR_MAX",
            "restingHeartRateUsed": FC_REPOUSO,
            "lactateThresholdHeartRateUsed": limiar,
            "zone1Floor": pisos[0], "zone2Floor": pisos[1], "zone3Floor": pisos[2],
            "zone4Floor": pisos[3], "zone5Floor": pisos[4],
            "maxHeartRateUsed": fc_max,
            "restingHrAutoUpdateUsed": True,
            "sport": esporte,
            "changeState": "UNCHANGED",
        }
    return [entrada("DEFAULT", FC_MAX_DEPOIS, 163), entrada("RUNNING", FC_MAX_DEPOIS, 163),
            entrada("CYCLING", 184, 150)]


def montar_bio_metrics_latest() -> list[dict]:
    return [{"lactateThresholdSpeed": 0.385, "lactateThresholdHeartRate": 163, "functionalThresholdPower": 200}]


def montar_personal_records() -> list[dict]:
    def pr(i, atividade, valor, quando, tipo, criado, atual):
        return {"personalRecordId": 6000000000 + i, "activityId": atividade, "value": valor,
                "prStartTimeGMT": quando.strftime("%a %b %d %H:%M:%S GMT %Y"),
                "personalRecordType": tipo, "createdDate": criado, "current": atual, "confirmed": True}
    d = datetime
    itens = [
        pr(1, 1000000001, 248.0, d(2025, 3, 4, 10, 0), "Best 1km Run", "2025-03-04", False),
        pr(2, 1000000002, 234.0, d(2025, 3, 11, 9, 5), "Best 1km Run", "2025-03-11", True),
        pr(3, 1000000003, 1750.0, d(2025, 3, 6, 8, 30), "Best 5km Run", "2025-03-06", True),
        pr(4, 1000000003, 8000.0, d(2025, 3, 6, 8, 30), "Farthest Run", "2025-03-06", True),
        pr(5, 1000000004, 440.0, d(2025, 3, 7, 7, 0), "Best 400m Pool Swim", "2025-03-07", True),
        pr(6, 0, 9000.0, d(2025, 3, 9, 0, 0), "Most Steps in a Day", "2025-03-10", True),  # sem atividade: 0
    ]
    return [{"personalRecords": itens}]


# --------------------------------------------------------------------------
# CARGA AGUDA/CRONICA
# --------------------------------------------------------------------------
INICIO_CARGA = date(2025, 2, 24)
FIM_CARGA = date(2025, 3, 20)  # inclusive
TROCA_ARQUIVO = date(2025, 3, 10)  # 1o arquivo [24/02, 10/03), 2o [10/03, 21/03)
CARGA_DO_DIA = {date(2025, 3, 4): 70, date(2025, 3, 6): 40, date(2025, 3, 7): 20,
                date(2025, 3, 11): 75, date(2025, 3, 13): 55}
DIAS_COM_DOIS_ITENS = {date(2025, 3, 4), date(2025, 3, 6), date(2025, 3, 11)}


def _status(razao: float) -> tuple[str, str]:
    if razao < 0.8:
        return "LOW", "FEEDBACK_1"
    if razao <= 1.3:
        return "OPTIMAL", "FEEDBACK_2"
    if razao <= 1.5:
        return "HIGH", "FEEDBACK_4"
    return "VERY_HIGH", "FEEDBACK_5"


def montar_carga() -> list[dict]:
    """Itens da carga em ordem de arquivo (por dia; no dia com dois itens, o parcial vem antes do final)."""
    itens = []
    agudo, cronico = 40, 55
    dia = INICIO_CARGA
    while dia <= FIM_CARGA:
        agudo = round(0.85 * agudo + CARGA_DO_DIA.get(dia, 0))
        cronico = round(0.96 * cronico + 0.04 * agudo)
        meia_noite = _ms(datetime(dia.year, dia.month, dia.day))

        def item(ag, cr, horas, primeiro_dia=False):
            razao = round(ag / cr, 1)
            base_item = {"userProfilePK": ID_USUARIO, "calendarDate": meia_noite, "deviceId": ID_DISPOSITIVO,
                         "timestamp": meia_noite + horas * 3_600_000, "dailyTrainingLoadAcute": ag,
                         "dailyTrainingLoadChronic": cr}
            if primeiro_dia:  # sem razao: o relogio ainda nao calculou
                return {**base_item, "acwrStatus": "NONE", "acwrStatusFeedback": "NONE"}
            status, fb = _status(razao)
            return {**base_item, "acwrPercent": min(100, round(razao * 50)), "acwrStatus": status,
                    "acwrStatusFeedback": fb, "dailyAcuteChronicWorkloadRatio": razao}

        if dia in DIAS_COM_DOIS_ITENS:
            itens.append(item(agudo - 10, cronico, 9))  # parcial, antes do treino ser contado
        itens.append(item(agudo, cronico, 21, primeiro_dia=dia == INICIO_CARGA))
        dia += timedelta(days=1)
    return itens


def _arquivos_carga() -> dict[str, list[dict]]:
    todos = montar_carga()
    corte = _ms(datetime(TROCA_ARQUIVO.year, TROCA_ARQUIVO.month, TROCA_ARQUIVO.day))
    fim = FIM_CARGA + timedelta(days=1)
    nome = "MetricsAcuteTrainingLoad_{}_{}_{}.json"
    fmt = "%Y%m%d"
    return {
        nome.format(INICIO_CARGA.strftime(fmt), TROCA_ARQUIVO.strftime(fmt), ID_USUARIO):
            [i for i in todos if i["calendarDate"] < corte],
        nome.format(TROCA_ARQUIVO.strftime(fmt), fim.strftime(fmt), ID_USUARIO):
            [i for i in todos if i["calendarDate"] >= corte],
    }


# --------------------------------------------------------------------------
# ZIPS
# --------------------------------------------------------------------------
def _json(obj) -> bytes:
    return json.dumps(obj, indent=1).encode()


def membros_saude() -> dict[str, bytes]:
    bem_estar = f"{RAIZ}/DI-Connect-Wellness/{ID_USUARIO}_"
    membros = {
        bem_estar + "userBioMetrics.json": _json(montar_user_bio_metrics()),
        bem_estar + "heartRateZones.json": _json(montar_heart_rate_zones()),
        bem_estar + "bioMetrics_latest.json": _json(montar_bio_metrics_latest()),
        f"{RAIZ}/DI-Connect-Fitness/atleta-ficticio_personalRecord.json": _json(montar_personal_records()),
    }
    for nome, itens in _arquivos_carga().items():
        membros[f"{RAIZ}/DI-Connect-Metrics/{nome}"] = _json(itens)
    return membros


def montar_exportacao_saude() -> bytes:
    fits = {f"atleta-ficticio_{a.id}.fit": montar_fit_com_zonas(a) for a in base.ATIVIDADES if a.voltas is not None}
    membros = {base.CAMINHO_JSON: base.montar_json(), base.CAMINHO_UPLOADS: base._zip(fits)}
    membros.update(membros_saude())
    return base._zip(membros)


def montar_exportacao_sem_saude() -> bytes:
    return base.montar_exportacao()


def main(destino: Path) -> None:
    pasta = destino / "saude"
    pasta.mkdir(parents=True, exist_ok=True)
    (pasta / "exportacao_saude.zip").write_bytes(montar_exportacao_saude())
    (pasta / "exportacao_sem_saude.zip").write_bytes(montar_exportacao_sem_saude())
    print(f"gerados: exportacao_saude.zip e exportacao_sem_saude.zip em {pasta}")


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else _AQUI)
