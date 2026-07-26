# Replit Instructions -- Milestone 4 Workstream 1

## Objective

Implement **only Workstream 1**. Do not begin any other Milestone 4
work.

### Scope

-   Worker Registry
-   Worker Heartbeats
-   Worker Capability Model

### Do NOT implement yet

-   Scheduling
-   Job claiming
-   Lease management
-   Execution queues
-   Back-pressure
-   Dead-letter handling
-   Worker execution

## Before Writing Code

Produce a design document covering:

1.  Database schema
2.  SQLAlchemy models
3.  Alembic migrations
4.  Index strategy
5.  RLS policies
6.  Authentication and authorization
7.  FastAPI endpoints
8.  Worker state transitions
9.  Race conditions and mitigations
10. Acceptance tests

Wait for approval before implementing.

## After Approval

Implement only Workstream 1.

Requirements: - PostgreSQL-first - Full RLS - Alembic migrations -
SQLAlchemy models - FastAPI endpoints - Integration tests - PostgreSQL
tests - Documentation - GitHub Actions updates if required

Worker Registry must support: - Registration - Deregistration -
Heartbeats - Last-seen timestamp - Version - Capabilities - Maximum
concurrency - Current load - Worker status - Offline detection -
Workspace isolation where applicable

After implementation: - Run the complete audit process - Open a Pull
Request - Stop and wait for approval before Workstream 2
