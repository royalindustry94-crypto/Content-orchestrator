import os

os.environ.setdefault("DATABASE_URL", "postgresql://user:pass@localhost:5432/content_orchestrator_test")

from worker.core.config import get_settings


def test_settings_load_from_environment() -> None:
    settings = get_settings()
    assert settings.service_name == "content-orchestrator-worker"
    assert settings.health_check_interval_seconds > 0
