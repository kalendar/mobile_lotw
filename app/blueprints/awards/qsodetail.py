from flask import current_app, render_template, session
from sqlalchemy.orm import Session

from ...database.queries import get_object, get_user
from ...database.table_declarations import QSOReport
from ..auth.wrappers import login_required
from .base import bp


@bp.get("/qsodetail/<int:id>")
@login_required(next_page="qsls")
def qsodetail(id: int):
    with current_app.config.get("SESSION_MAKER").begin() as session_:
        session_: Session

        user = get_user(op=session.get("op"), session=session_)
        qso_report = get_object(type_=QSOReport, id=id, session=session_)

        if qso_report and qso_report.user == user:
            return render_template(
                "qsl_details.html",
                qso_report=qso_report,
                title="QSL Details",
            )
