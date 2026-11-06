"""Gravacao de atividades no banco: exportacao Garmin (#13) e upload de FIT (#94, ADR 0006).

Os dois caminhos usam `gravar_atividade`, que aplica a identidade da atividade: a chave
`(atleta_id, fonte, fonte_id)` e, se nao existir, a regra dos 60 s (mesmo atleta, mesma modalidade, inicio a
ate 60 s; empate: inicio mais proximo, depois menor `id`, com aviso).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import timedelta
from pathlib import Path
from typing import Literal

from app.db.models import INTENSIDADES, Atividade, Atleta, Segmento
from app.ingestao import fit_guardado
from app.ingestao.fit_guardado import AtletaInexistente
from app.ingestao.garmin import AtividadeImportada, VoltaImportada, ler_atividade_fit, ler_exportacao
from app.ingestao.garmin.fit import FitSemAtividade
from app.ingestao.garmin.leitor import TOLERANCIA_S
from app.ingestao.garmin.posicao import e_indoor
from app.ingestao.garmin.unidades import para_utc
from app.servicos.evolucao_tiros import classificar_atividades
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

log = logging.getLogger(__name__)

FONTE_EXPORTACAO = "garmin_export"
FONTE_UPLOAD = "fit_upload"
TAMANHO_MAX_FIT = 10 * 1024 * 1024  # 10 MB (ADR 0006, item 4)

Resultado = Literal["inserida", "atualizada", "ignorada"]


class FitInvalido(ValueError):
    """FIT corrompido, truncado ou sem os dados minimos (inicio, duracao)."""


class FitNaoEAtividade(FitInvalido):
    """FIT valido, mas que nao e uma atividade (monitoramento, sono, configuracao...)."""


class FitGrande(ValueError):
    """Arquivo acima de `TAMANHO_MAX_FIT`."""


@dataclass
class RelatorioImportacao:
    inseridas: int = 0
    atualizadas: int = 0
    ignoradas: int = 0  # ja estavam iguais no banco
    avisos: list[str] = field(default_factory=list)
    ids_alterados: list[int] = field(default_factory=list)  # atividades que entraram ou mudaram (para o clima)


@dataclass
class ResultadoUpload:
    resultado: Resultado
    atividade_id: int
    avisos: list[str] = field(default_factory=list)


class _ColetaAvisos(logging.Handler):
    """Junta os avisos do parser no relatorio."""

    def __init__(self, destino: list[str]):
        super().__init__(logging.WARNING)
        self.destino = destino

    def emit(self, record: logging.LogRecord) -> None:
        self.destino.append(record.getMessage())


def normalizar_intensidade(valor: str | None) -> str | None:
    """Minusculas e sem espacos; valor fora da lista do CHECK vira "other"; ausente fica None."""
    if valor is None:
        return None
    v = str(valor).strip().lower()
    return v if v in INTENSIDADES else "other"


def pace_s_km(duracao_s: float, distancia_m: float | None) -> float | None:
    if not distancia_m or distancia_m <= 0:
        return None
    return duracao_s / distancia_m * 1000


def _chave_volta(ordem, offset, dur, dist, fc, intens) -> tuple:
    return (ordem, offset, dur, dist, fc, intens)


def _voltas_novas(voltas: list[VoltaImportada]) -> list[tuple]:
    return [_chave_volta(v.ordem, v.inicio_offset_s, v.duracao_s, v.distancia_m, v.fc_media,
                         normalizar_intensidade(v.intensidade)) for v in voltas]


def _voltas_no_banco(ativ: Atividade) -> list[tuple]:
    return [_chave_volta(s.ordem, s.inicio_offset_s, s.duracao_s, s.distancia_m, s.fc_media, s.intensidade)
            for s in ativ.segmentos]  # todos os tipos: a classificacao (#14) troca volta por tiro/recuperacao


def fuso_min(a: AtividadeImportada) -> int | None:
    """Deslocamento do fuso em minutos (inicio_local - inicio); None se a fonte nao traz o horario local."""
    if a.inicio_local is None or a.inicio_local.utcoffset() is None:
        return None
    return round(a.inicio_local.utcoffset().total_seconds() / 60)


def _campos(a: AtividadeImportada, duracao_s: float) -> dict:
    campos = dict(modalidade=a.modalidade, subtipo=a.subtipo, inicio=para_utc(a.inicio), duracao_s=duracao_s,
                  distancia_m=a.distancia_m, fc_media=a.fc_media, arquivo_bruto=a.arquivo_bruto)
    if e_indoor(a.subtipo):  # indoor nunca guarda posicao, mesmo que o arquivo traga coordenada (ADR 0007)
        campos.update(inicio_lat=None, inicio_lon=None)
    elif a.inicio_lat is not None:  # sem posicao na fonte nao apaga uma ja gravada (como o fuso)
        campos.update(inicio_lat=a.inicio_lat, inicio_lon=a.inicio_lon)
    fuso = fuso_min(a)
    if fuso is not None:  # sem horario local na fonte nao apaga um fuso ja gravado (ADR 0003)
        campos["fuso_min"] = fuso
    return campos


def _segmentos(voltas: list[VoltaImportada]) -> list[Segmento]:
    return [Segmento(ordem=v.ordem, tipo="volta", inicio_offset_s=v.inicio_offset_s, duracao_s=v.duracao_s,
                     distancia_m=v.distancia_m, fc_media=v.fc_media,
                     pace_s_km=pace_s_km(v.duracao_s, v.distancia_m),
                     intensidade=normalizar_intensidade(v.intensidade)) for v in voltas]


def _igual(ativ: Atividade, campos: dict) -> bool:
    return all(
        (para_utc(getattr(ativ, k)) == v) if k == "inicio" else getattr(ativ, k) == v
        for k, v in campos.items()
        if k != "arquivo_bruto"  # o caminho muda conforme o formato da entrada; nao conta como mudanca
    )


def tem_activity_id(fonte: str, fonte_id: str) -> bool:
    """A linha vem do JSON da exportacao (`fonte_id` = `activityId`). FIT avulso (`fit-...`) e upload nao tem."""
    return fonte == FONTE_EXPORTACAO and not fonte_id.startswith("fit-")


def duracao_da(a: AtividadeImportada) -> float | None:
    return a.duracao_s if a.duracao_s is not None else (sum(v.duracao_s for v in a.voltas) or None)


def _casar(session: Session, atleta_id: int, a: AtividadeImportada, avisos: list[str]) -> tuple[Atividade | None, bool]:
    """A atividade existente que `a` representa e se o casamento foi pela chave. Regra dos 60 s (ADR 0006, item 2)."""
    por_chave = session.scalars(select(Atividade).where(
        Atividade.atleta_id == atleta_id, Atividade.fonte == a.fonte, Atividade.fonte_id == a.fonte_id,
    )).first()
    if por_chave is not None:
        return por_chave, True
    inicio = para_utc(a.inicio)
    candidatas = list(session.scalars(select(Atividade).where(
        Atividade.atleta_id == atleta_id, Atividade.modalidade == a.modalidade,
        Atividade.inicio.between(inicio - timedelta(seconds=TOLERANCIA_S), inicio + timedelta(seconds=TOLERANCIA_S)),
    )))
    if tem_activity_id(a.fonte, a.fonte_id):
        # um activityId por atividade: se os DOIS lados tem activityId, e outra atividade, nunca a mesma (#133).
        # FIT avulso (`fit-...`) e upload nao tem activityId e entram na regra dos 60 s.
        candidatas = [c for c in candidatas if not tem_activity_id(c.fonte, c.fonte_id)]
    if not candidatas:
        return None, False
    candidatas.sort(key=lambda c: (abs((para_utc(c.inicio) - inicio).total_seconds()), c.id))
    if len(candidatas) > 1:
        ids = ", ".join(str(c.id) for c in sorted(candidatas, key=lambda c: c.id))
        avisos.append(f"atividade {a.fonte_id}: candidatas {ids}; usada a {candidatas[0].id} (inicio mais proximo, depois menor id)")
    return candidatas[0], False


def gravar_atividade(session: Session, atleta_id: int, a: AtividadeImportada, duracao_s: float,
                     avisos: list[str]) -> tuple[Resultado, Atividade, str | None]:
    """Insere ou atualiza a atividade (sem `commit`). Usada pela exportacao e pelo upload.

    - Casou (chave ou 60 s): atualiza a linha existente, o `id` nao muda. Nao casou: insere.
    - FIT avulso da exportacao (`fonte_id` `fit-...`) casa pela regra dos 60 s com qualquer linha; a exclusao
      "exportacao nao casa com exportacao" so vale quando os dois lados tem `activityId` (#133).
    - Linha com `activityId` que casa com linha sem `activityId` (upload ou FIT avulso): a linha adota o `activityId`.
    - Exportacao que casa com linha do upload: a linha passa a `garmin_export` com o `activityId`.
    - Upload que casa com linha da exportacao: a linha mantem fonte, `fonte_id` e os campos da exportacao
      (mais ricos, com horario local); o upload so completa as voltas se faltarem e troca o `arquivo_bruto`.
    - A exportacao nao troca um `arquivo_bruto` que ja aponta para um FIT de `FIT_DIR`.
    - Leitura sem voltas nunca apaga as voltas ja gravadas.

    Devolve (resultado, atividade, `arquivo_bruto` que a linha tinha antes), este para o upload apagar o FIT substituido.
    """
    campos = _campos(a, duracao_s)
    ativ, por_chave = _casar(session, atleta_id, a, avisos)
    if ativ is None:
        nova = Atividade(atleta_id=atleta_id, fonte=a.fonte, fonte_id=a.fonte_id,
                         segmentos=_segmentos(a.voltas), **campos)
        session.add(nova)
        session.flush()
        return "inserida", nova, None

    anterior = ativ.arquivo_bruto
    so_fit = a.fonte == FONTE_UPLOAD or not tem_activity_id(a.fonte, a.fonte_id)  # upload ou FIT avulso
    if not por_chave and so_fit and ativ.fonte == FONTE_EXPORTACAO and (
            a.fonte == FONTE_UPLOAD or tem_activity_id(ativ.fonte, ativ.fonte_id)):
        mudou = False
        if not ativ.segmentos and a.voltas:
            ativ.segmentos.extend(_segmentos(a.voltas))
            mudou = True
        if ativ.arquivo_bruto != a.arquivo_bruto and (a.fonte == FONTE_UPLOAD or not ativ.arquivo_bruto):
            ativ.arquivo_bruto = a.arquivo_bruto  # FIT avulso so preenche; nao troca a origem que a linha ja tem
            mudou = True
        if ativ.inicio_lat is None and a.inicio_lat is not None and not e_indoor(ativ.subtipo):
            ativ.inicio_lat, ativ.inicio_lon = a.inicio_lat, a.inicio_lon  # o JSON vale; sem posicao nele, a do FIT
            mudou = True
        return ("atualizada" if mudou else "ignorada"), ativ, anterior

    adotou = False
    if (not por_chave and a.fonte == FONTE_EXPORTACAO and not tem_activity_id(ativ.fonte, ativ.fonte_id)
            and (ativ.fonte != FONTE_EXPORTACAO or tem_activity_id(a.fonte, a.fonte_id))):
        ativ.fonte, ativ.fonte_id = a.fonte, a.fonte_id
        adotou = True
    if a.fonte != FONTE_UPLOAD and fit_guardado.esta_guardado(ativ.arquivo_bruto):
        campos.pop("arquivo_bruto")

    mudou_arquivo = a.fonte == FONTE_UPLOAD and ativ.arquivo_bruto != a.arquivo_bruto
    mudou_campos = not _igual(ativ, campos) or mudou_arquivo
    mudou_voltas = bool(a.voltas) and _voltas_novas(a.voltas) != _voltas_no_banco(ativ)
    if not a.voltas and ativ.segmentos:
        avisos.append(f"atividade {a.fonte_id} veio sem voltas; mantidas as {len(ativ.segmentos)} gravadas")
    if not (mudou_campos or mudou_voltas or adotou):
        return "ignorada", ativ, anterior
    if mudou_campos:
        for k, v in campos.items():
            setattr(ativ, k, v)
    if mudou_voltas:
        ativ.segmentos.clear()
        session.flush()  # remove os antigos antes de inserir (unique atividade_id + ordem)
        ativ.segmentos.extend(_segmentos(a.voltas))
    return "atualizada", ativ, anterior


def importar(session: Session, caminho: str | Path, atleta_nome: str) -> RelatorioImportacao:
    """Le a exportacao e grava atividades e voltas. Reimportar nao duplica nada.

    Atividade ja existente: se nada mudou, e ignorada (segmentos e classificacoes da #14 ficam intactos);
    se mudou, os campos sao atualizados e, se as voltas mudaram, os segmentos sao substituidos
    (o `id` da atividade nao muda). Uma atividade que ja veio por upload (mesmo atleta, modalidade e inicio a ate
    60 s) e atualizada, nao duplicada (ver `gravar_atividade`). No fim, classifica as corridas do atleta.
    Uma leitura sem voltas nunca apaga as voltas ja gravadas.
    """
    rel = RelatorioImportacao()
    coleta = _ColetaAvisos(rel.avisos)
    logger_parser = logging.getLogger("app.ingestao.garmin")
    logger_parser.addHandler(coleta)
    try:
        importadas = ler_exportacao(caminho)
    finally:
        logger_parser.removeHandler(coleta)

    atleta = session.scalars(select(Atleta).where(Atleta.nome == atleta_nome).order_by(Atleta.id)).first()
    if atleta is None:
        atleta = Atleta(nome=atleta_nome)
        session.add(atleta)
        session.flush()

    for a in importadas:
        duracao = duracao_da(a)
        if duracao is None:
            rel.avisos.append(f"atividade {a.fonte_id} sem duracao, ignorada")
            continue
        resultado, ativ, _ = gravar_atividade(session, atleta.id, a, duracao, rel.avisos)
        if resultado != "ignorada":
            rel.ids_alterados.append(ativ.id)
        if resultado == "inserida":
            rel.inseridas += 1
        elif resultado == "atualizada":
            rel.atualizadas += 1
        else:
            rel.ignoradas += 1

    session.commit()
    classificar_atividades(session, atleta.id)  # esforcos (#166), tiros/recuperacoes e tipo do treino (#14, #168); idempotente
    return rel


def importar_fit(session: Session, atleta_id: int, conteudo: bytes, fit_dir: Path | None = None) -> ResultadoUpload:
    """Importa um FIT enviado por upload (ADR 0006).

    Valida e le o FIT (invalido nunca chega ao disco nem ao banco), grava a atividade com a regra de identidade,
    guarda o arquivo em `FIT_DIR/<atleta_id>/<sha256>.fit` (temporario + renomeacao), faz o `commit`, apaga o FIT
    substituido se ficou orfao e classifica as corridas do atleta.

    Levanta `AtletaInexistente`, `FitGrande`, `FitNaoEAtividade` ou `FitInvalido`.
    """
    if session.get(Atleta, atleta_id) is None:
        raise AtletaInexistente(f"atleta {atleta_id} não encontrado")
    if len(conteudo) > TAMANHO_MAX_FIT:
        raise FitGrande(f"arquivo acima de {TAMANHO_MAX_FIT // (1024 * 1024)} MB")
    try:
        a = ler_atividade_fit(conteudo, fonte=FONTE_UPLOAD)
    except FitSemAtividade as e:
        raise FitNaoEAtividade("o arquivo é um FIT, mas não é uma atividade") from e
    except ValueError as e:
        raise FitInvalido("FIT inválido ou corrompido") from e
    duracao = duracao_da(a)
    if duracao is None:
        raise FitInvalido("FIT sem duração")

    relativo = fit_guardado.caminho_relativo(atleta_id, conteudo)
    a.arquivo_bruto = relativo
    avisos: list[str] = []
    for tentativa in (1, 2):
        criado = False
        try:
            resultado, ativ, anterior = gravar_atividade(session, atleta_id, a, duracao, avisos)
            antigo = anterior if fit_guardado.esta_guardado(anterior) and anterior != relativo else None
            if not fit_guardado.existe(relativo, fit_dir):
                criado = fit_guardado.gravar(relativo, conteudo, fit_dir)
                if resultado == "ignorada":  # o arquivo tinha sumido: regravar conta como atualizacao
                    resultado = "atualizada"
            session.commit()
            break
        except IntegrityError:  # dois envios iguais ao mesmo tempo: le de novo uma vez
            session.rollback()
            if criado:
                fit_guardado.remover(relativo, fit_dir)
            if tentativa == 2:
                raise
            avisos.clear()
        except BaseException:
            session.rollback()
            if criado:
                fit_guardado.remover(relativo, fit_dir)
            raise

    if antigo and not fit_guardado.ainda_referenciado(session, antigo):
        try:
            fit_guardado.remover(antigo, fit_dir)
        except OSError as e:
            avisos.append(f"não foi possível apagar o FIT substituído ({antigo}): {e.__class__.__name__}")
    atividade_id = ativ.id
    classificar_atividades(session, atleta_id)
    return ResultadoUpload(resultado, atividade_id, avisos)

