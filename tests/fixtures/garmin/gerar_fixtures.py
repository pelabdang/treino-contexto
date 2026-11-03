"""Gera as fixtures sinteticas da exportacao Garmin (issue #8).

Tudo aqui e inventado: sem GPS, sem nome, e-mail ou id real. Rode:

    uv run python tests/fixtures/garmin/gerar_fixtures.py

A saida e deterministica (mesmos bytes a cada execucao). A TABELA abaixo e a
fonte da verdade dos valores de cada volta, para conferir a mao.
Cada volta: (intensidade, distancia_m, duracao_s, fc_media).

Tambem gera, em ``fit/``, os FIT avulsos do upload de arquivo (Meta 3, issue #93; ADR 0006). Os valores
esperados e a conta a mao de cada um estao em ``tests/test_fixtures_fit_upload.py``.
"""

from __future__ import annotations

import io
import json
import sys
import zipfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from fit_tool.fit_file_builder import FitFileBuilder
from fit_tool.profile.messages.file_id_message import FileIdMessage
from fit_tool.profile.messages.lap_message import LapMessage
from fit_tool.profile.messages.session_message import SessionMessage
from fit_tool.profile.profile_type import FileType, Intensity, Manufacturer, Sport, SubSport

AQUEC, TIRO, RECUP, DESAQ = "warmup", "active", "rest", "cooldown"

# --------------------------------------------------------------------------
# TABELA DAS VOLTAS (valores inventados)
# --------------------------------------------------------------------------
# (a) 6 x 1 km, recuperacao ativa de 400 m  -> 13 voltas
VOLTAS_A = [
    (AQUEC, 2000, 720, 130),
    (TIRO, 1000, 255, 165), (RECUP, 400, 150, 150),
    (TIRO, 1000, 252, 168), (RECUP, 400, 150, 152),
    (TIRO, 1000, 250, 170), (RECUP, 400, 150, 153),
    (TIRO, 1000, 251, 171), (RECUP, 400, 150, 154),
    (TIRO, 1000, 249, 173), (RECUP, 400, 150, 155),
    (TIRO, 1000, 248, 175),
    (DESAQ, 1500, 585, 135),
]
# (b) 5 x 1 km, recuperacao de 2 min parado (distancia quase zero) -> 11 voltas
VOLTAS_B = [
    (AQUEC, 2000, 700, 128),
    (TIRO, 1000, 240, 166), (RECUP, 10, 120, 140),
    (TIRO, 1000, 238, 170), (RECUP, 10, 120, 145),
    (TIRO, 1000, 237, 172), (RECUP, 10, 120, 146),
    (TIRO, 1000, 236, 174), (RECUP, 10, 120, 147),
    (TIRO, 1000, 234, 177),
    (DESAQ, 1000, 400, 138),
]
# (c) corrida leve de 8 km, auto-lap de 1 km, sem tiros -> 8 voltas
VOLTAS_C = [(TIRO, 1000, d, hr) for d, hr in
            [(352, 138), (349, 141), (351, 142), (348, 143), (350, 144), (353, 145), (351, 146), (347, 147)]]
# (d) natacao em piscina (ignorada na Meta 1) -> 4 voltas de 100 m
VOLTAS_D = [(TIRO, 100, d, hr) for d, hr in [(110, 120), (112, 124), (115, 126), (118, 128)]]


# --------------------------------------------------------------------------
# FIT AVULSOS DO UPLOAD (Meta 3, #93). Datas de abril/2025: nenhuma colide com a exportacao (marco/2025),
# exceto a "mesma atividade", que repete de proposito a 1000000001.
# --------------------------------------------------------------------------
# (f) 5 x 1 km, recuperacao de 400 m -> entra na serie
VOLTAS_F = [
    (AQUEC, 2000, 720, 130),
    (TIRO, 1000, 250, 166), (RECUP, 400, 150, 150),
    (TIRO, 1000, 248, 169), (RECUP, 400, 150, 152),
    (TIRO, 1000, 246, 171), (RECUP, 400, 150, 153),
    (TIRO, 1000, 244, 173), (RECUP, 400, 150, 154),
    (TIRO, 1000, 242, 176),
    (DESAQ, 1500, 585, 135),
]
# (g) rodagem de 6 km, auto-lap de 1 km, sem tiros
VOLTAS_G = [(TIRO, 1000, d, hr) for d, hr in
            [(355, 140), (352, 142), (350, 143), (351, 144), (349, 145), (348, 146)]]
# (h) corrida simples de 3 km em 3 voltas de 1 km (candidatas do empate e chegadas)
VOLTAS_H = [(TIRO, 1000, d, hr) for d, hr in [(360, 140), (358, 142), (356, 144)]]
# (i) 4 x 1 km na esteira
VOLTAS_I = [
    (AQUEC, 1500, 560, 128),
    (TIRO, 1000, 260, 160), (RECUP, 400, 160, 145),
    (TIRO, 1000, 258, 163), (RECUP, 400, 160, 147),
    (TIRO, 1000, 256, 165), (RECUP, 400, 160, 148),
    (TIRO, 1000, 254, 167),
    (DESAQ, 1000, 400, 135),
]
# (j) natacao em piscina, 4 x 100 m
VOLTAS_J = [(TIRO, 100, d, hr) for d, hr in [(108, 118), (110, 122), (113, 125), (116, 127)]]


@dataclass
class Atividade:
    id: int
    nome: str
    activity_type: str  # como vem no JSON da Garmin
    sport_type: str
    sport_fit: Sport
    sub_sport_fit: SubSport
    inicio: datetime  # UTC
    voltas: list[tuple[str, float, float, int]] | None  # None = sem FIT
    json_total: tuple[float, float, int] | None = None  # (distancia_m, duracao_s, fc) se sem voltas
    deslocamento_fit_s: int = 0  # FIT comeca um pouco depois do JSON (testa tolerancia)
    fc_max: int = 0
    fuso_h: int | None = None  # se definido, o JSON traz startTimeLocal = startTimeGmt + fuso_h
    extra: dict = field(default_factory=dict)

    def totais(self) -> tuple[float, float, int]:
        if self.voltas is None:
            return self.json_total
        dist = sum(v[1] for v in self.voltas)
        dur = sum(v[2] for v in self.voltas)
        fc = round(sum(v[2] * v[3] for v in self.voltas) / dur)
        return dist, dur, fc


def _utc(*a) -> datetime:
    return datetime(*a, tzinfo=timezone.utc)


ATIVIDADES = [
    Atividade(1000000001, "Intervalado 6x1km", "running", "RUNNING", Sport.RUNNING, SubSport.GENERIC,
              _utc(2025, 3, 4, 9, 0, 0), VOLTAS_A, fuso_h=-3),
    Atividade(1000000002, "Intervalado 5x1km pista", "track_running", "RUNNING", Sport.RUNNING,
              SubSport.TRACK, _utc(2025, 3, 11, 9, 5, 0), VOLTAS_B, deslocamento_fit_s=2, fuso_h=-3),
    Atividade(1000000003, "Corrida leve 8km", "running", "RUNNING", Sport.RUNNING, SubSport.GENERIC,
              _utc(2025, 3, 6, 8, 30, 0), VOLTAS_C),
    Atividade(1000000004, "Natacao 400m", "lap_swimming", "SWIMMING", Sport.SWIMMING,
              SubSport.LAP_SWIMMING, _utc(2025, 3, 7, 7, 0, 0), VOLTAS_D),
    # (e) intervalado so com JSON (esteira), sem FIT
    Atividade(1000000005, "Intervalado esteira 4x1km", "treadmill_running", "RUNNING", Sport.RUNNING,
              SubSport.TREADMILL, _utc(2025, 3, 13, 18, 0, 0), None, json_total=(7000.0, 2400.0, 158)),
]

_RUN = ("running", "RUNNING", Sport.RUNNING, SubSport.GENERIC)
_INICIO_EMPATE = _utc(2025, 4, 8, 9, 0, 0)

# nome do arquivo em fit/ -> atividade. Os ids sao so para o serial do file_id (id % 1_000_000).
ATIVIDADES_UPLOAD = {
    "upload_intervalado_5x1km.fit": Atividade(
        2000000001, "Intervalado 5x1km", *_RUN, _utc(2025, 4, 1, 9, 0, 0), VOLTAS_F),
    "upload_rodagem_6km.fit": Atividade(
        2000000002, "Rodagem 6km", *_RUN, _utc(2025, 4, 2, 8, 0, 0), VOLTAS_G),
    # mesma atividade da exportacao (1000000001, inicio 09:00:00), FIT comecando 30 s depois
    "upload_mesma_atividade_1000000001.fit": Atividade(
        1000000001, "Intervalado 6x1km", *_RUN, _utc(2025, 3, 4, 9, 0, 0), VOLTAS_A,
        deslocamento_fit_s=30),
    "upload_esteira_4x1km.fit": Atividade(
        2000000003, "Esteira 4x1km", "treadmill_running", "RUNNING", Sport.RUNNING,
        SubSport.TREADMILL, _utc(2025, 4, 3, 18, 0, 0), VOLTAS_I),
    "upload_natacao_400m.fit": Atividade(
        2000000004, "Natacao 400m", "lap_swimming", "SWIMMING", Sport.SWIMMING,
        SubSport.LAP_SWIMMING, _utc(2025, 4, 4, 7, 0, 0), VOLTAS_J),
    # empate: duas candidatas a 40 s uma da outra e duas chegadas
    "empate_candidata_a.fit": Atividade(
        2000000011, "Candidata A", *_RUN, _INICIO_EMPATE, VOLTAS_H),
    "empate_candidata_b.fit": Atividade(
        2000000012, "Candidata B", *_RUN, _INICIO_EMPATE, VOLTAS_H, deslocamento_fit_s=40),
    "empate_chegada_equidistante.fit": Atividade(  # 20 s de cada candidata
        2000000013, "Chegada equidistante", *_RUN, _INICIO_EMPATE, VOLTAS_H, deslocamento_fit_s=20),
    "empate_chegada_mais_perto_de_b.fit": Atividade(  # 30 s de A, 10 s de B
        2000000014, "Chegada perto de B", *_RUN, _INICIO_EMPATE, VOLTAS_H, deslocamento_fit_s=30),
}
FRACAO_TRUNCADO = 0.6  # o FIT truncado guarda os primeiros 60% dos bytes de upload_intervalado_5x1km.fit

RAIZ_ZIP = "DI_CONNECT"
CAMINHO_JSON = f"{RAIZ_ZIP}/DI-Connect-Fitness/atleta-ficticio_0_summarizedActivities.json"
CAMINHO_UPLOADS = f"{RAIZ_ZIP}/DI-Connect-Uploaded-Files/UploadedFiles_0-_Part1.zip"
DATA_ZIP = (2025, 1, 1, 0, 0, 0)  # data fixa nos membros do zip (determinismo)


def _ms(dt: datetime) -> int:
    return int(dt.timestamp() * 1000)


def montar_fit(a: Atividade) -> bytes:
    inicio = _ms(a.inicio) + a.deslocamento_fit_s * 1000
    b = FitFileBuilder(auto_define=True, min_string_size=50)

    fid = FileIdMessage()
    fid.type = FileType.ACTIVITY
    fid.manufacturer = Manufacturer.GARMIN.value
    fid.product = 1
    fid.serial_number = a.id % 1_000_000  # ficticio
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
        lap.avg_heart_rate = fc
        lap.sport = a.sport_fit
        lap.sub_sport = a.sub_sport_fit
        lap.intensity = {AQUEC: Intensity.WARMUP, TIRO: Intensity.ACTIVE,
                         RECUP: Intensity.REST, DESAQ: Intensity.COOLDOWN}[intens]
        b.add(lap)
        t += int(dur * 1000)

    dist, dur, fc = a.totais()
    s = SessionMessage()
    s.message_index = 0
    s.start_time = inicio
    s.timestamp = t
    s.total_elapsed_time = dur
    s.total_timer_time = dur
    s.total_distance = dist
    s.avg_heart_rate = fc
    s.num_laps = len(a.voltas)
    s.sport = a.sport_fit
    s.sub_sport = a.sub_sport_fit
    b.add(s)
    return b.build().to_bytes()


def montar_json() -> bytes:
    itens = []
    for a in ATIVIDADES:
        dist, dur, fc = a.totais()
        local = {} if a.fuso_h is None else {"startTimeLocal": _ms(a.inicio) + a.fuso_h * 3_600_000}
        itens.append({
            "activityId": a.id,
            "name": a.nome,
            "activityType": a.activity_type,
            "sportType": a.sport_type,
            "startTimeGmt": _ms(a.inicio),
            **local,
            "beginTimestamp": _ms(a.inicio),
            "duration": dur * 1000,  # ms
            "elapsedDuration": dur * 1000,  # ms
            "distance": dist * 100,  # cm
            "avgHr": fc,
        })
    return json.dumps([{"summarizedActivitiesExport": itens}], indent=1).encode()


def _zip(membros: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for nome in sorted(membros):
            zi = zipfile.ZipInfo(nome, DATA_ZIP)
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.external_attr = 0o644 << 16
            z.writestr(zi, membros[nome])
    return buf.getvalue()


def montar_fits() -> dict[str, bytes]:
    return {f"atleta-ficticio_{a.id}.fit": montar_fit(a) for a in ATIVIDADES if a.voltas is not None}


def montar_exportacao() -> bytes:
    uploads = _zip(montar_fits())
    return _zip({CAMINHO_JSON: montar_json(), CAMINHO_UPLOADS: uploads})


def montar_fit_nao_atividade() -> bytes:
    """FIT valido cujo file_id.type e SETTINGS (nao e atividade)."""
    b = FitFileBuilder(auto_define=True, min_string_size=50)
    fid = FileIdMessage()
    fid.type = FileType.SETTINGS
    fid.manufacturer = Manufacturer.GARMIN.value
    fid.product = 1
    fid.serial_number = 2000000021 % 1_000_000
    fid.time_created = _ms(_utc(2025, 4, 5, 10, 0, 0))
    b.add(fid)
    return b.build().to_bytes()


def montar_fits_upload() -> dict[str, bytes]:
    """Todos os FIT avulsos do upload, por nome de arquivo (deterministico)."""
    fits = {nome: montar_fit(a) for nome, a in ATIVIDADES_UPLOAD.items()}
    inteiro = fits["upload_intervalado_5x1km.fit"]
    fits["upload_truncado.fit"] = inteiro[: int(len(inteiro) * FRACAO_TRUNCADO)]
    fits["upload_nao_atividade.fit"] = montar_fit_nao_atividade()
    return fits


def main(destino: Path) -> None:
    destino.mkdir(parents=True, exist_ok=True)
    (destino / "exportacao_minima.zip").write_bytes(montar_exportacao())
    print(f"gerado: {destino / 'exportacao_minima.zip'}")
    (destino / "fit").mkdir(exist_ok=True)
    for nome, conteudo in montar_fits_upload().items():
        (destino / "fit" / nome).write_bytes(conteudo)
    print(f"gerados: {len(montar_fits_upload())} FIT em {destino / 'fit'}")


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent)
