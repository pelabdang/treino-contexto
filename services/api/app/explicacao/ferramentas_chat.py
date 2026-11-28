"""Ferramentas de consulta do chat sobre as métricas que já existem (issue #594, ADR 0017, item 1): séries da Evolução, comparação de períodos,
carga e forma do dia, linha de base. **Nenhuma métrica nova**: cada função lê o que a API já calcula e devolve um `dict` com os números em **texto
pronto** (`*_texto`), que é o único texto que o modelo pode citar; o modelo nunca soma, subtrai nem converte (as `checagens_chat@1` conferem).

Funções puras de leitura: só `SELECT`, nunca gravam, sem rede, sem IA, sem log. O `atleta_id` é **parâmetro do código** (vem da sessão, ADR 0017,
item 2), nunca argumento do modelo: o registro das ferramentas (#593) o passa. O relógio (`agora`) é injetável.

Fontes (todas já existentes e documentadas): `evolucao_serie` e `frase_evolucao@1` (mediana de 28 dias contra os 28 anteriores,
docs/metricas/evolucao-series.md), `serie_carga@2` e `frase_forma@1` (docs/metricas/serie-carga.md), `linha_base@3` (docs/metricas/linha-base.md).
"""

from __future__ import annotations

import dataclasses
import math
import statistics
from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Atividade
from app.metricas import serie_carga as sc
from app.servicos import evolucao_serie as ev
from app.servicos import frase_evolucao as fe
from app.servicos import frase_forma as ff
from app.servicos.carga_leitura import hoje_do_atleta, serie_do_atleta
from app.servicos.carga_textos import aprendendo_texto, numero_texto, tsb_texto
from app.servicos.evolucao_series import POR_ID, carregar
from app.servicos.fuso import data_local
from app.servicos.linha_base_leitura import linha_base_da_atividade

VERSAO = "ferramentas_chat@1"

# Períodos nomeados (ADR 0017, item 1): dias que terminam em "hoje" do atleta. `ultimos_28_dias_anteriores` só existe como par de comparação.
PERIODOS_DIAS = {"ultimos_7_dias": 7, "ultimos_28_dias": 28, "ultimas_12_semanas": 84, "ultimos_6_meses": 182, "ultimo_ano": 365}
PERIODO_TEXTO = {
    "ultimos_7_dias": "últimos 7 dias", "ultimos_28_dias": "últimos 28 dias", "ultimas_12_semanas": "últimas 12 semanas",
    "ultimos_6_meses": "últimos 6 meses", "ultimo_ano": "último ano",
}
PERIODO_PADRAO = "ultimas_12_semanas"
PAR_DA_COMPARACAO = ("ultimos_28_dias", "ultimos_28_dias_anteriores")  # a janela da `frase_evolucao@1`


def erro(codigo: str, **extra: Any) -> dict[str, Any]:
    """O resultado de uma ferramenta que não pôde responder: volta ao modelo uma vez (ADR 0017, item 3)."""
    return {"versao": VERSAO, "estado": "erro", "codigo": codigo, **extra}


def _hoje(session: Session, atleta_id: int, agora: datetime | None) -> date:
    r = session.execute(
        select(Atividade.inicio, Atividade.fuso_min).where(Atividade.atleta_id == atleta_id).order_by(Atividade.inicio.desc()).limit(1)
    ).first()
    return hoje_do_atleta(None if r is None else r[1], agora)


def _janela(hoje: date, periodo: str | None, de: str | None, ate: str | None) -> tuple[date, date, str] | None:
    """(início, fim, texto) do período pedido; `None` se o nome ou as datas são inválidos."""
    if de is not None or ate is not None:
        try:
            ini = date.fromisoformat(de) if de else hoje - timedelta(days=PERIODOS_DIAS[PERIODO_PADRAO] - 1)
            fim = date.fromisoformat(ate) if ate else hoje
        except ValueError:
            return None
        if ini > fim:
            return None
        return ini, fim, f"de {ini:%d/%m} a {fim:%d/%m}"
    periodo = periodo or PERIODO_PADRAO
    if periodo not in PERIODOS_DIAS:
        return None
    return hoje - timedelta(days=PERIODOS_DIAS[periodo] - 1), hoje, PERIODO_TEXTO[periodo]


def _com_unidade(frase_tipo: str, x: float) -> str:
    return str(int(fe.arredonda(x))) if frase_tipo == "ctl" else fe._mostra(frase_tipo, x)


def _margem(frase_tipo: str, base: float) -> str | None:
    """O limite de "parecido" da `frase_evolucao@1` (piso absoluto ou relativo sobre a base mostrada), em texto; `None` onde a diferença vai em %."""
    if frase_tipo in fe.MEDIDAS:
        m = fe.MEDIDAS[frase_tipo]
        return None if m.percentual else fe._dif(frase_tipo, max(m.piso_abs, m.piso_rel * abs(base)), base)
    if frase_tipo in fe.VOLUMES:
        return fe._dif(frase_tipo, fe.VOLUME_PISO_REL * abs(base), base)
    return fe._num(max(fe.CTL_PISO_ABS, fe.CTL_PISO_REL * abs(base)), 0)


def _serie_ou_erro(serie_id: str) -> dict[str, Any] | None:
    if serie_id not in POR_ID:
        return erro("serie_desconhecida", ids_validos=sorted(POR_ID))
    return None


# ---------------------------------------------------------------- ler_serie
def serie_evolucao(session: Session, atleta_id: int, serie_id: str, periodo: str | None = None, de: str | None = None, ate: str | None = None,
                   agora: datetime | None = None) -> dict[str, Any]:
    """`ler_serie`: os pontos da série do catálogo no período, a faixa do normal e a frase de 4 semanas, como a API da Evolução devolve."""
    if (e := _serie_ou_erro(serie_id)) is not None:
        return e
    janela = _janela(_hoje(session, atleta_id, agora), periodo, de, ate)
    if janela is None:
        return erro("argumento_invalido", campo="periodo")
    ini, fim, texto_periodo = janela
    lida = ev.serie(session, atleta_id, serie_id, "1a", agora)  # o maior período; o recorte é nosso, a faixa do normal é sempre a das 12 semanas
    pontos = [p for p in lida.pontos if ini <= p.data <= fim and p.valor_texto is not None]

    def com_unidade(texto: str) -> str:  # a rota manda a unidade à parte; o texto citável a leva junto ("5:44/km"), para a checagem conferir a unidade
        return texto + ("" if lida.unidade.startswith("/") or not lida.unidade else " ") + lida.unidade
    base: dict[str, Any] = {"versao": lida.versao_calculo, "serie_id": serie_id, "titulo": lida.serie.titulo, "periodo_texto": texto_periodo,
                            "unidade": lida.unidade}
    if not pontos:
        motivo = lida.frase.texto if lida.frase.tipo in ("sem_treino", "poucos") else "Sem treinos dessa série nesse período."
        return {**base, "estado": "sem_dados", "motivo_texto": motivo}
    out = {**base, "estado": "ok", "pontos": [
        {"atividade_id": p.atividade_id, "data_texto": p.data_texto, "valor_texto": com_unidade(p.valor_texto), "fora_do_normal": p.fora_do_normal} for p in pontos],
        "ultimo_valor_texto": com_unidade(pontos[-1].valor_texto), "ultimo_rotulo": pontos[-1].rotulo, "frase_texto": lida.frase.texto}
    if lida.referencia is not None:
        out["faixa_normal_texto"] = lida.referencia.texto
    if lida.aprendendo_texto:
        out["aprendendo_texto"] = lida.aprendendo_texto
    return out


# ---------------------------------------------------------------- comparar_periodos
ROLANTES = {"ultimos_7_dias": 7, "ultimos_14_dias": 14, "ultimos_28_dias": 28, "ultimas_12_semanas": 84}  # terminam ONTEM (hoje ainda não acabou)
FIXOS = ("esta_semana", "semana_passada", "semana_retrasada", "este_mes", "mes_passado")
PERIODOS_COMPARAVEIS = tuple(ROLANTES) + tuple(f"{n}_anteriores" for n in ROLANTES) + FIXOS  # e o mês de calendário "AAAA-MM"
MINIMO_TREINOS = fe.MINIMO_PADRAO
MINIMO_TIROS = 2


@dataclasses.dataclass(frozen=True)
class Janela:
    ini: date
    fim: date
    tipo: str  # rolante | semana | mes
    parcial: bool  # a semana ou o mês em curso (vai até hoje)
    texto: str

    @property
    def dias(self) -> int:
        return (self.fim - self.ini).days + 1


def _mes(ano: int, mes: int) -> tuple[date, date]:
    ini = date(ano, mes, 1)
    return ini, (date(ano + (mes == 12), mes % 12 + 1, 1) - timedelta(days=1))


def _janela_de_comparacao(nome: str, hoje: date) -> Janela | None:
    """Resolve o nome do período em datas locais. Os rolantes terminam ontem (como a `frase_evolucao@1`); a semana e o mês em curso vão até hoje."""
    ontem = hoje - timedelta(days=1)
    base = nome.removesuffix("_anteriores")
    if base in ROLANTES:
        n = ROLANTES[base]
        fim = ontem - timedelta(days=n if nome != base else 0)
        ini = fim - timedelta(days=n - 1)
        rotulo = {"ultimos_7_dias": "últimos 7 dias", "ultimos_14_dias": "últimos 14 dias", "ultimos_28_dias": "últimos 28 dias",
                  "ultimas_12_semanas": "últimas 12 semanas"}[base] if nome == base else {
            "ultimos_7_dias": "7 dias anteriores", "ultimos_14_dias": "14 dias anteriores", "ultimos_28_dias": "28 dias anteriores",
            "ultimas_12_semanas": "12 semanas anteriores"}[base]
        return Janela(ini, fim, "rolante", False, f"{rotulo} ({ini:%d/%m} a {fim:%d/%m})")
    segunda = hoje - timedelta(days=hoje.weekday())
    if nome == "esta_semana":
        return Janela(segunda, hoje, "semana", True, f"esta semana ({segunda:%d/%m} a {hoje:%d/%m})")
    if nome in ("semana_passada", "semana_retrasada"):
        ini = segunda - timedelta(days=7 if nome == "semana_passada" else 14)
        fim = ini + timedelta(days=6)
        return Janela(ini, fim, "semana", False, f"{'semana passada' if nome == 'semana_passada' else 'semana retrasada'} ({ini:%d/%m} a {fim:%d/%m})")
    if nome == "este_mes":
        ini = hoje.replace(day=1)
        return Janela(ini, hoje, "mes", True, f"este mês ({ini:%d/%m} a {hoje:%d/%m})")
    if nome == "mes_passado":
        ini, fim = _mes(hoje.year - (hoje.month == 1), 12 if hoje.month == 1 else hoje.month - 1)
        return Janela(ini, fim, "mes", False, f"mês passado ({ini:%d/%m} a {fim:%d/%m})")
    try:  # mês de calendário "AAAA-MM"
        ano, mes = int(nome[:4]), int(nome[5:7])
        if len(nome) != 7 or nome[4] != "-" or not 1 <= mes <= 12:
            return None
        ini, fim = _mes(ano, mes)
    except ValueError:
        return None
    if ini > hoje:
        return None
    parcial = fim > hoje
    fim = min(fim, hoje)
    return Janela(ini, fim, "mes", parcial, f"mês {ini:%m/%Y} ({ini:%d/%m} a {fim:%d/%m})")


def _estatistica(s, pontos, j: Janela) -> tuple[float | None, int, str, bool]:
    """(valor, n, medida, aprendendo) da série na janela. treino e tiros: mediana dos treinos; volume: média por semana (total / (dias / 7));
    condicionamento: o valor do último dia da janela."""
    vistos = [p for p in pontos if j.ini <= p.dia <= j.fim and p.valor is not None and math.isfinite(p.valor)]
    if s.tipo == "ctl":
        if not vistos:
            return None, 0, "valor no último dia do período", False
        ultimo = max(vistos, key=lambda p: p.dia)
        return ultimo.valor, 1, "valor no último dia do período", ultimo.aprendendo
    if s.tipo == "volume":
        return (sum(p.valor for p in vistos) / (j.dias / 7) if vistos else None), len(vistos), "média por semana", False
    return (statistics.median(p.valor for p in vistos) if vistos else None), len(vistos), "mediana dos treinos", False


def _limite(s, base: float) -> tuple[float, int]:
    """(limite de "parecido", casas do valor mostrado), os mesmos da `frase_evolucao@1`."""
    if s.frase in fe.MEDIDAS:
        m = fe.MEDIDAS[s.frase]
        return max(m.piso_abs, m.piso_rel * abs(base)), m.casas
    if s.frase in fe.VOLUMES:
        return fe.VOLUME_PISO_REL * abs(base), fe.VOLUMES[s.frase][2]
    return max(fe.CTL_PISO_ABS, fe.CTL_PISO_REL * abs(base)), 0


def _pct(d: float, base: float) -> str | None:
    return f"{fe._num(fe.arredonda(100 * abs(d) / abs(base)), 0)}%" if base else None


def comparar_periodos(session: Session, atleta_id: int, serie_id: str, periodo_a: str = "ultimos_28_dias", periodo_b: str = "ultimos_28_dias_anteriores",
                      agora: datetime | None = None) -> dict[str, Any]:
    """`comparar_periodos`: dois períodos de mesmo tamanho (semana, 14 dias, 28 dias, 12 semanas, semana ou mês de calendário), por código.

    Regras da `frase_evolucao@1` sobre os valores mostrados: mediana dos treinos (pace, FC...), limite de "parecido" por série, `direcao` do valor de `a` contra
    `b`, diferença absoluta e em %, mínimo de 3 treinos por período (2 nos tiros). Abaixo do mínimo o resultado é `parcial`: traz valores e `n`, **sem `direcao`**.
    Para 28 contra 28 o resultado **é** o da `frase_evolucao@1`. A semana ou o mês em curso corta o outro período nos mesmos primeiros dias."""
    if (e := _serie_ou_erro(serie_id)) is not None:
        return e
    s = POR_ID[serie_id]
    m = carregar(session, atleta_id, agora, (s,))
    ja, jb = _janela_de_comparacao(periodo_a, m.hoje), _janela_de_comparacao(periodo_b, m.hoje)
    if ja is None or jb is None:
        return erro("argumento_invalido", campo="periodo_a" if ja is None else "periodo_b", periodos_validos=[*PERIODOS_COMPARAVEIS, "AAAA-MM"])
    corte = None
    for curta, longa in ((ja, jb), (jb, ja)):  # a semana ou o mês em curso: o outro vira os mesmos primeiros dias
        if curta.parcial and curta.tipo == longa.tipo and longa.dias > curta.dias:
            cortada = dataclasses.replace(longa, fim=longa.ini + timedelta(days=curta.dias - 1))
            cortada = dataclasses.replace(cortada, texto=f"{longa.texto.split(' (')[0]}, primeiros {curta.dias} dias ({cortada.ini:%d/%m} a {cortada.fim:%d/%m})")
            ja, jb = (ja, cortada) if longa is jb else (cortada, jb)
            corte = f"O outro período foi cortado nos primeiros {curta.dias} dias, para ter o mesmo tamanho do que está em curso."
            break
    if ja.dias != jb.dias and not (ja.tipo == jb.tipo == "mes"):
        return erro("comparacao_nao_suportada", motivo="tamanhos_diferentes", texto="Só dá para comparar períodos do mesmo tamanho.")
    if not (ja.fim < jb.ini or jb.fim < ja.ini):
        return erro("comparacao_nao_suportada", motivo="periodos_sobrepostos", texto="Os dois períodos se sobrepõem.")
    base: dict[str, Any] = {"versao": fe.VERSAO, "serie_id": serie_id, "periodo_a_texto": ja.texto, "periodo_b_texto": jb.texto}
    if corte:
        base["corte_texto"] = corte
    if (periodo_a, periodo_b) == PAR_DA_COMPARACAO:
        frase = ev.serie(session, atleta_id, serie_id, "12s", agora).frase  # o resultado da frase da Evolução, não uma segunda conta
        if frase.tipo not in ("comparada", "so_valor") or frase.valor_atual is None:
            return {**base, "estado": "sem_dados" if frase.tipo in ("sem_treino", "sem_dado") else "parcial", "motivo_texto": frase.texto,
                    "a": {"n": frase.n_atual}, "b": {"n": frase.n_anterior}}
        va, vb, n_a, n_b = frase.valor_atual, frase.valor_anterior, frase.n_atual, frase.n_anterior
        medida = "média por semana (mediana das semanas)" if s.tipo == "volume" else "valor no último dia do período" if s.tipo == "ctl" else "mediana dos treinos"
        if vb is None:  # condicionamento "aprendendo": só o valor
            return {**base, "estado": "parcial", "motivo_texto": frase.texto, "medida_texto": medida,
                    "a": {"n": n_a, "valor_texto": _com_unidade(s.frase, va)}, "b": {"n": n_b}}
        direcao = frase.mudanca
    else:
        pontos = m.pontos_por_serie[s.id]
        va, n_a, medida, apr_a = _estatistica(s, pontos, ja)
        vb, n_b, _, apr_b = _estatistica(s, pontos, jb)
        minimo = MINIMO_TIROS if s.tipo == "tiros" else 1 if s.tipo in ("volume", "ctl") else MINIMO_TREINOS
        if n_a == 0 and n_b == 0:
            return {**base, "estado": "sem_dados", "motivo_texto": "Sem treinos dessa série nos dois períodos.", "a": {"n": 0}, "b": {"n": 0}}
        lado = lambda v, n: {"n": n, **({} if v is None else {"valor_texto": _com_unidade(s.frase, v)})}  # noqa: E731
        if n_a < minimo or n_b < minimo or apr_a or apr_b:
            aviso = ("O condicionamento ainda está aprendendo em um dos períodos." if apr_a or apr_b else
                     f"Poucos treinos para comparar: {n_a} no primeiro período, {n_b} no segundo (o mínimo é {minimo}).")
            return {**base, "estado": "parcial", "motivo_texto": aviso, "medida_texto": medida, "a": lado(va, n_a), "b": lado(vb, n_b)}
        limite, casas = _limite(s, vb)
        ma, mb = fe.arredonda(va, casas), fe.arredonda(vb, casas)  # as regras decidem sobre os valores mostrados
        d = fe.arredonda(ma - mb, casas)
        direcao = "parecido" if abs(d) < limite - 1e-9 or d == 0 else "maior" if d > 0 else "menor"
        va, vb = ma, mb
    out: dict[str, Any] = {**base, "estado": "ok", "medida_texto": medida, "a": {"n": n_a, "valor_texto": _com_unidade(s.frase, va)},
                           "b": {"n": n_b, "valor_texto": _com_unidade(s.frase, vb)}, "direcao": direcao, "margem_texto": _margem(s.frase, vb)}
    if direcao != "parecido":
        d = va - vb
        if s.frase in (*fe.MEDIDAS, *fe.VOLUMES):
            out["diferenca_texto"] = fe._dif(s.frase, abs(d), vb)
        else:
            out["diferenca_texto"] = fe._num(abs(d), 0)
        out["diferenca_pct_texto"] = _pct(d, vb)
    return out


# ---------------------------------------------------------------- ler_carga_forma
def carga_e_forma(session: Session, atleta_id: int, data: str | None = None, agora: datetime | None = None) -> dict[str, Any]:
    """`ler_carga_forma`: CTL, ATL e TSB do dia (`serie_carga@2`) e a frase de forma (`frase_forma@1`). A série vai **até ontem** (hoje não acabou), então
    `data` ausente ou posterior vale o último dia calculado; `data` antes do primeiro dia com carga é `sem_dados`. Dia que ainda aprende (42 dias) é `parcial`."""
    try:
        pedido = date.fromisoformat(data) if data else None
    except ValueError:
        return erro("argumento_invalido", campo="data")
    lida = serie_do_atleta(session, atleta_id, agora)
    serie = lida.serie
    base = {"versao": sc.VERSAO}
    if not serie.dias:
        return {**base, "estado": "sem_dados", "motivo_texto": "Ainda não há treino com carga calculada."}
    if pedido is not None and pedido < serie.dias[0].dia:
        return {**base, "estado": "sem_dados", "motivo_texto": f"A carga só começa em {ev.data_texto(serie.dias[0].dia)}."}
    i = len(serie.dias) - 1 if pedido is None or pedido >= serie.dias[-1].dia else next(k for k, d in enumerate(serie.dias) if d.dia == pedido)
    d = serie.dias[i]
    ate_o_dia = dataclasses.replace(serie, dias=serie.dias[: i + 1])
    out: dict[str, Any] = {**base, "estado": "parcial" if d.aprendendo else "ok", "data_texto": ev.data_texto(d.dia), "carga_dia_texto": numero_texto(d.carga),
                           "ctl_texto": numero_texto(d.ctl), "atl_texto": numero_texto(d.atl), "tsb_texto": tsb_texto(d.tsb), "estimativa": True}
    if d.aprendendo:
        out["motivo_texto"] = aprendendo_texto(sc.DIAS_APRENDENDO - (d.dia - serie.dias[0].dia).days)
    frase = ff.frase_forma(ate_o_dia, lida.pendentes if i == len(serie.dias) - 1 else 0)
    if frase is not None:
        out["frase_texto"] = frase.texto
    return out


# ---------------------------------------------------------------- ler_linha_base
def linha_base(session: Session, atleta_id: int, modalidade: str, tipo_treino: str) -> dict[str, Any]:
    """`ler_linha_base`: o normal do atleta para o tipo de treino (`linha_base@3`: mediana de cada métrica, `n` e estado), lido pelo treino mais recente do
    tipo, que é quem tem janela de 12 semanas atrás de si. Sem treino do tipo: `sem_dados`."""
    a = session.scalar(
        select(Atividade).where(Atividade.atleta_id == atleta_id, Atividade.modalidade == modalidade, Atividade.tipo_treino == tipo_treino)
        .order_by(Atividade.inicio.desc()).limit(1))
    if a is None:
        return {"versao": VERSAO, "estado": "sem_dados", "modalidade": modalidade, "tipo_treino": tipo_treino,
                "motivo_texto": "Sem treinos desse tipo para calcular o seu normal."}
    r = linha_base_da_atividade(session, a)
    ref = {"atividade_id": a.id, "data_texto": ev.data_texto(data_local(a.inicio, a.fuso_min))}
    if r.estado == "sem_linha_base":
        return {"versao": r.versao, "estado": "sem_dados", "modalidade": modalidade, "tipo_treino": tipo_treino, "motivo_texto": r.texto, "treino_de_referencia": ref}
    metricas = [{"chave": m.chave, "rotulo": m.rotulo, "estado": m.estado, "mediana_texto": m.mediana_texto, "valor_do_treino_texto": m.valor_texto, "n": m.n,
                 "texto": m.texto} for m in r.metricas]
    tem_normal = any(m["estado"] in ("dentro", "fora") for m in metricas)  # sem nenhuma métrica com normal calculado, o estado é parcial
    return {"versao": r.versao, "estado": "ok" if tem_normal else "parcial", "modalidade": modalidade, "tipo_treino": tipo_treino,
            "janela_semanas": r.janela_semanas, "minimo_treinos": r.minimo_treinos, "treino_de_referencia": ref, "metricas": metricas}
