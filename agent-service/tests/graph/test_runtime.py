import pytest
from langchain_core.messages import AIMessage, HumanMessage

from app.graph.build import build_graph
from app.graph.runtime import run_turn
from tests.fakes import FakeChatModel


@pytest.mark.asyncio
async def test_run_turn_preserves_context() -> None:
    graph = build_graph(FakeChatModel())

    result = await run_turn(
        graph=graph,
        message="你好",
        conversation_id=1,
        user_id="u1",
    )

    assert len(result["messages"]) == 2

    assert isinstance(
        result["messages"][0],
        HumanMessage,
    )

    assert isinstance(
        result["messages"][1],
        AIMessage,
    )

    assert result["messages"][0].content == "你好"
    assert (
        result["messages"][1].content
        == "Fake response: 你好"
    )

    assert result["conversation_id"] == 1
    assert result["user_id"] == "u1"
