from collections.abc import AsyncIterator

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import Settings
from app.db.base import Base
from app.db.models import Mechanic, Service


@pytest.fixture
def settings() -> Settings:
    return Settings(
        telegram_bot_token="test-token",
        admin_api_key="test-key",
        _env_file=None,
    )


@pytest.fixture
async def session() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


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
