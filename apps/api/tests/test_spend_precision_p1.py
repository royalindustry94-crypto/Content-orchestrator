"""P-009 — spend caps preserve sub-cent (4 decimal) precision."""

from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy import text

from app.db.session import AsyncSessionLocal


@pytest.mark.asyncio
async def test_spend_cap_preserves_sub_cent_precision(client, new_user):
    _uid, _tok, headers = new_user
    ws = await client.post("/workspaces", headers=headers, json={"name": "Subcent Cap"})
    ws_id = ws.json()["id"]
    patched = await client.patch(
        f"/workspaces/{ws_id}/spend",
        headers=headers,
        json={"daily_cap_usd": "0.0050", "monthly_cap_usd": "0.0100"},
    )
    assert patched.status_code == 200, patched.text
    body = patched.json()
    assert Decimal(str(body["daily_cap_usd"])) == Decimal("0.005")
    assert Decimal(str(body["monthly_cap_usd"])) == Decimal("0.01")

    async with AsyncSessionLocal() as session:
        row = (
            await session.execute(
                text(
                    "SELECT daily_cap_usd, monthly_cap_usd FROM spend_caps "
                    "WHERE workspace_id = :ws AND provider IS NULL"
                ),
                {"ws": ws_id},
            )
        ).one()
    assert Decimal(str(row.daily_cap_usd)) == Decimal("0.0050")
    assert Decimal(str(row.monthly_cap_usd)) == Decimal("0.0100")


@pytest.mark.asyncio
async def test_spend_cap_rejects_more_than_four_decimals(client, new_user):
    _uid, _tok, headers = new_user
    ws = await client.post("/workspaces", headers=headers, json={"name": "Too Fine"})
    ws_id = ws.json()["id"]
    res = await client.patch(
        f"/workspaces/{ws_id}/spend",
        headers=headers,
        json={"daily_cap_usd": "0.00001", "monthly_cap_usd": "1"},
    )
    assert res.status_code == 422
