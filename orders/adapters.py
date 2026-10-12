"""Source adapters: raw JSON dict -> Order.

Each adapter only knows about its own source's shape. Field validation
is shared, so both sources reject bad data the same way.
"""
from datetime import datetime
from decimal import Decimal, InvalidOperation

from .models import InvalidOrder, Order


def _get(data, path):
    """Read a nested key like 'customer.id'. Returns None if any part is missing."""
    cur = data
    for key in path.split("."):
        if not isinstance(cur, dict) or key not in cur:
            return None
        cur = cur[key]
    return cur


def _require_str(data, path):
    value = _get(data, path)
    if not isinstance(value, str) or not value.strip():
        raise InvalidOrder(f"missing or empty field '{path}'")
    return value.strip()


def _require_quantity(data, path):
    value = _get(data, path)
    # bool is a subclass of int in Python, so exclude it explicitly
    if isinstance(value, bool) or not isinstance(value, int):
        raise InvalidOrder(f"'{path}' must be an integer, got {value!r}")
    if value <= 0:
        raise InvalidOrder(f"'{path}' must be positive, got {value}")
    return value


def _require_price(data, path):
    value = _get(data, path)
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        raise InvalidOrder(f"'{path}' must be a number, got {value!r}")
    try:
        # via str() so 80.1 becomes Decimal('80.1'), not the float's binary expansion
        price = Decimal(str(value))
    except InvalidOperation:
        raise InvalidOrder(f"'{path}' is not a valid number: {value!r}")
    if not price.is_finite() or price < 0:
        raise InvalidOrder(f"'{path}' must be a non-negative number, got {value!r}")
    return price


def _require_timestamp(data, path):
    raw = _require_str(data, path)
    try:
        return datetime.fromisoformat(raw)
    except ValueError:
        raise InvalidOrder(f"'{path}' is not an ISO-8601 timestamp: {raw!r}")


def parse_source_a(data):
    return Order(
        source="A",
        order_id=_require_str(data, "orderId"),
        customer_id=_require_str(data, "customerId"),
        customer_name=" ".join(_require_str(data, "customerName").split()),
        country_code=_require_str(data, "country").upper(),
        order_time=_require_timestamp(data, "orderDate"),
        product_code=_require_str(data, "productCode"),
        quantity=_require_quantity(data, "quantity"),
        unit_price=_require_price(data, "unitPrice"),
    )


def parse_source_b(data):
    first = _require_str(data, "customer.first_name")
    # last name is optional - some people only have one name
    last = _get(data, "customer.last_name")
    last = last.strip() if isinstance(last, str) else ""
    full_name = f"{first} {last}".strip()

    return Order(
        source="B",
        order_id=_require_str(data, "order_number"),
        customer_id=_require_str(data, "customer.id"),
        customer_name=" ".join(full_name.split()),
        country_code=_require_str(data, "customer.country_code").upper(),
        order_time=_require_timestamp(data, "created_at"),
        product_code=_require_str(data, "item.sku"),
        quantity=_require_quantity(data, "item.units"),
        unit_price=_require_price(data, "item.price"),
    )


# Adding a source = write a parse function and register it here.
ADAPTERS = {
    "A": parse_source_a,
    "B": parse_source_b,
}


def get_adapter(source):
    try:
        return ADAPTERS[source.upper()]
    except KeyError:
        raise ValueError(f"unknown source '{source}', expected one of {sorted(ADAPTERS)}")

