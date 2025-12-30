from __future__ import annotations

import logging
from datetime import datetime
from decimal import Decimal

from aiogram import BaseMiddleware, F, Router
from aiogram.filters import StateFilter
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

from .keyboards import (
    api_error_keyboard,
    month_keyboard,
    result_keyboard,
    start_menu_keyboard,
    year_keyboard,
)
from .services.calendar import CalendarError, CalendarService
from .services.payroll import build_payroll, format_money, parse_salary, short_days_line
from .states import PayrollStates
from .storage.db import get_salary, set_salary
from .texts import (
    API_ERROR,
    HELP_TEXT,
    MONTH_SELECT,
    MONTH_NAMES,
    SALARY_ERROR,
    SALARY_PROMPT,
    SALARY_SAVED,
    START_NO_SALARY,
    START_WITH_SALARY,
    YEAR_ERROR,
    YEAR_MANUAL_PROMPT,
    YEAR_SELECT,
)

LOGGER = logging.getLogger(__name__)

router = Router()


class EventLoggingMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        state = data.get("state")
        state_name = await state.get_state() if state else None
        if isinstance(event, Message):
            LOGGER.info(
                "Event message state=%s text=%r user_id=%s",
                state_name,
                event.text,
                event.from_user.id if event.from_user else None,
            )
        elif isinstance(event, CallbackQuery):
            LOGGER.info(
                "Event callback state=%s data=%r user_id=%s",
                state_name,
                event.data,
                event.from_user.id if event.from_user else None,
            )
        return await handler(event, data)


router.message.middleware(EventLoggingMiddleware())
router.callback_query.middleware(EventLoggingMiddleware())


def salary_format(value: int) -> str:
    return format_money(Decimal(value))


async def show_main_menu(message: Message) -> None:
    salary = await get_salary(message.from_user.id)
    if salary is None:
        await message.answer(START_NO_SALARY, parse_mode="Markdown")
    else:
        await message.answer(
            START_WITH_SALARY.format(salary_fmt=salary_format(salary)),
            reply_markup=start_menu_keyboard(),
            parse_mode="Markdown",
        )


async def show_year_select(message: Message, state: FSMContext, year: int | None = None) -> None:
    year = year or datetime.now().year
    await state.set_state(PayrollStates.year)
    await state.update_data(year_view=year)
    await message.answer(YEAR_SELECT, reply_markup=year_keyboard(year))


async def show_month_select(message: Message, state: FSMContext) -> None:
    await state.set_state(PayrollStates.month)
    await message.answer(MONTH_SELECT, reply_markup=month_keyboard())


@router.message(F.text == "/start")
async def start_command(message: Message, state: FSMContext) -> None:
    await state.clear()
    salary = await get_salary(message.from_user.id)
    if salary is None:
        await state.set_state(PayrollStates.salary)
        await message.answer(START_NO_SALARY, parse_mode="Markdown")
        return
    await message.answer(
        START_WITH_SALARY.format(salary_fmt=salary_format(salary)),
        reply_markup=start_menu_keyboard(),
        parse_mode="Markdown",
    )


@router.message(F.text == "/help")
async def help_command(message: Message) -> None:
    await message.answer(HELP_TEXT, parse_mode="Markdown")


@router.message(F.text == "❓ Как это считается")
async def help_button(message: Message) -> None:
    await message.answer(HELP_TEXT, parse_mode="Markdown")


@router.message(F.text == "📅 Рассчитать за месяц")
async def menu_calculate(message: Message, state: FSMContext) -> None:
    await show_year_select(message, state)


@router.message(F.text == "✏️ Изменить оклад")
async def menu_change_salary(message: Message, state: FSMContext) -> None:
    await state.set_state(PayrollStates.salary)
    await message.answer(SALARY_PROMPT, parse_mode="Markdown")


@router.message(F.text == "📅 Другой месяц")
async def menu_other_month(message: Message, state: FSMContext) -> None:
    await show_year_select(message, state)


@router.message(StateFilter(PayrollStates.result), F.text == "📋 Детали по дням")
async def menu_details(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    details = data.get("last_details")
    if not details:
        await message.answer("Сначала рассчитай месяц.")
        return
    await send_details(message, data)


@router.message(StateFilter(PayrollStates.salary))
async def salary_input(message: Message, state: FSMContext) -> None:
    parsed = parse_salary(message.text or "")
    if not parsed:
        await message.answer(SALARY_ERROR, parse_mode="Markdown")
        return
    await set_salary(message.from_user.id, parsed)
    await message.answer(
        SALARY_SAVED.format(salary_fmt=salary_format(parsed)),
        parse_mode="Markdown",
    )
    await show_year_select(message, state)


@router.callback_query(StateFilter(PayrollStates.year), F.data.startswith("year:") | F.data.in_({"year_prev", "year_next", "year_manual", "back"}))
async def year_callbacks(callback: CallbackQuery, state: FSMContext) -> None:
    data_value = callback.data
    data = await state.get_data()
    year_view = int(data.get("year_view", datetime.now().year))

    if data_value == "year_prev":
        year_view -= 1
        await state.update_data(year_view=year_view)
        await callback.message.edit_text(YEAR_SELECT, reply_markup=year_keyboard(year_view))
    elif data_value == "year_next":
        year_view += 1
        await state.update_data(year_view=year_view)
        await callback.message.edit_text(YEAR_SELECT, reply_markup=year_keyboard(year_view))
    elif data_value.startswith("year:"):
        year = int(data_value.split(":", maxsplit=1)[1])
        await state.update_data(year=year)
        await callback.message.edit_text(YEAR_SELECT)
        await show_month_select(callback.message, state)
    elif data_value == "year_manual":
        await state.set_state(PayrollStates.year_manual)
        await callback.message.answer(YEAR_MANUAL_PROMPT, parse_mode="Markdown")
    elif data_value == "back":
        await state.clear()
        await show_main_menu(callback.message)
    await callback.answer()


@router.message(StateFilter(PayrollStates.year_manual))
async def year_manual_input(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()
    if not text.isdigit():
        await message.answer(YEAR_ERROR, parse_mode="Markdown")
        return
    year = int(text)
    if year < 2000 or year > 2100:
        await message.answer(YEAR_ERROR, parse_mode="Markdown")
        return
    await state.update_data(year=year)
    await show_month_select(message, state)


@router.callback_query(StateFilter(PayrollStates.month), F.data.startswith("month:"))
async def month_selected(
    callback: CallbackQuery,
    state: FSMContext,
    calendar: CalendarService,
) -> None:
    month = int(callback.data.split(":", maxsplit=1)[1])
    data = await state.get_data()
    year = data.get("year")
    if not year:
        await show_year_select(callback.message, state)
        await callback.answer()
        return
    await calculate_and_show(
        callback.message,
        state,
        calendar,
        user_id=callback.from_user.id,
        year=year,
        month=month,
    )
    await callback.answer()


@router.callback_query(StateFilter(PayrollStates.month), F.data == "api:retry")
async def api_retry(
    callback: CallbackQuery,
    state: FSMContext,
    calendar: CalendarService,
) -> None:
    data = await state.get_data()
    year = data.get("pending_year")
    month = data.get("pending_month")
    if year and month:
        await calculate_and_show(
            callback.message,
            state,
            calendar,
            user_id=callback.from_user.id,
            year=year,
            month=month,
        )
    await callback.answer()


@router.callback_query(StateFilter(PayrollStates.month), F.data == "api:back")
async def api_back(callback: CallbackQuery, state: FSMContext) -> None:
    await show_month_select(callback.message, state)
    await callback.answer()


async def calculate_and_show(
    message: Message,
    state: FSMContext,
    calendar: CalendarService,
    *,
    user_id: int,
    year: int,
    month: int,
) -> None:
    # callback.message.from_user is the bot; always use the triggering user's id.
    salary = await get_salary(user_id)
    if salary is None:
        await state.set_state(PayrollStates.salary)
        await message.answer(START_NO_SALARY, parse_mode="Markdown")
        return
    try:
        calendar_raw = await calendar.get_month(year, month)
    except CalendarError:
        await state.update_data(pending_year=year, pending_month=month)
        await message.answer(API_ERROR, reply_markup=api_error_keyboard())
        return

    payroll = build_payroll(year, month, salary, calendar_raw)
    await state.update_data(
        last_year=year,
        last_month=month,
        last_details=[detail.__dict__ for detail in payroll.details],
        hours_total=payroll.hours_total,
        hours_1_15=payroll.hours_1_15,
        hours_16_end=payroll.hours_16_end,
    )
    await state.set_state(PayrollStates.result)

    result_text = (
        f"**{payroll.month_name} {year}**\n"
        f"Оклад: **{salary_format(salary)} ₽**\n\n"
        f"Норма рабочих часов: **{payroll.hours_total} ч**\n"
        f"• 1–15: **{payroll.hours_1_15} ч**\n"
        f"• 16–{payroll.last_day}: **{payroll.hours_16_end} ч**\n\n"
        f"**Аванс (1–15): {format_money(payroll.advance)} ₽**\n"
        f"**Вторая часть: {format_money(payroll.salary2)} ₽**\n\n"
        f"{short_days_line(payroll.short_days_count)}"
    )

    await message.answer(result_text, reply_markup=result_keyboard(), parse_mode="Markdown")


async def send_details(message: Message, data: dict) -> None:
    month = data.get("last_month")
    year = data.get("last_year")
    details = data.get("last_details", [])
    if not month or not year or not details:
        await message.answer("Сначала рассчитай месяц.")
        return

    header = f"**Детали за {month_name(month)} {year}:**"
    lines = [
        f"{detail['day']:02d} {detail['weekday_short']} — {detail['day_type']} — {detail['hours']}ч"
        for detail in details
    ]
    summary = (
        f"Итого: **{data.get('hours_total', 0)} ч** (1–15: {data.get('hours_1_15', 0)} ч, "
        f"16–конец: {data.get('hours_16_end', 0)} ч)"
    )

    chunk_size = 35
    for idx in range(0, len(lines), chunk_size):
        chunk = lines[idx : idx + chunk_size]
        if idx == 0:
            text = "\n".join([header, *chunk])
        else:
            text = "\n".join(chunk)
        await message.answer(text, parse_mode="Markdown")
    await message.answer(summary, parse_mode="Markdown")


def month_name(month: int) -> str:
    return MONTH_NAMES[month - 1]


@router.message(StateFilter(None))
async def fallback_start(message: Message) -> None:
    await message.answer("Нажми /start, чтобы начать.")
