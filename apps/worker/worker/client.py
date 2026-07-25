"""Reference worker client — implements the registration/heartbeat/claim/
ack/submit protocol against the worker_registry and stage_assignments
tables. NO generation logic: `execute_stage` is the one method a real
worker subclasses/injects, and this reference implementation's default
just returns a canned success — enough to exercise the whole contract in
tests without pretending to do AI generation (out of scope this
milestone).

This client talks to the API's database directly (same Postgres, via the
shared apps/api SQLAlchemy models) rather than over HTTP, matching the
"in-process reference client" scope agreed for M4. A future real worker
process would either import this client the same way or reimplement the
same protocol over an HTTP/gRPC facade — the protocol is what's fixed,
not the transport.
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime

logger = logging.getLogger("worker.client")

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
        max_concurrency: int = 1,
        workspace_id: uuid.UUID | None = None,
        executor: StageExecutor = _default_executor,
        heartbeat_interval_seconds: int = 10,
        lease_seconds: int = 60,
    ) -> None:
        self.name = name
        self.supported_stages = supported_stages
        self.max_concurrency = max_concurrency
        self.workspace_id = workspace_id
        self.executor = executor
        self.heartbeat_interval_seconds = heartbeat_interval_seconds
        self.lease_seconds = lease_seconds
        self.worker_id: uuid.UUID | None = None
        self._draining = False

    async def register(self, session) -> uuid.UUID:
        from app.models.enums import WorkerStatus
        from app.models.workers import WorkerRegistration

        registration = WorkerRegistration(
            id=uuid.uuid4(), workspace_id=self.workspace_id, name=self.name,
            supported_stages=self.supported_stages, capabilities={},
            status=WorkerStatus.ONLINE, max_concurrency=self.max_concurrency,
            current_load=0, health_score=100,
            last_heartbeat_at=datetime.now(UTC), registered_at=datetime.now(UTC),
        )
        session.add(registration)
        await session.flush()
        self.worker_id = registration.id
        return registration.id

    async def heartbeat(self, session) -> None:
        from app.models.workers import WorkerHeartbeat, WorkerRegistration

        if self.worker_id is None:
            return
        registration = await session.get(WorkerRegistration, self.worker_id)
        if registration is None:
            return
        now = datetime.now(UTC)
        registration.last_heartbeat_at = now
        # Health score recovers over time absent failures; a real
        # implementation would factor in recent success/failure ratio —
        # this reference version keeps it simple and honest about that.
        registration.health_score = min(100, registration.health_score + 1)
        session.add(
            WorkerHeartbeat(
                id=uuid.uuid4(), worker_id=self.worker_id, status=registration.status,
                current_load=registration.current_load, heartbeat_at=now,
            )
        )

    async def drain(self, session) -> None:
        """Graceful shutdown: stop accepting new work, let in-flight
        assignments finish naturally (their leases aren't touched)."""
        from app.models.enums import WorkerStatus
        from app.models.workers import WorkerRegistration

        self._draining = True
        if self.worker_id is None:
            return
        registration = await session.get(WorkerRegistration, self.worker_id)
        if registration is not None:
            registration.status = WorkerStatus.DRAINING

    async def go_offline(self, session) -> None:
        from app.models.enums import WorkerStatus
        from app.models.workers import WorkerRegistration

        if self.worker_id is None:
            return
        registration = await session.get(WorkerRegistration, self.worker_id)
        if registration is not None:
            registration.status = WorkerStatus.OFFLINE

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
