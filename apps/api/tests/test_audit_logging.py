"""Audit logging safety: the audit helper must refuse sensitive fields
outright (never redact-and-continue) and correlate events to request IDs."""

import pytest

from app.core.audit import audit


@pytest.mark.parametrize(
    "field", ["secret", "worker_secret", "secret_hash", "token", "authorization", "SECRET"]
)
def test_audit_refuses_sensitive_fields(field):
    with pytest.raises(ValueError, match="sensitive"):
        audit(None, "some_event", **{field: "value-that-must-never-be-logged"})


@pytest.mark.parametrize("field", ["name", "module", "filename", "message", "args"])
def test_audit_refuses_log_record_reserved_fields(field):
    """Regression: `audit(request, "workspace_created", name=...)` passed
    Python's own `logging.LogRecord` type-checks and unit-tested cleanly,
    then raised KeyError deep inside stdlib logging the first time an
    actual request hit it, because `extra={"name": ...}` collides with
    the LogRecord's own `name` attribute. Catch these at the call site.
    """
    with pytest.raises(ValueError, match="LogRecord"):
        audit(None, "some_event", **{field: "value"})


def test_audit_accepts_identifiers(caplog):
    with caplog.at_level("INFO", logger="audit"):
        audit(None, "worker_registered", worker_id="abc", credential_id="def")
    record = next(r for r in caplog.records if r.getMessage() == "worker_registered")
    assert record.audit_event == "worker_registered"
    assert record.worker_id == "abc"


@pytest.mark.asyncio
async def test_request_id_header_present(client):
    response = await client.get("/health")
    assert "x-request-id" in response.headers
