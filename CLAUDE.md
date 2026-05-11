# CLAUDE.md This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Automated AI news briefing bot. 3-stage pipeline: collect → synthesize → deliver. Runs as single Python process, deployed via GitHub Actions cron.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run full pipeline locally
python main.py

# Trigger GitHub Actions workflow manually
# Actions tab → "Daily AI News Brief" → Run workflow
```

No test suite, linter, or Makefile exists.

## Architecture

**Pipeline:** `main.py` orchestrates three stages sequentially.

| Stage | File | Responsibility |
|-------|------|----------------|
| 1. Collect | `collect.py` | Fetch HN (Firebase API), arXiv, RSS feeds. Keyword-filter HN. Deduplicate via SHA-256 title hashes in `data/seen_stories.json`. Prune entries >7 days. |
| 2. Synthesize | `synthesize.py` | Load system prompt from `prompts/analyst.md`. Build user prompt from stories. Call NVIDIA LLM via `openai` client (custom `base_url`). Exponential backoff retry. |
| 3. Deliver | `deliver.py` | Sanitize markdown for Telegram (whitelist chars, escape brackets). Send via Bot API. Archive brief to `data/briefs/brief_<timestamp>.md` with YAML front-matter. |

**Config:** `settings.py` — pydantic-settings `BaseSettings` reads `.env`. All modules import `Settings`.

**Data flow:**
```
HN/arXiv/RSS → collect() → dedup (seen_stories.json) → stories list
  → synthesize() via LLM (system + user prompt) → markdown brief
  → deliver() → Telegram API + archive (data/briefs/*.md)
```

## Key Patterns

- **Dedup:** SHA-256 of title prefix → stored in `data/seen_stories.json`. 7-day TTL auto-prune.
- **Retry:** Exponential backoff (`2^attempt` seconds) on LLM and Telegram calls.
- **Telegram sanitization:** `sanitize_markdown` strips unsupported chars, escapes brackets. Telegram `parse_mode=Markdown` is strict.
- **State persistence:** GitHub Actions commits `seen_stories.json` + new briefs back to repo. No external DB.
- **Pydantic Settings:** All config via `.env` + `Settings` class. Secrets: `LLM_API_KEY`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHANNEL_ID`. Optional: `LLM_BASE_URL`, `MODEL_NAME`, `MAX_RETRIES`.

## Deployment

GitHub Actions workflow (`.github/workflows/daily_brief.yml`):
- Cron: `0 9,21 * * *` UTC (twice daily) + manual `workflow_dispatch`
- Runs on `ubuntu-latest`, Python 3.12
- Injects secrets as env vars
- Commits state changes (seen_stories + briefs) back to repo

## LLM Integration

Uses NVIDIA-hosted LLM (`meta/llama-3.1-70b-instruct` by default) via OpenAI-compatible client. `synthesize.py` sets `base_url` to NVIDIA's integrate API. Single completion call per run.

## Requirements

- Python 3.10+
- `pydantic-settings>=2.0.0`, `openai>=1.0.0`, `requests>=2.31.0`, `pyyaml>=6.0`
