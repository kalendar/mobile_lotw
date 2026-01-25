from concurrent.futures import ThreadPoolExecutor, as_completed

from flask import Response, current_app, flash, redirect, session, url_for
from requests import Response as RResponse
from requests import get as r_get
from requests import post as r_post

from .database.queries import get_user


def get(url: str, op: str | None = None) -> RResponse | Response:
    if not op:
        op: str | None = session.get("op")

    if op is None:
        flash("LoTW Login has Expired! Please re-log.")
        return redirect(url_for("auth.logout"))

    with current_app.config.get("SESSION_MAKER").begin() as session_:
        user = get_user(op=op, session=session_)

        response = r_get(url=url, cookies=user.lotw_cookies)

        if not is_valid_response(response=response) or not response.status_code == 200:
            flash("LoTW Login has Expired! Please re-log.")
            return redirect(url_for("auth.logout"))

        return response


def post(url: str, data: dict, op: str | None = None) -> RResponse | Response | None:
    if not op:
        op: str = session.get("op")

    if not op:
        flash("LoTW Login has Expired! Please re-log.")
        return redirect(url_for("auth.logout"))

    with current_app.config.get("SESSION_MAKER").begin() as session_:
        user = get_user(op=op, session=session_)

        response = r_post(url=url, data=data, cookies=user.lotw_cookies)

        if not is_valid_response(response=response):
            flash("LoTW Login has Expired! Please re-log.")
            return redirect(url_for("auth.logout"))

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
    if not op:
        op = session.get("op")

    if op is None:
        flash("LoTW Login has Expired! Please re-log.")
        return {}

    with current_app.config.get("SESSION_MAKER").begin() as session_:
        user = get_user(op=op, session=session_)
        cookies = user.lotw_cookies

    def fetch_url(url: str) -> tuple[str, RResponse | None]:
        try:
            response = r_get(url=url, cookies=cookies)
            if is_valid_response(response) and response.status_code == 200:
                return url, response
        except Exception:
            pass
        return url, None

    results = {}
    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = {executor.submit(fetch_url, url): url for url in urls}
        for future in as_completed(futures):
            url, response = future.result()
            if response is not None:
                results[url] = response

    return results
