"""Чтение каталога из PostgreSQL одной общей выборкой."""

from datetime import date

import psycopg2
from app.config import DB_CONFIG
from app.models import CatalogProduct
from app.pricing import calculate_price, previous_month_bounds
from psycopg2.extras import RealDictCursor

CATALOG_SQL = """
    WITH stock AS (
        SELECT model_id, SUM(available_qty) AS available_qty
        FROM public.skus
        GROUP BY model_id
    )
    SELECT m.id AS model_id, m.name, m.manufacturer,
           c.name AS category, m.composition, m.image_path,
           COALESCE(stock.available_qty, 0) AS available_qty,
           m.price AS base_price,
           EXISTS (
               SELECT 1
               FROM public.order_skus AS item
               JOIN public.orders AS o ON o.id = item.order_id
               JOIN public.skus AS s ON s.id = item.sku_id
               WHERE s.model_id = m.id
                 AND o.created_at >= %s AND o.created_at < %s
           ) AS had_orders
    FROM public.shoe_models AS m
    JOIN public.categories AS c ON c.id = m.category_id
    LEFT JOIN stock ON stock.model_id = m.id
    ORDER BY m.id
"""


def load_catalog(calculation_date: date) -> list[CatalogProduct]:
    """Загрузить модели, сумму остатков и цену на переданную дату."""
    bounds = previous_month_bounds(calculation_date)
    connection = psycopg2.connect(**DB_CONFIG)
    try:
        connection.set_session(readonly=True)
        with connection, connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("SELECT set_config('statement_timeout', '5000', true)")
            # EXISTS не умножает остаток при нескольких заказах одного SKU.
            cursor.execute(CATALOG_SQL, bounds)
            products = []
            for row in cursor.fetchall():
                had_orders = row.pop("had_orders")
                products.append(
                    CatalogProduct(
                        **row,
                        final_price=calculate_price(row["base_price"], had_orders),
                        has_discount=not had_orders,
                    )
                )
            return products
    finally:
        # Контекст psycopg2 завершает транзакцию, но не закрывает соединение.
        connection.close()
