from datetime import datetime

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from dependencies import SessionBeginDep
from env import SETTINGS
from lotw import update_user
from lotw.awards import DXCC, VUCC, WAS, WAZ, WPX, retrieve_award
from utilities import get_user

router = APIRouter()

templates = Jinja2Templates(directory="templates")


@router.get("/qsls", response_class=HTMLResponse)
async def qsls(request: Request, session: SessionBeginDep):
    user = get_user(request=request, session=session)

    update_user(user=user)

    qsls = user.qsl_reports

    # Since it's being shown to the user, mark as notified
    for qsl in qsls:
        qsl.notified = True

    return templates.TemplateResponse(
        "qsls.html",
        {
            "request": request,
            "qsls": qsls,
            "datetime": f"{datetime.now():%Y-%m-%d %H:%M:%S%z}",
            "title": "25 Most Recent QSLs",
        },
    )


@router.get("/dxcc", response_class=HTMLResponse)
async def dxcc(request: Request, session: SessionBeginDep):
    user = get_user(request=request, session=session)

    dxccs = retrieve_award(url=SETTINGS.DXCC_url, user=user, award=DXCC)

    return templates.TemplateResponse(
        "dxcc.html",
        {
            "request": request,
            "dxccs": dxccs,
            "datetime": f"{datetime.now():%Y-%m-%d %H:%M:%S%z}",
            "title": "DXCC Awards",
        },
    )


@router.get("/was", response_class=HTMLResponse)
async def was(request: Request, session: SessionBeginDep):
    user = get_user(request=request, session=session)

    wass = retrieve_award(url=SETTINGS.WAS_url, user=user, award=WAS)

    return templates.TemplateResponse(
        "generic_award.html",
        {
            "request": request,
            "award_name": "WAS",
            "awards": wass,
            "datetime": f"{datetime.now():%Y-%m-%d %H:%M:%S%z}",
            "title": "WAS Awards",
        },
    )


@router.get("/vucc", response_class=HTMLResponse)
async def vucc(request: Request, session: SessionBeginDep):
    user = get_user(request=request, session=session)

    vuccs = retrieve_award(url=SETTINGS.VUCC_url, user=user, award=VUCC)

    return templates.TemplateResponse(
        "generic_award.html",
        {
            "request": request,
            "award_name": "VUCC",
            "awards": vuccs,
            "datetime": f"{datetime.now():%Y-%m-%d %H:%M:%S%z}",
            "title": "VUCC Awards",
        },
    )


@router.get("/wpx", response_class=HTMLResponse)
async def wpx(request: Request, session: SessionBeginDep):
    user = get_user(request=request, session=session)

    wpxs = retrieve_award(url=SETTINGS.WPX_url, user=user, award=WPX)

    return templates.TemplateResponse(
        "generic_award.html",
        {
            "request": request,
            "award_name": "WPX",
            "awards": wpxs,
            "datetime": f"{datetime.now():%Y-%m-%d %H:%M:%S%z}",
            "title": "WPX Awards",
        },
    )


@router.get("/waz", response_class=HTMLResponse)
async def waz(request: Request, session: SessionBeginDep):
    user = get_user(request=request, session=session)

    wazs = retrieve_award(url=SETTINGS.WAZ_url, user=user, award=WAZ)

    return templates.TemplateResponse(
        "generic_award.html",
        {
            "request": request,
            "award_name": "WAZ",
            "awards": wazs,
            "datetime": f"{datetime.now():%Y-%m-%d %H:%M:%S%z}",
            "title": "WAZ Awards",
        },
    )
