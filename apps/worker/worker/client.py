"""Reference worker client — implements the registration/heartbeat/claim/
ack/renew/submit protocol over HTTP against the API's worker endpoints,
authenticated with a per-worker credential (Workstream 1–3).

NO generation logic: `execute_stage` is the one method a real worker
subclasses/injects, and this reference implementation's default just
returns a canned success — enough to exercise the whole contract in
tests without pretending to do AI generation.
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import Awaitable, Callable

import httpx

logger = logging.getLogger("worker.client")

CAPABILITY_PROTOCOL_VERSION = 1

# Type for the pluggable stage-execution function a real worker provides.
# Returns (success, result_dict_or_None, error_message).
StageExecutor = Callable[[dict], Awaitable[tuple[bool, dict | None, str]]]


async def _default_executor(assignment_context: dict) -> tuple[bool, dict | None, str]:
    """Default executor is Draft Desk (real structured output, never {})."""
    from worker.executors.draft_desk import draft_desk_executor

    return await draft_desk_executor(assignment_context)


class ReferenceWorkerClient:
    def __init__(
        self,
        *,
        name: str,
        supported_stages: list[str],
        http: httpx.AsyncClient,
        credential: str,
        worker_id: uuid.UUID | str,
        max_concurrency: int = 1,
        workspace_id: uuid.UUID | None = None,
        executor: StageExecutor = _default_executor,
        heartbeat_interval_seconds: int = 10,
        lease_seconds: int = 60,
        worker_version: str = "reference-0.4.0",
    ) -> None:
        """`http` is an httpx.AsyncClient pointed at the API (tests inject
        an ASGI-transport client); `credential` is the
        `<credential_id>.<secret>` string issued at provisioning, and
        `worker_id` the provisioned identity.
        """
        self.name = name
        self.supported_stages = supported_stages
        self.max_concurrency = max_concurrency
        self.workspace_id = workspace_id
        self.executor = executor
        self.heartbeat_interval_seconds = heartbeat_interval_seconds
        self.lease_seconds = lease_seconds
        self.worker_version = worker_version
        self._http = http
        self._auth_headers = {"Authorization": f"Bearer {credential}"}
        self.worker_id: uuid.UUID = (
            worker_id if isinstance(worker_id, uuid.UUID) else uuid.UUID(worker_id)
        )
        self.current_load = 0
        self._draining = False

    async def register(self) -> uuid.UUID:
        response = await self._http.post(
            "/workers/register",
            headers=self._auth_headers,
            json={
                "supported_stages": self.supported_stages,
                "capabilities": {
                    "protocol_version": CAPABILITY_PROTOCOL_VERSION,
                    "providers": [],
                    "features": [],
                },
                "worker_version": self.worker_version,
                "max_concurrency": self.max_concurrency,
            },
        )
        response.raise_for_status()
        return self.worker_id

    async def heartbeat(self) -> None:
        status = "draining" if self._draining else ("busy" if self.current_load else "online")
        response = await self._http.post(
            "/workers/heartbeat",
            headers=self._auth_headers,
            json={"status": status, "current_load": self.current_load},
        )
        response.raise_for_status()

    async def log(
        self,
        severity: str,
        message: str,
        *,
        pipeline_run_id: uuid.UUID | str | None = None,
        assignment_id: uuid.UUID | str | None = None,
        context: dict | None = None,
    ) -> dict:
        """Submit one durable Mission Control log event."""
        response = await self._http.post(
            "/workers/logs",
            headers=self._auth_headers,
            json={
                "severity": severity,
                "message": message,
                "pipeline_run_id": (
                    str(pipeline_run_id) if pipeline_run_id is not None else None
                ),
                "assignment_id": (
                    str(assignment_id) if assignment_id is not None else None
                ),
                "context": context or {},
            },
        )
        response.raise_for_status()
        return response.json()

    async def drain(self) -> None:
        """Graceful shutdown: stop accepting new work, let in-flight
        assignments finish naturally (their leases aren't touched)."""
        self._draining = True
        await self.heartbeat()

    async def deregister(self) -> None:
        response = await self._http.post("/workers/deregister", headers=self._auth_headers)
        response.raise_for_status()

    async def claim_next(self, session=None):
        """Pull-mode claim via HTTP (WS2/WS3). ``session`` is accepted for
        back-compat with older call sites and ignored — work transport is
        no longer direct-DB.
        """
        del session  # unused; HTTP path only
        if self._draining:
            return None
        response = await self._http.post(
            "/workers/claim",
            headers=self._auth_headers,
            json={},
        )
        response.raise_for_status()
        body = response.json()
        if body.get("outcome") != "granted" or body.get("assignment") is None:
            return None
        self.current_load += 1
        return body["assignment"]

    async def ack(self, assignment_id: uuid.UUID | str) -> dict:
        response = await self._http.post(
            f"/workers/assignments/{assignment_id}/ack",
            headers=self._auth_headers,
        )
        response.raise_for_status()
        return response.json()

    async def renew(self, assignment_id: uuid.UUID | str, session=None) -> dict:
        """HTTP lease renew. ``session`` ignored (back-compat)."""
        del session
        response = await self._http.post(
            f"/workers/assignments/{assignment_id}/renew",
            headers=self._auth_headers,
        )
        response.raise_for_status()
        return response.json()

    async def submit(
        self,
        assignment_id: uuid.UUID | str,
        *,
        success: bool,
        result: dict | None = None,
        error_message: str = "",
        provider_effect_key: str | None = None,
    ) -> dict:
        payload: dict = {
            "success": success,
            "result": result,
            "error_message": error_message,
        }
        if provider_effect_key is not None:
            payload["provider_effect_key"] = provider_effect_key
        response = await self._http.post(
            f"/workers/assignments/{assignment_id}/submit",
            headers=self._auth_headers,
            json=payload,
        )
        response.raise_for_status()
        if self.current_load > 0:
            self.current_load -= 1
        return response.json()

    async def run_one(self, session=None, assignment=None) -> None:
        """Execute (via the pluggable executor) and submit the result —
        the full worker-side half of the contract. ``assignment`` is the
        dict returned by ``claim_next`` (HTTP). ``session`` is unused.

        Protocol: ack (reserves provider effect key) → renew (keep lease
        alive across execution) → execute → submit. Real workers with
        long provider calls should renew on an interval; the reference
        client renews once immediately before submit as a minimal
        heartbeat-extend.
        """
        del session
        if assignment is None:
            return
        assignment_id = assignment["id"] if isinstance(assignment, dict) else assignment.id
        attempt = (
            assignment["attempt_number"]
            if isinstance(assignment, dict)
            else assignment.attempt_number
        )
        stage = assignment["stage"] if isinstance(assignment, dict) else assignment.stage
        await self.ack(assignment_id)
        effect_key = f"{assignment_id}:{attempt}"
        # Renew before side effects so a slow executor does not race the reaper.
        await self.renew(assignment_id)
        context = {
            "stage": stage,
            "assignment_id": str(assignment_id),
            "attempt_number": attempt,
            "provider_effect_key": effect_key,
        }
        if isinstance(assignment, dict):
            for key in (
                "topic",
                "content_item_id",
                "workspace_id",
                "target_length_seconds",
                "business_name",
                "offer",
                "target_audience",
                "brand_voice",
                "content_goal",
                "target_platform",
                "provider",
                "pipeline_run_id",
            ):
                if key in assignment and assignment[key] is not None:
                    context[key] = assignment[key]
        success, result, error = await self.executor(context)
        await self.submit(
            assignment_id,
            success=success,
            result=result,
            error_message=error,
            provider_effect_key=effect_key,
        )
