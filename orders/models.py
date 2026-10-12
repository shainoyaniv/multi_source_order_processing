from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


class InvalidOrder(Exception):
    """A record that can't be turned into a valid order (bad data, not a bug)."""


@dataclass(frozen=True)
class Order:
    """Internal order model, independent of the source format."""
    source: str
    order_id: str
    customer_id: str
    customer_name: str
    country_code: str
    order_time: datetime
    product_code: str
    quantity: int
    unit_price: Decimal
