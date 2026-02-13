from secrets import token_urlsafe

from flask import (
    current_app,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from requests import RequestException, post
from requests.utils import dict_from_cookiejar

from ... import lotw
from ...database.queries import ensure_user
from ...urls import LOGIN_URL
from .base import bp
from .wrappers import sanitize_next_page


def _issue_login_csrf_token() -> str:
    token = token_urlsafe(32)
    session["login_csrf_token"] = token
    return token


@bp.route(
    "/login",
    methods=["POST", "GET"],
)
def login():
    # If the user is attempting to login
    if request.method == "POST":
        csrf_token = request.form.get("csrf_token", type=str, default="")
        if not csrf_token or csrf_token != session.get("login_csrf_token"):
            flash("Login session expired. Please try again.", "error")
            _issue_login_csrf_token()
            return redirect(url_for("auth.login", **request.args))

        login_input = request.form.get("login", type=str, default="").strip().lower()
        password = request.form.get("password", type=str, default="").strip()
        if not login_input or not password:
            flash("Callsign and password are both required.", "error")
            _issue_login_csrf_token()
            return redirect(url_for("auth.login", **request.args))

        # Create a payload for LOTW
        lotw_payload = {
            "login": login_input,
            "password": password,
            "acct_sel": "",
            "thisForm": "login",
        }

        # Post to LOTW and save response
        try:
            login_response = post(
                url=LOGIN_URL,
                data=lotw_payload,
                timeout=current_app.config.get("LOTW_REQUEST_TIMEOUT_SECONDS", 20),
            )
        except RequestException:
            flash("LoTW is temporarily unavailable. Please try again.", "error")
            _issue_login_csrf_token()
            return redirect(url_for("auth.login", **request.args))

        # Check if login failed
        if not lotw.is_valid_response(response=login_response):
            flash("LoTW login unsuccessful! Please try again.", "error")
            _issue_login_csrf_token()

            # Refresh & preserve URI argument(s) if present
            return redirect(url_for("auth.login", **request.args))

        # Login successful
        op = login_input

        # Mark session as logged_in
        session.clear()
        session.permanent = True
        session.update(
            {
                "logged_in": True,
                "op": op,
                "login_csrf_token": token_urlsafe(32),
            }
        )

        next_page = sanitize_next_page(
            next_page=request.args.get("next_page"),
            default="awards.qsls",
        )
        response = redirect(url_for(next_page))

        # Make sure the user exists on our side
        with current_app.config.get("SESSION_MAKER").begin() as session_:
            user = ensure_user(op=op, session=session_)

            user.lotw_cookies = dict_from_cookiejar(login_response.cookies)

            session_.add(user)

            if not user.has_imported:
                flash('Due to a recent server upgrade, QSOs need to be re-imported.')
                return render_template("import_qsos_data.html")

        return response

    # If not logging in
    else:
        # If known user, redirect to next_page or awards.qsls
        # Preserves URI arguments
        if session.get("logged_in") and session.get("op"):
            next_page = sanitize_next_page(
                next_page=request.args.get("next_page"),
                default="awards.qsls",
            )
            return redirect(
                url_for(
                    next_page,
                    **request.args,
                )
            )

        # If not web_session, render login template
        # Does not preserve URI
        else:
            return render_template(
                "login.html",
                title="Login to Mobile LotW",
                csrf_token=_issue_login_csrf_token(),
            )
