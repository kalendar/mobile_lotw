from flask import (
    current_app,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from sqlalchemy.orm import Session

from ...database.queries import get_object, get_user
from ...database.table_declarations import QSOReport
from ...parser import qsodetail as parse_qsodetail
from ..auth.wrappers import login_required
from .base import bp


@bp.get("/qsodetail")
@login_required(next_page="qsls")
def qsodetail():
    qso_db_id = request.args.get("id", default=None, type=int)

    # If trying to access something not in the db, fallback to calling lotw
    if not qso_db_id:
        qsl_detail = parse_qsodetail()

        return render_template(
            "qsl_details_lotw.html",
            qsl_detail=qsl_detail,
            title="QSL Details",
        )

    with current_app.config.get("SESSION_MAKER").begin() as session_:
        session_: Session

        user = get_user(op=session.get("op"), session=session_)
        qso_report = get_object(type_=QSOReport, id=qso_db_id, session=session_)

        if qso_report and qso_report.user == user:
            return render_template(
                "qsl_details_db.html",
                qso_report=qso_report,
                title="QSL Details",
            )
        else:
            # No access
            return redirect(url_for("qsls"))
