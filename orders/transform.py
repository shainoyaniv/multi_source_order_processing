"""Business rules: Order -> target system payload."""
from decimal import ROUND_HALF_UP, Decimal

from .models import InvalidOrder
from .reference import lookup_country

CENTS = Decimal("0.01")


def total_value(order):
    return (order.unit_price * order.quantity).quantize(CENTS, rounding=ROUND_HALF_UP)


def to_target(order):
    country = lookup_country(order.country_code)
    if country is None:
        # Without a country we can't set the currency, and guessing a
        # currency for a money field is worse than rejecting the order.
        raise InvalidOrder(f"unknown country code '{order.country_code}'")

    return {
        "orderReference": order.order_id,
        "customer": {
            "customerReference": order.customer_id,
            "fullName": order.customer_name,
            "country": country.name,
        },
        "orderTimestamp": order.order_time.isoformat(),
        "product": {
            "code": order.product_code,
            "quantity": order.quantity,
            "unitPrice": order.unit_price,
        },
        "totalOrderValue": total_value(order),
        "currency": country.currency,
    }