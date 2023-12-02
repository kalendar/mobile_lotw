from bs4 import BeautifulSoup
from flask import g, render_template, request

from ...urls import WAS_PAGE_URL
from ..auth.wrappers import login_required
from .awards_dataclass import AwardsDetail
from .base import bp


@bp.get("/was")
@login_required(next_page="awards.was")
def was():
    response = g.web_session.get(WAS_PAGE_URL)
    op = request.cookies.get("op")
    soup = BeautifulSoup(response.content, "html.parser")
    table = soup.find("table", attrs={"id": "accountStatusTable"})

    # Parse the table to get rows
    rows = table.find_all("tr")
    was_details: list[AwardsDetail] = []

    # Skip the header row
    for row in rows[1:]:
        columns = row.find_all("td")
        # Remove the link to Challenge, since it's just too big to
        # display nicely on mobile
        award_value = (
            str(columns[0].find("a"))
            .replace(' target="_new"', "")
            .replace(' target="+new"', "")
            if columns[0].find("a")
            else columns[0].text
        )

        if "Triple" in award_value:
            award_value = (
                '<a href="https://mobilelotw.org/triple">Triple Play</a>'
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

        was_details.append(current_row)

    return render_template(
        "award.html",
        awards=was_details,
        page_url=WAS_PAGE_URL,
        award_name="WAS",
        title="WAS Award Info",
    )
