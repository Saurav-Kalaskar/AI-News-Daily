"""
aiogram 3.x bot entry point.
Starts polling and sets up scheduled pipeline runs.
"""
import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import RedisStorage
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from settings import Settings
from bot.handlers.commands import dp as commands_router
from bot.handlers.callbacks import dp as callbacks_router
from bot.keyboards import digest_keyboard
from services.cache import Cache
from services.fetcher import collect
from services.synthesize import synthesize
from services.deliver import deliver

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)


def create_bot(settings: Settings) -> Bot:
    return Bot(token=settings.TELEGRAM_BOT_TOKEN)


def create_dispatcher(storage: RedisStorage) -> Dispatcher:
    dp = Dispatcher(storage=storage)
    return dp


async def run_pipeline(settings: Settings, bot: Bot) -> None:
    """Full pipeline: collect -> synthesize -> deliver."""
    try:
        log.info("=" * 50)
        log.info("AI News Daily starting")
        log.info("=" * 50)

        # Stage 1: Collection
        log.info("--- Stage 1: Collection ---")
        stories = await collect(settings)
        log.info(f"  -> Collected {len(stories)} new stories")

        if not stories:
            log.warning("  -> No new stories. Exiting.")
            return

        # Stage 2: Synthesis
        log.info("--- Stage 2: Synthesis ---")
        brief = await synthesize(settings, stories)

        # Stage 3: Delivery with inline keyboard
        log.info("--- Stage 3: Delivery ---")
        brief_id = str(int(__import__("time").time()))
        keyboard = digest_keyboard(brief_id)
        await deliver(settings, bot, brief, stories, keyboard)

        log.info("AI News Daily done.")
    except Exception as e:
        log.error(f"Pipeline failed: {e}")
        raise


async def main() -> None:
    settings = Settings()
    bot = create_bot(settings)
    storage = RedisStorage.from_url(settings.REDIS_URL)
    dp = create_dispatcher(storage)

    cache = Cache(redis_url=settings.REDIS_URL)
    await cache.connect()
    await bot.delete_webhook(drop_pending_updates=True)

    dp.include_routers(commands_router, callbacks_router)

    if "--run-once" in sys.argv:
        await run_pipeline(settings, bot)
        return

    scheduler = AsyncIOScheduler()
    scheduler.add_job(run_pipeline, "cron", hour="9,21", minute="0", args=(settings, bot))
    scheduler.start()

    try:
        log.info("  -> Starting aiogram polling...")
        await dp.start_polling(bot)
    finally:
        scheduler.shutdown()
        await storage.close()
        await cache.disconnect()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
