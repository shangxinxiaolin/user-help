from unittest.mock import AsyncMock, MagicMock

import pytest

from app.grpc_client.aftersales_client import AftersalesClient
from app.grpc_client.business_client import BusinessClient
from app.grpc_client.errors import (
    BusinessRpcError,
    OrderNotFoundError,
    RefundNotAllowedError,
)
from app.grpc_client.generated.business_service_pb2 import (
    CreateTicketResponse,
    LogisticsInfo,
    OrderBrief,
    OrderSnapshot,
    QueryLogisticsResponse,
    QueryOrderResponse,
    QueryReturnStatusResponse,
    QueryWarrantyResponse,
    ReturnInfo,
    SubmitRefundResponse,
    ValidateRefundResponse,
    WarrantyInfo,
)
from app.grpc_client.logistics_client import LogisticsClient
from app.grpc_client.order_client import OrderClient
from app.grpc_client.refund_client import RefundClient
from app.grpc_client.ticket_client import TicketClient


@pytest.fixture
def mock_channel():
    channel = MagicMock()
    channel.timeout = 3.0
    channel.order = MagicMock()
    channel.logistics = MagicMock()
    channel.aftersales = MagicMock()
    channel.refund = MagicMock()
    channel.ticket = MagicMock()
    return channel


@pytest.mark.asyncio
async def test_order_client_query_success(mock_channel):
    mock_channel.order.QueryOrder = AsyncMock(
        return_value=QueryOrderResponse(
            success=True,
            order=OrderSnapshot(
                order_id="1001",
                status="已付款",
                amount=199,
                product="无线降噪耳机",
                tracking_no="SF12345",
            ),
        )
    )
    client = OrderClient(mock_channel)
    result = await client.query_order("u1", "1001")
    assert result["order_id"] == "1001"
    assert result["status"] == "已付款"
    assert result["product"] == "无线降噪耳机"


@pytest.mark.asyncio
async def test_order_client_not_found(mock_channel):
    mock_channel.order.QueryOrder = AsyncMock(
        return_value=QueryOrderResponse(
            success=False,
            error_code="ORDER_NOT_FOUND",
            message="没有找到您的这笔订单",
        )
    )
    client = OrderClient(mock_channel)
    with pytest.raises(OrderNotFoundError):
        await client.query_order("u1", "9999")


@pytest.mark.asyncio
async def test_logistics_client_success(mock_channel):
    mock_channel.logistics.QueryLogistics = AsyncMock(
        return_value=QueryLogisticsResponse(
            success=True,
            info=LogisticsInfo(
                tracking_no="SF12345",
                status="运输中",
                current_city="北京",
                trace=["已揽件", "运往北京"],
            ),
        )
    )
    client = LogisticsClient(mock_channel)
    result = await client.query_logistics("u1", "SF12345")
    assert result["tracking_no"] == "SF12345"
    assert result["status"] == "运输中"
    assert result["current_city"] == "北京"


@pytest.mark.asyncio
async def test_aftersales_client_success(mock_channel):
    mock_channel.aftersales.QueryWarranty = AsyncMock(
        return_value=QueryWarrantyResponse(
            success=True,
            info=WarrantyInfo(
                order_id="1001",
                warranty_status="在保",
                warranty_until="2027-10-01",
            ),
        )
    )
    mock_channel.aftersales.QueryReturnStatus = AsyncMock(
        return_value=QueryReturnStatusResponse(
            success=True,
            info=ReturnInfo(
                order_id="1001",
                return_status="退货中",
                updated_at="2026-10-10",
            ),
        )
    )
    client = AftersalesClient(mock_channel)
    w = await client.query_warranty("u1", "1001")
    assert w["warranty_status"] == "在保"
    r = await client.query_return_status("u1", "1001")
    assert r["return_status"] == "退货中"


@pytest.mark.asyncio
async def test_refund_client_success_and_error(mock_channel):
    mock_channel.refund.ValidateRefund = AsyncMock(
        return_value=ValidateRefundResponse(
            success=True,
            refundable=True,
            message="允许退款",
            reason="",
        )
    )
    mock_channel.refund.SubmitRefund = AsyncMock(
        return_value=SubmitRefundResponse(
            success=True,
            refund_id="RF-123456",
            message="success",
        )
    )
    client = RefundClient(mock_channel)
    v = await client.validate_refund("u1", "1001")
    assert v["refundable"] is True
    s = await client.submit_refund("u1", "1001", "不想要了", "idemp_1")
    assert s["refund_id"] == "RF-123456"

    # Test error
    mock_channel.refund.SubmitRefund = AsyncMock(
        return_value=SubmitRefundResponse(
            success=False,
            error_code="REFUND_NOT_ALLOWED",
            message="当前订单状态不允许退款",
        )
    )
    with pytest.raises(RefundNotAllowedError):
        await client.submit_refund("u1", "1001", "不想要了", "idemp_2")


@pytest.mark.asyncio
async def test_ticket_client_success(mock_channel):
    mock_channel.ticket.CreateTicket = AsyncMock(
        return_value=CreateTicketResponse(
            success=True,
            ticket_no="TK-9876",
            message="success",
        )
    )
    client = TicketClient(mock_channel)
    res = await client.create_ticket("u1", "商品破损", "售后", "idemp_tk1")
    assert res["ticket_no"] == "TK-9876"


@pytest.mark.asyncio
async def test_business_client_composition(mock_channel):
    bclient = BusinessClient(mock_channel)
    assert isinstance(bclient.orders, OrderClient)
    assert isinstance(bclient.logistics, LogisticsClient)
    assert isinstance(bclient.aftersales, AftersalesClient)
    assert isinstance(bclient.refunds, RefundClient)
    assert isinstance(bclient.tickets, TicketClient)
