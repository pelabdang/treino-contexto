"""Pacote de fatos `fatos_treino@2` (issues #324 e #374, ADR 0013 item 1 e ADR 0014 item 4): a única coisa que o provedor de LLM recebe sobre o treino.

Função pura: sem banco, sem rede, sem IA. Recebe o que o código **já calculou** (a atividade, o resultado da `linha_base@2` com os valores da
sessão, o clima, a `carga@2`, os esforços e o check-in) e devolve um dicionário com os fatos lado a lado e os textos prontos (`*_texto`),
com as mesmas funções de formatação que a API já usa. **Não inventa número, não faz conta nova e não afirma causa**: o calor, p. ex., aparece
como dois fatos separados (a temperatura medida e o atalho "calor"), sem ligação.

**Nunca entra no pacote:** o texto livre da observação do check-in (nem o fato de existir), nome, `atleta_id`, `atividade_id` ou qualquer
identificador, data ou hora real (só durações), posição (`inicio_lat`, `inicio_lon`), nome de arquivo, nome do professor. Por construção: a função
lê da atividade e do check-in só os atributos listados em ``_campos_*`` abaixo; o resto do objeto (ORM ou não) é ignorado.

Fonte: regra própria do projeto, sem artigo (ADR 0013, "Fontes"). Qualquer mudança de campo, de unidade, de estado, da lista de métricas ou do
que fica de fora exige subir ``VERSAO``. Campos, ordem das chaves e exemplos em docs/metricas/fatos-treino.md.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from app.metricas import carga as cg
from app.metricas import carga_pse as cp
from app.metricas import esforcos as esf
from app.metricas import linha_base as lb
from app.metricas import recuperacao as rc
from app.servicos.carga_pse_leitura import duracao_pt, numero_pt
from app.servicos.checkin import PSE_ANCORA, SENSACAO_TEXTO
from app.servicos.distancia_texto import distancia_da_atividade
from app.servicos.linha_base_leitura import (
    JANELA_SEMANAS,
    METRICAS,
    MINIMO_TREINOS,
    _diferenca,
    _texto_valor,
)

VERSAO = "fatos_treino@2"

# Atalhos do check-in (ADR 0012, item 2). Só as chaves vão ao pacote, ordenadas por nome: a ordem não depende de quem chama.
_ATALHOS = ("dor", "cansaco", "sono_ruim", "calor", "trabalho_estresse")


@dataclass(frozen=True)
class ClimaFatos:
    """Clima da atividade como a API o lê (ADR 0007). Só em `ok` há valores; fonte, atribuição e posição não entram."""

    estado: str  # ok | pendente | falha | indoor | sem_posicao
    temperatura_c: float | None = None
    sensacao_termica_c: float | None = None
    umidade_pct: float | None = None
    vento_kmh: float | None = None


@dataclass(frozen=True)
class CargaFatos:
    """`carga@2` da atividade como a API a lê (ADR 0010)."""

    estado: str  # calculada | sem_carga | pendente
    valor: float | None = None
    metodo: str | None = None  # rtss | hrtss
    motivo: str | None = None  # só em sem_carga


@dataclass(frozen=True)
class EsforcosFatos:
    """Esforços detectados (`esforcos@1`): a contagem por faixa, sem pace por esforço nesta versão."""

    treino_chave: bool
    series: Sequence[tuple[str, int]] = ()  # (faixa_rotulo, quantidade)


def _inteiro_se_exato(x: float) -> float | int:
    return int(x) if float(x).is_integer() else x


def _treino(atividade: Any, parte_de_transicao: bool) -> dict[str, Any]:
    distancia = atividade.distancia_m
    return {
        "modalidade": atividade.modalidade,
        "tipo_treino": atividade.tipo_treino,
        "parte_de_transicao": bool(parte_de_transicao),
        "ambiente": "esteira" if atividade.subtipo == "esteira" else None,
        "duracao_s": atividade.duracao_s,
        "duracao_texto": duracao_pt(atividade.duracao_s / 60),
        "distancia_m": distancia,
        "distancia_texto": distancia_da_atividade(atividade.modalidade, distancia),
        "fc_media_bpm": None if atividade.fc_media is None else int(atividade.fc_media + 0.5),
    }


def _metrica(m: lb.MetricaBase, motivos: Mapping[str, str]) -> dict[str, Any]:
    tipo = METRICAS[m.chave][2]
    valor_t = mediana_t = dif_t = motivo = None
    if m.estado == "sem_valor":
        motivo = motivos.get(m.chave)
    else:
        valor_t = _texto_valor(tipo, m.valor)
        if m.estado in ("dentro", "fora"):
            mediana_t = _texto_valor(tipo, m.mediana)
        if m.estado == "fora":
            dif_t = _diferenca(tipo, m.valor, m.mediana)
    return {"chave": m.chave, "estado": m.estado, "valor_texto": valor_t, "mediana_texto": mediana_t,
            "diferenca_texto": dif_t, "n": m.n, "motivo": motivo}


def _linha_base(r: lb.LinhaBase, motivos: Mapping[str, str]) -> dict[str, Any]:
    return {"versao": r.versao, "estado": r.estado, "motivo": r.motivo, "janela_semanas": JANELA_SEMANAS,
            "minimo_treinos": MINIMO_TREINOS, "metricas": [_metrica(m, motivos) for m in r.metricas]}


def _esforcos(e: EsforcosFatos | None) -> dict[str, Any] | None:
    if e is None:
        return None
    return {"versao": esf.VERSAO, "treino_chave": bool(e.treino_chave),
            "series": [{"faixa_rotulo": rotulo, "quantidade": q} for rotulo, q in e.series]}


def _clima(c: ClimaFatos | None) -> dict[str, Any] | None:
    if c is None:
        return None
    ok = c.estado == "ok"  # fora do `ok` os valores ficam nulos, mesmo que venham preenchidos
    return {"estado": c.estado, "temperatura_c": c.temperatura_c if ok else None,
            "sensacao_termica_c": c.sensacao_termica_c if ok else None,
            "umidade_pct": c.umidade_pct if ok else None, "vento_kmh": c.vento_kmh if ok else None}


def _hm(segundos: float) -> str:
    """Duração em minutos inteiros: "5 h 40 min", "6 h", "45 min" (a conta fecha à mão, como `duracao_pt`)."""
    h, m = divmod(int(segundos / 60 + 0.5), 60)
    return f"{h} h" if h and not m else f"{h} h {m} min" if h else f"{m} min"


def _arred(x: float) -> int:
    return int(x + 0.5)


def _medida_recuperacao(m: rc.MedidaRecuperacao) -> dict[str, Any]:
    """Uma medida da noite. O texto vem dos valores **arredondados** (minuto, ms, bpm), e a diferença é a conta entre eles."""
    com_normal = m.estado in (rc.DENTRO, rc.ABAIXO, rc.ACIMA)
    valor_t = normal_t = dif_t = None
    if m.valor is not None:
        if m.chave == "sono":
            valor_t = _hm(m.valor)
            normal_t = _hm(m.mediana) if com_normal else None
            diff = abs(_arred(m.mediana / 60) - _arred(m.valor / 60)) * 60 if com_normal else 0
            dif_t = _hm(diff) if m.estado in (rc.ABAIXO, rc.ACIMA) else None
        else:
            unidade = "ms" if m.chave == "vfc" else "bpm"
            valor_t = f"{_arred(m.valor)} {unidade}"
            normal_t = f"{_arred(m.mediana)} {unidade}" if com_normal else None
            dif_t = f"{abs(_arred(m.mediana) - _arred(m.valor))} {unidade}" if m.estado in (rc.ABAIXO, rc.ACIMA) else None
        if dif_t is not None:
            dif_t += " abaixo" if m.estado == rc.ABAIXO else " acima"
    return {"chave": m.chave, "estado": m.estado, "valor": None if m.valor is None else _inteiro_se_exato(m.valor),
            "valor_texto": valor_t, "normal_texto": normal_t, "diferenca_texto": dif_t, "n": m.n}


def _recuperacao(r: rc.Recuperacao | None, p: rc.Parametros = rc.PADRAO) -> dict[str, Any] | None:
    """Bloco `recuperacao` (ADR 0014, item 4). `None` quando quem chama não passa a recuperação. Em `sem_dado` só `versao`,
    `estado` e `motivo`. Nunca a série diária, a data da noite, MAD, z ou a mediana numérica."""
    if r is None:
        return None
    if r.estado != rc.OK:
        return {"versao": r.versao, "estado": r.estado, "motivo": r.motivo}
    return {"versao": r.versao, "estado": r.estado, "motivo": None, "janela_noites": p.janela_noites,
            "minimo_noites": p.minimo_noites, "medidas": [_medida_recuperacao(m) for m in r.medidas]}


def _carga(c: CargaFatos) -> dict[str, Any]:
    calculada = c.estado == "calculada"
    return {"versao": None if c.estado == "pendente" else cg.VERSAO, "estado": c.estado,
            "valor": c.valor if calculada else None,
            "valor_texto": f"{c.valor:.1f}".replace(".", ",") + " pontos" if calculada else None,  # igual ao da API
            "metodo": c.metodo if calculada else None, "motivo": c.motivo if c.estado == "sem_carga" else None}


def _carga_pse(r: cp.CargaPse) -> dict[str, Any]:
    calculada = r.estado == cp.CALCULADA
    return {"versao": r.versao, "estado": r.estado, "valor": _inteiro_se_exato(r.valor) if calculada else None,
            "valor_texto": f"{numero_pt(r.valor)} UA" if calculada else None}


def _atalhos(checkin: Any) -> list[str]:
    """Só as chaves marcadas. Aceita a lista `atalhos` ou as cinco colunas booleanas do `CheckinTreino`."""
    lista = getattr(checkin, "atalhos", None)
    marcados = set(lista) if lista is not None else {k for k in _ATALHOS if getattr(checkin, k, False)}
    return sorted(marcados & set(_ATALHOS))


def _checkin(c: Any) -> dict[str, Any]:
    return {"pse": c.pse, "pse_texto": PSE_ANCORA.get(c.pse), "sensacao_nivel": c.sensacao,
            "sensacao_texto": SENSACAO_TEXTO[c.sensacao], "nada_a_relatar": bool(c.nada_a_relatar), "atalhos": _atalhos(c)}


def fatos_treino(
    atividade: Any,
    checkin: Any | None,
    linha_base: lb.LinhaBase,
    motivos_sem_valor: Mapping[str, str],
    clima: ClimaFatos | None,
    carga: CargaFatos,
    esforcos: EsforcosFatos | None,
    parte_de_transicao: bool = False,
    recuperacao: rc.Recuperacao | None = None,
) -> dict[str, Any] | None:
    """O pacote `fatos_treino@2`, ou ``None`` quando não há feedback possível: **sem check-in** ou atividade **não elegível**
    (`multiesporte_pai` e `troca`, ADR 0012 item 4).

    - ``atividade``: lê só `modalidade`, `subtipo`, `tipo_treino`, `duracao_s`, `distancia_m` e `fc_media`.
    - ``checkin``: lê só `pse`, `sensacao`, `nada_a_relatar` e os atalhos (`atalhos` ou as colunas `dor`, `cansaco`...). **Nunca** o texto livre.
    - ``linha_base``: o resultado da `linha_base@2`; ``motivos_sem_valor``: o motivo de cada métrica `sem_valor` (como `valores_e_motivos`).
    - ``recuperacao``: o resultado da `recuperacao@1` da noite do treino (ou ``None``: o bloco sai ``None``).
    - ``clima``, ``carga`` e ``esforcos``: o que a API já lê; ``None`` em clima e esforços onde não se aplica (natação).
    Chaves sempre presentes, na ordem da ADR; ausente é ``None``. Nada é alterado nos argumentos.
    """
    if checkin is None:
        return None
    r_pse = cp.carga_pse(checkin.pse, atividade.duracao_s, atividade.subtipo)
    if r_pse is None:  # não elegível
        return None
    return {
        "versao": VERSAO,
        "treino": _treino(atividade, parte_de_transicao),
        "linha_base": _linha_base(linha_base, motivos_sem_valor),
        "esforcos": _esforcos(esforcos),
        "clima": _clima(clima),
        "recuperacao": _recuperacao(recuperacao),
        "carga": _carga(carga),
        "carga_pse": _carga_pse(r_pse),
        "checkin": _checkin(checkin),
    }
