"""Checagens do texto final do chat (issue #595, ADR 0017, item 4): `checagens_chat@1`.

Função pura: sem banco, sem rede, sem IA, sem log. Confere o texto contra os **resultados das ferramentas daquela pergunta** (lista de
`{nome, argumentos, resultado}`) e devolve se foi aprovado e, se não, só os **códigos** dos motivos: nunca o texto nem o termo que reprovou
(pergunta, resposta e resultado são dado de saúde). Texto reprovado é descartado pelo chamador e o atleta recebe uma frase fixa.

A recusa (`fora_do_tema`) e o encaminhamento ao professor (`pedido_de_mudanca`) são **textos fixos do código** (`TEXTOS_FIXOS`), devolvidos quando o
modelo chama `recusar`; um texto do modelo numa pergunta que ele mesmo classificou como recusável reprova (`fora_do_escopo_respondido`).

Fonte: regra própria do projeto, sem artigo (ADR 0017, decisões do Angelo de 10/11 e 28/11). Reusa as funções puras e as listas da
`checagens_feedback@6` (conferência de números, linguagem proibida, nome próprio). Mudar uma lista de lá obriga a rever esta e a subir as duas
versões. Qualquer mudança de regra ou de limite sobe ``VERSAO`` (gravada em `mensagem.versao_checagens`).
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any

from app.explicacao import checagens as fb

VERSAO = "checagens_chat@1"
Resultado = fb.Resultado

LINHAS_MAX = 8
TEXTO_MAX_CARACTERES = 900

TEXTOS_FIXOS = {
    "fora_do_tema": "Eu respondo perguntas sobre os seus treinos. Pergunte, por exemplo, sobre o seu pace, a sua carga ou como foi a sua semana.",
    "pedido_de_mudanca": "Mudar o treino é com o seu professor. Posso mostrar o que os seus treinos dizem, se isso ajudar na conversa com ele.",
}
FRASE_DOR = fb.FRASE_DOR

MOTIVOS = (
    "numero_fora_dos_resultados", "numero_por_extenso", "unidade_trocada", "sem_ferramenta", "dado_ausente_afirmado",
    "linguagem_diagnostico", "linguagem_culpa", "linguagem_promessa", "linguagem_causa", "linguagem_julgamento", "linguagem_quem_fala",
    "prescricao", "comparacao_sem_ferramenta", "dor_regra", "forma", "fora_do_escopo_respondido",
)
_DE_NUMERO = {"numero_fora_do_pacote": "numero_fora_dos_resultados", "numero_por_extenso": "numero_por_extenso", "unidade_trocada": "unidade_trocada"}

# Julgamento: elogio e juízo de valor. As palavras de comparação (melhorou, evoluiu...) ficam à parte, em COMPARACAO, porque só se dizem com `direcao`.
_VERBOS_DE_COMPARACAO = {"melhorou", "melhora", "melhorar", "evolucao", "evoluindo", "evoluiu", "progresso", "superou", "superar"}
JULGAMENTO = tuple(t for t in fb.ELOGIO if t not in _VERBOS_DE_COMPARACAO) + ("em forma", "boa forma", "forma otima", "bom ritmo", "ritmo bom", "muito melhor", "muito pior")
COMPARACAO = tuple(sorted(_VERBOS_DE_COMPARACAO)) + (
    "piorou", "mais rapido", "mais rapida", "mais lento", "mais lenta", "subiu", "caiu", "aumentou", "diminuiu", "a mais", "a menos",
    "maior que", "menor que", "melhor que", "muito melhor", "mais alto", "mais alta", "mais baixo", "mais baixa", "mais que", "menos que", "bem mais", "bem menos",
)
PRESCRICAO = tuple(t for t in fb.CONSELHO if t not in ("recuperacao", "descanso")) + (
    "faca", "faca mais", "treine", "troque", "siga", "deveria", "monte", "pegue leve", "reduzir", "aumentar", "repetir", "plano de",
    "o melhor e",
)
SIGLAS = fb.SIGLAS_PERMITIDAS | {"CTL", "ATL", "TSB", "VFC"}
_DOR = re.compile(r"(?<!\w)(dor|dores|doer|doi|doloroso|dolorosa|dolorido|dolorida)(?!\w)")
_ENTRE_ASPAS = re.compile(r'"([^"]*)"')
_LINK = re.compile(r"https?://|www\.|\[\[")


def _resultados(ferramentas: Sequence[Mapping[str, Any]]) -> list[Any]:
    return [f.get("resultado") for f in ferramentas if f.get("resultado") is not None]


def _percorrer(x: Any):
    yield x
    if isinstance(x, Mapping):
        for v in x.values():
            yield from _percorrer(v)
    elif isinstance(x, (list, tuple)):
        for v in x:
            yield from _percorrer(v)


def _valores(resultados: list[Any], chave: str) -> list[Any]:
    return [v for r in resultados for no in _percorrer(r) if isinstance(no, Mapping) for k, v in no.items() if k == chave]


def _consultas_ok(ferramentas: Sequence[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    return [f for f in ferramentas if f.get("nome") != "recusar" and isinstance(f.get("resultado"), Mapping) and f["resultado"].get("estado") != "erro"]


def _sem_aspas_da_observacao(texto: str, resultados: list[Any]) -> str:
    """Tira do texto o que o atleta escreveu e a resposta cita entre aspas (`observacao_texto`): é fala dele, não do app (ADR 0017, item 6)."""
    obs = {str(o).strip().casefold() for o in _valores(resultados, "observacao_texto")}
    return _ENTRE_ASPAS.sub(lambda m: " " if m.group(1).strip().casefold() in obs else m.group(0), texto)


def _forma(texto: str, linhas: list[str]) -> bool:
    return (len(linhas) > LINHAS_MAX or len(texto) > TEXTO_MAX_CARACTERES or bool(re.search(r"[*`]|__", texto))
            or any(re.match(r"\s*(#|>|[-•]\s|\d+[.)]\s)", x) for x in linhas) or bool(_LINK.search(texto)) or fb._emoji(texto))


def _mascarar_rotulos(plano: str, resultados: list[Any]) -> str:
    """Tira o que o app escreve de propósito: o rótulo da sensação que o resultado traz ("mal", "muito bem") e a frase "sono ruim" do atalho."""
    for rotulo in {fb._plano(str(v)) for v in _valores(resultados, "sensacao_texto") if v}:
        plano = re.sub(rf"(?<!\w){re.escape(rotulo)}(?!\w)", " ", plano)
    return plano.replace("sono ruim", " ")


def _comparacao(plano: str, resultados: list[Any]) -> bool:
    """Palavra de comparação só com um resultado que traga `direcao` maior ou menor; o `diferenca_texto` do resultado, citado, não conta como palavra."""
    for d in _valores(resultados, "diferenca_texto"):
        plano = plano.replace(fb._plano(str(d)), " ")
    if not fb._tem_termo(plano, COMPARACAO):
        return False
    return not any(d in ("maior", "menor") for d in _valores(resultados, "direcao"))


def _dado_ausente(resultados: list[Any]) -> bool:
    """Todo resultado diz que não há dado (`sem_dados`, ou clima `indoor`): o texto não pode trazer valor que ele não tem."""
    if not resultados:
        return False
    return all(
        (isinstance(r, Mapping) and r.get("estado") == "sem_dados") or any(c in ("indoor", "sem_dados") for c in _valores([r], "estado"))
        for r in resultados
    )


def _dor(plano: str, resultados: list[Any]) -> bool:
    marcada = any("dor" in (a or []) for a in _valores(resultados, "atalhos"))
    palavras = len(_DOR.findall(plano))
    if marcada:
        return fb._plano(FRASE_DOR) not in plano or palavras != 1 or fb._tem_termo(plano, fb.PARTES_DO_CORPO)
    return bool(palavras)


def checar_texto(ferramentas: Sequence[Mapping[str, Any]], texto: str) -> Resultado:
    """Confere o `texto` do modelo contra os resultados das `ferramentas` chamadas naquela pergunta (ADR 0017, item 4).

    `ferramentas`: lista de `{nome, argumentos, resultado}` na ordem das chamadas. Aprovado só se nenhuma checagem reprovar.
    """
    linhas = [x for x in texto.split("\n") if x.strip()]
    resultados = _resultados(ferramentas)
    plano = fb._plano(texto)
    mascarado = _mascarar_rotulos(plano, resultados)
    achados: set[str] = set()
    if any(f.get("nome") == "recusar" for f in ferramentas):
        achados.add("fora_do_escopo_respondido")  # a recusa é o texto fixo do código; texto do modelo aqui nunca é mostrado
    for m in fb._numeros({"resultados": resultados}, texto, plano):
        achados.add(_DE_NUMERO[m])
    if not _consultas_ok(ferramentas) and any(True for _ in fb._numeros_do_texto(texto)):
        achados.add("sem_ferramenta")
    if _dado_ausente(resultados) and achados & {"numero_fora_dos_resultados", "unidade_trocada"}:
        achados.add("dado_ausente_afirmado")
    if _forma(texto, linhas):
        achados.add("forma")
    if fb._nome_proprio(_trocar_siglas(_sem_aspas_da_observacao(texto, resultados))):
        achados.add("forma")
    if fb._tem_termo(mascarado, fb.DIAGNOSTICO):
        achados.add("linguagem_diagnostico")
    if fb._tem_termo(mascarado, fb.CULPA):
        achados.add("linguagem_culpa")
    if fb._tem_termo(mascarado, fb.PROMESSA):
        achados.add("linguagem_promessa")
    if fb._tem_termo(mascarado, fb.CAUSA) or any(re.search(p, mascarado) for p in fb.CAUSA_PADROES):
        achados.add("linguagem_causa")
    if fb._tem_termo(mascarado, JULGAMENTO):
        achados.add("linguagem_julgamento")
    if fb._tem_termo(mascarado, PRESCRICAO):
        achados.add("prescricao")
    if _comparacao(plano, resultados):
        achados.add("comparacao_sem_ferramenta")
    if _dor(plano, resultados):
        achados.add("dor_regra")
    falado = _sem_aspas_da_observacao(texto, resultados)
    if fb._tem_termo(fb._plano(falado), fb.QUEM_FALA) or "!" in falado:
        achados.add("linguagem_quem_fala")
    motivos = tuple(m for m in MOTIVOS if m in achados)
    return Resultado(aprovado=not motivos, motivos=motivos)


def _trocar_siglas(texto: str) -> str:
    """CTL, ATL, TSB e VFC não são nomes próprios (a lista da `checagens_feedback` só conhece FC, PSE, UA e °C)."""
    return re.sub(rf"(?<!\w)(?:{'|'.join(sorted(SIGLAS))})(?!\w)", "x", texto)


def texto_da_recusa(motivo: str) -> str:
    """O que o atleta lê quando o modelo chama `recusar`. Motivo desconhecido cai na recusa de tema."""
    return TEXTOS_FIXOS.get(motivo, TEXTOS_FIXOS["fora_do_tema"])
