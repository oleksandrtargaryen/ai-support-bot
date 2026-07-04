# TurboFix — AI Support Bot

Telegram support bot for a car service workshop. An LLM agent built on
**LangGraph** manages client appointments on its own — it looks up services,
finds free slots, books, reschedules and cancels visits — and answers general
questions using **RAG** over a FAQ knowledge base in **Chroma**.

## Features

- **Booking agent** — a ReAct-style LangGraph agent with 7 tools:
  `list_services`, `check_availability`, `create_booking`, `my_bookings`,
  `cancel_booking`, `reschedule_booking`, `search_faq`
- **FAQ over RAG** — markdown documents chunked and embedded into Chroma,
  retrieved as a tool call
- **Conversation memory** — LangGraph Postgres checkpointer, one thread per
  Telegram chat
- **Security by construction** — the client's `telegram_id` is injected into
  tools via `RunnableConfig`, not through the LLM, so the agent cannot touch
  other clients' appointments
- **Admin REST API** — CRUD for services, appointment management and FAQ
  reindexing, protected by an API key
- **Provider-agnostic LLM** — any model supported by LangChain
  `init_chat_model` / `init_embeddings`, configured via `.env`

## Stack

| Layer | Tech |
| --- | --- |
| Agent | LangGraph, LangChain |
| Telegram | aiogram 3 (webhook mode) |
| API | FastAPI, Pydantic v2 |
| Database | PostgreSQL, SQLAlchemy 2 (async), Alembic |
| Vector store | Chroma |
| Infra | Docker Compose, uv, ruff, pytest |

## Architecture

```
Telegram ──webhook──▶ FastAPI ──▶ aiogram Dispatcher ──▶ LangGraph agent
                        │                                   │
                        │                          ┌────────┴────────┐
Admin ──X-API-Key──▶ /api/v1                     tools            search_faq
                        │                          │                 │
                        ▼                          ▼                 ▼
                    PostgreSQL ◀────────── booking services       Chroma
                    (+ checkpointer)
```

The agent graph:

```
START ──▶ agent ◀──▶ tools
            │
            ▼
           END
```

## Quick start

```bash
cp .env.example .env   # fill in TELEGRAM_BOT_TOKEN, OPENAI_API_KEY, ADMIN_API_KEY
docker compose up -d --build
docker compose exec app python -m scripts.seed        # demo services & mechanics
docker compose exec app python -m scripts.ingest_faq  # index FAQ into Chroma
```

For the Telegram webhook you need a public URL. Locally the easiest way is:

```bash
ngrok http 8000
# put the https URL into WEBHOOK_BASE_URL in .env and restart:
docker compose up -d app
```

Then message your bot: *"Book an oil change tomorrow morning"*.

## Local development

```bash
uv sync
docker compose up -d postgres chroma
uv run alembic upgrade head
uv run pytest
uv run ruff check .
uv run uvicorn app.main:app --reload
```

## Admin API

All endpoints live under `/api/v1` and require the `X-API-Key` header.

| Method | Path | Description |
| --- | --- | --- |
| GET | `/services` | list services |
| POST | `/services` | create a service |
| PATCH | `/services/{id}` | update a service |
| DELETE | `/services/{id}` | delete a service |
| GET | `/appointments` | list appointments (`?status_filter=scheduled`) |
| DELETE | `/appointments/{id}` | cancel an appointment |
| POST | `/faq/reindex` | re-embed FAQ documents into Chroma |

Interactive docs: `http://localhost:8000/docs`.

## Project layout

```
app/
  agent/      # LangGraph graph, tools, prompts, RAG
  api/        # admin REST API
  bot/        # aiogram handlers and middlewares
  db/         # SQLAlchemy models and session
  services/   # business logic: availability, booking rules
  schemas/    # Pydantic schemas
data/faq/     # FAQ knowledge base (markdown)
migrations/   # Alembic
scripts/      # seed and FAQ ingestion
tests/        # pytest (no live LLM required)
```

## License

Apache 2.0
