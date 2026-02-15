from datetime import datetime, timezone

from flask import current_app, jsonify, request, session
from sqlalchemy import select

from ...database.queries import get_user
from ...database.table_declarations import WebPushSubscription
from ..auth.wrappers import login_required, paid_required
from .base import bp


def _extract_subscription_data(data: dict) -> tuple[str, str, str]:
    endpoint = (data.get("endpoint") or "").strip()
    keys = data.get("keys") or {}
    p256dh = (data.get("p256dh") or keys.get("p256dh") or "").strip()
    auth = (data.get("auth") or keys.get("auth") or "").strip()
    return endpoint, p256dh, auth


@bp.get("/api/v1/notifications/web-push/public-key")
@login_required()
@paid_required()
def web_push_public_key():
    key = current_app.config.get("WEB_PUSH_VAPID_PUBLIC_KEY", "")
    if not key:
        return jsonify({"error": "web_push_not_configured"}), 503
    return jsonify({"public_key": key})


@bp.post("/api/v1/notifications/web-push/subscribe")
@login_required()
@paid_required()
def web_push_subscribe():
    payload = request.get_json(silent=True) or {}
    endpoint, p256dh, auth = _extract_subscription_data(payload)
    if not endpoint or not p256dh or not auth:
        return jsonify({"error": "invalid_subscription_payload"}), 400

    now = datetime.now(tz=timezone.utc)
    with current_app.config.get("SESSION_MAKER").begin() as session_:
        user = get_user(op=session.get("op"), session=session_)
        subscription = session_.scalar(
            select(WebPushSubscription).where(
                WebPushSubscription.endpoint == endpoint
            )
        )
        if subscription is None:
            subscription = WebPushSubscription(
                user_id=user.id,
                endpoint=endpoint,
                p256dh_key=p256dh,
                auth_key=auth,
            )
            session_.add(subscription)

        subscription.user_id = user.id
        subscription.p256dh_key = p256dh
        subscription.auth_key = auth
        subscription.status = "active"
        subscription.user_agent = (
            payload.get("user_agent")
            or request.headers.get("User-Agent")
            or subscription.user_agent
        )
        subscription.platform = payload.get("platform") or subscription.platform
        subscription.last_seen_at = now

        session_.flush()
        return jsonify(
            {
                "status": "ok",
                "subscription_id": subscription.id,
            }
        )


@bp.post("/api/v1/notifications/web-push/unsubscribe")
@login_required()
@paid_required()
def web_push_unsubscribe():
    payload = request.get_json(silent=True) or {}
    endpoint = (payload.get("endpoint") or "").strip()
    if not endpoint:
        return jsonify({"error": "missing_endpoint"}), 400

    now = datetime.now(tz=timezone.utc)
    with current_app.config.get("SESSION_MAKER").begin() as session_:
        user = get_user(op=session.get("op"), session=session_)
        subscription = session_.scalar(
            select(WebPushSubscription).where(
                WebPushSubscription.user_id == user.id,
                WebPushSubscription.endpoint == endpoint,
            )
        )
        if subscription:
            subscription.status = "unsubscribed"
            subscription.last_seen_at = now
            subscription.updated_at = now
        return jsonify({"status": "ok"})


@bp.post("/api/v1/notifications/web-push/heartbeat")
@login_required()
@paid_required()
def web_push_heartbeat():
    payload = request.get_json(silent=True) or {}
    endpoint = (payload.get("endpoint") or "").strip()
    if not endpoint:
        return jsonify({"error": "missing_endpoint"}), 400

    now = datetime.now(tz=timezone.utc)
    with current_app.config.get("SESSION_MAKER").begin() as session_:
        user = get_user(op=session.get("op"), session=session_)
        subscription = session_.scalar(
            select(WebPushSubscription).where(
                WebPushSubscription.user_id == user.id,
                WebPushSubscription.endpoint == endpoint,
            )
        )
        if not subscription:
            return jsonify({"error": "subscription_not_found"}), 404
        subscription.last_seen_at = now
        subscription.updated_at = now
        return jsonify({"status": "ok"})
