from bs4 import BeautifulSoup
from flask import g, request, url_for

from ..dataclasses import AwardsDetail
from ..urls import WAS_PAGE_URL


def was() -> list[AwardsDetail]:
    response = g.web_session.get(WAS_PAGE_URL)

    op = request.cookies.get("op")
    soup = BeautifulSoup(response.content, "html.parser")

    # Parse the table to get rows
    was_details: list[AwardsDetail] = []
    rows = soup.select("table#accountStatusTable tbody tr")

    for row in rows:
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
                f'<a href="{url_for("awards.triple")}">Triple Play</a>'
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

    return was_details
