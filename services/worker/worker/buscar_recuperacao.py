"""Busca sono, VFC noturna e FC de repouso no Garmin Connect e guarda por noite (issue #372, ADR 0014, item 5).

    uv run python -m worker.buscar_recuperacao --atleta "<nome>" [--desde AAAA-MM-DD] [--ate AAAA-MM-DD]

So local, na conta do proprio atleta, com a mesma biblioteca nao oficial e o mesmo token do `worker.buscar_garmin` (nao
rodar os dois ao mesmo tempo). UM login por execucao. Guarda so tres numeros por noite (`recuperacao_dia`); dado de saude:
a saida tem so contagens e codigos, NUNCA valor, data, resposta ou nome de campo, e nada vai para log.

Datas: primeira rodada (o atleta nao tem nenhuma noite): do treino mais antigo com check-in menos 28 noites ate hoje, no
minimo 35 e no maximo 120 noites; depois: da ultima noite gravada menos 2 ate hoje, no maximo 60. `--desde` e `--ate`
sobrepoem (e `--desde` vai alem do teto de noites). Faixas de ate 28 dias, pausa entre chamadas, teto de 12 chamadas de
faixa (VFC e FC de repouso) por execucao. O sono so existe por dia (`get_sleep_data`): uma chamada por noite, com teto proprio.

Cada medida e pedida e gravada a parte; erro numa medida nao perde as outras. Idempotente (*upsert* por atleta, origem e
noite; `importado_em` so muda quando um valor muda; valor nulo nunca apaga). A FC de repouso e a do DIA: so se grava quando a
noite ja passou (hoje a medida fica vazia e entra na rodada seguinte).

Codigos de saida: 0 ok; 1 configuracao ou argumento; 2 login ou sessao recusados; 3 MFA; 4 limite (429, para a execucao e
preserva o gravado); 5 rede; 6 outro erro do Garmin. Precedencia 4 > 5 > 6.
"""

from __future__ import annotations

import argparse
import sys
import time
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone

from app.db.models import Atividade, Atleta, CheckinTreino
from app.servicos import recuperacao_banco as banco
from app.servicos.fuso import FUSO_PADRAO, data_local
from sqlalchemy import select
from sqlalchemy.orm import Session

from worker.garmin_cliente import (
    BLOCO_MAX_DIAS,
    VERSAO_LEITURA,
    ClienteGarmin,
    ClienteGarminConnect,
    ErroGarmin,
    ErroLimite,
    ErroLogin,
    ErroMfa,
)

MARGEM_NOITES = 28  # o normal de um treino em D usa as noites D-28 a D-1
MINIMO_NOITES, TETO_NOITES_PRIMEIRA, TETO_NOITES_SEGUINTE = 35, 120, 60
RECUO_SEGUINTES = 2  # rebusca as duas ultimas noites (sincronizacao atrasada)
TETO_CHAMADAS_FAIXA = 12  # VFC e FC de repouso, por execucao
TETO_CHAMADAS_SONO = 130  # `get_sleep_data` e por dia; cobre a primeira rodada de ate 120 noites
PAUSA_S = 1.5


@dataclass
class RelatorioRecuperacao:
    noites_novas: int = 0
    atualizadas: int = 0
    iguais: int = 0
    sem_dado: int = 0
    falhas: int = 0  # chamadas que falharam
    avisos: list[str] = field(default_factory=list)  # so contagens e codigos
    codigo: int = 0


def hoje_local() -> date:
    return datetime.now(FUSO_PADRAO).date()


def escolher_faixa(session: Session, atleta_id: int, hoje: date, desde: date | None, ate: date | None) -> tuple[date, date, list[str]]:
    """A faixa de noites a buscar (ADR 0014, item 5). Devolve `(desde, ate, avisos)`."""
    avisos: list[str] = []
    fim = ate or hoje
    if desde is not None:
        return desde, fim, avisos
    ultima = banco.ultima_noite(session, atleta_id)
    if ultima is not None:  # rodadas seguintes
        ini = ultima - timedelta(days=RECUO_SEGUINTES)
        if (fim - ini).days + 1 > TETO_NOITES_SEGUINTE:
            ini = fim - timedelta(days=TETO_NOITES_SEGUINTE - 1)
            avisos.append(f"faixa cortada no teto de {TETO_NOITES_SEGUINTE} noites; use --desde para ir alem")
        return ini, fim, avisos
    mais_antigo = None  # primeira rodada: a data local do treino mais antigo com check-in
    for inicio, fuso in session.execute(select(Atividade.inicio, Atividade.fuso_min).join(
            CheckinTreino, CheckinTreino.atividade_id == Atividade.id).where(Atividade.atleta_id == atleta_id)):
        d = data_local(inicio, fuso)
        mais_antigo = d if mais_antigo is None or d < mais_antigo else mais_antigo
    ini = fim - timedelta(days=MINIMO_NOITES - 1)
    if mais_antigo is not None:
        ini = min(ini, mais_antigo - timedelta(days=MARGEM_NOITES))
    if (fim - ini).days + 1 > TETO_NOITES_PRIMEIRA:
        ini = fim - timedelta(days=TETO_NOITES_PRIMEIRA - 1)
        avisos.append(f"faixa cortada no teto de {TETO_NOITES_PRIMEIRA} noites; use --desde para ir alem")
    return ini, fim, avisos


def _blocos(desde: date, ate: date):
    ini = desde
    while ini <= ate:
        fim = min(ini + timedelta(days=BLOCO_MAX_DIAS - 1), ate)
        yield ini, fim
        ini = fim + timedelta(days=1)


def _pior(atual: int, novo: int) -> int:
    ordem = {0: 0, 6: 1, 5: 2, 4: 3}  # precedencia 4 > 5 > 6
    return novo if ordem.get(novo, 1) > ordem.get(atual, 0) else atual


def buscar(session: Session, cliente: ClienteGarmin, atleta_id: int, desde: date, ate: date, hoje: date,
           agora: datetime | None = None, pausa=time.sleep) -> RelatorioRecuperacao:
    """Busca e grava, bloco a bloco (cada bloco e gravado e confirmado). Nunca levanta `ErroGarmin`: devolve o codigo."""
    rel = RelatorioRecuperacao()
    agora = agora or datetime.now(timezone.utc)
    chamadas = {"faixa": 0, "sono": 0}
    primeira = [True]
    falhou: set[str] = set()  # medidas que falharam: nao insiste nas chamadas seguintes desta execucao
    parar = False

    def chamar(medida: str, ini: date, fim: date):
        """Uma chamada ao cliente. Devolve `None` se nao pode ou falhou (conta a falha); `ErroLimite` para tudo."""
        nonlocal parar
        tipo = "sono" if medida == "sono" else "faixa"
        teto = TETO_CHAMADAS_SONO if tipo == "sono" else TETO_CHAMADAS_FAIXA
        if medida in falhou or parar:
            return None
        if chamadas[tipo] >= teto:
            if f"teto_{tipo}" not in rel.avisos:
                rel.avisos.append(f"teto_{tipo}")
            return None
        if not primeira[0]:
            pausa(PAUSA_S)
        primeira[0] = False
        chamadas[tipo] += 1
        try:
            return cliente.recuperacao(ini, fim, (medida,))
        except (ErroLogin, ErroMfa, ErroLimite) as e:  # sessao recusada ou 429 no meio da execucao: para tudo
            rel.falhas += 1
            rel.codigo = _pior(rel.codigo, e.codigo)
            parar = True
        except ErroGarmin as e:  # rede ou outro erro: esta medida nao insiste mais
            rel.falhas += 1
            rel.codigo = _pior(rel.codigo, e.codigo)
            falhou.add(medida)
        return None

    for ini, fim in _blocos(desde, ate):
        if parar:
            break
        valores: dict[str, dict[date, object]] = {"sono": {}, "vfc": {}, "fc": {}}
        consultadas: dict[str, set[date]] = {"sono": set(), "vfc": set(), "fc": set()}
        for medida in ("vfc", "fc"):
            noites = chamar(medida, ini, fim)
            if noites is not None:
                consultadas[medida].update(ini + timedelta(days=i) for i in range((fim - ini).days + 1))
                for n in noites:
                    valores[medida][n.noite] = n.vfc_ms if medida == "vfc" else n.fc_repouso_bpm
        dia = ini
        while dia <= fim and not parar:
            noites = chamar("sono", dia, dia)
            if noites is not None:
                consultadas["sono"].add(dia)
                for n in noites:
                    valores["sono"][n.noite] = n.sono_s
            elif "sono" in falhou:
                break
            dia += timedelta(days=1)
        dia = ini
        while dia <= fim:  # grava o bloco (inclusive o que veio antes de um 429)
            sono, vfc, fc = valores["sono"].get(dia), valores["vfc"].get(dia), valores["fc"].get(dia)
            if dia >= hoje:  # a FC de repouso e a do DIA: so vale quando a noite ja passou (ADR 0014, item 5)
                fc = None
            r = banco.gravar_noite(session, atleta_id, dia, sono, vfc, fc, VERSAO_LEITURA, agora)
            if r == "nova":
                rel.noites_novas += 1
            elif r == "atualizada":
                rel.atualizadas += 1
            elif r == "igual":
                rel.iguais += 1
            elif all(dia in consultadas[m] for m in consultadas):  # consultou as tres e nenhuma trouxe valor
                rel.sem_dado += 1
            dia += timedelta(days=1)
        session.commit()
    return rel


def _data(texto: str) -> date:
    try:
        return date.fromisoformat(texto)
    except ValueError:
        raise argparse.ArgumentTypeError("use o formato AAAA-MM-DD") from None


def main(argv: list[str] | None = None, cliente: ClienteGarmin | None = None, session_factory=None,
         hoje: date | None = None, env: dict[str, str] | None = None, pausa=time.sleep,
         agora: datetime | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m worker.buscar_recuperacao",
                                description="Busca sono, VFC noturna e FC de repouso no Garmin Connect (piloto local).")
    p.add_argument("--atleta", required=True, help="nome do atleta (precisa existir)")
    p.add_argument("--desde", type=_data, help="primeira noite, AAAA-MM-DD (vai alem do teto de noites)")
    p.add_argument("--ate", type=_data, help="ultima noite, AAAA-MM-DD (padrao: hoje)")
    args = p.parse_args(argv)

    dia = hoje or hoje_local()
    if args.desde and (args.ate or dia) < args.desde:
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
            desde, ate, avisos = escolher_faixa(session, atleta.id, dia, args.desde, args.ate)
            if desde > ate:
                print("erro: faixa vazia (--desde depois de --ate)", file=sys.stderr)
                return 1
            if cliente is None:
                cliente = ClienteGarminConnect.entrar(env)  # a unica tentativa de login; antes de qualquer gravacao
            rel = buscar(session, cliente, atleta.id, desde, ate, dia, agora=agora, pausa=pausa)
            rel.avisos[:0] = avisos
    except ErroGarmin as e:  # login, MFA ou configuracao: mensagem fixa, nada gravado
        print(f"erro: {e}", file=sys.stderr)
        return e.codigo

    print(f"recuperacao: noites_novas={rel.noites_novas} atualizadas={rel.atualizadas} iguais={rel.iguais} "
          f"sem_dado={rel.sem_dado} falhas={rel.falhas}")
    for aviso in rel.avisos:
        print(f"  aviso: {aviso}")
    return rel.codigo


if __name__ == "__main__":
    sys.exit(main())
