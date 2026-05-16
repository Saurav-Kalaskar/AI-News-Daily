"""
Async Telegram delivery and archiving service.
Sends digest with inline keyboard, saves articles to PostgreSQL.
"""
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup
from aiogram.enums import ParseMode

from settings import Settings
from bot.dao.articles import ArticlesDAO

log = logging.getLogger(__name__)

BRIEFS_DIR = Path("data/briefs")


async def send_telegram(
    settings: Settings,
    bot: Bot,
    brief: str,
    keyboard: InlineKeyboardMarkup | None = None,
) -> bool:
    """Send HTML brief to Telegram channel with optional inline keyboard."""
    log.info("Sending brief to Telegram...")
    for attempt in range(1, settings.MAX_RETRIES + 1):
        try:
            await bot.send_message(
                chat_id=settings.TELEGRAM_CHANNEL_ID,
                text=brief,
                parse_mode=ParseMode.HTML,
                reply_markup=keyboard,
            )
            log.info("  → Telegram delivery successful")
            return True
        except Exception as e:
            log.warning(f"  → Telegram attempt {attempt}/{settings.MAX_RETRIES} failed: {e}")
            if attempt < settings.MAX_RETRIES:
                import asyncio
                await asyncio.sleep(2 ** attempt)
            else:
                log.error("  → Telegram delivery failed after all retries")
                return False


async def save_articles_to_db(stories: list[dict[str, Any]]) -> None:
    """Persist stories to PostgreSQL via ArticlesDAO."""
    dao = ArticlesDAO()
    try:
        await dao.save_many(stories)
    except Exception as e:
        log.warning(f"  → DB save failed (non-fatal): {e}")


async def archive_brief(brief: str, stories: list[dict[str, Any]]) -> Path:
    """Save brief to data/briefs/brief_{timestamp}.md with YAML frontmatter."""
    BRIEFS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H-%M-%S")
    frontmatter = {
        "date": datetime.utcnow().isoformat(),
        "story_count": len(stories),
        "source_count": len({s["source"] for s in stories}),
    }
    content = "---\n" + str(frontmatter) + "\n---\n\n" + brief
    path = BRIEFS_DIR / f"brief_{timestamp}.md"
    path.write_text(content)
    log.info(f"  → Archived to {path}")
    return path


async def deliver(
    settings: Settings,
    bot: Bot,
    brief: str,
    stories: list[dict[str, Any]],
    keyboard: InlineKeyboardMarkup | None = None,
) -> None:
    """Stage 3: Save to DB, send to Telegram, and archive locally."""
    await save_articles_to_db(stories)
    await send_telegram(settings, bot, brief, keyboard)
    await archive_brief(brief, stories)
