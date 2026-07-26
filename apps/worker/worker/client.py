"""Reference worker client — implements the registration/heartbeat/claim/
ack/submit protocol against the worker_registry and stage_assignments
tables. NO generation logic: `execute_stage` is the one method a real
worker subclasses/injects, and this reference implementation's default
just returns a canned success — enough to exercise the whole contract in
tests without pretending to do AI generation (out of scope this
milestone).

Lifecycle (register / heartbeat / deregister) goes over HTTP against the
API's worker endpoints, authenticated with a per-worker credential
(Workstream 1 — this replaced the M3 direct-database registration path).
Work transport (claim / renew / submit) still talks to Postgres directly
via the shared apps/api models; moving it to HTTP is a later workstream.
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
    """Reference default: always succeeds with an empty result. Exists so
    the reference client is runnable end-to-end in tests without a real
    generation backend — it is explicitly NOT a stand-in for generation
    logic, which this milestone excludes.
    """
    return True, {}, ""


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

    async def drain(self) -> None:
        """Graceful shutdown: stop accepting new work, let in-flight
        assignments finish naturally (their leases aren't touched)."""
        self._draining = True
        await self.heartbeat()

    async def deregister(self) -> None:
        response = await self._http.post("/workers/deregister", headers=self._auth_headers)
        response.raise_for_status()

    async def claim_next(self, session):
        """Pull-mode claim: find a pending assignment matching this
        worker's capabilities and take it (design doc §5.3, pull variant).
        """
        from app.models.assignments import StageAssignment
        from app.models.enums import StageAssignmentStatus
        from sqlalchemy import select

        if self._draining:
            return None

        result = await session.execute(
            select(StageAssignment)
            .where(
                StageAssignment.status == StageAssignmentStatus.PENDING,
                StageAssignment.stage.in_(self.supported_stages),
            )
            .order_by(StageAssignment.created_at)
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        assignment = result.scalar_one_or_none()
        if assignment is None:
            return None

        from app.orchestration import dispatcher

        assignment.worker_id = self.worker_id
        await dispatcher.acknowledge(session, assignment, lease_seconds=self.lease_seconds)
        return assignment

    async def renew(self, session, assignment) -> None:
        from app.orchestration import dispatcher

        await dispatcher.renew_lease(session, assignment, lease_seconds=self.lease_seconds)

    async def run_one(self, session, assignment) -> None:
        """Execute (via the pluggable executor) and submit the result —
        the full worker-side half of the contract."""
        from app.orchestration import dispatcher

        success, result, error = await self.executor(
            {"stage": assignment.stage, "assignment_id": str(assignment.id)}
        )
        await dispatcher.submit_result(
            session, assignment=assignment, success=success, result=result, error_message=error
        )
