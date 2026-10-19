from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Float, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


ID_TYPE = BigInteger().with_variant(Integer, "sqlite")


class EvalRun(Base):
    __tablename__ = "eval_runs"

    id: Mapped[int] = mapped_column(
        ID_TYPE,
        primary_key=True,
        autoincrement=True,
    )
    strategy: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    recall_rate: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    coverage_rate: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    faithful_rate: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    total_cases: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )
