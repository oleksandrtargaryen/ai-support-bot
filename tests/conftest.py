import os
from collections.abc import AsyncIterator

import pytest
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

os.environ.setdefault("TELEGRAM_BOT_TOKEN", "test-token")
os.environ.setdefault("ADMIN_API_KEY", "test-key")

from app.config import Settings  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.models import Mechanic, Service  # noqa: E402


@pytest.fixture
def settings() -> Settings:
    return Settings(
        telegram_bot_token="test-token",
        admin_api_key="test-key",
        _env_file=None,
    )


@pytest.fixture
async def db_factory() -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


@pytest.fixture
async def session(db_factory) -> AsyncIterator[AsyncSession]:
    async with db_factory() as session:
        yield session


@pytest.fixture
async def service(session: AsyncSession) -> Service:
    obj = Service(name="Oil change", description="Engine oil and filter", duration_min=60, price=50)
    session.add(obj)
    await session.commit()
    return obj


@pytest.fixture
async def mechanic(session: AsyncSession) -> Mechanic:
    obj = Mechanic(name="Bob", specialization="engines")
    session.add(obj)
    await session.commit()
    return obj
