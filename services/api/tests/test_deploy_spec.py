"""O app spec do App Platform e a imagem (issue #504, ADR 0016, itens 9 e 10): sem segredo, sem LLM, nada fora da lista. Nada aqui fala com o provedor."""

import re

import pytest
import yaml
from app.config import RAIZ_REPOSITORIO, Settings
from app.llm import criar_redator

SPEC = RAIZ_REPOSITORIO / ".do" / "app.yaml"
DOCKERFILE = RAIZ_REPOSITORIO / "services" / "api" / "Dockerfile"
# as unicas variaveis que o spec pode definir, por componente
PERMITIDAS = {
    "api": {"DATABASE_URL", "AMBIENTE", "CORS_ORIGENS", "FIT_DIR"},
    "migrar": {"DATABASE_URL"},
    "web": {"EXPO_PUBLIC_API_URL"},
}
SENSIVEL = re.compile(r"KEY|SECRET|PASSWORD|SENHA|TOKEN|DATABASE_URL", re.I)
BINDING = re.compile(r"^\$\{[A-Za-z0-9_.]+\}$")


@pytest.fixture(scope="module")
def spec():
    return yaml.safe_load(SPEC.read_text(encoding="utf-8"))


def _componentes(spec):
    for tipo in ("services", "jobs", "workers", "static_sites"):
        for c in spec.get(tipo, []):
            yield tipo, c


def test_os_componentes_sao_os_esperados(spec):
    assert {c["name"] for _, c in _componentes(spec)} == {"api", "migrar", "web"}
    assert [d["engine"] for d in spec["databases"]] == ["PG"] and spec["databases"][0]["production"] is True
    migrar = next(c for _, c in _componentes(spec) if c["name"] == "migrar")
    assert migrar["kind"] == "PRE_DEPLOY" and "alembic upgrade head" in migrar["run_command"]


def test_so_as_variaveis_da_lista_e_nenhuma_com_valor_secreto_escrito(spec):
    for _, c in _componentes(spec):
        nomes = {e["key"] for e in c.get("envs", [])}
        assert nomes <= PERMITIDAS[c["name"]], (c["name"], nomes - PERMITIDAS[c["name"]])
        for e in c.get("envs", []):
            if SENSIVEL.search(e["key"]):
                assert e.get("type") == "SECRET" and BINDING.match(str(e.get("value", ""))), e["key"]  # so binding do provedor


def test_nenhuma_chave_de_llm_nem_variavel_do_piloto_local_no_spec():
    texto = SPEC.read_text(encoding="utf-8")
    for proibido in ("LLM_", "GROQ", "OPENAI", "ANTHROPIC", "GARMIN", "PROFESSOR_ID", "ATLETA_ID"):
        linhas = [l for l in texto.splitlines() if proibido in l and not l.lstrip().startswith("#")]
        assert linhas == [], proibido


def test_a_api_sobe_em_producao_com_health_e_sem_deploy_automatico(spec):
    api = next(c for _, c in _componentes(spec) if c["name"] == "api")
    env = {e["key"]: e["value"] for e in api["envs"]}
    assert env["AMBIENTE"] == "producao" and api["health_check"]["http_path"] == "/health"
    assert api["github"]["deploy_on_push"] is False and (RAIZ_REPOSITORIO / api["dockerfile_path"]).is_file()
    assert api["routes"] == [{"path": "/api"}]


def test_o_app_web_recebe_a_url_da_api_em_tempo_de_build_na_mesma_origem(spec):
    web = next(c for _, c in _componentes(spec) if c["name"] == "web")
    (e,) = web["envs"]
    assert e["key"] == "EXPO_PUBLIC_API_URL" and e["scope"] == "BUILD_TIME" and e["value"] == "${APP_URL}/api"
    assert web["routes"] == [{"path": "/"}] and "expo export" in web["build_command"]


def test_o_spec_nao_traz_url_de_banco_nem_token_com_credencial():
    texto = SPEC.read_text(encoding="utf-8")
    assert not re.search(r"postgres(ql)?(\+\w+)?://\S*:\S*@", texto)  # usuario:senha@host
    assert "dop_v1_" not in texto  # token de API da DigitalOcean


def test_a_imagem_roda_sem_root_sem_segredo_e_sem_chave_de_llm():
    txt = DOCKERFILE.read_text(encoding="utf-8")
    assert re.search(r"^USER app$", txt, flags=re.M) and "AMBIENTE=producao" in txt
    assert "--no-access-log" in txt  # o log de acesso do uvicorn grava a query string
    envs = " ".join(l for l in txt.splitlines() if l.startswith(("ENV", "ARG")))
    assert not re.search(r"KEY|SECRET|PASSWORD|TOKEN|LLM_|DATABASE_URL", envs)


@pytest.mark.parametrize("de,para", [
    ("postgresql://u@h/d?sslmode=require", "postgresql+psycopg://u@h/d?sslmode=require"),
    ("postgres://u@h/d", "postgresql+psycopg://u@h/d"),
    ("postgresql+psycopg://u@h/d", "postgresql+psycopg://u@h/d"),
])
def test_a_url_do_banco_gerenciado_vale_com_o_driver_psycopg(de, para):
    assert Settings(_env_file=None, database_url=de).database_url == para


def test_sem_modelo_nem_chave_o_feedback_fica_desligado_no_servidor():
    s = Settings(_env_file=None)  # como no servidor: nenhuma variavel de LLM
    assert s.llm_model == "" and criar_redator(s).configurado is False
