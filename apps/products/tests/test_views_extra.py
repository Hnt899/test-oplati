"""Extra view tests for branches and error paths."""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest
from django.test import Client

from apps.products.models import Currency, Item


@pytest.mark.django_db
def test_checkout_success_page(client: Client) -> None:
    resp = client.get("/checkout/success/")
    assert resp.status_code == 200
    body = resp.content.decode()
    assert "Спасибо за покупку" in body
    assert "Оплата прошла успешно" in body


@pytest.mark.django_db
def test_checkout_cancel_page(client: Client) -> None:
    resp = client.get("/checkout/cancel/")
    assert resp.status_code == 200
    body = resp.content.decode()
    assert "Оплата отменена" in body
    assert "попробовать снова" in body


@pytest.mark.django_db
def test_create_order_invalid_json(client: Client) -> None:
    resp = client.post("/create-order/", data="{", content_type="application/json")
    assert resp.status_code == 400


@pytest.mark.django_db
def test_create_order_missing_items_key(client: Client) -> None:
    resp = client.post("/create-order/", data=json.dumps({}), content_type="application/json")
    assert resp.status_code == 400


@pytest.mark.django_db
def test_create_order_mixed_currency_items(client: Client) -> None:
    rub = Item.objects.create(name="R", description="", price=100, currency=Currency.RUB)
    usd = Item.objects.create(name="U", description="", price=100, currency=Currency.USD)
    resp = client.post(
        "/create-order/",
        data=json.dumps(
            {
                "items": [
                    {"id": rub.pk, "quantity": 1},
                    {"id": usd.pk, "quantity": 1},
                ],
            },
        ),
        content_type="application/json",
    )
    assert resp.status_code == 400


@pytest.mark.django_db
def test_buy_stripe_failure_returns_502(client: Client, rub_item: object) -> None:
    with patch("stripe.checkout.Session.create", side_effect=RuntimeError("boom")):
        resp = client.get(f"/buy/{rub_item.pk}/")
    assert resp.status_code == 502
