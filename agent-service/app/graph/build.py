from typing import Any

from langgraph.graph import END, START, StateGraph

from app.graph.nodes.chat import make_chat_node
from app.graph.state import ConversationState


def build_graph(model: Any | None = None):
    graph = StateGraph(ConversationState)

    graph.add_node(
        "chat",
        make_chat_node(model),
    )

    graph.add_edge(START, "chat")
    graph.add_edge("chat", END)

    return graph.compile()