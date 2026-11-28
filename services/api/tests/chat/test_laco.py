"""Laco do chat com o provedor falso (#596, ADR 0017, item 3). Sem rede; so as fixtures sinteticas da #592.

Cada caso das fixtures roda de ponta a ponta: o roteiro chama as ferramentas esperadas (o executor devolve o resultado da fixture),
o modelo escreve a resposta boa (ou a ruim duas vezes) e o laco decide o estado pelas `checagens_chat@1`.
"""

import json
import logging
from datetime import date
from pathlib import Path

import pytest
from app.chat import laco
from app.chat.registro import Consulta, Quem
from app.llm.camada import (ChamadaFerramenta, ErroProvedor, LimiteDoProvedor, ProvedorFalso, Redator, RespostaConversa, TempoLimite)

PASTA = Path(__file__).parents[1] / "fixtures" / "chat"
DADOS = json.loads((PASTA / "perguntas.json").read_text(encoding="utf-8"))
CASOS = {c["id"]: c for c in DADOS["casos"]}
CONSULTA = Consulta(Quem("atleta", 1), 1, date(2030, 3, 15))


def _chamadas(caso, inicio=0):
    return RespostaConversa(chamadas=tuple(ChamadaFerramenta(f"c{inicio + i}", f["nome"], f["argumentos"]) for i, f in enumerate(caso["ferramentas_esperadas"])))


def _executor(caso):
    resultados = {(f["nome"], json.dumps(f["argumentos"], sort_keys=True)): f["resultado"] for f in caso["ferramentas_esperadas"]}

    def executar(nome, argumentos):
        return resultados.get((nome, json.dumps(argumentos, sort_keys=True))) or {"estado": "ok", "motivo": argumentos.get("motivo")}
    return executar


def _redator(roteiro, **kw):
    prov = ProvedorFalso(roteiro=roteiro)
    return Redator(prov, "falso", "falso-1", **kw), prov


def _rodar(caso, roteiro, **kw):
    redator, prov = _redator(roteiro)
    return laco.responder(redator, _executor(caso), CONSULTA, caso["pergunta"], **kw), prov


COM_FERRAMENTA = [i for i, c in CASOS.items() if c["categoria"] not in ("fora_do_tema", "pedido_de_mudanca")]
RECUSAS = [i for i, c in CASOS.items() if c["categoria"] in ("fora_do_tema", "pedido_de_mudanca")]


@pytest.mark.parametrize("id_", COM_FERRAMENTA)
def test_caminho_feliz_de_cada_pergunta_das_fixtures(id_):
    caso = CASOS[id_]
    r, prov = _rodar(caso, [_chamadas(caso), caso["resposta_boa"]])
    assert r.estado == "respondida" and r.resposta == caso["resposta_boa"] and r.motivo is None
    assert [c["nome"] for c in r.chamadas_ferramenta] == [f["nome"] for f in caso["ferramentas_esperadas"]]
    assert prov.chamadas == 2 and (r.provedor, r.modelo) == ("falso", "falso-1")


@pytest.mark.parametrize("id_", RECUSAS)
def test_fora_do_tema_e_pedido_de_mudanca_dao_o_texto_fixo(id_):
    caso = CASOS[id_]
    r, prov = _rodar(caso, [_chamadas(caso)])
    assert r.estado == "recusada" and r.resposta == caso["resposta_boa"] and r.motivo == caso["ferramentas_esperadas"][0]["argumentos"]["motivo"]
    assert prov.chamadas == 1  # o modelo nao escreve a recusa


@pytest.mark.parametrize("id_", COM_FERRAMENTA)
def test_resposta_ruim_duas_vezes_e_reprovada_sem_guardar_o_texto(id_):
    caso = CASOS[id_]
    ruim = caso["resposta_ruim"]
    r, prov = _rodar(caso, [_chamadas(caso), ruim["texto"], ruim["texto"]])
    assert r.estado == "reprovada" and r.resposta is None and r.motivo == r.motivos[0]
    assert set(r.motivos) == set(ruim["motivos_esperados"])
    # a regeneracao leva so os CODIGOS; o texto reprovado nunca volta ao provedor
    assert prov.chamadas == 3
    assert ruim["texto"] not in json.dumps(prov.recebidas[2], ensure_ascii=False)
    assert all(m in json.dumps(prov.recebidas[2]) for m in r.motivos)
    assert ruim["texto"] not in json.dumps(r.__dict__, ensure_ascii=False, default=str)


def test_regeneracao_que_passa_vira_respondida():
    caso = CASOS["E01"]
    r, prov = _rodar(caso, [_chamadas(caso), caso["resposta_ruim"]["texto"], caso["resposta_boa"]])
    assert r.estado == "respondida" and r.resposta == caso["resposta_boa"] and prov.chamadas == 3


def test_pergunta_que_nao_e_da_ferramenta_com_numero_sem_ferramenta_reprova():
    r, _ = _rodar(CASOS["E01"], ["Você correu 99 km.", "Você correu 99 km."])
    assert r.estado == "reprovada" and "sem_ferramenta" in r.motivos


def test_limite_de_seis_ferramentas_por_pergunta():
    caso = CASOS["T01"]
    uma = RespostaConversa(chamadas=(ChamadaFerramenta("x", "ver_atividade", {"atividade_id": 9001}),))
    r, prov = _rodar(caso, [uma] * 7 + [caso["resposta_boa"]])
    assert r.estado == "erro" and r.motivo == "limite_de_ferramentas" and r.resposta is None
    assert len(r.chamadas_ferramenta) == 6 and prov.chamadas == 7
    # chamadas paralelas na mesma volta contam uma a uma
    sete = RespostaConversa(chamadas=tuple(ChamadaFerramenta(f"p{i}", "ver_atividade", {"atividade_id": 9001}) for i in range(7)))
    r, _ = _rodar(caso, [sete])
    assert r.motivo == "limite_de_ferramentas" and len(r.chamadas_ferramenta) == 6


def test_limite_de_oito_chamadas_ao_provedor():
    caso = CASOS["T01"]
    r, prov = _rodar(caso, [RespostaConversa(chamadas=(ChamadaFerramenta("x", "listar_atividades", {}),))] * 9)
    assert r.estado == "erro" and r.motivo in ("limite_de_ferramentas", "limite_de_chamadas") and prov.chamadas <= laco.MAX_CHAMADAS_PROVEDOR


def test_um_erro_de_ferramenta_volta_ao_modelo_e_o_segundo_encerra():
    chamada = RespostaConversa(chamadas=(ChamadaFerramenta("x", "ver_atividade", {"atividade_id": 1}),))
    caso = CASOS["T01"]
    erro = lambda nome, args: {"estado": "erro", "codigo": "nao_encontrada"}  # noqa: E731
    redator, prov = _redator([chamada, _chamadas(caso), caso["resposta_boa"]])
    r = laco.responder(redator, lambda n, a: erro(n, a) if a.get("atividade_id") == 1 else _executor(caso)(n, a), CONSULTA, caso["pergunta"])
    assert r.estado == "respondida"  # o modelo viu o erro uma vez, corrigiu e respondeu
    assert "nao_encontrada" in json.dumps(prov.recebidas[1])
    redator, _ = _redator([chamada, chamada, caso["resposta_boa"]])
    r = laco.responder(redator, erro, CONSULTA, caso["pergunta"])
    assert r.estado == "erro" and r.motivo == "ferramenta_erro" and r.resposta is None


def test_argumentos_malformados_do_provedor_viram_erro_de_argumento():
    r, prov = _rodar(CASOS["T01"], [RespostaConversa(chamadas=(ChamadaFerramenta("x", "ver_atividade", None),)), "x"])
    assert r.chamadas_ferramenta[0]["resultado"]["codigo"] == "argumento_invalido"


@pytest.mark.parametrize("evento,motivo", [(ErroProvedor(), "provedor_erro"), (TempoLimite(), "provedor_tempo_limite"), (LimiteDoProvedor(), "limite_de_chamadas")])
def test_erro_do_provedor_vira_motivo_em_codigo(evento, motivo):
    r, _ = _rodar(CASOS["T01"], [evento])
    assert (r.estado, r.motivo, r.resposta) == ("erro", motivo, None)


def test_provedor_nao_configurado_e_resposta_vazia():
    r = laco.responder(Redator(None, None, None), lambda *_: {}, CONSULTA, "oi")
    assert (r.estado, r.motivo) == ("erro", "provedor_nao_configurado")
    r, _ = _rodar(CASOS["T01"], [""])
    assert (r.estado, r.motivo) == ("erro", "provedor_erro")


def _com_relogio(roteiro, por_volta):
    """Redator cujo relogio anda `por_volta` segundos a cada chamada ao provedor; devolve (redator, prov, relogio, esperas)."""
    agora = [0.0]
    redator, prov = _redator(roteiro)
    original, esperas = redator.conversar, []

    def espiar(m, f, timeout_s=None):
        esperas.append(timeout_s)
        agora[0] += por_volta
        return original(m, f, timeout_s)
    redator.conversar = espiar
    return redator, prov, (lambda: agora[0]), esperas


def test_tempo_total_de_45_segundos_e_20_por_chamada():
    caso = CASOS["T01"]
    redator, prov, relogio, esperas = _com_relogio([_chamadas(caso), caso["resposta_boa"]], 30.0)
    r = laco.responder(redator, _executor(caso), CONSULTA, caso["pergunta"], relogio=relogio)
    assert esperas == [20.0, 15.0] and r.estado == "respondida"  # a 2a volta so tem o que sobra dos 45 s
    redator, prov, relogio, _ = _com_relogio([_chamadas(caso)] * 3, 30.0)
    r = laco.responder(redator, _executor(caso), CONSULTA, caso["pergunta"], relogio=relogio)
    assert (r.estado, r.motivo, r.resposta) == ("erro", "tempo_limite", None) and prov.chamadas == 2  # 60 s > 45 s: sem 3a volta


def test_historico_ultimas_seis_trocas_aprovadas_sem_resultado_de_ferramenta():
    trocas = [(f"p{i}", f"r{i}") for i in range(9)]
    msgs = laco.historico_para_provedor(trocas)
    assert len(msgs) == 12 and msgs[0] == {"role": "user", "content": "p3"} and msgs[-1] == {"role": "assistant", "content": "r8"}
    caso = CASOS["T01"]
    redator, prov = _redator([_chamadas(caso), caso["resposta_boa"]])
    laco.responder(redator, _executor(caso), CONSULTA, caso["pergunta"], historico=trocas)
    primeira = prov.recebidas[0]
    assert primeira[0]["role"] == "system" and primeira[-1] == {"role": "user", "content": caso["pergunta"]}
    assert not any(m["role"] == "tool" for m in primeira)
    assert "15/03/2030" in primeira[0]["content"]  # o "hoje" do atleta; nenhum dado do atleta no sistema


def test_so_as_ferramentas_do_papel_vao_ao_provedor_e_o_executor_recusa_papel_alheio(session):
    from app.chat.registro import executar
    assert executar(session, Consulta(Quem("visitante", 1), 1, date(2030, 3, 15)), "listar_atividades", {})["codigo"] == "ferramenta_nao_permitida"


def test_nada_da_pergunta_dos_resultados_ou_da_resposta_vai_para_log_ou_saida(caplog, capsys):
    marca = "MARCA-SINTETICA-PERGUNTA"
    caplog.set_level(logging.DEBUG)
    caso = CASOS["T01"]
    for roteiro in ([_chamadas(caso), f"Resposta com {marca}."], [ErroProvedor()], [_chamadas(caso), caso["resposta_ruim"]["texto"], caso["resposta_ruim"]["texto"]]):
        redator, _ = _redator(roteiro)
        laco.responder(redator, lambda n, a: {"estado": "ok", "x": marca}, CONSULTA, f"Pergunta {marca}?")
    saida = capsys.readouterr()
    assert marca not in caplog.text and marca not in saida.out and marca not in saida.err


def test_prompt_manda_citar_datas_e_numeros_como_nos_resultados():
    from app.chat import prompt
    assert prompt.VERSAO == "prompt_chat@2"
    texto = prompt.sistema(date(2030, 3, 15))
    assert "EXATAMENTE como estao nos resultados" in texto and "data_texto" in texto


def test_o_laco_enxerga_as_ferramentas_de_metricas_do_atleta_de_ponta_a_ponta(session):
    """O provedor recebe os esquemas de TODAS as ferramentas do papel e o laco executa `ler_serie` de verdade (registro real, banco de teste)."""
    from app.chat.registro import REGISTRO, executar
    from app.db.models import Atleta
    atleta = Atleta(nome="Atleta Teste")
    session.add(atleta)
    session.commit()
    consulta = Consulta(Quem("atleta", 1), atleta.id, date(2030, 3, 15))
    chamada = RespostaConversa(chamadas=(ChamadaFerramenta("c1", "ler_serie", {"serie_id": "corrida.pace.leve", "periodo": "ultimas_12_semanas"}),))
    redator, prov = _redator([chamada, "Não há dados dessa série ainda."])
    r = laco.responder(redator, lambda n, a: executar(session, consulta, n, a), consulta, "Como está o meu pace leve?")
    oferecidas = {f["function"]["name"] for f in prov.ferramentas_recebidas[0]}
    assert {"listar_atividades", "ver_atividade", "listar_checkins", "ler_serie", "comparar_periodos", "ler_carga_forma", "ler_linha_base",
            "ler_recuperacao", "recusar"} <= oferecidas == set(REGISTRO)
    [feita] = r.chamadas_ferramenta
    assert feita["nome"] == "ler_serie" and feita["resultado"].get("estado") != "erro", feita["resultado"]
    assert r.estado in ("respondida", "reprovada")  # chegou ate as checagens com o resultado real da ferramenta
