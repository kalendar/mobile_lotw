from bs4 import BeautifulSoup, Comment
from flask import g, render_template, request

from ...urls import DETAILS_PAGE_URL
from ..auth.wrappers import login_required
from .base import bp


@bp.get("/qsodetail")
@login_required(next_page="qsls")
def qsodetail():
    response = g.web_session.get(DETAILS_PAGE_URL + request.args.get("qso"))

    soup = BeautifulSoup(response.content, "html.parser")

    for element in soup(text=lambda text: isinstance(text, Comment)):
        element.extract()

    tables = soup.find_all("table")
    table = tables[6]

    rows = table.find_all("tr")
    for row in rows:
        cells = row.find_all("td")
        for cell in cells:
            if cell.has_attr("colspan") and cell["colspan"] == "3":
                row.decompose()

    qsl_details = []

    rows = table.find_all("tr")
    for row in rows:
        columns = row.find_all("td")
        current_row = {"label": columns[0].text, "value": columns[2].text}
        qsl_details.append(current_row)

    return render_template(
        "qsl_details.html",
        qsl_details=qsl_details,
        title="QSL Details",
    )
