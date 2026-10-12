"""Календарные границы и расчёт цены без ошибок float."""

from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal


def previous_month_bounds(calculation_date: date) -> tuple[date, date]:
    """Первый день прошлого месяца и первый день текущего (исключается)."""
    current_start = calculation_date.replace(day=1)
    previous_start = (current_start - timedelta(days=1)).replace(day=1)
    return previous_start, current_start


def calculate_price(base_price: Decimal, had_orders: bool) -> Decimal:
    """Скидка 25%, если модель не заказывали в прошлом календарном месяце."""
    price = base_price if had_orders else base_price * Decimal("0.75")
    return price.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def format_price(price: Decimal) -> str:
    """Рубли с пробелами между тысячами и запятой перед копейками."""
    return f"{price:,.2f}".replace(",", " ").replace(".", ",") + " ₽"
