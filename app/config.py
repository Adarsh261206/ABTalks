from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="VIVA_", env_file=".env", extra="ignore"
    )

    app_name: str = "VIVA Interview Agent"
    data_dir: Path = Path("data")
    session_ttl_hours: float = 2.0
    rate_limit_per_minute: int = 60
    max_message_chars: int = 4000
    max_body_bytes: int = 1_048_576
    max_turns: int = 50
    default_questions: int = 8

    llm_provider: str = "mock"
    llm_model: str = ""
    llm_base_url: str = ""
    llm_temperature: float = 0.2
    openai_api_key: str = ""
    groq_api_key: str = ""

    curriculum_path: Path = Path("curriculum.json")

    @property
    def db_path(self) -> Path:
        return self.data_dir / "viva.db"


settings = Settings()
