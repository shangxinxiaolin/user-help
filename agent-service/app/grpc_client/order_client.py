import grpc

from app.grpc_client.channel import BusinessGrpcChannel
from app.grpc_client.context import make_request_context
from app.grpc_client.errors import (
    RpcTimeoutError,
    RpcUnavailableError,
    raise_for_business_error,
)
from app.grpc_client.generated.business_service_pb2 import (
    ListUserOrdersRequest,
    QueryOrderRequest,
)


class OrderClient:
    def __init__(self, channel: BusinessGrpcChannel) -> None:
        self._channel = channel

    async def query_order(
        self,
        user_id: str,
        order_id: str,
        conversation_id: int | str | None = None,
        trace_id: str | None = None,
    ) -> dict:
        context = make_request_context(user_id, conversation_id, trace_id)
        request = QueryOrderRequest(context=context, order_id=order_id)
        try:
            response = await self._channel.order.QueryOrder(
                request,
                timeout=self._channel.timeout,
            )
        except grpc.aio.AioRpcError as exc:
            if exc.code() == grpc.StatusCode.DEADLINE_EXCEEDED:
                raise RpcTimeoutError() from exc
            raise RpcUnavailableError(str(exc)) from exc

        if not response.success:
            raise_for_business_error(response.error_code, response.message)

        order = response.order
        return {
            "order_id": order.order_id,
            "status": order.status,
            "amount": order.amount,
            "created_at": order.created_at,
            "product": order.product,
            "tracking_no": order.tracking_no,
        }

    async def list_user_orders(
        self,
        user_id: str,
        conversation_id: int | str | None = None,
        trace_id: str | None = None,
    ) -> list[dict]:
        context = make_request_context(user_id, conversation_id, trace_id)
        request = ListUserOrdersRequest(context=context)
        try:
            response = await self._channel.order.ListUserOrders(
                request,
                timeout=self._channel.timeout,
            )
        except grpc.aio.AioRpcError as exc:
            if exc.code() == grpc.StatusCode.DEADLINE_EXCEEDED:
                raise RpcTimeoutError() from exc
            raise RpcUnavailableError(str(exc)) from exc

        if not response.success:
            raise_for_business_error(response.error_code, "获取订单列表失败")

        return [
            {
                "order_id": o.order_id,
                "product": o.product,
                "status": o.status,
                "amount": o.amount,
            }
            for o in response.orders
        ]
