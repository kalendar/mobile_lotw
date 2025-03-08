from datetime import date, datetime
from json import dumps, loads

from argon2 import PasswordHasher
from Crypto.Cipher import AES
from sqlalchemy import DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base
from .qso_report import QSLReport


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)

    mobile_lotw_username: Mapped[str] = mapped_column(unique=True)
    lotw_username: Mapped[str]

    email: Mapped[str]
    # Hashed
    password_hash: Mapped[str]
    # Encoded bytes
    lotw_password_b: Mapped[bytes]
    lotw_cookies_b: Mapped[bytes | None]

    qsl_reports: Mapped[list[QSLReport]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    qso_reports_last_update_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )

    def __init__(
        self,
        mobile_lotw_username: str,
        mobile_lotw_password: str,
        lotw_username: str,
        email: str,
        qsl_reports_last_update: date = date(year=1970, month=1, day=1),
        qsl_reports: list[QSLReport] = [],
    ):
        ph = PasswordHasher()
        self.password_hash = ph.hash(mobile_lotw_password)

        self.mobile_lotw_username = mobile_lotw_username
        self.lotw_username = lotw_username
        self.qsl_reports.extend(qsl_reports)
        self.qso_reports_last_update = qsl_reports_last_update
        self.email = email

    def get_lotw_password(self, database_key: str) -> str:
        key = bytes(
            database_key,
            encoding="utf-8",
        )

        nonce, tag, ciphertext = (
            self.lotw_password_b[:16],
            self.lotw_password_b[16:32],
            self.lotw_password_b[32:],
        )

        cipher = AES.new(key, AES.MODE_EAX, nonce)  # type: ignore
        return cipher.decrypt_and_verify(ciphertext, tag)  # type: ignore

    def set_lotw_password(self, password: str, database_key: str) -> None:
        key = bytes(
            database_key,
            encoding="utf-8",
        )

        data = bytes(password, encoding="utf-8")
        cipher = AES.new(key, AES.MODE_EAX)  # type: ignore
        ciphertext, tag = cipher.encrypt_and_digest(data)

        total_bytes = cipher.nonce + tag + ciphertext

        self.lotw_password_b = total_bytes

    def get_lotw_cookies(self, database_key: str) -> dict[str, str] | None:
        key = bytes(
            database_key,
            encoding="utf-8",
        )

        if self.lotw_cookies_b:
            nonce, tag, ciphertext = (
                self.lotw_cookies_b[:16],
                self.lotw_cookies_b[16:32],
                self.lotw_cookies_b[32:],
            )

            cipher = AES.new(key, AES.MODE_EAX, nonce)  # type: ignore
            data = cipher.decrypt_and_verify(ciphertext, tag)

            dictionary = loads(data.decode(encoding="utf-8"))

            return dictionary
        return None

    def set_lotw_cookies(self, cookies: dict[str, str], database_key: str) -> None:
        key = bytes(
            database_key,
            encoding="utf-8",
        )

        data = bytes(dumps(cookies), encoding="utf-8")
        cipher = AES.new(key, AES.MODE_EAX)  # type: ignore
        ciphertext, tag = cipher.encrypt_and_digest(data)

        total_bytes = cipher.nonce + tag + ciphertext

        self.lotw_cookies_b = total_bytes
