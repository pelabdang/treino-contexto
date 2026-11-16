"""`atencao@1` (issue #422, ADR 0015): os quatro motivos, contra o oráculo à mão de `tests/fixtures/meta11/` e casos de borda.

Valores esperados escritos à mão em `oraculo.json` (nota `docs/metricas/atencao-oraculo.md`); aqui só se lê. Tudo sintético.
"""

import json
from datetime import date
from pathlib import Path

import pytest
from app.metricas import atencao as at

RAIZ = Path(__file__).resolve().parents[4]
PASTA = RAIZ / "tests" / "fixtures" / "meta11"
HOJE = date(2026, 11, 18)  # quarta


def _json(nome):
    return json.loads((PASTA / nome).read_text(encoding="utf-8"))


def _treino(d):
    return at.TreinoAtencao(
        id=d["id"], dia=date.fromisoformat(d["dia"]), modalidade=d["modalidade"], subtipo=d["subtipo"],
        tipo_treino=d["tipo_treino"], tipo_origem=d["tipo_origem"], tipo_confirmado=d["tipo_confirmado"],
        tipo_divergencia=d["tipo_divergencia"], metricas_fora=tuple((m["chave"], m["z"]) for m in d["metricas_fora"]),
        dor=None if d["checkin"] is None else d["checkin"]["dor"],
    )


def _consentidos(ident):
    prof = ident["professor_do_piloto"]
    return {a["nome"] for a in ident["atletas"] for v in a["vinculos"]
            if v["professor"] == prof and v["consentimento_em"] is not None and v["consentimento_em"] < "2026-11-18T12:00:00+00:00"}


def _por_atleta():
    ok = _consentidos(_json("identidade.json"))
    por = {n: [] for n in ok}
    for d in _json("treinos.json")["treinos"]:
        if d["atleta"] in ok:
            por[d["atleta"]].append(_treino(d))
    return por


def test_oraculo_da_lista():
    orac = _json("oraculo.json")
    r = at.atencao(_por_atleta(), HOJE)
    assert r.versao == "atencao@1" == orac["versao"]
    obtido = [{"atleta": a.atleta, "treinos": [{"id": t.id, "motivos": [{"codigo": m.codigo, "texto": m.texto} for m in t.motivos]}
                                               for t in a.treinos]} for a in r.com_atencao]
    assert obtido == orac["lista"]
    assert list(r.sem_atencao) == orac["sem_atencao"]["atletas"]
    assert r.sem_atencao_texto == orac["sem_atencao"]["texto"]


def test_oraculo_dos_treinos_novos():
    todos = [t for ts in _por_atleta().values() for t in ts]
    assert sorted(at.treinos_novos(todos, HOJE)) == sorted(_json("oraculo.json")["novos"])


def test_atleta_fora_do_filtro_nao_entra_pois_quem_chama_nao_o_passa():
    r = at.atencao(_por_atleta(), HOJE)
    nomes = {a.atleta for a in r.com_atencao} | set(r.sem_atencao)
    assert "Atleta Fixture Eva Sem Consentimento" not in nomes and "Atleta Fixture Fabio De Outro Professor" not in nomes


def _t(**k):
    base = dict(id="x", dia=HOJE, modalidade="corrida", subtipo=None, tipo_treino="leve", tipo_origem="sugestao",
                tipo_confirmado=False, tipo_divergencia=None, metricas_fora=(), dor=False)
    base.update(k)
    return at.TreinoAtencao(**base)


@pytest.mark.parametrize("dias,esperado", [(4, None), (5, "em 2 dias"), (6, "em 1 dia"), (7, "hoje"), (8, None)])
def test_checkin_vencendo_bordas(dias, esperado):
    from datetime import timedelta
    m = at.motivos_do_treino(_t(dia=HOJE - timedelta(days=dias), dor=None), HOJE)
    if esperado is None:
        assert m == ()
    else:
        assert [x.codigo for x in m] == ["checkin_vencendo"] and m[0].texto.endswith(f"termina {esperado}.")


def test_limite_de_fora_e_o_da_linha_de_base():
    assert at.motivos_do_treino(_t(metricas_fora=(("fc_media", 2.49),)), HOJE) == ()
    m = at.motivos_do_treino(_t(metricas_fora=(("fc_media", -2.5),)), HOJE)
    assert m[0].texto == "Treino de quarta fora do normal: FC média abaixo do habitual."


def test_tres_medidas_fora_na_ordem_da_tabela():
    m = at.motivos_do_treino(_t(metricas_fora=(("carga_hora", 3.0), ("pace_medio", -3.0), ("fc_media", 3.0))), HOJE)
    assert m[0].texto == ("Treino de quarta fora do normal: FC média acima do habitual, pace médio mais rápido e "
                          "carga por hora acima do habitual.")


def test_janela_de_atencao_vai_de_hoje_menos_7_a_hoje():
    from datetime import timedelta
    assert at.motivos_do_treino(_t(dia=HOJE - timedelta(days=7), dor=True), HOJE)
    assert at.motivos_do_treino(_t(dia=HOJE - timedelta(days=8), dor=True), HOJE) == ()
    assert at.motivos_do_treino(_t(dia=HOJE + timedelta(days=1), dor=True), HOJE) == ()


def test_divergencia_some_com_tipo_confirmado_e_texto_por_tipo():
    d = _t(tipo_origem="semana_padrao", tipo_divergencia="sem_esforco", tipo_treino="intervalado")
    assert at.motivos_do_treino(d, HOJE)[0].texto == "Treino de quarta diferente da semana-padrão: previsto intervalado, sem esforço detectado."
    assert at.motivos_do_treino(_t(tipo_origem="semana_padrao", tipo_divergencia="sem_esforco", tipo_confirmado=True), HOJE) == ()


def test_multiesporte_nao_pede_checkin_e_treino_sem_checkin_dentro_do_prazo_curto_nao_avisa():
    from datetime import timedelta
    assert at.motivos_do_treino(_t(dia=HOJE - timedelta(days=6), dor=None, subtipo="multiesporte_pai"), HOJE) == ()
    assert at.motivos_do_treino(_t(dia=HOJE - timedelta(days=1), dor=None), HOJE) == ()


def test_sem_nenhum_treino_o_atleta_fica_sem_atencao_e_a_funcao_e_idempotente():
    r = at.atencao({"b": [], "a": [_t(dor=False)]}, HOJE)
    assert r.com_atencao == () and r.sem_atencao == ("a", "b")
    assert at.atencao({"b": [], "a": [_t(dor=False)]}, HOJE) == r


def test_entrada_nao_tem_campo_de_texto_livre():
    campos = set(at.TreinoAtencao.__dataclass_fields__)
    assert not campos & {"texto", "observacao", "nota", "comentario"}
