from flask import render_template

from ...blueprints.api import get_map_data
from ...blueprints.auth.wrappers import login_required, paid_required
from .base import bp


@bp.route("/map", methods=["POST", "GET"])
@login_required()
@paid_required()
def view():
    return render_template(
        "map.html",
        title="QSL Map",
        marker_locations=get_map_data(),
    )
