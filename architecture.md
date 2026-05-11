# Architecture

## 3-Stage Pipeline

```
Collection (RSS/API) → Synthesis (LLM) → Delivery (Telegram + Archive)
```

### Stage 1: Collection
Pure functions, no LLM involved.

| Source | Method | Filter |
|--------|--------|--------|
| Hacker News | Firebase API (`hacker-news.firebaseio.com`) | Keyword allowlist |
| arXiv cs.AI | Atom XML feed | Category = cs.AI |
| MIT Tech Review | RSS | None |
| TechCrunch | RSS | None |
| VentureBeat | RSS | None |

**Deduplication**: SHA256 hash of first 80 chars of title → stored in `data/seen_stories.json`. Entries older than 7 days pruned.

### Stage 2: Synthesis
Single instruction-following LLM (meta/llama-3.1-70b-instruct). One completion call. Temperature 0.3, max 1200 tokens.

**Why one model**: KISS. Multi-agent systems add overhead, latency, cost. A well-prompted single model handles summarization and structuring effectively.

System prompt stored in `prompts/analyst.md`, read at runtime.

### Stage 3: Delivery
- **Telegram**: `parse_mode: Markdown` - strict. Sanitization function strips all unauthorized characters.
- **Archive**: Brief saved to `data/briefs/brief_{timestamp}.md` with YAML frontmatter.

## Data Flow
```
data/seen_stories.json  ← dedup across runs
data/briefs/            ← permanent archive
prompts/analyst.md      ← system prompt
```

## GitHub Actions State
After each run, `seen_stories.json` and new `briefs/` files are committed back. This maintains dedup state across workflow runs.

## Why no database?
Flat file (`seen_stories.json`) sufficient for dedup. No operational overhead.

## Why no LangChain?
Overkill. Standard `openai` SDK sufficient for single completion call.