from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import Message

from app.db.session import get_session
from app.services.booking import get_or_create_client


class ClientUpsertMiddleware(BaseMiddleware):
    """Make sure every writing Telegram user exists as a Client row."""

    async def __call__(
        self,
        handler: Callable[[Message, dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: dict[str, Any],
    ) -> Any:
        if event.from_user is not None:
            async with get_session() as session:
                await get_or_create_client(session, event.from_user.id, event.from_user.full_name)
                await session.commit()
        return await handler(event, data)
