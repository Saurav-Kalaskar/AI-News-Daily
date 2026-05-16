# AI News Daily — Architectural Conventions

## 1. Async-First
- All I/O-bound code runs under `asyncio`.
- Use `aiohttp` for HTTP requests, `asyncpg` / SQLAlchemy async for database, `aioredis` for Redis.
- No synchronous blocking calls in the main event loop.

## 2. aiogram 3.x
- Bot entry point: `bot/main.py` using `aiogram.Bot` + `Dispatcher`.
- Handlers live in `bot/handlers/` and use aiogram FSM (`aiogram.fsm`).
- FSM state storage backed by Redis (`RedisStorage`).
- Telegram API calls go through aiogram; never raw `requests.post`.

## 3. SQLAlchemy 2.0 + Async PostgreSQL
- Engine created with `create_async_engine("postgresql+asyncpg://...")`.
- Models use `declarative_base()` with type-annotated columns (`Mapped[int]`, etc.).
- Sessions via `async_sessionmaker` with `expire_on_commit=False`.
- All DB access through async context managers (`async with session.begin()`).

## 4. Redis
- Used for FSM state persistence and short-term caching (e.g., dedup hashes, rate limits).
- Connection pool initialized once at startup, injected into services.
- Keys namespaced: `ai_news:<entity>:<id>`.

## 5. MarkdownV2 Sanitization
- All text sent to Telegram MUST pass through the strict sanitizer (`services/sanitize.py`).
- Escape EVERY character in the Telegram MarkdownV2 reserved set: `_ * [ ] ( ) ~ ` > # + - = | { } . !`
- No raw strings reaching `bot.send_message`.
- Use `aiogram`'s built-in markdown helpers when possible; supplement with custom sanitizer for dynamic content.

## 6. Single-Responsibility Principle
- One function = one job.
- A function either fetches data, transforms data, persists data, or dispatches a message—never two.
- Services (`services/`) are stateless and receive dependencies via arguments.

## 7. Project Layout

```
├── bot/
│   ├── main.py               # aiogram Dispatcher + startup/shutdown
│   └── handlers/
│       └── ...               # FSM-based command handlers
├── db/
│   ├── models.py             # SQLAlchemy 2.0 models
│   └── session.py            # Async engine + sessionmaker
├── services/
│   ├── collect.py            # Async fetchers (aiohttp)
│   ├── synthesize.py         # Async LLM call
│   ├── deliver.py            # Async Telegram delivery (aiogram)
│   ├── sanitize.py           # MarkdownV2 strict sanitizer
│   ├── cache.py              # Redis wrapper
│   └── fsm.py                # FSM state definitions
├── settings.py               # Pydantic BaseSettings
├── .env                      # Secrets (not committed)
├── docker-compose.yml        # PostgreSQL + Redis
└── requirements.txt
```

## 8. Environment Variables
- `DATABASE_URL` — PostgreSQL connection string (asyncpg)
- `REDIS_URL` — Redis connection string
- `TELEGRAM_BOT_TOKEN` — Bot token
- `TELEGRAM_CHANNEL_ID` — Target channel (with `-100` prefix)
- `LLM_API_KEY`, `LLM_BASE_URL`, `MODEL_NAME` — LLM config

## 9. CI/CD
- GitHub Actions runs `python -m bot.main` on schedule.
- Ensure `DATABASE_URL` and `REDIS_URL` are injected as secrets.

## 10. Error Handling
- All async operations wrapped in try/except with exponential backoff where appropriate.
- Log structured errors; never leak tokens or secrets in logs.
