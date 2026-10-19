import json
import logging
import time
from typing import Any

from app.tools.builtin.aftersales import query_return_status_fn, query_warranty_fn
from app.tools.builtin.faq import query_faq_fn
from app.tools.builtin.logistics import query_logistics_fn
from app.tools.builtin.orders import list_user_orders_fn, query_order_fn
from app.tools.builtin.refunds import submit_refund_fn, validate_refund_fn
from app.tools.builtin.tickets import create_ticket_fn

logger = logging.getLogger("app.tools.engine")


class ToolExecutionEngine:
    def __init__(
        self,
        business_client: Any = None,
        audit_repository: Any = None,
    ) -> None:
        self.business_client = business_client
        self.audit_repository = audit_repository

    async def execute_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        tool_call_id: str,
        user_id: str,
        conversation_id: int | str | None = None,
        trace_id: str | None = None,
        confirmed: bool = False,
    ) -> dict[str, Any] | list | str:
        start_time = time.perf_counter()
        status = "成功"
        error_message = None
        result: Any = None

        try:
            if tool_name == "query_order":
                result = await query_order_fn(
                    order_id=arguments.get("order_id", ""),
                    user_id=user_id,
                    business_client=self.business_client,
                    conversation_id=conversation_id,
                    trace_id=trace_id,
                )
            elif tool_name == "list_user_orders":
                result = await list_user_orders_fn(
                    user_id=user_id,
                    business_client=self.business_client,
                    conversation_id=conversation_id,
                    trace_id=trace_id,
                )
            elif tool_name == "query_logistics":
                result = await query_logistics_fn(
                    tracking_no=arguments.get("tracking_no", ""),
                    user_id=user_id,
                    business_client=self.business_client,
                    conversation_id=conversation_id,
                    trace_id=trace_id,
                )
            elif tool_name == "query_warranty":
                result = await query_warranty_fn(
                    order_id=arguments.get("order_id", ""),
                    user_id=user_id,
                    business_client=self.business_client,
                    conversation_id=conversation_id,
                    trace_id=trace_id,
                )
            elif tool_name == "query_return_status":
                result = await query_return_status_fn(
                    order_id=arguments.get("order_id", ""),
                    user_id=user_id,
                    business_client=self.business_client,
                    conversation_id=conversation_id,
                    trace_id=trace_id,
                )
            elif tool_name == "validate_refund":
                result = await validate_refund_fn(
                    order_id=arguments.get("order_id", ""),
                    user_id=user_id,
                    business_client=self.business_client,
                    conversation_id=conversation_id,
                    trace_id=trace_id,
                )
            elif tool_name == "submit_refund":
                result = await submit_refund_fn(
                    order_id=arguments.get("order_id", ""),
                    reason=arguments.get("reason", ""),
                    user_id=user_id,
                    business_client=self.business_client,
                    conversation_id=conversation_id,
                    trace_id=trace_id,
                    confirmed=confirmed,
                )
            elif tool_name == "create_ticket":
                result = await create_ticket_fn(
                    description=arguments.get("description", ""),
                    ticket_type=arguments.get("ticket_type", "售后"),
                    user_id=user_id,
                    business_client=self.business_client,
                    conversation_id=conversation_id,
                    trace_id=trace_id,
                    confirmed=confirmed,
                )
            elif tool_name == "query_faq":
                result = await query_faq_fn(
                    keyword=arguments.get("keyword", ""),
                )
            else:
                status = "未知工具"
                result = {"error": f"未知的工具名称: {tool_name}"}

        except Exception as exc:
            status = "失败"
            error_message = str(exc)
            result = {"error": f"工具调用异常: {exc}"}

        duration_ms = int((time.perf_counter() - start_time) * 1000)

        # Audit logging (SPEC 1.5.7)
        summary = str(result)[:500] if result is not None else ""
        logger.info(
            "tool_run conv=%s tool=%s source=builtin status=%s duration_ms=%d",
            conversation_id,
            tool_name,
            status,
            duration_ms,
        )

        if self.audit_repository is not None:
            try:
                conv_int = int(conversation_id) if conversation_id and str(conversation_id).isdigit() else None
                await self.audit_repository.record_audit(
                    conversation_id=conv_int,
                    tool_call_id=tool_call_id,
                    tool_name=tool_name,
                    tool_source="builtin",
                    arguments=arguments,
                    result_summary=summary,
                    status=status,
                    error_message=error_message,
                    duration_ms=duration_ms,
                )
            except Exception as audit_err:
                logger.warning("Failed to record tool audit: %s", audit_err)

        return result
