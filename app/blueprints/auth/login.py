from datetime import datetime, timedelta

from flask import (
    current_app,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from requests import post
from requests.utils import dict_from_cookiejar

from ... import lotw
from ...database.queries import ensure_user
from ...urls import LOGIN_URL
from .base import bp


@bp.route(
    "/login",
    methods=["POST", "GET"],
)
def login():
    # If the user is attempting to login
    if request.method == "POST":
        # Create a payload for LOTW
        lotw_payload = {
            "login": request.form.get("login").strip().lower(),
            "password": request.form.get("password").strip(),
            "acct_sel": "",
            "thisForm": "login",
        }

        # Post to LOTW and save response
        login_response = post(url=LOGIN_URL, data=lotw_payload)

        # Check if login failed
        if not lotw.is_valid_response(response=login_response):
            flash("LoTW login unsuccessful! Please try again.", "error")

            # Refresh & preserve URI argument(s) if present
            return redirect(url_for("auth.login", **request.args))

        # Login successful
        op = request.form.get("login").strip().lower()

        # Mark session as logged_in
        session.update({"logged_in": True, "op": op})

        response = redirect(
            url_for(request.args.get("next_page") or "awards.qsls")
        )
        # Set cookies for following requests
        response.set_cookie(
            key="op",
            value=op,
            expires=datetime.now() + timedelta(days=365),
        )

        # Make sure the user exists on our side
        with current_app.config.get("SESSION_MAKER").begin() as session_:
            user = ensure_user(op=op, session=session_)

            user.lotw_cookies = dict_from_cookiejar(login_response.cookies)

            session_.add(user)

            if not user.has_imported:
                return render_template("import_qsos_data.html")

        return response

    # If not logging in
    else:
        # If known user, redirect to next_page or awards.qsls
        # Preserves URI arguments
        if session.get("op"):
            return redirect(
                url_for(
                    request.args.get("next_page") or "awards.qsls",
                    **request.args,
                )
            )

        # If not web_session, render login template
        # Does not preserve URI
        else:
            return render_template("login.html", title="Login to Mobile LotW")
