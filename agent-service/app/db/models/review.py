from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


ID_TYPE = BigInteger().with_variant(Integer, "sqlite")


class ReviewQueueItem(Base):
    __tablename__ = "review_queue"

    id: Mapped[int] = mapped_column(
        ID_TYPE,
        primary_key=True,
        autoincrement=True,
    )
    normalized_question: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
        index=True,
    )
    ai_suggested_answer: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    occurrence_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="pending",
    )
    reviewed_answer: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    reviewed_by: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
