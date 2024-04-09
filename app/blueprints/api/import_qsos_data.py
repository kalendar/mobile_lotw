from datetime import datetime, timezone
from io import BytesIO
from itertools import batched

from adi_parser import parse_adi
from adi_parser.dataclasses import QSOReport as DCQSOReport
from flask import Response, current_app, redirect, session, url_for
from sqlalchemy.orm import Session

from ... import lotw
from ...database.queries import (
    get_qso_report_by_timestamp,
    get_user,
)
from ...database.table_declarations import QSOReport
from ...urls import QSOS_URL
from ..auth.wrappers import login_required
from .base import bp


@bp.get("/api/v1/import_qsos_data")
@login_required()
def import_qsos_data():
    user_op: str
    qso_reports_last_update: datetime
    has_imported: bool

    with current_app.config.get("SESSION_MAKER").begin() as session_:
        user = get_user(op=session.get("op"), session=session_)
        user_op = user.op
        qso_reports_last_update = user.qso_reports_last_update
        has_imported = user.has_imported

    current_app.logger.info(f"Updating {user_op}'s QSOs")

    url = QSOS_URL.format(qso_reports_last_update.strftime("%Y-%m-%d"))

    current_app.logger.info(f"Getting {user_op}'s QSOs from LoTW")
    response = lotw.get(url=url)

    if isinstance(response, Response):
        return response

    if "Page Request Limit!" in response.text:
        current_app.logger.warn(f"Page Request Limit for {user.op}!")
        return "LoTW page limit request hit.", 502

    current_app.logger.info(f"Got {user_op}'s QSOs from LoTW")
    adi_file = BytesIO(response.content)

    current_app.logger.info(f"Parsing {user_op}'s QSOs")
    _, qso_reports = parse_adi(file=adi_file)
    current_app.logger.info(f"Parsed {len(qso_reports)} QSOs for {user_op}")

    current_app.logger.info(f"Adding QSOs for {user_op} to DB")
    for qso_reports_subset in batched(qso_reports, 100):
        add_reports_to_db(qso_reports=qso_reports_subset, has_imported=has_imported)
    current_app.logger.info(f"Done Adding QSOs for {user_op} to DB")

    with current_app.config.get("SESSION_MAKER").begin() as session_:
        user = get_user(op=session.get("op"), session=session_)
        user.qso_reports_last_update = datetime.now(tz=timezone.utc).date()
        user.qso_reports_last_update_time = datetime.now(tz=timezone.utc)
        user.has_imported = True

    current_app.logger.info(f"Done Updating QSOs for {user_op}")

    return redirect(url_for("awards.qsls"))


def add_reports_to_db(qso_reports: list[DCQSOReport], has_imported: bool) -> None:
    with current_app.config.get("SESSION_MAKER").begin() as session_:
        session_: Session

        user = get_user(op=session.get("op"), session=session_)
        for qso_report in qso_reports:
            report = None

            if has_imported:
                report = get_qso_report_by_timestamp(
                    app_lotw_qso_timestamp=qso_report.app_lotw_qso_timestamp,
                    call=qso_report.call,
                    session=session_,
                )

            if not report:
                current_app.logger.debug(
                    f"Adding QSO at {qso_report.app_lotw_qso_timestamp} for {user.op} to DB"
                )

                session_.add(
                    QSOReport(
                        user=user,
                        dataclass=qso_report,
                    )
                )
                continue

            mutated = (
                report.app_lotw_rxqso != qso_report.app_lotw_rxqso
                or report.app_lotw_rxqsl != qso_report.app_lotw_rxqsl
            )
            if mutated:
                report.app_lotw_rxqso = qso_report.app_lotw_rxqso
                report.app_lotw_rxqsl = qso_report.app_lotw_rxqsl
