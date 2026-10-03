from langchain_core.messages import AIMessage, HumanMessage
from langgraph.graph import END, START, StateGraph

from app.graph.state import ConversationState

def append_ai_message(_state: ConversationState) -> dict:
    return {
        "messages": [
            AIMessage(
                content="你好，有什么可以帮你？"
            )
        ]
    }



def test_messages_are_appended_to_state() -> None:
    builder = StateGraph(ConversationState)

    builder.add_node(
        "append_ai_message",
        append_ai_message,
    )

    builder.add_edge(
        START,
        "append_ai_message",
    )

    builder.add_edge(
        "append_ai_message",
        END,
    )

    graph = builder.compile()

    result = graph.invoke(
        {
            "messages": [
                HumanMessage(content="你好")
            ]
        }
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
        == "你好，有什么可以帮你？"
    )
