"""Application configuration."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Settings loaded from environment variables or safe defaults."""

    app_name: str = "Resume Job Matcher API"
    app_env: str = "development"
    frontend_origin: str = "http://127.0.0.1:5500"
    max_upload_mb: int = 5
    embedding_model_name: str = "all-MiniLM-L6-v2"
    embedding_device: str = "auto"
    embedding_batch_size: int = 32
    embedding_warmup_on_startup: bool = True
    llm_enabled: bool | str = False
    llm_provider: str = "ollama"
    ollama_mode: str = "local"
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "llama3.2:1b"
    ollama_api_key: str = ""
    llm_timeout_seconds: int | str = 60

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
