"""Modelo de dados mínimo (ADR 0001).

Só o necessário para a Meta 1: quem é o atleta, as atividades importadas e os
segmentos (voltas/tiros) de cada atividade. O resto do modelo do plano
(check-in, clima, métricas derivadas...) entra por novas migrações, com ADR.
"""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

MODALIDADES = ("corrida", "natacao", "ciclismo", "outra")
TIPOS_TREINO = ("leve", "moderado", "longo", "intervalado", "fartlek")
ORIGENS_TIPO = ("sugestao", "professor", "trainingpeaks")
TIPOS_SEGMENTO = ("volta", "tiro", "recuperacao")
# Valores do campo `intensity` do lap no FIT, normalizados em minúsculas (ADR 0002).
INTENSIDADES = ("active", "rest", "warmup", "cooldown", "recovery", "interval", "other")


def _in(col: str, values: tuple[str, ...]) -> str:
    opts = ", ".join(f"'{v}'" for v in values)
    return f"{col} IN ({opts})"


class Assessoria(Base):
    __tablename__ = "assessoria"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(200))
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Professor(Base):
    __tablename__ = "professor"

    id: Mapped[int] = mapped_column(primary_key=True)
    assessoria_id: Mapped[int] = mapped_column(ForeignKey("assessoria.id"))
    nome: Mapped[str] = mapped_column(String(200))
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Atleta(Base):
    __tablename__ = "atleta"

    id: Mapped[int] = mapped_column(primary_key=True)
    assessoria_id: Mapped[int | None] = mapped_column(ForeignKey("assessoria.id"))
    nome: Mapped[str] = mapped_column(String(200))
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    atividades: Mapped[list["Atividade"]] = relationship(back_populates="atleta")


class VinculoProfessorAtleta(Base):
    __tablename__ = "vinculo_professor_atleta"

    professor_id: Mapped[int] = mapped_column(ForeignKey("professor.id"), primary_key=True)
    atleta_id: Mapped[int] = mapped_column(ForeignKey("atleta.id"), primary_key=True)
    consentimento_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Atividade(Base):
    __tablename__ = "atividade"
    __table_args__ = (
        UniqueConstraint("atleta_id", "fonte", "fonte_id", name="uq_atividade_origem"),
        CheckConstraint(_in("modalidade", MODALIDADES), name="modalidade"),
        CheckConstraint(f"tipo_treino IS NULL OR {_in('tipo_treino', TIPOS_TREINO)}", name="tipo_treino"),
        CheckConstraint(f"tipo_origem IS NULL OR {_in('tipo_origem', ORIGENS_TIPO)}", name="tipo_origem"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    atleta_id: Mapped[int] = mapped_column(ForeignKey("atleta.id"), index=True)
    fonte: Mapped[str] = mapped_column(String(40))  # ex.: garmin_export, fit_upload
    fonte_id: Mapped[str] = mapped_column(String(100))  # id da atividade na fonte
    modalidade: Mapped[str] = mapped_column(String(20))
    subtipo: Mapped[str | None] = mapped_column(String(60))  # ex.: esteira, pista (como vem da fonte)
    inicio: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    duracao_s: Mapped[float] = mapped_column(Float)
    distancia_m: Mapped[float | None] = mapped_column(Float)
    fc_media: Mapped[float | None] = mapped_column(Float)
    tipo_treino: Mapped[str | None] = mapped_column(String(20))
    tipo_origem: Mapped[str | None] = mapped_column(String(20))
    tipo_confirmado: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    arquivo_bruto: Mapped[str | None] = mapped_column(String(500))  # caminho do FIT/JSON original
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    atleta: Mapped[Atleta] = relationship(back_populates="atividades")
    segmentos: Mapped[list["Segmento"]] = relationship(
        back_populates="atividade", cascade="all, delete-orphan", order_by="Segmento.ordem"
    )


class Segmento(Base):
    __tablename__ = "segmento"
    __table_args__ = (
        UniqueConstraint("atividade_id", "ordem", name="uq_segmento_ordem"),
        CheckConstraint(_in("tipo", TIPOS_SEGMENTO), name="tipo"),
        CheckConstraint(f"intensidade IS NULL OR {_in('intensidade', INTENSIDADES)}", name="intensidade"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    atividade_id: Mapped[int] = mapped_column(ForeignKey("atividade.id", ondelete="CASCADE"), index=True)
    ordem: Mapped[int] = mapped_column(Integer)
    tipo: Mapped[str] = mapped_column(String(20))
    inicio_offset_s: Mapped[float | None] = mapped_column(Float)
    duracao_s: Mapped[float] = mapped_column(Float)
    distancia_m: Mapped[float | None] = mapped_column(Float)
    fc_media: Mapped[float | None] = mapped_column(Float)
    pace_s_km: Mapped[float | None] = mapped_column(Float)
    zona: Mapped[str | None] = mapped_column(String(20))
    equipamento: Mapped[str | None] = mapped_column(String(40))
    intensidade: Mapped[str | None] = mapped_column(String(20))  # do FIT; ADR 0002
    versao_deteccao: Mapped[str | None] = mapped_column(String(40))  # ex.: tiros_1km@1; ADR 0002

    atividade: Mapped[Atividade] = relationship(back_populates="segmentos")
