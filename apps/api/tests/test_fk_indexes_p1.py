"""P-006 — every foreign-key column has a leading-column index."""

from __future__ import annotations

import pytest
from sqlalchemy import text

from app.db.session import AsyncSessionLocal

_UNINDEXED_FK_SQL = """
SELECT
  c.conrelid::regclass::text AS table_name,
  a.attname AS column_name,
  c.conname AS constraint_name
FROM pg_constraint c
JOIN pg_attribute a ON a.attrelid = c.conrelid AND a.attnum = ANY (c.conkey)
WHERE c.contype = 'f'
  AND NOT EXISTS (
    SELECT 1 FROM pg_index i
    WHERE i.indrelid = c.conrelid
      AND (i.indkey::int2[])[0] = a.attnum
  )
ORDER BY 1, 2;
"""


@pytest.mark.asyncio
async def test_no_unindexed_foreign_key_columns():
    async with AsyncSessionLocal() as session:
        rows = (await session.execute(text(_UNINDEXED_FK_SQL))).mappings().all()
    assert rows == [], f"unindexed FK columns remain: {rows}"
