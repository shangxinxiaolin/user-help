from langchain_core.tools import Tool, StructuredTool
from pydantic import BaseModel, Field


class QueryOrderInput(BaseModel):
    order_id: str = Field(description="订单号，例如 1001")


class ListUserOrdersInput(BaseModel):
    pass


class QueryLogisticsInput(BaseModel):
    tracking_no: str = Field(description="快递物流单号，例如 SF123456789")


class QueryWarrantyInput(BaseModel):
    order_id: str = Field(description="订单号，例如 1001")


class QueryReturnStatusInput(BaseModel):
    order_id: str = Field(description="订单号，例如 1001")


class ValidateRefundInput(BaseModel):
    order_id: str = Field(description="待校验退款条件的订单号")


class SubmitRefundInput(BaseModel):
    order_id: str = Field(description="申请退款的订单号")
    reason: str = Field(description="退款原因说明")


class CreateTicketInput(BaseModel):
    description: str = Field(description="工单详细描述")
    ticket_type: str = Field(default="售后", description="工单类型，例如：售后、投诉、催发货、其他")


class QueryFaqInput(BaseModel):
    keyword: str = Field(description="需要查询的常见问题关键词，如：运费、发票、退货、保修")


TOOL_DEFINITIONS = [
    {
        "name": "query_order",
        "description": "查询指定订单的详细信息，包含商品、支付金额、状态、物流单号",
        "args_schema": QueryOrderInput,
    },
    {
        "name": "list_user_orders",
        "description": "查询当前登录用户的订单列表",
        "args_schema": ListUserOrdersInput,
    },
    {
        "name": "query_logistics",
        "description": "根据物流单号查询快递实时状态与物流轨迹",
        "args_schema": QueryLogisticsInput,
    },
    {
        "name": "query_warranty",
        "description": "根据订单号查询商品的保修在保状态和保修截止时间",
        "args_schema": QueryWarrantyInput,
    },
    {
        "name": "query_return_status",
        "description": "根据订单号查询退货审核进度及售后状态",
        "args_schema": QueryReturnStatusInput,
    },
    {
        "name": "validate_refund",
        "description": "校验订单是否符合退款条件",
        "args_schema": ValidateRefundInput,
    },
    {
        "name": "submit_refund",
        "description": "提交订单退款申请",
        "args_schema": SubmitRefundInput,
    },
    {
        "name": "create_ticket",
        "description": "为用户创建人工客服或投诉工单",
        "args_schema": CreateTicketInput,
    },
    {
        "name": "query_faq",
        "description": "查询常见问题解答FAQ，包含运费政策、发票开具、发货规则等",
        "args_schema": QueryFaqInput,
    },
]


def get_all_tool_schemas() -> list[dict]:
    schemas = []
    for item in TOOL_DEFINITIONS:
        schemas.append({
            "type": "function",
            "function": {
                "name": item["name"],
                "description": item["description"],
                "parameters": item["args_schema"].model_json_schema(),
            },
        })
    return schemas
