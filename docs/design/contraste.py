"""Contraste WCAG 2.x dos pares de cor do guia visual (issue #192).

Lê as cores da tabela "Cores" de docs/design/tokens.md (fonte única dos valores), calcula a razão de
contraste de cada par da lista PARES nos temas claro e escuro e escreve a tabela entre os marcadores
<!-- contraste:inicio --> e <!-- contraste:fim --> do mesmo arquivo.

Uso (na raiz do repo):
    python docs/design/contraste.py            # mostra a tabela
    python docs/design/contraste.py --escrever # atualiza tokens.md
    python docs/design/contraste.py --conferir # sai com 1 se algum par falha ou se a tabela está velha

Fórmula: luminância relativa e razão (L1 + 0,05) / (L2 + 0,05) da WCAG 2.2, item 1.4.3 e definições.
Mínimos AA: texto normal 4,5; texto grande (18 pt, ou 14 pt em negrito) 3,0; componente e gráfico 3,0 (1.4.11).
Só biblioteca padrão.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

TOKENS = Path(__file__).with_name("tokens.md")
INICIO = "<!-- contraste:inicio -->"
FIM = "<!-- contraste:fim -->"
MINIMO = {"texto": 4.5, "texto-grande": 3.0, "grafico": 3.0}
LINHA_COR = re.compile(r"^\| `(cor\.[a-z0-9.\-]+)` \| `(#[0-9A-Fa-f]{6})` \| `(#[0-9A-Fa-f]{6})` \|")

# (primeiro plano, fundo, tipo). O tipo diz o mínimo AA.
PARES: list[tuple[str, str, str]] = [
    # Texto principal e secundário em todos os fundos.
    ("cor.texto", "cor.fundo", "texto"),
    ("cor.texto", "cor.superficie", "texto"),
    ("cor.texto", "cor.superficie-2", "texto"),
    ("cor.texto-2", "cor.fundo", "texto"),
    ("cor.texto-2", "cor.superficie", "texto"),
    ("cor.texto-2", "cor.superficie-2", "texto"),
    # Destaque: link e texto de botão secundário; texto sobre o botão primário.
    ("cor.destaque", "cor.fundo", "texto"),
    ("cor.destaque", "cor.superficie", "texto"),
    ("cor.destaque", "cor.destaque-suave", "texto"),
    ("cor.texto", "cor.destaque-suave", "texto"),
    ("cor.sobre-destaque", "cor.destaque", "texto"),
    ("cor.sobre-destaque", "cor.destaque-pressionado", "texto"),
    # Estados (texto da mensagem, no cartão e na faixa suave).
    ("cor.sucesso", "cor.superficie", "texto"),
    ("cor.sucesso", "cor.sucesso-suave", "texto"),
    ("cor.texto", "cor.sucesso-suave", "texto"),
    ("cor.alerta", "cor.superficie", "texto"),
    ("cor.alerta", "cor.alerta-suave", "texto"),
    ("cor.texto", "cor.alerta-suave", "texto"),
    ("cor.erro", "cor.superficie", "texto"),
    ("cor.erro", "cor.erro-suave", "texto"),
    ("cor.texto", "cor.erro-suave", "texto"),
    # Modalidades: ícone e barra (gráfico), e também texto do chip.
    ("cor.corrida", "cor.superficie", "texto"),
    ("cor.corrida", "cor.fundo", "texto"),
    ("cor.ciclismo", "cor.superficie", "texto"),
    ("cor.ciclismo", "cor.fundo", "texto"),
    ("cor.natacao", "cor.superficie", "texto"),
    ("cor.natacao", "cor.fundo", "texto"),
    # Gráficos: linhas e pontos no cartão; texto do valor na mesma cor.
    ("cor.grafico.pace", "cor.superficie", "texto"),
    ("cor.grafico.fc", "cor.superficie", "texto"),
    ("cor.grafico.media", "cor.superficie", "grafico"),
    ("cor.grafico.pace", "cor.superficie-2", "grafico"),
    ("cor.grafico.fc", "cor.superficie-2", "grafico"),
    # Blocos do treino (ADR 0008): barras na faixa do treino.
    ("cor.bloco.esforco", "cor.superficie", "grafico"),
    ("cor.bloco.recuperacao", "cor.superficie", "grafico"),
    ("cor.bloco.aquecimento", "cor.superficie", "grafico"),
    ("cor.bloco.leve", "cor.superficie", "grafico"),
    # Componentes: contorno de botão secundário e campo; anel de foco.
    ("cor.borda-forte", "cor.superficie", "grafico"),
    ("cor.borda-forte", "cor.fundo", "grafico"),
    ("cor.foco", "cor.fundo", "grafico"),
    ("cor.foco", "cor.superficie", "grafico"),
]


def luminancia(hex_cor: str) -> float:
    """Luminância relativa sRGB (WCAG 2.2)."""
    h = hex_cor.lstrip("#")
    canais = []
    for i in (0, 2, 4):
        c = int(h[i : i + 2], 16) / 255
        canais.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
    r, g, b = canais
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def razao(a: str, b: str) -> float:
    la, lb = luminancia(a), luminancia(b)
    claro, escuro = max(la, lb), min(la, lb)
    return (claro + 0.05) / (escuro + 0.05)


def ler_cores(texto: str) -> dict[str, tuple[str, str]]:
    cores: dict[str, tuple[str, str]] = {}
    for linha in texto.splitlines():
        m = LINHA_COR.match(linha)
        if m:
            cores[m.group(1)] = (m.group(2).upper(), m.group(3).upper())
    return cores


def calcular(cores: dict[str, tuple[str, str]]) -> list[dict]:
    linhas = []
    for frente, fundo, tipo in PARES:
        if frente not in cores or fundo not in cores:
            raise KeyError(f"token sem cor em tokens.md: {frente if frente not in cores else fundo}")
        rc = razao(cores[frente][0], cores[fundo][0])
        re_ = razao(cores[frente][1], cores[fundo][1])
        minimo = MINIMO[tipo]
        linhas.append(
            {"frente": frente, "fundo": fundo, "tipo": tipo, "minimo": minimo, "claro": rc, "escuro": re_,
             "ok": rc >= minimo and re_ >= minimo}
        )
    return linhas


def num(v: float) -> str:
    return f"{v:.2f}".replace(".", ",")


def tabela(linhas: list[dict]) -> str:
    saida = [
        "| primeiro plano | fundo | tipo | mínimo AA | claro | escuro | passa |",
        "|---|---|---|---|---|---|---|",
    ]
    for l in linhas:
        saida.append(
            f"| `{l['frente']}` | `{l['fundo']}` | {l['tipo']} | {num(l['minimo'])} | "
            f"{num(l['claro'])} | {num(l['escuro'])} | {'sim' if l['ok'] else 'NÃO'} |"
        )
    return "\n".join(saida)


def documento_atualizado(texto: str) -> str:
    novo = tabela(calcular(ler_cores(texto)))
    antes, resto = texto.split(INICIO, 1)
    _, depois = resto.split(FIM, 1)
    return f"{antes}{INICIO}\n{novo}\n{FIM}{depois}"


def main(argv: list[str]) -> int:
    texto = TOKENS.read_text(encoding="utf-8")
    linhas = calcular(ler_cores(texto))
    falhas = [l for l in linhas if not l["ok"]]
    if "--escrever" in argv:
        TOKENS.write_text(documento_atualizado(texto), encoding="utf-8")
    elif "--conferir" in argv:
        if documento_atualizado(texto) != texto:
            print("tokens.md desatualizado: rode python docs/design/contraste.py --escrever")
            return 1
    else:
        print(tabela(linhas))
    for l in falhas:
        print(f"FALHA: {l['frente']} sobre {l['fundo']}: claro {num(l['claro'])}, escuro {num(l['escuro'])}"
              f" (mínimo {num(l['minimo'])})")
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
