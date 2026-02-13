from datetime import datetime, timezone

from cachetools import TTLCache
from flask import current_app, request, session

from .dataclasses import AwardsDetail, TripleDetail
from .parser import parse_award

# Server-side cache with 30-minute TTL (1800 seconds)
# maxsize=1000 allows caching for ~166 users * 6 awards each
_award_cache: TTLCache = TTLCache(maxsize=1000, ttl=1800)


def is_expired(
    datetime_obj: datetime | None,
    expiration_time: int,
) -> bool:
    # If there is no known parse time
    if not datetime_obj:
        return True

    time_delta = datetime.now(tz=timezone.utc) - datetime_obj
    minutes_passed = time_delta.total_seconds() / 60

    return minutes_passed > expiration_time


def get_award_details(
    award: str,
) -> tuple[list[AwardsDetail] | list[TripleDetail], datetime]:
    """Get the cached, or parsed, information about an award. Retrieves new
    information if the cache is expired.

    Args:
        award (str): The generic name of the award, like "dxcc" or "was"

    Returns:
        tuple[list[AwardsDetail] | list[TripleDetail], datetime]: Returns either
        a list of award details, or triple details as the first argument, and
        the time it was parsed as the second argument.
    """
    op = session.get("op")
    cache_key = f"{op}:{award}"

    force_reload: bool = request.args.get("force_reload", type=bool, default=False)

    # Check server-side cache first (unless force reload)
    if not force_reload and cache_key in _award_cache:
        return _award_cache[cache_key]

    # Fetch and parse award data
    award_details = parse_award(award=award)
    award_parsed_at = datetime.now(timezone.utc)

    # Store in server-side cache
    _award_cache[cache_key] = (award_details, award_parsed_at)

    return award_details, award_parsed_at
