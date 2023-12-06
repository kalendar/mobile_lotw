import json

from adi_parser import parse_adi
from flask import render_template
from flask.blueprints import Blueprint

bp = Blueprint(name="map", import_name=__name__)


@bp.get("/map")
def map():
    header, qos_reports = parse_adi(
        r"C:\Users\39008\Desktop\lotwreport_full.adi"
    )

    marker_locations = [
        (qos_report.latitude, qos_report.longitude)
        for qos_report in qos_reports
        if qos_report.latitude and qos_report.longitude
    ]

    return render_template(
        "map.html",
        marker_locations=json.dumps(marker_locations),
    )
