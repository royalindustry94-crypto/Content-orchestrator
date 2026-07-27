"""Scheduler's work queue (job_schedule) and per-workspace back-pressure
configuration (amendment 2: configurable back-pressure and fairness).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, Text, UniqueConstraint, text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, VersionMixin, WorkspaceScopedMixin
from app.models.enums import JobScheduleStatus, JobType


class JobSchedule(Base, WorkspaceScopedMixin, TimestampMixin, VersionMixin):
    """One row = one intention to run something at/after run_after. Covers
    retries, stage dispatch, timeouts, and recurring jobs uniformly.
    """

    __tablename__ = "job_schedule"
    __table_args__ = (
        Index(
            "ix_job_schedule_due",
            "status",
            "run_after",
            unique=False,
            postgresql_where=text("status = 'pending'::job_schedule_status"),
        ),
        Index(
            "ix_job_schedule_lease_expiry",
            "lease_expires_at",
            unique=False,
            postgresql_where=text("status = 'leased'::job_schedule_status"),
        ),
        Index(
            "ix_job_schedule_workspace_due",
            "workspace_id",
            "run_after",
            unique=False,
            postgresql_where=text("status = 'pending'::job_schedule_status"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_type: Mapped[JobType] = mapped_column(
        SAEnum(JobType, name="job_type", native_enum=True,
            values_callable=lambda obj: [e.value for e in obj]), nullable=False
    )
    ref_table: Mapped[str] = mapped_column(Text, nullable=False)
    ref_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    run_after: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[JobScheduleStatus] = mapped_column(
        SAEnum(JobScheduleStatus, name="job_schedule_status", native_enum=True,
            values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        default=JobScheduleStatus.PENDING,
    )
    lease_owner: Mapped[str | None] = mapped_column(Text, nullable=True)
    lease_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    attempt: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # Propagated for tracing (amendment 1) so a scheduler action can be
    # joined back to the workflow execution and trace it belongs to.
    correlation_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    trace_id: Mapped[str | None] = mapped_column(Text, nullable=True)


class WorkspaceConcurrencyLimit(Base, WorkspaceScopedMixin, TimestampMixin, VersionMixin):
    """Back-pressure / fairness config (amendment 2). One row per
    workspace; absence means the scheduler's global default applies.
    """

    __tablename__ = "workspace_concurrency_limits"
    __table_args__ = (UniqueConstraint("workspace_id", name="uq_workspace_concurrency_limit"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # Max stage_assignments this workspace may have in dispatched/
    # acknowledged state at once — the hard cap that prevents one
    # workspace from monopolizing worker capacity.
    max_concurrent_assignments: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    # Max job_schedule rows this workspace may have claimed by schedulers
    # in a single tick — bounds how much of one poll batch one tenant can
    # consume, which is the scheduler-fairness half of back-pressure.
    max_per_scheduler_tick: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    # WS4: queue-depth thresholds for back-pressure observability / throttle.
    queue_soft_limit: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
    queue_hard_limit: Mapped[int] = mapped_column(Integer, nullable=False, default=200)
