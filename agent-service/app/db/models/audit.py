from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


ID_TYPE = BigInteger().with_variant(Integer, "sqlite")


class ToolAuditLog(Base):
    __tablename__ = "tool_audit_logs"

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
    tool_call_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    tool_name: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )
    tool_source: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="builtin",
    )
    mcp_server: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )
    arguments: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
    )
    result_summary: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="成功",
    )
    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    retry_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    duration_ms: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )
