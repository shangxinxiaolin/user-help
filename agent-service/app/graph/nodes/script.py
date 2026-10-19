from langchain_core.messages import AIMessage

from app.graph.state import ConversationState


async def complaint_reply_node(state: ConversationState) -> dict:
    reply = (
        "非常抱歉给您带来不愉快的体验！我们非常重视您的反馈，已为您优先登记并转接高级客服专员。"
        "专员将在工作时间内主动跟进联系您，妥善解决您的问题。您也可以点击或输入具体诉求，我们将第一时间处理。"
    )
    return {
        "messages": [AIMessage(content=reply)],
        "answer": reply,
        "suggested_actions": ["提交人工工单", "查看处理进度"],
    }


async def fallback_script_node(state: ConversationState) -> dict:
    reply = (
        "您好，我是灵犀智能客服助手。请问有什么可以帮您？\n"
        "您可以直接询问我：\n"
        "• 订单查询与物流轨迹\n"
        "• 商品退货与退款申请\n"
        "• 保修与售后政策\n"
        "• 运费说明与发票开具\n"
        "如需人工服务，也可以随时告诉我「转人工」。"
    )
    return {
        "messages": [AIMessage(content=reply)],
        "answer": reply,
        "suggested_actions": ["查询我的订单", "运费怎么计算", "申请退款", "转人工客服"],
    }
