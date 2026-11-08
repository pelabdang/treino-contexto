"""Gráfico e CSV da carga de treino: CTL, ATL, TSB e carga diária (issue #143; ADR 0010, itens 6 e 8).

Funções puras sobre a série já calculada (``app.metricas.serie_carga.DiaCarga``): sem banco. Os números vêm do código de
``serie_carga``; aqui só se desenha. Sempre "estimativa" no título e na legenda. Dias "ainda aprendendo" (menos de 42 dias
desde o primeiro dia) ficam sombreados. Mesmas regras de data (``dd/mm/aa``) e de eixo mínimo dos gráficos da Meta 1
(``app.graficos.escala``). Formato em docs/modulos/grafico-carga.md.
"""

from __future__ import annotations

import io
from collections.abc import Sequence

import matplotlib

matplotlib.use("Agg")  # sem display; antes de importar pyplot

import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.ticker import FixedLocator  # noqa: E402

from app.graficos.escala import Escala, escala_eixo  # noqa: E402
from app.metricas.serie_carga import DiaCarga  # noqa: E402

COLUNAS_CSV = ("dia", "carga", "ctl", "atl", "tsb", "aprendendo", "atividades", "calculadas", "sem_carga")
CASAS_CSV = 6  # as do oráculo da #137 (tolerância de teste 1e-6)
COR_CARGA = "#9AA3AD"  # barras: carga do dia
COR_CTL = "#3340B0"  # condicionamento
COR_ATL = "#C2410C"  # fadiga
COR_TSB = "#0F766E"  # forma
COR_APRENDENDO = "#E5E7EB"
TEXTO_VAZIO = "Sem carga calculada no período"
# Amplitudes mínimas (regra própria, como as da Meta 1): evitam que uma variação de poucos pontos pareça grande.
AMPLITUDE_MIN_CARGA = 50.0  # pontos de TSS
AMPLITUDE_MIN_TSB = 20.0
PASSO_EIXO = 5.0


def _dd_mm_aa(d) -> str:
    return d.strftime("%d/%m/%y")


def linhas_csv(dias: Sequence[DiaCarga]) -> list[dict[str, str]]:
    """Uma linha por dia, colunas na ordem de ``COLUNAS_CSV``. ``aprendendo`` como ``sim``/``nao``."""
    f = f"{{:.{CASAS_CSV}f}}"
    return [
        {
            "dia": d.dia.isoformat(),
            "carga": f.format(d.carga),
            "ctl": f.format(d.ctl),
            "atl": f.format(d.atl),
            "tsb": f.format(d.tsb),
            "aprendendo": "sim" if d.aprendendo else "nao",
            "atividades": str(d.atividades),
            "calculadas": str(d.calculadas),
            "sem_carga": str(d.sem_carga),
        }
        for d in dias
    ]


def _eixo(ax, escala: Escala | None, zero: bool = False) -> None:
    if escala is None:
        return
    # barras: folga de 25% no topo para a legenda não cobrir a maior barra
    ax.set_ylim(0 if zero else escala.min, max(escala.max, 1) * 1.25 if zero else escala.max)
    ax.yaxis.set_major_locator(FixedLocator([m.valor for m in escala.marcas]))


def render_png(dias: Sequence[DiaCarga], atleta_nome: str) -> bytes:
    """PNG 1600 x 1200 (figsize 16 x 12, dpi 100), fundo branco, três painéis com o mesmo eixo de datas."""
    fig, (ax_c, ax_f, ax_t) = plt.subplots(
        3, 1, sharex=True, figsize=(16, 12), dpi=100, facecolor="white", height_ratios=(2, 3, 2)
    )
    try:
        if not dias:
            fig.suptitle(f"Carga de treino (estimativa) — {atleta_nome} (0 dias)", fontsize=16)
            for ax in (ax_c, ax_f, ax_t):
                ax.set_axis_off()
            fig.text(0.5, 0.5, TEXTO_VAZIO, ha="center", va="center", fontsize=18, color="#555555")
        else:
            dias = sorted(dias, key=lambda d: d.dia)
            datas = [d.dia for d in dias]
            fig.suptitle(
                f"Carga de treino (estimativa) — {atleta_nome} "
                f"({len(dias)} dias, {_dd_mm_aa(datas[0])} a {_dd_mm_aa(datas[-1])})",
                fontsize=16,
            )
            apr = [d for d in dias if d.aprendendo]
            for ax in (ax_c, ax_f, ax_t):
                if apr:
                    ax.axvspan(apr[0].dia, apr[-1].dia, color=COR_APRENDENDO, alpha=0.7, zorder=0, linewidth=0)
                ax.grid(True, alpha=0.3)

            ax_c.bar(datas, [d.carga for d in dias], width=1.0, color=COR_CARGA, label="Carga do dia (estimativa)")
            sem = [d for d in dias if d.sem_carga > 0]
            if sem:
                ax_c.plot([d.dia for d in sem], [0] * len(sem), linestyle="", marker="^", color="#B91C1C",
                          markersize=6, clip_on=False, label="Dia com treino sem carga (natação, outra ou falta de dado)")
            ax_c.set_title("Carga do dia (TSS estimado)", loc="left", fontsize=13)
            _eixo(ax_c, escala_eixo([d.carga for d in dias], AMPLITUDE_MIN_CARGA, PASSO_EIXO, max_marcas=8), zero=True)

            ax_f.plot(datas, [d.ctl for d in dias], color=COR_CTL, linewidth=2.2, label="CTL, condicionamento (estimativa)")
            ax_f.plot(datas, [d.atl for d in dias], color=COR_ATL, linewidth=1.6, label="ATL, fadiga (estimativa)")
            ax_f.set_title("CTL (42 dias) e ATL (7 dias)", loc="left", fontsize=13)
            _eixo(ax_f, escala_eixo([v for d in dias for v in (d.ctl, d.atl)], AMPLITUDE_MIN_CARGA, PASSO_EIXO))

            ax_t.plot(datas, [d.tsb for d in dias], color=COR_TSB, linewidth=2.0, label="TSB, forma = CTL - ATL (estimativa)")
            ax_t.axhline(0, color="#555555", linewidth=0.8)
            ax_t.set_title("TSB (forma)", loc="left", fontsize=13)
            _eixo(ax_t, escala_eixo([d.tsb for d in dias], AMPLITUDE_MIN_TSB, PASSO_EIXO))

            if apr:
                ax_f.axvspan(apr[0].dia, apr[0].dia, color=COR_APRENDENDO, label="Ainda aprendendo (menos de 42 dias)")
            for ax in (ax_c, ax_f, ax_t):
                ax.legend(loc="upper left", fontsize=10)
            ax_t.set_xlabel("Data do treino")
            ax_t.xaxis.set_major_locator(mdates.AutoDateLocator())
            ax_t.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m/%y"))
        fig.tight_layout(rect=(0, 0, 1, 0.96))
        buf = io.BytesIO()
        fig.savefig(buf, format="png", facecolor="white")
        return buf.getvalue()
    finally:
        plt.close(fig)
