"""Populate the database with demo services and mechanics."""

import asyncio

from sqlalchemy import select

from app.db.models import Mechanic, Service
from app.db.session import get_session

SERVICES = [
    Service(
        name="Oil change",
        description="Engine oil and oil filter replacement",
        duration_min=60,
        price=50,
    ),
    Service(
        name="Diagnostics",
        description="Full computer diagnostics with error report",
        duration_min=60,
        price=40,
    ),
    Service(
        name="Tire change",
        description="Seasonal tire change and balancing, 4 wheels",
        duration_min=90,
        price=60,
    ),
    Service(
        name="Brake pads replacement",
        description="Front or rear brake pads replacement, per axle",
        duration_min=120,
        price=90,
    ),
    Service(
        name="Wheel alignment",
        description="3D wheel alignment check and adjustment",
        duration_min=90,
        price=70,
    ),
]

MECHANICS = [
    Mechanic(name="Bob Wrench", specialization="engines"),
    Mechanic(name="Alice Torque", specialization="brakes and suspension"),
    Mechanic(name="Max Piston", specialization="tires and alignment"),
]


async def seed() -> None:
    async with get_session() as session:
        existing = (await session.execute(select(Service.id).limit(1))).first()
        if existing:
            print("Database already has services, skipping seed.")
            return
        session.add_all(SERVICES)
        session.add_all(MECHANICS)
        await session.commit()
        print(f"Seeded {len(SERVICES)} services and {len(MECHANICS)} mechanics.")


if __name__ == "__main__":
    asyncio.run(seed())
