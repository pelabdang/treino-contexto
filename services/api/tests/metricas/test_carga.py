"""rTSS e hrTSS por volta (issue #138, ADR 0010 itens 4 e 7, nota docs/metricas/carga-treino.md).

Fórmula (forma do TSS; Coggan & Allen, *Training and Racing with a Power Meter*; TrainingPeaks, "The Development of
the Training Stress Score"): carga_i = duração_i / 3600 x IF_i^2 x 100, com IF = v / v_limiar (rTSS) ou fc / fc_limiar
(hrTSS). Uma hora no limiar vale 100. Os valores esperados dos testes à mão estão calculados nos comentários.
A segunda metade confere a função contra o oráculo da #137 (``ESPERADO`` e ``SEM_SAUDE``) para todas as atividades.
"""

import importlib.util
import sys
from pathlib import Path

import pytest

# O oráculo da #137 é carregado por caminho (tests/ não é pacote), como os demais testes de métricas.
_spec = importlib.util.spec_from_file_location("_carga_oraculo", Path(__file__).with_name("test_carga_oraculo.py"))
_oraculo = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = _oraculo
_spec.loader.exec_module(_oraculo)
ESPERADO, GERADOR, LIMIAR_FC = _oraculo.ESPERADO, _oraculo.GERADOR, _oraculo.LIMIAR_FC
LIMIAR_VELOCIDADE, MOTIVOS_ORACULO, SEM_SAUDE = _oraculo.LIMIAR_VELOCIDADE, _oraculo.MOTIVOS, _oraculo.SEM_SAUDE
_dia_local, _vigente = _oraculo._dia_local, _oraculo._vigente

from app.ingestao.garmin.tipos import de_json
from app.metricas import carga
from app.metricas.carga import Limiares, Volta, calcular_carga

V_LIMIAR = 1000 / 270  # pace de limiar 270 s/km (exemplo 1 da ADR)
COM_TUDO = Limiares(fc_bpm=170, velocidade_ms=V_LIMIAR, atleta_tem_fc=True, atleta_tem_velocidade=True)
SO_FC = Limiares(fc_bpm=170, atleta_tem_fc=True, atleta_tem_velocidade=True)
SO_VEL = Limiares(velocidade_ms=V_LIMIAR, atleta_tem_fc=True, atleta_tem_velocidade=True)


def test_versao_e_constantes():
    assert carga.VERSAO == "carga@2"
    assert carga.COBERTURA_MIN == 0.95
    assert set(carga.MOTIVOS) == MOTIVOS_ORACULO


# ---------------------------------------------------------------------------------------------
# Casos à mão
# ---------------------------------------------------------------------------------------------
def test_exemplo_1_rtss():
    """Volta A: 1000 m em 300 s: IF = 270/300 = 0,9; 300/3600 x 0,81 x 100 = 6,75.
    Volta B: 1000 m em 240 s: IF = 1,125; 240/3600 x 1,265625 x 100 = 8,4375. Soma 15,1875."""
    r = calcular_carga("corrida", None, [Volta(300, 1000, None), Volta(240, 1000, None)], SO_VEL)
    assert r.estado == "calculada" and r.metodo == "rtss" and r.granularidade == "volta"
    assert r.carga == pytest.approx(15.1875, abs=1e-9) and r.carga_rtss == r.carga and r.carga_hrtss is None
    assert r.cobertura_pct == 100.0 and r.motivo is None


def test_uma_hora_no_limiar_vale_100():
    r = calcular_carga("corrida", None, [Volta(3600, 3600 * V_LIMIAR, None)], SO_VEL)
    assert r.carga == pytest.approx(100.0, abs=1e-9)
    r = calcular_carga("ciclismo", None, [Volta(3600, 30000, 170)], SO_FC)
    assert r.carga == pytest.approx(100.0, abs=1e-9)


def test_exemplo_2_hrtss():
    """FC de limiar 170. A: 300 s a 153 bpm: IF 0,9, 6,75. B: 240 s a 187 bpm: IF 1,1, 240/3600 x 1,21 x 100 = 8,06667."""
    r = calcular_carga("ciclismo", None, [Volta(300, 2000, 153), Volta(240, 2000, 187)], SO_FC)
    assert r.metodo == "hrtss" and r.carga == pytest.approx(14.816667, abs=1e-6)
    assert r.carga_hrtss == r.carga and r.carga_rtss is None
    assert r.limiar_fc_bpm == 170 and r.limiar_velocidade_ms is None


def test_rtss_vence_e_os_dois_sao_gravados():
    """Corrida com pace e FC: carga = rTSS (15,1875); hrTSS de 300 s a 153 e 240 s a 187 = 14,816667 também gravado."""
    voltas = [Volta(300, 1000, 153), Volta(240, 1000, 187)]
    r = calcular_carga("corrida", None, voltas, COM_TUDO)
    assert r.metodo == "rtss" and r.carga == pytest.approx(15.1875, abs=1e-9)
    assert r.carga_rtss == pytest.approx(15.1875, abs=1e-9) and r.carga_hrtss == pytest.approx(14.816667, abs=1e-6)
    assert r.limiar_fc_bpm == 170 and r.limiar_velocidade_ms == pytest.approx(V_LIMIAR)


def test_corrida_sem_limiar_de_velocidade_cai_para_hrtss():
    r = calcular_carga("corrida", None, [Volta(300, 1000, 153), Volta(240, 1000, 187)], SO_FC)
    assert r.metodo == "hrtss" and r.carga_rtss is None and r.carga == pytest.approx(14.816667, abs=1e-6)


def test_esteira_e_ciclismo_so_hrtss_mesmo_com_velocidade():
    for modalidade, subtipo in (("corrida", "esteira"), ("ciclismo", None), ("ciclismo", "virtual")):
        r = calcular_carga(modalidade, subtipo, [Volta(300, 1000, 153)], COM_TUDO)
        assert r.metodo == "hrtss" and r.carga_rtss is None, (modalidade, subtipo)
        assert r.carga == pytest.approx(6.75, abs=1e-9)  # 300/3600 x 0,81 x 100


def test_volta_sem_fc_no_meio_conta_zero_com_cobertura_95():
    """20 voltas de 50 s a 153 bpm (IF 0,9), uma sem FC: cobertura 950/1000 = 95%, vale.
    Cada volta: 50/3600 x 0,81 x 100 = 1,125; 19 voltas = 21,375."""
    voltas = [Volta(50, 100, 153)] * 9 + [Volta(50, 100, None)] + [Volta(50, 100, 153)] * 10
    r = calcular_carga("ciclismo", None, voltas, SO_FC)
    assert r.estado == "calculada" and r.cobertura_pct == pytest.approx(95.0)
    assert r.carga == pytest.approx(21.375, abs=1e-9)


def test_cobertura_90_nao_vale():
    voltas = [Volta(100, 100, 153)] * 9 + [Volta(100, 100, None)]
    r = calcular_carga("ciclismo", None, voltas, SO_FC)
    assert r.estado == "sem_carga" and r.motivo == "cobertura_insuficiente"
    assert r.cobertura_pct == pytest.approx(90.0) and r.carga is None and r.metodo is None
    assert r.carga_rtss is None and r.carga_hrtss is None


def test_volta_de_distancia_zero_nao_tem_pace_e_conta_zero_no_rtss():
    """Volta de 100 s com distância 0 em 1000 s de treino: cobertura 90% no rTSS, mas o hrTSS vale (FC em todas)."""
    voltas = [Volta(900, 3000, 153), Volta(100, 0, 153)]
    r = calcular_carga("corrida", None, voltas, COM_TUDO)
    # rTSS: 900 s, v = 3,3333 m/s, IF = 0,9; cobertura 90% < 95% -> não vale. hrTSS: 1000 s a 153 -> 1000/3600 x 0,81 x 100.
    assert r.metodo == "hrtss" and r.carga_rtss is None
    assert r.carga == pytest.approx(22.5, abs=1e-9) and r.cobertura_pct == 100.0


def test_volta_de_duracao_zero_nao_divide_por_zero():
    r = calcular_carga("corrida", None, [Volta(0, 0, None), Volta(300, 1000, None)], SO_VEL)
    assert r.carga == pytest.approx(6.75, abs=1e-9) and r.cobertura_pct == 100.0


def test_limiar_trocado_no_dia_vale_o_que_foi_passado():
    """O limiar resolvido para o dia é o que entra na conta: 300 s a 153 bpm. Limiar 170: IF 0,9, 6,75;
    limiar 180 (trocado no dia): IF 0,85, 300/3600 x 0,7225 x 100 = 6,020833."""
    voltas = [Volta(300, 1000, 153)]
    antes = calcular_carga("ciclismo", None, voltas, Limiares(fc_bpm=170, atleta_tem_fc=True))
    depois = calcular_carga("ciclismo", None, voltas, Limiares(fc_bpm=180, atleta_tem_fc=True))
    assert antes.carga == pytest.approx(6.75, abs=1e-9) and depois.carga == pytest.approx(6.020833, abs=1e-6)
    assert (antes.limiar_fc_bpm, depois.limiar_fc_bpm) == (170, 180)


def test_atividade_sem_voltas_e_volta_unica():
    """5 km em 1500 s: v = 3,3333, IF = 3,3333/3,7037 = 0,9; 1500/3600 x 0,81 x 100 = 33,75."""
    r = calcular_carga("corrida", None, [], SO_VEL, atividade=Volta(1500, 5000, 150))
    assert r.granularidade == "atividade" and r.carga == pytest.approx(33.75, abs=1e-9)


def test_carga2_voltas_sem_fc_usam_a_fc_media_da_atividade():
    """carga@2 (#255). Pedal com 3 voltas sem FC e atividade de 1800 s a 153 bpm, FC de limiar 170: IF = 0,9;
    1800/3600 x 0,81 x 100 = 40,5. Duração e FC vêm da atividade, não da soma das voltas."""
    voltas = [Volta(600, 5000, None), Volta(600, 5000, None), Volta(600, 5000, None)]
    r = calcular_carga("ciclismo", None, voltas, SO_FC, atividade=Volta(1800, 15000, 153))
    assert r.estado == "calculada" and r.metodo == "hrtss" and r.granularidade == "atividade"
    assert r.carga == pytest.approx(40.5, abs=1e-9) and r.carga_hrtss == r.carga and r.cobertura_pct == 100.0
    assert carga.usa_fc_da_atividade(voltas, Volta(1800, 15000, 153))


def test_carga2_sem_fc_na_atividade_continua_sem_fc():
    voltas = [Volta(600, 5000, None)] * 3
    for ativ in (Volta(1800, 15000, None), None):
        r = calcular_carga("ciclismo", None, voltas, SO_FC, atividade=ativ)
        assert r.estado == "sem_carga" and r.motivo == "sem_fc" and r.granularidade == "volta"


def test_carga2_fc_em_parte_das_voltas_segue_a_cobertura():
    """Uma volta com FC (10% da duração) e a atividade com FC: a atividade NÃO entra; cobertura 10% < 95%."""
    voltas = [Volta(100, 1000, 153)] + [Volta(100, 1000, None)] * 9
    r = calcular_carga("ciclismo", None, voltas, SO_FC, atividade=Volta(1000, 10000, 153))
    assert r.estado == "sem_carga" and r.motivo == "cobertura_insuficiente" and r.cobertura_pct == pytest.approx(10.0)
    assert not carga.usa_fc_da_atividade(voltas, Volta(1000, 10000, 153))


def test_carga2_rtss_nao_muda_e_granularidade_e_a_do_metodo_vencedor():
    """Corrida com pace e voltas sem FC: rTSS por volta vence (15,1875, granularidade volta); o hrTSS da atividade
    (540 s a 153 bpm: 540/3600 x 0,81 x 100 = 12,15) fica gravado."""
    voltas = [Volta(300, 1000, None), Volta(240, 1000, None)]
    r = calcular_carga("corrida", None, voltas, COM_TUDO, atividade=Volta(540, 2000, 153))
    assert r.metodo == "rtss" and r.granularidade == "volta" and r.carga == pytest.approx(15.1875, abs=1e-9)
    assert r.carga_hrtss == pytest.approx(12.15, abs=1e-9)


def test_sem_voltas_e_sem_atividade_nao_inventa():
    assert calcular_carga("corrida", None, [], SO_VEL).motivo == "sem_pace"
    assert calcular_carga("ciclismo", None, [], SO_FC).motivo == "sem_fc"


# ---- motivos, na ordem da ADR ----
def test_modalidade_sem_carga_vem_antes_do_limiar():
    for modalidade in ("natacao", "outra"):
        for lim in (Limiares(), COM_TUDO):
            r = calcular_carga(modalidade, None, [Volta(300, 1000, 150)], lim)
            assert (r.estado, r.motivo, r.carga) == ("sem_carga", "modalidade_sem_carga", None)


def test_sem_dados_saude_e_sem_limiar_na_data():
    voltas = [Volta(300, 1000, 150)]
    assert calcular_carga("corrida", None, voltas, Limiares()).motivo == "sem_dados_saude"
    so_depois = Limiares(atleta_tem_fc=True, atleta_tem_velocidade=True)  # há linhas, todas posteriores
    assert calcular_carga("corrida", None, voltas, so_depois).motivo == "sem_limiar_na_data"
    # só importa a grandeza dos caminhos da modalidade: velocidade existe, mas ciclismo precisa de FC
    assert calcular_carga("ciclismo", None, voltas, Limiares(atleta_tem_velocidade=True)).motivo == "sem_dados_saude"
    assert calcular_carga("ciclismo", None, voltas, Limiares(atleta_tem_fc=True)).motivo == "sem_limiar_na_data"
    # corrida: basta ter uma das duas para ser "na data"
    assert calcular_carga("corrida", None, voltas, Limiares(atleta_tem_velocidade=True)).motivo == "sem_limiar_na_data"


def test_motivo_e_o_do_primeiro_caminho_disponivel():
    """Corrida com os dois caminhos disponíveis: o motivo é o do rTSS (sem_pace), a menos que o hrTSS valha."""
    r = calcular_carga("corrida", None, [Volta(300, 0, 153)], COM_TUDO)
    assert r.metodo == "hrtss" and r.carga_rtss is None  # rTSS não vale, hrTSS vale: há carga
    # nenhum vale: sem distância e sem FC, o primeiro caminho disponível é o rTSS
    assert calcular_carga("corrida", None, [Volta(300, 0, None)], COM_TUDO).motivo == "sem_pace"
    # só o hrTSS disponível: o motivo é o do hrTSS, não o do rTSS
    assert calcular_carga("corrida", None, [Volta(300, 1000, None)], SO_FC).motivo == "sem_fc"
    # só o rTSS disponível, com dado só em parte
    voltas = [Volta(100, 300, None)] * 9 + [Volta(100, 0, None)]
    assert calcular_carga("corrida", None, voltas, SO_VEL).motivo == "cobertura_insuficiente"
    # esteira não tem caminho de pace: sem FC é sem_fc mesmo com distância
    assert calcular_carga("corrida", "esteira", [Volta(300, 1000, None)], COM_TUDO).motivo == "sem_fc"


def test_cobertura_so_aparece_em_cobertura_insuficiente():
    assert calcular_carga("corrida", None, [Volta(300, 0, None)], SO_VEL).cobertura_pct is None
    assert calcular_carga("natacao", None, [Volta(300, 100, 140)], COM_TUDO).cobertura_pct is None


@pytest.mark.parametrize("subtipo", ["multiesporte_pai", "troca"])
def test_subtipos_ignorados_nao_tem_resultado(subtipo):
    assert carga.ignorada(subtipo) is True
    assert calcular_carga("outra", subtipo, [Volta(60, 0, None)], Limiares()) is None
    assert calcular_carga("corrida", subtipo, [Volta(60, 100, 150)], COM_TUDO) is None
    assert carga.ignorada(None) is False and carga.ignorada("esteira") is False


@pytest.mark.parametrize("fc, vel", [(0, None), (-1, None), (None, 0), (None, float("nan"))])
def test_limiar_invalido_e_erro(fc, vel):
    with pytest.raises(ValueError):
        calcular_carga("corrida", None, [Volta(60, 100, 150)], Limiares(fc_bpm=fc, velocidade_ms=vel))


# ---------------------------------------------------------------------------------------------
# Oráculo da #137: todas as atividades das fixtures
# ---------------------------------------------------------------------------------------------
@pytest.fixture(scope="module")
def gerador():
    spec = importlib.util.spec_from_file_location("gerar_fixtures_carga", GERADOR)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def _entrada(a):
    """Voltas (ou volta única) da fixture, como a #141 as leria do banco."""
    if a.voltas:
        return [Volta(float(v[2]), float(v[1]), v[3]) for v in a.voltas], None
    dist, dur, fc = a.json_total
    return [], Volta(float(dur), float(dist), fc)


def _limiares(a):
    dia = _dia_local(a)
    fc, vel = _vigente(LIMIAR_FC, dia), _vigente(LIMIAR_VELOCIDADE, dia)
    return Limiares(
        fc_bpm=float(fc) if fc is not None else None,
        velocidade_ms=float(vel) if vel is not None else None,
        atleta_tem_fc=True,
        atleta_tem_velocidade=True,
    )


def _confere(r, e):
    assert r.estado == e.estado
    assert r.motivo == e.motivo
    assert r.metodo == e.metodo
    assert r.granularidade == e.granularidade
    for obtido, esperado in ((r.carga, e.carga), (r.carga_rtss, e.carga_rtss), (r.carga_hrtss, e.carga_hrtss),
                             (r.cobertura_pct, e.cobertura_pct)):
        if esperado is None:
            assert obtido is None
        else:
            assert obtido == pytest.approx(esperado, abs=1e-5)


@pytest.mark.parametrize("id_", sorted(ESPERADO))
def test_bate_com_o_oraculo(gerador, id_):
    a = next(x for x in gerador.ATIVIDADES if x.id == id_)
    modalidade, subtipo = de_json(a.activity_type, a.sport_type)
    voltas, total = _entrada(a)
    r = calcular_carga(modalidade, subtipo, voltas, _limiares(a), atividade=total)
    _confere(r, ESPERADO[id_])


@pytest.mark.parametrize("id_", sorted(SEM_SAUDE))
def test_atleta_sem_saude_bate_com_o_oraculo(gerador, id_):
    a = next(x for x in gerador.ATIVIDADES if x.id == id_)
    modalidade, subtipo = de_json(a.activity_type, a.sport_type)
    voltas, total = _entrada(a)
    r = calcular_carga(modalidade, subtipo, voltas, Limiares(), atividade=total)
    assert (r.estado, r.motivo, r.carga) == ("sem_carga", SEM_SAUDE[id_], None)


def test_ignoradas_do_oraculo_nao_tem_resultado(gerador):
    assert len(gerador.IGNORADAS_MULTIESPORTE) == 3
    for a in gerador.ATIVIDADES:
        if a.id not in gerador.IGNORADAS_MULTIESPORTE:
            continue
        modalidade, subtipo = de_json(a.activity_type, a.sport_type)
        voltas, total = _entrada(a)
        assert calcular_carga(modalidade, subtipo, voltas, _limiares(a), atividade=total) is None
