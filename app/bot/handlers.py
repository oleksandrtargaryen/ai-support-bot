import logging

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message
from langchain_core.messages import HumanMessage
from langgraph.graph.state import CompiledStateGraph

router = Router()
logger = logging.getLogger(__name__)

WELCOME = (
    "Hi! I'm the TurboFix assistant.\n\n"
    "I can show our services, find a free slot, book, move or cancel your "
    "appointment, and answer questions about the workshop. Just tell me what "
    'you need - for example: "Book an oil change tomorrow morning".'
)

FALLBACK = "Sorry, something went wrong on my side. Please try again in a minute."


@router.message(CommandStart())
@router.message(Command("help"))
async def start(message: Message) -> None:
    await message.answer(WELCOME)


@router.message(F.text)
async def chat(message: Message, graph: CompiledStateGraph) -> None:
    if message.from_user is None or message.text is None:
        return
    await message.bot.send_chat_action(message.chat.id, "typing")
    config = {
        "configurable": {
            "thread_id": str(message.chat.id),
            "telegram_id": message.from_user.id,
            "client_name": message.from_user.full_name,
        }
    }
    try:
        result = await graph.ainvoke({"messages": [HumanMessage(message.text)]}, config)
        reply = result["messages"][-1].text
    except Exception:
        logger.exception("Agent failed for chat %s", message.chat.id)
        await message.answer(FALLBACK)
        return
    await message.answer(reply or FALLBACK)
