from flask import current_app, render_template, request, session
from sqlalchemy.orm import Session

from ...database.queries import callsign as search_callsign
from ...database.queries import get_user
from ...database.table_declarations import QSOReport
from ..auth.wrappers import login_required
from .base import bp


@bp.route("/search/callsign", methods=["POST", "GET"])
@login_required("search.callsign")
def callsign():
    qsls: list[QSOReport] = None
    query: str = ""
    if request.method == "POST":
        query = request.form.get("query", type=str, default="")
        with current_app.config.get("SESSION_MAKER").begin() as session_:
            session_: Session

            user = get_user(op=session.get("op"), session=session_)
            qsls = search_callsign(user=user, query=query, session=session_)
            session_.expunge_all()

    return render_template(
        "search.html",
        search_type="Callsign",
        endpoint="search.callsign",
        query=query,
        qsls=qsls,
    )
