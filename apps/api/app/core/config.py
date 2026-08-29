"""Environment-driven configuration for the API service.

Nothing in here has a hardcoded secret or a production default that would
silently do the wrong thing — required values have no default and will
fail fast at startup if missing, per the "no placeholder / no silent
failure" rule in the project instructions.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field, PostgresDsn, model_validator
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
    # AUTH_MODE=local enables /auth/signup|/auth/login which mint the same
    # JWT shape with this secret (Private Beta / staging without Supabase).
    # Default is supabase (fail-closed): local issuance must be opted in
    # explicitly via AUTH_MODE=local (see .env.example for Private Beta).
    supabase_jwt_secret: str
    supabase_jwt_algorithm: str = Field(default="HS256")
    supabase_jwt_audience: str = Field(default="authenticated")
    auth_mode: str = Field(default="supabase")  # local | supabase
    # Explicit break-glass for AUTH_MODE=local when ENVIRONMENT=production.
    allow_local_auth_in_production: bool = Field(default=False)

    # --- Runtime profile ---
    # Where this process runs, which decides whether it can host the
    # in-process automation loops at all.
    #   server     (default) long-lived process (uvicorn/container). The API
    #              also runs the scheduler, outbox relay and maintenance
    #              loops, exactly as before this setting existed.
    #   serverless per-request execution (e.g. Vercel Functions). The process
    #              is frozen between requests, so a loop started at cold start
    #              would not tick. Those loops are therefore not started, and
    #              /health/automation reports them unavailable rather than
    #              idle. Request-inline work is unaffected: auth, every
    #              pipeline stage, the auditors, and review decisions all run
    #              to completion inside the request that triggers them.
    runtime_profile: str = Field(default="server")

    # --- Scheduler (background tick in API lifespan) ---
    scheduler_interval_seconds: float = Field(default=2.0, ge=0.2)
    scheduler_batch_size: int = Field(default=50, ge=1)

    # Default estimated stage cost used when dispatching with Draft Desk.
    default_stage_estimate_usd: float = Field(default=0.01, ge=0)

    # --- CORS ---
    cors_allow_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])

    # --- Pipeline provider (WP-PB-005) ---
    # Selects the implementation behind every Scout → Compliance stage.
    #   null       (default) no vendor; each stage stops truthfully at
    #              provider_not_configured and spends nothing.
    #   simulation deterministic offline provider for pre-vendor testing. It
    #              performs no network I/O, costs nothing, labels every record
    #              it writes `simulation`, and is refused in production.
    # Activating a paid vendor is a separate audited milestone (PROVIDER-001).
    pipeline_provider_mode: str = Field(default="null")

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

    # --- Outbox relay (Private Beta review decisions + future consumers) ---
    outbox_relay_interval_seconds: float = Field(default=2.0, ge=0.2)

    # --- Stripe billing (P-001 / WP-PB-004) ---
    # When false (default), entitlements are not enforced — Private Beta P0 path.
    # When true, Stripe secrets + price + redirect URLs are required at runtime
    # for checkout/webhook routes (validated in billing service, not at import).
    billing_enabled: bool = Field(default=False)
    stripe_secret_key: str | None = Field(default=None)
    stripe_webhook_secret: str | None = Field(default=None)
    stripe_price_id_pro: str | None = Field(default=None)
    stripe_checkout_success_url: str | None = Field(default=None)
    stripe_checkout_cancel_url: str | None = Field(default=None)

    # --- Metrics scrape auth (M-3) ---
    # When set, GET /metrics requires Authorization: Bearer <token>.
    # When unset in production/prod, /metrics is disabled (401). Non-prod
    # may scrape without a token for local docker-compose / CI convenience.
    metrics_scraper_token: str | None = Field(default=None)

    # --- Deployment metadata (Operations Dashboard) ---
    # Injected by the deploy system. Null is rendered as unavailable; the
    # dashboard never fabricates CI, branch, or deployment values.
    deployment_git_branch: str | None = Field(default=None)
    deployment_commit_sha: str | None = Field(default=None)
    deployment_at: str | None = Field(default=None)
    deployment_ci_status: str | None = Field(default=None)
    deployment_ci_url: str | None = Field(default=None)

    # --- GitHub live status (Operations Dashboard V2) ---
    # Optional. When unset, GitHub widgets report unavailable (never fake).
    # Prefer GITHUB_TOKEN from Actions; GITHUB_API_TOKEN is an alternate name.
    github_token: str | None = Field(default=None)
    github_api_token: str | None = Field(default=None)
    github_repository: str | None = Field(default=None)  # owner/repo

    @property
    def openapi_docs_enabled(self) -> bool:
        """Swagger/ReDoc/OpenAPI JSON are development-only (P-005)."""
        return self.environment.strip().lower() in {"development", "dev"}

    @property
    def is_serverless(self) -> bool:
        return self.runtime_profile == "serverless"

    @property
    def background_loops_supported(self) -> bool:
        """Whether this runtime can host the automation loops.

        ENVIRONMENT=test is excluded for the existing reason (tests drive the
        reapers directly with a controlled clock), serverless because a frozen
        process cannot tick one.
        """
        return self.runtime_profile == "server" and self.environment.strip().lower() != "test"

    @property
    def background_loops_disabled_reason(self) -> str | None:
        """Why the loops are not running, for honest ops reporting."""
        if self.background_loops_supported:
            return None
        if self.environment.strip().lower() == "test":
            return "ENVIRONMENT=test: tests invoke the reapers directly with a controlled clock"
        return (
            "RUNTIME_PROFILE=serverless: the process is frozen between requests, "
            "so in-process background loops cannot tick and are not started"
        )

    @model_validator(mode="after")
    def _validate_auth_mode(self) -> Settings:
        mode = self.auth_mode.strip().lower()
        if mode not in {"local", "supabase"}:
            raise ValueError("AUTH_MODE must be 'local' or 'supabase'")
        object.__setattr__(self, "auth_mode", mode)
        env = self.environment.strip().lower()
        if (
            env in {"production", "prod"}
            and mode == "local"
            and not self.allow_local_auth_in_production
        ):
            raise ValueError(
                "AUTH_MODE=local is forbidden when ENVIRONMENT is production; "
                "set ALLOW_LOCAL_AUTH_IN_PRODUCTION=true only as an audited override"
            )
        return self

    @model_validator(mode="after")
    def _validate_runtime_profile(self) -> Settings:
        profile = self.runtime_profile.strip().lower()
        if profile not in {"server", "serverless"}:
            raise ValueError("RUNTIME_PROFILE must be 'server' or 'serverless'")
        object.__setattr__(self, "runtime_profile", profile)
        return self

    @model_validator(mode="after")
    def _validate_pipeline_provider_mode(self) -> Settings:
        mode = self.pipeline_provider_mode.strip().lower()
        if mode not in {"null", "simulation"}:
            raise ValueError("PIPELINE_PROVIDER_MODE must be 'null' or 'simulation'")
        object.__setattr__(self, "pipeline_provider_mode", mode)
        # Simulated content is synthetic by construction. There is no audited
        # override for shipping it from a production deployment.
        if mode == "simulation" and self.environment.strip().lower() in {"production", "prod"}:
            raise ValueError(
                "PIPELINE_PROVIDER_MODE=simulation is forbidden when ENVIRONMENT is production; "
                "simulated pipeline output must never be produced by a production deployment"
            )
        return self


def openapi_route_kwargs(environment: str) -> dict[str, str | None]:
    """FastAPI docs URL kwargs — disabled outside development (P-005)."""
    enabled = environment.strip().lower() in {"development", "dev"}
    if enabled:
        return {
            "docs_url": "/docs",
            "redoc_url": "/redoc",
            "openapi_url": "/openapi.json",
        }
    return {"docs_url": None, "redoc_url": None, "openapi_url": None}


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton. FastAPI dependencies should import this,
    not construct Settings() directly, so config is loaded once per process.
    """
    return Settings()
