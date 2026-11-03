"""Guarda local dos FIT enviados por upload (ADR 0006, item 3).

Arquivo em `FIT_DIR/<atleta_id>/<sha256 do conteudo>.fit`; `atividade.arquivo_bruto` leva o caminho relativo a
`FIT_DIR`. O nome enviado pelo cliente nunca e usado. Sem dado pessoal no nome.
"""

from __future__ import annotations

import hashlib
import os
import re
import tempfile
from pathlib import Path

from app.config import pasta_fit
from app.db.models import Atividade, Atleta
from sqlalchemy import select
from sqlalchemy.orm import Session

# `<atleta_id>/<64 hex>.fit`; um caminho de zip da exportacao tem `!/` e nunca casa.
PADRAO_GUARDADO = re.compile(r"^(\d+)/[0-9a-f]{64}\.fit$")


def caminho_relativo(atleta_id: int, conteudo: bytes) -> str:
    return f"{atleta_id}/{hashlib.sha256(conteudo).hexdigest()}.fit"


def esta_guardado(arquivo_bruto: str | None) -> bool:
    """O `arquivo_bruto` aponta para um arquivo de `FIT_DIR` (e nao para um caminho dentro da exportacao)?"""
    return bool(arquivo_bruto and PADRAO_GUARDADO.match(arquivo_bruto))


def gravar(relativo: str, conteudo: bytes, fit_dir: Path | None = None) -> bool:
    """Grava `relativo` em `FIT_DIR` (temporario + renomeacao). Devolve True se criou o arquivo, False se ja existia."""
    destino = pasta_fit(fit_dir) / relativo
    if destino.exists():
        return False
    destino.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, tmp = tempfile.mkstemp(dir=destino.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(conteudo)
        os.chmod(tmp, 0o600)
        os.replace(tmp, destino)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise
    return True


def existe(relativo: str, fit_dir: Path | None = None) -> bool:
    return (pasta_fit(fit_dir) / relativo).is_file()


def remover(relativo: str, fit_dir: Path | None = None) -> None:
    (pasta_fit(fit_dir) / relativo).unlink(missing_ok=True)


def ainda_referenciado(session: Session, relativo: str) -> bool:
    return session.scalars(select(Atividade.id).where(Atividade.arquivo_bruto == relativo).limit(1)).first() is not None


class AtletaInexistente(LookupError):
    pass


def apagar_do_atleta(session: Session, atleta_id: int, fit_dir: Path | None = None) -> tuple[int, int]:
    """Apaga os FIT guardados do atleta e limpa `arquivo_bruto`; as atividades ficam. Idempotente.

    Devolve (arquivos apagados, atividades com `arquivo_bruto` limpo).
    """
    if session.get(Atleta, atleta_id) is None:
        raise AtletaInexistente(f"atleta {atleta_id} não encontrado")
    pasta = pasta_fit(fit_dir) / str(atleta_id)
    arquivos = 0
    if pasta.is_dir():
        for f in pasta.glob("*.fit"):
            f.unlink()
            arquivos += 1
        if not any(pasta.iterdir()):
            pasta.rmdir()
    limpas = 0
    for a in session.scalars(select(Atividade).where(Atividade.atleta_id == atleta_id,
                                                      Atividade.arquivo_bruto.is_not(None))):
        m = PADRAO_GUARDADO.match(a.arquivo_bruto)
        if m and int(m.group(1)) == atleta_id:
            a.arquivo_bruto = None
            limpas += 1
    session.commit()
    return arquivos, limpas
