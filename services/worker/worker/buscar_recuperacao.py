"""Busca sono, VFC noturna e FC de repouso no Garmin Connect e guarda por noite (issue #372, ADR 0014, item 5).

    uv run python -m worker.buscar_recuperacao --atleta "<nome>" [--desde AAAA-MM-DD] [--ate AAAA-MM-DD]
    uv run python -m worker.buscar_recuperacao --atleta "<nome>" --fixtures <pasta> [--alinhar-ao-treino <fonte_id>] [--desde ..] [--ate ..]

`--fixtures` (#397) carrega noites SINTETICAS de uma pasta de respostas do sono (`tests/fixtures/meta10/...`) com o leitor de
verdade (`ler_noite`), sem rede, sem login e sem token: o `ClienteGarminConnect` nem e criado e `.env`/token nao sao lidos. Grava com
`versao_leitura = "fixture"`. Recusa (codigo 1, mensagem fixa) atleta que ja tem alguma noite que nao seja de fixture, para nunca
misturar dado sintetico com dado real. `--alinhar-ao-treino` leva a ultima noite da pasta para o dia local daquele treino (as outras
vao junto). Sem `--desde`/`--ate`, busca todas as noites da pasta. A saida continua so de contagens.

So local, na conta do proprio atleta, com a mesma biblioteca nao oficial e o mesmo token do `worker.buscar_garmin` (nao
rodar os dois ao mesmo tempo). UM login por execucao. Guarda so tres numeros por noite (`recuperacao_dia`); dado de saude:
a saida tem so contagens e codigos, NUNCA valor, data, resposta ou nome de campo, e nada vai para log.

As TRES medidas vem da MESMA resposta do sono (`get_sleep_data`, uma chamada por noite, em ordem crescente, pausa de 1,5 s,
teto de 130 chamadas por execucao). Datas: primeira rodada (o atleta nao tem nenhuma noite): do treino mais antigo com
check-in menos 28 noites ate hoje, no minimo 35 e no maximo 120 noites. Depois: de `min(ultima noite - 2, noite mais antiga
com buraco nos ultimos 14 dias)` ate hoje, no maximo 60 noites; buraco = noite que ja passou e tem linha com alguma medida
vazia, ou nao tem linha (veja `escolher_faixa`). `--desde` e `--ate` sobrepoem (e `--desde` passa do teto de noites).

Idempotente (*upsert* por atleta, origem e noite; `importado_em` so muda quando um valor muda; valor nulo nunca apaga). A FC
de repouso e a do DIA: so se grava quando a noite ja passou (hoje a medida fica vazia e entra na rodada seguinte).

Codigos de saida: 0 ok; 1 configuracao ou argumento; 2 login ou sessao recusados; 3 MFA; 4 limite (429, para a execucao e
preserva o gravado); 5 rede; 6 outro erro do Garmin. Precedencia 4 > 5 > 6.
"""

from __future__ import annotations

import argparse
import sys
import time
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from app.db.models import Atividade, Atleta, CheckinTreino
from app.servicos import recuperacao_banco as banco
from app.servicos.fuso import FUSO_PADRAO, data_local
from sqlalchemy import select
from sqlalchemy.orm import Session

from worker.garmin_cliente import (
    VERSAO_LEITURA,
    ClienteGarmin,
    VERSAO_FIXTURE,
    ClienteFixtures,
    ClienteGarminConnect,
    ErroConfiguracao,
    ErroGarmin,
    ErroLimite,
    ErroLogin,
    ErroMfa,
)

MARGEM_NOITES = 28  # o normal de um treino em D usa as noites D-28 a D-1
MINIMO_NOITES, TETO_NOITES_PRIMEIRA, TETO_NOITES_SEGUINTE = 35, 120, 60
RECUO_SEGUINTES = 2  # rebusca as duas ultimas noites (sincronizacao atrasada)
TETO_CHAMADAS = 130  # `get_sleep_data` e por noite; cobre a primeira rodada de ate 120 noites (adendo 1 ao item 5 da ADR 0014)
JANELA_BURACOS = 14  # dias: so ate aqui uma noite com buraco puxa o inicio da rodada (evita rebuscar para sempre)
FALHAS_SEGUIDAS_MAX = 3  # a execucao para depois de tantas falhas seguidas (rede fora, erro persistente)
PAUSA_S = 1.5


@dataclass
class RelatorioRecuperacao:
    noites_novas: int = 0
    atualizadas: int = 0
    iguais: int = 0
    sem_dado: int = 0
    falhas: int = 0  # chamadas que falharam
    rebuscadas: int = 0  # noites antes de `ultima - 2` que a rodada refez por causa de um buraco (so a contagem)
    avisos: list[str] = field(default_factory=list)  # so contagens e codigos
    codigo: int = 0


def hoje_local() -> date:
    return datetime.now(FUSO_PADRAO).date()


def _noite_mais_antiga_com_buraco(session: Session, atleta_id: int, hoje: date) -> date | None:
    """Regra simples contra a rebusca sem fim (Theo, #388): so olha as ultimas `JANELA_BURACOS` noites que JA PASSARAM
    (`hoje - 14` a `hoje - 1`) e nunca antes da primeira noite gravada. Conta como buraco a noite com linha incompleta (alguma
    medida vazia: o Garmin pode completar depois, ou era a FC de repouso de uma noite que ainda nao tinha passado) e a noite
    sem linha (falha ou resposta vazia: nao da para distinguir). Uma noite que o Garmin realmente nao tem so e refeita
    enquanto estiver dentro dessa janela; depois ela sai e deixa de puxar a rodada. Devolve a mais antiga, ou `None`."""
    primeira = banco.primeira_noite(session, atleta_id)
    if primeira is None:
        return None
    ini, fim = max(hoje - timedelta(days=JANELA_BURACOS), primeira), hoje - timedelta(days=1)
    gravadas = banco.noites_do_atleta(session, atleta_id, ini, fim)
    dia = ini
    while dia <= fim:
        n = gravadas.get(dia)
        if n is None or None in (n.sono_s, n.vfc_ms, n.fc_repouso_bpm):
            return dia
        dia += timedelta(days=1)
    return None


def escolher_faixa(session: Session, atleta_id: int, hoje: date, desde: date | None, ate: date | None) -> tuple[date, date, list[str]]:
    """A faixa de noites a buscar (ADR 0014, item 5). Devolve `(desde, ate, avisos)`."""
    avisos: list[str] = []
    fim = ate or hoje
    if desde is not None:
        return desde, fim, avisos
    ultima = banco.ultima_noite(session, atleta_id)
    if ultima is not None:  # rodadas seguintes
        ini = ultima - timedelta(days=RECUO_SEGUINTES)
        buraco = _noite_mais_antiga_com_buraco(session, atleta_id, hoje)
        if buraco is not None and buraco < ini:
            ini = buraco
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


def _pior(atual: int, novo: int) -> int:
    ordem = {0: 0, 6: 1, 5: 2, 4: 3}  # precedencia 4 > 5 > 6
    return novo if ordem.get(novo, 1) > ordem.get(atual, 0) else atual


def buscar(session: Session, cliente: ClienteGarmin, atleta_id: int, desde: date, ate: date, hoje: date,
           agora: datetime | None = None, pausa=time.sleep, versao_leitura: str = VERSAO_LEITURA) -> RelatorioRecuperacao:
    """Uma chamada por noite, em ordem crescente; cada noite e gravada e confirmada. Nunca levanta `ErroGarmin`: devolve o codigo."""
    rel = RelatorioRecuperacao()
    agora = agora or datetime.now(timezone.utc)
    chamadas = seguidas = 0
    dia = desde
    while dia <= ate:
        if chamadas >= TETO_CHAMADAS:
            rel.avisos.append("teto_chamadas")
            break
        if chamadas:
            pausa(PAUSA_S)
        chamadas += 1
        try:
            n = cliente.recuperacao(dia)
        except ErroGarmin as e:  # login, MFA, limite, rede ou outro: a mensagem do erro nunca e usada
            rel.falhas += 1
            rel.codigo = _pior(rel.codigo, e.codigo)
            seguidas += 1
            if isinstance(e, (ErroLogin, ErroMfa, ErroLimite)) or seguidas >= FALHAS_SEGUIDAS_MAX:
                if not isinstance(e, (ErroLogin, ErroMfa, ErroLimite)):
                    rel.avisos.append("parou_por_falhas_seguidas")
                break  # o 429 e o login recusado param a execucao; o gravado fica
            dia += timedelta(days=1)
            continue
        seguidas = 0
        fc = None if dia >= hoje else n.fc_repouso_bpm  # a FC de repouso e a do DIA: so vale quando a noite ja passou
        r = banco.gravar_noite(session, atleta_id, dia, n.sono_s, n.vfc_ms, fc, versao_leitura, agora)
        if r == "nova":
            rel.noites_novas += 1
        elif r == "atualizada":
            rel.atualizadas += 1
        elif r == "igual":
            rel.iguais += 1
        else:  # a resposta nao trouxe nenhuma medida e nao havia linha
            rel.sem_dado += 1
        session.commit()
        dia += timedelta(days=1)
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
    p.add_argument("--fixtures", type=Path, help="pasta de respostas sinteticas do sono: carrega sem rede, sem login e sem token")
    p.add_argument("--alinhar-ao-treino", metavar="FONTE_ID",
                   help="com --fixtures: leva a ultima noite da pasta para o dia local deste treino (fonte_id da atividade)")
    args = p.parse_args(argv)
    if args.alinhar_ao_treino and not args.fixtures:
        print("erro: --alinhar-ao-treino so vale com --fixtures", file=sys.stderr)
        return 1

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
            versao = VERSAO_LEITURA
            if args.fixtures:
                cliente = ClienteFixtures.de_pasta(args.fixtures)  # sem rede, sem login, sem token
                if banco.ha_noite_de_outra_versao(session, atleta.id, VERSAO_FIXTURE):
                    print("erro: o atleta ja tem noites que nao sao de fixture; --fixtures so grava em banco de teste", file=sys.stderr)
                    return 1
                if args.alinhar_ao_treino:
                    ativ = session.scalars(select(Atividade).where(Atividade.atleta_id == atleta.id,
                                                                   Atividade.fonte_id == args.alinhar_ao_treino)).first()
                    if ativ is None:
                        print("erro: treino nao encontrado", file=sys.stderr)
                        return 1
                    cliente = cliente.com_deslocamento(data_local(ativ.inicio, ativ.fuso_min) - cliente.faixa()[1])
                primeira, ultima_fx = cliente.faixa()
                desde, ate, avisos = args.desde or primeira, args.ate or ultima_fx, []
                dia = ate + timedelta(days=1)  # sintetica: toda noite conta como ja passada (a FC de repouso e gravada)
                versao, pausa = VERSAO_FIXTURE, (lambda s: None)
            else:
                desde, ate, avisos = escolher_faixa(session, atleta.id, dia, args.desde, args.ate)
            if desde > ate:
                print("erro: faixa vazia (--desde depois de --ate)", file=sys.stderr)
                return 1
            if cliente is None:
                cliente = ClienteGarminConnect.entrar(env)  # a unica tentativa de login; antes de qualquer gravacao
            ultima = banco.ultima_noite(session, atleta.id) if args.desde is None and not args.fixtures else None
            rel = buscar(session, cliente, atleta.id, desde, ate, dia, agora=agora, pausa=pausa, versao_leitura=versao)
            rel.avisos[:0] = avisos
            if ultima is not None and desde < ultima - timedelta(days=RECUO_SEGUINTES):
                rel.rebuscadas = (ultima - timedelta(days=RECUO_SEGUINTES) - desde).days
    except ErroGarmin as e:  # login, MFA ou configuracao: mensagem fixa, nada gravado
        print(f"erro: {e}", file=sys.stderr)
        return e.codigo

    print(f"recuperacao: noites_novas={rel.noites_novas} atualizadas={rel.atualizadas} iguais={rel.iguais} "
          f"sem_dado={rel.sem_dado} falhas={rel.falhas}")
    if rel.rebuscadas:
        print(f"  aviso: rebuscadas={rel.rebuscadas}")  # so a contagem de noites refeitas por buraco, nunca as datas
    for aviso in rel.avisos:
        print(f"  aviso: {aviso}")
    return rel.codigo


if __name__ == "__main__":
    sys.exit(main())
