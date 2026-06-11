from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    llm_model: str
    llm_base_url: str
    llm_api_key: str
    memory_id: str
    akc_kb_dir: str = "./kb_data"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


# Module-level singleton — raises pydantic.ValidationError at import if any var missing.
# DO NOT catch this exception. The process must crash before uvicorn accepts connections.
settings = Settings()
