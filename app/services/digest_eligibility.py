from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from ..database.table_declarations import NotificationPreference, User


@dataclass(frozen=True)
class DigestEligibility:
    eligible: bool
    reason: str
    retry_at: datetime | None = None


def _transient_backoff_seconds(fail_count: int) -> int:
    # Start at 5 minutes, exponential backoff up to 24 hours.
    safe_fail_count = max(1, fail_count)
    return min(300 * (2 ** (safe_fail_count - 1)), 86_400)


def evaluate_digest_eligibility(
    *,
    user: User,
    preference: NotificationPreference | None,
    now_utc: datetime | None = None,
    require_paid_entitlement: bool = True,
) -> DigestEligibility:
    now = now_utc or datetime.now(tz=timezone.utc)

    if preference is None:
        return DigestEligibility(eligible=False, reason="missing_preference")
    if not preference.qsl_digest_enabled:
        return DigestEligibility(eligible=False, reason="digest_disabled")

    if require_paid_entitlement and not user.has_active_entitlement:
        return DigestEligibility(eligible=False, reason="inactive_entitlement")

    state = (user.lotw_auth_state or "unknown").lower()
    if state in {"auth_expired", "missing_cookies"}:
        return DigestEligibility(eligible=False, reason="lotw_auth_expired")

    if state == "transient_error":
        fail_count = user.lotw_fail_count or 0
        if fail_count <= 0 or not user.lotw_last_fail_at:
            return DigestEligibility(eligible=False, reason="lotw_transient_error")
        retry_at = user.lotw_last_fail_at + timedelta(
            seconds=_transient_backoff_seconds(fail_count)
        )
        if retry_at > now:
            return DigestEligibility(
                eligible=False,
                reason="lotw_transient_backoff",
                retry_at=retry_at,
            )

    if not user.lotw_cookies_b:
        return DigestEligibility(eligible=False, reason="lotw_auth_missing")

    return DigestEligibility(eligible=True, reason="eligible")
