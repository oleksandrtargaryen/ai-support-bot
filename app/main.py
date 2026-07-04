import logging
from contextlib import asynccontextmanager

from aiogram import Bot, Dispatcher
from aiogram.types import Update
from fastapi import APIRouter, Depends, FastAPI, Request
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from app.agent.graph import build_graph
from app.api.deps import require_api_key
from app.api.routes import appointments, faq, services
from app.bot.handlers import router as bot_router
from app.bot.middlewares import ClientUpsertMiddleware
from app.config import get_settings

logging.basicConfig(level=logging.INFO)


def create_dispatcher() -> Dispatcher:
    dp = Dispatcher()
    dp.message.middleware(ClientUpsertMiddleware())
    dp.include_router(bot_router)
    return dp


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()

    async with AsyncPostgresSaver.from_conn_string(settings.sync_database_url) as checkpointer:
        await checkpointer.setup()

        app.state.bot = Bot(token=settings.telegram_bot_token)
        app.state.dispatcher = create_dispatcher()
        app.state.dispatcher["graph"] = build_graph(checkpointer)

        if settings.webhook_base_url:
            await app.state.bot.set_webhook(
                settings.webhook_base_url.rstrip("/") + settings.webhook_path,
                drop_pending_updates=True,
            )
        yield
        await app.state.bot.delete_webhook()
        await app.state.bot.session.close()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="TurboFix support bot", lifespan=lifespan)

    @app.post(settings.webhook_path, include_in_schema=False)
    async def telegram_webhook(request: Request) -> dict[str, bool]:
        update = Update.model_validate(await request.json(), context={"bot": request.app.state.bot})
        await request.app.state.dispatcher.feed_update(request.app.state.bot, update)
        return {"ok": True}

    admin = APIRouter(prefix="/api/v1", dependencies=[Depends(require_api_key)])
    admin.include_router(services.router)
    admin.include_router(appointments.router)
    admin.include_router(faq.router)
    app.include_router(admin)

    @app.get("/health", include_in_schema=False)
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
