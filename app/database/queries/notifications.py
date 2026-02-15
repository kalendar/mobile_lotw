from datetime import date, datetime, timezone
from typing import Sequence

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from ..table_declarations import (
    NotificationDelivery,
    NotificationPreference,
    QSLDigestBatch,
    QSOReport,
    User,
    WebPushSubscription,
)


def ensure_notification_preference(
    user: User, session: Session
) -> NotificationPreference:
    preference = session.scalar(
        select(NotificationPreference).where(
            NotificationPreference.user_id == user.id
        )
    )
    if preference:
        return preference

    preference = NotificationPreference(user_id=user.id)
    session.add(preference)
    return preference


def get_notification_preference(
    user_id: int, session: Session
) -> NotificationPreference | None:
    return session.scalar(
        select(NotificationPreference).where(NotificationPreference.user_id == user_id)
    )


def get_active_web_push_subscriptions(
    user_id: int, session: Session
) -> Sequence[WebPushSubscription]:
    return session.scalars(
        select(WebPushSubscription)
        .where(
            and_(
                WebPushSubscription.user_id == user_id,
                WebPushSubscription.status == "active",
            )
        )
        .order_by(WebPushSubscription.id.asc())
    ).all()


def get_qsls_for_digest_window(
    user_id: int,
    window_start_utc: datetime,
    window_end_utc: datetime,
    session: Session,
) -> Sequence[QSOReport]:
    return session.scalars(
        select(QSOReport)
        .where(
            and_(
                QSOReport.user_id == user_id,
                QSOReport.app_lotw_rxqsl.isnot(None),
                QSOReport.app_lotw_rxqsl > window_start_utc,
                QSOReport.app_lotw_rxqsl <= window_end_utc,
            )
        )
        .order_by(QSOReport.app_lotw_rxqsl.desc(), QSOReport.id.desc())
    ).all()


def get_digest_batch(
    user_id: int, digest_date: date, session: Session
) -> QSLDigestBatch | None:
    return session.scalar(
        select(QSLDigestBatch).where(
            and_(
                QSLDigestBatch.user_id == user_id,
                QSLDigestBatch.digest_date == digest_date,
            )
        )
    )


def get_delivery_for_batch_channel(
    *,
    user_id: int,
    digest_batch_id: int | None,
    channel: str,
    session: Session,
) -> NotificationDelivery | None:
    if digest_batch_id is None:
        return session.scalar(
            select(NotificationDelivery).where(
                and_(
                    NotificationDelivery.user_id == user_id,
                    NotificationDelivery.digest_batch_id.is_(None),
                    NotificationDelivery.channel == channel,
                )
            )
        )

    return session.scalar(
        select(NotificationDelivery).where(
            and_(
                NotificationDelivery.user_id == user_id,
                NotificationDelivery.digest_batch_id == digest_batch_id,
                NotificationDelivery.channel == channel,
            )
        )
    )


def get_enabled_digest_users(session: Session) -> Sequence[User]:
    now_utc = datetime.now(tz=timezone.utc)
    return session.scalars(
        select(User)
        .join(NotificationPreference, NotificationPreference.user_id == User.id)
        .where(NotificationPreference.qsl_digest_enabled.is_(True))
        .where(
            or_(
                User.subscription_status.in_(["active", "trialing"]),
                User.entitlement_expires_at > now_utc,
            )
        )
    ).all()
