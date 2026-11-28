"""O repositório é público: nenhum arquivo de docs/ pode trazer caminho do computador de alguém.

Já aconteceu: o Graphify, rodado com caminho absoluto, gravou a origem de cada nota em docs/_grafo.
Rode o Graphify com caminho relativo (docs), a partir da raiz de um checkout limpo.
"""

import re
from pathlib import Path

DOCS = Path(__file__).resolve().parents[3] / "docs"
# montado em partes para este arquivo não casar com ele mesmo
PADROES = re.compile("|".join(["/" + "Users/", "/private" + "/tmp", "/" + "home/", "claude" + "-501"]))
EXTENSOES = {".md", ".json", ".svg", ".txt", ".canvas", ".yml", ".yaml", ".py"}


def test_docs_sem_caminho_local():
    achados = []
    for arq in DOCS.rglob("*"):
        if not arq.is_file() or arq.suffix.lower() not in EXTENSOES:
            continue
        for n, linha in enumerate(arq.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
            if PADROES.search(linha):
                achados.append(f"{arq.relative_to(DOCS.parent)}:{n}")
    assert not achados, "caminho local em docs/ (use caminho relativo): " + ", ".join(achados[:10])
