from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup

from .texts import MONTH_NAMES


def start_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📅 Рассчитать за месяц")],
            [KeyboardButton(text="✏️ Изменить оклад")],
            [KeyboardButton(text="❓ Как это считается")],
        ],
        resize_keyboard=True,
        input_field_placeholder="Выбери действие",
    )


def year_keyboard(year: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="◀️", callback_data="year_prev"),
                InlineKeyboardButton(text=str(year), callback_data=f"year:{year}"),
                InlineKeyboardButton(text="▶️", callback_data="year_next"),
            ],
            [InlineKeyboardButton(text="⌨️ Ввести год", callback_data="year_manual")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back")],
        ]
    )


def month_keyboard() -> InlineKeyboardMarkup:
    rows = []
    row = []
    for idx, name in enumerate(MONTH_NAMES, start=1):
        row.append(InlineKeyboardButton(text=name, callback_data=f"month:{idx:02d}"))
        if len(row) == 4:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    return InlineKeyboardMarkup(inline_keyboard=rows)


def result_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📅 Другой месяц")],
            [KeyboardButton(text="✏️ Изменить оклад")],
            [KeyboardButton(text="📋 Детали по дням")],
        ],
        resize_keyboard=True,
    )


def api_error_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔁 Повторить", callback_data="api:retry")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="api:back")],
        ]
    )
