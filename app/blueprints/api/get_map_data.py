import json

from flask import current_app, jsonify, request, session, url_for
from sqlalchemy.orm import Session

from ...database.queries import (
    get_user,
    get_user_qsos_for_map_by_rxqso,
    get_user_qsos_for_map_by_rxqso_count,
)
from ..auth.wrappers import login_required
from .base import bp


@bp.get("/api/v1/get_map_data")
@login_required()
def get_map_data(as_json: bool = False):
    as_json = request.args.get("json", type=bool, default=False) or as_json

    with current_app.config.get("SESSION_MAKER").begin() as session_:
        session_: Session

        user = get_user(op=session.get("op"), session=session_)

        current_app.logger.info(f"Getting marker locations for {user.op}")

        count = get_user_qsos_for_map_by_rxqso_count(user=user, session=session_)

        if user.map_data_count == count:
            current_app.logger.info(f"Decoding marker locations for {user.op} from DB cache")
            marker_locations = user.map_data.decode("utf-8")
        else:
            user_qso_reports = get_user_qsos_for_map_by_rxqso(
                user=user,
                session=session_,
            )

            current_app.logger.info(f"Creating marker locations for {user.op}")
            marker_locations = {}
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

                report = f'<p>Worked: {call}</p><p>Band: {band}</p><p>Mode: {mode}</p><p>Date: {qso_timestamp}</p><a href="{url_for('awards.qsodetail', id=id)}">QSL Details</a>' # noqa

                if existing:
                    report = existing.get("report") + "<hr>" + report

                formatted_gridsquare = gridsquare
                if len(gridsquare) == 6:
                    formatted_gridsquare = (
                        formatted_gridsquare[:4] + formatted_gridsquare[-2:].lower()
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

            user.map_data = bytes(json.dumps(marker_locations), encoding="utf-8")
            user.map_data_count = len(user_qso_reports)

        current_app.logger.info(f"Done getting marker locations for {user.op}")

        if as_json:
            return jsonify(marker_locations)

        if isinstance(marker_locations, str):
            return marker_locations
        else:
            return json.dumps(marker_locations)
