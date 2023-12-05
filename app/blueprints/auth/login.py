from datetime import datetime, timedelta

from flask import (
    flash,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from requests import post
from requests.utils import dict_from_cookiejar

from ...urls import LOGIN_URL
from .base import bp


@bp.route(
    "/login/",
    methods=["POST", "GET"],
)
def login():
    # If the user is attempting to login
    if request.method == "POST":
        # Create a payload for LOTW
        lotw_payload = {
            "login": request.form.get("login").strip(),
            "password": request.form.get("password").strip(),
            "acct_sel": "",
            "thisForm": "login",
        }

        # Post to LOTW and save response
        login_response = post(url=LOGIN_URL, data=lotw_payload)

        # Check if login failed
        if "postcard" in login_response.text:
            flash("LOTW login unsuccessful! Please try again.", "error")

            # Refresh & preserve URI argument(s) if present
            return redirect(
                url_for(
                    "auth.login",
                    **request.args,
                )
            )

        # Login successful
        else:
            # Add cookies to session, mark session as logged_in
            session.update(
                {
                    "web_session_cookies": dict_from_cookiejar(
                        login_response.cookies
                    ),
                    "logged_in": True,
                }
            )

            expiration_date = datetime.now() + timedelta(days=365)

            # Go to next_page if argument present, default to awards.dxcc
            response = redirect(
                url_for(request.args.get("next_page") or "awards.dxcc")
            )

            # Set cookies for following LOTW requests
            response.set_cookie(
                key="op",
                value=request.form.get("login").lower(),
                expires=expiration_date,
            )

            return response

    # If not logging in
    else:
        # If web_session already exists, redirect to next_page or awards.dxcc
        # Preserves URI arguments
        if g.get("web_session"):
            return redirect(
                url_for(
                    request.args.get("next_page") or "awards.dxcc",
                    **request.args,
                )
            )

        # If not web_session, render login template
        else:
            return render_template(
                "login.html",
                title="Login to Mobile LotW",
            )
