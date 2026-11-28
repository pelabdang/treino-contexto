"""`conversar` da camada de LLM (#596): chamada com ferramentas pelo LiteLLM, sem rede (o `completion` e trocado)."""

from types import SimpleNamespace

import pytest
from app.llm import camada
from app.llm.camada import ChamadaFerramenta, ProvedorLiteLLM, Redator, RespostaConversa

FERRAMENTAS = [{"type": "function", "function": {"name": "listar_atividades", "description": "x", "parameters": {"type": "object"}}}]


def _resp(texto=None, chamadas=()):
    tcs = [SimpleNamespace(id=i, function=SimpleNamespace(name=n, arguments=a)) for i, n, a in chamadas]
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=texto, tool_calls=tcs or None))])


@pytest.fixture
def litellm_falso(monkeypatch):
    visto = {}
    resposta = {"valor": _resp("oi")}

    def completion(**kw):
        visto.update(kw)
        if isinstance(resposta["valor"], BaseException):
            raise resposta["valor"]
        return resposta["valor"]
    monkeypatch.setattr(camada, "_configurar_litellm", lambda: SimpleNamespace(completion=completion))
    return visto, resposta


def test_manda_tools_sem_drop_params_e_devolve_chamadas(litellm_falso):
    visto, resposta = litellm_falso
    resposta["valor"] = _resp(chamadas=[("c1", "listar_atividades", '{"limite": 2}'), ("c2", "ver_atividade", "{quebrado")])
    prov = ProvedorLiteLLM("groq", "openai/gpt-oss-120b", "chave", reasoning_effort="low")
    r = Redator(prov, "groq", "openai/gpt-oss-120b").conversar([{"role": "user", "content": "q"}], FERRAMENTAS, 20.0)
    assert visto["tools"] == FERRAMENTAS and visto["tool_choice"] == "auto" and visto["drop_params"] is False and visto["num_retries"] == 0
    assert visto["model"] == "groq/openai/gpt-oss-120b" and visto["timeout"] == 20.0 and visto["reasoning_effort"] == "low"
    assert r.motivo is None and r.resposta.chamadas == (ChamadaFerramenta("c1", "listar_atividades", {"limite": 2}), ChamadaFerramenta("c2", "ver_atividade", None))


def test_texto_final_limpo_e_erros_viram_motivo(litellm_falso):
    _, resposta = litellm_falso
    redator = Redator(ProvedorLiteLLM("groq", "m", "k"), "groq", "m")
    resposta["valor"] = _resp("  linha  \n")
    assert redator.conversar([], FERRAMENTAS).resposta == RespostaConversa(texto="linha")
    for erro, motivo in [(RuntimeError("segredo"), "provedor_erro"), (TimeoutError(), "provedor_tempo_limite"), (_resp(""), "provedor_erro")]:
        resposta["valor"] = erro
        assert redator.conversar([], FERRAMENTAS).motivo == motivo
    resposta["valor"] = type("RateLimitError", (Exception,), {})()
    assert redator.conversar([], FERRAMENTAS).motivo == "limite_de_chamadas" and redator.limite_do_provedor


def test_limite_de_chamadas_da_instancia_vale_para_conversar(litellm_falso):
    redator = Redator(ProvedorLiteLLM("groq", "m", "k"), "groq", "m", limite_chamadas=1)
    assert redator.conversar([], FERRAMENTAS).motivo is None
    assert redator.conversar([], FERRAMENTAS).motivo == "limite_de_chamadas"
