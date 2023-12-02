from bs4 import BeautifulSoup
from flask import g, render_template, request

from ...urls import WPX_PAGE_URL
from ..auth.wrappers import login_required
from .awards_dataclass import AwardsDetail
from .base import bp


@bp.get("/wpx")
@login_required(next_page="awards.wpx")
def wpx():
    response = g.web_session.get(WPX_PAGE_URL)
    op = request.cookies.get("op")
    soup = BeautifulSoup(response.content, "html.parser")
    table = soup.find("table", attrs={"id": "accountStatusTable"})

    # Parse the table to get rows
    rows = table.find_all("tr")
    wpx_details: list[AwardsDetail] = []

    # Skip the header row
    for row in rows[1:]:
        columns = row.find_all("td")

        wpx_detail = AwardsDetail(
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

        wpx_details.append(wpx_detail)

    return render_template(
        "award.html",
        awards=wpx_details,
        page_url=WPX_PAGE_URL,
        award_name="WPX",
        title="WPX Award Info",
    )
