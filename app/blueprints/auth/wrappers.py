from functools import wraps

from flask import flash, redirect, session, url_for


def login_required(next_page: str = "dxcc"):
    def decorator(view):
        @wraps(view)
        def decorated_view(*args, **kwargs):
            # If the user is not logged in
            if not session.get("logged_in"):
                # Request login
                flash("Please login.", "info")
                return redirect(url_for("auth.login", next_page=next_page))
            # Else, move forward
            return view(*args, **kwargs)

        return decorated_view

    return decorator
