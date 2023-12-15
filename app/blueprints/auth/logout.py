from flask import (
    make_response,
    redirect,
    session,
    url_for,
)

from .base import bp


@bp.get("/logout")
def logout():
    # Remove relevant objects from session
    session.clear()

    # Remove op cookie and redirect home
    response = make_response(redirect(url_for("home")))
    response.delete_cookie("op")

    return response
