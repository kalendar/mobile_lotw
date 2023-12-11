from datetime import datetime, timezone
from io import BytesIO

from adi_parser import parse_adi
from flask import current_app, redirect, session, url_for
from sqlalchemy.orm import Session

from ... import lotw
from ...database.queries import get_user, qso_report_exists
from ...database.table_declarations import QSOReport
from ...urls import QSOS_URL
from ..auth.wrappers import login_required
from .base import bp


@bp.get("/api/v1/import_qsos_data")
@login_required()
def import_qsos_data():
    with current_app.config.get("SESSION_MAKER").begin() as session_:
        session_: Session
        user = get_user(op=session.get("op"), session=session_)

        current_app.logger.info(f"Updating {user.op}'s QSOs")

        url = QSOS_URL.format(user.qso_reports_last_update.strftime("%Y-%m-%d"))

        current_app.logger.info(f"Getting {user.op}'s QSOs from LoTW")
        response = lotw.get(url=url)

        if "Page Request Limit!" in response.text:
            current_app.logger.warn(f"Page Request Limit for {user.op}!")
            return "LoTW page limit request hit.", 502

        current_app.logger.info(f"Got {user.op}'s QSOs from LoTW")
        bytes_io = BytesIO(response.content)

        current_app.logger.info(f"Parsing {user.op}'s QSOs")
        _, qso_reports = parse_adi(file=bytes_io)
        current_app.logger.info(f"Parsed {len(qso_reports)} QSOs for {user.op}")

        for qso_report in qso_reports:
            current_app.logger.info(
                f"Adding QSO {qso_report.country} for {user.op}"
            )

            report_exists = qso_report_exists(
                app_lotw_qso_timestamp=qso_report.app_lotw_qso_timestamp,
                session=session_,
            )

            current_app.logger.info(
                f"QSO {qso_report.country} {qso_report.app_lotw_qso_timestamp} {report_exists}"
            )

            if not user.has_imported or not report_exists:
                current_app.logger.info(
                    f"Adding QSO at {qso_report.app_lotw_qso_timestamp} for {user.op}"
                )
                user.qso_reports.append(
                    QSOReport(
                        user=user,
                        dataclass=qso_report,
                    )
                )

        user.qso_reports_last_update = datetime.now(tz=timezone.utc).date()
        user.qso_reports_last_update_time = datetime.now(tz=timezone.utc)
        user.has_imported = True

        session_.add(user)

        current_app.logger.info(f"Done Updating QSOs for {user.op}")

        return redirect(url_for("awards.qsls"))
