"""
Async LLM synthesis service.
Single call with exponential back-off.
"""
import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from openai import AsyncOpenAI

from settings import Settings

log = logging.getLogger(__name__)

PROMPT_PATH = Path("prompts/analyst.md")


def _load_system_prompt() -> str:
    return PROMPT_PATH.read_text()


def _build_user_prompt(stories: list[dict[str, Any]]) -> str:
    lines = []
    for i, s in enumerate(stories, 1):
        lines.append(f"[{i}] {s['source']}: {s['title']}\n  URL: {s['url']}")
    return "\n\n".join(lines)


async def synthesize(settings: Settings, stories: list[dict[str, Any]]) -> str:
    """Send aggregated news to LLM, return markdown briefing."""
    if not stories:
        raise ValueError("No stories to synthesize")

    log.info(f"Synthesizing {len(stories)} stories via LLM...")

    client = AsyncOpenAI(
        base_url=settings.LLM_BASE_URL,
        api_key=settings.LLM_API_KEY,
    )

    system_prompt = _load_system_prompt()
    user_prompt = _build_user_prompt(stories)
    utc_now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    for attempt in range(1, settings.MAX_RETRIES + 1):
        try:
            response = await client.chat.completions.create(
                model=settings.MODEL_NAME,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Aggregated AI news (brief generated {utc_now}):\n\n{user_prompt}"},
                ],
                temperature=0.3,
                max_tokens=2000,
            )
            brief = response.choices[0].message.content
            log.info(f"  → LLM response received ({len(brief)} chars)")
            return brief
        except Exception as e:
            log.warning(f"  → LLM attempt {attempt}/{settings.MAX_RETRIES} failed: {e}")
            if attempt < settings.MAX_RETRIES:
                await asyncio.sleep(2 ** attempt)
            else:
                raise RuntimeError(f"All {settings.MAX_RETRIES} LLM attempts failed") from e
