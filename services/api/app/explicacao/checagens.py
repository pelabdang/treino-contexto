"""Checagens do texto do feedback (issue #325, ADR 0013, item 4): `checagens_feedback@6`.

Função pura: sem banco, sem rede, sem IA, sem log. Confere um texto contra o pacote de fatos (`fatos_treino@2`) e devolve se foi aprovado e, se não,
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

VERSAO = "checagens_feedback@6"

LINHAS_MIN, LINHAS_MAX = 3, 5  # ADR 0013, item 4.3
LINHA_MAX_CARACTERES = 140
TEXTO_MAX_CARACTERES = 700  # o CHECK da coluna `feedback_treino.texto`

FRASE_DOR = "Você registrou dor neste treino."  # decisão 7: sempre esta, sem conselho, sem parte do corpo

# Códigos de motivo, na ordem em que saem. A descrição de cada um está na nota da métrica.
MOTIVOS = (
    "numero_fora_do_pacote", "numero_por_extenso", "unidade_trocada",
    "linguagem_diagnostico", "linguagem_culpa", "linguagem_promessa", "linguagem_causa", "linguagem_conselho", "linguagem_quem_fala",
    "elogio_sem_fato", "forma_linhas", "forma_tamanho_linha", "forma_markdown", "forma_sem_verbo", "conclusao_repetida", "comparacao_mediana", "numero_repetido",
    "dor_regra", "dor_nao_marcada", "atalho_nao_marcado", "nome_fora_do_pacote",
    # checagens_feedback@4 (#375, ADR 0014, item 6): a recuperação da noite
    "linguagem_julgamento", "recuperacao_mistura", "recuperacao_forma", "recuperacao_outro_dia", "recuperacao_sem_pacote",
    # checagens_feedback@5 (#403): a linha de "aprendendo" e a concordância das siglas femininas
    "recuperacao_sem_aprendendo", "concordancia_sigla",
    # checagens_feedback@6 (#405): o que o texto diz do clima tem de bater com `clima.estado`
    "clima_estado",
)

# --- Listas de linguagem proibida --------------------------------------------------------------------------------------------
# Comparadas sem acento e sem diferença de maiúscula, como palavra inteira (ou expressão inteira). Mudar uma lista sobe VERSAO.
DIAGNOSTICO = (
    "lesao", "lesoes", "lesionado", "lesionada", "inflamacao", "tendinite", "fratura", "distensao", "overtraining", "sobretreino",
    "supertreino", "doenca", "infeccao", "sintoma", "sintomas", "diagnostico", "sindrome", "arritmia", "desidratacao", "desidratado",
    "fadiga", "esgotamento", "exaustao", "risco",
    # @4: termos fisiológicos e métricas proprietárias que o pacote não traz (ADR 0014, item 6.A)
    "insonia", "apneia", "sistema nervoso", "parassimpatico", "simpatico", "overreaching", "prontidao", "bateria", "body battery",
    "estado de treino", "readiness", "ansiedade",
)
# --- Recuperação (checagens_feedback@4, ADR 0014, item 6): valem só na LINHA que fala de sono, VFC ou FC de repouso ------------------
REC_CAUSA = (
    "por isso", "entao", "portanto", "logo", "assim", "dai", "reflete", "refletiu", "reflexo", "influenciou", "influencia", "afetou", "impactou",
    "pesou", "contribuiu", "efeito do sono", "efeito da noite", "explica", "o sono explica", "culpa do sono", "mesmo com", "apesar de",
    "apesar do", "mesmo assim", "mas", "porem", "no entanto", "enquanto",
)
REC_JULGAMENTO = (
    "noite ruim", "noite boa", "mal dormido", "mal dormiu", "dormiu mal", "dormiu bem", "sono curto", "sono bom", "sono pouco",
    "sono insuficiente", "pouco sono", "sono ruim", "bem recuperado", "mal recuperado", "recuperado", "descansado", "cansado",
    "vfc baixa", "vfc alta", "fc de repouso alta", "fc de repouso baixa", "melhor", "pior", "boa recuperacao", "ma recuperacao",
    "ruim",
)
REC_OUTRO_DIA = (
    "ontem", "anteontem", "semana", "semanas", "ultimos dias", "dias", "media de", "segunda", "terca", "quarta", "quinta", "sexta",
    "sabado", "domingo", "segunda-feira", "terca-feira", "quarta-feira", "quinta-feira", "sexta-feira",
)
# Vocabulário de OUTRA medida: a linha da recuperação não divide a linha com o resultado (regra 1).
REC_MISTURA = (
    "pace", "ritmo", "velocidade", "desempenho", "resultado", "fc", "carga", "esforco", "sensacao", "pse", "temperatura", "clima",
    "umidade", "vento", "tiro", "tiros", "km", "pontos", "ua", "calor", "marcou",
)
FRASE_SEM_DADO = "Sem dado de sono, VFC e FC de repouso da noite anterior."  # ADR 0014, item 4 (motivo sem_noite)
CULPA = (
    "falhou", "fracasso", "fracassou", "preguica", "desleixo", "culpa", "fraco", "fraca", "decepcionante", "voce deveria", "voce devia",
    "pessimo", "horrivel", "treino ruim", "mau treino", "ruim", "mau",
    "preocupante", "alerta", "problema", "pior", "erro", "mal",  # "mal" só passa como rótulo da sensação 2 do pacote (ver _mascarar_rotulos)
)
PROMESSA = (
    "vai melhorar", "com certeza", "certamente", "garanto", "prometo", "garantido", "voce vai conseguir", "na proxima sera", "em breve voce",
)
CAUSA = (
    "porque", "por causa", "por conta", "devido", "gracas a", "se deve", "foi por isso", "por isso", "causou", "explica", "explicam",
    "pode ter sido", "deve ter sido", "possivelmente", "provavelmente", "talvez", "pesou", "afetou", "atrapalhou", "influenciou",
    "contribuiu", "impactou", "consequencia",
    "pois", "ja que", "visto que",
    "indica que", "indicam que", "mostra que", "mostram que", "significa", "reflete", "reflexo", "em razao", "motivo", "efeito",
)
CAUSA_PADROES = (r"resultado d[oae]s?",)  # "resultado do calor", "resultado da carga"
CONSELHO = (
    "descanse", "descansar", "procure", "consulte", "evite", "tente", "recomendo", "sugiro", "o ideal", "precisa", "nao esqueca", "cuide",
    "hidrate", "beba", "medico", "fisioterapeuta", "fique de olho", "vale a pena", "convem", "mantenha", "continue", "aumente", "reduza",
    "diminua", "voce deve",
    "descanso", "recuperacao", "fique atento", "fique atenta", "prefira", "considere", "lembre-se", "priorize",
    # @4 (ADR 0014, item 6.A): conselho sobre o sono vale no texto inteiro
    "durma", "dormir mais", "dormir cedo", "va dormir", "o ideal e dormir",
)
QUEM_FALA = (
    "professor", "professora", "treinador", "treinadora", "tecnico", "coach", "eu", "meu", "minha", "meus", "minhas", "nosso", "nossa",
    "nossos", "nossas", "inteligencia artificial", "modelo de linguagem", "ola",
    "vamos", "estou", "sou", "acho", "penso", "notei",
)
QUEM_FALA_COM_ACENTO = ("nós",)  # "nos" (em + os) é preposição e aparece nos textos bons: só vale com o acento
ELOGIO = (
    "otimo", "otima", "excelente", "parabens", "muito bem", "bom treino", "bom trabalho", "bem feito", "mandou bem", "incrivel", "arrasou",
    "orgulho", "evolucao", "evoluindo", "caprichou", "perfeito", "perfeita", "maravilhoso", "melhorou", "melhora", "progresso", "superou",
    "evoluiu", "superar", "melhorar",
)
PARTES_DO_CORPO = (
    "joelho", "joelhos", "tornozelo", "canela", "panturrilha", "coxa", "quadril", "costas", "ombro", "tendao", "musculo", "perna", "pernas",
    "gluteo", "lombar", "coluna", "calcanhar", "pulso", "cotovelo", "peito", "barriga", "pescoco",
)
# O que cada atalho escreve no texto (ADR 0013, item 4.4). Só os marcados podem aparecer.
TERMOS_DO_ATALHO = {
    "cansaco": ("cansaco", "cansado", "cansada"),
    "sono_ruim": ("sono ruim",),
    "calor": ("calor", "quente", "quentes", "abafado", "abafada"),  # "quente" é o mesmo fato que "calor": só com o atalho marcado
    "trabalho_estresse": ("trabalho ou estresse", "estresse"),
}
# --- Concordância (checagens_feedback@5, #403): FC, VFC e PSE são femininas ("a FC média", "sua VFC"), nunca "seu FC médio" ---------------
_SIGLAS_FEMININAS = r"(?:fc|vfc|pse)"
_ARTIGO_MASCULINO = re.compile(rf"(?<!\w)(?:o|um|seu|meu|nosso|esse|este|aquele|do|no|ao|pelo|dele) {_SIGLAS_FEMININAS}(?!\w)")
_ADJETIVO_MASCULINO = re.compile(rf"(?<!\w){_SIGLAS_FEMININAS}(?: de repouso)? (?:medio|minimo|maximo|alto|baixo|elevado)(?!\w)")
# --- Clima (checagens_feedback@6, #405) -----------------------------------------------------------------------------------------------
# Palavras de estado, comparadas na FRASE que fala do clima. `indoor` só conta preso a "clima" ("o clima foi indoor"): "o treino foi indoor,
# sem dados de clima" descreve o treino, não o clima, e é o certo. Estados do pacote: ok | indoor | sem_posicao | pendente | falha.
_ESTADO_DO_CLIMA = {
    "pendente": re.compile(r"(?<!\w)(pendente|pendentes|aguardando)(?!\w)"),
    "indoor": re.compile(r"(?<!\w)clima (?:(?!treino)\w+ ){0,2}indoor(?!\w)"),
    "sem_posicao": re.compile(r"(?<!\w)(sem (?:a )?(?:posicao|localizacao)|sem gps|sem coordenada)"),
    "falha": re.compile(r"(?<!\w)(falha|falhou|indisponivel|nao foi possivel)(?!\w)"),
}
_NUMERO_DE_CLIMA = re.compile(r"\d\s?°\s?c|(?<!\w)(umidade|vento|sensacao termica)(?!\w)")
# --- Forma da frase (checagens_feedback@2, #355) --------------------------------------------------------------------------------
# Verbos aceitos, minúsculos e COM acento ("é" não é a conjunção "e"). Heurística: uma lista fechada mais a terminação do pretérito.
VERBOS = frozenset({
    "é", "são", "era", "eram", "foi", "foram", "está", "estão", "esteve", "estiveram", "tem", "têm", "teve", "tiveram", "houve",
    "fica", "ficam", "ficou", "ficaram", "marcou", "marcaram", "registrou", "registraram", "aparece", "aparecem", "apareceu", "apareceram",
    "soma", "somam", "somou", "somaram", "vale", "valem", "durou", "duraram", "fez", "fizeram", "corresponde", "equivale", "representa",
    "manteve", "mantiveram", "ocorreu", "ocorreram", "aconteceu", "ficando",
})
_PRETERITO = re.compile(r"^[a-zà-ÿ]{3,}(ou|eu|iu|aram|eram|iram)$")  # "percorreu", "nadou", "pedalaram"; "seu" e "meu" não entram (3 letras)
# Frases curtas sem verbo que os exemplos aprovados usam: "Sem comparação ...", o gerúndio de "Ainda aprendendo o seu normal..." e a
# abertura descritiva do exemplo 6 ("Natação de 1.600 m em 40 min, com FC média de 128 bpm."). Uma lista de valores sem isso reprova.
_ABERTURA_DESCRITIVA = re.compile(r"^(natacao|ciclismo|corrida|treino\b[^,]*)\b.* com fc media de \d+ bpm\.?$")
# Expressões de conclusão: a mesma em duas linhas é repetição ("dentro do seu normal" abrindo e fechando o texto).
CONCLUSOES = ("dentro do seu normal", "fora do seu normal", "dentro do normal", "perto da mediana", "sem comparacao com o seu historico")
_DENTRO_DA_MEDIANA = re.compile(r"dentro d[aeo]s? (sua |a )?mediana")  # o certo é "perto da mediana" ou "dentro do seu normal"

# Clima descrito em palavras que o pacote não traz (o pacote traz °C, não "frio"): sem o fato no pacote, reprova como "fora do pacote".
CLIMA_FORA_DO_PACOTE = ("frio", "fria", "frios", "frias", "gelado", "gelada", "friozinho")
EXTENSO = (
    "dois", "duas", "tres", "quatro", "cinco", "seis", "sete", "oito", "nove", "dez", "onze", "doze", "treze", "quatorze", "quinze",
    "dezesseis", "dezessete", "dezoito", "dezenove", "vinte", "trinta", "quarenta", "cinquenta", "sessenta", "setenta", "oitenta",
    "noventa", "cem", "cento", "mil", "metade", "dobro", "triplo", "dezena", "duzia",
)  # "um" e "uma" ficam de fora: como artigo passam
SIGLAS_PERMITIDAS = frozenset({"FC", "PSE", "UA", "C", "VFC"})  # o "C" de "°C"

# unidade de cada campo numérico do pacote (o que o texto pode escrever depois do número)
_UNIDADE_DO_CAMPO = {"temperatura_c": "°c", "sensacao_termica_c": "°c", "umidade_pct": "%", "vento_kmh": "km/h", "fc_media_bpm": "bpm",
                     "duracao_s": "s", "distancia_m": "m"}

_UNIDADES = r"pontos/h|pontos|s/km|km/h|km|bpm|min|ms|ua|°\s?c|%|/km|m|s|h"
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


_COMPOSTA = re.compile(r"(?<![\w:,.])(\d+) h (\d+) min(?!\w)")  # "5 h 40 min": UM número (ADR 0014, item 6.B3)


def _compostas_do_pacote(pacote: Any) -> set[str]:
    achadas: set[str] = set()
    if isinstance(pacote, Mapping):
        for v in pacote.values():
            achadas |= _compostas_do_pacote(v)
    elif isinstance(pacote, (list, tuple)):
        for v in pacote:
            achadas |= _compostas_do_pacote(v)
    elif isinstance(pacote, str):
        achadas |= {m.group(0) for m in _COMPOSTA.finditer(pacote)}
    return achadas


def _numeros(pacote: Mapping[str, Any], texto: str, plano: str) -> set[str]:
    pares: set[tuple[str, str]] = set()
    soltos: set[str] = set()
    _coletar(pacote, pares, soltos)
    motivos: set[str] = set()
    compostas = _compostas_do_pacote(pacote)
    for m in _COMPOSTA.finditer(texto):  # "1 h 30 min" só passa se é um texto composto do pacote
        if m.group(0) not in compostas:
            motivos.add("numero_fora_do_pacote")
    texto = _COMPOSTA.sub(" ", texto)
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
    """Tira do texto o que o app escreve de propósito e as listas pegariam: o rótulo da sensação **do pacote**, com ou sem parênteses
    ("muito bem", "mal"), o da PSE entre parênteses ("(repouso)") e a frase exata "sono ruim" (o rótulo do atalho; ADR 0013, item 4.2).
    O rótulo só passa se é o da sensação que o pacote traz: "muito bem" num treino de sensação "mal" continua elogio, e "mal" num treino
    de sensação "bem" continua juízo."""
    ck = pacote.get("checkin") or {}
    sens, pse = ck.get("sensacao_texto"), ck.get("pse_texto")
    if pse:
        plano = plano.replace(f"({_plano(str(pse))})", " ")
    if sens:
        rotulo = re.escape(_plano(str(sens)))
        antes = "" if _plano(str(sens)).startswith("muito") else r"(?<!muito )"  # "bem" não pode mascarar o "bem" de "muito bem"
        plano = re.sub(rf"(?<!\w){antes}{rotulo}(?!\w)", " ", plano)
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

# checagens_feedback@3 (#367): o mesmo numero repetido entre parenteses ("esforco 6 (6)"). A PSE 6, 8 e 9 nao tem ancora (ADR 0012, item 2).
_NUMERO_REPETIDO = re.compile(r"(?<![\d,.:])(\d+(?:[.,]\d+)?)\s*\(\s*\1\s*\)(?![\d])")


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


def _concordancia(plano: str) -> set[str]:
    if _ARTIGO_MASCULINO.search(plano) or _ADJETIVO_MASCULINO.search(plano):
        return {"concordancia_sigla"}
    return set()


def _clima_estado(plano: str, pacote: Mapping[str, Any]) -> set[str]:
    """A palavra de estado do clima no texto bate com `clima.estado`; temperatura, umidade ou vento só com `ok` (#405)."""
    estado = (pacote.get("clima") or {}).get("estado")  # None: natação, sem bloco de clima
    if estado != "ok" and _NUMERO_DE_CLIMA.search(plano):
        return {"clima_estado"}
    for frase in re.split(r"[.;:](?:\s|$)|\n", plano):
        if not re.search(r"(?<!\w)clima(?!\w)", frase):
            continue
        for nome, padrao in _ESTADO_DO_CLIMA.items():
            if nome == estado or not padrao.search(frase):
                continue
            if estado == "ok" and "carga" in frase and nome in ("pendente", "falha"):  # "clima ... 19 °C e a carga pendente"
                continue
            return {"clima_estado"}
    return set()


def _tem_verbo(linha: str) -> bool:
    plano = _plano(linha)
    if plano.startswith("sem ") or "aprendendo" in plano or _ABERTURA_DESCRITIVA.match(plano):
        return True
    return any(t in VERBOS or _PRETERITO.match(t) for t in re.findall(r"[\wà-ÿ]+", linha.casefold()))


_REC_TERMO = r"(?<!\w)(sono|vfc|fc de repouso|noite anterior|noite|dormiu|dormiram)(?!\w)"
_MEDIDA_NA_FRASE = re.compile(r"(?<!\w)(fc de repouso|vfc|sono|dormiu|dormiram)(?!\w)")
_CHAVE_DA_PALAVRA = {"fc de repouso": "fc_repouso", "vfc": "vfc"}
_COMPARACAO = re.compile(r"(?<!\w)(abaixo|acima|dentro)(?!\w)")
_COMPARACAO_PERMITIDA = re.compile(r"(?<!\w)(abaixo|acima|dentro) d[oa] seu normal(?!\w)")


def _e_linha_rec(linha: str, pacote: Mapping[str, Any]) -> bool:
    """A linha fala de sono, VFC ou FC de repouso (o rótulo "sono ruim" do atalho marcado não conta)."""
    return re.search(_REC_TERMO, _mascarar_rotulos(_plano(linha), pacote)) is not None


def _recuperacao(linhas: list[str], pacote: Mapping[str, Any]) -> set[str]:
    """Regras da recuperação da noite (ADR 0014, item 6; `checagens_feedback@4`). Linhas que não falam de sono, VFC ou FC de repouso
    não são tocadas por nenhuma delas."""
    bloco = pacote.get("recuperacao") or {}
    sem_dado_ok = bloco.get("estado") == "sem_dado" and bloco.get("motivo") == "sem_noite"
    frase = _plano(FRASE_SEM_DADO).rstrip(".")
    motivos: set[str] = set()
    rec = []
    for linha in linhas:
        if not _e_linha_rec(linha, pacote):
            continue
        plano = _plano(linha).strip().rstrip(".")
        if plano == frase:
            if not sem_dado_ok:
                motivos.add("recuperacao_sem_pacote")  # a frase pronta só vale em sem_dado/sem_noite
            continue
        rec.append(linha)
    if not rec:
        return motivos
    if bloco.get("estado") != "ok":  # regra 5: sem recuperação no pacote, sem recuperação no texto
        return motivos | {"recuperacao_sem_pacote"}
    planas = [_plano(x) for x in rec]
    sem_rotulo = [re.sub(r"\s+", " ", x) for x in planas]
    juntas = " | ".join(sem_rotulo)
    if _tem_termo(juntas, REC_CAUSA):
        motivos.add("linguagem_causa")
    if _tem_termo(juntas, REC_JULGAMENTO):
        motivos.add("linguagem_julgamento")
    if _tem_termo(juntas, REC_OUTRO_DIA) or re.search(r"\d{1,2}/\d{1,2}", juntas):
        motivos.add("recuperacao_outro_dia")
    for x in sem_rotulo:  # regra 1: nenhuma outra medida na linha ("fc de repouso" é da recuperação)
        sobra = x.replace("fc de repouso", " ")
        if _tem_termo(sobra, REC_MISTURA) or re.search(r"\d\s?°\s?c|/km", sobra):
            motivos.add("recuperacao_mistura")
    # regra 2: "noite anterior" aparece, e a comparação só tem a forma "abaixo/acima/dentro do seu normal", coerente com o estado
    if "noite anterior" not in juntas:
        motivos.add("recuperacao_forma")
    estados = {m.get("chave"): m.get("estado") for m in bloco.get("medidas") or []}
    citou_aprendendo = False
    for x in sem_rotulo:
        if len(_COMPARACAO.findall(x)) != len(_COMPARACAO_PERMITIDA.findall(x)):
            motivos.add("recuperacao_forma")
        for frase_ in re.split(r"(?<=[.!?])\s+", x):
            marcas = list(_MEDIDA_NA_FRASE.finditer(frase_))
            for i, mt in enumerate(marcas):
                fim = marcas[i + 1].start() if i + 1 < len(marcas) else len(frase_)
                trecho = frase_[mt.start():fim]
                chave = _CHAVE_DA_PALAVRA.get(mt.group(1), "sono")
                estado = estados.get(chave)
                achadas = set(_COMPARACAO.findall(trecho))
                if estado in ("abaixo", "acima", "dentro"):
                    if achadas - {estado}:
                        motivos.add("recuperacao_forma")
                elif achadas or estado in (None, "sem_dado"):  # aprendendo: sem comparação; sem_dado: nem se cita
                    motivos.add("recuperacao_forma")
                if estado == "aprendendo":
                    citou_aprendendo = True
    if citou_aprendendo and "aprendendo" not in juntas:  # @5: citou medida aprendendo, tem de dizer por que não compara
        motivos.add("recuperacao_sem_aprendendo")
    return motivos


def _forma(texto: str, linhas: list[str], pacote: Mapping[str, Any] | None = None) -> set[str]:
    motivos: set[str] = set()
    if not LINHAS_MIN <= len(linhas) <= LINHAS_MAX:
        motivos.add("forma_linhas")
    if len(texto) > TEXTO_MAX_CARACTERES or any(len(x) > LINHA_MAX_CARACTERES for x in linhas):
        motivos.add("forma_tamanho_linha")
    if re.search(r"[*`]|__", texto) or any(re.match(r"\s*(#|>|[-•]\s|\d+[.)]\s)", x) for x in linhas):
        motivos.add("forma_markdown")
    if any(not _tem_verbo(x) for x in linhas):
        motivos.add("forma_sem_verbo")
    # A linha da recuperação tem a sua própria conclusão ("dentro do seu normal" da VFC): conta à parte da do resultado (@4).
    rec = [_e_linha_rec(x, pacote or {}) for x in linhas]
    for grupo in ([_plano(x) for x, r in zip(linhas, rec) if not r], [_plano(x) for x, r in zip(linhas, rec) if r]):
        if any(sum(c in x for x in grupo) >= 2 for c in CONCLUSOES):
            motivos.add("conclusao_repetida")
    if _DENTRO_DA_MEDIANA.search(_plano(texto)):
        motivos.add("comparacao_mediana")
    if _NUMERO_REPETIDO.search(texto):
        motivos.add("numero_repetido")
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
    if _tem_termo(plano, CLIMA_FORA_DO_PACOTE):
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
    achados = _forma(texto, linhas, pacote) | _recuperacao(linhas, pacote) | _concordancia(plano) | _clima_estado(_mascarar_rotulos(plano, pacote), pacote) | _numeros(pacote, texto, plano) | _linguagem(texto, plano, pacote) | _dor_e_atalhos(plano, pacote)
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
