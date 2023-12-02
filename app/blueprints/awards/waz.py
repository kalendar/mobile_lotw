from bs4 import BeautifulSoup
from flask import g, render_template, request

from ...urls import WAZ_PAGE_URL
from ..auth.wrappers import login_required
from .awards_dataclass import AwardsDetail
from .base import bp


@bp.get("/waz")
@login_required(next_page="awards.waz")
def waz():
    response = g.web_session.get(WAZ_PAGE_URL)
    op = request.cookies.get("op")
    soup = BeautifulSoup(response.content, "html.parser")
    table = soup.find("table", attrs={"id": "accountStatusTable"})

    # Parse the table to get rows
    rows = table.find_all("tr")
    waz_details: list[AwardsDetail] = []

    for row in rows[1:]:  # Skip the header row
        columns = row.find_all("td")

        award_value = (
            str(columns[0].find("a"))
            .replace(' target="_new"', "")
            .replace(' target="+new"', "")
            if columns[0].find("a")
            else columns[0].text
        )

        if "5-Band" in award_value:
            award_value = "5-Band"

        current_row = AwardsDetail(
            op=op,
            award=award_value,
            new=columns[1].text,
            in_process=columns[2].text,
            awarded=columns[3].text,
            total=columns[4].text,
        )

        waz_details.append(current_row)

    return render_template(
        "award.html",
        awards=waz_details,
        page_url=WAZ_PAGE_URL,
        award_name="WAZ",
        title="WAZ Award Info",
    )
