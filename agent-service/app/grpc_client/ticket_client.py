import grpc

from app.grpc_client.channel import BusinessGrpcChannel
from app.grpc_client.context import make_request_context
from app.grpc_client.errors import (
    RpcTimeoutError,
    RpcUnavailableError,
    raise_for_business_error,
)
from app.grpc_client.generated.business_service_pb2 import CreateTicketRequest


class TicketClient:
    def __init__(self, channel: BusinessGrpcChannel) -> None:
        self._channel = channel

    async def create_ticket(
        self,
        user_id: str,
        description: str,
        ticket_type: str,
        idempotency_key: str,
        conversation_id: int | str | None = None,
        trace_id: str | None = None,
    ) -> dict:
        context = make_request_context(user_id, conversation_id, trace_id)
        request = CreateTicketRequest(
            context=context,
            description=description,
            ticket_type=ticket_type,
            idempotency_key=idempotency_key,
        )
        try:
            response = await self._channel.ticket.CreateTicket(
                request,
                timeout=self._channel.timeout,
            )
        except grpc.aio.AioRpcError as exc:
            if exc.code() == grpc.StatusCode.DEADLINE_EXCEEDED:
                raise RpcTimeoutError() from exc
            raise RpcUnavailableError(str(exc)) from exc

        if not response.success:
            raise_for_business_error(response.error_code, response.message)

        return {
            "ticket_no": response.ticket_no,
            "message": response.message,
        }
