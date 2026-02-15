from datetime import date

from flask import current_app, render_template, request, session
from sqlalchemy import select

from ...database.queries import get_digest_batch, get_user
from ...database.table_declarations import QSOReport
from ..auth.wrappers import login_required
from .base import bp


@bp.get("/qsl/digest")
@login_required(next_page="awards.qsl_digest")
def qsl_digest():
    date_input = request.args.get("date", type=str, default="")
    try:
        digest_date = (
            date.fromisoformat(date_input)
            if date_input
            else date.today()
        )
    except ValueError:
        digest_date = date.today()

    with current_app.config.get("SESSION_MAKER").begin() as session_:
        user = get_user(op=session.get("op"), session=session_)
        batch = get_digest_batch(
            user_id=user.id,
            digest_date=digest_date,
            session=session_,
        )

        qsls: list[QSOReport] = []
        if batch:
            qso_ids = list(dict.fromkeys(batch.payload_json.get("qso_ids", [])))
            if qso_ids:
                qso_rows = session_.scalars(
                    select(QSOReport).where(
                        QSOReport.user_id == user.id,
                        QSOReport.id.in_(qso_ids),
                    )
                ).all()
                qso_map = {qso.id: qso for qso in qso_rows}
                qsls = [qso_map[qso_id] for qso_id in qso_ids if qso_id in qso_map]

        return render_template(
            "qsl_digest.html",
            title=f"QSL Digest {digest_date.isoformat()}",
            digest_date=digest_date.isoformat(),
            batch=batch,
            qsls=qsls,
            user_op=user.op,
        )
