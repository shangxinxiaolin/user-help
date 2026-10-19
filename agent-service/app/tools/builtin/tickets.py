from typing import Any


async def create_ticket_fn(
    description: str,
    ticket_type: str,
    user_id: str,
    business_client: Any,
    conversation_id: int | str | None = None,
    trace_id: str | None = None,
    confirmed: bool = False,
    idempotency_key: str | None = None,
) -> dict:
    if not description or not description.strip():
        return {"error": "缺少工单描述，请说明您遇到的问题"}
    if not ticket_type or not ticket_type.strip():
        ticket_type = "客服咨询"

    if not confirmed:
        return {
            "status": "requires_confirmation",
            "action": "create_ticket",
            "ticket_type": ticket_type.strip(),
            "description": description.strip(),
            "message": f"确认要创建类型为「{ticket_type.strip()}」的工单吗？工单描述：{description.strip()}",
        }

    idemp_key = idempotency_key or f"ticket-{user_id}-{conversation_id or '0'}-{ticket_type.strip()}"
    try:
        return await business_client.tickets.create_ticket(
            user_id=user_id,
            description=description.strip(),
            ticket_type=ticket_type.strip(),
            idempotency_key=idemp_key,
            conversation_id=conversation_id,
            trace_id=trace_id,
        )
    except Exception as exc:
        return {"error": str(exc)}
