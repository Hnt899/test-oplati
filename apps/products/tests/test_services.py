"""Unit tests for Stripe service helpers."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import pytest

from apps.products.models import Currency, Discount, Item, Order, OrderItem, Tax
from apps.products.services import (
    create_checkout_session_for_item,
    create_checkout_session_for_order,
    ensure_stripe_coupon,
    ensure_stripe_tax_rate,
    get_publishable_key_for_currency,
    get_secret_key_for_currency,
)


@pytest.mark.django_db
def test_usd_price_below_50_interpreted_as_whole_dollars(settings: object) -> None:
    settings.STRIPE_SECRET_KEY_USD = "sk_test_usd"
    settings.SITE_URL = "http://testserver"
    item = Item.objects.create(
        name="USD dozen dollars stored as 12",
        description="",
        price=12,
        currency=Currency.USD,
    )
    fake = SimpleNamespace(id="cs_usd_1")
    with patch("stripe.checkout.Session.create", return_value=fake) as m:
        create_checkout_session_for_item(item)
    pd = m.call_args.kwargs["line_items"][0]["price_data"]
    assert pd["currency"] == "usd"
    assert pd["unit_amount"] == 1200


@pytest.mark.django_db
def test_usd_price_already_cents_not_scaled(settings: object) -> None:
    settings.STRIPE_SECRET_KEY_USD = "sk_test_usd"
    settings.SITE_URL = "http://testserver"
    item = Item.objects.create(
        name="USD cents",
        description="",
        price=999,
        currency=Currency.USD,
    )
    fake = SimpleNamespace(id="cs_usd_2")
    with patch("stripe.checkout.Session.create", return_value=fake) as m:
        create_checkout_session_for_item(item)
    pd = m.call_args.kwargs["line_items"][0]["price_data"]
    assert pd["unit_amount"] == 999


def test_get_secret_and_publishable_keys(settings: object) -> None:
    settings.STRIPE_SECRET_KEY = "sk_rub"
    settings.STRIPE_SECRET_KEY_USD = "sk_usd"
    settings.STRIPE_PUBLISHABLE_KEY = "pk_rub"
    settings.STRIPE_PUBLISHABLE_KEY_USD = "pk_usd"
    assert get_secret_key_for_currency("RUB") == "sk_rub"
    assert get_secret_key_for_currency("USD") == "sk_usd"
    assert get_publishable_key_for_currency("rub") == "pk_rub"
    assert get_publishable_key_for_currency("USD") == "pk_usd"


@pytest.mark.django_db
def test_ensure_stripe_coupon_reuses_stored_id(ten_percent_discount: Discount) -> None:
    ten_percent_discount.stripe_coupon_id = "existing_coupon"
    ten_percent_discount.save()
    with patch("stripe.Coupon.create") as m:
        cid = ensure_stripe_coupon(ten_percent_discount, "RUB")
    assert cid == "existing_coupon"
    assert not m.called


@pytest.mark.django_db
def test_ensure_stripe_coupon_creates_percent_coupon(ten_percent_discount: Discount) -> None:
    ten_percent_discount.stripe_coupon_id = ""
    ten_percent_discount.save()
    fake = SimpleNamespace(id="coupon_new")
    with patch("stripe.Coupon.create", return_value=fake) as m:
        cid = ensure_stripe_coupon(ten_percent_discount, "RUB")
    assert cid == "coupon_new"
    assert m.called
    ten_percent_discount.refresh_from_db()
    assert ten_percent_discount.stripe_coupon_id == "coupon_new"


@pytest.mark.django_db
def test_ensure_stripe_tax_rate_creates(ten_percent_tax: Tax) -> None:
    ten_percent_tax.stripe_tax_rate_id = ""
    ten_percent_tax.save()
    fake = SimpleNamespace(id="txr_new")
    with patch("stripe.TaxRate.create", return_value=fake):
        tid = ensure_stripe_tax_rate(ten_percent_tax, "RUB")
    assert tid == "txr_new"
    ten_percent_tax.refresh_from_db()
    assert ten_percent_tax.stripe_tax_rate_id == "txr_new"


@pytest.mark.django_db
def test_create_checkout_session_for_order_with_discount_and_tax(
    ten_percent_discount: Discount,
    ten_percent_tax: Tax,
) -> None:
    item = Item.objects.create(name="X", description="", price=5000, currency=Currency.RUB)
    order = Order.objects.create(discount=ten_percent_discount, tax=ten_percent_tax)
    OrderItem.objects.create(order=order, item=item, quantity=1)

    ten_percent_discount.stripe_coupon_id = "cpn_1"
    ten_percent_discount.save()
    ten_percent_tax.stripe_tax_rate_id = "txr_1"
    ten_percent_tax.save()

    fake_session = SimpleNamespace(id="cs_full")
    with patch("stripe.checkout.Session.create", return_value=fake_session) as m:
        session = create_checkout_session_for_order(order)

    assert session.id == "cs_full"
    kw = m.call_args.kwargs
    assert kw["discounts"] == [{"coupon": "cpn_1"}]
    assert kw["line_items"][0]["tax_rates"] == ["txr_1"]


@pytest.mark.django_db
def test_create_checkout_session_order_fixed_discount_creates_coupon(
    fixed_discount: Discount,
) -> None:
    fixed_discount.stripe_coupon_id = ""
    fixed_discount.save()
    item = Item.objects.create(name="X", description="", price=8000, currency=Currency.RUB)
    order = Order.objects.create(discount=fixed_discount)
    OrderItem.objects.create(order=order, item=item, quantity=1)

    fake_coupon = SimpleNamespace(id="cpn_fixed")
    fake_session = SimpleNamespace(id="cs_fixed")
    with patch("stripe.Coupon.create", return_value=fake_coupon):
        with patch("stripe.checkout.Session.create", return_value=fake_session):
            create_checkout_session_for_order(order)

    fixed_discount.refresh_from_db()
    assert fixed_discount.stripe_coupon_id == "cpn_fixed"
