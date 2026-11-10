"""Checagens do texto do feedback (issue #325, ADR 0013, item 4): `checagens_feedback@1`.

Função pura: sem banco, sem rede, sem IA, sem log. Confere um texto contra o pacote de fatos (`fatos_treino@1`) e devolve se foi aprovado e, se não,
os **códigos** dos motivos. Texto reprovado é descartado pelo chamador (nunca gravado nem mostrado) e a nova tentativa fica para a próxima execução
do worker (decisão 8 da ADR). **O resultado nunca repete o texto nem o termo que reprovou**: só códigos, para que nada do texto (dado de saúde)
vá parar em log. Lista de linguagem proibida e regras em docs/metricas/checagens-feedback.md.

Fonte: regra própria do projeto, sem artigo (ADR 0013, "Fontes"): decisões do Angelo de 10/11 (tom aprovado, observação positiva só com fato,
clima e check-in lado a lado, dor numa frase neutra) e a lista de linguagem proibida da ADR, ampliada nesta versão. Qualquer mudança de lista,
de regra ou de limite exige subir ``VERSAO`` (a versão é gravada junto do feedback).
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from typing import Any

VERSAO = "checagens_feedback@1"

LINHAS_MIN, LINHAS_MAX = 3, 5  # ADR 0013, item 4.3
LINHA_MAX_CARACTERES = 140
TEXTO_MAX_CARACTERES = 700  # o CHECK da coluna `feedback_treino.texto`

FRASE_DOR = "Você registrou dor neste treino."  # decisão 7: sempre esta, sem conselho, sem parte do corpo

# Códigos de motivo, na ordem em que saem. A descrição de cada um está na nota da métrica.
MOTIVOS = (
    "numero_fora_do_pacote", "numero_por_extenso", "unidade_trocada",
    "linguagem_diagnostico", "linguagem_culpa", "linguagem_promessa", "linguagem_causa", "linguagem_conselho", "linguagem_quem_fala",
    "elogio_sem_fato", "forma_linhas", "forma_tamanho_linha", "forma_markdown",
    "dor_regra", "dor_nao_marcada", "atalho_nao_marcado", "nome_fora_do_pacote",
)

# --- Listas de linguagem proibida --------------------------------------------------------------------------------------------
# Comparadas sem acento e sem diferença de maiúscula, como palavra inteira (ou expressão inteira). Mudar uma lista sobe VERSAO.
DIAGNOSTICO = (
    "lesao", "lesoes", "lesionado", "lesionada", "inflamacao", "tendinite", "fratura", "distensao", "overtraining", "sobretreino",
    "supertreino", "doenca", "infeccao", "sintoma", "sintomas", "diagnostico", "sindrome", "arritmia", "desidratacao", "desidratado",
)
CULPA = (
    "falhou", "fracasso", "fracassou", "preguica", "desleixo", "culpa", "fraco", "fraca", "decepcionante", "voce deveria", "voce devia",
    "pessimo", "horrivel", "treino ruim", "mau treino", "ruim", "mau",
)
PROMESSA = (
    "vai melhorar", "com certeza", "certamente", "garanto", "prometo", "garantido", "voce vai conseguir", "na proxima sera", "em breve voce",
)
CAUSA = (
    "porque", "por causa", "por conta", "devido", "gracas a", "se deve", "foi por isso", "por isso", "causou", "explica", "explicam",
    "pode ter sido", "deve ter sido", "possivelmente", "provavelmente", "talvez", "pesou", "afetou", "atrapalhou", "influenciou",
    "contribuiu", "impactou", "consequencia",
)
CAUSA_PADROES = (r"resultado d[oae]s?",)  # "resultado do calor", "resultado da carga"
CONSELHO = (
    "descanse", "descansar", "procure", "consulte", "evite", "tente", "recomendo", "sugiro", "o ideal", "precisa", "nao esqueca", "cuide",
    "hidrate", "beba", "medico", "fisioterapeuta", "fique de olho", "vale a pena", "convem", "mantenha", "continue", "aumente", "reduza",
    "diminua", "voce deve",
)
QUEM_FALA = (
    "professor", "professora", "treinador", "treinadora", "tecnico", "coach", "eu", "meu", "minha", "meus", "minhas", "nosso", "nossa",
    "nossos", "nossas", "inteligencia artificial", "modelo de linguagem", "ola",
)
QUEM_FALA_COM_ACENTO = ("nós",)  # "nos" (em + os) é preposição e aparece nos textos bons: só vale com o acento
ELOGIO = (
    "otimo", "otima", "excelente", "parabens", "muito bem", "bom treino", "bom trabalho", "bem feito", "mandou bem", "incrivel", "arrasou",
    "orgulho", "evolucao", "evoluindo", "caprichou", "perfeito", "perfeita", "maravilhoso", "melhorou", "melhora", "progresso", "superou",
)
PARTES_DO_CORPO = (
    "joelho", "joelhos", "tornozelo", "canela", "panturrilha", "coxa", "quadril", "costas", "ombro", "tendao", "musculo", "perna", "pernas",
    "gluteo", "lombar", "coluna", "calcanhar", "pulso", "cotovelo", "peito", "barriga", "pescoco",
)
# O que cada atalho escreve no texto (ADR 0013, item 4.4). Só os marcados podem aparecer.
TERMOS_DO_ATALHO = {
    "cansaco": ("cansaco", "cansado", "cansada"),
    "sono_ruim": ("sono ruim",),
    "calor": ("calor",),
    "trabalho_estresse": ("trabalho ou estresse", "estresse"),
}
EXTENSO = (
    "dois", "duas", "tres", "quatro", "cinco", "seis", "sete", "oito", "nove", "dez", "onze", "doze", "treze", "quatorze", "quinze",
    "dezesseis", "dezessete", "dezoito", "dezenove", "vinte", "trinta", "quarenta", "cinquenta", "sessenta", "setenta", "oitenta",
    "noventa", "cem", "cento", "mil", "metade", "dobro", "triplo", "dezena", "duzia",
)  # "um" e "uma" ficam de fora: como artigo passam
SIGLAS_PERMITIDAS = frozenset({"FC", "PSE", "UA", "C"})  # o "C" de "°C"

# unidade de cada campo numérico do pacote (o que o texto pode escrever depois do número)
_UNIDADE_DO_CAMPO = {"temperatura_c": "°c", "sensacao_termica_c": "°c", "umidade_pct": "%", "vento_kmh": "km/h", "fc_media_bpm": "bpm",
                     "duracao_s": "s", "distancia_m": "m"}

_UNIDADES = r"pontos/h|pontos|s/km|km/h|km|bpm|min|ua|°\s?c|%|/km|m|s|h"
_NUMERO = r"(?<![\w:,.])(\d{1,3}(?:\.\d{3})+(?:,\d+)?|\d+:\d{2}|\d+(?:,\d+)?)"
_NUM_UNIDADE = re.compile(_NUMERO + rf"(?:\s?({_UNIDADES})(?![\w]))?")


@dataclass(frozen=True)
class Resultado:
    aprovado: bool
    motivos: tuple[str, ...]  # códigos de MOTIVOS, sem repetição, na ordem de MOTIVOS; vazio se aprovado


def _sem_acento(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))


def _plano(s: str) -> str:
    """Minúsculo e sem acento, para comparar com as listas."""
    return _sem_acento(s).casefold()


def _tem_termo(plano: str, termos: tuple[str, ...]) -> bool:
    return any(re.search(rf"(?<!\w){re.escape(t)}(?!\w)", plano) for t in termos)


def _unidade(u: str | None) -> str | None:
    return None if u is None else re.sub(r"\s", "", u)


def _numeros_do_texto(texto: str) -> Iterator[tuple[str, str | None]]:
    for m in _NUM_UNIDADE.finditer(texto.casefold()):
        yield m.group(1), _unidade(m.group(2))


def _formas(x: float) -> set[str]:
    """Como um número do pacote pode aparecer escrito: inteiro, ou com vírgula."""
    f = {f"{x:.1f}".replace(".", ","), str(x).replace(".", ",")} if isinstance(x, float) else {str(x)}
    if float(x).is_integer():
        f.add(str(int(x)))
    return f


def _coletar(pacote: Any, pares: set[tuple[str, str]], soltos: set[str], campo: str = "") -> None:
    """Todo número que o pacote traz: os dos `*_texto` (com a unidade escrita) e os valores numéricos (com a unidade do campo)."""
    if isinstance(pacote, Mapping):
        for k, v in pacote.items():
            if k != "versao":  # "carga@2" não é um número do treino
                _coletar(v, pares, soltos, k)
    elif isinstance(pacote, (list, tuple)):
        for v in pacote:
            _coletar(v, pares, soltos, campo)
    elif isinstance(pacote, str):
        for num, un in _numeros_do_texto(pacote):
            soltos.add(num)
            if un:
                pares.add((num, un))
    elif isinstance(pacote, (int, float)) and not isinstance(pacote, bool):
        for f in _formas(pacote):
            soltos.add(f)
            if campo in _UNIDADE_DO_CAMPO:
                pares.add((f, _UNIDADE_DO_CAMPO[campo]))


def _numeros(pacote: Mapping[str, Any], texto: str, plano: str) -> set[str]:
    pares: set[tuple[str, str]] = set()
    soltos: set[str] = set()
    _coletar(pacote, pares, soltos)
    motivos: set[str] = set()
    for num, un in _numeros_do_texto(texto):
        if un is not None:
            if (num, un) in pares:
                continue
            motivos.add("unidade_trocada" if num in soltos else "numero_fora_do_pacote")
        elif num not in soltos:
            motivos.add("numero_fora_do_pacote")
    if _tem_termo(plano, EXTENSO):
        motivos.add("numero_por_extenso")
    return motivos


def _mascarar_rotulos(plano: str, pacote: Mapping[str, Any]) -> str:
    """Tira do texto o que o app escreve de propósito e as listas pegariam: os rótulos da PSE e da sensação, entre parênteses
    ("(muito bem)", "(repouso)"), e a frase exata "sono ruim" (o rótulo do atalho; ADR 0013, item 4.2)."""
    ck = pacote.get("checkin") or {}
    for rotulo in (ck.get("pse_texto"), ck.get("sensacao_texto")):
        if rotulo:
            plano = plano.replace(f"({_plano(str(rotulo))})", " ")
    return plano.replace("sono ruim", " ")


def _emoji(texto: str) -> bool:
    return any(ord(c) >= 0x1F000 or 0x2600 <= ord(c) <= 0x27BF or ord(c) == 0xFE0F for c in texto)


def _elogio_sustentado(pacote: Mapping[str, Any]) -> bool:
    """A observação positiva só vale quando um fato do pacote a sustenta (decisão 1 de 10/11): linha de base `ok`, ao menos uma métrica
    `dentro`, nenhuma `fora`, e sem o atalho dor (com dor, sem elogio em volta, decisão 7)."""
    lb = pacote.get("linha_base") or {}
    estados = [m.get("estado") for m in lb.get("metricas") or []]
    com_dor = "dor" in ((pacote.get("checkin") or {}).get("atalhos") or [])
    return lb.get("estado") == "ok" and "dentro" in estados and "fora" not in estados and not com_dor


def _nome_proprio(texto: str) -> bool:
    """Palavra com inicial maiúscula fora do começo de frase, ou em maiúsculas em qualquer lugar, que não seja sigla do pacote (FC, PSE, UA, °C)."""
    for m in re.finditer(r"[A-ZÀ-Ý][\wÀ-ÿ-]*", texto):
        palavra = m.group(0)
        if palavra in SIGLAS_PERMITIDAS:
            continue
        if len(palavra) > 1 and palavra.isupper():  # sigla ou marcador que não é do pacote, mesmo no começo da frase
            return True
        antes = texto[: m.start()].rstrip(" *_#>-•`\t")
        if antes == "" or antes[-1] in ".!?\n":
            continue
        return True
    return False


def _forma(texto: str, linhas: list[str]) -> set[str]:
    motivos: set[str] = set()
    if not LINHAS_MIN <= len(linhas) <= LINHAS_MAX:
        motivos.add("forma_linhas")
    if len(texto) > TEXTO_MAX_CARACTERES or any(len(x) > LINHA_MAX_CARACTERES for x in linhas):
        motivos.add("forma_tamanho_linha")
    if re.search(r"[*`]|__", texto) or any(re.match(r"\s*(#|>|[-•]\s|\d+[.)]\s)", x) for x in linhas):
        motivos.add("forma_markdown")
    return motivos


def _linguagem(texto: str, plano: str, pacote: Mapping[str, Any]) -> set[str]:
    m = _mascarar_rotulos(plano, pacote)
    motivos: set[str] = set()
    if _tem_termo(m, DIAGNOSTICO):
        motivos.add("linguagem_diagnostico")
    if _tem_termo(m, CULPA):
        motivos.add("linguagem_culpa")
    if _tem_termo(m, PROMESSA):
        motivos.add("linguagem_promessa")
    if _tem_termo(m, CAUSA) or any(re.search(p, m) for p in CAUSA_PADROES):
        motivos.add("linguagem_causa")
    if _tem_termo(m, CONSELHO):
        motivos.add("linguagem_conselho")
    if (_tem_termo(m, QUEM_FALA) or "!" in texto or _emoji(texto)
            or any(re.search(rf"(?<!\w){t}(?!\w)", texto.casefold()) for t in QUEM_FALA_COM_ACENTO)):
        motivos.add("linguagem_quem_fala")
    if _tem_termo(m, ELOGIO) and not _elogio_sustentado(pacote):
        motivos.add("elogio_sem_fato")
    return motivos


def _dor_e_atalhos(plano: str, pacote: Mapping[str, Any]) -> set[str]:
    atalhos = set((pacote.get("checkin") or {}).get("atalhos") or [])
    motivos: set[str] = set()
    palavras_dor = len(re.findall(r"(?<!\w)(dor|dores|doer|doi|doloroso|dolorosa|dolorido|dolorida)(?!\w)", plano))
    if "dor" in atalhos:
        if _plano(FRASE_DOR) not in plano or palavras_dor != 1 or _tem_termo(plano, PARTES_DO_CORPO):
            motivos.add("dor_regra")
    else:
        if palavras_dor:
            motivos.add("dor_nao_marcada")
        if _tem_termo(plano, PARTES_DO_CORPO):
            motivos.add("nome_fora_do_pacote")
    for atalho, termos in TERMOS_DO_ATALHO.items():
        if atalho not in atalhos and _tem_termo(plano, termos):
            motivos.add("atalho_nao_marcado")
    return motivos


def checar_texto(pacote: Mapping[str, Any], texto: str) -> Resultado:
    """Confere `texto` contra o `pacote` (`fatos_treino@1`). Aprovado só se **nenhuma** checagem reprovar.

    1. Todo número do texto está no pacote (valor ou `*_texto`), com a mesma unidade; número por extenso reprova.
    2. Nenhum termo da lista de linguagem proibida (diagnóstico, culpa, promessa, causa, conselho, quem fala) e elogio só com fato.
    3. Forma: 3 a 5 linhas de até 140 caracteres (700 no total), sem Markdown.
    4. Dor: com o atalho, exatamente a frase da decisão 7 e nenhuma outra menção; sem o atalho, nada de dor. Só se cita atalho marcado.
    5. Nada que não vem do pacote: nome próprio, lugar ou o texto livre (maiúscula fora de começo de frase que não seja sigla do pacote).
    """
    linhas = [x for x in texto.split("\n") if x.strip()]
    plano = _plano(texto)
    achados = _forma(texto, linhas) | _numeros(pacote, texto, plano) | _linguagem(texto, plano, pacote) | _dor_e_atalhos(plano, pacote)
    if _nome_proprio(texto):
        achados.add("nome_fora_do_pacote")
    motivos = tuple(m for m in MOTIVOS if m in achados)
    return Resultado(aprovado=not motivos, motivos=motivos)


def checar(pacote: Mapping[str, Any], texto: str) -> str | None:
    """Forma que o `worker.gerar_feedback` usa (injeção): ``None`` se aprovado; senão **um** código curto de motivo (o primeiro de MOTIVOS).

    O código nunca repete o texto nem o termo que reprovou. Quem precisa de todos os motivos usa ``checar_texto``.
    """
    r = checar_texto(pacote, texto)
    return None if r.aprovado else r.motivos[0]
