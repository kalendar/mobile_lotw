from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

from flask import current_app, session
from requests import RequestException
from requests import Response as RResponse
from requests import get as r_get
from requests import post as r_post

from .database.queries import get_user


class LotwAuthExpiredError(RuntimeError):
    pass


class LotwTransientError(RuntimeError):
    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


def _record_lotw_success(op: str) -> None:
    with current_app.config.get("SESSION_MAKER").begin() as session_:
        try:
            user = get_user(op=op, session=session_)
        except ValueError:
            return
        user.lotw_last_ok_at = datetime.now(tz=timezone.utc)
        user.lotw_fail_count = 0
        user.lotw_auth_state = "ok"
        user.lotw_last_fail_reason = None
    current_app.logger.info("LoTW health update op=%s state=ok fail_count=0", op)


def _record_lotw_failure(
    op: str,
    reason: str,
    *,
    auth_expired: bool = False,
) -> None:
    with current_app.config.get("SESSION_MAKER").begin() as session_:
        try:
            user = get_user(op=op, session=session_)
        except ValueError:
            return
        user.lotw_last_fail_at = datetime.now(tz=timezone.utc)
        user.lotw_fail_count = (user.lotw_fail_count or 0) + 1
        user.lotw_auth_state = "auth_expired" if auth_expired else "transient_error"
        user.lotw_last_fail_reason = reason
        fail_count = user.lotw_fail_count
    current_app.logger.warning(
        "LoTW health update op=%s state=%s fail_count=%s reason=%s",
        op,
        "auth_expired" if auth_expired else "transient_error",
        fail_count,
        reason,
    )


def _resolve_op(op: str | None) -> str:
    active_op = op or session.get("op")
    if not active_op:
        raise LotwAuthExpiredError("Missing local auth session.")
    return active_op


def _get_lotw_cookies(op: str) -> dict[str, str]:
    with current_app.config.get("SESSION_MAKER").begin() as session_:
        try:
            user = get_user(op=op, session=session_)
        except ValueError as error:
            raise LotwAuthExpiredError("Local user session is no longer valid.") from error
        cookies = user.lotw_cookies

    if not cookies:
        _record_lotw_failure(
            op=op,
            reason="missing_lotw_cookies",
            auth_expired=True,
        )
        raise LotwAuthExpiredError("No LoTW cookies are stored for this user.")
    return cookies


def _is_lotw_auth_expired(response: RResponse) -> bool:
    if response.status_code in {401, 403}:
        return True
    return not is_valid_response(response=response)


def _request_timeout_seconds() -> int:
    return current_app.config.get("LOTW_REQUEST_TIMEOUT_SECONDS", 20)


def _raise_for_non_success_status(response: RResponse, op: str) -> None:
    if response.status_code == 429:
        _record_lotw_failure(op=op, reason="http_429", auth_expired=False)
        raise LotwTransientError(
            "LoTW request limit reached.",
            status_code=429,
        )
    if response.status_code >= 500:
        _record_lotw_failure(
            op=op,
            reason=f"http_{response.status_code}",
            auth_expired=False,
        )
        raise LotwTransientError(
            f"LoTW responded with {response.status_code}.",
            status_code=502,
        )
    if response.status_code != 200:
        _record_lotw_failure(
            op=op,
            reason=f"http_{response.status_code}",
            auth_expired=False,
        )
        raise LotwTransientError(
            f"Unexpected LoTW status code {response.status_code}.",
            status_code=502,
        )


def get(url: str, op: str | None = None) -> RResponse:
    active_op = _resolve_op(op=op)
    cookies = _get_lotw_cookies(op=active_op)

    try:
        response = r_get(
            url=url,
            cookies=cookies,
            timeout=_request_timeout_seconds(),
        )
    except RequestException as error:
        _record_lotw_failure(op=active_op, reason="request_exception")
        raise LotwTransientError("Failed request to LoTW.") from error

    if _is_lotw_auth_expired(response=response):
        _record_lotw_failure(
            op=active_op,
            reason="auth_expired",
            auth_expired=True,
        )
        raise LotwAuthExpiredError("LoTW session is no longer authenticated.")

    _raise_for_non_success_status(response=response, op=active_op)
    _record_lotw_success(op=active_op)

    return response


def post(url: str, data: dict, op: str | None = None) -> RResponse:
    active_op = _resolve_op(op=op)
    cookies = _get_lotw_cookies(op=active_op)

    try:
        response = r_post(
            url=url,
            data=data,
            cookies=cookies,
            timeout=_request_timeout_seconds(),
        )
    except RequestException as error:
        _record_lotw_failure(op=active_op, reason="request_exception")
        raise LotwTransientError("Failed request to LoTW.") from error

    if _is_lotw_auth_expired(response=response):
        _record_lotw_failure(
            op=active_op,
            reason="auth_expired",
            auth_expired=True,
        )
        raise LotwAuthExpiredError("LoTW session is no longer authenticated.")

    _raise_for_non_success_status(response=response, op=active_op)
    _record_lotw_success(op=active_op)

    return response


def is_valid_response(response: RResponse) -> bool:
    if not response:
        return False

    text_response = (
        response.text if response.text else str(response.content, encoding="utf8")
    )

    return "postcard" not in text_response


def get_multiple(urls: list[str], op: str | None = None) -> dict[str, RResponse]:
    """Fetch multiple URLs concurrently.

    Args:
        urls: List of URLs to fetch
        op: Optional operator callsign

    Returns:
        Dict mapping URL -> response (only includes successful responses)
    """
    active_op = _resolve_op(op=op)
    cookies = _get_lotw_cookies(op=active_op)

    def fetch_url(url: str) -> tuple[str, RResponse | None, bool]:
        try:
            response = r_get(
                url=url,
                cookies=cookies,
                timeout=_request_timeout_seconds(),
            )
            if _is_lotw_auth_expired(response=response):
                return url, None, True
            if response.status_code == 200 and is_valid_response(response=response):
                return url, response, False
        except RequestException:
            pass
        return url, None, False

    results = {}
    saw_auth_expired = False
    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = {executor.submit(fetch_url, url): url for url in urls}
        for future in as_completed(futures):
            url, response, auth_expired = future.result()
            if auth_expired:
                saw_auth_expired = True
            if response is not None:
                results[url] = response

    if saw_auth_expired:
        _record_lotw_failure(
            op=active_op,
            reason="auth_expired",
            auth_expired=True,
        )
        raise LotwAuthExpiredError("LoTW session is no longer authenticated.")

    if results:
        _record_lotw_success(op=active_op)
    else:
        _record_lotw_failure(
            op=active_op,
            reason="concurrent_fetch_failed",
            auth_expired=False,
        )

    return results
