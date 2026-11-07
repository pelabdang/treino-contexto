"""Objetos simples devolvidos pelo leitor de saude (Meta 6, #136; ADR 0010). Sem banco."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime

VERSAO_LEITURA = "saude_garmin@1"
ORIGEM_EXPORT = "garmin_export"
ORIGEM_FIT = "garmin_fit"
GRANDEZA_FC = "fc_bpm"
GRANDEZA_VELOCIDADE = "velocidade_ms"


def velocidade_ms(valor_fonte: float) -> float:
    """Velocidade de limiar da exportacao (m/s dividido por 10) para m/s.

    Conta: valor da fonte 0,370 -> 0,370 x 10 = 3,70 m/s. Conferido por plausibilidade, nao por documentacao da
    Garmin (ver a nota do modulo).
    """
    return valor_fonte * 10


def pace_s_km(velocidade_m_s: float) -> float:
    """Pace em s/km de uma velocidade em m/s: 1000 m / v.

    Ex.: 3,70 m/s -> 1000 / 3,70 = 270,27 s/km. Direto do valor da fonte: 100 / valor (0,370 -> 270,27 s/km).
    """
    return 1000 / velocidade_m_s


@dataclass(frozen=True)
class LimiarRegistro:
    """Uma linha de `limiar_atleta`: o valor de uma grandeza que passou a valer no dia `vigente_desde`."""

    grandeza: str  # GRANDEZA_FC (bpm) ou GRANDEZA_VELOCIDADE (m/s)
    vigente_desde: date  # dia do calendario, sem fuso
    valor: float
    origem: str = ORIGEM_EXPORT

    @property
    def pace_s_km(self) -> float | None:
        """Pace de limiar em s/km (so para a velocidade): 1000 / velocidade em m/s."""
        return pace_s_km(self.valor) if self.grandeza == GRANDEZA_VELOCIDADE else None


@dataclass(frozen=True)
class ZonaFc:
    """Uma linha de `zona_fc_atleta`.

    `vigente_desde`: dia local da sessao (origem FIT); no retrato do JSON, o dia informado por quem importa
    (`dia_retrato`), ou `None` se nao foi informado.
    """

    esporte: str  # padrao, corrida, ciclismo
    origem: str
    vigente_desde: date | None
    metodo: str | None  # como veio: `HR_MAX` no JSON, `percent_max_hr` no FIT
    fc_max_bpm: int | None
    fc_repouso_bpm: int | None
    zona1_min_bpm: int
    zona2_min_bpm: int
    zona3_min_bpm: int
    zona4_min_bpm: int
    zona5_min_bpm: int
    zona5_max_bpm: int

    def conteudo(self) -> tuple:
        """Tudo menos data e origem: serve para ver se as zonas mudaram."""
        return (self.esporte, self.metodo, self.fc_max_bpm, self.fc_repouso_bpm,
                self.zona1_min_bpm, self.zona2_min_bpm, self.zona3_min_bpm, self.zona4_min_bpm,
                self.zona5_min_bpm, self.zona5_max_bpm)


@dataclass(frozen=True)
class RecordePessoal:
    """Uma linha de `recorde_pessoal`."""

    modalidade: str  # corrida, natacao, ciclismo, outra
    categoria: str  # o tipo como a fonte traz (ex.: "Best 5km Run")
    valor: float
    unidade: str | None  # s, m, W, passos; None se o tipo nao e conhecido
    alcancado_em: datetime  # UTC
    atividade_fonte_id: str | None  # None quando a fonte traz activityId 0
    atual: bool  # recorde vigente do tipo (os outros sao superados)
    origem: str = ORIGEM_EXPORT


@dataclass(frozen=True)
class CargaGarminDia:
    """Uma linha de `carga_garmin_dia`: o item de maior timestamp do dia."""

    dia: date
    carga_aguda: float | None
    carga_cronica: float | None
    razao: float | None  # a fonte pode nao trazer
    origem: str = ORIGEM_EXPORT


@dataclass
class SaudeGarmin:
    """Tudo que o leitor achou. Lista vazia = sem aquele dado; o motivo esta em `avisos` (sem dado pessoal)."""

    limiares: list[LimiarRegistro] = field(default_factory=list)
    zonas: list[ZonaFc] = field(default_factory=list)  # retrato do JSON + historico dos FIT
    recordes: list[RecordePessoal] = field(default_factory=list)
    carga_dia: list[CargaGarminDia] = field(default_factory=list)
    avisos: list[str] = field(default_factory=list)
