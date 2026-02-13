from bs4 import BeautifulSoup
from flask import session
from requests import Response as RResponse

from .. import lotw
from ..dataclasses import AwardsDetail
from ..urls import DXCC_PAGE_URL


def dxcc() -> list[AwardsDetail]:
    """Fetch and parse DXCC award page."""
    response = lotw.get(DXCC_PAGE_URL)
    return parse_dxcc_response(response)


def parse_dxcc_response(response: RResponse) -> list[AwardsDetail]:
    """Parse a pre-fetched DXCC response."""
    op = session.get("op", "")
    soup = BeautifulSoup(response.content, "html.parser")

    # Parse the table to get rows
    dxcc_details: list[AwardsDetail] = []
    rows = soup.select("table#accountStatusTable tbody tr")

    for row in rows:
        columns = row.find_all("td")

        # Remove the link to Challenge, since it's just too big to display
        # nicely on mobile
        if columns[0].find("a"):
            award_value = (
                str(columns[0].find("a"))
                .replace(' target="_new"', "")
                .replace(' target="+new"', "")
            )
        else:
            award_value = columns[0].text

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

    return dxcc_details
