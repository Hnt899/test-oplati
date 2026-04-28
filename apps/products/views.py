"""HTTP views for catalog and Stripe checkout."""

from __future__ import annotations

import json
import logging
from typing import Any

from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.http import Http404, HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_http_methods

from apps.products.models import Item, Order, OrderItem
from apps.products.services import (
    create_checkout_session_for_item,
    create_checkout_session_for_order,
    create_payment_intent_for_item,
    get_publishable_key,
)

logger = logging.getLogger(__name__)


def _json_error(message: str, status: int = 400) -> JsonResponse:
    return JsonResponse({"detail": message}, status=status)


@require_GET
def item_list(request: HttpRequest) -> HttpResponse:
    """Catalog: all items with links to detail/checkout."""
    items = Item.objects.all().order_by("pk")
    return render(
        request,
        "products/item_list.html",
        {"items": items},
    )


@require_GET
def item_page(request: HttpRequest, pk: int) -> HttpResponse:
    try:
        item = Item.objects.get(pk=pk)
    except Item.DoesNotExist:
        raise Http404("Item not found") from None

    publishable_key = get_publishable_key(item.currency)
    return render(
        request,
        "products/item.html",
        {
            "item": item,
            "stripe_publishable_key": publishable_key,
        },
    )


@require_GET
def buy(request: HttpRequest, pk: int) -> JsonResponse:
    item = get_object_or_404(Item, pk=pk)
    try:
        session = create_checkout_session_for_item(item)
    except Exception:
        logger.exception("Stripe Checkout Session failed for item pk=%s", pk)
        return _json_error("Payment provider error", status=502)
    return JsonResponse({"session_id": session.id})


@require_GET
def buy_intent(request: HttpRequest, pk: int) -> JsonResponse:
    item = get_object_or_404(Item, pk=pk)
    try:
        intent = create_payment_intent_for_item(item)
    except Exception:
        logger.exception("Stripe PaymentIntent failed for item pk=%s", pk)
        return _json_error("Payment provider error", status=502)
    return JsonResponse({"client_secret": intent.client_secret})


@csrf_exempt
@require_http_methods(["POST"])
def create_order(request: HttpRequest) -> JsonResponse:
    try:
        body: dict[str, Any] = json.loads(request.body.decode() or "{}")
    except json.JSONDecodeError:
        return _json_error("Invalid JSON body")

    raw_items = body.get("items")
    if raw_items is None:
        return _json_error('Missing "items" field')

    if not isinstance(raw_items, list):
        return _json_error('"items" must be a list')

    if len(raw_items) == 0:
        return _json_error("items cannot be empty", status=400)

    discount_id = body.get("discount_id") or None
    tax_id = body.get("tax_id") or None

    order = Order(
        discount_id=discount_id,
        tax_id=tax_id,
    )

    try:
        try:
            order.save()
        except IntegrityError:
            return _json_error("Invalid discount_id or tax_id", status=400)
        currency: str | None = None
        for row in raw_items:
            if not isinstance(row, dict):
                raise ValueError("Each item entry must be an object")
            iid = row.get("id")
            qty = row.get("quantity", 1)
            if iid is None:
                raise ValueError("Each item needs an id")
            item = Item.objects.get(pk=int(iid))
            q = int(qty)
            if q < 1:
                raise ValueError("quantity must be >= 1")
            if currency is None:
                currency = item.currency
            elif item.currency != currency:
                raise ValueError("Mixed currencies are not allowed in one order")
            existing = OrderItem.objects.filter(order=order, item=item).first()
            if existing:
                existing.quantity += q
                existing.save(update_fields=["quantity"])
            else:
                OrderItem.objects.create(order=order, item=item, quantity=q)

        order.refresh_from_db()
        order.full_clean()
        session = create_checkout_session_for_order(order)
    except Item.DoesNotExist:
        order.delete()
        return _json_error("Item not found", status=404)
    except ValidationError as e:
        try:
            order.delete()
        except Exception:
            pass
        return _json_error("; ".join(e.messages), status=400)
    except ValueError as e:
        order.delete()
        return _json_error(str(e), status=400)
    except Exception:
        logger.exception("create_order failed")
        try:
            order.delete()
        except Exception:
            pass
        return _json_error("Could not create order", status=502)

    return JsonResponse({"session_id": session.id})


@require_GET
def checkout_success(request: HttpRequest) -> HttpResponse:
    return render(request, "products/checkout_success.html")


@require_GET
def checkout_cancel(request: HttpRequest) -> HttpResponse:
    return render(request, "products/checkout_cancel.html")
