"""Helper unico dos testes de rota que nao tratam de login (ADR 0016, item 8).

`sem_login(app)` troca por sobrescrita de dependencia (`app.dependency_overrides`) as duas conferencias de sessao: o atleta e o
professor do caminho passam como se fossem o da sessao. Isso vale so para o `app` do teste: nao existe variavel nem flag no servidor
que desligue o login. Os testes de acesso (`test_acesso.py`) NAO usam este helper: entram com sessao de verdade.
"""

from __future__ import annotations

from app.autenticacao import PROFESSOR_INEXISTENTE, atleta_da_sessao, professor_da_sessao
from app.db.models import Professor
from app.db.session import get_session
from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session


def sem_login(app):
    def atleta(atleta_id: int) -> int:
        return atleta_id

    def professor(professor_id: int, session: Session = Depends(get_session)) -> int:
        if session.get(Professor, professor_id) is None:
            raise HTTPException(status_code=404, detail=PROFESSOR_INEXISTENTE["detail"])
        return professor_id

    app.dependency_overrides[atleta_da_sessao] = atleta
    app.dependency_overrides[professor_da_sessao] = professor
    return app
