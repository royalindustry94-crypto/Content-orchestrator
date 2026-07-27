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

    # --- Lease management & recovery (Workstream 3) ---
    # Per-extension lease length granted on claim / ack / renew.
    assignment_lease_seconds: int = Field(default=60)
    # Hard ceiling from lease_started_at; renewals past this are rejected.
    assignment_max_lease_seconds: int = Field(default=900)
    # How often the maintenance tick reaps expired leases (and runs the
    # offline sweep). Disabled in test env (tests call reapers directly).
    assignment_reaper_interval_seconds: int = Field(default=15)
    assignment_reaper_batch_size: int = Field(default=100)
    # Used when a workflow stage definition cannot be resolved at recovery.
    assignment_default_max_attempts: int = Field(default=3)

    # --- Priority / back-pressure / provider budgets (Workstream 4) ---
    assignment_age_boost_interval_seconds: int = Field(default=60, ge=1)
    assignment_age_boost_per_interval: int = Field(default=1, ge=0)
    assignment_age_boost_max: int = Field(default=100, ge=0)
    workspace_tier_priority_weight: int = Field(default=10, ge=1)
    queue_soft_limit_default: int = Field(default=50, ge=1)
    queue_hard_limit_default: int = Field(default=200, ge=1)
    backpressure_eval_interval_seconds: int = Field(default=15, ge=1)
    # How many PENDING candidates a claim may lock while skipping saturated providers.
    claim_candidate_batch_size: int = Field(default=32, ge=1)

    # --- Spend controls (defaults; per-workspace overrides live in DB) ---
    default_daily_spend_cap_usd: float = Field(default=50.0)
    default_monthly_spend_cap_usd: float = Field(default=1000.0)


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton. FastAPI dependencies should import this,
    not construct Settings() directly, so config is loaded once per process.
    """
    return Settings()
