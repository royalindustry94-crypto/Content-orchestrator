"""Environment-driven configuration for the worker service.

Mirrors apps/api/app/core/config.py deliberately — same fail-fast pattern
(required values have no default). The two services don't share a Python
package yet; if config drift becomes a real problem, promote this to
packages/ as a shared library rather than copy-pasting further changes.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field, PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class WorkerSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: str = Field(default="development")
    log_level: str = Field(default="INFO")
    service_name: str = Field(default="content-orchestrator-worker")

    database_url: PostgresDsn

    # How often the health-check loop runs, per the "API Health Monitor"
    # background agent in the spec. Configurable, not hardcoded to 9 minutes.
    health_check_interval_seconds: int = Field(default=300)


@lru_cache
def get_settings() -> WorkerSettings:
    return WorkerSettings()
