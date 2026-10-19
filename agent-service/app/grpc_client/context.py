from app.grpc_client.generated.business_service_pb2 import RequestContext


def make_request_context(
    user_id: str,
    conversation_id: int | str | None = None,
    trace_id: str | None = None,
) -> RequestContext:
    conv_str = str(conversation_id) if conversation_id is not None else ""
    tr_str = trace_id or ""
    return RequestContext(
        user_id=user_id,
        conversation_id=conv_str,
        trace_id=tr_str,
    )
