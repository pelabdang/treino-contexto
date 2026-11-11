"""Geracao do feedback automatico do treino (issue #327, ADR 0013 itens 2 a 4): pacote -> LLM -> checagens -> grava.

So o `worker.gerar_feedback` chama `gerar`; nunca dentro do `PUT` do check-in. O pacote de fatos (`fatos_treino@1`, #324) e as
checagens (`checagens_feedback@1`, #325) entram por INJECAO, para a camada nao depender de como eles sao feitos:

- `montar_pacote(session, atividade, checkin) -> dict | None`: o pacote de fatos, ou `None` se a atividade nao e elegivel;
- `checar(pacote, texto) -> str | None`: `None` se o texto passa, ou o codigo do motivo da reprovacao (descartado aqui).

Dado de saude: nada do pacote, do texto, do texto reprovado nem de excecao vai para log ou saida; so contagens e codigos de motivo.
Texto reprovado NUNCA e gravado: a linha fica `sem_feedback` com `motivo = texto_reprovado`.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as _insert_pg
from sqlalchemy.dialects.sqlite import insert as _insert_sqlite
from sqlalchemy.orm import Session, joinedload

from app.db.models import FEEDBACK_TEXTO_MAX, Atividade, CheckinTreino, FeedbackTreino
from app.ingestao.garmin.unidades import para_utc
from app.llm import Redator
from app.servicos.checkin import elegivel

_CODIGO = re.compile(r"[a-z0-9_]{1,40}")
_INSERT = {"postgresql": _insert_pg, "sqlite": _insert_sqlite}

MontarPacote = Callable[[Session, Atividade, CheckinTreino], "dict | None"]
Checar = Callable[[dict, str], "str | None"]


@dataclass(frozen=True)
class Versoes:
    fatos: str  # `fatos_treino@1`
    prompt: str  # `feedback_prompt@1`
    checagens: str  # `checagens_feedback@1`


@dataclass
class RelatorioFeedback:
    gerados: int = 0  # linhas `pronto` gravadas
    sem_feedback: int = 0  # linhas `sem_feedback` gravadas (qualquer motivo)
    ignorados: int = 0  # em dia, ou nao elegiveis
    adiados: int = 0  # sobraram por causa do limite de chamadas (nosso ou do provedor); entram na proxima execucao
    mantidos: int = 0  # `--refazer` falhou (provedor ou checagens) e o texto pronto e em dia foi mantido
    limite_do_provedor: bool = False  # o provedor recusou por limite por minuto: a execucao parou ali
    erros: int = 0  # falha ao montar o pacote ou checar: nada gravado (so a contagem, nunca a mensagem)
    motivos: dict[str, int] = field(default_factory=dict)  # codigos das falhas: soma = `sem_feedback` + `mantidos`
    reprovacoes: dict[str, int] = field(default_factory=dict)  # codigos devolvidos pelas checagens (nao gravados)


def desatualizado(fb: FeedbackTreino, checkin: CheckinTreino, versao_fatos: str) -> bool:
    """O feedback nao vale mais: o check-in foi editado (inclusive um `PUT` identico) ou a versao do pacote mudou.
    Os dois `datetime` sao normalizados (o SQLite devolve sem fuso)."""
    return (para_utc(fb.checkin_atualizado_em) != para_utc(checkin.atualizado_em)) or fb.versao_fatos != versao_fatos


def fila(session: Session, atleta_id: int, versoes: Versoes, refazer: bool = False) -> tuple[list[CheckinTreino], int]:
    """Os check-ins a gerar, na ordem de atendimento, e quantos ficaram de fora (em dia ou nao elegiveis).

    Entram: sem linha, `sem_feedback` e desatualizados (com `refazer`, todos). Ordem: quem nunca foi tentado primeiro; depois
    por menos `tentativas`, para um treino que sempre reprova nao gastar o limite dos outros; empate: o mais recente primeiro.
    """
    linhas = session.execute(
        select(CheckinTreino, Atividade).join(Atividade, Atividade.id == CheckinTreino.atividade_id)
        .options(joinedload(CheckinTreino.feedback))
        .where(Atividade.atleta_id == atleta_id)
    ).unique().all()
    entram, fora = [], 0
    for checkin, ativ in linhas:
        fb = checkin.feedback
        if not elegivel(ativ):
            fora += 1
        elif fb is None or refazer or fb.estado == "sem_feedback" or desatualizado(fb, checkin, versoes.fatos):
            nunca = 0 if fb is None else 1
            tent = 0 if fb is None else fb.tentativas
            entram.append(((nunca, tent, -para_utc(ativ.inicio).timestamp()), checkin))
        else:
            fora += 1
    entram.sort(key=lambda x: x[0])
    return [c for _, c in entram], fora


def _gravar(session: Session, checkin: CheckinTreino, atualizado_em: datetime, *, estado: str, motivo: str | None,
            texto: str | None, provedor: str | None, modelo: str | None, versoes: Versoes, agora: datetime) -> None:
    """Upsert por `checkin_id` (`INSERT ... ON CONFLICT DO NOTHING` por dialeto, sem savepoint, como o check-in) e commit."""
    fb = session.scalars(select(FeedbackTreino).where(FeedbackTreino.checkin_id == checkin.id)).first()
    if fb is None:
        dialeto = session.get_bind().dialect.name
        if dialeto not in _INSERT:
            raise RuntimeError(f"upsert do feedback sem suporte no banco {dialeto}")
        session.execute(
            _INSERT[dialeto](FeedbackTreino).values(
                checkin_id=checkin.id, estado=estado, motivo=motivo, texto=texto, versao_fatos=versoes.fatos,
                versao_prompt=versoes.prompt, versao_checagens=versoes.checagens, provedor=provedor, modelo=modelo,
                tentativas=1, checkin_atualizado_em=atualizado_em, tentado_em=agora,
            ).on_conflict_do_nothing(index_elements=["checkin_id"])
        )
        fb = session.scalars(select(FeedbackTreino).where(FeedbackTreino.checkin_id == checkin.id)).one()
        session.refresh(fb)
    else:  # `tentativas` conta sobre o MESMO check-in: volta a 1 quando ele mudou
        mesmo = para_utc(fb.checkin_atualizado_em) == para_utc(atualizado_em)
        fb.tentativas = fb.tentativas + 1 if mesmo else 1
    fb.estado, fb.motivo, fb.texto, fb.provedor, fb.modelo = estado, motivo, texto, provedor, modelo
    fb.versao_fatos, fb.versao_prompt, fb.versao_checagens = versoes.fatos, versoes.prompt, versoes.checagens
    fb.checkin_atualizado_em, fb.tentado_em = atualizado_em, agora
    session.commit()


def gerar(session: Session, atleta_id: int, redator: Redator, montar_pacote: MontarPacote, checar: Checar,
          versoes: Versoes, prompt: str, refazer: bool = False, agora: datetime | None = None) -> RelatorioFeedback:
    """Gera (ou refaz) o feedback dos check-ins do atleta, dentro do limite de chamadas do `redator`. Idempotente: sem mudanca
    nova, nao ha fila e nao ha chamada. Um `commit` por feedback. Nunca levanta por causa do provedor."""
    rel = RelatorioFeedback()
    checkins, rel.ignorados = fila(session, atleta_id, versoes, refazer)
    for n, checkin in enumerate(checkins):
        if redator.configurado and redator.chamadas >= redator.limite_chamadas:
            rel.adiados = len(checkins) - n  # sem linha nova; entram na proxima execucao
            break
        atualizado_em = checkin.atualizado_em  # o que o pacote vai refletir
        try:
            pacote = montar_pacote(session, checkin.atividade, checkin)
        except Exception:  # noqa: BLE001  (a mensagem pode ter dado de saude: so a contagem)
            session.rollback()
            rel.erros += 1
            continue
        if pacote is None:  # nao elegivel
            rel.ignorados += 1
            continue
        fb_antes = checkin.feedback  # com `refazer`: texto pronto e em dia nao se perde se a nova tentativa falhar
        manter = fb_antes is not None and fb_antes.estado == "pronto" and not desatualizado(fb_antes, checkin, versoes.fatos)
        res = redator.redigir(prompt, pacote)
        if res.texto is None and getattr(redator, "limite_do_provedor", False):  # limite do provedor: nada gravado, o resto fica para depois
            rel.adiados = len(checkins) - n
            rel.limite_do_provedor = True
            break
        momento = agora or datetime.now(timezone.utc)

        def grava(estado: str, motivo: str | None, texto: str | None) -> None:
            _gravar(session, checkin, atualizado_em, estado=estado, motivo=motivo, texto=texto, provedor=res.provedor,
                    modelo=res.modelo, versoes=versoes, agora=momento)

        if res.texto is None:
            if manter:
                rel.mantidos += 1
            else:
                grava("sem_feedback", res.motivo, None)
                rel.sem_feedback += 1
            rel.motivos[res.motivo] = rel.motivos.get(res.motivo, 0) + 1
            continue
        try:
            reprovado = checar(pacote, res.texto) if len(res.texto) <= FEEDBACK_TEXTO_MAX else "tamanho"
        except Exception:  # noqa: BLE001
            session.rollback()
            rel.erros += 1
            continue
        if reprovado is not None:  # o texto e descartado; guarda-se so o codigo de motivo da linha
            if manter:
                rel.mantidos += 1
            else:
                grava("sem_feedback", "texto_reprovado", None)
                rel.sem_feedback += 1
            rel.motivos["texto_reprovado"] = rel.motivos.get("texto_reprovado", 0) + 1
            codigo = str(reprovado) if _CODIGO.fullmatch(str(reprovado)) else "outro"  # nunca texto livre nem o termo
            rel.reprovacoes[codigo] = rel.reprovacoes.get(codigo, 0) + 1
            continue
        grava("pronto", None, res.texto)
        rel.gerados += 1
    return rel
