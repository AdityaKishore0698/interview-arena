import urllib.parse

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def normalize_pg_url(url: str) -> str:
    """Coerce a Postgres URL into the form SQLAlchemy + asyncpg expect.

    Hosted providers (Render, Supabase, Neon, Heroku, …) hand out plain
    ``postgres://`` / ``postgresql://`` URLs, which SQLAlchemy routes to the
    synchronous ``psycopg2`` driver — not installed here — and often carry
    libpq-only query params (``sslmode``, ``channel_binding``) that the async
    ``asyncpg`` driver rejects. This rewrites the scheme to
    ``postgresql+asyncpg://`` and translates/strips those params. It is a
    no-op for URLs that are already in the correct form.
    """
    if not url:
        return url

    if url.startswith("postgres://"):
        url = "postgresql+asyncpg://" + url[len("postgres://") :]
    elif url.startswith("postgresql://"):
        url = "postgresql+asyncpg://" + url[len("postgresql://") :]

    if "?" not in url:
        return url

    base, query = url.split("?", 1)
    out: list[tuple[str, str]] = []
    for key, value in urllib.parse.parse_qsl(query, keep_blank_values=True):
        if key == "sslmode":
            # asyncpg accepts the same values under the ``ssl`` key.
            out.append(("ssl", value))
        elif key in ("channel_binding", "gssencmode"):
            # libpq-only; asyncpg negotiates these itself.
            continue
        else:
            out.append((key, value))

    return base + ("?" + urllib.parse.urlencode(out) if out else "")


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

    # Outbound email (OTP / password reset). Leave SMTP_HOST empty to fall
    # back to console logging — no setup required for local dev.
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = ""
    SMTP_USE_TLS: bool = True

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @field_validator("DATABASE_URL", mode="after")
    @classmethod
    def _normalize_database_url(cls, v: str) -> str:
        return normalize_pg_url(v)


settings = Settings()
