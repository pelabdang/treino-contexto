"""Gráfico e CSV da evolução dos tiros de 1 km (issue #39; formato da #15).

Funções puras sobre uma série já calculada (``PontoSessao``): sem banco.
Os números vêm do código de ``app.metricas.tiros_1km``; aqui só se desenha.
"""

from __future__ import annotations

import io

import matplotlib

matplotlib.use("Agg")  # sem display; antes de importar pyplot

import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.ticker import FuncFormatter, MaxNLocator  # noqa: E402

from app.metricas.tiros_1km import PontoSessao, formatar_pace  # noqa: E402

COLUNAS_CSV = (
    "data",
    "atividade_id",
    "n_tiros",
    "pace_medio_s_km",
    "pace_medio_min_km",
    "fc_media",
)
TEXTO_VAZIO = "Sem treinos intervalados com tiros de 1 km no período"
MAX_TICKS_POR_SESSAO = 12


def _dd_mm_aa(d) -> str:
    return d.strftime("%d/%m/%y")


def linhas_csv(serie: list[PontoSessao]) -> list[dict[str, str]]:
    """Uma linha por sessão, colunas na ordem de ``COLUNAS_CSV``.

    Pace em s/km com 1 casa; ``pace_medio_min_km`` via ``formatar_pace``;
    FC com 1 casa ou vazio. Valores já em texto, prontos para ``csv``.
    """
    return [
        {
            "data": p.data.isoformat(),
            "atividade_id": str(p.atividade_id),
            "n_tiros": str(p.n_tiros),
            "pace_medio_s_km": f"{p.pace_s_km:.1f}",
            "pace_medio_min_km": formatar_pace(p.pace_s_km),
            "fc_media": "" if p.fc_media is None else f"{p.fc_media:.1f}",
        }
        for p in serie
    ]


def render_png(serie: list[PontoSessao], atleta_nome: str) -> bytes:
    """PNG 1600 x 1000 (figsize 16 x 10, dpi 100), fundo branco, dois painéis."""
    fig, (ax_pace, ax_fc) = plt.subplots(
        2, 1, sharex=True, figsize=(16, 10), dpi=100, facecolor="white"
    )
    try:
        if not serie:
            fig.suptitle(f"Evolução dos tiros de 1 km — {atleta_nome} (0 sessões)", fontsize=16)
            for ax in (ax_pace, ax_fc):
                ax.set_axis_off()
            fig.text(0.5, 0.5, TEXTO_VAZIO, ha="center", va="center", fontsize=18, color="#555555")
        else:
            serie = sorted(serie, key=lambda p: (p.data, str(p.atividade_id)))
            datas = [p.data for p in serie]
            n = len(serie)
            fig.suptitle(
                f"Evolução dos tiros de 1 km — {atleta_nome} "
                f"({n} {'sessão' if n == 1 else 'sessões'}, "
                f"{_dd_mm_aa(datas[0])} a {_dd_mm_aa(datas[-1])})",
                fontsize=16,
            )

            ax_pace.plot(datas, [p.pace_s_km for p in serie], marker="o", color="#1f5fa8")
            ax_pace.set_title("Pace médio dos tiros (min/km)", loc="left", fontsize=13)
            for ax in (ax_pace, ax_fc):
                ax.yaxis.set_major_locator(MaxNLocator(integer=True))  # segundos e bpm inteiros
            ax_pace.invert_yaxis()  # mais rápido (menos s/km) para cima
            ax_pace.yaxis.set_major_formatter(FuncFormatter(lambda v, _: formatar_pace(v)))

            com_fc = [(p.data, p.fc_media) for p in serie if p.fc_media is not None]
            if com_fc:
                ax_fc.plot(
                    [d for d, _ in com_fc], [f for _, f in com_fc], marker="o", color="#b3261e"
                )
            ax_fc.set_title("FC média dos tiros (bpm)", loc="left", fontsize=13)

            ax_fc.set_xlabel("Data do treino")
            if len(set(datas)) <= MAX_TICKS_POR_SESSAO:
                ax_fc.set_xticks(sorted(set(datas)))
            else:
                ax_fc.xaxis.set_major_locator(mdates.AutoDateLocator())
            ax_fc.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m/%y"))
            for ax in (ax_pace, ax_fc):
                ax.grid(True, alpha=0.3)
        fig.tight_layout(rect=(0, 0, 1, 0.96))
        buf = io.BytesIO()
        fig.savefig(buf, format="png", facecolor="white")
        return buf.getvalue()
    finally:
        plt.close(fig)
