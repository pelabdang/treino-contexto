"""Contas, senha e sessao (issue #499, ADR 0016, itens 1 a 3 e 6).

- Senha: Argon2id (`argon2-cffi`); minimo de 10 caracteres, maximo de 128, sem regra de composicao; recusa uma lista curta de senhas
  comuns e a senha igual ao e-mail. Nunca vai a log, a erro nem a resposta.
- Sessao: token opaco de 32 bytes; so o SHA-256 dele fica no banco; vale 30 dias fixos; sair, trocar a senha e desativar revogam.
- Forca bruta: 5 falhas em 15 minutos por e-mail (guardado como hash) travam o `entrar`, ate com a senha certa. Sem IP.
- Resposta uniforme: e-mail inexistente, senha errada e conta desativada levantam o mesmo `CredencialInvalida`, e o e-mail
  inexistente tambem gasta um hash, para o tempo nao dizer quais e-mails existem.
Nada daqui escreve em log. As datas sao UTC com fuso; o relogio entra por parametro (`agora`).
"""

from __future__ import annotations

import hashlib
import math
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db.models import Conta, Sessao, TentativaLogin
from app.ingestao.garmin.unidades import para_utc

SESSAO_DIAS = 30
FALHAS_MAX = 5
JANELA_FALHAS = timedelta(minutes=15)
SENHA_MIN = 10
SENHA_MAX = 128

SENHAS_COMUNS = frozenset({
    "1234567890", "12345678910", "0123456789", "123456789012", "1q2w3e4r5t", "qwertyuiop", "qwerty1234", "qwerty12345",
    "senha12345", "senha123456", "password12", "password123", "password1234", "passw0rd123", "abcd123456", "abc1234567",
    "1234512345", "0000000000", "1111111111", "aaaaaaaaaa", "iloveyou123", "treino1234", "treino12345", "corrida1234",
    "mudar12345", "trocar12345", "administrador", "welcome123", "letmein1234", "football123", "brasil1234", "brasil12345",
})

_ph = PasswordHasher()
_hash_falso: str | None = None


class CredencialInvalida(Exception):
    """E-mail inexistente, senha errada ou conta desativada: a mesma resposta nos tres casos."""


class ForcaBruta(Exception):
    def __init__(self, espere_s: int) -> None:
        super().__init__("muitas tentativas")
        self.espere_s = espere_s


class SenhaInvalida(Exception):
    """A senha nova nao serve. `motivo` e um codigo fixo, nunca um trecho da senha."""

    def __init__(self, motivo: str) -> None:
        super().__init__(motivo)
        self.motivo = motivo


class SenhaAtualIncorreta(Exception):
    pass


class ContaInvalida(Exception):
    """Erro de quem opera (e-mail repetido, papel que nao existe...). Mensagem fixa, sem e-mail."""


def normalizar_email(email: str) -> str:
    return email.strip().lower()


def hash_do_email(email: str) -> str:
    return hashlib.sha256(normalizar_email(email).encode()).hexdigest()


def hash_do_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def validar_senha(senha: str, email: str | None = None) -> None:
    if len(senha) < SENHA_MIN:
        raise SenhaInvalida("curta")
    if len(senha) > SENHA_MAX:
        raise SenhaInvalida("longa")
    if senha.lower() in SENHAS_COMUNS:
        raise SenhaInvalida("comum")
    if email is not None and senha.lower() == normalizar_email(email):
        raise SenhaInvalida("igual_ao_email")


def _gerar_hash(senha: str) -> str:
    return _ph.hash(senha)


def _confere(hash_: str, senha: str) -> bool:
    try:
        return _ph.verify(hash_, senha)
    except (VerificationError, InvalidHashError):
        return False


def _gastar_um_hash(senha: str) -> None:
    global _hash_falso
    if _hash_falso is None:
        _hash_falso = _ph.hash("senha-falsa-fixa-para-gastar-tempo")
    _confere(_hash_falso, senha)


def senha_temporaria() -> str:
    return secrets.token_urlsafe(12)


def agora_utc() -> datetime:
    return datetime.now(timezone.utc)


# ---------- contas (comandos do operador) ----------

def criar_conta(session: Session, email: str, senha: str, *, atleta_id: int | None = None, professor_id: int | None = None,
                deve_trocar_senha: bool = False, agora: datetime | None = None) -> Conta:
    """Um papel por conta. Nao faz commit. `ContaInvalida` com texto fixo; `SenhaInvalida` com o codigo."""
    from app.db.models import Atleta, Professor

    email = normalizar_email(email)
    if "@" not in email or len(email) > 254 or email.startswith("@") or email.endswith("@"):
        raise ContaInvalida("e-mail invalido")
    if (atleta_id is None) == (professor_id is None):
        raise ContaInvalida("informe o atleta ou o professor, um so")
    validar_senha(senha, email)
    if atleta_id is not None and session.get(Atleta, atleta_id) is None:
        raise ContaInvalida("atleta nao encontrado")
    if professor_id is not None and session.get(Professor, professor_id) is None:
        raise ContaInvalida("professor nao encontrado")
    if session.scalar(select(Conta.id).where(Conta.email == email)) is not None:
        raise ContaInvalida("ja existe uma conta com esse e-mail")
    papel = Conta.atleta_id if atleta_id is not None else Conta.professor_id
    if session.scalar(select(Conta.id).where(papel == (atleta_id if atleta_id is not None else professor_id))) is not None:
        raise ContaInvalida("esse atleta ou professor ja tem conta")
    c = Conta(email=email, senha_hash=_gerar_hash(senha), atleta_id=atleta_id, professor_id=professor_id, ativa=True,
              deve_trocar_senha=deve_trocar_senha, criada_em=agora or agora_utc())
    session.add(c)
    session.flush()
    return c


def conta_por_email(session: Session, email: str) -> Conta | None:
    return session.scalar(select(Conta).where(Conta.email == normalizar_email(email)))


def revogar_todas(session: Session, conta_id: int, agora: datetime) -> int:
    n = 0
    for s in session.scalars(select(Sessao).where(Sessao.conta_id == conta_id, Sessao.revogada_em.is_(None))):
        s.revogada_em = agora
        n += 1
    return n


def redefinir_senha(session: Session, conta: Conta, agora: datetime | None = None) -> str:
    """Senha temporaria aleatoria (devolvida uma vez, para o operador mostrar), `deve_trocar_senha` ligado e todas as sessoes revogadas."""
    agora = agora or agora_utc()
    nova = senha_temporaria()
    conta.senha_hash = _gerar_hash(nova)
    conta.deve_trocar_senha = True
    conta.senha_trocada_em = agora
    revogar_todas(session, conta.id, agora)
    return nova


def desativar(session: Session, conta: Conta, agora: datetime | None = None) -> None:
    conta.ativa = False
    revogar_todas(session, conta.id, agora or agora_utc())


def limpar_expiradas(session: Session, agora: datetime | None = None) -> tuple[int, int]:
    """Apaga sessoes expiradas ou revogadas e tentativas de login com mais de 30 dias. Devolve (sessoes, tentativas)."""
    agora = agora or agora_utc()
    s = session.execute(delete(Sessao).where((Sessao.expira_em < agora) | (Sessao.revogada_em.is_not(None)))).rowcount
    t = session.execute(delete(TentativaLogin).where(TentativaLogin.ocorrida_em < agora - timedelta(days=30))).rowcount
    return s, t


# ---------- sessao ----------

@dataclass(frozen=True)
class Acesso:
    token: str
    expira_em: datetime


def _nova_sessao(session: Session, conta_id: int, agora: datetime) -> Acesso:
    token = secrets.token_urlsafe(32)
    expira = agora + timedelta(days=SESSAO_DIAS)
    session.add(Sessao(conta_id=conta_id, token_hash=hash_do_token(token), criada_em=agora, expira_em=expira))
    return Acesso(token, expira)


def _espera(session: Session, email_hash: str, agora: datetime) -> int:
    """Segundos ate poder tentar de novo; 0 se nao esta travado."""
    desde = agora - JANELA_FALHAS
    quando = sorted(para_utc(t) for t in session.scalars(
        select(TentativaLogin.ocorrida_em).where(TentativaLogin.email_hash == email_hash, TentativaLogin.ok.is_(False),
                                                 TentativaLogin.ocorrida_em > desde)))
    if len(quando) < FALHAS_MAX:
        return 0
    liberar = quando[-FALHAS_MAX] + JANELA_FALHAS  # a mais antiga das cinco ultimas falhas sai da janela
    return max(1, math.ceil((liberar - agora).total_seconds()))


def entrar(session: Session, email: str, senha: str, agora: datetime | None = None) -> tuple[Conta, Acesso]:
    """`ForcaBruta` (429) ou `CredencialInvalida` (401); nos dois casos nada diz se o e-mail existe. Nao faz commit."""
    agora = agora or agora_utc()
    eh = hash_do_email(email)
    espera = _espera(session, eh, agora)
    if espera:
        raise ForcaBruta(espera)
    conta = conta_por_email(session, email)
    if conta is None:
        _gastar_um_hash(senha)
        ok = False
    else:
        ok = _confere(conta.senha_hash, senha) and bool(conta.ativa)
    if not ok:
        session.add(TentativaLogin(email_hash=eh, ocorrida_em=agora, ok=False))
        session.flush()
        raise CredencialInvalida()
    session.execute(delete(TentativaLogin).where(TentativaLogin.email_hash == eh))
    if _ph.check_needs_rehash(conta.senha_hash):
        conta.senha_hash = _gerar_hash(senha)
    return conta, _nova_sessao(session, conta.id, agora)


def conta_da_sessao(session: Session, token: str, agora: datetime | None = None) -> tuple[Conta, Sessao] | None:
    """A conta e a sessao do token, se a sessao nao expirou, nao foi revogada e a conta esta ativa."""
    agora = agora or agora_utc()
    s = session.scalar(select(Sessao).where(Sessao.token_hash == hash_do_token(token)))
    if s is None or s.revogada_em is not None or para_utc(s.expira_em) <= agora:
        return None
    conta = session.get(Conta, s.conta_id)
    if conta is None or not conta.ativa:
        return None
    return conta, s


def sair(sessao: Sessao, agora: datetime | None = None) -> None:
    sessao.revogada_em = agora or agora_utc()


def trocar_senha(session: Session, conta: Conta, senha_atual: str, senha_nova: str, agora: datetime | None = None) -> Acesso:
    """Revoga TODAS as sessoes (a atual inclusive) e devolve um acesso novo. `SenhaAtualIncorreta` e `SenhaInvalida` nao mudam nada."""
    agora = agora or agora_utc()
    if not _confere(conta.senha_hash, senha_atual):
        raise SenhaAtualIncorreta()
    validar_senha(senha_nova, conta.email)
    if senha_nova == senha_atual:
        raise SenhaInvalida("igual_a_atual")
    conta.senha_hash = _gerar_hash(senha_nova)
    conta.deve_trocar_senha = False
    conta.senha_trocada_em = agora
    revogar_todas(session, conta.id, agora)
    return _nova_sessao(session, conta.id, agora)
