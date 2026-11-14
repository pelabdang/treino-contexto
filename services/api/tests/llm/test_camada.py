"""Camada de LLM (issue #326, ADR 0013 item 3). Sem rede: provedor falso, ou LiteLLM real com `mock_response`.

Tudo sintetico. A guarda de socket derruba qualquer tentativa de abrir conexao externa.
"""

import logging
import socket

import pytest
from app.config import Settings
from app.llm import MOTIVOS, ProvedorFalso, ProvedorLiteLLM, Redator, criar_redator
from app.llm.camada import ErroProvedor, _configurar_litellm


def _litellm():
    """Importa o LiteLLM so pela camada: ela define LITELLM_LOCAL_MODEL_COST_MAP antes (sem isso a importacao usa a rede)."""
    return _configurar_litellm()

MARCADOR = "MARCADOR-SINTETICO-123"
CHAVE = "chave-sintetica-xyz"


@pytest.fixture(autouse=True)
def sem_rede(monkeypatch):
    locais = ("localhost", "127.0.0.1", "::1")
    connect, create, getaddr = socket.socket.connect, socket.create_connection, socket.getaddrinfo

    def bloqueia():
        raise AssertionError("teste tentou abrir conexao de rede")

    def _host(e):
        return e[0] if isinstance(e, tuple) else e

    def connect_(self, e, *a, **k):
        if _host(e) not in locais and self.family != socket.AF_UNIX:
            bloqueia()
        return connect(self, e, *a, **k)

    def create_(e, *a, **k):
        if _host(e) not in locais:
            bloqueia()
        return create(e, *a, **k)

    def getaddr_(h, *a, **k):
        if h not in locais and h is not None:
            bloqueia()
        return getaddr(h, *a, **k)

    monkeypatch.setattr(socket.socket, "connect", connect_)
    monkeypatch.setattr(socket, "create_connection", create_)
    monkeypatch.setattr(socket, "getaddrinfo", getaddr_)


def _cfg(**kw) -> Settings:
    base = dict(llm_provider="groq", llm_model="", groq_api_key=None, openai_api_key=None, anthropic_api_key=None)
    return Settings(_env_file=None, **{**base, **kw})


# ---------- provedor falso ----------

def test_falso_devolve_texto_fixo_e_marca_o_provedor():
    r = criar_redator(_cfg(llm_provider="falso"))
    res = r.redigir("sistema", {"a": 1})
    assert res.texto == ProvedorFalso.TEXTO_BOM and res.motivo is None
    assert (res.provedor, res.modelo) == ("falso", "falso")
    assert len([l for l in res.texto.splitlines() if l.strip()]) == 3


def test_falso_modo_ruim_devolve_texto_para_as_checagens_reprovarem():
    res = Redator(ProvedorFalso(modo="ruim"), "falso", "falso").redigir("s", "p")
    assert res.texto and len(res.texto.splitlines()) > 5 and "99" in res.texto


@pytest.mark.parametrize("modo,motivo", [("erro", "provedor_erro"), ("tempo", "provedor_tempo_limite"),
                                         ("vazio", "provedor_erro")])
def test_erro_tempo_e_resposta_vazia_viram_motivo_nunca_excecao(modo, motivo):
    res = Redator(ProvedorFalso(modo=modo), "falso", "falso").redigir("s", "p")
    assert (res.texto, res.motivo) == (None, motivo) and res.motivo in MOTIVOS


def test_excecao_qualquer_do_provedor_vira_provedor_erro():
    class Quebra:
        def completar(self, *a):
            raise RuntimeError(MARCADOR)

    res = Redator(Quebra(), "x", "y").redigir("s", "p")
    assert res.motivo == "provedor_erro"


# ---------- nao configurado ----------

@pytest.mark.parametrize("kw", [
    dict(llm_provider="groq", llm_model=""),  # sem modelo
    dict(llm_provider="groq", llm_model="modelo-x"),  # sem chave
    dict(llm_provider="", llm_model="modelo-x"),
    dict(llm_provider="desconhecido", llm_model="modelo-x", groq_api_key="k"),
])
def test_nao_configurado_nao_levanta_e_nao_chama(kw):
    r = criar_redator(_cfg(**kw))
    assert not r.configurado
    assert r.redigir("s", "p").motivo == "provedor_nao_configurado"
    assert r.chamadas == 0


# ---------- limite de chamadas ----------

def test_limite_de_chamadas_por_execucao():
    falso = ProvedorFalso()
    r = Redator(falso, "falso", "falso", limite_chamadas=2)
    assert [r.redigir("s", "p").motivo for _ in range(4)] == [None, None, "limite_de_chamadas", "limite_de_chamadas"]
    assert falso.chamadas == 2  # a acima do limite nem foi ao provedor


def test_chamada_que_falha_conta_no_limite():
    r = Redator(ProvedorFalso(modo="erro"), "falso", "falso", limite_chamadas=1)
    assert r.redigir("s", "p").motivo == "provedor_erro"
    assert r.redigir("s", "p").motivo == "limite_de_chamadas"


def test_padroes_20_s_e_20_chamadas():
    s = _cfg()
    assert (s.llm_timeout_s, s.llm_limite_chamadas) == (20.0, 20)


# ---------- troca de provedor so pelo .env ----------

def test_troca_de_provedor_so_pelo_env(monkeypatch, tmp_path):
    visto = {}

    def completion(**kw):
        visto.update(kw)
        raise ErroProvedor()

    litellm = _litellm()

    monkeypatch.chdir(tmp_path)
    for env, modelo in (("groq", "modelo-g"), ("openai", "modelo-o")):
        (tmp_path / ".env").write_text(f"LLM_PROVIDER={env}\nLLM_MODEL={modelo}\n{env.upper()}_API_KEY={CHAVE}\nLLM_TIMEOUT_S=7\n")
        cfg = Settings(_env_file=tmp_path / ".env")
        r = criar_redator(cfg)
        monkeypatch.setattr(litellm, "completion", completion)
        res = r.redigir("s", {"a": 1})
        assert visto["model"] == f"{env}/{modelo}" and visto["api_key"] == CHAVE
        assert visto["timeout"] == 7 and visto["num_retries"] == 0
        assert (res.provedor, res.modelo) == (env, modelo)

    (tmp_path / ".env").write_text("LLM_PROVIDER=falso\n")  # e o falso, sem chave nem modelo
    assert criar_redator(Settings(_env_file=tmp_path / ".env")).redigir("s", "p").texto == ProvedorFalso.TEXTO_BOM


def test_chave_nunca_aparece_no_repr_da_configuracao():
    assert CHAVE not in repr(_cfg(groq_api_key=CHAVE))


# ---------- LiteLLM real, offline (mock_response) ----------

def _lite(**extra):
    return Redator(ProvedorLiteLLM("groq", "modelo-g", CHAVE, extra), "groq", "modelo-g")


def test_litellm_real_com_mock_devolve_o_texto():
    res = _lite(mock_response="Linha um.\nLinha dois.\nLinha tres.").redigir("s", {"x": 1})
    assert res.texto == "Linha um.\nLinha dois.\nLinha tres." and res.motivo is None


def test_litellm_resposta_vazia_e_erro():
    assert _lite(mock_response=" ").redigir("s", "p").motivo == "provedor_erro"


def test_litellm_excecao_vira_erro_e_timeout_vira_tempo_limite():
    litellm = _litellm()

    assert _lite(mock_response=Exception(MARCADOR)).redigir("s", "p").motivo == "provedor_erro"
    t = litellm.Timeout(message=MARCADOR, model="m", llm_provider="groq")
    assert _lite(mock_response=t).redigir("s", "p").motivo == "provedor_tempo_limite"


def test_litellm_configurado_para_nao_registrar_conteudo():
    litellm = _litellm()

    _lite(mock_response="a").redigir("s", "p")
    assert litellm.turn_off_message_logging is True and litellm.redact_messages_in_exceptions is True
    assert not (litellm.input_callback or litellm.success_callback or litellm.failure_callback or litellm.callbacks)
    assert logging.getLogger("LiteLLM").level == logging.CRITICAL


@pytest.mark.parametrize("modo", ["sucesso", "erro", "tempo", "vazio", "limite"])
def test_nada_do_conteudo_vai_para_log_stdout_stderr_nem_motivo(modo, caplog, capsys):
    """O marcador esta no prompt, no pacote e na resposta/excecao do provedor: nao pode aparecer em lugar nenhum."""
    litellm = _litellm()

    extras = {
        "sucesso": dict(mock_response=f"{MARCADOR} resposta"),
        "erro": dict(mock_response=Exception(f"corpo da requisicao {MARCADOR}")),
        "tempo": dict(mock_response=litellm.Timeout(message=MARCADOR, model="m", llm_provider="groq")),
        "vazio": dict(mock_response=" "),
        "limite": dict(mock_response=MARCADOR),
    }[modo]
    r = Redator(ProvedorLiteLLM("groq", "modelo-g", CHAVE, extras), "groq", "modelo-g",
                limite_chamadas=0 if modo == "limite" else 20)
    with caplog.at_level(logging.DEBUG):
        logging.getLogger().setLevel(logging.DEBUG)
        res = r.redigir(f"prompt {MARCADOR}", {"campo": MARCADOR})
    saida = capsys.readouterr()
    visto = caplog.text + saida.out + saida.err
    assert MARCADOR not in visto and CHAVE not in visto
    if modo != "sucesso":
        assert res.texto is None and MARCADOR not in repr(res) and res.motivo in MOTIVOS
    else:
        assert MARCADOR in res.texto  # o texto volta so para quem chamou


def test_litellm_importado_em_modo_production_sem_carregar_o_env():
    """No modo padrao ("DEV") a importacao do LiteLLM faz `load_dotenv()` e joga o `.env` mais proximo no ambiente."""
    import os

    litellm = _litellm()
    assert os.environ["LITELLM_MODE"] == "PRODUCTION" and litellm.litellm_mode == "PRODUCTION"


# ---------- #357: limite por minuto do provedor e pausa entre chamadas ----------

def test_litellm_429_vira_limite_do_provedor():
    import litellm

    r = _lite(mock_response=litellm.RateLimitError(message=MARCADOR, model="m", llm_provider="groq"))
    res = r.redigir("s", "p")
    assert (res.texto, res.motivo, r.limite_do_provedor) == (None, "limite_de_chamadas", True)
    assert MARCADOR not in repr(res)


def test_excecao_qualquer_com_status_429_vira_limite_do_provedor(monkeypatch):
    """Sem depender da classe: basta o `status_code` 429 na excecao que sai do `litellm.completion`."""
    import litellm

    class Recusa(Exception):
        status_code = 429

    def completion(**kw):
        raise Recusa(MARCADOR)

    monkeypatch.setattr(litellm, "completion", completion)
    r = _lite()
    res = r.redigir("s", "p")
    assert (res.motivo, r.limite_do_provedor) == ("limite_de_chamadas", True) and MARCADOR not in repr(res)


def test_503_continua_provedor_erro():
    import litellm

    r = _lite(mock_response=litellm.ServiceUnavailableError(message=MARCADOR, model="m", llm_provider="groq"))
    assert r.redigir("s", "p").motivo == "provedor_erro" and not r.limite_do_provedor


def test_criar_redator_repassa_o_intervalo():
    assert criar_redator(_cfg(llm_provider="falso", llm_intervalo_s=40)).intervalo_s == 40
    assert criar_redator(_cfg(llm_provider="falso")).intervalo_s == 0


def _oraculo_meta9():
    import importlib.util
    import sys
    from pathlib import Path

    caminho = Path(__file__).parents[4] / "tests" / "fixtures" / "meta9" / "oraculo.py"
    spec = importlib.util.spec_from_file_location("oraculo_meta9_camada", caminho)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_texto_do_provedor_falso_nas_checagens_reais():
    """#361: roda a `checar_texto` DE VERDADE (os testes do worker injetam uma propria e nao pegaram a reprovacao por forma)."""
    from app.explicacao.checagens import checar_texto

    pacotes = _oraculo_meta9().PACOTES
    comum = checar_texto(pacotes["F01"], ProvedorFalso.TEXTO_BOM)
    assert comum.aprovado and comum.motivos == ()
    com_dor = checar_texto(pacotes["F05"], ProvedorFalso.TEXTO_BOM)
    assert not com_dor.aprovado and com_dor.motivos == ("dor_regra",)


def test_texto_sai_sem_espacos_no_fim_de_cada_linha():
    """#367: o provedor de verdade devolveu dois espacos no fim de cada linha; a camada limpa antes de checar e gravar."""
    sujo = "  Linha um.  \nLinha dois.  \n\nLinha tres.\t \n  Linha quatro.  \n"
    res = Redator(ProvedorFalso(texto=sujo), "falso", "falso").redigir("s", "p")
    assert res.texto == "Linha um.\nLinha dois.\n\nLinha tres.\n  Linha quatro."
    assert all(linha == linha.rstrip() for linha in res.texto.split("\n"))


def test_texto_do_provedor_falso_com_espacos_no_fim_passa_nas_checagens_reais():
    from app.explicacao.checagens import checar_texto

    sujo = "\n".join(linha + "  " for linha in ProvedorFalso.TEXTO_BOM.split("\n"))
    res = Redator(ProvedorFalso(texto=sujo), "falso", "falso").redigir("s", "p")
    assert res.texto == ProvedorFalso.TEXTO_BOM.strip()
    assert checar_texto(_oraculo_meta9().PACOTES["F01"], res.texto).aprovado


def test_texto_do_provedor_falso_nao_tem_numero_repetido():
    from app.explicacao.checagens import checar_texto

    assert "numero_repetido" not in checar_texto(_oraculo_meta9().PACOTES["F01"], ProvedorFalso.TEXTO_BOM).motivos


# ---------- #395: teto de saida e esforco de raciocinio ----------

def _captura(monkeypatch):
    """Troca `litellm.completion` por um que guarda os argumentos e chama o de verdade (offline, com mock_response)."""
    litellm = _litellm()
    real, vistos = litellm.completion, {}

    def espia(**kw):
        vistos.update(kw)
        return real(**kw)

    monkeypatch.setattr(litellm, "completion", espia)
    return vistos


def test_teto_e_esforco_chegam_na_chamada(monkeypatch):
    vistos = _captura(monkeypatch)
    p = ProvedorLiteLLM("groq", "openai/gpt-oss-120b", CHAVE, dict(mock_response="Texto."), max_tokens=1200, reasoning_effort="low")
    assert Redator(p, "groq", "m").redigir("s", "p").texto == "Texto."
    assert vistos["max_tokens"] == 1200 and vistos["reasoning_effort"] == "low" and vistos["drop_params"] is True


def test_sem_teto_e_sem_esforco_nao_manda_os_parametros(monkeypatch):
    vistos = _captura(monkeypatch)
    for kw in ({}, dict(max_tokens=0, reasoning_effort="  "), dict(max_tokens=None, reasoning_effort=None)):
        vistos.clear()
        p = ProvedorLiteLLM("groq", "modelo-g", CHAVE, dict(mock_response="Texto."), **kw)
        assert Redator(p, "groq", "m").redigir("s", "p").texto == "Texto."
        assert not {"max_tokens", "reasoning_effort", "drop_params"} & vistos.keys()


def test_so_o_teto_sem_esforco(monkeypatch):
    vistos = _captura(monkeypatch)
    p = ProvedorLiteLLM("groq", "modelo-g", CHAVE, dict(mock_response="Texto."), max_tokens=800)
    Redator(p, "groq", "m").redigir("s", "p")
    assert vistos["max_tokens"] == 800 and "reasoning_effort" not in vistos


def test_padrao_do_env_e_1200_e_low_e_vem_do_settings():
    base = dict(llm_provider="groq", llm_model="modelo-g", groq_api_key=CHAVE)
    c = _cfg(**base)
    assert (c.llm_max_tokens, c.llm_reasoning_effort) == (1200, "low")
    r = criar_redator(c)
    assert (r._provedor.max_tokens, r._provedor.reasoning_effort) == (1200, "low")
    r2 = criar_redator(_cfg(**base, llm_max_tokens=900, llm_reasoning_effort="HIGH"))
    assert (r2._provedor.max_tokens, r2._provedor.reasoning_effort) == (900, "high")
    r3 = criar_redator(_cfg(**base, llm_max_tokens=0, llm_reasoning_effort=""))
    assert (r3._provedor.max_tokens, r3._provedor.reasoning_effort) == (None, None)


def test_modelo_que_nao_aceita_reasoning_effort_nao_vira_erro():
    """Groq/llama nao lista `reasoning_effort`: com `drop_params` o LiteLLM descarta e a chamada segue."""
    p = ProvedorLiteLLM("groq", "llama-3.3-70b-versatile", CHAVE, dict(mock_response="Texto."), max_tokens=1200, reasoning_effort="low")
    res = Redator(p, "groq", "llama-3.3-70b-versatile").redigir("s", "p")
    assert (res.texto, res.motivo) == ("Texto.", None)


def test_texto_vazio_com_teto_continua_erro_e_nada_e_gravado():
    """O modelo de raciocinio que gasta a saida pensando devolve vazio: vira `provedor_erro`, sem texto."""
    p = ProvedorLiteLLM("groq", "openai/gpt-oss-120b", CHAVE, dict(mock_response=" "), max_tokens=1200, reasoning_effort="low")
    res = Redator(p, "groq", "m").redigir("s", "p")
    assert (res.texto, res.motivo) == (None, "provedor_erro")
