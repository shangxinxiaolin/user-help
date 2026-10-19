import grpc

from app.grpc_client.channel import BusinessGrpcChannel
from app.grpc_client.context import make_request_context
from app.grpc_client.errors import (
    RpcTimeoutError,
    RpcUnavailableError,
    raise_for_business_error,
)
from app.grpc_client.generated.business_service_pb2 import (
    QueryReturnStatusRequest,
    QueryWarrantyRequest,
)


class AftersalesClient:
    def __init__(self, channel: BusinessGrpcChannel) -> None:
        self._channel = channel

    async def query_warranty(
        self,
        user_id: str,
        order_id: str,
        conversation_id: int | str | None = None,
        trace_id: str | None = None,
    ) -> dict:
        context = make_request_context(user_id, conversation_id, trace_id)
        request = QueryWarrantyRequest(context=context, order_id=order_id)
        try:
            response = await self._channel.aftersales.QueryWarranty(
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
            "order_id": info.order_id,
            "warranty_status": info.warranty_status,
            "warranty_until": info.warranty_until,
        }

    async def query_return_status(
        self,
        user_id: str,
        order_id: str,
        conversation_id: int | str | None = None,
        trace_id: str | None = None,
    ) -> dict:
        context = make_request_context(user_id, conversation_id, trace_id)
        request = QueryReturnStatusRequest(context=context, order_id=order_id)
        try:
            response = await self._channel.aftersales.QueryReturnStatus(
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
            "order_id": info.order_id,
            "return_status": info.return_status,
            "updated_at": info.updated_at,
        }
