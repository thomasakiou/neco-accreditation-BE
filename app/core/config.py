from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    ADMIN_EMAIL: str = "admin@neco.gov.ng"
    ADMIN_PASSWORD: str = "123456"
    DEFAULT_STATE_PASSWORD: str = "NECOpassword@1"
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_TLS: bool = True

    class Config:
        env_file = ".env"

@lru_cache()
def get_settings():
    return Settings()
