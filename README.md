# AI News Daily

Automated daily briefing service. Collects AI news, synthesizes via LLM, delivers to Telegram.

## Architecture

```
Collect (async) → Synthesize (LLM) → Deliver (Telegram + Archive)
```

Uses aiogram 3.x, SQLAlchemy 2.0 (async PostgreSQL), Redis for FSM/cache, strict MarkdownV2 sanitization.

## Prerequisites

- Python 3.10+
- Docker + Docker Compose
- Telegram bot token + channel ID
- NVIDIA API key

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Start PostgreSQL + Redis
docker compose up -d

# 3. Run migrations
alembic upgrade head

# 4. Copy and fill .env
cp .env.example .env
# Edit .env with your credentials

# 5. Run the bot (long-poll + scheduler)
python -m bot.main

# Or run pipeline once (CI use)
python -m bot.main --run-once
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_API_KEY` | (required) | NVIDIA API key |
| `LLM_BASE_URL` | NVIDIA integrate API | LLM endpoint |
| `MODEL_NAME` | `meta/llama-3.1-70b-instruct` | LLM model |
| `TELEGRAM_BOT_TOKEN` | (required) | Bot token from @BotFather |
| `TELEGRAM_CHANNEL_ID` | (required) | Channel ID (use `-100…` for channels) |
| `DATABASE_URL` | PostgreSQL async URL | Database connection |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection |
| `MAX_RETRIES` | `3` | Retry count |

## Project Layout

```
├── bot/                  # aiogram 3.x entry point + handlers
│   ├── main.py
│   └── handlers.py
├── services/             # Async services (single-responsibility)
│   ├── fetcher.py        # aiohttp fetchers
│   ├── synthesize.py     # LLM call
│   ├── deliver.py        # Telegram delivery
│   ├── sanitize.py       # MarkdownV2 strict sanitizer
│   └── cache.py          # Redis wrapper
├── db/                   # SQLAlchemy 2.0 async
│   ├── models.py
│   └── session.py
├── lib/                  # TypeScript utilities
│   ├── types.ts
│   ├── config.ts
│   └── engine.ts
├── alembic/              # DB migrations
├── docker-compose.yml    # PostgreSQL + Redis
├── CLAUDE.md             # Architectural conventions
└── requirements.txt
```

## Deploy via GitHub Actions

Schedule: `0 9,21 * * *` UTC (twice daily). Add secrets: `LLM_API_KEY`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHANNEL_ID`.

## Output Format

Brief in 4 sections: `# TL;DR`, `## Key Releases`, `## Developer Takeaways`, `## Sources`.