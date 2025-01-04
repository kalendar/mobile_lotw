from datetime import datetime

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from dependencies import SessionBeginDep
from lotw import update_user
from utilities import get_user, logged_in

router = APIRouter()

templates = Jinja2Templates(directory="templates")


@router.get("/qsos", response_class=HTMLResponse)
async def qsos(request: Request, session: SessionBeginDep):
    if not logged_in(request=request):
        return RedirectResponse(request.url_for("/"))

    user = get_user(request=request, session=session)

    update_user(user=user)

    qsos = user.qso_reports

    # Since it's being shown to the user, mark as notified
    for qso in qsos:
        qso.notified = True

    return templates.TemplateResponse(
        "qsos.html",
        {
            "request": request,
            "qsos": qsos,
            "datetime": f"{datetime.now():%Y-%m-%d %H:%M:%S%z}",
            "title": "25 Most Recent QSLs",
        },
    )
