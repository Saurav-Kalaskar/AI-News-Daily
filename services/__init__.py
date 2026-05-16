"""AI News Daily - Stage 3: Delivery (Telegram + archiving)."""
import logging
import re
import time
from datetime import datetime
from pathlib import Path

import requests
import yaml

from settings import Settings

log = logging.getLogger(__name__)

TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"
BRIEFS_DIR = Path("data/briefs")
ALLOWED_CHARS = set("*_`[]()~`>#+-=|{}.!")


def sanitize_markdown(text: str) -> str:
    """
    Escape special chars that break Telegram parse_mode=Markdown.
    Keep all normal letters, numbers, newlines."""
    # Escape unpaired special chars
    text = re.sub(r'(?<!\*)\*(?!\*)', r'\\*', text)
    text = re.sub(r'(?<!_)_(?!_)', r'\\_', text)
    text = re.sub(r'(?<!`)`(?!`)', r'\\`', text)
    # Escape [ and ] when not part of a markdown link [text](url)
    text = re.sub(r'\[(?![^\]]+\])', r'\\[', text)
    text = re.sub(r'(?<!\])\]', r'\\]', text)
    # Escape other Telegram MarkdownV2 special chars
    for ch in ('(', ')', '~', '>', '#', '+', '-', '=', '|', '{', '}'):
        text = text.replace(ch, f'\\{ch}')
    return text


def send_telegram(settings: Settings, brief: str) -> bool:
    """Send markdown brief to Telegram channel. Returns True on success."""
    log.info("Sending brief to Telegram...")
    sanitized = sanitize_markdown(brief)
    payload = {
        "chat_id": settings.TELEGRAM_CHANNEL_ID,
        "text": sanitized,
        "parse_mode": "Markdown",
    }
    url = TELEGRAM_API.format(token=settings.TELEGRAM_BOT_TOKEN)
    for attempt in range(1, settings.MAX_RETRIES + 1):
        try:
            resp = requests.post(url, json=payload, timeout=30)
            data = resp.json()
            if data.get("ok"):
                log.info("  → Telegram delivery successful")
                return True
            log.warning(f"  → Telegram API error: {data.get('description')}")
            return False
        except Exception as e:
            log.warning(f"  → Telegram attempt {attempt}/{settings.MAX_RETRIES} failed: {e}")
            if attempt < settings.MAX_RETRIES:
                time.sleep(2 ** attempt)
    log.error("  → Telegram delivery failed after all retries")
    return False


def archive_brief(brief: str, stories: list[dict]) -> Path:
    """Save brief to data/briefs/brief_{timestamp}.md with YAML frontmatter."""
    BRIEFS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H-%M-%S")
    frontmatter = {
        "date": datetime.utcnow().isoformat(),
        "story_count": len(stories),
        "source_count": len({s["source"] for s in stories}),
    }
    content = "---\n" + yaml.dump(frontmatter) + "---\n\n" + brief
    path = BRIEFS_DIR / f"brief_{timestamp}.md"
    path.write_text(content)
    log.info(f"  → Archived to {path}")
    return path


def deliver(settings: Settings, brief: str, stories: list[dict]) -> None:
    """Stage 3: Send to Telegram and archive locally."""
    send_telegram(settings, brief)
    archive_brief(brief, stories)
