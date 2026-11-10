"""Busca as atividades do Garmin Connect e as importa, sem subir FIT a mao (issue #335, paralela da Meta 9).

    uv run python -m worker.buscar_garmin --atleta "<nome>" [--desde AAAA-MM-DD] [--ate AAAA-MM-DD] [--sem-clima]

Padrao: hoje. So local, na conta do proprio atleta. Biblioteca nao oficial (`garminconnect`): pode quebrar quando o
Garmin mudar o login; a API oficial segue sendo o caminho de producao. Veja `worker.garmin_cliente` e a nota do modulo.

Cada FIT original passa por `app.ingestao.importacao.importar_fit`, o MESMO caminho do upload de FIT da Meta 3
(identidade, guarda do arquivo, esforcos, tipo), e depois pelo clima e pela carga, como na importacao da exportacao.
Idempotente: uma atividade cujo inicio ja esta no banco (a ate 60 s, regra da ADR 0006) nem e baixada; e se for, o
`importar_fit` reconhece e nao duplica. Sem mudanca no modelo de dados.

Codigos de saida: 0 ok; 1 configuracao ou argumento; 2 login recusado; 3 MFA pedido; 4 limite de requisicoes;
5 rede; 6 outro erro do Garmin ou atividades que falharam. Credenciais e token nunca vao para log nem mensagem.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path

from app.db.models import Atividade, Atleta
from app.ingestao.fit_guardado import AtletaInexistente
from app.ingestao.garmin.leitor import TOLERANCIA_S
from app.ingestao.garmin.unidades import para_utc
from app.ingestao.importacao import FitInvalido, RelatorioImportacao, importar_fit
from sqlalchemy import select
from sqlalchemy.orm import Session

from worker.garmin_cliente import (
    AtividadeGarmin,
    ClienteGarmin,
    ClienteGarminConnect,
    ErroGarmin,
)
from worker.importar_garmin import carga_do_atleta, clima_do_que_mudou


@dataclass
class RelatorioBusca:
    listadas: int = 0
    ja_no_banco: int = 0  # nem baixadas
    inseridas: int = 0
    atualizadas: int = 0
    ignoradas: int = 0  # baixadas, mas ja estavam iguais no banco
    falhas: int = 0
    avisos: list[str] = field(default_factory=list)


# Parecido o bastante para ser a mesma atividade: os intervalos [inicio, inicio + duracao] coincidem em pelo menos
# 70% do maior deles (#342). Duas atividades diferentes nao se sobrepoem assim; uma atividade-pai de multiesporte e as
# filhas tambem nao (a filha e bem menor que a pai).
SOBREPOSICAO_MIN = 0.7
JANELA_BUSCA = timedelta(hours=6)  # so para limitar a consulta; a regra e a sobreposicao


def _mesma_pelo_intervalo(a: AtividadeGarmin, inicio_banco, duracao_banco: float) -> bool:
    """O inicio da lista pode diferir do do FIT em mais de 60 s (#342); o intervalo inteiro ainda quase coincide."""
    if not a.duracao_s or not duracao_banco:
        return False
    ini_a = para_utc(a.inicio_utc)
    ini_b = para_utc(inicio_banco)
    fim_a, fim_b = ini_a + timedelta(seconds=a.duracao_s), ini_b + timedelta(seconds=duracao_banco)
    comum = (min(fim_a, fim_b) - max(ini_a, ini_b)).total_seconds()
    return comum >= SOBREPOSICAO_MIN * max(a.duracao_s, duracao_banco)


def _ja_no_banco(session: Session, atleta_id: int, a: AtividadeGarmin) -> bool:
    """Ja ha uma atividade do atleta que esta lista representa? (1) inicio a ate 60 s, a regra da ADR 0006; (2) sem isso,
    o intervalo da lista quase coincide com o de uma atividade do banco. Sem mudanca no modelo e sem guardar o id do Garmin."""
    if a.inicio_utc is None:
        return False
    inicio = para_utc(a.inicio_utc)
    folga = timedelta(seconds=TOLERANCIA_S)
    if session.scalars(select(Atividade.id).where(
        Atividade.atleta_id == atleta_id, Atividade.inicio.between(inicio - folga, inicio + folga),
    ).limit(1)).first() is not None:
        return True
    if not a.duracao_s:
        return False
    fim = inicio + timedelta(seconds=a.duracao_s)
    candidatas = session.execute(select(Atividade.inicio, Atividade.duracao_s).where(
        Atividade.atleta_id == atleta_id, Atividade.inicio.between(inicio - JANELA_BUSCA, fim + JANELA_BUSCA),
    )).all()
    return any(_mesma_pelo_intervalo(a, ini, dur) for ini, dur in candidatas)


def _diferenca(session: Session, atividade_id: int, a: AtividadeGarmin) -> str:
    """So numeros (segundos de diferenca), nunca datas, ids do Garmin nem tipos."""
    ativ = session.get(Atividade, atividade_id)
    if ativ is None or a.inicio_utc is None:
        return "atividade baixada e ja existente (sem dados da lista para comparar)"
    d_ini = (para_utc(a.inicio_utc) - para_utc(ativ.inicio)).total_seconds()
    d_dur = "sem duracao na lista" if not a.duracao_s else f"duracao da lista {a.duracao_s - ativ.duracao_s:+.0f} s"
    return f"atividade baixada e ja existente: inicio da lista {d_ini:+.0f} s do FIT, {d_dur}"


def buscar(session: Session, cliente: ClienteGarmin, atleta_id: int, desde: date, ate: date,
           fit_dir: Path | None = None) -> tuple[RelatorioBusca, RelatorioImportacao]:
    """Lista, pula o que ja esta no banco, baixa e importa o resto. Erro de login, limite ou rede sobe como `ErroGarmin`."""
    rel = RelatorioBusca()
    alterados = RelatorioImportacao()
    atividades = cliente.listar(desde, ate)
    rel.listadas = len(atividades)
    for a in atividades:
        if _ja_no_banco(session, atleta_id, a):
            rel.ja_no_banco += 1
            continue
        conteudo = cliente.baixar_fit(a.id)
        try:
            r = importar_fit(session, atleta_id, conteudo, fit_dir)
        except (FitInvalido, ValueError):  # FIT que nao e atividade, corrompido ou grande demais
            rel.falhas += 1
            continue
        rel.avisos.extend(r.avisos)
        if r.resultado == "ignorada":  # baixada a toa: diz quanto a lista diferia do banco, para achar a causa (#342)
            rel.avisos.append(_diferenca(session, r.atividade_id, a))
        if r.resultado == "inserida":
            rel.inseridas += 1
        elif r.resultado == "atualizada":
            rel.atualizadas += 1
        else:
            rel.ignoradas += 1
        if r.resultado != "ignorada":
            alterados.ids_alterados.append(r.atividade_id)
    return rel, alterados


def _data(texto: str) -> date:
    try:
        return date.fromisoformat(texto)
    except ValueError:
        raise argparse.ArgumentTypeError("use o formato AAAA-MM-DD") from None


def main(argv: list[str] | None = None, cliente: ClienteGarmin | None = None, session_factory=None,
         clima_cliente=None, hoje: date | None = None, env: dict[str, str] | None = None, fit_dir: Path | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m worker.buscar_garmin",
                                description="Busca as atividades do Garmin Connect e importa (piloto local).")
    p.add_argument("--atleta", required=True, help="nome do atleta (precisa existir)")
    p.add_argument("--desde", type=_data, help="primeira data local, AAAA-MM-DD (padrao: hoje)")
    p.add_argument("--ate", type=_data, help="ultima data local, AAAA-MM-DD (padrao: hoje)")
    p.add_argument("--sem-clima", action="store_true", help="nao busca o clima no Open-Meteo")
    args = p.parse_args(argv)

    dia = hoje or date.today()
    desde, ate = args.desde or dia, args.ate or dia
    if desde > ate:
        print("erro: --desde depois de --ate", file=sys.stderr)
        return 1

    if session_factory is None:
        from app.db.session import SessionLocal as session_factory  # usa DATABASE_URL

    try:
        with session_factory() as session:
            atleta = session.scalars(select(Atleta).where(Atleta.nome == args.atleta).order_by(Atleta.id)).first()
            if atleta is None:
                print("erro: atleta nao encontrado (importe a exportacao antes ou crie o atleta)", file=sys.stderr)
                return 1
            atleta_id = atleta.id
            if cliente is None:
                cliente = ClienteGarminConnect.entrar(env)  # a unica tentativa de login da execucao
            rel, alterados = buscar(session, cliente, atleta_id, desde, ate, fit_dir)
    except AtletaInexistente:
        print("erro: atleta nao encontrado", file=sys.stderr)
        return 1
    except ErroGarmin as e:
        print(f"erro: {e}", file=sys.stderr)
        return e.codigo

    print(f"garmin: listadas={rel.listadas} ja_no_banco={rel.ja_no_banco} inseridas={rel.inseridas} "
          f"atualizadas={rel.atualizadas} ignoradas={rel.ignoradas} falhas={rel.falhas}")
    for aviso in rel.avisos:
        print(f"  aviso: {aviso}")
    if alterados.ids_alterados:
        carga_do_atleta(args.atleta, session_factory=session_factory)
        if not args.sem_clima:
            clima_do_que_mudou(alterados, cliente=clima_cliente, session_factory=session_factory)
    if rel.falhas:
        print("erro: alguma atividade nao pode ser importada (FIT invalido ou que nao e atividade)", file=sys.stderr)
        return ErroGarmin.codigo
    return 0


if __name__ == "__main__":
    sys.exit(main())
