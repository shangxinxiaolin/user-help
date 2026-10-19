from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


ID_TYPE = BigInteger().with_variant(Integer, "sqlite")


class FaithCase(Base):
    __tablename__ = "faith_cases"

    id: Mapped[int] = mapped_column(
        ID_TYPE,
        primary_key=True,
        autoincrement=True,
    )
    question: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    evidence: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    answer: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    judge_reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    seen_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="open",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )
