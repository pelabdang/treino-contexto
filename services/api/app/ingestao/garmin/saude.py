"""Leitor dos dados de saude e metricas da exportacao Garmin (Meta 6, #136; ADR 0010).

Funcao pura: sem banco e sem rede. `ler_saude(caminho)` aceita a mesma entrada de `ler_exportacao` (zip, pasta
descompactada, ou zip dentro de zip) e devolve `SaudeGarmin`. Arquivo ausente, campo ausente ou valor invalido
dao lista vazia (ou item ignorado) e um aviso em `avisos` e no log, nunca excecao. Os avisos e o log nao trazem
nome de arquivo, id nem valor: so o tipo do dado e contagens.

Os arquivos sao achados por **pasta + sufixo do nome**, em qualquer profundidade; o identificador do usuario
nunca entra na busca. A arvore pode aparecer mais de uma vez (pasta, `DI_CONNECT/`, zip interno): cada conteudo
e lido uma vez (pelo hash do conteudo).

Velocidade de limiar: a exportacao traz m/s dividido por 10. Conta: valor 0,370 -> 0,370 x 10 = 3,70 m/s;
pace = 1000 / 3,70 = 270,27 s/km (ou 100 / 0,370). Ver `modelos_saude.velocidade_ms` e `pace_s_km`.
"""

from __future__ import annotations

import hashlib
import io
import json
import logging
import re
import zipfile
from collections.abc import Callable, Iterator
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from .leitor import PROFUNDIDADE_MAX_ZIP
from .modelos_saude import (
    GRANDEZA_FC,
    GRANDEZA_VELOCIDADE,
    ORIGEM_EXPORT,
    CargaGarminDia,
    LimiarRegistro,
    RecordePessoal,
    SaudeGarmin,
    ZonaFc,
    velocidade_ms,
)
from .zonas_fit import esporte_da_zona, ler_zonas_fit

log = logging.getLogger(__name__)

_PADROES = {
    "limiar": re.compile(r"(^|/)DI-Connect-Wellness/[^/]*_userBioMetrics\.json$", re.I),
    "zonas": re.compile(r"(^|/)DI-Connect-Wellness/[^/]*_heartRateZones\.json$", re.I),
    "recordes": re.compile(r"(^|/)DI-Connect-Fitness/[^/]*_personalRecord\.json$", re.I),
    "carga": re.compile(r"(^|/)DI-Connect-Metrics/MetricsAcuteTrainingLoad_\d{8}_\d{8}_[^/]*\.json$", re.I),
}
_ROTULOS = {
    "limiar": "limiar de lactato (userBioMetrics)",
    "zonas": "zonas de FC (heartRateZones)",
    "recordes": "recordes pessoais (personalRecord)",
    "carga": "carga aguda/cronica (MetricsAcuteTrainingLoad)",
}
FC_PLAUSIVEL_BPM = (30, 250)
VELOCIDADE_PLAUSIVEL_MS = (0.5, 10.0)  # depois de multiplicar por 10; fora disso a unidade da fonte nao confere


# --------------------------------------------------------------------------
# ACHAR OS ARQUIVOS
# --------------------------------------------------------------------------
def _tipo(nome: str) -> str | None:
    """Tipo do dado de saude pelo nome logico (`!/` separa zips aninhados), ou `fit`, ou `None`."""
    n = nome.replace("!/", "/")
    base = n.rsplit("/", 1)[-1]
    if "__macosx/" in n.lower() or base.startswith("._"):  # lixo do Finder
        return None
    if base.lower().endswith(".fit"):
        return "fit"
    return next((t for t, p in _PADROES.items() if p.search(n)), None)


def _percorrer(caminho: Path) -> Iterator[tuple[str, str, bytes]]:
    """Gera (tipo, nome logico, bytes) so dos arquivos que interessam; os outros nem sao lidos."""
    if caminho.is_dir():
        for f in sorted(p for p in caminho.rglob("*") if p.is_file()):
            yield from _visitar(f.relative_to(caminho).as_posix(), f.read_bytes, 0)
    elif caminho.is_file():
        yield from _visitar(caminho.name, caminho.read_bytes, 0)
    else:
        raise FileNotFoundError(f"Exportacao nao encontrada: {caminho}")


def _visitar(nome: str, ler: Callable[[], bytes], nivel: int) -> Iterator[tuple[str, str, bytes]]:
    base = nome.rsplit("/", 1)[-1]
    if "__macosx/" in nome.lower() or base.startswith("._"):
        return
    if nome.lower().endswith(".zip"):
        if nivel >= PROFUNDIDADE_MAX_ZIP:
            log.warning("zip aninhado fundo demais, ignorado")
            return
        try:
            with zipfile.ZipFile(io.BytesIO(ler())) as z:
                for membro in sorted(z.namelist()):
                    if not membro.endswith("/"):
                        yield from _visitar(f"{nome}!/{membro}", lambda m=membro: z.read(m), nivel + 1)
        except zipfile.BadZipFile:
            log.warning("zip corrompido, ignorado")
        return
    tipo = _tipo(nome)
    if tipo:
        yield tipo, nome, ler()


# --------------------------------------------------------------------------
# LEITURA DE CADA DADO
# --------------------------------------------------------------------------
class _Avisos:
    def __init__(self) -> None:
        self.lista: list[str] = []

    def __call__(self, msg: str) -> None:
        if msg not in self.lista:
            self.lista.append(msg)
            log.warning("saude Garmin: %s", msg)


def _json_lista(dados: bytes) -> list | None:
    try:
        obj = json.loads(dados)
    except ValueError:
        return None
    return obj if isinstance(obj, list) else None


def _num(v) -> float | None:
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def _inteiro(v) -> int | None:
    n = _num(v)
    return int(n) if n is not None and n == int(n) else None


def _data_hora(texto) -> datetime | None:
    """`AAAA-MM-DDTHH:MM:SS` seguido (ou nao) de fracao; sem fuso."""
    try:
        return datetime.fromisoformat(str(texto)[:19])
    except ValueError:
        return None


def ler_limiares(registros: list, aviso: Callable[[str], None] = lambda m: None) -> list[LimiarRegistro]:
    """Historico de limiar (`userBioMetrics`) para uma serie por grandeza, com vigencia em dia.

    Cada registro traz so o que mudou. Ordena por `metaData.calendarDate` (empate: `sequence`) e, por dia e por
    campo, fica o ultimo valor. FC `0` e sentinela de sem limiar: nao vira registro (e nao cancela um limiar
    anterior). Velocidade = valor x 10 em m/s. Um valor igual ao vigente da mesma grandeza nao abre vigencia nova.
    Valor fora do plausivel (FC 30 a 250 bpm; velocidade 0,5 a 10 m/s) ou data invalida: ignorado, com aviso.
    """
    itens = []
    for r in registros:
        meta = r.get("metaData") if isinstance(r, dict) else None
        quando = _data_hora(meta.get("calendarDate")) if isinstance(meta, dict) else None
        if quando is None:
            if isinstance(r, dict) and (r.get("lactateThresholdHearRate") or r.get("lactateThresholdSpeed")):
                aviso("registro de limiar sem data valida ignorado")
            continue
        itens.append((quando, _inteiro(meta.get("sequence")) or 0, r))
    itens.sort(key=lambda t: (t[0], t[1]))

    por_dia: dict[tuple[str, date], float] = {}  # o ultimo valor de cada campo no dia
    for quando, _, r in itens:
        fc = r.get("lactateThresholdHearRate")
        if fc is not None and _num(fc) != 0:  # 0 = sem limiar: nao vira registro
            n = _num(fc)
            if n is not None and FC_PLAUSIVEL_BPM[0] <= n <= FC_PLAUSIVEL_BPM[1]:
                por_dia[(GRANDEZA_FC, quando.date())] = n
            else:
                aviso("FC de limiar invalida ignorada")
        vel = r.get("lactateThresholdSpeed")
        if vel is not None and _num(vel) != 0:
            n = _num(vel)
            ms = velocidade_ms(n) if n is not None else None
            if ms is not None and VELOCIDADE_PLAUSIVEL_MS[0] <= ms <= VELOCIDADE_PLAUSIVEL_MS[1]:
                por_dia[(GRANDEZA_VELOCIDADE, quando.date())] = ms
            else:
                aviso("velocidade de limiar invalida ignorada")

    resultado: list[LimiarRegistro] = []
    for grandeza in (GRANDEZA_FC, GRANDEZA_VELOCIDADE):
        vigente = None
        for (g, dia), valor in sorted(por_dia.items(), key=lambda kv: kv[0][1]):
            if g == grandeza and valor != vigente:
                resultado.append(LimiarRegistro(grandeza, dia, valor))
                vigente = valor
    return resultado


_ESPORTE_ZONA = {"DEFAULT": "padrao", "RUNNING": "corrida", "CYCLING": "ciclismo"}


def ler_zonas_json(entradas: list, dia_retrato: date | None = None,
                   aviso: Callable[[str], None] = lambda m: None) -> list[ZonaFc]:
    """Retrato das zonas (`heartRateZones`, origem `garmin_export`): uma `ZonaFc` por esporte.

    `dia_retrato` (o dia da importacao) vira `vigente_desde`; o arquivo nao tem data. Entrada sem os 5 pisos ou
    sem FC maxima e ignorada com aviso. O teto da zona 5 e a FC maxima usada.
    """
    zonas = []
    for e in entradas:
        if not isinstance(e, dict):
            continue
        pisos = [_inteiro(e.get(f"zone{i}Floor")) for i in range(1, 6)]
        fc_max = _inteiro(e.get("maxHeartRateUsed"))
        if any(p is None for p in pisos) or fc_max is None:
            aviso("zonas de FC incompletas ignoradas")
            continue
        sport = str(e.get("sport") or "")
        metodo = e.get("trainingMethod")
        zonas.append(ZonaFc(
            esporte=_ESPORTE_ZONA.get(sport.upper(), sport.lower() or "padrao"), origem=ORIGEM_EXPORT,
            vigente_desde=dia_retrato, metodo=str(metodo) if metodo is not None else None, fc_max_bpm=fc_max,
            fc_repouso_bpm=_inteiro(e.get("restingHeartRateUsed")),
            zona1_min_bpm=pisos[0], zona2_min_bpm=pisos[1], zona3_min_bpm=pisos[2], zona4_min_bpm=pisos[3],
            zona5_min_bpm=pisos[4], zona5_max_bpm=fc_max,
        ))
    return zonas


def historico_zonas_fit(lidas: list[tuple[datetime, ZonaFc]]) -> list[ZonaFc]:
    """Uma linha por mudanca de zonas, por esporte, na ordem das sessoes (origem `garmin_fit`).

    No mesmo dia local vale a ultima sessao (a chave da tabela e esporte, origem e dia).
    """
    ultimo_do_dia: dict[tuple[str, date], ZonaFc] = {}
    for _, z in sorted(lidas, key=lambda t: t[0]):
        ultimo_do_dia[(z.esporte, z.vigente_desde)] = z
    vistas: dict[str, tuple] = {}
    resultado = []
    for (esporte, _), z in sorted(ultimo_do_dia.items(), key=lambda kv: (kv[0][1], kv[0][0])):
        if vistas.get(esporte) != z.conteudo():
            resultado.append(z)
            vistas[esporte] = z.conteudo()
    return resultado


_MESES = {m: i for i, m in enumerate("Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split(), 1)}
_JAVA_DATA = re.compile(r"^[A-Za-z]{3} ([A-Za-z]{3}) (\d{2}) (\d{2}):(\d{2}):(\d{2}) GMT (\d{4})$")


def _data_java(texto) -> datetime | None:
    """`Dia Mes DD HH:MM:SS GMT AAAA` (nomes em ingles, UTC), sem depender do locale."""
    m = _JAVA_DATA.match(str(texto).strip())
    if not m or m.group(1) not in _MESES:
        return None
    try:
        return datetime(int(m.group(6)), _MESES[m.group(1)], int(m.group(2)), int(m.group(3)), int(m.group(4)),
                        int(m.group(5)), tzinfo=timezone.utc)
    except ValueError:
        return None


def _modalidade_unidade(tipo: str) -> tuple[str, str | None]:
    t = tipo.lower()
    modalidade = ("natacao" if "swim" in t else "corrida" if "run" in t
                  else "ciclismo" if ("ride" in t or "cycl" in t or "bike" in t or "power" in t) else "outra")
    unidade = ("s" if t.startswith("best ") else "m" if t.startswith(("farthest", "longest")) else
               "W" if "power" in t else "passos" if "steps" in t else None)
    return modalidade, unidade


def ler_recordes(blocos: list, aviso: Callable[[str], None] = lambda m: None) -> list[RecordePessoal]:
    """Recordes pessoais (`personalRecord`): `activityId` 0 vira id nulo; sem `prStartTimeGMT` valido, ignorado."""
    itens = []
    for b in blocos:
        if isinstance(b, dict) and isinstance(b.get("personalRecords"), list):
            itens.extend(b["personalRecords"])
    vistos: set[tuple] = set()
    resultado = []
    ignorados = 0
    for r in itens:
        if not isinstance(r, dict):
            continue
        tipo, valor = r.get("personalRecordType"), _num(r.get("value"))
        quando = _data_java(r.get("prStartTimeGMT"))
        if not isinstance(tipo, str) or not tipo or valor is None or quando is None:
            ignorados += 1
            continue
        modalidade, unidade = _modalidade_unidade(tipo)
        chave = (modalidade, tipo, quando)
        if chave in vistos:
            continue
        vistos.add(chave)
        ativ = _inteiro(r.get("activityId"))
        resultado.append(RecordePessoal(
            modalidade=modalidade, categoria=tipo, valor=valor, unidade=unidade, alcancado_em=quando,
            atividade_fonte_id=str(ativ) if ativ else None, atual=r.get("current") is True,
        ))
    if ignorados:
        aviso(f"{ignorados} recorde(s) pessoal(is) invalido(s) ignorado(s)")
    return sorted(resultado, key=lambda x: (x.alcancado_em, x.categoria))


def ler_carga_dia(itens: list, aviso: Callable[[str], None] = lambda m: None) -> list[CargaGarminDia]:
    """Carga aguda/cronica por dia: de varios itens do mesmo `calendarDate` vale o de maior `timestamp`.

    `calendarDate` e ms desde 1970 (meia-noite UTC), nao `AAAAMMDD`. A razao pode faltar (fica `None`).
    """
    melhor: dict[date, tuple[float, dict]] = {}
    ignorados = 0
    for i in itens:
        if not isinstance(i, dict):
            continue
        ms = _num(i.get("calendarDate"))
        try:
            dia = (datetime(1970, 1, 1, tzinfo=timezone.utc) + timedelta(milliseconds=ms)).date()
        except (TypeError, OverflowError, ValueError):
            ignorados += 1
            continue
        ts = _num(i.get("timestamp"))
        ts = ts if ts is not None else float("-inf")
        if dia not in melhor or ts >= melhor[dia][0]:
            melhor[dia] = (ts, i)
    if ignorados:
        aviso(f"{ignorados} item(ns) de carga sem data valida ignorado(s)")
    return [CargaGarminDia(dia=d, carga_aguda=_num(i.get("dailyTrainingLoadAcute")),
                           carga_cronica=_num(i.get("dailyTrainingLoadChronic")),
                           razao=_num(i.get("dailyAcuteChronicWorkloadRatio")))
            for d, (_, i) in sorted(melhor.items())]


# --------------------------------------------------------------------------
# ENTRADA
# --------------------------------------------------------------------------
def ler_saude(caminho: str | Path, dia_retrato: date | None = None) -> SaudeGarmin:
    """Le os dados de saude e metricas da exportacao Garmin (zip, pasta ou zip dentro de zip). Sem banco.

    `dia_retrato`: dia que `vigente_desde` recebe nas zonas do JSON (o arquivo e so um retrato, sem data).
    Levanta `FileNotFoundError` so se o proprio caminho nao existe.
    """
    aviso = _Avisos()
    achados: dict[str, list[list]] = {t: [] for t in _PADROES}
    zonas_fit: list[tuple[datetime, ZonaFc]] = []
    vistos: set[bytes] = set()
    for tipo, _, dados in _percorrer(Path(caminho)):
        digest = hashlib.sha1(dados).digest()
        if digest in vistos:  # a mesma arvore em outra copia
            continue
        vistos.add(digest)
        if tipo == "fit":
            lida = ler_zonas_fit(dados)
            if lida:
                zonas_fit.append(lida)
            continue
        lista = _json_lista(dados)
        if lista is None:
            aviso(f"arquivo de {_ROTULOS[tipo]} ilegivel ignorado")
        else:
            achados[tipo].append(lista)

    saude = SaudeGarmin()
    for tipo in _PADROES:
        if not achados[tipo]:
            aviso(f"sem arquivo de {_ROTULOS[tipo]} na exportacao")
    todos = {t: [x for lista in v for x in lista] for t, v in achados.items()}
    saude.limiares = ler_limiares(todos["limiar"], aviso)
    if achados["limiar"] and not saude.limiares:
        aviso("arquivo de limiar sem nenhum limiar valido (atleta sem limiar)")
    saude.zonas = ler_zonas_json(todos["zonas"], dia_retrato, aviso) + historico_zonas_fit(zonas_fit)
    if not zonas_fit:
        aviso("nenhum FIT com zonas de FC: sem historico de zonas")
    saude.recordes = ler_recordes(todos["recordes"], aviso)
    saude.carga_dia = ler_carga_dia(todos["carga"], aviso)
    saude.avisos = aviso.lista
    return saude


__all__ = ["ler_saude", "ler_limiares", "ler_zonas_json", "historico_zonas_fit", "ler_recordes", "ler_carga_dia",
           "esporte_da_zona"]
