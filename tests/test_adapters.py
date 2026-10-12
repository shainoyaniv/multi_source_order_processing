from datetime import datetime
from decimal import Decimal

import pytest

from orders.adapters import get_adapter, parse_source_a, parse_source_b
from orders.models import InvalidOrder


def test_source_a_maps_all_fields(rec_a):
    order = parse_source_a(rec_a)
    assert order.source == "A"
    assert order.order_id == "ORD-10001"
    assert order.customer_id == "CUST-501"
    assert order.customer_name == "John Smith"
    assert order.country_code == "US"
    assert order.order_time == datetime(2026, 9, 1, 10, 30)
    assert order.product_code == "P100"
    assert order.quantity == 2
    assert order.unit_price == Decimal("125.5")


def test_source_b_maps_all_fields(rec_b):
    order = parse_source_b(rec_b)
    assert order.source == "B"
    assert order.order_id == "ORD-20001"
    assert order.customer_id == "CUST-842"
    assert order.customer_name == "Jane Miller"
    assert order.country_code == "DE"
    assert order.product_code == "P200"
    assert order.quantity == 3
    assert order.unit_price == Decimal("80")


def test_name_whitespace_is_normalized(rec_a):
    rec_a["customerName"] = "  John   Smith "
    assert parse_source_a(rec_a).customer_name == "John Smith"


def test_source_b_without_last_name(rec_b):
    del rec_b["customer"]["last_name"]
    assert parse_source_b(rec_b).customer_name == "Jane"


def test_source_b_without_first_name_is_rejected(rec_b):
    del rec_b["customer"]["first_name"]
    with pytest.raises(InvalidOrder):
        parse_source_b(rec_b)


def test_missing_nested_object_is_rejected(rec_b):
    del rec_b["item"]
    with pytest.raises(InvalidOrder, match="item.sku"):
        parse_source_b(rec_b)


def test_lowercase_country_is_normalized(rec_b):
    rec_b["customer"]["country_code"] = "de"
    assert parse_source_b(rec_b).country_code == "DE"


@pytest.mark.parametrize("field", ["orderId", "customerId", "customerName", "country",
                                   "orderDate", "productCode", "quantity", "unitPrice"])
def test_missing_field_is_rejected(rec_a, field):
    del rec_a[field]
    with pytest.raises(InvalidOrder, match=field):
        parse_source_a(rec_a)


def test_blank_string_is_rejected(rec_a):
    rec_a["orderId"] = "   "
    with pytest.raises(InvalidOrder):
        parse_source_a(rec_a)


@pytest.mark.parametrize("quantity", [0, -1, 1.5, "2", True, None])
def test_invalid_quantity(rec_a, quantity):
    rec_a["quantity"] = quantity
    with pytest.raises(InvalidOrder):
        parse_source_a(rec_a)


@pytest.mark.parametrize("price", [-1, "abc", None, True, float("nan")])
def test_invalid_price(rec_a, price):
    rec_a["unitPrice"] = price
    with pytest.raises(InvalidOrder):
        parse_source_a(rec_a)


def test_zero_price_is_allowed(rec_a):
    rec_a["unitPrice"] = 0
    assert parse_source_a(rec_a).unit_price == 0


def test_invalid_timestamp(rec_a):
    rec_a["orderDate"] = "01/09/2026"
    with pytest.raises(InvalidOrder):
        parse_source_a(rec_a)


def test_unknown_source():
    with pytest.raises(ValueError):
        get_adapter("C")