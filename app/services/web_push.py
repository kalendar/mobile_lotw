import json
from dataclasses import dataclass, field
from datetime import datetime, timezone

from flask import current_app

from ..database.table_declarations import QSLDigestBatch, User, WebPushSubscription


class WebPushPermanentError(RuntimeError):
    pass


class WebPushTemporaryError(RuntimeError):
    pass


@dataclass
class WebPushDeliveryReport:
    attempted: int = 0
    sent: int = 0
    failed: int = 0
    errors: list[str] = field(default_factory=list)


def _default_send_callable(subscription: WebPushSubscription, payload: dict) -> None:
    try:
        from pywebpush import WebPushException, webpush  # type: ignore
    except ImportError as error:
        raise WebPushTemporaryError("pywebpush_not_installed") from error

    vapid_private_key = current_app.config.get("WEB_PUSH_VAPID_PRIVATE_KEY")
    vapid_subject = current_app.config.get("WEB_PUSH_VAPID_SUBJECT")
    if not vapid_private_key or not vapid_subject:
        raise WebPushTemporaryError("web_push_vapid_not_configured")

    subscription_info = {
        "endpoint": subscription.endpoint,
        "keys": {
            "p256dh": subscription.p256dh_key,
            "auth": subscription.auth_key,
        },
    }
    try:
        webpush(
            subscription_info=subscription_info,
            data=json.dumps(payload),
            vapid_private_key=vapid_private_key,
            vapid_claims={"sub": vapid_subject},
        )
    except WebPushException as error:
        response = getattr(error, "response", None)
        status_code = getattr(response, "status_code", None)
        if status_code in {404, 410}:
            raise WebPushPermanentError(f"endpoint_gone_{status_code}") from error
        raise WebPushTemporaryError(
            f"web_push_error_{status_code if status_code else 'unknown'}"
        ) from error


def send_qsl_digest_web_push(
    *,
    user: User,
    batch: QSLDigestBatch,
    subscriptions: list[WebPushSubscription],
    digest_url: str,
    send_callable=None,
) -> WebPushDeliveryReport:
    report = WebPushDeliveryReport()
    sender = send_callable or _default_send_callable
    now = datetime.now(tz=timezone.utc)

    payload = {
        "title": "New LoTW QSLs",
        "body": f"You received {batch.qsl_count} new QSLs.",
        "url": digest_url,
        "digest_date": batch.digest_date.isoformat(),
        "qsl_count": batch.qsl_count,
        "op": user.op,
    }

    for subscription in subscriptions:
        report.attempted += 1
        try:
            sender(subscription, payload)
            subscription.last_success_at = now
            subscription.last_failure_at = None
            subscription.failure_count = 0
            report.sent += 1
        except WebPushPermanentError as error:
            subscription.last_failure_at = now
            subscription.failure_count = (subscription.failure_count or 0) + 1
            subscription.status = "invalid"
            report.failed += 1
            report.errors.append(str(error))
        except Exception as error:  # noqa: BLE001
            subscription.last_failure_at = now
            subscription.failure_count = (subscription.failure_count or 0) + 1
            report.failed += 1
            report.errors.append(str(error))

    return report
