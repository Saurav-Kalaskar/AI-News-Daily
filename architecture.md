# AI News Daily Architecture

## Overview

AI News Daily is an automated 3‑stage pipeline that collects AI‑related news, synthesizes a concise briefing using a single LLM call, and delivers the result to a Telegram channel while archiving the brief locally.

## Pipeline Stages

```
+----------+      +------------+      +----------+
| Collect  | -->  | Synthesize | -->  | Deliver  |
+----------+      +------------+      +----------+
```

### Stage 1 – Collection (`collect.py`)

| Source                 | Method                               | Filter                     |
|-----------------------|--------------------------------------|----------------------------|
| Hacker News           | Firebase API (`topstories` + `item`) | Keyword allowlist (AI, LLM, etc.) |
| arXiv (cs.AI)         | Atom XML feed (`export.arxiv.org`)   | Category `cs.AI` (last 15) |
| MIT Technology Review| RSS feed (`technologyreview.com`)    | None                       |
| TechCrunch            | RSS feed (`techcrunch.com`)          | None                       |
| VentureBeat           | RSS feed (`venturebeat.com`)          | None                       |

**Deduplication:** Each story title is hashed (SHA‑256 of first 80 characters, first 16 hex chars). Hashes stored in `data/seen_stories.json`. Entries older than 7 days are pruned. Only stories with unseen hashes proceed to synthesis.

### Stage 2 – Synthesis (`synthesize.py`)

1. Load system prompt from `prompts/analyst.md`.
2. Build numbered user prompt listing each story with source, title, and URL.
3. Call NVIDIA LLM (`meta/llama-3.1-70b-instruct`) via OpenAI‑compatible client.
   - Temperature 0.3, max 1200 tokens.
   - Up to `MAX_RETRIES` (default 3) with exponential back‑off.
4. Receive markdown brief with sections:
   - `# TL;DR`
   - `## Key Releases`
   - `## Developer Takeaways`
   - `## Sources`

### Stage 3 – Delivery (`deliver.py`)

1. **Sanitization** – `sanitize_markdown()` escapes all characters that break Telegram `parse_mode=Markdown` (e.g., `*`, `_`, `` ` ``, unpaired brackets, and other MarkdownV2 special characters such as `(`, `)`, `~`, `>`, `#`, `+`, `-`, `=`, `|`, `{`, `}`, `.`).
2. **Telegram API** – POST to `https://api.telegram.org/bot<TELEGRAM_BOT_TOKEN>/sendMessage` with payload:
   ```json
   {
     "chat_id": <TELEGRAM_CHANNEL_ID>,
     "text": <sanitized brief>,
     "parse_mode": "Markdown"
   }
   ```
   Retries follow the same exponential back‑off strategy.
3. **Archiving** – Save the brief to `data/briefs/brief_<timestamp>.md` with YAML front‑matter containing `date`, `story_count`, and `source_count`.

## Settings (`settings.py`)

| Variable                | Source   | Description |
|-------------------------|----------|-------------|
| `LLM_API_KEY`           | `.env` / GitHub Secret | NVIDIA API key |
| `LLM_BASE_URL`          | `.env` (default) | NVIDIA endpoint |
| `MODEL_NAME`            | `.env` (default) | LLM model identifier |
| `TELEGRAM_BOT_TOKEN`   | `.env` / GitHub Secret | Bot authentication token |
| `TELEGRAM_CHANNEL_ID`  | `.env` / GitHub Secret | Target channel ID (must include `-100` prefix for channels) |
| `MAX_RETRIES`          | `.env` (default 3) | Retry count for LLM and Telegram calls |

## Data Flow

```
HN / arXiv / RSS → collect() → dedup (seen_stories.json) → stories list
  → synthesize() (LLM) → markdown brief
  → deliver() → Telegram API + archive (data/briefs/*.md)
```

## Deployment & Scheduling

- **Local execution:** `python main.py`
- **CI/CD:** GitHub Actions (`.github/workflows/daily_brief.yml`)
  - Cron schedule: `0 9,21 * * *` UTC (twice daily)
  - Manual trigger via `workflow_dispatch`
  - After each run:
    1. Commit updated `data/seen_stories.json`
    2. Commit new brief files in `data/briefs/`
    3. Push to repository

## Directory Layout

```
Ai-News-Daily/
├─ main.py               # Orchestrates pipeline stages
├─ collect.py            # Stage 1 – fetch & dedup
├─ synthesize.py         # Stage 2 – LLM call
├─ deliver.py            # Stage 3 – Telegram + archive
├─ settings.py           # Pydantic settings (reads .env)
├─ prompts/              # System prompt for LLM
│   └─ analyst.md
├─ data/                # Runtime data
│   ├─ seen_stories.json # Dedup state
│   └─ briefs/            # Archived briefs
├─ .env                  # Local secrets (not committed)
└─ .github/workflows/   # GitHub Actions configuration
    └─ daily_brief.yml
```

## Design Rationale

1. **Flat‑file dedup** – Simple JSON store avoids external DB overhead.
2. **Single LLM call** – Minimises token consumption and latency.
3. **Robust retries** – Exponential back‑off for network‑transient failures.
4. **Telegram MarkdownV2 sanitization** – Guarantees messages render correctly despite strict parser.
5. **Git‑backed state** – `seen_stories.json` and briefs persist across CI runs without extra storage.
