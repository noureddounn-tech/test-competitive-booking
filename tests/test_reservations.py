import asyncio
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event, func, select

from app.database import async_session_factory, engine
from app.main import app
from app.models import Reservation


@pytest.mark.asyncio
async def test_concurrent_bookings_never_exceed_capacity(create_scenario) -> None:
    scenario = await create_scenario(capacity=3)
    slot_id = scenario["slot_id"]
    user_id = scenario["user_ids"][0]

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        responses = await asyncio.gather(
            *[
                client.post(
                    f"/slots/{slot_id}/reservations",
                    json={"user_id": user_id, "request_id": f"parallel-{index}-{uuid4().hex}"},
                )
                for index in range(12)
            ]
        )

    statuses = [response.status_code for response in responses]
    assert statuses.count(201) == 3
    assert statuses.count(409) == 9

    async with async_session_factory() as session:
        count = await session.scalar(
            select(func.count(Reservation.id)).where(
                Reservation.slot_id == slot_id,
                Reservation.status == "confirmed",
            )
        )
    assert count == 3


@pytest.mark.asyncio
async def test_retries_with_same_request_id_return_same_reservation(create_scenario) -> None:
    scenario = await create_scenario(capacity=2)
    slot_id = scenario["slot_id"]
    user_id = scenario["user_ids"][0]
    payload = {"user_id": user_id, "request_id": f"retry-{uuid4().hex}"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        first = await client.post(f"/slots/{slot_id}/reservations", json=payload)
        second = await client.post(f"/slots/{slot_id}/reservations", json=payload)

    assert first.status_code == second.status_code == 201
    assert first.json()["id"] == second.json()["id"]

    async with async_session_factory() as session:
        count = await session.scalar(
            select(func.count(Reservation.id)).where(
                Reservation.slot_id == slot_id,
                Reservation.user_id == user_id,
            )
        )
    assert count == 1


@pytest.mark.asyncio
async def test_cancellation_restores_availability_and_keeps_history(create_scenario) -> None:
    scenario = await create_scenario(capacity=1)
    slot_id = scenario["slot_id"]
    user_id = scenario["user_ids"][0]

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        created = await client.post(
            f"/slots/{slot_id}/reservations",
            json={"user_id": user_id, "request_id": f"cancel-{uuid4().hex}"},
        )
        assert created.status_code == 201
        reservation_id = created.json()["id"]
        booked = await client.get(f"/slots/{slot_id}")
        assert booked.json()["available"] == 0

        cancelled = await client.delete(f"/reservations/{reservation_id}")
        cancelled_again = await client.delete(f"/reservations/{reservation_id}")
        available = await client.get(f"/slots/{slot_id}")

    assert cancelled.status_code == cancelled_again.status_code == 204
    assert available.json()["available"] == 1
    async with async_session_factory() as session:
        reservation = await session.get(Reservation, reservation_id)
    assert reservation is not None
    assert reservation.status == "cancelled"


@pytest.mark.asyncio
async def test_reservation_list_is_paginated_and_uses_two_selects(create_scenario) -> None:
    scenario = await create_scenario(capacity=10, user_count=3)
    slot_id = scenario["slot_id"]
    user_ids = scenario["user_ids"]

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        for index, user_id in enumerate(user_ids):
            response = await client.post(
                f"/slots/{slot_id}/reservations",
                json={"user_id": user_id, "request_id": f"list-{uuid4().hex}-{index}"},
            )
            assert response.status_code == 201

        statement_count = 0

        def count_selects(_conn, _cursor, statement, _parameters, _context, _executemany):
            nonlocal statement_count
            if statement.lstrip().upper().startswith("SELECT"):
                statement_count += 1

        event.listen(engine.sync_engine, "before_cursor_execute", count_selects)
        try:
            response = await client.get(f"/slots/{slot_id}/reservations?limit=2&offset=1")
        finally:
            event.remove(engine.sync_engine, "before_cursor_execute", count_selects)

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 3
    assert body["limit"] == 2
    assert body["offset"] == 1
    assert len(body["items"]) == 2
    assert all(item["user_name"].startswith("Test user") for item in body["items"])
    assert all(item["event_name"].startswith("Test event") for item in body["items"])
    assert statement_count == 2
