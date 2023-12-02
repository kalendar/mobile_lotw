from bs4 import BeautifulSoup
from flask import g, render_template, request

from ...urls import DXCC_PAGE_URL
from ..auth.wrappers import login_required
from .awards_dataclass import AwardsDetail
from .base import bp


@bp.get("/dxcc")
@login_required(next_page="awards.dxcc")
def dxcc():
    response = g.web_session.get(DXCC_PAGE_URL)
    op = request.cookies.get("op")

    soup = BeautifulSoup(response.content, "html.parser")
    table = soup.find("table", attrs={"id": "accountStatusTable"})

    # Parse the table to get rows
    dxcc_details: list[AwardsDetail] = []
    rows = table.find_all("tr")

    # Skip the header row
    for row in rows[1:]:
        columns = row.find_all("td")

        # Remove the link to Challenge, since it's just too big to display nicely on mobile
        award_value = (
            str(columns[0].find("a"))
            .replace(' target="_new"', "")
            .replace(' target="+new"', "")
            if columns[0].find("a")
            else columns[0].text
        )

        if "Challenge" in award_value:
            award_value = "Challenge"

        dxcc_detail = AwardsDetail(
            op=op,
            award=award_value,
            new=columns[1].text,
            in_process=columns[2].text,
            awarded=columns[3].text,
            total=columns[5].text,
        )

        dxcc_details.append(dxcc_detail)

    return render_template(
        "award.html",
        awards=dxcc_details,
        page_url=DXCC_PAGE_URL,
        award_name="DXCC",
        title="DXCC Award Info",
    )
