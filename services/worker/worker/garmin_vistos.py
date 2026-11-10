"""Ids do Garmin ja processados, num arquivo local (issue #342). Sem mudanca no modelo de dados.

Para nao baixar de novo o que ja entrou quando o inicio da lista do Garmin nao bate com o do FIT. O arquivo guarda o par
`id do Garmin -> id interno da atividade`, por atleta, em `dados-garmin/ids-atleta-<id>.json` (ao lado do token; a pasta
esta no `.gitignore`). So acelera: a verdade continua no banco (o par so vale se a atividade ainda existe) e o
`importar_fit` continua sem duplicar. Apagar o arquivo (ou a pasta) e seguro: a proxima rodada baixa e reconstroi.

Escrita atomica (temporario + renomeacao), arquivo 0600 em pasta 0700. Arquivo ausente e normal; corrompido ou ilegivel
vira um aviso fixo e o comportamento de antes, nunca erro. O conteudo nunca vai para log, saida nem mensagem.
"""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

VERSAO = 1


@dataclass
class Vistos:
    caminho: Path
    ids: dict[int, int] = field(default_factory=dict)  # id do Garmin -> id interno da atividade
    aviso: str | None = None

    @classmethod
    def carregar(cls, caminho: Path) -> Vistos:
        v = cls(caminho)
        try:
            bruto = caminho.read_bytes()
        except FileNotFoundError:
            return v  # ainda nao ha: caso normal
        except OSError:
            v.aviso = "aviso: arquivo de ids do Garmin ilegivel; todas as atividades da lista serao baixadas de novo"
            return v
        try:
            dados = json.loads(bruto)
            if dados.get("versao") != VERSAO:
                raise ValueError
            v.ids = {int(k): int(i) for k, i in dados["ids"].items()}
        except (ValueError, TypeError, KeyError, AttributeError):
            v.ids = {}
            v.aviso = ("aviso: arquivo de ids do Garmin corrompido; sera refeito e todas as atividades da lista "
                       "serao baixadas de novo")
        return v

    def registrar(self, id_garmin: int, atividade_id: int) -> None:
        """Guarda o par e grava o arquivo. Falha ao gravar vira aviso (so o primeiro), nunca erro."""
        if self.ids.get(id_garmin) == atividade_id:
            return
        self.ids[id_garmin] = atividade_id
        try:
            self._gravar()
        except OSError:
            self.aviso = self.aviso or "aviso: nao foi possivel gravar o arquivo de ids do Garmin"

    def _gravar(self) -> None:
        pasta = self.caminho.parent
        pasta.mkdir(parents=True, exist_ok=True, mode=0o700)
        try:
            os.chmod(pasta, 0o700)
        except OSError:
            pass
        fd, tmp = tempfile.mkstemp(dir=pasta, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump({"versao": VERSAO, "ids": {str(k): v for k, v in self.ids.items()}}, f)
            os.chmod(tmp, 0o600)
            os.replace(tmp, self.caminho)
        except BaseException:
            Path(tmp).unlink(missing_ok=True)
            raise
