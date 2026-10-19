from typing import Any


async def query_logistics_fn(
    tracking_no: str,
    user_id: str,
    business_client: Any,
    conversation_id: int | str | None = None,
    trace_id: str | None = None,
) -> dict:
    if not tracking_no or not tracking_no.strip():
        return {"error": "缺少物流单号，请提供物流单号"}
    try:
        return await business_client.logistics.query_logistics(
            user_id=user_id,
            tracking_no=tracking_no.strip(),
            conversation_id=conversation_id,
            trace_id=trace_id,
        )
    except Exception as exc:
        return {"error": str(exc)}
