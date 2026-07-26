"""Environment-driven configuration for the API service.

Nothing in here has a hardcoded secret or a production default that would
silently do the wrong thing — required values have no default and will
fail fast at startup if missing, per the "no placeholder / no silent
failure" rule in the project instructions.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field, PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Core ---
    environment: str = Field(default="development")
    log_level: str = Field(default="INFO")
    service_name: str = Field(default="content-orchestrator-api")

    # --- Database ---
    # DATABASE_URL: migration/owner connection (Alembic, table ownership).
    # APP_DATABASE_URL: runtime connection used for request-scoped queries,
    # via the non-owner `app_runtime` role so Row Level Security actually
    # applies (the owner role bypasses RLS unless FORCE ROW LEVEL SECURITY
    # is set, and we don't want request traffic running as table owner
    # regardless). See docs/milestone-2-identity-and-access.md §6.
    database_url: PostgresDsn
    app_database_url: PostgresDsn

    # --- Supabase Auth ---
    # Supabase-issued JWTs are verified here, not issued here — see
    # docs/milestone-2-identity-and-access.md §1 for why.
    supabase_jwt_secret: str
    supabase_jwt_algorithm: str = Field(default="HS256")
    supabase_jwt_audience: str = Field(default="authenticated")

    # --- CORS ---
    cors_allow_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])

    # --- Worker registry (Workstream 1) ---
    # Liveness thresholds, server-clock only (see app/services/workers.py).
    worker_suspect_after_seconds: int = Field(default=30)
    worker_offline_after_seconds: int = Field(default=90)
    # Old credential stays valid this long after rotation (zero-downtime).
    worker_credential_rotation_grace_seconds: int = Field(default=3600)
    # Capability protocol versions this server accepts (negotiation).
    worker_capability_protocol_versions: list[int] = Field(default_factory=lambda: [1])
    # Server-driven offline sweep interval; the sweep task is disabled in
    # tests (they call mark_stale_workers_offline directly with a
    # controlled clock).
    worker_offline_sweep_interval_seconds: int = Field(default=30)

    # --- Spend controls (defaults; per-workspace overrides live in DB) ---
    default_daily_spend_cap_usd: float = Field(default=50.0)
    default_monthly_spend_cap_usd: float = Field(default=1000.0)


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton. FastAPI dependencies should import this,
    not construct Settings() directly, so config is loaded once per process.
    """
    return Settings()
