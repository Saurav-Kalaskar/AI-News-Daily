"""
AI News Daily - Stage 2: Synthesis (single LLM call).
"""
import logging
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from openai import OpenAI

from settings import Settings

log = logging.getLogger(__name__)

PROMPT_PATH = Path("prompts/analyst.md")


def _fix_llm_html(text: str) -> str:
    """Fix common LLM-generated HTML malformations before Telegram delivery."""
    # Convert <a href="URL">Title</a> → Title (URL)
    text = re.sub(r'<a href="([^"]+)">([^<]+)</a>', r'\2 (\1)', text)
    # Remove broken/unclosed <a> tags
    text = re.sub(r'<a[^>]*>', '[', text)
    text = re.sub(r'</a>', ']', text)
    # Escape bare & not already HTML entities
    text = re.sub(r'&(?![a-zA-Z]{2,6};|#[0-9]+;)', '&', text)
    return text


def load_system_prompt() -> str:
    return PROMPT_PATH.read_text()


def build_user_prompt(stories: list[dict[str, Any]]) -> str:
    """Format stories into a plain-text digest for the LLM."""
    lines = []
    for i, s in enumerate(stories, 1):
        lines.append(f"[{i}] {s['source']}: {s['title']}\n  URL: {s['url']}")
    return "\n\n".join(lines)


def synthesize(settings: Settings, stories: list[dict[str, Any]]) -> str:
    """
    Stage 2: Send aggregated news to LLM, return markdown briefing.
    Retries up to MAX_RETRIES on transient failures.
    """
    if not stories:
        raise ValueError("No stories to synthesize")

    log.info(f"Synthesizing {len(stories)} stories via LLM...")

    client = OpenAI(
        base_url=settings.LLM_BASE_URL,
        api_key=settings.LLM_API_KEY,
    )

    system_prompt = load_system_prompt()
    user_prompt = build_user_prompt(stories)
    utc_now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    for attempt in range(1, settings.MAX_RETRIES + 1):
        try:
            response = client.chat.completions.create(
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
            return _fix_llm_html(brief)
        except Exception as e:
            log.warning(f"  → LLM attempt {attempt}/{settings.MAX_RETRIES} failed: {e}")
            if attempt < settings.MAX_RETRIES:
                time.sleep(2 ** attempt)
            else:
                raise RuntimeError(f"All {settings.MAX_RETRIES} LLM attempts failed") from e