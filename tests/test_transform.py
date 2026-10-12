from datetime import datetime
from decimal import Decimal

import pytest

from orders.models import InvalidOrder, Order
from orders.transform import to_target, total_value


def make_order(**overrides):
    fields = dict(
        source="A",
        order_id="ORD-10001",
        customer_id="CUST-501",
        customer_name="John Smith",
        country_code="US",
        order_time=datetime(2026, 9, 1, 10, 30),
        product_code="P100",
        quantity=2,
        unit_price=Decimal("125.50"),
    )
    fields.update(overrides)
    return Order(**fields)


def test_target_matches_spec_example():
    assert to_target(make_order()) == {
        "orderReference": "ORD-10001",
        "customer": {
            "customerReference": "CUST-501",
            "fullName": "John Smith",
            "country": "United States",
        },
        "orderTimestamp": "2026-09-01T10:30:00",
        "product": {"code": "P100", "quantity": 2, "unitPrice": Decimal("125.50")},
        "totalOrderValue": Decimal("251.00"),
        "currency": "USD",
    }


@pytest.mark.parametrize("code, name, currency", [
    ("US", "United States", "USD"),
    ("GB", "United Kingdom", "GBP"),
    ("DE", "Germany", "EUR"),
])
def test_country_and_currency(code, name, currency):
    out = to_target(make_order(country_code=code))
    assert out["customer"]["country"] == name
    assert out["currency"] == currency


def test_unknown_country_is_rejected():
    with pytest.raises(InvalidOrder, match="FR"):
        to_target(make_order(country_code="FR"))


def test_total_has_no_float_error():
    # in float, 3 * 0.1 == 0.30000000000000004
    assert total_value(make_order(quantity=3, unit_price=Decimal("0.1"))) == Decimal("0.30")


def test_total_rounds_half_up():
    assert total_value(make_order(quantity=1, unit_price=Decimal("10.005"))) == Decimal("10.01")