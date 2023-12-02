from bs4 import BeautifulSoup, Comment
from flask import flash, g, redirect, render_template, request, url_for

from ..urls import DETAILS_PAGE_URL


def qsodetail():
    if g.web_session:
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

    else:
        flash("Please login.", "info")
        return redirect(url_for("login", next_page="qsls"))
