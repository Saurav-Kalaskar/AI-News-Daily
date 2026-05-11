"""
AI News Daily - Stage 3: Delivery (Telegram + archiving).
"""
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
    Strip unauthorized characters for Telegram parse_mode=Markdown.
    Only allow: * _ ` [ ] ( ) ~ ` > # + - = | { } . !
    Also escape brackets that contain | to avoid table parse errors.
    """
    # Remove any char not in allowed set
    cleaned = "".join(c if c in ALLOWED_CHARS else " " for c in text)
    # Collapse multiple spaces
    cleaned = re.sub(r" {2,}", " ", cleaned)
    # Escape | inside brackets (Telegram treats | as table delimiter in some contexts)
    cleaned = re.sub(r"\[([^\]]*\|[^\]]*)\]", lambda m: m.group(0).replace("|", "\\|"), cleaned)
    return cleaned.strip()


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
    """
    Save brief to data/briefs/brief_{timestamp}.md with YAML frontmatter.
    """
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