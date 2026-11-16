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
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as _insert_pg
from sqlalchemy.dialects.sqlite import insert as _insert_sqlite
from sqlalchemy.orm import Session, joinedload

from app.db.models import FEEDBACK_TEXTO_MAX, Atividade, CheckinTreino, ClimaAtividade, FeedbackTreino
from app.ingestao.garmin.unidades import para_utc
from app.llm import Redator
from app.servicos.checkin import elegivel
from app.servicos.clima import assinatura_clima
from app.servicos.recuperacao_pacote import mesmo_instante

_CODIGO = re.compile(r"[a-z0-9_]{1,40}")
_INSERT = {"postgresql": _insert_pg, "sqlite": _insert_sqlite}

# `RecuperacaoHoje(atividade) -> importado_em | None`: o `importado_em` da noite do treino HOJE (ADR 0014, item 4b).
RecuperacaoHoje = Callable[[Atividade], "datetime | None"]
_NAO_SEI = object()  # quem chama sem a recuperacao nao compara essa parte (so check-in e versao)

MontarPacote = Callable[[Session, Atividade, CheckinTreino], "dict | None"]
Checar = Callable[[dict, str], "str | None"]


@dataclass(frozen=True)
class Versoes:
    fatos: str  # `fatos_treino@1`
    prompt: str  # texto do `feedback_prompt`
    checagens: str  # `checagens_feedback@1`


@dataclass
class RelatorioFeedback:
    gerados: int = 0  # linhas `pronto` gravadas
    sem_feedback: int = 0  # linhas `sem_feedback` gravadas (qualquer motivo)
    ignorados: int = 0  # em dia, ou nao elegiveis
    adiados: int = 0  # sobraram por causa do limite de chamadas (nosso ou do provedor); entram na proxima execucao
    mantidos: int = 0  # `--refazer` falhou (provedor ou checagens) e o texto pronto e em dia passou nas checagens atuais: mantido
    mantido_reprovado: int = 0  # idem, mas o texto antigo NAO passou nas checagens atuais (#407): caiu e a linha ficou `sem_feedback`
    limite_do_provedor: bool = False  # o provedor recusou por limite por minuto: a execucao parou ali
    erros: int = 0  # falha ao montar o pacote ou checar: nada gravado (so a contagem, nunca a mensagem)
    motivos: dict[str, int] = field(default_factory=dict)  # codigos das falhas: soma = `sem_feedback` + `mantidos` (o texto antigo que caiu ja esta em `sem_feedback`)
    reprovacoes: dict[str, int] = field(default_factory=dict)  # codigos devolvidos pelas checagens (nao gravados), do texto novo e do antigo que caiu


def motivos_desatualizado(fb: FeedbackTreino, checkin: CheckinTreino, versao_fatos: str, recuperacao_hoje: Any = _NAO_SEI,
                          clima_hoje: Any = _NAO_SEI) -> frozenset[str]:
    """Por que o feedback nao vale mais, entre `checkin`, `versao`, `noite` e `clima` (vazio = em dia).

    - `checkin`: o check-in foi editado (inclusive um `PUT` identico); `versao`: a `versao_fatos` mudou;
    - `noite`: `fb.recuperacao_importada_em` difere do `importado_em` de hoje (ADR 0014, item 4b; `None` dos dois lados nao conta);
    - `clima`: `fb.clima_visto` difere da assinatura do clima de hoje (#409, adendo 4 da ADR 0013). `clima_visto` nulo = linha anterior
      a migracao `0015`, de que o pacote viu: nao se compara (nao entra na fila de uma vez; `--refazer` resolve).
    Todos os `datetime` sao normalizados para UTC (o SQLite devolve sem fuso). Noite e clima so entram na conta quando quem chama
    passa `recuperacao_hoje` / `clima_hoje`."""
    motivos = set()
    if para_utc(fb.checkin_atualizado_em) != para_utc(checkin.atualizado_em):
        motivos.add("checkin")
    if fb.versao_fatos != versao_fatos:
        motivos.add("versao")
    if recuperacao_hoje is not _NAO_SEI and not mesmo_instante(fb.recuperacao_importada_em, recuperacao_hoje):
        motivos.add("noite")
    if clima_hoje is not _NAO_SEI and fb.clima_visto is not None and fb.clima_visto != clima_hoje:
        motivos.add("clima")
    return frozenset(motivos)


def desatualizado(fb: FeedbackTreino, checkin: CheckinTreino, versao_fatos: str, recuperacao_hoje: Any = _NAO_SEI,
                  clima_hoje: Any = _NAO_SEI) -> bool:
    """O feedback nao vale mais por qualquer um dos motivos de `motivos_desatualizado`."""
    return bool(motivos_desatualizado(fb, checkin, versao_fatos, recuperacao_hoje, clima_hoje))


def so_a_noite_mudou(fb: FeedbackTreino, checkin: CheckinTreino, versao_fatos: str, recuperacao_hoje: Any = _NAO_SEI) -> bool:
    """Desatualizado SO porque a noite do treino chegou ou mudou (#396)."""
    return motivos_desatualizado(fb, checkin, versao_fatos, recuperacao_hoje) == {"noite"}


def _hoje(recuperacao_hoje: RecuperacaoHoje | None, ativ: Atividade) -> Any:
    return _NAO_SEI if recuperacao_hoje is None else recuperacao_hoje(ativ)


def _climas_do_atleta(session: Session, atleta_id: int) -> dict[int, ClimaAtividade]:
    """As linhas de `clima_atividade` do atleta, por atividade, numa consulta so (como as noites)."""
    return {c.atividade_id: c for c in session.scalars(
        select(ClimaAtividade).join(Atividade, Atividade.id == ClimaAtividade.atividade_id).where(Atividade.atleta_id == atleta_id))}


def fila(session: Session, atleta_id: int, versoes: Versoes, refazer: bool = False,
         recuperacao_hoje: RecuperacaoHoje | None = None) -> tuple[list[CheckinTreino], int]:
    """Os check-ins a gerar, na ordem de atendimento, e quantos ficaram de fora (em dia ou nao elegiveis).

    Entram: sem linha, `sem_feedback` e desatualizados (com `refazer`, todos). Ordem: quem nunca foi tentado primeiro; depois
    por menos `tentativas`, para um treino que sempre reprova nao gastar o limite dos outros; empate: o mais recente primeiro.
    """
    linhas = session.execute(
        select(CheckinTreino, Atividade).join(Atividade, Atividade.id == CheckinTreino.atividade_id)
        .options(joinedload(CheckinTreino.feedback))
        .where(Atividade.atleta_id == atleta_id)
    ).unique().all()
    climas = _climas_do_atleta(session, atleta_id)
    entram, fora = [], 0
    for checkin, ativ in linhas:
        fb = checkin.feedback
        if not elegivel(ativ):
            fora += 1
        elif fb is None or refazer or fb.estado == "sem_feedback" or desatualizado(fb, checkin, versoes.fatos, _hoje(recuperacao_hoje, ativ), assinatura_clima(ativ, climas.get(ativ.id))):
            nunca = 0 if fb is None else 1
            tent = 0 if fb is None else fb.tentativas
            entram.append(((nunca, tent, -para_utc(ativ.inicio).timestamp()), checkin))
        else:
            fora += 1
    entram.sort(key=lambda x: x[0])
    return [c for _, c in entram], fora


def _gravar(session: Session, checkin: CheckinTreino, atualizado_em: datetime, *, estado: str, motivo: str | None,
            texto: str | None, provedor: str | None, modelo: str | None, versoes: Versoes, agora: datetime,
            recuperacao_em: datetime | None = None, clima_visto: str | None = None) -> None:
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
                tentativas=1, checkin_atualizado_em=atualizado_em, recuperacao_importada_em=recuperacao_em, clima_visto=clima_visto, tentado_em=agora,
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
    fb.recuperacao_importada_em = recuperacao_em
    fb.clima_visto = clima_visto
    session.commit()


def gerar(session: Session, atleta_id: int, redator: Redator, montar_pacote: MontarPacote, checar: Checar,
          versoes: Versoes, prompt: str, refazer: bool = False, agora: datetime | None = None,
          recuperacao_hoje: RecuperacaoHoje | None = None) -> RelatorioFeedback:
    """Gera (ou refaz) o feedback dos check-ins do atleta, dentro do limite de chamadas do `redator`. Idempotente: sem mudanca
    nova, nao ha fila e nao ha chamada. Um `commit` por feedback. Nunca levanta por causa do provedor."""
    rel = RelatorioFeedback()
    checkins, rel.ignorados = fila(session, atleta_id, versoes, refazer, recuperacao_hoje)
    climas = _climas_do_atleta(session, atleta_id)
    for n, checkin in enumerate(checkins):
        if redator.configurado and redator.chamadas >= redator.limite_chamadas:
            rel.adiados = len(checkins) - n  # sem linha nova; entram na proxima execucao
            break
        atualizado_em = checkin.atualizado_em  # o que o pacote vai refletir
        recuperacao_em = None if recuperacao_hoje is None else recuperacao_hoje(checkin.atividade)  # a noite que o pacote usa
        clima_visto = assinatura_clima(checkin.atividade, climas.get(checkin.atividade.id))  # o clima que o pacote vai usar
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
        manter = fb_antes is not None and fb_antes.estado == "pronto" and not desatualizado(fb_antes, checkin, versoes.fatos, _hoje(recuperacao_hoje, checkin.atividade), clima_visto)
        res = redator.redigir(prompt, pacote)
        if res.texto is None and getattr(redator, "limite_do_provedor", False):  # limite do provedor: nada gravado, o resto fica para depois
            rel.adiados = len(checkins) - n
            rel.limite_do_provedor = True
            break
        momento = agora or datetime.now(timezone.utc)

        def grava(estado: str, motivo: str | None, texto: str | None) -> None:
            _gravar(session, checkin, atualizado_em, estado=estado, motivo=motivo, texto=texto, provedor=res.provedor,
                    modelo=res.modelo, versoes=versoes, agora=momento, recuperacao_em=recuperacao_em, clima_visto=clima_visto)

        def mantem_ou_cai() -> bool | None:
            """A nova tentativa falhou: o texto pronto antigo so fica se passar nas checagens ATUAIS com o pacote desta
            tentativa (#407). Passou: fica e `versao_checagens` vira a atual. Reprovou: a linha vira `sem_feedback`
            (`texto_reprovado`) e o codigo soma em `reprovacoes`. `True` = manteve, `False` = caiu, `None` = a checagem levantou (nada gravado)."""
            try:
                antigo = checar(pacote, fb_antes.texto) if len(fb_antes.texto) <= FEEDBACK_TEXTO_MAX else "tamanho"
            except Exception:  # noqa: BLE001
                session.rollback()
                rel.erros += 1
                return None
            if antigo is None:
                fb_antes.versao_checagens = versoes.checagens  # o texto foi conferido por ela; nao conta tentativa
                fb_antes.clima_visto = clima_visto  # linha anterior a 0015 (nulo) passa a comparar o clima daqui em diante
                session.commit()
                rel.mantidos += 1
                return True
            else:
                grava("sem_feedback", "texto_reprovado", None)
                rel.sem_feedback += 1
                rel.mantido_reprovado += 1
                codigo_antigo = str(antigo) if _CODIGO.fullmatch(str(antigo)) else "outro"
                rel.reprovacoes[codigo_antigo] = rel.reprovacoes.get(codigo_antigo, 0) + 1
                return False

        if res.texto is None:
            if manter:
                mantido = mantem_ou_cai()
                if mantido is None:
                    continue
                if not mantido:  # o texto antigo caiu: o motivo da linha e o da reprovacao
                    rel.motivos["texto_reprovado"] = rel.motivos.get("texto_reprovado", 0) + 1
                    continue
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
            codigo = str(reprovado) if _CODIGO.fullmatch(str(reprovado)) else "outro"  # nunca texto livre nem o termo
            rel.reprovacoes[codigo] = rel.reprovacoes.get(codigo, 0) + 1
            if manter:
                mantido = mantem_ou_cai()
                if mantido is None:
                    continue
            else:
                grava("sem_feedback", "texto_reprovado", None)
                rel.sem_feedback += 1
            rel.motivos["texto_reprovado"] = rel.motivos.get("texto_reprovado", 0) + 1
            continue
        grava("pronto", None, res.texto)
        rel.gerados += 1
    return rel
