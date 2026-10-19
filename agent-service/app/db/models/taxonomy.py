from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Float, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


ID_TYPE = BigInteger().with_variant(Integer, "sqlite")


class TopicClassification(Base):
    __tablename__ = "topic_classifications"

    id: Mapped[int] = mapped_column(
        ID_TYPE,
        primary_key=True,
        autoincrement=True,
    )
    question_id: Mapped[int | None] = mapped_column(
        ID_TYPE,
        nullable=True,
        index=True,
    )
    raw_question: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    topics: Mapped[list | None] = mapped_column(
        JSON,
        nullable=True,
    )
    confidence: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    classified_by: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="llm",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )
