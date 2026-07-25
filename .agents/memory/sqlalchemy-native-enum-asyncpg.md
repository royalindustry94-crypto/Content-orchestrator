---
name: SQLAlchemy 2 native enum asyncpg values_callable
description: Without values_callable, asyncpg sends Python enum .name (uppercase) to PG native enum columns, causing DataError at runtime.
---

# SQLAlchemy 2 native enum + asyncpg

**Rule:** Every `SAEnum(MyEnum, native_enum=True, ...)` column must include `values_callable=lambda obj: [e.value for e in obj]`.

**Why:** SQLAlchemy 2.0 with the asyncpg dialect sends the Python enum member's `.name` attribute (UPPERCASE) as the PG enum value when `values_callable` is absent. PostgreSQL native enums store lowercase values, so the insert fails with `DataError: invalid input value for enum`. With `values_callable`, SQLAlchemy registers the enum type using `.value` strings and sends those instead.

**How to apply:** Any time a model uses `SAEnum(SomePythonEnum, name="...", native_enum=True)`, add `values_callable=lambda obj: [e.value for e in obj]`. Apply to all 14+ model files that had this pattern (assignments, config, content, delivery, events, history, operations, pipeline, review_gate, scheduling, spend, workers, workflow, workspace_membership).
