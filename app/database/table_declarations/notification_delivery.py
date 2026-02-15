from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .qsl_digest_batch import QSLDigestBatch
    from .user import User


class NotificationDelivery(Base):
    __tablename__ = "notification_deliveries"
    __table_args__ = (
        Index(
            "ix_notification_deliveries_user_digest_channel",
            "user_id",
            "digest_batch_id",
            "channel",
            unique=True,
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    user: Mapped["User"] = relationship(back_populates="notification_deliveries")

    digest_batch_id: Mapped[int | None] = mapped_column(
        ForeignKey("qsl_digest_batches.id"),
        nullable=True,
        index=True,
    )
    digest_batch: Mapped["QSLDigestBatch | None"] = relationship(
        back_populates="deliveries"
    )

    type: Mapped[str] = mapped_column(String(length=32), default="qsl_digest")
    channel: Mapped[str] = mapped_column(String(length=32))
    status: Mapped[str] = mapped_column(String(length=32), default="queued")
    provider_message_id: Mapped[str | None] = mapped_column(
        String(length=255),
        nullable=True,
    )
    error_code: Mapped[str | None] = mapped_column(String(length=128), nullable=True)
    error_detail: Mapped[str | None] = mapped_column(Text(), nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(tz=timezone.utc),
    )
