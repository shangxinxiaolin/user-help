from typing import Any

from langgraph.graph import END, START, StateGraph

from app.db.repositories import ConversationRepository
from app.graph.nodes.chat import make_chat_node
from app.graph.nodes.logging import make_log_node
from app.graph.state import ConversationState


def build_graph(
    model: Any | None = None,
    repository: ConversationRepository | None = None,
    checkpointer: Any | None = None,
):
    graph = StateGraph(ConversationState)

    graph.add_node("chat", make_chat_node(model))
    graph.add_node("log", make_log_node(repository))

    graph.add_edge(START, "chat")
    graph.add_edge("chat", "log")
    graph.add_edge("log", END)

    return graph.compile(checkpointer=checkpointer)
