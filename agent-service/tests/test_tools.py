from unittest.mock import AsyncMock, MagicMock

import pytest

from app.tools.engine import ToolExecutionEngine
from app.tools.registry import get_all_tool_schemas


@pytest.fixture
def mock_business_client():
    client = MagicMock()
    client.orders.query_order = AsyncMock(return_value={"order_id": "1001", "status": "已付款"})
    client.orders.list_user_orders = AsyncMock(return_value=[{"order_id": "1001"}])
    client.logistics.query_logistics = AsyncMock(return_value={"tracking_no": "SF123", "status": "运输中"})
    client.aftersales.query_warranty = AsyncMock(return_value={"warranty_status": "在保"})
    client.aftersales.query_return_status = AsyncMock(return_value={"return_status": "退货中"})
    client.refunds.validate_refund = AsyncMock(return_value={"refundable": True})
    client.refunds.submit_refund = AsyncMock(return_value={"refund_id": "RF-1001"})
    client.tickets.create_ticket = AsyncMock(return_value={"ticket_no": "TK-1001"})
    return client


@pytest.fixture
def mock_audit_repo():
    repo = MagicMock()
    repo.record_audit = AsyncMock(return_value=1)
    return repo


@pytest.mark.asyncio
async def test_engine_query_order(mock_business_client, mock_audit_repo):
    engine = ToolExecutionEngine(mock_business_client, mock_audit_repo)
    res = await engine.execute_tool(
        tool_name="query_order",
        arguments={"order_id": "1001"},
        tool_call_id="call_1",
        user_id="u1",
        conversation_id=123,
    )
    assert res["order_id"] == "1001"
    mock_audit_repo.record_audit.assert_called_once()


@pytest.mark.asyncio
async def test_engine_submit_refund_confirmation_flow(mock_business_client, mock_audit_repo):
    engine = ToolExecutionEngine(mock_business_client, mock_audit_repo)
    # 1. Unconfirmed should return requires_confirmation
    res = await engine.execute_tool(
        tool_name="submit_refund",
        arguments={"order_id": "1001", "reason": "商品不想要了"},
        tool_call_id="call_2",
        user_id="u1",
        conversation_id=123,
        confirmed=False,
    )
    assert res["status"] == "requires_confirmation"
    assert "您确认要申请订单 1001 的退款吗" in res["message"]

    # 2. Confirmed executes real RPC
    res_confirmed = await engine.execute_tool(
        tool_name="submit_refund",
        arguments={"order_id": "1001", "reason": "商品不想要了"},
        tool_call_id="call_3",
        user_id="u1",
        conversation_id=123,
        confirmed=True,
    )
    assert res_confirmed["refund_id"] == "RF-1001"


@pytest.mark.asyncio
async def test_engine_faq_builtin(mock_business_client):
    engine = ToolExecutionEngine(mock_business_client)
    res = await engine.execute_tool(
        tool_name="query_faq",
        arguments={"keyword": "运费"},
        tool_call_id="call_4",
        user_id="u1",
    )
    assert isinstance(res, list)
    assert any("99" in item["answer"] for item in res)


def test_registry_schemas():
    schemas = get_all_tool_schemas()
    assert len(schemas) == 9
    names = {s["function"]["name"] for s in schemas}
    assert "query_order" in names
    assert "submit_refund" in names
    assert "query_logistics" in names
    assert "create_ticket" in names
    assert "query_faq" in names
