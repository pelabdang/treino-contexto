"""Agrupar treinos de transicao (issue #170; ADR 0009, item 4).

O grupo nao e guardado: sai dos rotulos finais (`transicao = true`, por linha `sugerido` ou `atleta`). Uma sequencia de
atividades rotuladas em que cada uma comeca ate `INTERVALO_MAX_S` depois do fim da anterior (mesmo limite da regra). O fim
e estimado por `inicio + duracao_s` (tempo em movimento), entao o intervalo entre partes e maior ou igual ao real.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Atividade, RotuloTransicao
from app.metricas.transicao import INTERVALO_MAX_S


@dataclass(frozen=True)
class Parte:
    atividade_id: int
    modalidade: str
    inicio: datetime  # UTC
    fuso_min: int | None
    duracao_s: float
    distancia_m: float | None
    fc_media: float | None

    @property
    def fim(self) -> datetime:
        return self.inicio + timedelta(seconds=max(self.duracao_s, 0))


@dataclass
class Grupo:
    partes: list[Parte] = field(default_factory=list)

    @property
    def grupo_id(self) -> int:
        """O `id` da primeira atividade. Derivado: muda quando uma correcao parte ou junta o grupo."""
        return self.partes[0].atividade_id

    @property
    def forma(self) -> str:
        return ">".join(p.modalidade for p in self.partes)

    @property
    def incompleto(self) -> bool:
        return len(self.partes) < 2

    @property
    def inicio(self) -> datetime:
        return self.partes[0].inicio

    @property
    def fim(self) -> datetime:
        return max(p.fim for p in self.partes)

    @property
    def intervalos_estimados_s(self) -> list[float]:
        """Entre cada duas partes: inicio da seguinte menos o maior fim ja visto, com minimo 0."""
        r, maior_fim = [], self.partes[0].fim
        for p in self.partes[1:]:
            r.append(max((p.inicio - maior_fim).total_seconds(), 0.0))
            maior_fim = max(maior_fim, p.fim)
        return r

    @property
    def soma_duracoes_s(self) -> float:
        return sum(p.duracao_s for p in self.partes)

    @property
    def soma_intervalos_estimados_s(self) -> float:
        return sum(self.intervalos_estimados_s)

    @property
    def tempo_total_s(self) -> float:
        """Do inicio da primeira parte ao fim estimado da ultima."""
        return (self.fim - self.inicio).total_seconds()

    @property
    def fc_media(self) -> float | None:
        """Media das partes ponderada pela duracao, so entre as que tem FC."""
        com_fc = [p for p in self.partes if p.fc_media is not None and p.duracao_s > 0]
        total = sum(p.duracao_s for p in com_fc)
        return None if total <= 0 else sum(p.fc_media * p.duracao_s for p in com_fc) / total


def ritmo(p: Parte) -> tuple[float, str] | None:
    """Ritmo da parte, como em docs/metricas/esforcos: corrida s/km, natacao s/100 m, ciclismo km/h. Vazio sem distancia."""
    if not p.distancia_m or p.distancia_m <= 0 or p.duracao_s <= 0:
        return None
    if p.modalidade == "corrida":
        return p.duracao_s / p.distancia_m * 1000, "s/km"
    if p.modalidade == "natacao":
        return p.duracao_s / p.distancia_m * 100, "s/100m"
    if p.modalidade == "ciclismo":
        return p.distancia_m / p.duracao_s * 3.6, "km/h"
    return None


def _utc(d: datetime) -> datetime:
    return d.replace(tzinfo=timezone.utc) if d.tzinfo is None else d.astimezone(timezone.utc)


def grupos_do_atleta(session: Session, atleta_id: int) -> list[Grupo]:
    """Todos os grupos do atleta, do mais antigo ao mais recente."""
    atividades = session.scalars(
        select(Atividade)
        .join(RotuloTransicao, RotuloTransicao.atividade_id == Atividade.id)
        .where(Atividade.atleta_id == atleta_id, RotuloTransicao.transicao.is_(True))
    ).all()
    partes = sorted(
        (
            Parte(a.id, a.modalidade, _utc(a.inicio), a.fuso_min, a.duracao_s, a.distancia_m, a.fc_media)
            for a in atividades
        ),
        key=lambda p: (p.inicio, p.atividade_id),
    )
    grupos: list[Grupo] = []
    for p in partes:
        if grupos and (p.inicio - grupos[-1].fim).total_seconds() <= INTERVALO_MAX_S:
            grupos[-1].partes.append(p)
        else:
            grupos.append(Grupo([p]))
    return grupos
