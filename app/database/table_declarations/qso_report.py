from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING, Any

from adi_parser.dataclasses import QSOReport as QSOReportDC
from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .user import User


class QSOReport(Base):
    __tablename__ = "qso_reports"

    id: Mapped[int] = mapped_column(primary_key=True)

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    user: Mapped[User] = relationship(back_populates="qso_reports")

    seen: Mapped[bool] = mapped_column(default=False)

    station_callsign: Mapped[str | None]

    my_dxcc: Mapped[int | None]
    my_country: Mapped[str | None]
    my_gridsquare: Mapped[str | None]
    my_latitude: Mapped[float | None]
    my_longitude: Mapped[float | None]
    my_state: Mapped[str | None]
    my_state_human: Mapped[str | None]
    my_cnty: Mapped[str | None]
    my_cnty_human: Mapped[str | None]
    my_cq_zone: Mapped[int | None]
    my_itu_zone: Mapped[int | None]

    call: Mapped[str | None]
    band: Mapped[str | None]
    freq: Mapped[float | None]
    mode: Mapped[str | None]
    qso_date: Mapped[int | None]
    time_on: Mapped[int | None]
    qsl_rcvd: Mapped[str | None]
    qslrdate: Mapped[date | None]
    dxcc: Mapped[int | None]
    country: Mapped[str | None]
    pfx: Mapped[str | None]
    gridsquare: Mapped[str | None]
    latitude: Mapped[float | None]
    longitude: Mapped[float | None]
    cqz: Mapped[int | None]
    ituz: Mapped[int | None]
    state: Mapped[str | None]
    state_human: Mapped[str | None]
    cnty: Mapped[str | None]
    cnty_human: Mapped[str | None]
    credit_granted: Mapped[str | None]
    freq_rx: Mapped[float | None]
    iota: Mapped[str | None]
    submode: Mapped[str | None]
    sat_name: Mapped[str | None]
    prop_mode: Mapped[str | None]

    app_lotw_mode: Mapped[str | None]
    app_lotw_rxqsl: Mapped[datetime | None]
    app_lotw_rxqso: Mapped[datetime | None]
    app_lotw_2xqsl: Mapped[str | None]
    app_lotw_npsunit: Mapped[str | None]
    app_lotw_owncall: Mapped[str | None]
    app_lotw_qslmode: Mapped[str | None]
    app_lotw_modegroup: Mapped[str | None]
    app_lotw_cqz_invalid: Mapped[str | None]
    app_lotw_cqz_inferred: Mapped[str | None]
    app_lotw_ituz_invalid: Mapped[str | None]
    app_lotw_ituz_inferred: Mapped[str | None]
    app_lotw_qso_timestamp: Mapped[datetime | None]
    app_lotw_credit_granted: Mapped[str | None]
    app_lotw_dxcc_entity_status: Mapped[str | None]
    app_lotw_my_cq_zone_inferre: Mapped[str | None]
    app_lotw_gridsquare_invalid: Mapped[str | None]
    app_lotw_my_itu_zone_inferred: Mapped[str | None]
    app_lotw_my_dxcc_entity_status: Mapped[str | None]

    def __init__(
        self,
        user: User,
        dataclass: QSOReportDC | None = None,
        **kw: Any,
    ):
        self.user = user

        if dataclass:
            non_under_attrs = [
                key for key in vars(QSOReport).keys() if key[0] != "_"
            ]
            for attr in non_under_attrs:
                if hasattr(dataclass, attr):
                    setattr(self, attr, getattr(dataclass, attr))

        for key, value in kw.items():
            if hasattr(self, key):
                setattr(self, key, value)

    @property
    def their_coordinates(self) -> tuple[float, float] | None:
        if self.latitude and self.longitude:
            return (self.latitude, self.longitude)
        return None

    def table_values(self) -> tuple[dict[str, str], dict[str, str]]:
        user_details: dict[str, str] = {
            "Call Sign": self.station_callsign,
            "DXCC": f"{self.my_country} ({self.my_dxcc})",
            "CQ Zone": self.my_cq_zone,
            "ITU Zone": self.my_itu_zone,
            "Grid": self.my_gridsquare,
        }
        if self.my_state:
            user_details.update(
                {"State": f"{self.my_state_human} ({self.my_state})"}
            )
        if self.my_cnty:
            user_details.update(
                {"County": f"{self.my_cnty_human} ({self.my_cnty})"}
            )

        other_details: dict[str, str] = {
            "Worked": self.call,
            "DXCC": f"{self.country} ({self.dxcc})",
            "CQ Zone": self.cqz,
            "ITU Zone": self.ituz,
            "Grid": self.gridsquare,
            "County": self.cnty_human,
            "Date/Time": self.app_lotw_qso_timestamp,
            "Mode": self.mode,
            "Band": self.band,
            "Frequency": self.freq,
            "QSL": self.app_lotw_rxqsl,
            "Credits Awarded": self.app_lotw_credit_granted,
        }

        return user_details, other_details
