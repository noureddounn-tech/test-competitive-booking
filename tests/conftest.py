from collections.abc import AsyncIterator, Awaitable, Callable
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest_asyncio
from sqlalchemy import delete

from app.database import async_session_factory
from app.models import Event, Reservation, Slot, User

Scenario = dict[str, int | list[int]]
ScenarioFactory = Callable[..., Awaitable[Scenario]]


@pytest_asyncio.fixture
async def create_scenario() -> AsyncIterator[ScenarioFactory]:
    """Create isolated PostgreSQL rows and remove only rows created by a test."""
    scenarios: list[Scenario] = []

    async def factory(capacity: int = 2, user_count: int = 1) -> Scenario:
        token = uuid4().hex
        async with async_session_factory() as session:
            event = Event(
                name=f"Test event {token}",
                date=datetime.now(UTC) + timedelta(days=7),
            )
            users = [
                User(name=f"Test user {index}", email=f"{token}-{index}@example.test")
                for index in range(user_count)
            ]
            session.add_all([event, *users])
            await session.flush()
            slot = Slot(event_id=event.id, capacity=capacity)
            session.add(slot)
            await session.commit()
            scenario: Scenario = {
                "event_id": event.id,
                "slot_id": slot.id,
                "user_ids": [user.id for user in users],
            }
            scenarios.append(scenario)
            return scenario

    yield factory

    async with async_session_factory() as session:
        for scenario in scenarios:
            slot_id = int(scenario["slot_id"])
            event_id = int(scenario["event_id"])
            user_ids = list(scenario["user_ids"])
            await session.execute(delete(Reservation).where(Reservation.slot_id == slot_id))
            await session.execute(delete(Slot).where(Slot.id == slot_id))
            await session.execute(delete(User).where(User.id.in_(user_ids)))
            await session.execute(delete(Event).where(Event.id == event_id))
        await session.commit()
