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
        return redirect(url_for("auth.login"))

    with current_app.config.get("SESSION_MAKER").begin() as session_:
        user = get_user(op=op, session=session_)

        response = r_get(url=url, cookies=user.lotw_cookies)

        if not is_valid_response(response=response) or not response.status_code == 200:
            flash("LoTW Login has Expired! Please re-log.")
            return redirect(url_for("auth.login"))

        return response


def post(url: str, data: dict, op: str | None = None) -> RResponse | Response | None:
    if not op:
        op: str = session.get("op")

    if not op:
        flash("LoTW Login has Expired! Please re-log.")
        return redirect(url_for("auth.login"))

    with current_app.config.get("SESSION_MAKER").begin() as session_:
        user = get_user(op=op, session=session_)

        response = r_post(url=url, data=data, cookies=user.lotw_cookies)

        if not is_valid_response(response=response):
            flash("LoTW Login has Expired! Please re-log.")
            return redirect(url_for("auth.login"))

        return response


def is_valid_response(response: Response) -> bool:
    return response and "postcard" not in response.text
