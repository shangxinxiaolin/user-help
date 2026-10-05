from unittest.mock import AsyncMock

import pytest

from app.db.repositories import ConversationRepository
from app.graph.nodes.logging import make_log_node


@pytest.mark.asyncio
async def test_log_node_writes_assistant_answer() -> None:
    repository = AsyncMock(spec=ConversationRepository)
    log_node = make_log_node(repository)

    result = await log_node({
        "conversation_id": 1,
        "answer": "你好，有什么可以帮你？",
    })

    repository.append_message.assert_awaited_once_with(
        conversation_id=1,
        role="assistant",
        content="你好，有什么可以帮你？",
    )
    assert result == {}