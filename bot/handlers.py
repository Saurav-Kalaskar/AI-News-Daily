"""
aiogram 3.x FSM-based command handlers.
"""
import logging

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from settings import Settings
from services.cache import Cache
from services.fetcher import collect
from services.synthesize import synthesize
from services.deliver import deliver
from services.cache import Cache

log = logging.getLogger(__name__)

# FSM states for /run command
class RunPipeline(StatesGroup):
    waiting_for_confirmation = State()


async def cmd_start(message: types.Message) -> None:
    """Handler for /start command."""
    await message.answer(
        "Welcome to AI News Daily! 🤖\n"
        "Commands:\n"
        "/run       - Run the news pipeline manually\n"
        "/status    - Check system status\n"
        "/lastbrief - Get the last brief\n"
        "/help      - Show help",
        parse_mode="MarkdownV2",
    )


async def cmd_help(message: types.Message) -> None:
    """Handler for /help command."""
    await message.answer(
        "*AI News Daily* 🤖\n\n"
        "*Commands:*\n"
        "`/run`       - Run the news pipeline manually\n"
        "`/status`    - Check system status\n"
        "`/lastbrief` - Get the last brief\n"
        "`/help`      - Show help",
        parse_mode="MarkdownV2",
    )


async def cmd_run(message: types.Message, state: FSMContext) -> None:
    """Handler for /run command."""
    await message.answer(
        "Are you sure you want to run the pipeline? (yes/no)",
        parse_mode="MarkdownV2",
    )
    await state.set_state(RunPipeline.waiting_for_confirmation)


async def cmd_run_confirm(callback_query: types.CallbackQuery, state: FSMContext, bot: Bot, settings: Settings) -> None:
    """Callback for pipeline confirmation."""
    await callback_query.answer()
    await state.clear()
    await callback_query.message.answer("Running pipeline...")

    # Use bot instance from DI to run pipeline
    try:
        stories = await collect(settings)
        if not stories:
            await callback_query.message.answer("No new stories found.")
            return
        brief = await synthesize(settings, stories)
        await deliver(settings, bot, brief, stories)
        await callback_query.message.answer("Pipeline completed successfully! ✅")
    except Exception as e:
        log.error(f"Pipeline failed: {e}")
        await callback_query.message.answer(f"Pipeline failed: {e}")


async def cmd_status(message: types.Message, cache: Cache) -> None:
    """Handler for /status command."""
    # Check Redis connection
    try:
        redis_keys = await cache.keys("ai_news:*")
        redis_status = "✅ Connected"
    except Exception as e:
        redis_status = f"❌ Error: {e}"
        redis_keys = []

    await message.answer(
        f"*System Status*\n\n"
        f"Redis: {redis_status}\n"
        f"Redis keys: {len(redis_keys)}\n",
        parse_mode="MarkdownV2",
    )


async def cmd_last_brief(message: types.Message) -> None:
    """Handler for /lastbrief command."""
    from pathlib import Path

    briefs_dir = Path("data/briefs")
    if not briefs_dir.exists() or not list(briefs_dir.iterdir()):
        await message.answer("No briefs found.")
        return

    last_brief = max(briefs_dir.iterdir(), key=lambda p: p.stat().st_mtime)
    content = last_brief.read_text()
    await message.answer(
        f"*Last Brief:* `{last_brief.name}`\n\n{content[:4000]}",
        parse_mode="MarkdownV2",
    )


def register_handlers(dp: Dispatcher) -> None:
    """Register all command handlers."""
    dp.message.register(cmd_start, Command("start"))
    dp.message.register(cmd_help, Command("help"))
    dp.message.register(cmd_run, Command("run"))
    dp.message.register(cmd_status, Command("status"))
    dp.message.register(cmd_last_brief, Command("lastbrief"))
