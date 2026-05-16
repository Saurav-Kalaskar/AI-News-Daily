from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    LLM_API_KEY: str
    LLM_BASE_URL: str = "https://integrate.api.nvidia.com/v1"
    MODEL_NAME: str = "meta/llama-3.1-70b-instruct"
    TELEGRAM_BOT_TOKEN: str
    TELEGRAM_CHANNEL_ID: str
    MAX_RETRIES: int = 3
    # Async infra
    DATABASE_URL: str = "postgresql+asyncpg://user:pass@localhost/ai_news_db"
    REDIS_URL: str = "redis://localhost:6379/0"

    class Config:
        env_file = ".env"
