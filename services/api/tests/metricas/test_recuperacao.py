"""`recuperacao@1` (issue #373, ADR 0014). Valores SINTÉTICOS, escritos à mão; o cálculo de cada caso está em
docs/metricas/recuperacao-oraculo.md. Nenhum dado real."""

from datetime import date, time, timedelta

import pytest
from app.metricas import recuperacao as rc
from app.metricas.recuperacao import Noite

D = date(2030, 3, 15)  # data sintética do treino
MANHA = time(8, 0)

SONO_MIN = [400, 410, 420, 420, 425, 430, 435, 435, 440, 440, 445, 450, 460, 470]  # caso A (minutos)
VFC = [40, 42, 44, 44, 45, 46, 47, 47, 48, 49, 50, 52, 54, 56]  # caso D (ms)


def _janela(valores, campo, fim=None, inicio_dias=None):
    """Uma noite por valor, nas datas D-n .. D-1 (a mais antiga primeiro)."""
    n = len(valores)
    return [Noite(D - timedelta(days=n - i), **{campo: v}) for i, v in enumerate(valores)]


def _med(r, chave):
    return next(m for m in r.medidas if m.chave == chave)


def _sono(valores_min):
    return _janela([v * 60 for v in valores_min], "sono_s")


def test_versao():
    assert rc.VERSAO == "recuperacao@1"


def test_a_sono_abaixo():  # caso A: mediana 26100 s, MAD 750, desvio max(1111,95; 1305) = 1305
    r = rc.recuperacao(D, MANHA, _sono(SONO_MIN) + [Noite(D, sono_s=345 * 60)])
    m = _med(r, "sono")
    assert (r.estado, r.motivo) == ("ok", None)
    assert (m.estado, m.n, m.mediana, m.desvio) == ("abaixo", 14, 26100, 1305)
    assert m.z == pytest.approx(-4.1379, abs=1e-4)


def test_a_sono_dentro():
    m = _med(rc.recuperacao(D, MANHA, _sono(SONO_MIN) + [Noite(D, sono_s=420 * 60)]), "sono")
    assert m.estado == "dentro"
    assert m.z == pytest.approx(-0.6897, abs=1e-4)


@pytest.mark.parametrize("minutos,estado", [(391.5, "abaixo"), (392, "dentro"), (478, "dentro"), (478.5, "acima")])
def test_a_limite_2_0_inclusive(minutos, estado):  # 435 -+ 43,5 min (2 x 21,75): o limite pertence a "abaixo"/"acima"
    assert _med(rc.recuperacao(D, MANHA, _sono(SONO_MIN) + [Noite(D, sono_s=minutos * 60)]), "sono").estado == estado


def test_b_aprendendo_com_13_noites():
    r = rc.recuperacao(D, MANHA, _sono(SONO_MIN[:13]) + [Noite(D, sono_s=345 * 60)])
    m = _med(r, "sono")
    assert (r.estado, m.estado, m.valor, m.n) == ("ok", "aprendendo", 20700, 13)
    assert m.mediana is None and m.desvio is None and m.z is None


def test_c_piso_relativo_fc_repouso():  # 14 noites iguais a 52: MAD 0, desvio = 0,05 x 52 = 2,6
    noites = _janela([52] * 14, "fc_repouso_bpm")
    for valor, estado, z in [(57, "dentro", 1.9231), (58, "acima", 2.3077), (47, "dentro", -1.9231), (46, "abaixo", -2.3077)]:
        m = _med(rc.recuperacao(D, MANHA, noites + [Noite(D, fc_repouso_bpm=valor)]), "fc_repouso")
        assert (m.estado, m.desvio) == (estado, pytest.approx(2.6))
        assert m.z == pytest.approx(z, abs=1e-4)


def test_d_mad_domina_vfc():  # mediana 47, MAD 3, desvio 1,4826 x 3 = 4,4478 (> piso 2,35)
    noites = _janela(VFC, "vfc_ms")
    m41 = _med(rc.recuperacao(D, MANHA, noites + [Noite(D, vfc_ms=41)]), "vfc")
    m38 = _med(rc.recuperacao(D, MANHA, noites + [Noite(D, vfc_ms=38)]), "vfc")
    assert (m41.estado, m41.mediana, m41.desvio) == ("dentro", 47, pytest.approx(4.4478))
    assert m41.z == pytest.approx(-1.3490, abs=1e-4)
    assert m38.estado == "abaixo" and m38.z == pytest.approx(-2.0235, abs=1e-4)


def test_e_bordas_da_janela():  # caso E: só D-28 a D-1 entram; D-29, a própria noite D e D+1 ficam fora
    base = [Noite(D - timedelta(days=k), sono_s=26100) for k in range(1, 29)]  # D-1 .. D-28: 28 noites
    fora = [Noite(D - timedelta(days=29), sono_s=1), Noite(D + timedelta(days=1), sono_s=1)]
    m = _med(rc.recuperacao(D, MANHA, base + fora + [Noite(D, sono_s=26100)]), "sono")
    assert m.n == 28 and m.mediana == 26100  # nenhum 1 s entrou, nem a noite D
    sem_borda = [n for n in base if n.noite != D - timedelta(days=28)]
    assert _med(rc.recuperacao(D, MANHA, sem_borda + [Noite(D, sono_s=26100)]), "sono").n == 27


def test_f_medida_sem_valor_na_noite():  # sono vem, VFC não: o bloco é ok e a VFC é sem_dado
    noites = _sono(SONO_MIN) + [Noite(D, sono_s=26100, vfc_ms=None, fc_repouso_bpm=52)]
    r = rc.recuperacao(D, MANHA, noites)
    assert r.estado == "ok"
    assert [m.estado for m in r.medidas] == ["dentro", "sem_dado", "aprendendo"]
    assert [m.chave for m in r.medidas] == ["sono", "vfc", "fc_repouso"]
    assert _med(r, "fc_repouso").n == 0 and _med(r, "vfc").valor is None


def test_g_noite_sem_linha_e_linha_vazia_sao_sem_noite():
    base = _sono(SONO_MIN)
    for noites in (base, base + [Noite(D)]):
        r = rc.recuperacao(D, MANHA, noites)
        assert (r.estado, r.motivo, r.medidas) == ("sem_dado", "sem_noite", ())


def test_h_madrugada_corte_as_6():
    noites = _sono(SONO_MIN) + [Noite(D, sono_s=26100)]
    r = rc.recuperacao(D, time(5, 59), noites)
    assert (r.estado, r.motivo, r.medidas) == ("sem_dado", "treino_de_madrugada", ())
    assert rc.recuperacao(D, time(6, 0), noites).estado == "ok"


def test_i_fora_do_periodo_e_busca_nunca_rodou():
    noites = _sono(SONO_MIN) + [Noite(D, sono_s=26100)]
    mais_antiga = min(n.noite for n in noites)
    assert rc.recuperacao(mais_antiga - timedelta(days=1), MANHA, noites).motivo == "fora_do_periodo"
    r = rc.recuperacao(mais_antiga, MANHA, noites)  # no primeiro dia gravado não é fora do período
    assert (r.estado, _med(r, "sono").estado, _med(r, "sono").n) == ("ok", "aprendendo", 0)
    assert rc.recuperacao(D, MANHA, []).motivo == "sem_noite"  # sem nenhuma noite gravada


def test_madrugada_vem_antes_do_fora_do_periodo():
    noites = [Noite(D, sono_s=26100)]
    assert rc.recuperacao(D - timedelta(days=3), time(5, 0), noites).motivo == "treino_de_madrugada"


def test_noite_do_treino_e_a_mesma_regra_do_pacote():
    noite = Noite(D, sono_s=26100)
    assert rc.noite_do_treino(D, MANHA, [noite]) == (noite, None)
    assert rc.noite_do_treino(D, time(5, 30), [noite]) == (None, "treino_de_madrugada")  # NULL do "desatualizado"
    assert rc.noite_do_treino(D, MANHA, [Noite(D - timedelta(days=1), sono_s=1)]) == (None, "sem_noite")
    assert rc.noite_do_treino(D - timedelta(days=2), MANHA, [noite]) == (None, "fora_do_periodo")


def test_dois_treinos_no_mesmo_dia_usam_a_mesma_noite():
    noites = _sono(SONO_MIN) + [Noite(D, sono_s=345 * 60)]
    assert rc.recuperacao(D, time(7, 0), noites) == rc.recuperacao(D, time(22, 0), noites)


def test_pura_nao_altera_a_entrada():
    noites = _sono(SONO_MIN) + [Noite(D, sono_s=345 * 60)]
    copia = list(noites)
    rc.recuperacao(D, MANHA, noites)
    assert noites == copia


def test_primeira_noite_do_atleta_vale_mais_que_a_da_janela():
    # Janela so com D-3..D; o atleta tem noites desde D-30: o treino em D-10 NAO e fora do periodo (sem_noite), e em D-40 e.
    noites = [Noite(D - timedelta(days=k), sono_s=1) for k in (3, 2, 1, 0)]
    assert rc.noite_do_treino(D - timedelta(days=10), MANHA, noites) == (None, "fora_do_periodo")  # sem o argumento: a da lista
    assert rc.noite_do_treino(D - timedelta(days=10), MANHA, noites, primeira_noite=D - timedelta(days=30)) == (None, "sem_noite")
    assert rc.noite_do_treino(D - timedelta(days=40), MANHA, noites, primeira_noite=D - timedelta(days=30)) == (None, "fora_do_periodo")
    assert rc.recuperacao(D - timedelta(days=40), MANHA, noites, primeira_noite=D - timedelta(days=30)).motivo == "fora_do_periodo"
