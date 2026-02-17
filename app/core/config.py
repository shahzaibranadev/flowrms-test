from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    database_url: str = "sqlite:///./invoice_reconciliation.db"
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4o-mini"
    ai_enabled: bool = True

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
