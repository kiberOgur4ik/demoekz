"""Данные одной модели в каталоге."""

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class CatalogProduct:
    model_id: int
    name: str
    manufacturer: str
    category: str
    composition: str
    image_path: str | None
    available_qty: int
    base_price: Decimal
    final_price: Decimal
    has_discount: bool

    @property
    def low_stock(self) -> bool:
        return self.available_qty <= 3
