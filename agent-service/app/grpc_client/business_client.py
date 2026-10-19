from app.grpc_client.aftersales_client import AftersalesClient
from app.grpc_client.channel import BusinessGrpcChannel
from app.grpc_client.logistics_client import LogisticsClient
from app.grpc_client.order_client import OrderClient
from app.grpc_client.refund_client import RefundClient
from app.grpc_client.ticket_client import TicketClient


class BusinessClient:
    def __init__(self, channel: BusinessGrpcChannel) -> None:
        self.channel = channel
        self.orders = OrderClient(channel)
        self.logistics = LogisticsClient(channel)
        self.aftersales = AftersalesClient(channel)
        self.refunds = RefundClient(channel)
        self.tickets = TicketClient(channel)
