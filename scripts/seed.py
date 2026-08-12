import asyncio
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.database import async_session_factory
from app.models import Event, Reservation, Slot, User


async def seed() -> None:
    async with async_session_factory() as session:
        existing = await session.scalar(select(User).limit(1))
        if existing is not None:
            print("Database already seeded, skipping.")
            return

        alice = User(name="Alice Martin", email="alice@example.com")
        bob = User(name="Bob Dupont", email="bob@example.com")
        carol = User(name="Carol Nguyen", email="carol@example.com")
        session.add_all([alice, bob, carol])

        concert = Event(
            name="Concert Rock en Seine",
            date=datetime.now(UTC) + timedelta(days=30),
        )
        conference = Event(
            name="Conférence PyParis",
            date=datetime.now(UTC) + timedelta(days=60),
        )
        session.add_all([concert, conference])
        await session.flush()

        almost_full_slot = Slot(event_id=concert.id, capacity=3)
        roomy_slot = Slot(event_id=concert.id, capacity=50)
        conference_slot = Slot(event_id=conference.id, capacity=20)
        session.add_all([almost_full_slot, roomy_slot, conference_slot])
        await session.flush()

        session.add_all(
            [
                Reservation(slot_id=almost_full_slot.id, user_id=alice.id, request_id="seed-req-1"),
                Reservation(slot_id=almost_full_slot.id, user_id=bob.id, request_id="seed-req-2"),
            ]
        )

        await session.commit()
        print("Seed data created: 3 users, 2 events, 3 slots, 2 reservations.")
        print(
            f"Slot {almost_full_slot.id} has capacity 3 with 2 reservations already "
            "(1 spot left) — useful for manual concurrency testing."
        )


if __name__ == "__main__":
    asyncio.run(seed())
