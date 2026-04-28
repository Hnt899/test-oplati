"""Stripe integration: key selection, Checkout Sessions, Payment Intents."""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urljoin

import stripe
from django.conf import settings

from apps.products.models import Currency, DiscountType, Item, Order

logger = logging.getLogger(__name__)


def get_secret_key_for_currency(currency: str) -> str:
    cur = currency.upper()
    if cur == Currency.USD:
        key = settings.STRIPE_SECRET_KEY_USD
        if not key:
            raise RuntimeError("STRIPE_SECRET_KEY_USD is not configured")
        return key
    key = settings.STRIPE_SECRET_KEY
    if not key:
        raise RuntimeError("STRIPE_SECRET_KEY is not configured")
    return key


def get_publishable_key_for_currency(currency: str) -> str:
    cur = currency.upper()
    if cur == Currency.USD:
        pk = settings.STRIPE_PUBLISHABLE_KEY_USD
        if not pk:
            raise RuntimeError("STRIPE_PUBLISHABLE_KEY_USD is not configured")
        return pk
    pk = settings.STRIPE_PUBLISHABLE_KEY
    if not pk:
        raise RuntimeError("STRIPE_PUBLISHABLE_KEY is not configured")
    return pk


def _stripe_request_options(currency: str) -> dict[str, Any]:
    return {"api_key": get_secret_key_for_currency(currency)}


def ensure_stripe_coupon(discount: Any, currency: str) -> str | None:
    """Return Stripe coupon id for Checkout Session discounts[]."""
    if discount.stripe_coupon_id:
        return discount.stripe_coupon_id
    opts = _stripe_request_options(currency)
    if discount.discount_type == DiscountType.PERCENT:
        coupon = stripe.Coupon.create(
            percent_off=float(discount.value),
            duration="once",
            name=discount.name[:40],
            **opts,
        )
    else:
        coupon = stripe.Coupon.create(
            amount_off=int(discount.value),
            currency=currency.lower(),
            duration="once",
            name=discount.name[:40],
            **opts,
        )
    discount.stripe_coupon_id = coupon.id
    discount.save(update_fields=["stripe_coupon_id"])
    logger.info("Created Stripe coupon %s for discount pk=%s", coupon.id, discount.pk)
    return coupon.id


def ensure_stripe_tax_rate(tax: Any, currency: str) -> str | None:
    if tax.stripe_tax_rate_id:
        return tax.stripe_tax_rate_id
    opts = _stripe_request_options(currency)
    tr = stripe.TaxRate.create(
        display_name=tax.name[:40],
        percentage=float(tax.rate_percent),
        inclusive=False,
        **opts,
    )
    tax.stripe_tax_rate_id = tr.id
    tax.save(update_fields=["stripe_tax_rate_id"])
    logger.info("Created Stripe TaxRate %s for tax pk=%s", tr.id, tax.pk)
    return tr.id


def build_success_cancel_urls() -> tuple[str, str]:
    base = settings.SITE_URL.rstrip("/") + "/"
    success = urljoin(base, "checkout/success/")
    cancel = urljoin(base, "checkout/cancel/")
    return success, cancel


def create_checkout_session_for_item(item: Item) -> stripe.checkout.Session:
    success_url, cancel_url = build_success_cancel_urls()
    opts = _stripe_request_options(item.currency)
    session = stripe.checkout.Session.create(
        mode="payment",
        line_items=[
            {
                "price_data": {
                    "currency": item.currency.lower(),
                    "product_data": {"name": item.name, "description": item.description[:500]},
                    "unit_amount": item.price,
                },
                "quantity": 1,
            }
        ],
        success_url=success_url + "?session_id={CHECKOUT_SESSION_ID}",
        cancel_url=cancel_url,
        **opts,
    )
    logger.debug("Checkout Session created for item pk=%s session=%s", item.pk, session.id)
    return session


def create_checkout_session_for_order(order: Order) -> stripe.checkout.Session:
    currency = order.assert_single_currency()
    success_url, cancel_url = build_success_cancel_urls()
    opts = _stripe_request_options(currency)

    tax_rate_id: str | None = None
    if order.tax_id:
        tax_rate_id = ensure_stripe_tax_rate(order.tax, currency)

    line_items: list[dict[str, Any]] = []
    for oi in order.order_items.select_related("item").all():
        li: dict[str, Any] = {
            "price_data": {
                "currency": oi.item.currency.lower(),
                "product_data": {
                    "name": oi.item.name,
                    "description": oi.item.description[:500],
                },
                "unit_amount": oi.item.price,
            },
            "quantity": oi.quantity,
        }
        if tax_rate_id:
            li["tax_rates"] = [tax_rate_id]
        line_items.append(li)

    payload: dict[str, Any] = {
        "mode": "payment",
        "line_items": line_items,
        "success_url": success_url + "?session_id={CHECKOUT_SESSION_ID}",
        "cancel_url": cancel_url,
        **opts,
    }

    if order.discount_id:
        cid = ensure_stripe_coupon(order.discount, currency)
        if cid:
            payload["discounts"] = [{"coupon": cid}]

    session = stripe.checkout.Session.create(**payload)
    logger.debug("Checkout Session created for order pk=%s session=%s", order.pk, session.id)
    return session


def create_payment_intent_for_item(item: Item) -> stripe.PaymentIntent:
    opts = _stripe_request_options(item.currency)
    intent = stripe.PaymentIntent.create(
        amount=item.price,
        currency=item.currency.lower(),
        metadata={"item_id": str(item.pk)},
        automatic_payment_methods={"enabled": True},
        **opts,
    )
    intent_id = getattr(intent, "id", "")
    logger.debug("PaymentIntent created for item pk=%s intent=%s", item.pk, intent_id)
    return intent
