from langchain_core.messages import AIMessage

from app.graph.state import ConversationState


def route_by_intent(state: ConversationState) -> str:
    intent = state.get("intent", "其他")
    if intent == "投诉":
        return "escalate"
    if intent in ("闲聊", "其他"):
        return "fallback_script"
    if intent == "商品咨询":
        return "knowledge"
    if intent in ("退款退货", "售后"):
        return "refund_flow"
    return "business"


def route_after_confidence(state: ConversationState) -> str:
    # If evidence confidence is checked, route to main_agent
    return "main_agent"


def route_main_agent(state: ConversationState) -> str:
    messages = state.get("messages", [])
    if messages:
        last_message = messages[-1]
        if isinstance(last_message, AIMessage) and getattr(last_message, "tool_calls", None):
            return "agent_tools"
    return "log"
