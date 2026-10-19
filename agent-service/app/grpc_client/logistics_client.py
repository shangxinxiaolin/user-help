import grpc

from app.grpc_client.channel import BusinessGrpcChannel
from app.grpc_client.context import make_request_context
from app.grpc_client.errors import (
    RpcTimeoutError,
    RpcUnavailableError,
    raise_for_business_error,
)
from app.grpc_client.generated.business_service_pb2 import QueryLogisticsRequest


class LogisticsClient:
    def __init__(self, channel: BusinessGrpcChannel) -> None:
        self._channel = channel

    async def query_logistics(
        self,
        user_id: str,
        tracking_no: str,
        conversation_id: int | str | None = None,
        trace_id: str | None = None,
    ) -> dict:
        context = make_request_context(user_id, conversation_id, trace_id)
        request = QueryLogisticsRequest(context=context, tracking_no=tracking_no)
        try:
            response = await self._channel.logistics.QueryLogistics(
                request,
                timeout=self._channel.timeout,
            )
        except grpc.aio.AioRpcError as exc:
            if exc.code() == grpc.StatusCode.DEADLINE_EXCEEDED:
                raise RpcTimeoutError() from exc
            raise RpcUnavailableError(str(exc)) from exc

        if not response.success:
            raise_for_business_error(response.error_code, response.message)

        info = response.info
        return {
            "tracking_no": info.tracking_no,
            "status": info.status,
            "current_city": info.current_city,
            "trace": list(info.trace),
        }
