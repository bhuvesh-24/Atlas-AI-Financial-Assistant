from pydantic_settings import BaseSettings
from typing import Optional, List


class Settings(BaseSettings):
    TELEGRAM_BOT_TOKEN: str

    GROQ_API_KEY: Optional[str] = None
    GROQ_MODEL: str = "llama-3.1-8b-instant"

    OPENROUTER_API_KEY: Optional[str] = None
    OPENROUTER_MODEL: str = "meta-llama/llama-3.3-70b-instruct:free"

    LLM_PROVIDER: str = "auto"  # auto | groq | openrouter

    FINNHUB_API_KEY: Optional[str] = None
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/oauth/callback"
    OAUTH_SERVER_PORT: int = 8000

    DATABASE_URL: str = "sqlite+aiosqlite:////app/data/atlas.db"
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"
    DAILY_BRIEFING_HOUR: int = 8
    DAILY_BRIEFING_MINUTE: int = 30
    TIMEZONE: str = "Asia/Kolkata"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()