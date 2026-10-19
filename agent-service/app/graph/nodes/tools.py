import json
from typing import Any

from langchain_core.messages import AIMessage, ToolMessage

from app.graph.state import ConversationState
from app.tools.engine import ToolExecutionEngine


def make_agent_tools_node(
    tool_engine: ToolExecutionEngine,
):
    async def agent_tools_node(state: ConversationState) -> dict:
        messages = state.get("messages", [])
        last_message = messages[-1] if messages else None

        if not isinstance(last_message, AIMessage) or not last_message.tool_calls:
            return {}

        user_id = state.get("user_id", "")
        conversation_id = state.get("conversation_id")
        action_confirmed = state.get("action_confirmed", False)

        tool_messages = []
        pending_action = None

        for tool_call in last_message.tool_calls:
            tool_name = tool_call.get("name")
            tool_args = tool_call.get("args") or {}
            tool_call_id = tool_call.get("id") or f"call_{tool_name}"

            res = await tool_engine.execute_tool(
                tool_name=tool_name,
                arguments=tool_args,
                tool_call_id=tool_call_id,
                user_id=user_id,
                conversation_id=conversation_id,
                confirmed=action_confirmed,
            )

            if isinstance(res, dict) and res.get("status") == "requires_confirmation":
                pending_action = res

            content_str = json.dumps(res, ensure_ascii=False) if isinstance(res, (dict, list)) else str(res)
            tool_messages.append(
                ToolMessage(
                    content=content_str,
                    tool_call_id=tool_call_id,
                )
            )

        update: dict[str, Any] = {"messages": tool_messages}
        if pending_action:
            update["pending_action"] = pending_action
        return update

    return agent_tools_node
