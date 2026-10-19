import grpc

from app.grpc_client.channel import BusinessGrpcChannel
from app.grpc_client.context import make_request_context
from app.grpc_client.errors import (
    RpcTimeoutError,
    RpcUnavailableError,
    raise_for_business_error,
)
from app.grpc_client.generated.business_service_pb2 import (
    SubmitRefundRequest,
    ValidateRefundRequest,
)


class RefundClient:
    def __init__(self, channel: BusinessGrpcChannel) -> None:
        self._channel = channel

    async def validate_refund(
        self,
        user_id: str,
        order_id: str,
        conversation_id: int | str | None = None,
        trace_id: str | None = None,
    ) -> dict:
        context = make_request_context(user_id, conversation_id, trace_id)
        request = ValidateRefundRequest(context=context, order_id=order_id)
        try:
            response = await self._channel.refund.ValidateRefund(
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
            "refundable": response.refundable,
            "message": response.message,
            "reason": response.reason,
        }

    async def submit_refund(
        self,
        user_id: str,
        order_id: str,
        reason: str,
        idempotency_key: str,
        conversation_id: int | str | None = None,
        trace_id: str | None = None,
    ) -> dict:
        context = make_request_context(user_id, conversation_id, trace_id)
        request = SubmitRefundRequest(
            context=context,
            order_id=order_id,
            reason=reason,
            idempotency_key=idempotency_key,
        )
        try:
            response = await self._channel.refund.SubmitRefund(
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
            "refund_id": response.refund_id,
            "message": response.message,
        }
