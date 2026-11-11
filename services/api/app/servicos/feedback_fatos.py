"""Adaptador do pacote de fatos: banco -> argumentos de `fatos_treino` (issue #327, ADR 0013 item 1).

A função pura `app.explicacao.fatos_treino.fatos_treino` não lê o banco. Aqui a sessão, a atividade e o check-in viram os argumentos dela
**com os serviços de leitura que a API já usa** (linha de base, clima, carga, esforços, rótulo de transição); nada é recalculado nem
gravado. O texto livre do check-in nunca é lido pela função do pacote.

Dado de saúde: o pacote é o que sai para o provedor; este módulo não registra nada.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.db.models import Atividade, CheckinTreino
from app.explicacao import fatos_treino as ft
from app.explicacao.fatos_treino import CargaFatos, ClimaFatos, EsforcosFatos
from app.servicos.carga_leitura import carga_da_atividade
from app.servicos.clima import clima_da_atividade
from app.servicos.esforcos_leitura import esforcos_da_atividade
from app.servicos.linha_base_leitura import linha_base_resultado, valores_e_motivos

VERSAO = ft.VERSAO


def _rotulo_faixa(faixa: str) -> str:
    """`d1000` -> "1 km", `d400` -> "400 m", `t4` -> "4 min" (o rótulo do oráculo e da ADR 0013: acima de 1 km, em km)."""
    n = int(faixa[1:])
    if faixa[0] == "t":
        return f"{n} min"
    return f"{n} m" if n < 1000 else (f"{n // 1000} km" if n % 1000 == 0 else f"{n / 1000:.1f}".replace(".", ",") + " km")


def _clima(session: Session, a: Atividade) -> ClimaFatos | None:
    if a.modalidade == "natacao":  # o clima nao se aplica a natacao: bloco ausente no pacote (oraculo F06)
        return None
    c = clima_da_atividade(session, a.id)
    if c is None:
        return None
    return ClimaFatos(c.estado, c.temperatura_c, c.sensacao_c, c.umidade_pct, c.vento_kmh)


def _carga(session: Session, a: Atividade) -> CargaFatos:
    c = carga_da_atividade(session, a)
    if c is None:  # ignorada (pai/troca): nem chega aqui, a função do pacote devolve None antes
        return CargaFatos("pendente")
    return CargaFatos(c.estado, c.carga, c.metodo, c.motivo)


def _esforcos(session: Session, a: Atividade) -> EsforcosFatos | None:
    e = esforcos_da_atividade(session, a)
    if e is None:  # modalidade sem detecção (natação)
        return None
    contagem: dict[str, int] = {}
    for b in sorted(e.blocos, key=lambda b: b.ordem):
        if b.categoria == "esforco" and b.faixa:
            rotulo = _rotulo_faixa(b.faixa)
            contagem[rotulo] = contagem.get(rotulo, 0) + 1
    return EsforcosFatos(e.treino_chave, tuple(contagem.items()))


def fatos_da_atividade(session: Session, atividade: Atividade, checkin: CheckinTreino | None) -> dict[str, Any] | None:
    """O pacote `fatos_treino@1` da atividade com o check-in, ou `None` (sem check-in ou atividade não elegível)."""
    if checkin is None:
        return None
    return ft.fatos_treino(
        atividade=atividade,
        checkin=checkin,
        linha_base=linha_base_resultado(session, atividade),
        motivos_sem_valor=valores_e_motivos(atividade)[1],
        clima=_clima(session, atividade),
        carga=_carga(session, atividade),
        esforcos=_esforcos(session, atividade),
        parte_de_transicao=bool(atividade.rotulo_transicao and atividade.rotulo_transicao.transicao),
    )
