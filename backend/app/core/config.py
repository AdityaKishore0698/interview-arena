from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Interview Arena API"
    DATABASE_URL: str = "postgresql+asyncpg://arena_user:arena_password@localhost:5432/interview_arena"
    REDIS_URL: str = "redis://localhost:6379"
    SECRET_KEY: str = "supersecret_jwt_key_that_is_at_least_32_bytes_long"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7

    # OAuth
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    FRONTEND_URL: str = "http://localhost:3000"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
