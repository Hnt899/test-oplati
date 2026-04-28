"""HTTP endpoint tests."""

from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from django.test import Client


@pytest.mark.django_db
def test_get_item_page_200(rub_item: object, client: Client) -> None:
    resp = client.get(f"/item/{rub_item.pk}/")
    assert resp.status_code == 200
    content = resp.content.decode()
    assert rub_item.name in content


@pytest.mark.django_db
def test_get_item_page_404(client: Client) -> None:
    resp = client.get("/item/999999/")
    assert resp.status_code == 404


@pytest.mark.django_db
def test_buy_endpoint_returns_session_id(rub_item: object, client: Client) -> None:
    fake_session = SimpleNamespace(id="cs_test_abc123")
    with patch("stripe.checkout.Session.create", return_value=fake_session) as m:
        resp = client.get(f"/buy/{rub_item.pk}/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["session_id"] == "cs_test_abc123"
    assert m.called


@pytest.mark.django_db
def test_buy_endpoint_404(client: Client) -> None:
    with patch("stripe.checkout.Session.create") as m:
        resp = client.get("/buy/999999/")
    assert resp.status_code == 404
    assert not m.called


@pytest.mark.django_db
def test_buy_intent_returns_client_secret(rub_item: object, client: Client) -> None:
    fake_pi = SimpleNamespace(client_secret="pi_secret_xyz")
    with patch("stripe.PaymentIntent.create", return_value=fake_pi):
        resp = client.get(f"/buy-intent/{rub_item.pk}/")
    assert resp.status_code == 200
    assert resp.json()["client_secret"] == "pi_secret_xyz"


@pytest.mark.django_db
def test_create_order_endpoint(rub_item: object, client: Client) -> None:
    fake_session = SimpleNamespace(id="cs_order_1")
    with patch("stripe.checkout.Session.create", return_value=fake_session):
        resp = client.post(
            "/create-order/",
            data=json.dumps({"items": [{"id": rub_item.pk, "quantity": 2}]}),
            content_type="application/json",
        )
    assert resp.status_code == 200
    assert resp.json()["session_id"] == "cs_order_1"


@pytest.mark.django_db
def test_create_order_empty_items(client: Client) -> None:
    resp = client.post(
        "/create-order/",
        data=json.dumps({"items": []}),
        content_type="application/json",
    )
    assert resp.status_code == 400


@pytest.mark.django_db
def test_create_order_invalid_item_id(client: Client) -> None:
    resp = client.post(
        "/create-order/",
        data=json.dumps({"items": [{"id": 999999, "quantity": 1}]}),
        content_type="application/json",
    )
    assert resp.status_code == 404
