from datetime import datetime, timezone

from flask import current_app, g, request, session

from .dataclasses import AwardsDetail, TripleDetail
from .parser import parse_award


def is_expired(datetime_obj: datetime | None) -> bool:
    if not datetime_obj:
        return True

    time_delta = datetime.now(timezone.utc) - datetime_obj
    minutes_passed = time_delta.seconds / 60

    return minutes_passed > current_app.config.get("SESSION_CACHE_EXPIRATION")


def get_award_details(
    award: str,
) -> tuple[list[AwardsDetail] | list[TripleDetail], datetime]:
    # Attempt to retrieve cached award from cookies
    award_details: list[AwardsDetail] | None = session.get(
        f"{award}_details", default=None
    )
    award_parsed_at: datetime = session.get(f"{award}_parsed_at", default=None)

    force_reload: bool = request.args.get(
        "force_reload", type=bool, default=False
    )

    # If a reload is requested, or data expired/missing
    if force_reload or is_expired(award_parsed_at) or not award_details:
        # Get it and cache it
        award_details = parse_award(award=award)
        award_parsed_at = datetime.now(timezone.utc)
        session.update(
            {
                f"{award}_details": award_details,
                f"{award}_parsed_at": award_parsed_at,
            }
        )

    return award_details, award_parsed_at
