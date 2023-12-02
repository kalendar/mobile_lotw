import re
from dataclasses import dataclass

from bs4 import BeautifulSoup
from flask import g, render_template, request

from ...urls import TRIPLE_PAGE_URL
from ..auth.wrappers import login_required
from .base import bp

STATES_COMPILED = re.compile(r"(?s).+ \((\w+)\)")


@dataclass
class TripleDetail:
    op: str
    state: str
    cw: str
    phone: str
    digital: str


@bp.get("/triple")
@login_required(next_page="awards.triple")
def triple():
    response = g.get("web_session").get(TRIPLE_PAGE_URL)

    op = request.cookies.get("op")

    soup = BeautifulSoup(response.content, "html.parser")
    table = soup.find("table", attrs={"id": "creditsTable"})

    # Parse the table to get rows
    rows = table.find_all("tr")
    triples: list[TripleDetail] = []

    # Skip the header row
    for row in rows[1:]:
        columns = row.find_all("td")

        triple_detail = TripleDetail(
            op=op,
            # reduce states to abbreviations
            state=re.sub(
                STATES_COMPILED,
                r"\1",
                columns[0].text,
            ),
            cw=str(columns[1].find("a"))
            .replace(' target="_new"', "")
            .replace(' target="+new"', "")
            if columns[1].find("a")
            else "-",
            phone=str(columns[2].find("a"))
            .replace(' target="_new"', "")
            .replace(' target="+new"', "")
            if columns[2].find("a")
            else "-",
            digital=str(columns[3].find("a"))
            .replace(' target="_new"', "")
            .replace(' target="+new"', "")
            if columns[3].find("a")
            else "-",
        )

        triples.append(triple_detail)

    return render_template(
        "triple.html",
        triples=triples,
        triple_page_url=TRIPLE_PAGE_URL,
        title="Triple Play Award Info",
    )
