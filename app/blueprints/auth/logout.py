from flask import (
    g,
    make_response,
    redirect,
    session,
    url_for,
)

from .base import bp


@bp.get("/logout")
def logout():
    session.pop("web_session_cookies", None)
    session.pop("logged_in", None)

    if g.get("web_session"):
        g.web_session.cookies.clear()

    g.web_session = None

    resp = make_response(redirect(url_for("home")))
    resp.delete_cookie("op")

    return resp
