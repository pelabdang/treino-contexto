"""`prompt_chat@3` e as 3 perguntas que o Groq reprovou na rodada real (K02, K03, F01), com o provedor falso e SEM texto de modelo no repositório.

O que o modelo escreveu de errado fica no scratchpad de quem rodou; aqui o "texto de modelo" é sintético e curto, do TIPO do erro (frase da dor com outras
palavras, palavra de culpa, "fadiga", comparação sem direção), para provar duas coisas: (1) a checagem pega cada tipo e o laço regenera uma vez e, se repetir,
descarta o texto; (2) as frases que as ferramentas e o prompt mandam usar passam nas checagens (o `leitura_texto` da carga, a frase da dor).
"""

import json
from datetime import date
from pathlib import Path

import pytest
from app.chat import laco, prompt
from app.chat.registro import Consulta, Quem
from app.explicacao import checagens as fb
from app.explicacao import checagens_chat as ck
from app.explicacao import ferramentas_chat as fc
from app.llm.camada import ChamadaFerramenta, ProvedorFalso, Redator, RespostaConversa

PASTA = Path(__file__).parents[1] / "fixtures" / "chat"
CASOS = {c["id"]: c for c in json.loads((PASTA / "perguntas.json").read_text(encoding="utf-8"))["casos"]}
CONSULTA = Consulta(Quem("atleta", 1), 1, date(2030, 3, 15))
SISTEMA = prompt.sistema(date(2030, 3, 15))

# Textos sintéticos do TIPO do erro visto na rodada real (não são saída do modelo).
ERRADOS = {
    "K03": ("Você marcou dor em um treino recente.", {"dor_regra"}),
    "K02": ("Seu pior treino foi em 21/02, com sensação mal e esforço 7.", {"linguagem_culpa"}),
    "F01": ("Sua fadiga está alta: o TSB −7,4 mostra risco de sobrecarga.", {"linguagem_diagnostico"}),
}


def _roteiro(caso, *textos):
    chamadas = RespostaConversa(chamadas=tuple(ChamadaFerramenta(f"c{i}", f["nome"], f["argumentos"]) for i, f in enumerate(caso["ferramentas_esperadas"])))
    return ProvedorFalso(roteiro=[chamadas, *textos])


def _rodar(id_, *textos):
    caso = CASOS[id_]
    resultados = {f["nome"]: f["resultado"] for f in caso["ferramentas_esperadas"]}
    redator = Redator(_roteiro(caso, *textos), "falso", "falso-1")
    return laco.responder(redator, lambda nome, args: resultados[nome], CONSULTA, caso["pergunta"])


def test_a_versao_e_as_listas_do_prompt_vem_das_checagens():
    assert prompt.VERSAO == "prompt_chat@3"
    for lista in (fb.DIAGNOSTICO, ck.COMPARACAO):
        assert all(t in SISTEMA for t in lista)
    assert all(t in SISTEMA for t in fb.CULPA if " " not in t)
    assert f'"{fb.FRASE_DOR}"' in SISTEMA  # a frase da dor é a da checagem, não uma cópia


@pytest.mark.parametrize("trecho", [
    "DOR:", "Nao escreva \"marcou dor\"", "recusar", "pedido_de_mudanca", "CULPA e JULGAMENTO", "DIAGNOSTICO", "COMPARACAO", "`direcao`", "CARGA E FORMA",
    "leitura_texto", "nao escreva o nome em ingles", "frases completas com ponto final", "margem de X", "SO se um check-in tem", "Em vez de \"Seu pior treino foi...\"",
])
def test_o_prompt_traz_as_regras_pedidas(trecho):
    assert trecho in SISTEMA


@pytest.mark.parametrize("id_", ["K02", "K03", "F01"])
def test_o_tipo_de_erro_reprova_o_laco_regenera_e_descarta(id_):
    texto, motivos = ERRADOS[id_]
    caso = CASOS[id_]
    assert motivos <= set(ck.checar_texto(caso["ferramentas_esperadas"], texto).motivos)
    r = _rodar(id_, texto, texto)
    assert r.estado == "reprovada" and r.resposta is None and motivos <= set(r.motivos)
    r = _rodar(id_, texto, caso["resposta_boa"])  # a regeneração (com os CÓDIGOS, nunca o texto) acerta
    assert r.estado == "respondida" and r.resposta == caso["resposta_boa"]


def test_a_frase_da_dor_do_prompt_e_a_unica_que_passa():
    caso = CASOS["K03"]
    assert ck.checar_texto(caso["ferramentas_esperadas"], f"{fb.FRASE_DOR}\nFoi em 05/03.").aprovado
    for errado in ("Você marcou dor em um treino recente.", "Você registrou dor neste treino. A dor foi em 05/03.", "Você registrou uma dor neste treino."):
        assert "dor_regra" in ck.checar_texto(caso["ferramentas_esperadas"], errado).motivos, errado


@pytest.mark.parametrize("faixa,direcao", [("parecidos", "parecido"), ("acima", "maior"), ("abaixo", "menor"), ("bem_acima", "maior"), ("bem_abaixo", "menor")])
@pytest.mark.parametrize("tendencia", [None, "subiu", "caiu", "perto"])
def test_a_leitura_da_carga_copiada_igual_passa_nas_checagens(faixa, direcao, tendencia):
    """A `frase_forma@1` do app diz "fadiga" e "subiu" e reprovaria no chat; o `leitura_texto` da ferramenta é o mesmo resultado em palavras que passam."""
    from app.servicos import frase_forma as ff

    leitura = fc._leitura_forma(ff.FraseForma(ff.VERSAO, faixa, tendencia, ""), 56, 48, 44, [])
    resultado = {"estado": "ok", "data_texto": "qui 14/03", "ctl_texto": "48,2", "atl_texto": "55,6", "tsb_texto": "−7,4", "leitura_texto": leitura, "direcao": direcao}
    r = ck.checar_texto([{"nome": "ler_carga_forma", "argumentos": {}, "resultado": resultado}], leitura)
    assert r.aprovado, (leitura, r.motivos)
    assert "fadiga" not in leitura.lower()


def test_leitura_da_carga_aprendendo_e_sem_treino_recente():
    from app.servicos import frase_forma as ff

    ap = fc._leitura_forma(ff.FraseForma(ff.VERSAO, "aprendendo", None, "Ainda aprendendo a sua forma: faltam 41 dias de histórico para estimar."), 14, 2, 2, [])
    assert ap.startswith("Ainda aprendendo") and "41" in ap
    sem = fc._leitura_forma(ff.FraseForma(ff.VERSAO, "sem_treino_recente", None, ""), 20, 30, 30, ["Há 1 treino ainda sem carga calculada; a frase pode mudar quando ele for calculado."])
    assert sem.startswith("Você não teve treino com carga calculada") and "ATL em 20" in sem and sem.endswith("calculado.")
    assert "fadiga" not in sem.lower()
