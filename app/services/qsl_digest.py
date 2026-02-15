from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from flask import current_app
from sqlalchemy.orm import Session

from ..database.queries import (
    ensure_notification_preference,
    get_digest_batch,
    get_enabled_digest_users,
    get_qsls_for_digest_window,
)
from ..database.table_declarations import QSLDigestBatch, User
from .digest_eligibility import evaluate_digest_eligibility


@dataclass(frozen=True)
class DigestSchedule:
    digest_date: date
    window_start_utc: datetime
    window_end_utc: datetime
    timezone_name: str


def _resolve_timezone(tz_name: str | None) -> ZoneInfo:
    if not tz_name:
        return ZoneInfo("UTC")
    try:
        return ZoneInfo(tz_name)
    except ZoneInfoNotFoundError:
        return ZoneInfo("UTC")


def _digest_payload(batch: list) -> dict[str, object]:
    return {
        "qso_ids": [qso.id for qso in batch],
        "items": [
            {
                "qso_id": qso.id,
                "call": qso.call,
                "band": qso.band,
                "mode": qso.mode,
                "rxqsl_at": qso.app_lotw_rxqsl.isoformat()
                if qso.app_lotw_rxqsl
                else None,
            }
            for qso in batch
        ],
    }


def compute_digest_schedule(
    *,
    now_utc: datetime,
    timezone_name: str | None,
    digest_time_local: time,
    last_digest_cursor_at: datetime | None = None,
) -> DigestSchedule:
    tz = _resolve_timezone(timezone_name)
    local_now = now_utc.astimezone(tz=tz)

    scheduled_today = datetime.combine(
        local_now.date(),
        digest_time_local,
        tzinfo=tz,
    )
    if local_now >= scheduled_today:
        digest_date = local_now.date()
    else:
        digest_date = local_now.date() - timedelta(days=1)

    scheduled_local = datetime.combine(digest_date, digest_time_local, tzinfo=tz)
    window_end_utc = scheduled_local.astimezone(timezone.utc)
    default_window_start = window_end_utc - timedelta(days=1)

    if (
        last_digest_cursor_at
        and last_digest_cursor_at.tzinfo is not None
        and last_digest_cursor_at < window_end_utc
    ):
        window_start_utc = last_digest_cursor_at
    else:
        window_start_utc = default_window_start

    if window_start_utc >= window_end_utc:
        window_start_utc = default_window_start

    return DigestSchedule(
        digest_date=digest_date,
        window_start_utc=window_start_utc,
        window_end_utc=window_end_utc,
        timezone_name=getattr(tz, "key", "UTC"),
    )


def _upsert_digest_batch(
    *,
    user: User,
    schedule: DigestSchedule,
    session: Session,
) -> tuple[QSLDigestBatch, bool]:
    existing = get_digest_batch(
        user_id=user.id,
        digest_date=schedule.digest_date,
        session=session,
    )
    qso_rows = get_qsls_for_digest_window(
        user_id=user.id,
        window_start_utc=schedule.window_start_utc,
        window_end_utc=schedule.window_end_utc,
        session=session,
    )
    payload = _digest_payload(batch=list(qso_rows))

    if existing:
        existing.window_start_utc = schedule.window_start_utc
        existing.window_end_utc = schedule.window_end_utc
        existing.qsl_count = len(qso_rows)
        existing.payload_json = payload
        existing.generated_at = datetime.now(tz=timezone.utc)
        return existing, False

    created = QSLDigestBatch(
        user_id=user.id,
        digest_date=schedule.digest_date,
        window_start_utc=schedule.window_start_utc,
        window_end_utc=schedule.window_end_utc,
        qsl_count=len(qso_rows),
        payload_json=payload,
    )
    session.add(created)
    return created, True


def run_due_qsl_digest_generation(
    *,
    now_utc: datetime | None = None,
    limit: int | None = None,
) -> dict[str, int]:
    if not current_app.config.get("DIGEST_NOTIFICATIONS_ENABLED", True):
        current_app.logger.info("Digest generation skipped: DIGEST_NOTIFICATIONS_ENABLED=0")
        return {"created": 0, "updated": 0, "skipped": 0}

    now = now_utc or datetime.now(tz=timezone.utc)
    created = 0
    updated = 0
    skipped = 0

    with current_app.config.get("SESSION_MAKER").begin() as session_:
        users = list(get_enabled_digest_users(session=session_))
        if limit is not None:
            users = users[:limit]

        for user in users:
            preference = ensure_notification_preference(user=user, session=session_)
            eligibility = evaluate_digest_eligibility(
                user=user,
                preference=preference,
                now_utc=now,
            )
            if not eligibility.eligible:
                skipped += 1
                current_app.logger.info(
                    "Skipping digest generation for %s: %s",
                    user.op,
                    eligibility.reason,
                )
                continue

            schedule = compute_digest_schedule(
                now_utc=now,
                timezone_name=user.timezone,
                digest_time_local=preference.qsl_digest_time_local,
                last_digest_cursor_at=preference.last_digest_cursor_at,
            )
            if now < schedule.window_end_utc:
                skipped += 1
                continue

            _, was_created = _upsert_digest_batch(
                user=user,
                schedule=schedule,
                session=session_,
            )
            preference.last_digest_cursor_at = schedule.window_end_utc

            if was_created:
                created += 1
            else:
                updated += 1

    result = {
        "created": created,
        "updated": updated,
        "skipped": skipped,
    }
    current_app.logger.info("Digest generation summary: %s", result)
    return result
