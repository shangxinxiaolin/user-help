from collections.abc import Awaitable, Callable

from app.db.repositories import ConversationRepository
from app.graph.answer import resolve_answer
from app.graph.state import ConversationState

LogNode = Callable[[ConversationState], Awaitable[dict]]

def make_log_node(
    repository: ConversationRepository | None = None,
) -> LogNode:
    async def log_node(state: ConversationState) -> dict:
        if repository is None:
            return {}

        conversation_id = state.get("conversation_id")
        if conversation_id is None:
            raise ValueError("conversation_id is required to log an answer")

        await repository.append_message(
            conversation_id=conversation_id,
            role="assistant",
            content=resolve_answer(state),
        )
        return {}

    return log_node