from datetime import date, datetime, timezone
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .notification_delivery import NotificationDelivery
    from .user import User


class QSLDigestBatch(Base):
    __tablename__ = "qsl_digest_batches"
    __table_args__ = (
        Index(
            "ix_qsl_digest_batches_user_digest_date",
            "user_id",
            "digest_date",
            unique=True,
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    user: Mapped["User"] = relationship(back_populates="qsl_digest_batches")

    digest_date: Mapped[date]
    window_start_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    window_end_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    qsl_count: Mapped[int] = mapped_column(default=0)
    payload_json: Mapped[dict[str, Any]] = mapped_column(default=dict)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(tz=timezone.utc),
    )

    deliveries: Mapped[list["NotificationDelivery"]] = relationship(
        back_populates="digest_batch"
    )
