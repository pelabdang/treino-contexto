"""Checagens do texto do feedback (issue #325, ADR 0013, item 4): todos os textos bons passam e todos os ruins reprovam, com o motivo certo.

As listas de textos são as da #323 (`tests/fixtures/meta9/textos.py`), escritas à mão contra os pacotes do oráculo (`oraculo.py`). Aqui
a função pura `checar_texto` é testada contra elas e contra casos pequenos de cada regra. Tudo sintético.
"""

import importlib.util
import inspect
import sys
from pathlib import Path

import pytest
from app.explicacao import checagens as ck

PASTA = Path(__file__).parents[4] / "tests" / "fixtures" / "meta9"


def _carregar(nome):
    spec = importlib.util.spec_from_file_location(f"{nome}_meta9_checagens", PASTA / f"{nome}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


O = _carregar("oraculo")
T = _carregar("textos")


@pytest.mark.parametrize("i", list(T.BONS))
def test_texto_bom_passa(i):
    caso, texto = T.BONS[i]
    r = ck.checar_texto(O.PACOTES[caso], texto)
    assert r.aprovado and r.motivos == (), (i, r.motivos)


@pytest.mark.parametrize("i", list(T.RUINS))
def test_texto_ruim_reprova_com_o_motivo_certo(i):
    caso, texto, motivo, _porque = T.RUINS[i]
    r = ck.checar_texto(O.PACOTES[caso], texto)
    assert not r.aprovado
    assert r.motivos == (motivo,), (i, r.motivos)


def test_os_motivos_da_funcao_sao_os_da_lista_de_textos():
    assert ck.MOTIVOS == T.MOTIVOS


def test_o_resultado_so_traz_codigos_nunca_o_texto_nem_o_termo():
    caso, texto, _motivo, _ = T.RUINS["R19"]
    r = ck.checar_texto(O.PACOTES[caso], texto)
    bruto = repr(r)
    assert "médico" not in bruto and "medico" not in bruto and "Descanse" not in bruto
    assert all(m in ck.MOTIVOS for m in r.motivos)


def _p(caso="F01"):
    return O.PACOTES[caso]


def _ok(texto, caso="F01"):
    return ck.checar_texto(_p(caso), texto)


BASE = ("Seu pace médio foi 5:44/km, perto da mediana de 5:48/km nos 11 treinos leves das últimas 12 semanas.\n"
        "A FC média foi 146 bpm, dentro do seu normal.\n"
        "Você marcou esforço 4 (um pouco difícil), sensação 4 (bem) e nada a relatar.\n")


def test_base_dos_testes_curtos_passa():
    assert _ok(BASE + "Foram 47 min a 19 °C.").aprovado


# --- números -------------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("ultima", ["Foram 47 min.", "Foram 47 min a 19 °C.", "A carga pela PSE foi 188 UA em 47 min.",
                                    "A carga foi de 38,5 pontos.", "A umidade foi de 62% e o vento, de 9 km/h.", "A distância foi de 8,20 km."])
def test_numero_do_pacote_com_a_unidade_certa_passa(ultima):
    assert _ok(BASE + ultima).aprovado


@pytest.mark.parametrize(("ultima", "motivo"), [
    ("Foram 48 min.", "numero_fora_do_pacote"),
    ("Foram 47 km.", "unidade_trocada"),
    ("Foram 47 bpm.", "unidade_trocada"),
    ("A carga foi de 38,5 UA.", "unidade_trocada"),
    ("A carga foi de 38,6 pontos.", "numero_fora_do_pacote"),
    ("Foram 8.200 m.", "numero_fora_do_pacote"),  # o pacote traz "8,20 km" e 8200 (m), mas não "8.200" escrito assim
])
def test_numeros_que_reprovam(ultima, motivo):
    assert _ok(BASE + ultima).motivos == (motivo,)


def test_ordinal_fora_da_lista_passa_limite_conhecido():
    """Limite conhecido (nota da métrica): a lista por extenso cobre cardinais, "metade" e "dobro"; ordinais ("terceiro") não."""
    assert _ok(BASE + "Foi o terceiro treino da semana.").aprovado


def test_numero_so_com_virgula_ou_dois_pontos_nao_se_confunde():
    # "5:44" não vira "5" e "44"; "49,1" não vira "49" e "1"
    r = _ok(BASE + "A carga por hora foi 49,1 pontos/h.")
    assert r.aprovado


@pytest.mark.parametrize("palavra", ["cinco", "Cinco", "dois", "três", "metade", "dobro", "mil", "dez", "vinte"])
def test_numero_por_extenso_reprova(palavra):
    assert "numero_por_extenso" in _ok(BASE + f"Foram {palavra} tiros.").motivos


def test_um_e_uma_como_artigo_passam():
    assert _ok(BASE + "Foi um treino leve em uma manhã de 19 °C.").aprovado


def test_numeros_do_pacote_fora_dos_textos_prontos_tambem_valem():
    # F06: "1.600 m" é texto pronto; 1600 (distancia_m) e 2400 (duracao_s) são valores do pacote
    base = "Natação de 1.600 m em 40 min, com FC média de 128 bpm.\nSem comparação com o seu histórico: o treino não tem tipo.\n"
    assert ck.checar_texto(_p("F06"), base + "Você marcou esforço 5 (difícil) e sensação 4 (bem).").aprovado
    assert "numero_fora_do_pacote" in ck.checar_texto(_p("F06"), base + "Você marcou esforço 6 e sensação 4 (bem).").motivos


# --- linguagem proibida --------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize(("frase", "motivo"), [
    ("Há sinal de LESÃO.", "linguagem_diagnostico"),
    ("Parece tendinite.", "linguagem_diagnostico"),
    ("Pode ser overtraining.", "linguagem_diagnostico"),
    ("Você falhou.", "linguagem_culpa"),
    ("Foi um treino péssimo.", "linguagem_culpa"),
    ("Foi mau.", "linguagem_culpa"),
    ("Você vai conseguir no próximo.", "linguagem_promessa"),
    ("Certamente melhora.", "linguagem_promessa"),
    ("Isso foi devido ao vento.", "linguagem_causa"),
    ("Foi por conta do vento.", "linguagem_causa"),
    ("Foi o resultado do vento.", "linguagem_causa"),
    ("Talvez o vento.", "linguagem_causa"),
    ("Hidrate-se mais.", "linguagem_conselho"),
    ("Consulte um médico.", "linguagem_conselho"),
    ("O ideal é poupar.", "linguagem_conselho"),
    ("Sou o seu professor.", "linguagem_quem_fala"),
    ("Nós vimos o treino.", "linguagem_quem_fala"),
    ("Meu palpite.", "linguagem_quem_fala"),
    ("Que treino!", "linguagem_quem_fala"),
    ("Treino feito 💪", "linguagem_quem_fala"),
])
def test_termos_proibidos(frase, motivo):
    assert motivo in _ok(BASE + frase).motivos


def test_sem_diferenca_de_acento_nem_de_maiuscula():
    assert "linguagem_diagnostico" in _ok(BASE + "Pode ser LESAO.").motivos
    assert "linguagem_diagnostico" in _ok(BASE + "Pode ser lesão.").motivos
    assert "linguagem_causa" in _ok(BASE + "PORQUE sim.").motivos


def test_nos_sem_acento_e_preposicao_e_passa_mas_nos_com_acento_reprova():
    assert "linguagem_quem_fala" not in _ok(BASE + "Foram 47 min nos 11 treinos leves.").motivos
    assert "linguagem_quem_fala" in _ok(BASE + "Foram 47 min e nós 11 treinos leves.").motivos


def test_palavra_inteira_nao_pega_pedaco_de_outra():
    # "porque" não está em "porquê" do meio de outra palavra; "eu" não está em "seu"; "dor" não está em "calor"
    assert _ok(BASE + "Seu ritmo foi parecido com o de um treino leve.").aprovado
    assert "linguagem_quem_fala" not in _ok(BASE + "Foram 47 min no seu ritmo.").motivos


def test_ruim_so_passa_na_frase_sono_ruim():
    ck3 = O.PACOTES["F03"]
    base = ("Ainda aprendendo o seu normal em treino moderado: 3 de 8 treinos nas últimas 12 semanas.\n"
            "Sem comparação com o seu histórico por enquanto.\n")
    assert ck.checar_texto(ck3, base + "Você marcou esforço 6, sensação 4 (bem) e sono ruim.").aprovado
    assert "linguagem_culpa" in ck.checar_texto(ck3, base + "Você marcou esforço 6 e foi ruim.").motivos


def test_rotulos_da_pse_e_da_sensacao_nao_sao_elogio_nem_culpa():
    # F10: sensação 5 "muito bem" e PSE 0 "repouso" são rótulos do check-in; o rótulo do pacote passa com ou sem parênteses
    ok = ("Ciclismo de 28,00 km em 60 min, com FC média de 135 bpm.\nSem comparação com o seu histórico: o treino não tem tipo.\n"
          "Você marcou esforço 0 (repouso), sensação 5 (muito bem) e nada a relatar.")
    f10 = O.PACOTES["F10"]
    assert ck.checar_texto(f10, ok).aprovado
    assert ck.checar_texto(f10, ok.replace("sensação 5 (muito bem)", "sensação 5, muito bem")).aprovado
    # "muito bem" que NÃO é o rótulo da sensação do pacote continua elogio (F04: sensação "mal", métricas fora do normal)
    f4 = O.PACOTES["F04"]
    base = T.BONS["G04"][1].replace("A carga pela PSE foi 630 UA em 90 min.", "Você foi muito bem.")
    assert ck.checar_texto(f4, base).motivos == ("elogio_sem_fato",)


def test_mal_so_passa_como_rotulo_da_sensacao_2_do_pacote():
    f4 = O.PACOTES["F04"]  # sensação 2, "mal"
    g04 = T.BONS["G04"][1]
    assert ck.checar_texto(f4, g04).aprovado
    assert ck.checar_texto(f4, g04.replace("sensação 2 (mal)", "sensação 2, mal")).aprovado  # sem parênteses também
    # F01 tem sensação "bem": "mal" aí é juízo
    assert ck.checar_texto(O.PACOTES["F01"], BASE + "Foi mal.").motivos == ("linguagem_culpa",)
    # o rótulo da sensação 1 é "muito mal": passa inteiro, mas "mal" sozinho não
    p = {**f4, "checkin": {**f4["checkin"], "sensacao_nivel": 1, "sensacao_texto": "muito mal"}}
    assert ck.checar_texto(p, g04.replace("sensação 2 (mal)", "sensação 1 (muito mal)")).aprovado
    assert "linguagem_culpa" in ck.checar_texto(p, g04.replace("sensação 2 (mal)", "sensação 1 (muito mal) e foi mal")).motivos


def test_quente_e_calor_sao_o_mesmo_fato_e_frio_nao_esta_no_pacote():
    f4 = O.PACOTES["F04"]  # calor marcado
    g04 = T.BONS["G04"][1]
    assert ck.checar_texto(f4, g04.replace("Você marcou calor e cansaço", "Você marcou dia quente e cansaço")).aprovado
    # F01 não marcou calor: "quente" e "calor" reprovam igual
    assert _ok(BASE + "Foi um dia quente.").motivos == ("atalho_nao_marcado",)
    assert _ok(BASE + "Foi um dia de calor.").motivos == ("atalho_nao_marcado",)
    # o pacote traz °C, não "frio": a palavra sozinha não é fato do pacote
    assert _ok(BASE + "Foi um dia frio.").motivos == ("nome_fora_do_pacote",)
    assert ck.checar_texto(f4, g04.replace("Você marcou calor e cansaço", "Você marcou calor e frio")).motivos == ("nome_fora_do_pacote",)


@pytest.mark.parametrize(("termo", "motivo"), [
    ("Fique atento ao ritmo.", "linguagem_conselho"), ("Prefira treinos curtos.", "linguagem_conselho"), ("Considere poupar.", "linguagem_conselho"),
    ("Lembre-se do descanso.", "linguagem_conselho"), ("Priorize a recuperação.", "linguagem_conselho"),
    ("Isso indica que foi forte.", "linguagem_causa"), ("Isso mostra que foi forte.", "linguagem_causa"), ("Isso significa mais esforço.", "linguagem_causa"),
    ("A FC reflete o esforço.", "linguagem_causa"), ("Em razão do vento.", "linguagem_causa"), ("Esse é o motivo.", "linguagem_causa"),
    ("O efeito apareceu.", "linguagem_causa"), ("Foi reflexo do ritmo.", "linguagem_causa"),
    ("Sinal de fadiga.", "linguagem_diagnostico"), ("Sinal de esgotamento.", "linguagem_diagnostico"), ("Sinal de exaustão.", "linguagem_diagnostico"),
    ("Há risco.", "linguagem_diagnostico"),
    ("É preocupante.", "linguagem_culpa"), ("Fique em alerta.", "linguagem_culpa"), ("Há um problema.", "linguagem_culpa"),
    ("Foi pior.", "linguagem_culpa"), ("Foi um erro.", "linguagem_culpa"),
    ("Vamos ver o treino.", "linguagem_quem_fala"), ("Estou vendo o treino.", "linguagem_quem_fala"),
])
def test_termos_da_revisao_da_nina(termo, motivo):
    assert motivo in ck.checar_texto(O.PACOTES["F02"], T.BONS["G02"][1].replace("É uma comparação com o seu histórico, não um julgamento do treino.", termo)).motivos


@pytest.mark.parametrize("termo", ["Você evoluiu.", "É hora de superar.", "É hora de melhorar."])
def test_elogio_nas_formas_que_faltavam(termo):
    # F02: melhor pace fora do normal, nada sustenta o elogio
    texto = T.BONS["G02"][1].replace("É uma comparação com o seu histórico, não um julgamento do treino.", termo)
    assert ck.checar_texto(O.PACOTES["F02"], texto).motivos == ("elogio_sem_fato",)


def test_termos_novos_nao_barram_texto_legitimo():
    """Contexto: 'melhor tiro', 'esforço', 'pior' só como palavra inteira, rótulos do check-in e 'estou/sou/vamos' não aparecem nos bons."""
    for i, (caso, texto) in T.BONS.items():
        assert ck.checar_texto(O.PACOTES[caso], texto).aprovado, i
    assert ck.checar_texto(O.PACOTES["F02"], T.BONS["G02"][1]).aprovado  # "melhor tiro"
    assert _ok(BASE + "Foi um esforço leve.").aprovado
    assert _ok(BASE + "O erro padrão não aparece aqui.").motivos == ("linguagem_culpa",)  # "erro" é palavra de juízo, mesmo em outro sentido: limite conhecido


# --- elogio só com fato --------------------------------------------------------------------------------------------------------
def test_elogio_com_fato_passa_e_sem_fato_reprova():
    # F01: tudo dentro do normal e sem dor: o fato sustenta
    assert _ok(BASE + "Foi um ótimo treino.").aprovado
    # F02: o melhor pace está fora; F03: aprendendo; F05: com dor; F06: sem linha de base
    for caso in ("F02", "F03", "F05", "F06"):
        assert "elogio_sem_fato" in ck.checar_texto(O.PACOTES[caso], "Ótimo treino.\nLinha dois.\nLinha três.").motivos, caso


# --- forma ---------------------------------------------------------------------------------------------------------------------
def test_limites_de_linhas_e_de_caracteres():
    linha = "Foram 47 min."
    assert "forma_linhas" in _ok("\n".join([linha] * 2)).motivos
    assert "forma_linhas" not in _ok("\n".join([linha] * 3)).motivos
    assert "forma_linhas" not in _ok("\n".join([linha] * 5)).motivos
    assert "forma_linhas" in _ok("\n".join([linha] * 6)).motivos
    assert "forma_linhas" not in _ok("\n\n".join([linha] * 3)).motivos  # linha vazia não conta
    longa = "Foram 47 min " + "a " * 70 + "agora."
    assert len(longa) > 140 and "forma_tamanho_linha" in _ok(f"{longa}\n{linha}\n{linha}").motivos
    justa = ("Foram 47 min " + "a " * 70)[:139] + "."
    assert len(justa) == 140 and "forma_tamanho_linha" not in _ok(f"{justa}\n{linha}\n{linha}").motivos


@pytest.mark.parametrize("linha", ["**Foram** 47 min.", "# Foram 47 min.", "- Foram 47 min.", "1. Foram 47 min.", "> Foram 47 min.", "`Foram` 47 min."])
def test_markdown_reprova(linha):
    assert "forma_markdown" in _ok("Foram 47 min.\nForam 47 min.\n" + linha).motivos


# --- dor e atalhos -------------------------------------------------------------------------------------------------------------
DOR = ("Seu pace médio foi 6:00/km, perto da mediana de 5:56/km nos 10 treinos leves das últimas 12 semanas.\n"
       "Você marcou esforço 3 (moderado) e sensação 3 (normal).\n")


def test_dor_marcada_exige_a_frase_exata_uma_vez():
    f5 = O.PACOTES["F05"]
    assert ck.checar_texto(f5, DOR + "Você registrou dor neste treino.").aprovado
    for ruim in ("Você registrou o treino.", "Você registrou dor.", "Você registrou dor neste treino e dor de novo.",
                 "Você registrou dor no joelho neste treino.", "Você registrou dor neste treino. Mais dor depois.",
                 "Você registrou dor neste treino. Foi na perna."):
        assert "dor_regra" in ck.checar_texto(f5, DOR + ruim).motivos, ruim


def test_dor_nao_marcada_reprova_em_qualquer_forma():
    for frase in ("Você registrou dor neste treino.", "Foi doloroso.", "Sem dores.", "Dói."):
        assert "dor_nao_marcada" in _ok(BASE + frase).motivos, frase


def test_atalho_so_pode_ser_citado_se_marcado():
    # F04 marcou calor e cansaço
    f4 = O.PACOTES["F04"]
    base = ("Seu pace médio foi 6:00/km, 18 s/km mais lento que a mediana de 5:42/km nos 9 treinos longos das últimas 12 semanas.\n"
            "A FC média foi 158 bpm, 8 bpm acima da mediana de 150 bpm.\n")
    assert ck.checar_texto(f4, base + "Você marcou calor e cansaço.").aprovado
    assert ck.checar_texto(f4, base + "Você marcou calor e sono ruim.").motivos == ("atalho_nao_marcado",)
    assert ck.checar_texto(f4, base + "Você marcou estresse.").motivos == ("atalho_nao_marcado",)
    assert ck.checar_texto(f4, base + "Você marcou trabalho ou estresse.").motivos == ("atalho_nao_marcado",)
    assert "atalho_nao_marcado" in _ok(BASE + "Você marcou calor.").motivos  # F01 sem atalho


# --- nome e lugar ---------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("fim", ["Foi na Avenida Exemplo.", "Foi com a Maria.", "MARCADOR-SINTETICO-TEXTO-LIVRE."])
def test_nome_proprio_reprova(fim):
    assert "nome_fora_do_pacote" in _ok(BASE + f"Foram 47 min. {fim}").motivos


def test_siglas_do_pacote_e_comeco_de_frase_passam():
    assert _ok(BASE + "A FC e a PSE ficaram registradas. Foram 188 UA a 19 °C.").aprovado


# --- ordem e pureza ------------------------------------------------------------------------------------------------------------
def test_motivos_saem_sem_repeticao_e_na_ordem_da_lista():
    r = _ok("Eu acho que foi o dobro de 99 bpm porque sim!")
    assert list(r.motivos) == [m for m in ck.MOTIVOS if m in r.motivos]
    assert len(set(r.motivos)) == len(r.motivos)
    assert {"forma_linhas", "numero_por_extenso", "numero_fora_do_pacote", "linguagem_causa", "linguagem_quem_fala"} <= set(r.motivos)


def test_nao_altera_o_pacote_e_se_repete():
    import copy

    p = copy.deepcopy(O.PACOTES["F04"])
    _caso, texto = T.BONS["G04"]
    a = ck.checar_texto(p, texto)
    assert p == O.PACOTES["F04"] and a == ck.checar_texto(p, texto)


def test_o_modulo_e_puro_sem_rede_llm_banco_nem_log():
    fonte = inspect.getsource(ck)
    for proibido in ("httpx", "requests", "litellm", "urllib", "socket", "sqlalchemy", "logging", "print(", "open("):
        assert proibido not in fonte


def test_versao():
    assert ck.VERSAO == "checagens_feedback@2"


def test_checar_devolve_none_se_aprovado_e_um_codigo_se_reprovado():
    caso, texto = T.BONS["G01"]
    assert ck.checar(O.PACOTES[caso], texto) is None
    caso, texto, motivo, _ = T.RUINS["R05"]
    assert ck.checar(O.PACOTES[caso], texto) == motivo
    # com vários motivos, o primeiro da lista MOTIVOS
    assert ck.checar(O.PACOTES["F01"], "Eu acho que foi o dobro!") == "numero_por_extenso"


# --- checagens_feedback@2 (#355): forma pedida pelo Angelo em 11/11 ------------------------------------------------------------
def test_linha_sem_verbo_reprova_e_as_formas_dos_exemplos_aprovados_passam():
    assert "forma_sem_verbo" in _ok(BASE + "Treino leve, 47 min, 8,20 km e 188 UA.").motivos
    assert "forma_sem_verbo" in _ok(BASE + "Duração de 47 min e carga pela PSE de 188 UA.").motivos
    # formas curtas dos exemplos aprovados: "Sem ...", o gerúndio de G03 e a abertura descritiva do exemplo 6
    assert _ok(BASE + "Sem carga do relógio por enquanto.").aprovado
    assert ck._tem_verbo("Ainda aprendendo o seu normal em treino moderado: 3 de 8 treinos.")
    assert ck._tem_verbo("Natação de 1.600 m em 40 min, com FC média de 128 bpm.")
    assert ck._tem_verbo("Treino leve na esteira de 30 min e 5,00 km, com FC média de 140 bpm.")
    assert not ck._tem_verbo("Treino indoor, carga do relógio 20,0 pontos e 150 UA pela PSE.")  # sem "com FC média de": não é a abertura


@pytest.mark.parametrize("linha", ["Foram 47 min.", "A carga foi de 188 UA.", "Você marcou esforço 4.", "Isso é tudo.", "A FC ficou estável.",
                                   "O treino durou 47 min.", "Você percorreu 8,20 km.", "Você nadou 1.600 m.", "As métricas estão no pacote."])
def test_verbos_aceitos(linha):
    assert ck._tem_verbo(linha)


@pytest.mark.parametrize("linha", ["Seu pace.", "Carga pela PSE de 188 UA.", "Esforço 4, sensação 4.", "O seu normal."])
def test_sem_verbo_nao_e_aceito(linha):
    assert not ck._tem_verbo(linha)


def test_pois_e_ja_que_sao_causa():
    for frase in ("Foi assim, pois o dia ajudou.", "Foi assim, já que o dia ajudou.", "Foi assim visto que o dia ajudou."):
        assert _ok(BASE + frase).motivos == ("linguagem_causa",), frase
    assert _ok(BASE + "Foi um treino de 47 min nos pontos do pacote.").aprovado  # "pontos" não é "pois"


@pytest.mark.parametrize("frase", ["A FC foi 146 bpm, dentro da mediana de 148 bpm.", "A FC foi 146 bpm, dentro de mediana.",
                                   "A FC foi 146 bpm, dentro da sua mediana de 148 bpm."])
def test_dentro_da_mediana_reprova(frase):
    assert "comparacao_mediana" in _ok(BASE + frase).motivos


def test_formas_certas_de_dizer_a_comparacao_passam():
    assert _ok(BASE + "A FC foi 146 bpm, perto da mediana de 148 bpm.").motivos == ("conclusao_repetida",)  # "perto da mediana" já abriu o texto
    f2 = T.BONS["G02"][1]
    assert "(mediana de 172 bpm)" in f2 and ck.checar_texto(O.PACOTES["F02"], f2).aprovado  # "dentro do seu normal (mediana de ...)"


def test_conclusao_repetida_em_duas_linhas():
    assert "conclusao_repetida" in _ok(BASE + "Foi tudo dentro do seu normal.").motivos
    # conclusões diferentes em linhas diferentes passam: "perto da mediana" (linha 1) e "dentro do seu normal" (linha 2)
    assert ck.checar_texto(O.PACOTES["F01"], T.BONS["G01"][1]).aprovado
    assert ck.checar_texto(O.PACOTES["F06"], T.BONS["G06"][1]).aprovado
    # F06: "sem comparação" em duas linhas
    texto = T.BONS["G06"][1].replace("A natação não tem carga do relógio; a carga pela PSE foi 200 UA.", "Foi sem comparação com o seu histórico.")
    assert "conclusao_repetida" in ck.checar_texto(O.PACOTES["F06"], texto).motivos


def test_versao_2_e_codigos_novos():
    assert ck.VERSAO == "checagens_feedback@2"
    assert {"forma_sem_verbo", "conclusao_repetida", "comparacao_mediana"} <= set(ck.MOTIVOS)
