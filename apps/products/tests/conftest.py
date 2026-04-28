"""Pytest fixtures."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

import pytest


@pytest.fixture(autouse=True)
def _configure_stripe_keys_and_site(settings: Any) -> None:
    settings.STRIPE_PUBLISHABLE_KEY = "pk_test_rub"
    settings.STRIPE_SECRET_KEY = "sk_test_rub"
    settings.STRIPE_PUBLISHABLE_KEY_USD = "pk_test_usd"
    settings.STRIPE_SECRET_KEY_USD = "sk_test_usd"
    settings.SITE_URL = "http://testserver"


@pytest.fixture
def rub_item(db: Any) -> Any:
    from apps.products.models import Currency, Item

    return Item.objects.create(
        name="Test RUB",
        description="desc",
        price=1000,
        currency=Currency.RUB,
    )


@pytest.fixture
def usd_item(db: Any) -> Any:
    from apps.products.models import Currency, Item

    return Item.objects.create(
        name="Test USD",
        description="desc",
        price=999,
        currency=Currency.USD,
    )


@pytest.fixture
def ten_percent_discount(db: Any) -> Any:
    from apps.products.models import Discount, DiscountType

    return Discount.objects.create(
        name="10%",
        discount_type=DiscountType.PERCENT,
        value=Decimal("10.00"),
    )


@pytest.fixture
def fixed_discount(db: Any) -> Any:
    from apps.products.models import Discount, DiscountType

    return Discount.objects.create(
        name="500 off",
        discount_type=DiscountType.FIXED,
        value=Decimal("500"),
    )


@pytest.fixture
def ten_percent_tax(db: Any) -> Any:
    from apps.products.models import Tax

    return Tax.objects.create(name="VAT", rate_percent=Decimal("10.00"))
