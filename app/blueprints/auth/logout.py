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
    # Remove relevant objects from session
    session.pop("web_session_cookies", None)
    session.pop("logged_in", None)

    # Teardown g session
    g.web_session = None

    # Remove op cookie and redirect home
    response = make_response(redirect(url_for("home")))
    response.delete_cookie("op")

    return response
