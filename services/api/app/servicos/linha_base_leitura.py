"""Linha de base da atividade, calculada na leitura (issue #266, ADR 0011, itens 6 e 7).

Lê do banco as atividades do atleta (mesma modalidade e tipo, janela de 56 dias antes da sessão), calcula os valores de cada
métrica (pace médio, melhor tiro, FC, carga) e chama a função pura `app.metricas.linha_base.linha_base`. Aqui também ficam
os textos prontos: a API formata, o app mostra (ADR 0004, adendo 2). Nada é gravado e nenhum valor vem de modelo de
linguagem. Os motivos de uma métrica sem valor (`esteira`, `sem_tiros`, `sem_fc`, ...) saem daqui, não da função pura.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.models import Atividade
from app.metricas import carga as cg
from app.metricas import linha_base as lb
from app.metricas.tiros_1km import agregar_sessao, formatar_pace, tiro_de_bloco, tiros_de_blocos
from app.servicos.evolucao_tiros import SUBTIPOS_FORA_DA_SERIE, _bloco
from app.servicos.fuso import data_local

JANELA_SEMANAS = lb.PADRAO.janela_dias // 7
MINIMO_TREINOS = lb.PADRAO.minimo_treinos

# rótulo, unidade e tipo de diferença de cada métrica (ADR 0011, item 7)
METRICAS = {
    "pace_medio": ("Pace médio", "s/km", "pace"),
    "melhor_pace": ("Pace do melhor tiro", "s/km", "pace"),
    "fc_media": ("FC média", "bpm", "fc"),
    "fc_melhor_tiro": ("FC do melhor tiro", "bpm", "fc"),
    "carga": ("Carga", "pontos", "carga"),
}

MOTIVO_SEM_LINHA_BASE = {
    "multiesporte": "parte de um treino multiesporte que não recebe tipo (o pai ou a troca)",
    "modalidade_sem_metricas": "a modalidade não tem métricas de linha de base",
    "sem_tipo": "o treino não tem tipo",
    "divergente": "treino com formato diferente do plano",
    "transicao": "parte de treino de transição",
}
MOTIVO_SEM_VALOR = {
    "esteira": "esteira, a distância vem do aparelho",
    "sem_distancia": "o treino não tem distância",
    "sem_fc": "o treino não tem frequência cardíaca",
    "sem_tiros": "o treino não teve série de tiros",
    "carga_pendente": "a carga ainda não foi calculada",
    "sem_dados_saude": "sem dados de saúde para a carga",
    "sem_limiar_na_data": "sem limiar na data para a carga",
    "sem_fc_carga": "sem frequência cardíaca para a carga",
    "sem_pace": "sem pace para a carga",
    "cobertura_insuficiente": "cobertura insuficiente para a carga",
    "modalidade_sem_carga": "a modalidade não tem carga",
}


@dataclass(frozen=True)
class MetricaTexto:
    chave: str
    rotulo: str
    unidade: str
    estado: str
    motivo: str | None
    valor: float | None
    valor_texto: str | None
    mediana: float | None
    mediana_texto: str | None
    desvio: float | None
    z: float | None
    n: int
    diferenca_texto: str | None
    texto: str


@dataclass(frozen=True)
class LinhaBaseTexto:
    versao: str
    estado: str  # ok | sem_linha_base
    motivo: str | None
    texto: str | None  # só em sem_linha_base
    modalidade: str
    tipo_treino: str | None
    janela_semanas: int
    minimo_treinos: int
    metricas: tuple[MetricaTexto, ...]


def _utc(dt: datetime) -> datetime:
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)


def _melhor_tiro(a: Atividade) -> tuple[float, float | None] | None:
    """(pace do melhor tiro em s/km, FC dele) da série `tiros_1km@6`, ou None sem série (2 ou mais tiros)."""
    blocos = [_bloco(b) for b in sorted(a.blocos, key=lambda b: b.ordem)]
    r = tiros_de_blocos(blocos, a.modalidade)
    if not r.eh_intervalado:
        return None
    por_ordem = {b.ordem: b for b in blocos}
    p = agregar_sessao(a.id, data_local(a.inicio, a.fuso_min), [tiro_de_bloco(por_ordem[o]) for o in r.tiros])
    return p.melhor_pace_s_km, p.melhor_fc_media


def valores_e_motivos(a: Atividade) -> tuple[dict[str, float | None], dict[str, str]]:
    """Valor de cada métrica da atividade e, onde não há valor, o motivo (chave em `MOTIVO_SEM_VALOR`)."""
    v: dict[str, float | None] = {}
    m: dict[str, str] = {}
    esteira = a.subtipo in SUBTIPOS_FORA_DA_SERIE
    if a.modalidade == "corrida":
        if esteira:
            v["pace_medio"], m["pace_medio"] = None, "esteira"
        elif a.distancia_m and a.distancia_m > 0 and a.duracao_s > 0:
            v["pace_medio"] = a.duracao_s / a.distancia_m * 1000.0
        else:
            v["pace_medio"], m["pace_medio"] = None, "sem_distancia"
    if a.fc_media is not None:
        v["fc_media"] = a.fc_media
    else:
        v["fc_media"], m["fc_media"] = None, "sem_fc"
    c = a.carga
    if c is None or c.versao != cg.VERSAO:
        v["carga"], m["carga"] = None, "carga_pendente"
    elif c.estado == "calculada":
        v["carga"] = c.carga
    else:
        v["carga"], m["carga"] = None, "sem_fc_carga" if c.motivo == "sem_fc" else c.motivo
    if a.modalidade == "corrida" and a.tipo_treino == "intervalado":
        melhor = _melhor_tiro(a)
        if melhor is None:
            v["melhor_pace"] = v["fc_melhor_tiro"] = None
            m["melhor_pace"] = m["fc_melhor_tiro"] = "sem_tiros"
        else:
            pace, fc = melhor
            if esteira:
                v["melhor_pace"], m["melhor_pace"] = None, "esteira"
            else:
                v["melhor_pace"] = pace
            if fc is None:
                v["fc_melhor_tiro"], m["fc_melhor_tiro"] = None, "sem_fc"
            else:
                v["fc_melhor_tiro"] = fc
    return v, m


def _treino(a: Atividade) -> lb.Treino:
    valores, _ = valores_e_motivos(a)
    return lb.Treino(
        id=a.id, inicio=_utc(a.inicio), dia=data_local(a.inicio, a.fuso_min), modalidade=a.modalidade,
        tipo_treino=a.tipo_treino, valores=valores, subtipo=a.subtipo, divergente=a.tipo_divergencia is not None,
        transicao=bool(a.rotulo_transicao and a.rotulo_transicao.transicao),
    )


def _minusculo(rotulo: str) -> str:
    """Rótulo em minúsculas no meio da frase, mantendo a sigla FC ("FC média" vira "FC média", "Carga" vira "carga")."""
    palavras = rotulo.split(" ")
    return " ".join(w if w == "FC" else w.lower() for w in palavras)


def _virgula(x: float, casas: int = 1) -> str:
    return f"{x:.{casas}f}".replace(".", ",")


def _texto_valor(tipo: str, x: float) -> str:
    if tipo == "pace":
        return f"{formatar_pace(x)}/km"
    if tipo == "fc":
        return f"{int(x + 0.5)} bpm"
    return f"{_virgula(x)} pontos"


def _diferenca(tipo: str, valor: float, mediana: float) -> str:
    d = abs(valor - mediana)
    if tipo == "pace":
        return f"{int(d + 0.5)} s/km {'mais rápido' if valor < mediana else 'mais lento'}"
    if tipo == "fc":
        return f"{int(d + 0.5)} bpm {'acima' if valor > mediana else 'abaixo'}"
    return f"{_virgula(d)} pontos {'maior' if valor > mediana else 'menor'}"


def _treinos(n: int) -> str:
    return f"{n} treino" if n == 1 else f"{n} treinos"


def _metrica_texto(m: lb.MetricaBase, tipo_treino: str, motivos: dict[str, str]) -> MetricaTexto:
    rotulo, unidade, tipo = METRICAS[m.chave]
    janela = f"nas últimas {JANELA_SEMANAS} semanas"
    valor_t = None if m.valor is None else _texto_valor(tipo, m.valor)
    mediana_t = None if m.mediana is None else _texto_valor(tipo, m.mediana)
    motivo, dif = None, None
    if m.estado == "sem_valor":
        motivo = motivos.get(m.chave)
        por_que = MOTIVO_SEM_VALOR.get(motivo or "", "sem o dado neste treino")
        texto = f"Sem {_minusculo(rotulo)} neste treino: {por_que}."
    elif m.estado == "aprendendo":
        texto = f"Ainda aprendendo o seu normal em treino {tipo_treino}: {m.n} de {MINIMO_TREINOS} treinos {janela}."
    elif m.estado == "dentro":
        texto = (f"{rotulo} dentro do seu normal para treino {tipo_treino}: {valor_t}, perto da mediana de {mediana_t} "
                 f"({_treinos(m.n)} {janela}).")
    else:
        dif = _diferenca(tipo, m.valor, m.mediana)
        texto = (f"{rotulo} fora do seu normal para treino {tipo_treino}: {valor_t}, {dif} que a mediana de {mediana_t} "
                 f"({_treinos(m.n)} {janela}). Isto compara com o seu histórico; não diz se o treino foi bom ou ruim.")
    return MetricaTexto(m.chave, rotulo, unidade, m.estado, motivo, m.valor, valor_t, m.mediana, mediana_t, m.desvio, m.z,
                        m.n, dif, texto)


def linha_base_da_atividade(session: Session, a: Atividade) -> LinhaBaseTexto:
    """A linha de base da atividade (`linha_base@1`) com os textos prontos. Calculada na leitura; nunca grava."""
    sessao = _treino(a)
    base = dict(modalidade=a.modalidade, tipo_treino=a.tipo_treino, janela_semanas=JANELA_SEMANAS, minimo_treinos=MINIMO_TREINOS)
    motivo = lb.motivo_sem_linha_base(sessao)
    if motivo is not None:
        return LinhaBaseTexto(lb.VERSAO, "sem_linha_base", motivo, f"Sem linha de base: {MOTIVO_SEM_LINHA_BASE[motivo]}.", metricas=(), **base)
    corte = sessao.dia - timedelta(days=lb.PADRAO.janela_dias + 1)  # folga de um dia para o fuso; a data local exata é conferida na função
    candidatas = session.scalars(
        select(Atividade)
        .where(
            Atividade.atleta_id == a.atleta_id,
            Atividade.id != a.id,
            Atividade.modalidade == a.modalidade,
            Atividade.tipo_treino == a.tipo_treino,
            Atividade.inicio >= datetime(corte.year, corte.month, corte.day, tzinfo=timezone.utc),
            Atividade.inicio <= _utc(a.inicio),
        )
        .options(selectinload(Atividade.blocos), selectinload(Atividade.carga), selectinload(Atividade.rotulo_transicao))
    ).all()
    resultado = lb.linha_base(sessao, [_treino(c) for c in candidatas])
    _, motivos = valores_e_motivos(a)
    return LinhaBaseTexto(
        resultado.versao, resultado.estado, resultado.motivo, None,
        metricas=tuple(_metrica_texto(m, a.tipo_treino, motivos) for m in resultado.metricas), **base)


TEXTO_DIVERGENCIA = {
    "sem_esforco": "O plano diz intervalado, mas o treino não teve esforço detectado.",
}


def texto_divergencia(a: Atividade) -> tuple[str, str] | None:
    """(motivo, texto pronto) da divergência gravada, ou None."""
    if a.tipo_divergencia == "sem_esforco":
        return "sem_esforco", TEXTO_DIVERGENCIA["sem_esforco"]
    if a.tipo_divergencia == "tem_tiros":
        blocos = [_bloco(b) for b in sorted(a.blocos, key=lambda b: b.ordem)]
        n = len(tiros_de_blocos(blocos, a.modalidade).tiros)
        quantos = f"{n} tiros de 1 km" if n else "tiros de 1 km"
        return "tem_tiros", f"O plano diz {a.tipo_treino}, mas o treino teve {quantos}."
    return None
