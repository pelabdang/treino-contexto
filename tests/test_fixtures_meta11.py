"""Confere as fixtures sintéticas da Meta 11 e o oráculo à mão de `atencao@2` (issue #421, ADR 0015).

NÃO roda código de produção (a `atencao@2` é a #422 e a #454): confere a forma das fixtures, que cobrem os casos da ADR e que o oráculo
escrito à mão é coerente com uma referência curta e independente das regras (`_referencia`), escrita só para este teste.
Tabela legível em `docs/metricas/atencao-oraculo.md`. Tudo sintético, atletas fictícios.
"""

import json
from datetime import date, datetime
from pathlib import Path

PASTA = Path(__file__).parent / "fixtures" / "meta11"
HOJE = date(2026, 11, 18)  # quarta
JANELA_DIAS, AVISO_CHECKIN_DIAS, PRAZO_DIAS, JANELA_NOVOS_DIAS = 7, 5, 7, 14  # ADR 0015, item 4
DIAS = ["segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo"]
PRIORIDADE = ["dor", "fora_do_normal", "divergencia", "checkin_vencendo"]
# ADR 0015, item 4: ordem das medidas e vocabulário por sinal do z (z > 0 primeiro)
MEDIDAS = [
    ("fc_media", "FC média acima do habitual", "FC média abaixo do habitual"),
    ("fc_melhor_tiro", "FC do melhor tiro acima do habitual", "FC do melhor tiro abaixo do habitual"),
    ("pace_medio", "pace médio mais lento", "pace médio mais rápido"),
    ("melhor_pace", "melhor pace mais lento", "melhor pace mais rápido"),
    ("carga_hora", "carga por hora acima do habitual", "carga por hora abaixo do habitual"),
]
NAO_ELEGIVEIS = {"multiesporte_pai", "troca"}
CHAVES_TREINO = {"id", "atleta", "dia", "modalidade", "subtipo", "tipo_treino", "tipo_origem", "tipo_confirmado",
                 "tipo_divergencia", "metricas_fora", "checkin"}


def _ler(nome):
    return json.loads((PASTA / nome).read_text(encoding="utf-8"))


def _consentidos(ident, agora=datetime.fromisoformat("2026-11-18T12:00:00+00:00")):
    prof = ident["professor_do_piloto"]
    return {a["nome"] for a in ident["atletas"] for v in a["vinculos"]
            if v["professor"] == prof and v["consentimento_em"] is not None
            and datetime.fromisoformat(v["consentimento_em"]) <= agora}


def _motivos(t):
    dia = date.fromisoformat(t["dia"])
    dias = (HOJE - dia).days
    if not (0 <= dias <= JANELA_DIAS):
        return []
    nome = DIAS[dia.weekday()]
    out = []
    if t["checkin"] and t["checkin"]["dor"]:
        out.append(("dor", f"Treino de {nome} com dor marcada no check-in."))
    fora = {m["chave"]: m["z"] for m in t["metricas_fora"] if abs(m["z"]) >= 2.5}
    if fora:
        partes = [(a if fora[c] > 0 else b) for c, a, b in MEDIDAS if c in fora]
        junto = partes[0] if len(partes) == 1 else ", ".join(partes[:-1]) + " e " + partes[-1]
        out.append(("fora_do_normal", f"Treino de {nome} fora do normal: {junto}."))
    if t["tipo_origem"] == "semana_padrao" and t["tipo_divergencia"] and not t["tipo_confirmado"]:
        det = "sem esforço detectado" if t["tipo_divergencia"] == "sem_esforco" else "com tiros detectados"
        out.append(("divergencia", f"Treino de {nome} diferente da semana-padrão: previsto {t['tipo_treino']}, {det}."))
    return out


def _aviso_checkin(treinos):
    """`checkin_vencendo` (atencao@2): uma linha por aluno, no treino mais antigo sem check-in; `outra` não conta."""
    pend = sorted((t for t in treinos if t["checkin"] is None and t["subtipo"] not in NAO_ELEGIVEIS and t["modalidade"] != "outra"
                   and AVISO_CHECKIN_DIAS <= (HOJE - date.fromisoformat(t["dia"])).days <= PRAZO_DIAS), key=lambda t: (t["dia"], t["id"]))
    if not pend:
        return None
    resta = PRAZO_DIAS - (HOJE - date.fromisoformat(pend[0]["dia"])).days
    quando = "hoje" if resta == 0 else f"em {resta} dia" + ("s" if resta > 1 else "")
    if len(pend) == 1:
        return pend[0]["id"], f"Treino de {DIAS[date.fromisoformat(pend[0]['dia']).weekday()]} sem check-in; o prazo termina {quando}."
    return pend[0]["id"], f"{len(pend)} treinos sem check-in; o prazo do mais antigo termina {quando}."


def _referencia(ident, treinos):
    ok = _consentidos(ident)
    por_atleta = {}
    for t in treinos:
        if t["atleta"] in ok:
            por_atleta.setdefault(t["atleta"], []).append(t)
    com, sem = [], []
    for atleta in sorted(ok):
        itens = []
        aviso = _aviso_checkin(por_atleta.get(atleta, []))
        for t in sorted(por_atleta.get(atleta, []), key=lambda x: x["dia"], reverse=True):
            mot = _motivos(t)
            if aviso and aviso[0] == t["id"]:
                mot.append(("checkin_vencendo", aviso[1]))
            if mot:
                itens.append((t, mot))
        if itens:
            topo = min(PRIORIDADE.index(c) for _, ms in itens for c, _ in ms)
            recente = max(t["dia"] for t, _ in itens)
            com.append((topo, [-int(recente.replace("-", "")), ], atleta, itens))
        else:
            sem.append(atleta)
    com.sort(key=lambda x: (x[0], x[1], x[2]))
    lista = [{"atleta": a, "treinos": [{"id": t["id"], "motivos": [{"codigo": c, "texto": x} for c, x in ms]} for t, ms in it]}
             for _, _, a, it in com]
    novos = [t["id"] for t in treinos if t["atleta"] in ok and t["tipo_treino"] and t["tipo_origem"] in ("sugestao", "semana_padrao")
             and not t["tipo_confirmado"] and t["subtipo"] not in NAO_ELEGIVEIS
             and 0 <= (HOJE - date.fromisoformat(t["dia"])).days <= JANELA_NOVOS_DIAS]
    return lista, sorted(sem), novos


def test_forma_das_fixtures():
    ident, trein, orac = _ler("identidade.json"), _ler("treinos.json"), _ler("oraculo.json")
    nomes_prof = [p["nome"] for p in ident["professores"]]
    assert ident["professor_do_piloto"] in nomes_prof and len(nomes_prof) == 2
    atletas = [a["nome"] for a in ident["atletas"]]
    assert len(set(atletas)) == len(atletas) == 8 and all(n.startswith("Atleta Fixture ") for n in atletas)
    for a in ident["atletas"]:  # mesmo formato do carregador `worker.carregar_professor`
        for v in a["vinculos"]:
            assert v["professor"] in nomes_prof
            assert v["consentimento_em"] is None or datetime.fromisoformat(v["consentimento_em"]).tzinfo is not None
    assert trein["hoje"] == orac["hoje"] == HOJE.isoformat()
    ids = [t["id"] for t in trein["treinos"]]
    assert len(set(ids)) == len(ids)
    for t in trein["treinos"]:
        assert set(t) == CHAVES_TREINO  # sem texto livre nem observação: a atencao@1 não os recebe (ADR 0015, item 7)
        assert t["atleta"] in atletas
        date.fromisoformat(t["dia"])
        assert t["checkin"] is None or set(t["checkin"]) == {"dor"}
        for m in t["metricas_fora"]:
            assert m["chave"] in {c for c, _, _ in MEDIDAS} and abs(m["z"]) >= 2.5
        assert t["tipo_divergencia"] is None or t["tipo_origem"] == "semana_padrao"  # CHECK tipo_divergencia_origem


def test_cobre_os_casos_da_adr():
    ident, trein, orac = _ler("identidade.json"), _ler("treinos.json"), _ler("oraculo.json")
    codigos = {m["codigo"] for it in orac["lista"] for t in it["treinos"] for m in t["motivos"]}
    assert codigos == set(PRIORIDADE)
    assert any(len(t["motivos"]) == 2 for it in orac["lista"] for t in it["treinos"])  # um treino com dois motivos
    assert "car-2" in orac["sem_motivo_e_por_que"]  # treino de ontem sem check-in, longe do prazo
    assert {"car-1", "car-6"} <= set(orac["sem_motivo_e_por_que"])  # uma linha por aluno; modalidade outra não conta
    assert set(orac["nao_aparecem"]) == {"Atleta Fixture Eva Sem Consentimento", "Atleta Fixture Fabio De Outro Professor"}
    assert not set(orac["nao_aparecem"]) & _consentidos(ident)
    assert orac["sem_atencao"]["atletas"] == ["Atleta Fixture Davi"]
    com_motivo = {t["id"] for it in orac["lista"] for t in it["treinos"]}
    assert not com_motivo & set(orac["sem_motivo_e_por_que"])
    assert {t["id"] for t in trein["treinos"]} == com_motivo | set(orac["sem_motivo_e_por_que"]) | {"eva-1", "fab-1"}


def test_oraculo_igual_a_referencia_independente():
    ident, trein, orac = _ler("identidade.json"), _ler("treinos.json"), _ler("oraculo.json")
    lista, sem, novos = _referencia(ident, trein["treinos"])
    assert lista == orac["lista"]
    assert sem == orac["sem_atencao"]["atletas"]
    assert sorted(novos) == sorted(orac["novos"])
