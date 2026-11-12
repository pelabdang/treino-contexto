"""Modelo de dados mínimo (ADR 0001).

Só o necessário para a Meta 1: quem é o atleta, as atividades importadas e os
segmentos (voltas/tiros) de cada atividade. O resto do modelo do plano
(check-in, clima, métricas derivadas...) entra por novas migrações, com ADR.
"""

from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
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
ORIGENS_TIPO = ("sugestao", "professor", "trainingpeaks", "semana_padrao")  # semana_padrao: ADR 0011, item 1
DIVERGENCIAS_TIPO = ("sem_esforco", "tem_tiros")  # ADR 0011, item 4
DEFINIDO_POR = ("atleta", "professor")  # declarado, nao verificado (ADR 0011, item 1)
MODALIDADES_SEMANA = ("corrida", "natacao", "ciclismo")  # `outra` fica de fora da semana-padrao
TIPOS_SEGMENTO = ("volta", "tiro", "recuperacao")
CATEGORIAS_BLOCO = ("esforco", "recuperacao", "aquecimento", "desaquecimento", "leve")  # ADR 0008, item 1
# Valores do campo `intensity` do lap no FIT, normalizados em minúsculas (ADR 0002).
INTENSIDADES = ("active", "rest", "warmup", "cooldown", "recovery", "interval", "other")


ORIGENS_ROTULO = ("sugerido", "atleta")  # ADR 0009, item 1

GRANDEZAS_LIMIAR = ("fc_bpm", "velocidade_ms")  # ADR 0010, item 1
ORIGENS_LIMIAR = ("garmin_export", "informado")
ORIGENS_ZONA = ("garmin_export", "garmin_fit")
ORIGENS_RECUPERACAO = ("garmin_connect",)  # ADR 0014, item 1; a exportacao nao e fonte da recuperacao
ORIGENS_SAUDE = ("garmin_export",)  # recorde_pessoal e carga_garmin_dia (ADR 0010, item 2)
UNIDADES_RECORDE = ("s", "m", "W", "passos")  # ou nulo: tipo desconhecido (adendo da ADR 0010)

ESTADOS_CARGA = ("calculada", "sem_carga")  # ADR 0010, item 5
METODOS_CARGA = ("rtss", "hrtss")
GRANULARIDADES_CARGA = ("volta", "atividade")
MOTIVOS_CARGA = (
    "sem_dados_saude", "sem_limiar_na_data", "sem_fc", "sem_pace", "cobertura_insuficiente", "modalidade_sem_carga",
)

ESTADOS_CLIMA = ("ok", "pendente", "falha")  # indoor e sem_posicao sao calculados na leitura (ADR 0007)

CHECKIN_ATALHOS = ("dor", "cansaco", "sono_ruim", "calor", "trabalho_estresse")  # ADR 0012, item 2
CHECKIN_VERSAO = "checkin@1"  # versao do formulario (escala CR-10 inteira, sensacao 1 a 5, os 5 atalhos)
CHECKIN_TEXTO_MAX = 500
FEEDBACK_TEXTO_MAX = 700  # ADR 0013, item 2
FEEDBACK_ESTADOS = ("pronto", "sem_feedback")
FEEDBACK_MOTIVOS = ("texto_reprovado", "provedor_erro", "provedor_tempo_limite", "provedor_nao_configurado",
                    "limite_de_chamadas")

FUSO_MIN_MIN, FUSO_MIN_MAX = -720, 840  # minutos: UTC-12 a UTC+14


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
        # ADR 0011, item 1: a divergencia so existe com a origem `semana_padrao`.
        CheckConstraint(f"tipo_divergencia IS NULL OR {_in('tipo_divergencia', DIVERGENCIAS_TIPO)}", name="tipo_divergencia"),
        # `IS NOT NULL` explicito: com origem nula, `tipo_origem = 'semana_padrao'` e NULL e o CHECK deixaria passar.
        CheckConstraint(
            "tipo_divergencia IS NULL OR (tipo_origem IS NOT NULL AND tipo_origem = 'semana_padrao')",
            name="tipo_divergencia_origem",
        ),
        # Fusos reais vao de UTC-12 a UTC+14 (ADR 0003).
        CheckConstraint(f"fuso_min IS NULL OR fuso_min BETWEEN {FUSO_MIN_MIN} AND {FUSO_MIN_MAX}", name="fuso_min"),
        # Posicao de inicio arredondada (ADR 0007): faixa valida e as duas nulas ou as duas preenchidas.
        CheckConstraint("inicio_lat IS NULL OR inicio_lat BETWEEN -90 AND 90", name="inicio_lat"),
        CheckConstraint("inicio_lon IS NULL OR inicio_lon BETWEEN -180 AND 180", name="inicio_lon"),
        CheckConstraint("(inicio_lat IS NULL) = (inicio_lon IS NULL)", name="inicio_par"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    atleta_id: Mapped[int] = mapped_column(ForeignKey("atleta.id"), index=True)
    fonte: Mapped[str] = mapped_column(String(40))  # ex.: garmin_export, fit_upload
    fonte_id: Mapped[str] = mapped_column(String(100))  # id da atividade na fonte
    modalidade: Mapped[str] = mapped_column(String(20))
    subtipo: Mapped[str | None] = mapped_column(String(60))  # ex.: esteira, pista (como vem da fonte)
    inicio: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    # deslocamento do fuso em minutos (startTimeLocal - startTimeGmt); NULL se desconhecido; ADR 0003
    fuso_min: Mapped[int | None] = mapped_column(Integer)
    duracao_s: Mapped[float] = mapped_column(Float)
    distancia_m: Mapped[float | None] = mapped_column(Float)
    fc_media: Mapped[float | None] = mapped_column(Float)
    # posicao de inicio em graus, arredondada a 2 casas (~1 km) no leitor; NULL se indoor/sem GPS; nunca sai pela API
    inicio_lat: Mapped[float | None] = mapped_column(Float)
    inicio_lon: Mapped[float | None] = mapped_column(Float)
    tipo_treino: Mapped[str | None] = mapped_column(String(20))
    tipo_origem: Mapped[str | None] = mapped_column(String(20))
    tipo_confirmado: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    # versao da regra que escreveu o tipo (ex.: tipo_treino@1) quando a origem e `sugestao` ou `semana_padrao`; ADR 0011
    tipo_versao: Mapped[str | None] = mapped_column(String(40))
    tipo_divergencia: Mapped[str | None] = mapped_column(String(20))  # sem_esforco ou tem_tiros (ADR 0011, item 4)
    arquivo_bruto: Mapped[str | None] = mapped_column(String(500))  # caminho do FIT/JSON original
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    atleta: Mapped[Atleta] = relationship(back_populates="atividades")
    segmentos: Mapped[list["Segmento"]] = relationship(
        back_populates="atividade", cascade="all, delete-orphan", order_by="Segmento.ordem"
    )
    blocos: Mapped[list["BlocoAtividade"]] = relationship(
        back_populates="atividade", cascade="all, delete-orphan", order_by="BlocoAtividade.ordem"
    )
    rotulo_transicao: Mapped["RotuloTransicao | None"] = relationship(
        back_populates="atividade", cascade="all, delete-orphan", uselist=False
    )
    carga: Mapped["CargaAtividade | None"] = relationship(
        back_populates="atividade", cascade="all, delete-orphan", uselist=False
    )
    checkin: Mapped["CheckinTreino | None"] = relationship(
        back_populates="atividade", cascade="all, delete-orphan", uselist=False
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


class BlocoAtividade(Base):
    """Um bloco de uma atividade: voltas contiguas juntadas e classificadas (ADR 0008, item 9).

    Uma linha por bloco, de todas as categorias. So guarda o que a regra produz; a modalidade vem da atividade.
    Quem grava e `app.servicos.esforcos.detectar_esforcos`, que apaga e recria os blocos da atividade.
    """

    __tablename__ = "bloco_atividade"
    __table_args__ = (
        UniqueConstraint("atividade_id", "ordem", name="uq_bloco_atividade_ordem"),
        CheckConstraint(_in("categoria", CATEGORIAS_BLOCO), name="categoria"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    atividade_id: Mapped[int] = mapped_column(ForeignKey("atividade.id", ondelete="CASCADE"), index=True)
    ordem: Mapped[int] = mapped_column(Integer)
    categoria: Mapped[str] = mapped_column(String(20))
    volta_inicial: Mapped[int] = mapped_column(Integer)  # segmento.ordem da primeira volta
    volta_final: Mapped[int] = mapped_column(Integer)  # segmento.ordem da ultima volta
    inicio_offset_s: Mapped[float] = mapped_column(Float)
    duracao_s: Mapped[float] = mapped_column(Float)  # tempo em movimento
    parada_apos_s: Mapped[float | None] = mapped_column(Float)  # parado entre este bloco e o seguinte
    distancia_m: Mapped[float | None] = mapped_column(Float)
    fc_media: Mapped[float | None] = mapped_column(Float)  # ponderada pela duracao
    pace_s_km: Mapped[float | None] = mapped_column(Float)
    faixa: Mapped[str | None] = mapped_column(String(10))  # d400, t4...; NULL fora de qualquer faixa
    treino_chave: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    versao_deteccao: Mapped[str] = mapped_column(String(40))  # ex.: esforcos@1

    atividade: Mapped[Atividade] = relationship(back_populates="blocos")


class ClimaAtividade(Base):
    """Clima de uma atividade que foi consultada (ADR 0007, item 3). Sem linha para indoor nem sem posicao."""

    __tablename__ = "clima_atividade"
    __table_args__ = (CheckConstraint(_in("estado", ESTADOS_CLIMA), name="estado"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    atividade_id: Mapped[int] = mapped_column(ForeignKey("atividade.id", ondelete="CASCADE"), unique=True)
    estado: Mapped[str] = mapped_column(String(20))
    temperatura_c: Mapped[float | None] = mapped_column(Float)
    sensacao_c: Mapped[float | None] = mapped_column(Float)
    umidade_pct: Mapped[float | None] = mapped_column(Float)
    vento_kmh: Mapped[float | None] = mapped_column(Float)
    fonte: Mapped[str | None] = mapped_column(String(40))
    entrada: Mapped[str] = mapped_column(String(64))  # SHA-256 de inicio, duracao_s e posicao
    tentativas: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    erro: Mapped[str | None] = mapped_column(String(200))
    consultado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class RotuloTransicao(Base):
    """Rotulo "treino de transicao" de uma atividade (ADR 0009, item 1).

    Sem linha = "nao". A regra (`transicao@N`) so grava "sim" (origem `sugerido`); a linha `atleta` e a correcao dele
    (sim ou nao) e nunca e tocada pela regra. Quem grava a sugestao e `app.servicos.transicao`.
    """

    __tablename__ = "rotulo_transicao"
    __table_args__ = (
        CheckConstraint(_in("origem", ORIGENS_ROTULO), name="origem"),
        # a regra so grava "sim", sempre com a versao; a correcao do atleta nao tem versao
        CheckConstraint(
            "(origem = 'sugerido' AND transicao AND versao_regra IS NOT NULL) OR "
            "(origem = 'atleta' AND versao_regra IS NULL)",
            name="origem_versao",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    atividade_id: Mapped[int] = mapped_column(ForeignKey("atividade.id", ondelete="CASCADE"), unique=True)
    transicao: Mapped[bool] = mapped_column(Boolean)
    origem: Mapped[str] = mapped_column(String(20))
    versao_regra: Mapped[str | None] = mapped_column(String(40))  # ex.: transicao@1; nulo em `atleta`
    definido_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    atividade: Mapped[Atividade] = relationship(back_populates="rotulo_transicao")


class LimiarAtleta(Base):
    """Limiar do atleta com vigencia (ADR 0010, item 1): uma linha por (grandeza, inicio de vigencia).

    Dado fisiologico (LGPD): so no banco local, nunca em log nem pela API. Vale a linha de maior `vigente_desde`
    menor ou igual ao dia; antes da primeira nao ha limiar. Quem grava e `app.ingestao.saude.importar_saude`.
    """

    __tablename__ = "limiar_atleta"
    __table_args__ = (
        UniqueConstraint("atleta_id", "grandeza", "origem", "vigente_desde", name="uq_limiar_atleta_chave"),
        CheckConstraint(_in("grandeza", GRANDEZAS_LIMIAR), name="grandeza"),
        CheckConstraint(_in("origem", ORIGENS_LIMIAR), name="origem"),
        CheckConstraint("valor > 0", name="valor"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    atleta_id: Mapped[int] = mapped_column(ForeignKey("atleta.id", ondelete="CASCADE"), index=True)
    grandeza: Mapped[str] = mapped_column(String(20))  # fc_bpm (bpm) ou velocidade_ms (m/s)
    valor: Mapped[float] = mapped_column(Float)
    vigente_desde: Mapped[date] = mapped_column(Date)  # dia do calendario, sem fuso
    origem: Mapped[str] = mapped_column(String(20))
    versao_leitura: Mapped[str] = mapped_column(String(40))  # ex.: saude_garmin@1
    importado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ZonaFcAtleta(Base):
    """Zonas de FC com vigencia (ADR 0010, item 2). `metodo` guardado como a fonte traz, sem CHECK.

    `garmin_export`: retrato do JSON, datado pelo dia da importacao. `garmin_fit`: uma linha por mudanca de zonas
    vista nos FIT, datada pelo dia local da sessao. Nenhuma metrica da `carga@2` usa estas linhas.
    """

    __tablename__ = "zona_fc_atleta"
    __table_args__ = (
        UniqueConstraint("atleta_id", "esporte", "origem", "vigente_desde", name="uq_zona_fc_atleta_chave"),
        CheckConstraint(_in("origem", ORIGENS_ZONA), name="origem"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    atleta_id: Mapped[int] = mapped_column(ForeignKey("atleta.id", ondelete="CASCADE"), index=True)
    esporte: Mapped[str] = mapped_column(String(20))  # padrao, corrida, ciclismo
    vigente_desde: Mapped[date] = mapped_column(Date)
    origem: Mapped[str] = mapped_column(String(20))
    metodo: Mapped[str | None] = mapped_column(String(40))
    fc_max_bpm: Mapped[int | None] = mapped_column(Integer)
    fc_repouso_bpm: Mapped[int | None] = mapped_column(Integer)
    zona1_min_bpm: Mapped[int] = mapped_column(Integer)
    zona2_min_bpm: Mapped[int] = mapped_column(Integer)
    zona3_min_bpm: Mapped[int] = mapped_column(Integer)
    zona4_min_bpm: Mapped[int] = mapped_column(Integer)
    zona5_min_bpm: Mapped[int] = mapped_column(Integer)
    zona5_max_bpm: Mapped[int] = mapped_column(Integer)
    versao_leitura: Mapped[str] = mapped_column(String(40))
    importado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class RecordePessoal(Base):
    """Recorde pessoal (ADR 0010, item 2): uma linha por (modalidade, categoria, data em que foi batido).

    Um recorde melhorado entra como linha nova, sem apagar o anterior. `categoria` e o tipo como a fonte traz.
    `unidade` (`s`, `m`, `W`, `passos` ou nulo se o tipo e desconhecido) depende da categoria. `atividade_fonte_id`
    nao tem FK: a atividade pode nao estar importada. Dado fisiologico (LGPD): so no banco local, nunca em log.
    """

    __tablename__ = "recorde_pessoal"
    __table_args__ = (
        UniqueConstraint("atleta_id", "origem", "modalidade", "categoria", "alcancado_em", name="uq_recorde_pessoal_chave"),
        CheckConstraint(_in("modalidade", MODALIDADES), name="modalidade"),
        CheckConstraint(_in("origem", ORIGENS_SAUDE), name="origem"),
        CheckConstraint(f"unidade IS NULL OR {_in('unidade', UNIDADES_RECORDE)}", name="unidade"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    atleta_id: Mapped[int] = mapped_column(ForeignKey("atleta.id", ondelete="CASCADE"), index=True)
    origem: Mapped[str] = mapped_column(String(20))
    modalidade: Mapped[str] = mapped_column(String(20))
    categoria: Mapped[str] = mapped_column(String(60))
    valor: Mapped[float] = mapped_column(Float)
    unidade: Mapped[str | None] = mapped_column(String(10))
    alcancado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    atividade_fonte_id: Mapped[str | None] = mapped_column(String(100))
    versao_leitura: Mapped[str] = mapped_column(String(40))
    importado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CargaGarminDia(Base):
    """Carga aguda e cronica do Garmin, um valor por dia (ADR 0010, item 2). Na escala do Garmin, nao a do TSS.

    So a conferencia (item 8) usa; nunca entra na nossa carga. Dado fisiologico (LGPD): so no banco local.
    """

    __tablename__ = "carga_garmin_dia"
    __table_args__ = (
        UniqueConstraint("atleta_id", "origem", "dia", name="uq_carga_garmin_dia_chave"),
        CheckConstraint(_in("origem", ORIGENS_SAUDE), name="origem"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    atleta_id: Mapped[int] = mapped_column(ForeignKey("atleta.id", ondelete="CASCADE"), index=True)
    origem: Mapped[str] = mapped_column(String(20))
    dia: Mapped[date] = mapped_column(Date)
    carga_aguda: Mapped[float | None] = mapped_column(Float)
    carga_cronica: Mapped[float | None] = mapped_column(Float)
    razao: Mapped[float | None] = mapped_column(Float)
    versao_leitura: Mapped[str] = mapped_column(String(40))
    importado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CargaAtividade(Base):
    """Carga de treino de uma atividade elegivel (ADR 0010, item 5): `calculada` ou `sem_carga` com motivo.

    Sem linha para `multiesporte_pai` e `troca`. So guarda o que a conta produz (`app.metricas.carga`); quem grava,
    pela `entrada` e pela `versao`, e `app.servicos.carga.calcular_carga_do_atleta`. Os limiares sao os usados
    (auditoria): dado fisiologico (LGPD), so no banco local, nunca em log nem pela API.
    """

    __tablename__ = "carga_atividade"
    __table_args__ = (
        CheckConstraint(_in("estado", ESTADOS_CARGA), name="estado"),
        CheckConstraint(f"metodo IS NULL OR {_in('metodo', METODOS_CARGA)}", name="metodo"),
        CheckConstraint(f"motivo IS NULL OR {_in('motivo', MOTIVOS_CARGA)}", name="motivo"),
        CheckConstraint(_in("granularidade", GRANULARIDADES_CARGA), name="granularidade"),
        CheckConstraint(
            "(estado = 'calculada' AND carga IS NOT NULL AND metodo IS NOT NULL AND cobertura_pct IS NOT NULL "
            "AND motivo IS NULL) OR "
            "(estado = 'sem_carga' AND motivo IS NOT NULL AND carga IS NULL AND metodo IS NULL "
            "AND carga_rtss IS NULL AND carga_hrtss IS NULL)",
            name="estado_campos",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    atividade_id: Mapped[int] = mapped_column(ForeignKey("atividade.id", ondelete="CASCADE"), unique=True)
    estado: Mapped[str] = mapped_column(String(20))
    carga: Mapped[float | None] = mapped_column(Float)  # a do metodo vencedor
    metodo: Mapped[str | None] = mapped_column(String(10))
    carga_rtss: Mapped[float | None] = mapped_column(Float)
    carga_hrtss: Mapped[float | None] = mapped_column(Float)
    motivo: Mapped[str | None] = mapped_column(String(30))
    cobertura_pct: Mapped[float | None] = mapped_column(Float)
    granularidade: Mapped[str] = mapped_column(String(10))
    limiar_fc_bpm: Mapped[float | None] = mapped_column(Float)
    limiar_velocidade_ms: Mapped[float | None] = mapped_column(Float)
    limiar_vigente_desde: Mapped[date | None] = mapped_column(Date)  # vigencia do limiar do metodo vencedor
    entrada: Mapped[str] = mapped_column(String(64))  # SHA-256 do que entrou na conta
    versao: Mapped[str] = mapped_column(String(40))  # ex.: carga@2
    calculado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    atividade: Mapped[Atividade] = relationship(back_populates="carga")


class SemanaPadrao(Base):
    """Cabecalho da semana-padrao do atleta (ADR 0011, item 1): uma linha por (atleta, vigencia).

    Vale, para a data local `t`, a linha de maior `vigente_desde <= t`; nao ha `vigente_ate`. Vigencia sem itens e
    valida ("a partir daqui, sem plano"). Plano de treino do atleta: so no banco local, nunca em log nem fixture real.
    """

    __tablename__ = "semana_padrao"
    __table_args__ = (
        UniqueConstraint("atleta_id", "vigente_desde", name="uq_semana_padrao_vigencia"),
        CheckConstraint(_in("definido_por", DEFINIDO_POR), name="definido_por"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    atleta_id: Mapped[int] = mapped_column(ForeignKey("atleta.id"))
    vigente_desde: Mapped[date] = mapped_column(Date)  # dia do calendario, sem fuso
    definido_por: Mapped[str] = mapped_column(String(20))
    definido_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    itens: Mapped[list["SemanaPadraoItem"]] = relationship(
        back_populates="semana", cascade="all, delete-orphan", passive_deletes=True,
    )


class SemanaPadraoItem(Base):
    """Um item da semana-padrao: modalidade (e tipo, opcional) de um dia da semana ISO (1 = segunda ... 7 = domingo)."""

    __tablename__ = "semana_padrao_item"
    __table_args__ = (
        UniqueConstraint("semana_padrao_id", "dia_semana", "modalidade", name="uq_semana_padrao_item_dia_modalidade"),
        CheckConstraint("dia_semana BETWEEN 1 AND 7", name="dia_semana"),
        CheckConstraint(_in("modalidade", MODALIDADES_SEMANA), name="modalidade"),
        CheckConstraint(f"tipo_treino IS NULL OR {_in('tipo_treino', TIPOS_TREINO)}", name="tipo_treino"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    semana_padrao_id: Mapped[int] = mapped_column(ForeignKey("semana_padrao.id", ondelete="CASCADE"), index=True)
    dia_semana: Mapped[int] = mapped_column(Integer)
    modalidade: Mapped[str] = mapped_column(String(20))
    tipo_treino: Mapped[str | None] = mapped_column(String(20))  # NULL: treina a modalidade nesse dia, sem tipo

    semana: Mapped[SemanaPadrao] = relationship(back_populates="itens")


class CheckinTreino(Base):
    """Check-in pos-treino (ADR 0012, item 1): um por atividade (`UNIQUE`), com PSE, sensacao e observacao.

    Dado pessoal e de saude (a observacao e o mais sensivel): so no banco local, nunca em log nem em mensagem de erro,
    devolvido so ao proprio atleta; `worker.apagar_checkin` apaga todos de um atleta. `registrado_em` e `atualizado_em`
    sao definidos pela aplicacao (nao ha `server_default` nem `onupdate`). O `PUT` substitui tudo.
    """

    __tablename__ = "checkin_treino"
    __table_args__ = (
        CheckConstraint("pse BETWEEN 0 AND 10", name="pse"),
        CheckConstraint("sensacao BETWEEN 1 AND 5", name="sensacao"),
        CheckConstraint(f"texto IS NULL OR length(texto) BETWEEN 1 AND {CHECKIN_TEXTO_MAX}", name="texto_tamanho"),
        # ou "nada a relatar" sem atalho e sem texto, ou ao menos um atalho ou texto. Comparacoes explicitas com
        # TRUE/FALSE; todas as colunas sao NOT NULL (`texto` so aparece em IS [NOT] NULL): nunca vira NULL.
        CheckConstraint(
            "(nada_a_relatar = TRUE AND dor = FALSE AND cansaco = FALSE AND sono_ruim = FALSE AND calor = FALSE "
            "AND trabalho_estresse = FALSE AND texto IS NULL) OR "
            "(nada_a_relatar = FALSE AND (dor = TRUE OR cansaco = TRUE OR sono_ruim = TRUE OR calor = TRUE "
            "OR trabalho_estresse = TRUE OR texto IS NOT NULL))",
            name="observacao_coerente",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    atividade_id: Mapped[int] = mapped_column(ForeignKey("atividade.id", ondelete="CASCADE"), unique=True)
    pse: Mapped[int] = mapped_column(Integer)
    sensacao: Mapped[int] = mapped_column(Integer)
    nada_a_relatar: Mapped[bool] = mapped_column(Boolean)
    dor: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    cansaco: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    sono_ruim: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    calor: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    trabalho_estresse: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    texto: Mapped[str | None] = mapped_column(String)
    versao: Mapped[str] = mapped_column(String(20))
    registrado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    atualizado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    atividade: Mapped[Atividade] = relationship(back_populates="checkin")
    feedback: Mapped["FeedbackTreino | None"] = relationship(
        back_populates="checkin", cascade="all, delete-orphan", uselist=False
    )


class FeedbackTreino(Base):
    """Feedback automatico do treino (ADR 0013, item 2): um por check-in (`UNIQUE`), apagado com ele (`ON DELETE CASCADE`).

    Dado de saude (derivado do check-in): so no banco local, nunca em log nem em mensagem de erro, devolvido so ao proprio
    atleta. `estado = pronto` guarda o texto aprovado; `sem_feedback` guarda so o `motivo` (codigo), NUNCA o texto reprovado
    nem o termo que reprovou. O pacote de fatos nao e gravado. `tentado_em` e definido pela aplicacao.
    """

    __tablename__ = "feedback_treino"
    __table_args__ = (
        CheckConstraint("estado IN ('pronto', 'sem_feedback')", name="estado"),
        CheckConstraint(
            "motivo IS NULL OR motivo IN ('texto_reprovado', 'provedor_erro', 'provedor_tempo_limite', "
            "'provedor_nao_configurado', 'limite_de_chamadas')",
            name="motivo",
        ),
        CheckConstraint(f"texto IS NULL OR length(texto) BETWEEN 1 AND {FEEDBACK_TEXTO_MAX}", name="texto_tamanho"),
        # comparacoes explicitas: `texto`, `motivo`, `provedor` e `modelo` so aparecem em IS [NOT] NULL; nunca vira NULL.
        CheckConstraint(
            "(estado = 'pronto' AND texto IS NOT NULL AND motivo IS NULL AND provedor IS NOT NULL AND modelo IS NOT NULL) OR "
            "(estado = 'sem_feedback' AND texto IS NULL AND motivo IS NOT NULL)",
            name="estado_campos",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    checkin_id: Mapped[int] = mapped_column(ForeignKey("checkin_treino.id", ondelete="CASCADE"), unique=True)
    estado: Mapped[str] = mapped_column(String(20))
    motivo: Mapped[str | None] = mapped_column(String(30))
    texto: Mapped[str | None] = mapped_column(String)
    versao_fatos: Mapped[str] = mapped_column(String(20))
    versao_prompt: Mapped[str] = mapped_column(String(40))
    versao_checagens: Mapped[str] = mapped_column(String(40))
    provedor: Mapped[str | None] = mapped_column(String(40))
    modelo: Mapped[str | None] = mapped_column(String(80))
    tentativas: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    checkin_atualizado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    # ADR 0014, item 1: copia do `importado_em` da noite usada no pacote; NULL = o pacote saiu sem noite
    recuperacao_importada_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    tentado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    checkin: Mapped[CheckinTreino] = relationship(back_populates="feedback")


class RecuperacaoDia(Base):
    """Recuperacao de uma noite: sono, VFC noturna e FC de repouso (ADR 0014, item 1). Um registro por atleta, origem e noite.

    Guarda so tres numeros, nada mais da resposta do Garmin. `noite` e a data local de ACORDAR. Dado de saude: so no banco
    local, nunca em log nem em mensagem de erro, sem rota que o devolva. Noite sem nenhuma medida nao vira linha (a ausencia
    da linha e o "sem dado"). `importado_em` e definido pela aplicacao e so muda quando algum dos tres valores muda.
    """

    __tablename__ = "recuperacao_dia"
    __table_args__ = (
        UniqueConstraint("atleta_id", "origem", "noite", name="uq_recuperacao_dia_chave"),
        CheckConstraint(_in("origem", ORIGENS_RECUPERACAO), name="origem"),
        CheckConstraint("sono_s IS NULL OR sono_s BETWEEN 1 AND 86400", name="sono_s"),
        CheckConstraint("vfc_ms IS NULL OR (vfc_ms > 0 AND vfc_ms <= 500)", name="vfc_ms"),
        CheckConstraint("fc_repouso_bpm IS NULL OR fc_repouso_bpm BETWEEN 20 AND 150", name="fc_repouso_bpm"),
        CheckConstraint("sono_s IS NOT NULL OR vfc_ms IS NOT NULL OR fc_repouso_bpm IS NOT NULL", name="alguma_medida"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    atleta_id: Mapped[int] = mapped_column(ForeignKey("atleta.id", ondelete="CASCADE"), index=True)
    origem: Mapped[str] = mapped_column(String(20))
    noite: Mapped[date] = mapped_column(Date)
    sono_s: Mapped[int | None] = mapped_column(Integer)
    vfc_ms: Mapped[float | None] = mapped_column(Float)
    fc_repouso_bpm: Mapped[int | None] = mapped_column(Integer)
    versao_leitura: Mapped[str] = mapped_column(String(40))
    importado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
