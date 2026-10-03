import pytest
from langchain_core.messages import AIMessage, HumanMessage

from app.graph.nodes.chat import make_chat_node
from tests.fakes import FakeChatModel


@pytest.mark.asyncio
async def test_chat_node_appends_ai_message() -> None:
    chat_node = make_chat_node(
        FakeChatModel()
    )

    result = await chat_node(
        {
            "messages": [
                HumanMessage(content="你好")
            ]
        }
    )

    assert len(result["messages"]) == 1
    assert isinstance(
        result["messages"][0],
        AIMessage,
    )

    assert (
        result["messages"][0].content
        == "Fake response: 你好"
    )
