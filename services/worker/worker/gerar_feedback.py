"""Gera o feedback automatico dos treinos de um atleta (issue #327, ADR 0013 itens 2 a 4).

    uv run python -m worker.gerar_feedback --atleta "<nome>" [--limite N] [--refazer]

Para cada check-in sem feedback, com feedback `sem_feedback` ou desatualizado (o check-in foi editado ou a `fatos_treino` mudou):
monta o pacote de fatos, pede o texto a camada de LLM (`app.llm`), passa pelas checagens e grava em `feedback_treino`. Texto
reprovado NUNCA e gravado (so o motivo `texto_reprovado`). No maximo N chamadas ao provedor por execucao (`--limite`, senao
`LLM_LIMITE_CHAMADAS`, padrao 20); as que sobram entram na proxima execucao. Idempotente: sem mudanca nova, nenhuma chamada.
`--refazer` refaz tambem o que esta pronto e em dia (ainda dentro do limite).

Esta e a UNICA execucao que chama o provedor. Com `LLM_PROVIDER=groq` o pacote (dado de saude) sai da maquina: so no computador
do proprio atleta, com o "sim" dele (ADR 0013, decisao 9). Saida: so contagens e codigos de motivo, nunca texto nem pacote.

Codigos de saida: 0 ok; 1 atleta inexistente ou pacote e checagens (#324 e #325) indisponiveis.
"""

from __future__ import annotations

import argparse
import sys

from app.db.models import Atleta
from app.llm import Redator, criar_redator
from app.llm import prompt_feedback
from app.servicos.feedback import Versoes, gerar
from sqlalchemy import select


def _padroes():
    """Pacote de fatos (#324, pelo adaptador que le o banco) e checagens (#325). Falta um deles: `None`."""
    try:
        from app.explicacao import checagens, fatos_treino
        from app.servicos.feedback_fatos import fatos_da_atividade

        return fatos_da_atividade, checagens.checar, fatos_treino.VERSAO, checagens.VERSAO
    except (ImportError, AttributeError):
        return None


def main(argv: list[str] | None = None, redator: Redator | None = None, montar_pacote=None, checar=None,
         versoes: Versoes | None = None, session_factory=None) -> int:
    p = argparse.ArgumentParser(prog="python -m worker.gerar_feedback",
                                description="Gera o feedback automatico dos treinos de um atleta.")
    p.add_argument("--atleta", required=True, help="nome do atleta")
    p.add_argument("--limite", type=int, help="maximo de chamadas ao provedor nesta execucao (padrao: LLM_LIMITE_CHAMADAS)")
    p.add_argument("--refazer", action="store_true", help="refaz tambem o feedback pronto e em dia")
    args = p.parse_args(argv)
    if args.limite is not None and args.limite < 0:
        print("erro: --limite nao pode ser negativo", file=sys.stderr)
        return 1

    if montar_pacote is None or checar is None or versoes is None:
        padroes = _padroes()
        if padroes is None:
            print("erro: o pacote de fatos e as checagens do feedback ainda nao estao disponiveis", file=sys.stderr)
            return 1
        montar_pacote, checar = montar_pacote or padroes[0], checar or padroes[1]
        versoes = versoes or Versoes(fatos=padroes[2], prompt=prompt_feedback.VERSAO, checagens=padroes[3])

    if session_factory is None:
        from app.db.session import SessionLocal as session_factory  # usa DATABASE_URL

    with session_factory() as session:
        atletas = session.scalars(select(Atleta).where(Atleta.nome == args.atleta).order_by(Atleta.id)).all()
        if not atletas:
            print("erro: atleta nao encontrado", file=sys.stderr)
            return 1
        if len(atletas) > 1:
            print(f"aviso: {len(atletas)} atletas com esse nome; usado o de menor id", file=sys.stderr)
        redator = redator or criar_redator()
        if args.limite is not None:
            redator.limite_chamadas = args.limite
        rel = gerar(session, atletas[0].id, redator, montar_pacote, checar, versoes, prompt_feedback.TEXTO,
                    refazer=args.refazer)

    print(f"feedback: gerados={rel.gerados} sem_feedback={rel.sem_feedback} ignorados={rel.ignorados}"
          f" adiados={rel.adiados} erros={rel.erros}" + (f" mantidos={rel.mantidos}" if rel.mantidos else ""))
    for nome, mapa in (("motivos", rel.motivos), ("reprovacoes", rel.reprovacoes)):
        if mapa:
            print(f"  {nome}: " + " ".join(f"{k}={v}" for k, v in sorted(mapa.items())))
    if rel.limite_do_provedor:
        print("aviso: o provedor recusou por limite de requisicoes; rode de novo mais tarde (limite por minuto: 1 minuto basta, ou use LLM_INTERVALO_S; limite diario: so no dia seguinte)",
              file=sys.stderr)
    if not redator.configurado:
        print("aviso: provedor de LLM nao configurado (LLM_PROVIDER, LLM_MODEL e a chave no .env)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
