from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Float, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


ID_TYPE = BigInteger().with_variant(Integer, "sqlite")


class LowConfidenceQuestion(Base):
    __tablename__ = "low_confidence_questions"

    id: Mapped[int] = mapped_column(
        ID_TYPE,
        primary_key=True,
        autoincrement=True,
    )
    conversation_id: Mapped[int | None] = mapped_column(
        ID_TYPE,
        nullable=True,
        index=True,
    )
    raw_question: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    intent: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )
    evidence_confidence: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    source: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="evidence_confidence",
    )
    matched_review_id: Mapped[int | None] = mapped_column(
        ID_TYPE,
        nullable=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )
