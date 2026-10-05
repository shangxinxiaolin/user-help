from unittest.mock import AsyncMock

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from app.db.repositories import ConversationRepository
from app.graph.build import build_graph
from tests.fakes import FakeChatModel


@pytest.mark.asyncio
async def test_chat_graph() -> None:
    graph = build_graph(FakeChatModel())

    result = await graph.ainvoke(
        {"messages": [HumanMessage(content="你好")]}
    )

    assert len(result["messages"]) == 2
    assert isinstance(result["messages"][0], HumanMessage)
    assert isinstance(result["messages"][1], AIMessage)
    assert result["messages"][0].content == "你好"
    assert result["messages"][1].content == "Fake response: 你好"


@pytest.mark.asyncio
async def test_chat_graph_logs_assistant_answer() -> None:
    repository = AsyncMock(spec=ConversationRepository)
    graph = build_graph(
        model=FakeChatModel(),
        repository=repository,
    )
    await graph.ainvoke(
        {
            "conversation_id": 1,
            "messages": [HumanMessage(content="你好")],
        }
    )

    repository.append_message.assert_awaited_once_with(
        conversation_id=1,
        role="assistant",
        content="Fake response: 你好",
    )