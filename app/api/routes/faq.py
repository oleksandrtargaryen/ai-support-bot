from pathlib import Path

import anyio
from fastapi import APIRouter

from app.agent.rag import ingest_faq

router = APIRouter(prefix="/faq", tags=["faq"])

FAQ_DIR = Path(__file__).resolve().parents[3] / "data" / "faq"


@router.post("/reindex")
async def reindex_faq() -> dict[str, int]:
    chunks = await anyio.to_thread.run_sync(ingest_faq, FAQ_DIR)
    return {"chunks": chunks}
