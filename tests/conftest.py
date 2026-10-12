import copy

import pytest

SAMPLE_A = {
    "orderId": "ORD-10001",
    "customerId": "CUST-501",
    "customerName": "John Smith",
    "country": "US",
    "orderDate": "2026-09-01T10:30:00",
    "productCode": "P100",
    "quantity": 2,
    "unitPrice": 125.50,
}

SAMPLE_B = {
    "order_number": "ORD-20001",
    "customer": {"id": "CUST-842", "first_name": "Jane", "last_name": "Miller", "country_code": "DE"},
    "created_at": "2026-09-01T11:15:00",
    "item": {"sku": "P200", "units": 3, "price": 80.00},
}


@pytest.fixture
def rec_a():
    return copy.deepcopy(SAMPLE_A)


@pytest.fixture
def rec_b():
    return copy.deepcopy(SAMPLE_B)