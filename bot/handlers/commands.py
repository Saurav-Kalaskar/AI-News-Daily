"""AI News Daily bot command handlers router."""
import logging

from aiogram import Bot, Dispatcher, Router
from aiogram.filters import Command
from aiogram.types import Message

from services.sanitize import sanitize_markdown
from bot.dao.articles import ArticlesDAO

log = logging.getLogger(__name__)
dp = Router()


@dp.message(Command("start"))
async def cmd_start(message: Message) -> None:
    text = (
        "Welcome to AI News Daily\n\n"
        "Commands:\n"
        "/search <query> - Search past articles\n"
        "/lastbrief     - View recent articles\n"
        "/categories    - Browse by category\n"
        "/help          - Show help"
    )
    await message.answer(sanitize_markdown(text), parse_mode="MarkdownV2")


@dp.message(Command("help"))
async def cmd_help(message: Message) -> None:
    text = "AI News Daily Help\n\n/search <query> - Search articles\n/lastbrief     - Recent articles\n/categories    - List categories\n/help          - This message"
    await message.answer(sanitize_markdown(text), parse_mode="MarkdownV2")


@dp.message(Command("lastbrief"))
async def cmd_lastbrief(message: Message) -> None:
    dao = ArticlesDAO()
    articles = await dao.get_recent(limit=5)
    if not articles:
        await message.answer("No articles found.")
        return
    lines = ["Recent Articles:\n"]
    for a in articles:
        cat = f"[{a.category}]" if a.category else ""
        lines.append(f"{cat} {a.title}\n{a.source} | {a.created_at.strftime('%Y-%m-%d')}")
        if a.url:
            lines.append(f"URL: {a.url}")
        lines.append("")
    await message.answer(sanitize_markdown("\n".join(lines)), parse_mode="MarkdownV2")


@dp.message(Command("categories"))
async def cmd_categories(message: Message) -> None:
    dao = ArticlesDAO()
    cats = await dao.get_all_categories()
    if not cats:
        await message.answer("No categories found.")
        return
    text = "Categories:\n" + "\n".join(f"  - {c}" for c in cats)
    await message.answer(sanitize_markdown(text), parse_mode="MarkdownV2")


@dp.message(Command("search"))
async def cmd_search(message: Message) -> None:
    query = message.text.replace("/search", "").strip()
    if not query:
        await message.answer("Usage: /search <keyword>")
        return
    dao = ArticlesDAO()
    articles = await dao.search_articles(query, limit=10)
    if not articles:
        await message.answer(f"No results for '{query}'")
        return
    lines = [f"Search results for '{query}':\n"]
    for a in articles:
        lines.append(f"{a.title}\n{a.source} | {a.category or 'uncategorized'}")
        if a.url:
            lines.append(f"URL: {a.url}")
        lines.append("")
    await message.answer(sanitize_markdown("\n".join(lines)), parse_mode="MarkdownV2")
