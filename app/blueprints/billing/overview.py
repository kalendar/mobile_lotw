from datetime import datetime, timezone
from os import getenv
from typing import Any

from flask import current_app, jsonify, render_template, request, session, url_for
from sqlalchemy import select

from ...database.queries import get_user
from ...database.table_declarations import StripeEvent, User
from ..auth.wrappers import login_required
from .base import bp


def _get_stripe():
    try:
        import stripe  # type: ignore

        return stripe
    except ImportError:
        return None


def _stripe_ready() -> bool:
    monthly_price_id = getenv("STRIPE_PRICE_ID_MONTHLY") or getenv("STRIPE_PRICE_ID")
    annual_price_id = getenv("STRIPE_PRICE_ID_ANNUAL")
    return bool(
        getenv("STRIPE_SECRET_KEY")
        and getenv("STRIPE_WEBHOOK_SECRET")
        and (monthly_price_id or annual_price_id)
    )


def _stripe_price_options() -> dict[str, str]:
    options: dict[str, str] = {}
    monthly_price_id = getenv("STRIPE_PRICE_ID_MONTHLY") or getenv("STRIPE_PRICE_ID")
    annual_price_id = getenv("STRIPE_PRICE_ID_ANNUAL")

    if monthly_price_id:
        options["monthly"] = monthly_price_id
    if annual_price_id:
        options["annual"] = annual_price_id

    return options


def _timestamp_to_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    try:
        return datetime.fromtimestamp(int(value), tz=timezone.utc)
    except (TypeError, ValueError):
        return None


def _apply_subscription_to_user(
    *,
    customer_id: str | None,
    subscription_id: str | None,
    status: str | None,
    period_end_ts: Any,
) -> None:
    if not customer_id:
        return

    with current_app.config.get("SESSION_MAKER").begin() as session_:
        user = session_.scalar(
            select(User).where(User.stripe_customer_id == customer_id)
        )
        if not user:
            return

        user.stripe_subscription_id = subscription_id
        user.subscription_status = status or user.subscription_status
        period_end = _timestamp_to_datetime(period_end_ts)
        user.subscription_current_period_end = period_end
        user.entitlement_expires_at = period_end
        user.plan_tier = (
            "plus"
            if (status or "").lower() in {"active", "trialing"}
            else "free"
        )


@bp.get("/billing")
@login_required(next_page="billing.overview")
def overview():
    with current_app.config.get("SESSION_MAKER").begin() as session_:
        user = get_user(op=session.get("op"), session=session_)
        subscription = {
            "tier": user.plan_tier,
            "status": user.subscription_status,
            "current_period_end": user.subscription_current_period_end,
            "entitlement_expires_at": user.entitlement_expires_at,
            "stripe_customer_id": user.stripe_customer_id,
            "stripe_subscription_id": user.stripe_subscription_id,
        }

    return render_template(
        "billing.html",
        title="Billing",
        subscription=subscription,
        stripe_ready=_stripe_ready(),
        price_options=_stripe_price_options(),
    )


@bp.post("/api/v1/billing/create-checkout-session")
@login_required()
def create_checkout_session():
    stripe = _get_stripe()
    if not stripe:
        return jsonify({"error": "stripe_not_installed"}), 503

    secret_key = getenv("STRIPE_SECRET_KEY")
    price_options = _stripe_price_options()
    if not secret_key or not price_options:
        return jsonify({"error": "stripe_not_configured"}), 503

    stripe.api_key = secret_key
    payload = request.get_json(silent=True) or {}
    email = (payload.get("email") or "").strip() or None
    plan = (payload.get("plan") or "monthly").strip().lower()
    price_id = price_options.get(plan)
    if not price_id:
        return jsonify({"error": "invalid_plan"}), 400

    with current_app.config.get("SESSION_MAKER").begin() as session_:
        user = get_user(op=session.get("op"), session=session_)
        if email and not user.email:
            user.email = email

        try:
            if not user.stripe_customer_id:
                customer = stripe.Customer.create(
                    email=user.email,
                    metadata={"op": user.op},
                )
                user.stripe_customer_id = customer.id

            checkout_session = stripe.checkout.Session.create(
                mode="subscription",
                customer=user.stripe_customer_id,
                line_items=[{"price": price_id, "quantity": 1}],
                metadata={"selected_plan": plan},
                success_url=url_for("billing.overview", _external=True)
                + "?checkout=success",
                cancel_url=url_for("billing.overview", _external=True)
                + "?checkout=cancel",
                allow_promotion_codes=True,
            )
        except Exception as error:  # noqa: BLE001
            current_app.logger.exception("Stripe checkout session creation failed.")
            return jsonify({"error": "stripe_checkout_failed", "detail": str(error)}), 502

        return jsonify(
            {
                "checkout_url": checkout_session.url,
            }
        )


@bp.post("/api/v1/billing/webhook")
def stripe_webhook():
    stripe = _get_stripe()
    if not stripe:
        return jsonify({"error": "stripe_not_installed"}), 503

    secret_key = getenv("STRIPE_SECRET_KEY")
    webhook_secret = getenv("STRIPE_WEBHOOK_SECRET")
    if not secret_key or not webhook_secret:
        return jsonify({"error": "stripe_not_configured"}), 503

    stripe.api_key = secret_key
    payload = request.get_data(cache=False)
    signature = request.headers.get("Stripe-Signature")

    try:
        event = stripe.Webhook.construct_event(
            payload=payload,
            sig_header=signature,
            secret=webhook_secret,
        )
    except Exception:
        return jsonify({"error": "invalid_webhook_signature"}), 400

    event_id = event.get("id")
    event_type = event.get("type", "unknown")

    with current_app.config.get("SESSION_MAKER").begin() as session_:
        if event_id:
            existing = session_.scalar(
                select(StripeEvent).where(StripeEvent.event_id == event_id)
            )
            if existing:
                return jsonify({"status": "duplicate"}), 200

        event_record = StripeEvent(
            event_id=event_id or f"missing-id-{datetime.now(tz=timezone.utc).timestamp()}",
            event_type=event_type,
            status="received",
            payload=event,
        )
        session_.add(event_record)

    try:
        data_object = event.get("data", {}).get("object", {})
        if event_type in {
            "customer.subscription.created",
            "customer.subscription.updated",
            "customer.subscription.deleted",
        }:
            _apply_subscription_to_user(
                customer_id=data_object.get("customer"),
                subscription_id=data_object.get("id"),
                status=data_object.get("status"),
                period_end_ts=data_object.get("current_period_end"),
            )
        elif event_type == "checkout.session.completed":
            _apply_subscription_to_user(
                customer_id=data_object.get("customer"),
                subscription_id=data_object.get("subscription"),
                status="active",
                period_end_ts=data_object.get("expires_at"),
            )

        with current_app.config.get("SESSION_MAKER").begin() as session_:
            saved_event = session_.scalar(
                select(StripeEvent).where(StripeEvent.event_id == event_id)
            )
            if saved_event:
                saved_event.status = "processed"
                saved_event.processed_at = datetime.now(tz=timezone.utc)
    except Exception as error:  # noqa: BLE001
        current_app.logger.exception("Stripe webhook processing failed.")
        with current_app.config.get("SESSION_MAKER").begin() as session_:
            saved_event = session_.scalar(
                select(StripeEvent).where(StripeEvent.event_id == event_id)
            )
            if saved_event:
                saved_event.status = "failed"
                saved_event.processed_at = datetime.now(tz=timezone.utc)
        return jsonify({"error": "webhook_processing_failed", "detail": str(error)}), 500

    return jsonify({"status": "ok"}), 200
