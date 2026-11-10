"""`fatos_treino@1` (issue #324, ADR 0013, item 1): a função pura devolve exatamente o pacote do oráculo da #323.

O oráculo (`tests/fixtures/meta9/oraculo.py`) é escrito à mão: cada pacote esperado, com as contas da linha de base nos comentários.
Aqui cada caso é montado a partir da ENTRADA do oráculo (a atividade, o histórico, o clima, a carga e o check-in) e comparado com o PACOTE.
Tudo sintético; o texto livre do check-in é um marcador que nunca pode aparecer.
"""

import copy
import importlib.util
import inspect
import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest
from app.db.models import Atividade, CheckinTreino
from app.explicacao import fatos_treino as ft
from app.explicacao.fatos_treino import CargaFatos, ClimaFatos, EsforcosFatos
from app.metricas import linha_base as lb

PASTA = Path(__file__).parents[4] / "tests" / "fixtures" / "meta9"
HOJE = datetime(2026, 11, 9, 9, 0, tzinfo=UTC)

_spec = importlib.util.spec_from_file_location("oraculo_meta9_fatos", PASTA / "oraculo.py")
O = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = O
_spec.loader.exec_module(O)

IDS = list(O.ENTRADAS)
COM_PACOTE = [i for i in IDS if O.PACOTES[i] is not None]
# o método da carga@2 não está na ENTRADA do oráculo; vem do pacote esperado de cada caso com carga calculada
METODO = {"F07": "rtss", "F08": "rtss", "F01": "rtss", "F02": "rtss", "F03": "hrtss", "F04": "rtss", "F09": "hrtss"}


def _valores(e):
    a = e["atividade"]
    v = {"fc_media": float(a["fc_media"])}
    esteira = a["subtipo"] == "esteira"
    v["pace_medio"] = None if esteira else a["duracao_s"] / a["distancia_m"] * 1000
    v["carga_hora"] = None if e["carga"] is None else e["carga"] / (a["duracao_s"] / 3600)
    if "melhor_tiro" in e:
        v["melhor_pace"] = float(e["melhor_tiro"]["pace_s_km"])
        v["fc_melhor_tiro"] = float(e["melhor_tiro"]["fc_bpm"])
    return v


def _linha_base(e):
    a = e["atividade"]
    sessao = lb.Treino(id="s", inicio=HOJE, dia=HOJE.date(), modalidade=a["modalidade"], tipo_treino=a["tipo_treino"],
                       valores=_valores(e), subtipo=a["subtipo"])
    n = max((len(x) for x in e["historico"].values()), default=0)
    historico = []
    for k in range(n):  # um treino por semana, do mais antigo ao mais recente
        dt = HOJE - timedelta(days=7 * (n - k))
        historico.append(lb.Treino(id=f"h{k}", inicio=dt, dia=dt.date(), modalidade=a["modalidade"], tipo_treino=a["tipo_treino"],
                                   valores={c: (xs[k] if k < len(xs) else None) for c, xs in e["historico"].items()}))
    return lb.linha_base(sessao, historico)


def _motivos(e):
    m = {}
    if e["carga"] is None:
        m["carga_hora"] = "carga_pendente"
    if e["atividade"]["subtipo"] == "esteira":
        m["pace_medio"] = "esteira"
    return m


def _clima(e):
    cl = e["clima"]
    if cl is None:
        return None
    if isinstance(cl, tuple):
        return ClimaFatos("ok", *cl)
    return ClimaFatos(cl)


def _carga(i, e):
    if e["carga"] is not None:
        return CargaFatos("calculada", e["carga"], METODO[i])
    if e["atividade"]["modalidade"] == "natacao":
        return CargaFatos("sem_carga", motivo="modalidade_sem_carga")
    return CargaFatos("pendente")


def _esforcos(e):
    if e["atividade"]["modalidade"] == "natacao":
        return None
    return EsforcosFatos(False, tuple(e.get("tiros", ())))


def _atividade(e, **extra):
    a = e["atividade"]
    return SimpleNamespace(modalidade=a["modalidade"], subtipo=a["subtipo"], tipo_treino=a["tipo_treino"], duracao_s=a["duracao_s"],
                           distancia_m=a["distancia_m"], fc_media=a["fc_media"], **extra)


def _checkin(e):
    c = e["checkin"]
    if c is None:
        return None
    # o objeto leva o texto livre (o marcador, quando há) e a função não pode usá-lo
    return SimpleNamespace(pse=c["pse"], sensacao=c["sensacao"], nada_a_relatar=c["nada_a_relatar"], atalhos=c["atalhos"],
                           texto=c["texto"], observacao=c["texto"])


def _pacote(i, **troca):
    e = O.ENTRADAS[i]
    args = {"atividade": _atividade(e), "checkin": _checkin(e), "linha_base": _linha_base(e), "motivos_sem_valor": _motivos(e),
            "clima": _clima(e), "carga": _carga(i, e), "esforcos": _esforcos(e)}
    args.update(troca)
    return ft.fatos_treino(**args)


@pytest.mark.parametrize("i", COM_PACOTE)
def test_igual_ao_oraculo(i):
    assert _pacote(i) == O.PACOTES[i]


@pytest.mark.parametrize("i", COM_PACOTE)
def test_chaves_na_ordem_da_adr(i):
    p = _pacote(i)
    assert tuple(p) == O.CHAVES["pacote"]
    assert tuple(p["treino"]) == O.CHAVES["treino"]
    assert tuple(p["linha_base"]) == O.CHAVES["linha_base"]
    assert tuple(p["checkin"]) == O.CHAVES["checkin"]
    assert tuple(p["carga"]) == O.CHAVES["carga"] and tuple(p["carga_pse"]) == O.CHAVES["carga_pse"]
    assert p["versao"] == ft.VERSAO == "fatos_treino@1"


def test_sem_checkin_nao_ha_pacote():
    assert _pacote("F07") is None
    assert O.PACOTES["F07"] is None


def test_nao_elegivel_nao_tem_pacote():
    # F08: pai do multiesporte, com check-in no oráculo de entrada, mas sem pacote
    assert _pacote("F08") is None
    assert O.PACOTES["F08"] is None


def test_a_troca_do_multiesporte_tambem_nao_tem_pacote():
    e = O.ENTRADAS["F01"]
    a = _atividade(e)
    a.subtipo = "troca"
    assert _pacote("F01", atividade=a) is None


@pytest.mark.parametrize("i", COM_PACOTE)
def test_o_texto_livre_nunca_entra(i):
    bruto = json.dumps(_pacote(i), ensure_ascii=False)
    assert O.MARCADOR_TEXTO_LIVRE not in bruto


def test_o_texto_livre_do_orm_nao_entra_nem_o_fato_de_existir():
    """Com um `CheckinTreino` de verdade (a coluna `texto` preenchida), o pacote é o mesmo de um check-in sem texto."""
    e = O.ENTRADAS["F05"]
    ck = CheckinTreino(id=7, atividade_id=99, pse=3, sensacao=3, nada_a_relatar=False, dor=True, cansaco=False, sono_ruim=False,
                       calor=False, trabalho_estresse=False, texto=O.MARCADOR_TEXTO_LIVRE, versao="checkin@1",
                       registrado_em=HOJE, atualizado_em=HOJE)
    com_texto = _pacote("F05", checkin=ck)
    ck.texto = None
    sem_texto = _pacote("F05", checkin=ck)
    assert com_texto == sem_texto == O.PACOTES["F05"]
    assert e["checkin"]["texto"] == O.MARCADOR_TEXTO_LIVRE  # o texto existia na entrada


def test_nenhum_identificador_data_ou_posicao_da_atividade_entra():
    """Com uma `Atividade` ORM (id, atleta, início, posição), nada disso aparece no pacote."""
    e = O.ENTRADAS["F01"]
    a = e["atividade"]
    atv = Atividade(id=4242, atleta_id=777, fonte="garmin", fonte_id="ARQUIVO-SINTETICO-9", modalidade=a["modalidade"],
                    subtipo=a["subtipo"], tipo_treino=a["tipo_treino"], duracao_s=a["duracao_s"], distancia_m=a["distancia_m"],
                    fc_media=a["fc_media"], inicio=datetime(2026, 3, 1, 7, 0, tzinfo=UTC), fuso_min=-180,
                    inicio_lat=-23.55123, inicio_lon=-46.63331)
    p = _pacote("F01", atividade=atv)
    assert p == O.PACOTES["F01"]
    bruto = json.dumps(p, ensure_ascii=False)
    for proibido in ("4242", "777", "ARQUIVO-SINTETICO-9", "2026", "23,55", "46,63", "-23.55", "-46.63"):
        assert proibido not in bruto
    chaves = set()

    def coleta(x):
        if isinstance(x, dict):
            for k, v in x.items():
                chaves.add(k)
                coleta(v)
        elif isinstance(x, list):
            for v in x:
                coleta(v)

    coleta(p)
    assert not chaves & set(O.NOMES_PROIBIDOS_NO_PACOTE)


@pytest.mark.parametrize("i", COM_PACOTE)
def test_nenhuma_causa_afirmada_nem_estimativa(i):
    """O pacote põe fatos lado a lado: nenhuma chave nem texto de causa, probabilidade ou efeito."""
    bruto = json.dumps(_pacote(i), ensure_ascii=False).lower()
    for termo in ("causa", "porque", "provável", "provavel", "possível", "possivel", "explica", "efeito", "devido", "culpa"):
        assert termo not in bruto


@pytest.mark.parametrize("i", COM_PACOTE)
def test_nenhum_numero_novo(i):
    """Todo número do pacote vem da entrada ou dos formatos da API: igual ao oráculo à mão, e as chaves de número são as de sempre."""
    p = _pacote(i)

    def numeros(x, caminho=""):
        if isinstance(x, bool):
            return
        if isinstance(x, (int, float)):
            yield caminho, x
        elif isinstance(x, dict):
            for k, v in x.items():
                yield from numeros(v, f"{caminho}.{k}")
        elif isinstance(x, list):
            for k, v in enumerate(x):
                yield from numeros(v, f"{caminho}[{k}]")

    assert dict(numeros(p)) == dict(numeros(O.PACOTES[i]))


def test_e_pura_nao_altera_os_argumentos_e_repete_o_resultado():
    e = O.ENTRADAS["F04"]
    lb_ = _linha_base(e)
    ck = _checkin(e)
    atv = _atividade(e)
    antes = (copy.deepcopy(lb_), copy.deepcopy(vars(ck)), copy.deepcopy(vars(atv)))
    a = _pacote("F04", linha_base=lb_, checkin=ck, atividade=atv)
    b = _pacote("F04", linha_base=lb_, checkin=ck, atividade=atv)
    assert a == b
    assert (lb_, vars(ck), vars(atv)) == antes
    a["checkin"]["atalhos"].append("dor")  # o resultado é do chamador: mexer nele não muda o seguinte
    assert _pacote("F04", linha_base=lb_, checkin=ck, atividade=atv)["checkin"]["atalhos"] == ["calor", "cansaco"]


def test_o_modulo_nao_importa_rede_nem_llm_nem_sessao_de_banco():
    fonte = inspect.getsource(ft)
    for proibido in ("httpx", "requests", "litellm", "urllib", "socket", "sqlalchemy", "Session", "logging", "print("):
        assert proibido not in fonte


def test_parte_de_transicao_e_so_o_rotulo():
    assert _pacote("F01", parte_de_transicao=True)["treino"]["parte_de_transicao"] is True
    assert _pacote("F01")["treino"]["parte_de_transicao"] is False


def test_atalhos_saem_em_ordem_alfabetica_e_so_os_marcados():
    ck = SimpleNamespace(pse=5, sensacao=3, nada_a_relatar=False, atalhos=["trabalho_estresse", "dor", "sono_ruim", "calor", "cansaco", "outro"])
    p = _pacote("F01", checkin=ck)
    assert p["checkin"]["atalhos"] == ["calor", "cansaco", "dor", "sono_ruim", "trabalho_estresse"]


def test_clima_fora_do_ok_nao_leva_valores():
    p = _pacote("F01", clima=ClimaFatos("falha", 20.0, 20.0, 50.0, 5.0))
    assert p["clima"] == {"estado": "falha", "temperatura_c": None, "sensacao_termica_c": None, "umidade_pct": None, "vento_kmh": None}
    assert _pacote("F01", clima=None)["clima"] is None


def test_carga_pse_sem_duracao_e_pse_sem_ancora():
    e = O.ENTRADAS["F01"]
    a = _atividade(e)
    a.duracao_s = 0
    ck = SimpleNamespace(pse=6, sensacao=3, nada_a_relatar=True, atalhos=[])
    p = _pacote("F01", atividade=a, checkin=ck)
    assert p["carga_pse"] == {"versao": "carga_pse@1", "estado": "sem_duracao", "valor": None, "valor_texto": None}
    assert p["checkin"]["pse_texto"] == "6"  # 6, 8 e 9 ficam só com o número (ADR 0012, item 2)
    assert p["treino"]["distancia_texto"] == "8,20 km"


def test_carga_pse_com_casa_decimal_mantem_o_valor_e_o_texto():
    """PSE 6 em 2725 s = 272,5 UA (exemplo da nota da carga pela PSE): o valor não vira inteiro à força."""
    a = SimpleNamespace(modalidade="corrida", subtipo=None, tipo_treino="leve", duracao_s=2725, distancia_m=8000, fc_media=140.4)
    ck = SimpleNamespace(pse=6, sensacao=3, nada_a_relatar=True, atalhos=[])
    p = _pacote("F01", atividade=a, checkin=ck)
    assert p["carga_pse"]["valor"] == pytest.approx(272.5) and p["carga_pse"]["valor_texto"] == "272,5 UA"
    assert p["treino"]["duracao_texto"] == "45 min 25 s" and p["treino"]["fc_media_bpm"] == 140
