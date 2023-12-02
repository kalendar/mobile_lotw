from functools import wraps

from flask import flash, redirect, session, url_for


def login_required(next_page: str = "dxcc"):
    def decorator(view):
        @wraps(view)
        def decorated_view(*args, **kwargs):
            if not session.get("logged_in"):
                flash("Please login.", "info")
                return redirect(url_for("auth.login", next_page=next_page))
            return view(*args, **kwargs)

        return decorated_view

    return decorator
