"""Callback query handlers for inline button responses."""
import logging

from aiogram import Bot, Dispatcher, Router
from aiogram.types import CallbackQuery

from services.sanitize import sanitize_markdown
from bot.dao.articles import ArticlesDAO
from bot.keyboards import back_to_main_keyboard

log = logging.getLogger(__name__)
dp = Router()


@dp.callback_query(lambda c: c.data and c.data.startswith("read_brief:"))
async def read_brief_callback(callback: CallbackQuery) -> None:
    brief_id = callback.data.split(":", 1)[1]
    dao = ArticlesDAO()
    article = await dao.get_article_by_id(int(brief_id))
    if not article:
        await callback.answer("Brief not found", show_alert=True)
        return
    lines = [
        f"*{article.title}*",
        f"Source: {article.source}",
        f"Category: {article.category or 'N/A'}",
        "",
    ]
    if article.summary:
        lines.append(article.summary)
    if article.url:
        lines.append(f"\nURL: {article.url}")
    await callback.message.answer(
        sanitize_markdown("\n".join(lines)),
        parse_mode="MarkdownV2",
        reply_markup=back_to_main_keyboard(),
    )
    await callback.answer()


@dp.callback_query(lambda c: c.data == "filter:open-source")
async def filter_open_source(callback: CallbackQuery) -> None:
    dao = ArticlesDAO()
    articles = await dao.get_by_category("open-source", limit=10)
    if not articles:
        await callback.answer("No open-source articles found", show_alert=True)
        return
    lines = ["*Open-Source Articles:*\n"]
    for a in articles:
        lines.append(f"*{a.title}*")
        lines.append(f"{a.source} | {a.created_at.strftime('%Y-%m-%d')}")
        if a.url:
            lines.append(f"URL: {a.url}")
        lines.append("")
    await callback.message.answer(
        sanitize_markdown("\n".join(lines)),
        parse_mode="MarkdownV2",
        reply_markup=back_to_main_keyboard(),
    )
    await callback.answer()


@dp.callback_query(lambda c: c.data == "search:archives")
async def search_archives(callback: CallbackQuery) -> None:
    text = "Use /search <keyword> to search the archives."
    await callback.message.answer(
        sanitize_markdown(text),
        parse_mode="MarkdownV2",
    )
    await callback.answer()


@dp.callback_query(lambda c: c.data and c.data.startswith("filter:"))
async def filter_category(callback: CallbackQuery) -> None:
    category = callback.data.split(":", 1)[1]
    dao = ArticlesDAO()
    articles = await dao.get_by_category(category, limit=10)
    if not articles:
        await callback.answer(f"No articles in '{category}'", show_alert=True)
        return
    lines = [f"*{category.title()} Articles:*\n"]
    for a in articles:
        lines.append(f"*{a.title}*")
        lines.append(f"{a.source} | {a.created_at.strftime('%Y-%m-%d')}")
        if a.url:
            lines.append(f"URL: {a.url}")
        lines.append("")
    await callback.message.answer(
        sanitize_markdown("\n".join(lines)),
        parse_mode="MarkdownV2",
        reply_markup=back_to_main_keyboard(),
    )
    await callback.answer()


@dp.callback_query(lambda c: c.data == "menu:back")
async def menu_back(callback: CallbackQuery) -> None:
    text = "Welcome to AI News Daily\n\nCommands:\n/search <query> - Search\n/lastbrief     - Recent\n/categories    - Categories\n/help          - Help"
    await callback.message.answer(
        sanitize_markdown(text),
        parse_mode="MarkdownV2",
    )
    await callback.answer()
