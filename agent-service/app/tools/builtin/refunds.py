from typing import Any


async def validate_refund_fn(
    order_id: str,
    user_id: str,
    business_client: Any,
    conversation_id: int | str | None = None,
    trace_id: str | None = None,
) -> dict:
    if not order_id or not order_id.strip():
        return {"error": "缺少订单号，请提供订单号"}
    try:
        return await business_client.refunds.validate_refund(
            user_id=user_id,
            order_id=order_id.strip(),
            conversation_id=conversation_id,
            trace_id=trace_id,
        )
    except Exception as exc:
        return {"error": str(exc)}


async def submit_refund_fn(
    order_id: str,
    reason: str,
    user_id: str,
    business_client: Any,
    conversation_id: int | str | None = None,
    trace_id: str | None = None,
    confirmed: bool = False,
    idempotency_key: str | None = None,
) -> dict:
    if not order_id or not order_id.strip():
        return {"error": "缺少订单号，请提供订单号"}
    if not reason or not reason.strip():
        return {"error": "缺少退款原因，请提供退款原因"}

    # SPEC 12.3 & 12.6: write operations require user confirmation
    if not confirmed:
        return {
            "status": "requires_confirmation",
            "action": "submit_refund",
            "order_id": order_id.strip(),
            "reason": reason.strip(),
            "message": f"您确认要申请订单 {order_id.strip()} 的退款吗？退款原因：{reason.strip()}",
        }

    idemp_key = idempotency_key or f"refund-{user_id}-{order_id.strip()}-{conversation_id or '0'}"
    try:
        return await business_client.refunds.submit_refund(
            user_id=user_id,
            order_id=order_id.strip(),
            reason=reason.strip(),
            idempotency_key=idemp_key,
            conversation_id=conversation_id,
            trace_id=trace_id,
        )
    except Exception as exc:
        return {"error": str(exc)}
