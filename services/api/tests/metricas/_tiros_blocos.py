"""Ajuda dos testes da série de tiros de 1 km (#168): voltas sintéticas -> blocos, como o banco os guarda."""

from app.metricas import esforcos as ef
from app.metricas.tiros_1km import BlocoEntrada

REF_HABITUAL = 330.0  # ritmo habitual sintético (s/km): o limiar de esforço é 330 x 0,90 = 297 s/km


def voltas(specs):
    """specs: (distancia_m, duracao_s[, parada_apos_s[, fc]]). O início de cada volta soma duração e parada."""
    resultado, t = [], 0.0
    for i, s in enumerate(specs):
        parada = s[2] if len(s) > 2 else 0.0
        fc = s[3] if len(s) > 3 else None
        resultado.append(ef.VoltaTreino(i, t, s[1], s[0], fc))
        t += s[1] + parada
    return resultado


def blocos_de(specs, ref=REF_HABITUAL):
    """Roda ``montar_blocos`` (esforcos@1) e leva o resultado ao formato da visão de tiros (com a faixa)."""
    resultado = ef.montar_blocos(voltas(specs), "corrida", referencia=ref)
    faixas = {e.bloco_ordem: e.faixa for e in ef.esforcos_corrida(resultado)}
    return [
        BlocoEntrada(
            b.ordem, b.categoria, b.volta_inicial, b.volta_final, b.distancia_m, b.duracao_s, b.fc_media,
            faixas.get(b.ordem), b.parada_apos_s,
        )
        for b in resultado.blocos
    ]
