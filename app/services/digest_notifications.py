from datetime import datetime, timezone

from flask import current_app
from sqlalchemy import select

from ..database.queries import (
    ensure_notification_preference,
    get_active_web_push_subscriptions,
    get_delivery_for_batch_channel,
)
from ..database.table_declarations import (
    NotificationDelivery,
    QSLDigestBatch,
)
from .digest_email import send_qsl_digest_email
from .web_push import send_qsl_digest_web_push


def _digest_url(batch: QSLDigestBatch) -> str:
    base_url = (current_app.config.get("DIGEST_BASE_URL") or "").strip().rstrip("/")
    path = f"/qsl/digest?date={batch.digest_date.isoformat()}"
    if base_url:
        return f"{base_url}{path}"
    return path


def _notification_recipient_email(*, user, preference) -> str | None:
    if not preference:
        return (user.email or "").strip() or None

    if preference.use_account_email_for_notifications:
        return (user.email or "").strip() or None

    custom = (preference.notification_email or "").strip()
    if custom:
        return custom
    return None


def _upsert_delivery(
    *,
    user_id: int,
    digest_batch_id: int,
    channel: str,
    status: str,
    session,
    provider_message_id: str | None = None,
    error_code: str | None = None,
    error_detail: str | None = None,
) -> NotificationDelivery:
    delivery = get_delivery_for_batch_channel(
        user_id=user_id,
        digest_batch_id=digest_batch_id,
        channel=channel,
        session=session,
    )
    if delivery is None:
        delivery = NotificationDelivery(
            user_id=user_id,
            digest_batch_id=digest_batch_id,
            channel=channel,
        )
        session.add(delivery)

    delivery.status = status
    delivery.provider_message_id = provider_message_id
    delivery.error_code = error_code
    delivery.error_detail = error_detail
    delivery.sent_at = datetime.now(tz=timezone.utc) if status == "sent" else None
    return delivery


def dispatch_digest_notifications_for_batch(
    *,
    batch_id: int,
    push_sender=None,
    email_sender=None,
) -> dict[str, str | int]:
    with current_app.config.get("SESSION_MAKER").begin() as session_:
        batch = session_.scalar(
            select(QSLDigestBatch).where(QSLDigestBatch.id == batch_id)
        )
        if batch is None:
            raise ValueError(f"Digest batch {batch_id} does not exist.")
        user = batch.user
        preference = ensure_notification_preference(user=user, session=session_)
        recipient_email = _notification_recipient_email(
            user=user,
            preference=preference,
        )
        digest_url = _digest_url(batch=batch)
        digest_enabled = current_app.config.get("DIGEST_NOTIFICATIONS_ENABLED", True)
        web_push_enabled = current_app.config.get("WEB_PUSH_ENABLED", True)
        email_enabled = current_app.config.get("DIGEST_EMAIL_ENABLED", True)
        dry_run = current_app.config.get("DIGEST_DRY_RUN", False)

        if not digest_enabled:
            _upsert_delivery(
                user_id=user.id,
                digest_batch_id=batch.id,
                channel="web_push",
                status="skipped",
                session=session_,
                error_code="digest_disabled",
            )
            _upsert_delivery(
                user_id=user.id,
                digest_batch_id=batch.id,
                channel="email",
                status="skipped",
                session=session_,
                error_code="digest_disabled",
            )
            return {
                "batch_id": batch.id,
                "push_status": "skipped",
                "email_status": "skipped",
            }

        if batch.qsl_count <= 0:
            _upsert_delivery(
                user_id=user.id,
                digest_batch_id=batch.id,
                channel="web_push",
                status="skipped",
                session=session_,
                error_code="empty_digest",
            )
            _upsert_delivery(
                user_id=user.id,
                digest_batch_id=batch.id,
                channel="email",
                status="skipped",
                session=session_,
                error_code="empty_digest",
            )
            return {
                "batch_id": batch.id,
                "push_status": "skipped",
                "email_status": "skipped",
            }

        subscriptions = list(
            get_active_web_push_subscriptions(user_id=user.id, session=session_)
        )

        existing_push = get_delivery_for_batch_channel(
            user_id=user.id,
            digest_batch_id=batch.id,
            channel="web_push",
            session=session_,
        )
        push_status = "skipped"
        push_sent_count = 0
        if existing_push and existing_push.status == "sent":
            push_status = "sent"
            push_sent_count = 1
        elif not web_push_enabled:
            push_status = "skipped"
            _upsert_delivery(
                user_id=user.id,
                digest_batch_id=batch.id,
                channel="web_push",
                status="skipped",
                session=session_,
                error_code="web_push_disabled",
            )
        elif dry_run:
            push_status = "skipped"
            _upsert_delivery(
                user_id=user.id,
                digest_batch_id=batch.id,
                channel="web_push",
                status="skipped",
                session=session_,
                error_code="dry_run",
            )
        elif subscriptions:
            report = send_qsl_digest_web_push(
                user=user,
                batch=batch,
                subscriptions=subscriptions,
                digest_url=digest_url,
                send_callable=push_sender,
            )
            push_sent_count = report.sent
            push_status = "sent" if report.sent > 0 else "failed"
            _upsert_delivery(
                user_id=user.id,
                digest_batch_id=batch.id,
                channel="web_push",
                status=push_status,
                session=session_,
                error_code=None if report.sent > 0 else "push_failed",
                error_detail=None
                if report.sent > 0
                else ",".join(report.errors[-3:]) or "no_push_success",
            )
        else:
            push_status = "skipped"
            _upsert_delivery(
                user_id=user.id,
                digest_batch_id=batch.id,
                channel="web_push",
                status="skipped",
                session=session_,
                error_code="no_active_subscriptions",
            )

        email_needed = preference.fallback_to_email and push_sent_count == 0
        existing_email = get_delivery_for_batch_channel(
            user_id=user.id,
            digest_batch_id=batch.id,
            channel="email",
            session=session_,
        )
        email_status = "skipped"
        if existing_email and existing_email.status == "sent":
            email_status = "sent"
        elif not email_needed:
            email_status = "skipped"
            _upsert_delivery(
                user_id=user.id,
                digest_batch_id=batch.id,
                channel="email",
                status="skipped",
                session=session_,
                error_code="push_succeeded",
            )
        elif not email_enabled:
            email_status = "skipped"
            _upsert_delivery(
                user_id=user.id,
                digest_batch_id=batch.id,
                channel="email",
                status="skipped",
                session=session_,
                error_code="email_disabled",
            )
        elif dry_run:
            email_status = "skipped"
            _upsert_delivery(
                user_id=user.id,
                digest_batch_id=batch.id,
                channel="email",
                status="skipped",
                session=session_,
                error_code="dry_run",
            )
        elif email_needed:
            try:
                provider_message_id = send_qsl_digest_email(
                    user=user,
                    batch=batch,
                    digest_url=digest_url,
                    recipient_email=recipient_email,
                    send_callable=email_sender,
                )
                email_status = "sent"
                _upsert_delivery(
                    user_id=user.id,
                    digest_batch_id=batch.id,
                    channel="email",
                    status="sent",
                    session=session_,
                    provider_message_id=provider_message_id,
                )
            except Exception as error:  # noqa: BLE001
                email_status = "failed"
                _upsert_delivery(
                    user_id=user.id,
                    digest_batch_id=batch.id,
                    channel="email",
                    status="failed",
                    session=session_,
                    error_code="email_failed",
                    error_detail=str(error),
                )
        result = {
            "batch_id": batch.id,
            "push_status": push_status,
            "email_status": email_status,
        }
        current_app.logger.info(
            "Digest dispatch summary op=%s batch=%s result=%s",
            user.op,
            batch.id,
            result,
        )
        return result


def dispatch_pending_digest_notifications(*, limit: int = 100) -> dict[str, int]:
    if not current_app.config.get("DIGEST_NOTIFICATIONS_ENABLED", True):
        current_app.logger.info("Digest dispatch skipped: DIGEST_NOTIFICATIONS_ENABLED=0")
        return {"processed": 0, "sent": 0, "failed": 0, "skipped": 0}

    with current_app.config.get("SESSION_MAKER").begin() as session_:
        batch_ids = list(
            session_.scalars(
                select(QSLDigestBatch.id)
                .where(QSLDigestBatch.qsl_count > 0)
                .order_by(QSLDigestBatch.generated_at.asc())
                .limit(limit)
            )
        )

    sent = 0
    failed = 0
    skipped = 0
    for batch_id in batch_ids:
        try:
            result = dispatch_digest_notifications_for_batch(batch_id=batch_id)
            if result["push_status"] == "sent" or result["email_status"] == "sent":
                sent += 1
            elif result["push_status"] == "failed" and result["email_status"] == "failed":
                failed += 1
            else:
                skipped += 1
        except Exception:  # noqa: BLE001
            current_app.logger.exception(
                "Failed to dispatch notifications for digest batch %s", batch_id
            )
            failed += 1

    result = {
        "processed": len(batch_ids),
        "sent": sent,
        "failed": failed,
        "skipped": skipped,
    }
    current_app.logger.info("Digest pending dispatch summary: %s", result)
    return result
