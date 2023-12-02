from bs4 import BeautifulSoup
from flask import g, render_template, request

from ...urls import VUCC_PAGE_URL
from ..auth.wrappers import login_required
from .awards_dataclass import AwardsDetail
from .base import bp


@bp.get("/vucc")
@login_required(next_page="awards.vucc")
def vucc():
    response = g.web_session.get(VUCC_PAGE_URL)

    op = request.cookies.get("op")
    soup = BeautifulSoup(response.content, "html.parser")
    table = soup.find("table", attrs={"id": "accountStatusTable"})

    # Parse the table to get rows
    rows = table.find_all("tr")
    vucc_details: list[AwardsDetail] = []

    for row in rows[1:]:  # Skip the header row
        columns = row.find_all("td")

        current_row = AwardsDetail(
            op=op,
            award=str(columns[0].find("a"))
            .replace(' target="_new"', "")
            .replace(' target="+new"', "")
            if columns[0].find("a")
            else columns[0].text,
            new=columns[1].text,
            in_process=columns[2].text,
            awarded=columns[3].text,
            total=columns[4].text,
        )

        vucc_details.append(current_row)

    return render_template(
        "award.html",
        awards=vucc_details,
        page_url=VUCC_PAGE_URL,
        award_name="VUCC",
        title="VUCC Award Info",
    )
