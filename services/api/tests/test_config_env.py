"""O `.env` lido e o da raiz do repositorio, de qualquer pasta de execucao (#354). So valores sinteticos."""

from pathlib import Path

from app.config import RAIZ_REPOSITORIO, Settings


def test_env_file_e_absoluto_e_fica_na_raiz():
    caminho = Path(Settings.model_config["env_file"])
    assert caminho.is_absolute() and caminho == RAIZ_REPOSITORIO / ".env"
    assert (RAIZ_REPOSITORIO / "AGENTS.md").exists()  # a raiz e mesmo a do repositorio


def test_mesmos_valores_de_qualquer_pasta(tmp_path, monkeypatch):
    env = tmp_path / ".env"
    env.write_text("LLM_MODEL=modelo-sintetico\n", encoding="utf-8")

    class S(Settings):
        model_config = {**Settings.model_config, "env_file": env}

    for var in ("LLM_MODEL", "LLM_INTERVALO_S"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.chdir(RAIZ_REPOSITORIO)
    da_raiz = S().llm_model
    monkeypatch.chdir(tmp_path)  # outra pasta, sem `.env` proprio
    assert da_raiz == S().llm_model == "modelo-sintetico"


def test_variavel_de_ambiente_vale_mais_que_o_arquivo(tmp_path, monkeypatch):
    env = tmp_path / ".env"
    env.write_text("LLM_MODEL=do-arquivo\n", encoding="utf-8")

    class S(Settings):
        model_config = {**Settings.model_config, "env_file": env}

    monkeypatch.setenv("LLM_MODEL", "do-ambiente")
    assert S().llm_model == "do-ambiente"


def test_um_env_na_pasta_de_execucao_nao_e_lido(tmp_path, monkeypatch):
    (tmp_path / ".env").write_text("LLM_MODEL=da-pasta-errada\n", encoding="utf-8")
    monkeypatch.delenv("LLM_MODEL", raising=False)
    monkeypatch.chdir(tmp_path)
    assert Settings(_env_file=None).llm_model == ""  # sem arquivo: o padrao
    assert Path(Settings.model_config["env_file"]) != tmp_path / ".env"
