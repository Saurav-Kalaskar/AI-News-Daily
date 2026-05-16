"""Inline keyboard factories for AI News Daily bot."""
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def digest_keyboard(brief_id: str) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Read Full Brief", callback_data=f"read_brief:{brief_id}"),
            InlineKeyboardButton(text="Filter: Open-Source", callback_data="filter:open-source"),
        ],
        [
            InlineKeyboardButton(text="Search Archives", callback_data="search:archives"),
        ],
    ])
    return keyboard


def back_to_main_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Back to Main Menu", callback_data="menu:back")],
    ])