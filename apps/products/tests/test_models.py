"""Unit tests for domain models."""

from __future__ import annotations

import pytest
from django.core.exceptions import ValidationError

from apps.products.models import Currency, Discount, Item, Order, OrderItem, Tax


@pytest.mark.django_db
def test_create_item() -> None:
    item = Item.objects.create(
        name="Widget",
        description="A widget",
        price=12345,
        currency=Currency.USD,
    )
    assert item.pk is not None
    assert item.name == "Widget"
    assert item.description == "A widget"
    assert item.price == 12345
    assert item.currency == Currency.USD


@pytest.mark.django_db
def test_item_str_method() -> None:
    item = Item.objects.create(name="Name", description="", price=1, currency=Currency.RUB)
    assert str(item) == "Name (RUB)"


@pytest.mark.django_db
def test_create_order() -> None:
    a = Item.objects.create(name="A", description="", price=100, currency=Currency.RUB)
    b = Item.objects.create(name="B", description="", price=200, currency=Currency.RUB)
    order = Order.objects.create()
    OrderItem.objects.create(order=order, item=a, quantity=2)
    OrderItem.objects.create(order=order, item=b, quantity=1)
    assert order.order_items.count() == 2


@pytest.mark.django_db
def test_order_total_price() -> None:
    a = Item.objects.create(name="A", description="", price=500, currency=Currency.RUB)
    b = Item.objects.create(name="B", description="", price=300, currency=Currency.RUB)
    order = Order.objects.create()
    OrderItem.objects.create(order=order, item=a, quantity=2)
    OrderItem.objects.create(order=order, item=b, quantity=1)
    assert order.subtotal_amount() == 500 * 2 + 300
    assert order.total_price() == order.subtotal_amount()


@pytest.mark.django_db
def test_order_with_discount_percent(ten_percent_discount: Discount) -> None:
    item = Item.objects.create(name="A", description="", price=10000, currency=Currency.RUB)
    order = Order.objects.create(discount=ten_percent_discount)
    OrderItem.objects.create(order=order, item=item, quantity=1)
    assert order.subtotal_amount() == 10000
    assert order.total_price() == 9000


@pytest.mark.django_db
def test_order_with_discount_fixed(fixed_discount: Discount) -> None:
    item = Item.objects.create(name="A", description="", price=10000, currency=Currency.RUB)
    order = Order.objects.create(discount=fixed_discount)
    OrderItem.objects.create(order=order, item=item, quantity=1)
    assert order.total_price() == 9500


@pytest.mark.django_db
def test_order_with_tax(ten_percent_tax: Tax) -> None:
    item = Item.objects.create(name="A", description="", price=10000, currency=Currency.RUB)
    order = Order.objects.create(tax=ten_percent_tax)
    OrderItem.objects.create(order=order, item=item, quantity=1)
    assert order.subtotal_amount() == 10000
    assert order.total_price() == 11000


@pytest.mark.django_db
def test_order_currency_mismatch() -> None:
    rub = Item.objects.create(name="R", description="", price=100, currency=Currency.RUB)
    usd = Item.objects.create(name="U", description="", price=100, currency=Currency.USD)
    order = Order.objects.create()
    OrderItem.objects.create(order=order, item=rub, quantity=1)
    OrderItem.objects.create(order=order, item=usd, quantity=1)
    with pytest.raises(ValidationError):
        order.full_clean()
