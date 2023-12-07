from flask import render_template

from ...blueprints.api import get_map_data
from ...blueprints.auth.wrappers import login_required
from .base import bp


@bp.route("/map", methods=["POST", "GET"])
@login_required()
def view():
    return render_template(
        "map.html",
        marker_locations=get_map_data(),
    )
