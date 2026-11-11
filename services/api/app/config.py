from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


RAIZ_REPOSITORIO = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    # O `.env` e sempre o da raiz do repositorio, de qualquer pasta de execucao (#354): rodando um worker de
    # `services/worker`, um `.env` relativo nao era lido e o provedor de LLM aparecia como nao configurado, sem erro.
    # Variavel de ambiente continua valendo mais que o arquivo.
    model_config = SettingsConfigDict(env_file=RAIZ_REPOSITORIO / ".env", extra="ignore")

    database_url: str = "postgresql+psycopg://treino:treino@localhost:5433/treino"
    # Origens do app web liberadas no CORS, separadas por vírgula (ADR 0004, item 7). Vazio libera nenhuma.
    cors_origens: str = "http://localhost:8081"
    # Pasta dos FIT enviados por upload (ADR 0006). Relativo = a partir da raiz do repositório. Fora do git.
    fit_dir: str = "dados-upload/fit"
    # Camada de LLM trocavel (AGENTS.md, ADR 0013 item 3). Vazio em `llm_model` = nao configurado.
    llm_provider: str = "groq"
    llm_model: str = ""
    llm_timeout_s: float = 20.0  # por chamada, sem nova tentativa dentro da chamada
    llm_limite_chamadas: int = 20  # por execucao do worker
    llm_intervalo_s: float = 0.0  # pausa entre chamadas na mesma execucao (limite por minuto do provedor); 0 = sem pausa
    # Chaves dos provedores: so no .env local, nunca no repositorio, nunca em log (SecretStr).
    groq_api_key: SecretStr | None = None
    openai_api_key: SecretStr | None = None
    anthropic_api_key: SecretStr | None = None


def lista_origens(texto: str) -> list[str]:
    """Separa `CORS_ORIGENS` por vírgula, sem espaços nem itens vazios. `*` é proibido (ADR 0004)."""
    origens = [o.strip() for o in texto.split(",") if o.strip()]
    if "*" in origens:
        raise ValueError("CORS_ORIGENS não aceita '*': liste as origens do app, separadas por vírgula")
    return origens


settings = Settings()


def pasta_fit(valor: str | Path | None = None) -> Path:
    """Pasta dos FIT guardados: `valor` ou `FIT_DIR`. Caminho relativo conta a partir da raiz do repositório."""
    caminho = Path(settings.fit_dir if valor is None else valor)
    return caminho if caminho.is_absolute() else RAIZ_REPOSITORIO / caminho
