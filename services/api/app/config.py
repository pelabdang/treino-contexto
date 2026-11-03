from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://treino:treino@localhost:5432/treino"
    # Origens do app web liberadas no CORS, separadas por vírgula (ADR 0004, item 7). Vazio libera nenhuma.
    cors_origens: str = "http://localhost:8081"


def lista_origens(texto: str) -> list[str]:
    """Separa `CORS_ORIGENS` por vírgula, sem espaços nem itens vazios. `*` é proibido (ADR 0004)."""
    origens = [o.strip() for o in texto.split(",") if o.strip()]
    if "*" in origens:
        raise ValueError("CORS_ORIGENS não aceita '*': liste as origens do app, separadas por vírgula")
    return origens


settings = Settings()
