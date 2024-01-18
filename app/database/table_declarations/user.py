from datetime import date, datetime
from json import dumps, loads
from typing import Any

from Crypto.Cipher import AES
from sqlalchemy import DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base
from .qso_report import QSOReport


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    op: Mapped[str]

    lotw_cookies_b: Mapped[bytes | None]

    has_imported: Mapped[bool] = mapped_column(default=False)

    qso_reports: Mapped[list[QSOReport]] = relationship(back_populates="user")

    qso_reports_last_update: Mapped[date]
    qso_reports_last_update_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )

    map_data: Mapped[bytes | None]
    map_data_count: Mapped[int] = mapped_column(default=0)

    def __init__(
        self,
        op: str,
        qso_reports_last_update: date = date(year=1970, month=1, day=1),
        qso_reports: list[QSOReport] = [],
        **kw: Any,
    ):
        self.op = op
        self.qso_reports.extend(qso_reports)
        self.qso_reports_last_update = qso_reports_last_update

    @property
    def lotw_cookies(self) -> dict[str, str] | None:
        from flask import current_app

        key = bytes(
            current_app.config.get("MOBILE_LOTW_DB_KEY"),
            encoding="utf-8",
        )

        if self.lotw_cookies_b:
            nonce, tag, ciphertext = (
                self.lotw_cookies_b[:16],
                self.lotw_cookies_b[16:32],
                self.lotw_cookies_b[32:],
            )

            cipher = AES.new(key, AES.MODE_EAX, nonce)
            data = cipher.decrypt_and_verify(ciphertext, tag)

            dictionary = loads(data.decode(encoding="utf-8"))

            return dictionary
        return None

    def outside_app_context_lotw_cookies(
        self, db_key: str
    ) -> dict[str, str] | None:
        key = bytes(
            db_key,
            encoding="utf-8",
        )

        if self.lotw_cookies_b:
            nonce, tag, ciphertext = (
                self.lotw_cookies_b[:16],
                self.lotw_cookies_b[16:32],
                self.lotw_cookies_b[32:],
            )

            cipher = AES.new(key, AES.MODE_EAX, nonce)
            data = cipher.decrypt_and_verify(ciphertext, tag)

            dictionary = loads(data.decode(encoding="utf-8"))

            return dictionary
        return None

    @lotw_cookies.setter
    def lotw_cookies(self, dictionary: dict[str, str]) -> None:
        from flask import current_app

        key = bytes(
            current_app.config.get("MOBILE_LOTW_DB_KEY"),
            encoding="utf-8",
        )

        data = bytes(dumps(dictionary), encoding="utf-8")
        cipher = AES.new(key, AES.MODE_EAX)
        ciphertext, tag = cipher.encrypt_and_digest(data)

        total_bytes = cipher.nonce + tag + ciphertext

        self.lotw_cookies_b = total_bytes
