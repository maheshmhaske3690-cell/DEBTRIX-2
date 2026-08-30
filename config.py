"""
Central configuration. All secrets/config come from environment
variables (.env locally, real env vars in production) — nothing
sensitive is ever hardcoded here.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    DATABASE_URL: str

    # Redis / job queue
    REDIS_URL: str

    # Auth
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    TOKEN_ENCRYPTION_KEY: str

    # GitHub OAuth
    GITHUB_CLIENT_ID: str
    GITHUB_CLIENT_SECRET: str
    GITHUB_OAUTH_REDIRECT_URI: str

    # Frontend
    FRONTEND_URL: str = "http://localhost:3000"

    # Scan worker
    CLONE_TMP_DIR: str = "/tmp/debtrix_scans"


settings = Settings()
