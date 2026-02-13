import json
from html import escape

from flask import current_app, jsonify, request, session, url_for
from sqlalchemy.orm import Session

from ...database.queries import (
    get_user,
    get_user_qsos_for_map_by_rxqso,
    get_user_qsos_for_map_by_rxqso_count,
)
from ..auth.wrappers import login_required, paid_required
from .base import bp


@bp.get("/api/v1/get_map_data")
@login_required()
@paid_required()
def get_map_data(as_json: bool = False):
    as_json = request.args.get("json", type=bool, default=False) or as_json
    force_reload = request.args.get("force_reload", type=bool, default=False)

    with current_app.config.get("SESSION_MAKER").begin() as session_:
        session_: Session

        user = get_user(op=session.get("op"), session=session_)

        current_app.logger.info(f"Getting marker locations for {user.op}")

        count = get_user_qsos_for_map_by_rxqso_count(
            user=user, session=session_
        )

        marker_locations: dict[str, dict[str, str | float]] = {}

        if (
            user.map_data_count == count
            and not force_reload
            and user.map_data is not None
        ):
            current_app.logger.info(
                f"Decoding marker locations for {user.op} from DB cache"
            )
            try:
                marker_locations = json.loads(user.map_data.decode("utf-8"))
            except Exception:
                marker_locations = {}

        if not marker_locations:
            user_qso_reports = get_user_qsos_for_map_by_rxqso(
                user=user,
                session=session_,
            )

            current_app.logger.info(f"Creating marker locations for {user.op}")
            for (
                id,
                gridsquare,
                latitude,
                longitude,
                call,
                band,
                mode,
                qso_timestamp,
                ) in user_qso_reports:
                existing = marker_locations.get(gridsquare)

                safe_call = escape(str(call or ""))
                safe_band = escape(str(band or ""))
                safe_mode = escape(str(mode or ""))
                safe_timestamp = escape(str(qso_timestamp or ""))
                details_href = url_for("awards.qsodetail", id=id)

                report = (
                    f"<p>Worked: {safe_call}</p>"
                    f"<p>Band: {safe_band}</p>"
                    f"<p>Mode: {safe_mode}</p>"
                    f"<p>Date: {safe_timestamp}</p>"
                    f'<a href="{details_href}">QSL Details</a>'
                )

                if existing:
                    report = existing.get("report") + "<hr>" + report

                formatted_gridsquare = gridsquare
                if len(gridsquare) == 6:
                    formatted_gridsquare = (
                        formatted_gridsquare[:4]
                        + formatted_gridsquare[-2:].lower()
                    )

                marker_locations.update(
                    {
                        gridsquare: {
                            "report": report,
                            "lat": latitude,
                            "long": longitude,
                            "gridsquare": formatted_gridsquare,
                        }
                    }
                )
            current_app.logger.info(f"Created marker locations for {user.op}")

            user.map_data = bytes(
                json.dumps(marker_locations), encoding="utf-8"
            )
            user.map_data_count = len(user_qso_reports)

        current_app.logger.info(f"Done getting marker locations for {user.op}")

        if as_json:
            return jsonify(marker_locations)
        return json.dumps(marker_locations)
