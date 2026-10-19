from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.models.audit import ToolAuditLog


class ToolAuditRepository:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self._session_factory = session_factory

    async def record_audit(
        self,
        tool_call_id: str,
        tool_name: str,
        tool_source: str = "builtin",
        conversation_id: int | None = None,
        mcp_server: str | None = None,
        arguments: dict | None = None,
        result_summary: str | None = None,
        status: str = "成功",
        error_message: str | None = None,
        retry_count: int = 0,
        duration_ms: int = 0,
    ) -> int:
        async with self._session_factory() as session:
            audit = ToolAuditLog(
                conversation_id=conversation_id,
                tool_call_id=tool_call_id,
                tool_name=tool_name,
                tool_source=tool_source,
                mcp_server=mcp_server,
                arguments=arguments,
                result_summary=result_summary[:500] if result_summary else None,
                status=status,
                error_message=error_message,
                retry_count=retry_count,
                duration_ms=duration_ms,
            )
            session.add(audit)
            await session.flush()
            log_id = audit.id
            await session.commit()
            return log_id

    async def list_by_conversation(
        self,
        conversation_id: int,
    ) -> list[ToolAuditLog]:
        async with self._session_factory() as session:
            result = await session.execute(
                select(ToolAuditLog)
                .where(ToolAuditLog.conversation_id == conversation_id)
                .order_by(ToolAuditLog.id)
            )
            return list(result.scalars())
