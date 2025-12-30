from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from ..texts import MONTH_NAMES, WEEKDAY_SHORT

SALARY_RE = re.compile(r"^(?P<num>[\d\s]+)(?P<k>[kк])?$", re.IGNORECASE)


@dataclass
class DayInfo:
    day: int
    weekday_short: str
    day_type: str
    hours: int


@dataclass
class PayrollResult:
    year: int
    month: int
    month_name: str
    last_day: int
    hours_total: int
    hours_1_15: int
    hours_16_end: int
    advance: Decimal
    salary2: Decimal
    short_days_count: int
    details: list[DayInfo]


def parse_salary(text: str) -> int | None:
    cleaned = text.strip().replace("\xa0", " ")
    match = SALARY_RE.match(cleaned)
    if not match:
        return None
    num = match.group("num").replace(" ", "")
    if not num.isdigit():
        return None
    value = int(num)
    if value <= 0:
        return None
    if match.group("k"):
        value *= 1000
    return value


def format_money(value: Decimal) -> str:
    quantized = value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    formatted = f"{quantized:,.2f}".replace(",", " ")
    return formatted


def build_payroll(year: int, month: int, salary: int, calendar_raw: str) -> PayrollResult:
    last_day = len(calendar_raw)
    details: list[DayInfo] = []
    hours_total = 0
    hours_1_15 = 0
    hours_16_end = 0
    short_days_count = 0

    for day in range(1, last_day + 1):
        code = calendar_raw[day - 1]
        if code in {"0", "4"}:
            day_type = "рабочий"
            hours = 8
        elif code == "2":
            day_type = "сокр."
            hours = 7
            short_days_count += 1
        else:
            day_type = "выходной"
            hours = 0
        weekday_short = WEEKDAY_SHORT[date(year, month, day).weekday()]
        details.append(DayInfo(day=day, weekday_short=weekday_short, day_type=day_type, hours=hours))
        hours_total += hours
        if day <= 15:
            hours_1_15 += hours
        else:
            hours_16_end += hours

    salary_dec = Decimal(salary)
    if hours_total == 0:
        advance = Decimal("0.00")
    else:
        advance = (salary_dec * Decimal(hours_1_15) / Decimal(hours_total)).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )
    salary2 = salary_dec - advance

    return PayrollResult(
        year=year,
        month=month,
        month_name=MONTH_NAMES[month - 1],
        last_day=last_day,
        hours_total=hours_total,
        hours_1_15=hours_1_15,
        hours_16_end=hours_16_end,
        advance=advance,
        salary2=salary2,
        short_days_count=short_days_count,
        details=details,
    )


def short_days_line(count: int) -> str:
    if count > 0:
        return f"Сокращённых дней: {count} (учтено -1 час)."
    return "Сокращённых дней нет."
