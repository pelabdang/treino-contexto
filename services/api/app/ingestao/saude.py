"""Gravacao dos dados de saude da exportacao Garmin: limiar e zonas de FC (Meta 6, #140; ADR 0010, itens 1 a 3).

`importar_saude` usa o leitor puro (`garmin.saude.ler_saude`) e grava em `limiar_atleta` e `zona_fc_atleta`. Sem rede.
Idempotente pela chave de cada tabela; uma mudanca nova entra como nova vigencia, sem apagar o historico; uma reimportacao
mais curta nunca apaga linhas. Recordes e carga do Garmin ficam na #174.

So devolve contagens e avisos do leitor (sem valor fisiologico): nada aqui escreve valor em log.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from app.db.models import Atleta, LimiarAtleta, ZonaFcAtleta
from app.ingestao.garmin.modelos_saude import (
    ORIGEM_EXPORT,
    VERSAO_LEITURA,
    LimiarRegistro,
    ZonaFc,
)
from app.ingestao.garmin.saude import ler_saude
from sqlalchemy import select
from sqlalchemy.orm import Session


@dataclass
class Contagem:
    inseridas: int = 0
    atualizadas: int = 0  # mesma chave, valor diferente (correcao da fonte); unico caso de sobrescrita
    ignoradas: int = 0  # ja estavam iguais no banco


@dataclass
class RelatorioSaude:
    limiar: Contagem = field(default_factory=Contagem)
    zonas: Contagem = field(default_factory=Contagem)
    avisos: list[str] = field(default_factory=list)

    @property
    def gravou_algo(self) -> bool:
        return any(c.inseridas or c.atualizadas for c in (self.limiar, self.zonas))


_CAMPOS_ZONA = ("metodo", "fc_max_bpm", "fc_repouso_bpm", "zona1_min_bpm", "zona2_min_bpm", "zona3_min_bpm",
                "zona4_min_bpm", "zona5_min_bpm", "zona5_max_bpm")


def _conteudo_zona(z: ZonaFc | ZonaFcAtleta) -> tuple:
    return tuple(getattr(z, c) for c in _CAMPOS_ZONA)


def _gravar_limiar(session: Session, atleta_id: int, r: LimiarRegistro, cont: Contagem, avisos: list[str]) -> None:
    atual = session.scalars(select(LimiarAtleta).where(
        LimiarAtleta.atleta_id == atleta_id, LimiarAtleta.grandeza == r.grandeza,
        LimiarAtleta.origem == r.origem, LimiarAtleta.vigente_desde == r.vigente_desde)).first()
    if atual is None:
        session.add(LimiarAtleta(atleta_id=atleta_id, grandeza=r.grandeza, valor=r.valor,
                                 vigente_desde=r.vigente_desde, origem=r.origem, versao_leitura=VERSAO_LEITURA))
        cont.inseridas += 1
    elif atual.valor != r.valor:
        atual.valor, atual.versao_leitura = r.valor, VERSAO_LEITURA
        cont.atualizadas += 1
        avisos.append(f"limiar ({r.grandeza}) de {r.vigente_desde.isoformat()} corrigido pela fonte")
    else:
        cont.ignoradas += 1


def _gravar_zona(session: Session, atleta_id: int, z: ZonaFc, cont: Contagem, avisos: list[str]) -> None:
    if z.origem == ORIGEM_EXPORT:
        # Retrato sem data: so abre vigencia nova se as zonas diferem das vigentes (reimportar em outro dia o mesmo
        # retrato nao duplica).
        anterior = session.scalars(select(ZonaFcAtleta).where(
            ZonaFcAtleta.atleta_id == atleta_id, ZonaFcAtleta.esporte == z.esporte,
            ZonaFcAtleta.origem == z.origem, ZonaFcAtleta.vigente_desde <= z.vigente_desde)
            .order_by(ZonaFcAtleta.vigente_desde.desc())).first()
        if anterior is not None and _conteudo_zona(anterior) == _conteudo_zona(z):
            cont.ignoradas += 1
            return
    atual = session.scalars(select(ZonaFcAtleta).where(
        ZonaFcAtleta.atleta_id == atleta_id, ZonaFcAtleta.esporte == z.esporte,
        ZonaFcAtleta.origem == z.origem, ZonaFcAtleta.vigente_desde == z.vigente_desde)).first()
    campos = dict(zip(_CAMPOS_ZONA, _conteudo_zona(z)))
    if atual is None:
        session.add(ZonaFcAtleta(atleta_id=atleta_id, esporte=z.esporte, origem=z.origem,
                                 vigente_desde=z.vigente_desde, versao_leitura=VERSAO_LEITURA, **campos))
        cont.inseridas += 1
    elif _conteudo_zona(atual) != _conteudo_zona(z):
        for k, v in campos.items():
            setattr(atual, k, v)
        atual.versao_leitura = VERSAO_LEITURA
        cont.atualizadas += 1
        avisos.append(f"zonas de FC ({z.esporte}) de {z.vigente_desde.isoformat()} corrigidas pela fonte")
    else:
        cont.ignoradas += 1


def importar_saude(session: Session, caminho: str | Path, atleta_nome: str,
                   dia_retrato: date | None = None) -> RelatorioSaude:
    """Le a exportacao e grava limiar e zonas de FC do atleta. Reimportar nao duplica nada.

    `dia_retrato` (padrao: hoje) e o `vigente_desde` das zonas do JSON, que e so um retrato sem data. Exportacao sem
    dados de saude: nada e gravado (nem o atleta e criado) e os motivos vem em `avisos`. Faz `commit` ao fim.
    Levanta `FileNotFoundError` se o caminho nao existe.
    """
    dia = dia_retrato or date.today()
    saude = ler_saude(caminho, dia_retrato=dia)
    rel = RelatorioSaude(avisos=list(saude.avisos))
    if not saude.limiares and not saude.zonas:
        return rel

    atleta = session.scalars(select(Atleta).where(Atleta.nome == atleta_nome).order_by(Atleta.id)).first()
    if atleta is None:
        atleta = Atleta(nome=atleta_nome)
        session.add(atleta)
        session.flush()

    for r in saude.limiares:
        _gravar_limiar(session, atleta.id, r, rel.limiar, rel.avisos)
    session.flush()
    for z in saude.zonas:
        if z.vigente_desde is not None:
            _gravar_zona(session, atleta.id, z, rel.zonas, rel.avisos)
            session.flush()
    session.commit()
    return rel


def limiar_vigente(session: Session, atleta_id: int, grandeza: str, dia: date) -> LimiarAtleta | None:
    """Limiar de `grandeza` vigente no `dia` (ADR 0010, item 1): maior `vigente_desde <= dia`; no mesmo dia `informado`
    vence `garmin_export`. Antes da primeira linha: `None` (nunca olha para a linha seguinte)."""
    return session.scalars(select(LimiarAtleta).where(
        LimiarAtleta.atleta_id == atleta_id, LimiarAtleta.grandeza == grandeza, LimiarAtleta.vigente_desde <= dia)
        .order_by(LimiarAtleta.vigente_desde.desc(), (LimiarAtleta.origem == "informado").desc())).first()


def zonas_vigentes(session: Session, atleta_id: int, esporte: str, dia: date,
                   origem: str | None = None) -> ZonaFcAtleta | None:
    """Zonas de FC do `esporte` vigentes no `dia` (maior `vigente_desde <= dia`), de uma `origem` ou de qualquer uma
    (empate no mesmo dia: a `garmin_fit`, que e a da sessao). Sem linha anterior: `None`."""
    consulta = select(ZonaFcAtleta).where(
        ZonaFcAtleta.atleta_id == atleta_id, ZonaFcAtleta.esporte == esporte, ZonaFcAtleta.vigente_desde <= dia)
    if origem is not None:
        consulta = consulta.where(ZonaFcAtleta.origem == origem)
    return session.scalars(consulta.order_by(ZonaFcAtleta.vigente_desde.desc(), ZonaFcAtleta.origem.desc())).first()
