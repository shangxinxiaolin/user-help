from typing import Any


async def query_order_fn(
    order_id: str,
    user_id: str,
    business_client: Any,
    conversation_id: int | str | None = None,
    trace_id: str | None = None,
) -> dict:
    if not order_id or not order_id.strip():
        return {"error": "缺少订单号，请提供订单号"}
    try:
        return await business_client.orders.query_order(
            user_id=user_id,
            order_id=order_id.strip(),
            conversation_id=conversation_id,
            trace_id=trace_id,
        )
    except Exception as exc:
        return {"error": str(exc)}


async def list_user_orders_fn(
    user_id: str,
    business_client: Any,
    conversation_id: int | str | None = None,
    trace_id: str | None = None,
) -> list[dict] | dict:
    try:
        return await business_client.orders.list_user_orders(
            user_id=user_id,
            conversation_id=conversation_id,
            trace_id=trace_id,
        )
    except Exception as exc:
        return {"error": str(exc)}
