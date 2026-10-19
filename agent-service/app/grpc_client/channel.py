from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import grpc

from app.grpc_client.generated.business_service_pb2_grpc import (
    AftersalesServiceStub,
    LogisticsServiceStub,
    OrderServiceStub,
    RefundServiceStub,
    TicketServiceStub,
)


class BusinessGrpcChannel:
    def __init__(
        self,
        target: str,
        timeout: float,
    ) -> None:
        self.channel = grpc.aio.insecure_channel(target)
        self.order = OrderServiceStub(self.channel)
        self.logistics = LogisticsServiceStub(self.channel)
        self.aftersales = AftersalesServiceStub(self.channel)
        self.refund = RefundServiceStub(self.channel)
        self.ticket = TicketServiceStub(self.channel)
        self.timeout = timeout

    async def close(self) -> None:
        await self.channel.close()


@asynccontextmanager
async def open_business_grpc_channel(
    target: str,
    timeout: float,
) -> AsyncGenerator[BusinessGrpcChannel, None]:
    client = BusinessGrpcChannel(
        target=target,
        timeout=timeout,
    )
    try:
        yield client
    finally:
        await client.close()
