from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    MONGO_URI: str = "mongodb://localhost:27017"
    MONGO_DB: str = "trackbucks"
    SECRET_KEY: str = "change-me-to-a-long-random-string"
    GEMINI_API_KEY: str = ""
    SMTP_EMAIL: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    DISASTER_THRESHOLD_STOCK: float = 5.0
    DISASTER_THRESHOLD_MF: float = 3.0
    POLL_INTERVAL_MINUTES: int = 15

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
