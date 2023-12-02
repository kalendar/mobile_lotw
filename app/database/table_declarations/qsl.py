from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class QSL(Base):
    __tablename__ = "qsls"

    id: Mapped[int] = mapped_column(primary_key=True)
    op: Mapped[str]
    worked: Mapped[str]
    band: Mapped[str]
    mode: Mapped[str]
    details: Mapped[str]

    def __init__(
        self,
        op: str,
        worked: str,
        band: str,
        mode: str,
        details: str,
    ):
        self.op = op
        self.worked = worked
        self.band = band
        self.mode = mode
        self.details = details
        super().__init__()

    def __eq__(self, __value: object) -> bool:
        if isinstance(__value, QSL):
            return (
                __value.worked == self.worked
                and __value.band == self.band
                and __value.mode == self.mode
                and __value.details == self.details
            )
        return False

    def __ne__(self, __value: object) -> bool:
        return not self.__eq__(__value=__value)
