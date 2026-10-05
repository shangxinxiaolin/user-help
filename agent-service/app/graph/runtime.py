from typing import Any

from langchain_core.messages import HumanMessage

from app.db.repositories import ConversationRepository
from app.graph.state import ConversationState


class ConversationNotFound(Exception):
    """会话不存在，或不属于当前用户。"""


async def run_turn(
    graph: Any,
    message: str,
    conversation_id: int | None = None,
    user_id: str | None = None,
    repository: ConversationRepository | None = None,
) -> ConversationState:
    ensured_id = conversation_id
    if repository is not None:
        if user_id is None or not user_id.strip():
            raise ValueError("user_id is required")

        ensured_id = await _ensure_conversation(
            repository=repository,
            user_id=user_id,
            conversation_id=conversation_id,
        )

        await repository.append_message(
            conversation_id=ensured_id,
            role="user",
            content=message,
        )

    initial_state: ConversationState = {
        "messages": [
            HumanMessage(content=message)
        ],
        "conversation_id": ensured_id,
        "user_id": user_id,
    }

    if ensured_id is None:
        return await graph.ainvoke(initial_state)

    return await graph.ainvoke(
        initial_state,
        config={"configurable": {"thread_id": str(ensured_id)}},
    )


async def _ensure_conversation(
    repository: ConversationRepository,
    user_id: str,
    conversation_id: int | None,
) -> int:
    if conversation_id is None:
        return await repository.create_conversation(user_id)

    conversation = await repository.get_conversation_for_user(
        conversation_id,
        user_id,
    )
    if conversation is None:
        raise ConversationNotFound()

    return conversation.id
