"""Integration-style tests with mocked Stripe."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import pytest
from django.test import Client

from apps.products.models import Currency, Item


@pytest.mark.django_db
def test_full_checkout_flow(client: Client) -> None:
    item = Item.objects.create(
        name="Flow Item",
        description="Integration test product",
        price=1500,
        currency=Currency.RUB,
    )
    fake_session = SimpleNamespace(id="cs_integration_1")

    with patch("stripe.checkout.Session.create", return_value=fake_session) as m_create:
        page = client.get(f"/item/{item.pk}/")
        assert page.status_code == 200
        assert item.name in page.content.decode()

        buy_resp = client.get(f"/buy/{item.pk}/")
        assert buy_resp.status_code == 200
        assert buy_resp.json()["session_id"] == "cs_integration_1"

    call_kw = m_create.call_args.kwargs
    assert call_kw.get("mode") == "payment"
    line_items = call_kw.get("line_items") or []
    assert len(line_items) == 1
    assert line_items[0]["quantity"] == 1
    pd = line_items[0]["price_data"]
    assert pd["currency"] == "rub"
    assert pd["unit_amount"] == 1500
    assert pd["product_data"]["name"] == "Flow Item"
