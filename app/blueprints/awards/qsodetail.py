from flask import render_template

from ...parser import qsodetail as parse_qsodetail
from ..auth.wrappers import login_required
from .base import bp


@bp.get("/qsodetail")
@login_required(next_page="qsls")
def qsodetail():
    qsl_detail = parse_qsodetail()

    return render_template(
        "qsl_details.html",
        qsl_detail=qsl_detail,
        title="QSL Details",
    )
