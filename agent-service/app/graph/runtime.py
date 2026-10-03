from typing import Any

from langchain_core.messages import HumanMessage

from app.graph.state import ConversationState


async def run_turn(
    graph: Any,
    message: str,
    conversation_id: int | None = None,
    user_id: str | None = None,
) -> ConversationState:
    initial_state: ConversationState = {
        "messages": [
            HumanMessage(content=message)
        ],
        "conversation_id": conversation_id,
        "user_id": user_id,
    }

    result = await graph.ainvoke(initial_state)

    return result