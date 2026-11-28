"""Fixtures sinteticas do chat (issue #592, ADR 0017, item 9): `tests/fixtures/chat/perguntas.json` e `atletas.json`.

Por enquanto confere o CONTRATO das fixtures, sem depender do que ainda nao existe:
- estrutura, contagens e ids unicos; so dado sintetico (nenhum e-mail, telefone ou URL);
- ferramentas e argumentos conforme o catalogo da ADR 0017 (item 1); nenhum `atleta_id` nos argumentos (item 2);
- toda resposta boa so cita numeros presentes nos resultados das ferramentas (a regra `numero_fora_dos_resultados`, ADR 0017
  item 4; fonte: regra propria do projeto, a mesma conferencia da `checagens_feedback`);
- a resposta ruim declara os motivos pelos quais reprova, e o motivo `numero_fora_dos_resultados` bate com a conta feita aqui;
- recusa e encaminhamento sao o texto fixo.
Quando a `checagens_chat@1` (#595) existir, o mesmo arquivo passa a rodar a boa e a ruim contra ela.
"""

import json
import re
from pathlib import Path

import pytest

PASTA = Path(__file__).parents[1] / "fixtures" / "chat"
DADOS = json.loads((PASTA / "perguntas.json").read_text(encoding="utf-8"))
CASOS = DADOS["casos"]
ATLETAS = json.loads((PASTA / "atletas.json").read_text(encoding="utf-8"))["atletas"]

# Catalogo da ADR 0017, item 1: ferramenta -> argumentos permitidos.
FERRAMENTAS = {
    "listar_atividades": {"modalidade", "periodo", "tipo_treino", "ordem", "limite", "de", "ate"},
    "ver_atividade": {"atividade_id"},
    "listar_checkins": {"periodo", "limite", "de", "ate"},
    "ler_serie": {"serie_id", "periodo", "de", "ate"},
    "comparar_periodos": {"serie_id", "periodo_a", "periodo_b"},
    "ler_carga_forma": {"data"},
    "ler_linha_base": {"modalidade", "tipo_treino"},
    "ler_recuperacao": {"periodo", "de", "ate"},
    "recusar": {"motivo"},
}
MOTIVOS = {
    "numero_fora_dos_resultados", "numero_por_extenso", "unidade_trocada", "sem_ferramenta",
    "linguagem_diagnostico", "linguagem_culpa", "linguagem_promessa", "linguagem_causa", "linguagem_julgamento", "linguagem_quem_fala",
    "prescricao", "comparacao_sem_ferramenta", "dor_regra", "dado_ausente_afirmado", "forma", "fora_do_escopo_respondido",
}
CATEGORIAS_TREINO = {"evolucao", "treino", "comparacao", "checkin", "carga_forma", "clima", "recuperacao"}
NUMERO = re.compile(r"\d+(?:[:,.]\d+)*")


def _numeros_do_texto(texto):
    return set(NUMERO.findall(texto))


def _numeros_dos_resultados(ferramentas):
    achados = set()

    def andar(x):
        if isinstance(x, str):
            achados.update(NUMERO.findall(x))
        elif isinstance(x, bool):
            pass
        elif isinstance(x, int | float):
            achados.add(str(x).replace(".", ","))
        elif isinstance(x, dict):
            for v in x.values():
                andar(v)
        elif isinstance(x, list):
            for v in x:
                andar(v)

    for f in ferramentas:
        andar(f["resultado"])
    return achados


def _ids():
    return [c["id"] for c in CASOS]


def test_contagens():
    categorias = [c["categoria"] for c in CASOS]
    treino = [c for c in CASOS if c["categoria"] in CATEGORIAS_TREINO]
    assert 20 <= len(treino) <= 30
    assert categorias.count("fora_do_tema") == 5
    assert categorias.count("pedido_de_mudanca") == 3
    assert set(categorias) == CATEGORIAS_TREINO | {"fora_do_tema", "pedido_de_mudanca"}
    assert len(set(_ids())) == len(CASOS)


def test_atletas_sinteticos():
    assert {c["atleta"] for c in CASOS} <= set(ATLETAS)
    bruto = (PASTA / "perguntas.json").read_text(encoding="utf-8") + (PASTA / "atletas.json").read_text(encoding="utf-8")
    assert not re.search(r"[\w.]+@[\w.]+\.\w+|https?://|www\.", bruto)  # sem e-mail nem endereco
    assert not re.search(r"\b\d{2}\s?\d{4,5}-?\d{4}\b", bruto)  # sem telefone


@pytest.mark.parametrize("caso", CASOS, ids=_ids())
def test_ferramentas_do_catalogo(caso):
    assert caso["ferramentas_esperadas"], "toda pergunta tem ao menos uma ferramenta (a recusa e uma)"
    for f in caso["ferramentas_esperadas"]:
        assert f["nome"] in FERRAMENTAS
        assert set(f["argumentos"]) <= FERRAMENTAS[f["nome"]]
        assert not {"atleta_id", "conta_id", "professor_id"} & set(f["argumentos"])  # o atleta vem da sessao (ADR 0017, item 2)
        if f["nome"] != "recusar":
            assert f["resultado"]["estado"] in {"ok", "sem_dados", "parcial", "erro"}
            assert f["resultado"].get("versao")


@pytest.mark.parametrize("caso", CASOS, ids=_ids())
def test_resposta_boa_so_cita_numeros_dos_resultados(caso):
    boa = caso["resposta_boa"]
    assert _numeros_do_texto(boa) <= _numeros_dos_resultados(caso["ferramentas_esperadas"])
    linhas = [x for x in boa.split("\n") if x.strip()]
    assert len(linhas) <= 8 and len(boa) <= 900
    assert "**" not in boa and "#" not in boa and "[[" not in boa


@pytest.mark.parametrize("caso", CASOS, ids=_ids())
def test_resposta_ruim_declara_o_motivo(caso):
    ruim = caso["resposta_ruim"]
    motivos = ruim["motivos_esperados"]
    assert motivos and set(motivos) <= MOTIVOS and len(set(motivos)) == len(motivos)
    fora = _numeros_do_texto(ruim["texto"]) - _numeros_dos_resultados(caso["ferramentas_esperadas"])
    assert bool(fora) == ("numero_fora_dos_resultados" in motivos)
    assert ruim["texto"] != caso["resposta_boa"]


@pytest.mark.parametrize("caso", [c for c in CASOS if c["categoria"] in ("fora_do_tema", "pedido_de_mudanca")], ids=lambda c: c["id"])
def test_recusa_e_texto_fixo(caso):
    (f,) = caso["ferramentas_esperadas"]
    assert f["nome"] == "recusar" and f["resultado"] is None
    assert f["argumentos"]["motivo"] == caso["categoria"]
    assert caso["resposta_boa"] == DADOS["textos_fixos"][caso["categoria"]]
    assert "fora_do_escopo_respondido" in caso["resposta_ruim"]["motivos_esperados"]


def test_pergunta_de_treino_nao_e_recusada():
    for c in CASOS:
        if c["categoria"] in CATEGORIAS_TREINO:
            assert all(f["nome"] != "recusar" for f in c["ferramentas_esperadas"])
