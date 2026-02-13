from flask import (
    redirect,
    session,
    url_for,
)

from .base import bp


@bp.get("/logout")
def logout():
    # Remove relevant objects from session
    session.clear()

    # Redirect to login
    return redirect(url_for("auth.login"))
