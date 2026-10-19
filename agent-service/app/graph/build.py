from typing import Any

from langgraph.graph import END, START, StateGraph

from app.db.repositories import ConversationRepository
from app.graph.nodes.business import make_fetch_order_node, make_retrieve_policy_node
from app.graph.nodes.chat import make_chat_node
from app.graph.nodes.intent import (
    make_classify_intent_node,
    make_resolve_reference_node,
)
from app.graph.nodes.knowledge import (
    make_confidence_check_node,
    make_retrieve_knowledge_node,
)
from app.graph.nodes.logging import make_log_node
from app.graph.nodes.script import complaint_reply_node, fallback_script_node
from app.graph.nodes.tools import make_agent_tools_node
from app.graph.routing import (
    route_by_intent,
    route_main_agent,
)
from app.graph.state import ConversationState
from app.tools.engine import ToolExecutionEngine


def build_workflow_graph(
    model: Any | None = None,
    repository: ConversationRepository | None = None,
    checkpointer: Any | None = None,
    business_client: Any | None = None,
    tool_engine: ToolExecutionEngine | None = None,
):
    graph = StateGraph(ConversationState)
    engine = tool_engine or ToolExecutionEngine(business_client=business_client)

    # 1. Add nodes
    graph.add_node("resolve_reference", make_resolve_reference_node(model))
    graph.add_node("classify_intent", make_classify_intent_node(model))
    graph.add_node("retrieve_knowledge", make_retrieve_knowledge_node())
    graph.add_node("confidence_check", make_confidence_check_node())
    graph.add_node("fetch_order", make_fetch_order_node(business_client))
    graph.add_node("retrieve_policy", make_retrieve_policy_node())
    graph.add_node("main_agent", make_chat_node(model))
    graph.add_node("agent_tools", make_agent_tools_node(engine))
    graph.add_node("complaint_reply", complaint_reply_node)
    graph.add_node("fallback_script", fallback_script_node)
    graph.add_node("log", make_log_node(repository))

    # 2. Add edges
    graph.add_edge(START, "resolve_reference")
    graph.add_edge("resolve_reference", "classify_intent")

    # Intent routing (SPEC 1.3)
    graph.add_conditional_edges(
        "classify_intent",
        route_by_intent,
        {
            "knowledge": "retrieve_knowledge",
            "refund_flow": "fetch_order",
            "business": "main_agent",
            "escalate": "complaint_reply",
            "fallback_script": "fallback_script",
        },
    )

    # Sub-flows
    graph.add_edge("retrieve_knowledge", "confidence_check")
    graph.add_edge("confidence_check", "main_agent")

    graph.add_edge("fetch_order", "retrieve_policy")
    graph.add_edge("retrieve_policy", "main_agent")

    # ReAct tool loop
    graph.add_conditional_edges(
        "main_agent",
        route_main_agent,
        {
            "agent_tools": "agent_tools",
            "log": "log",
        },
    )
    graph.add_edge("agent_tools", "main_agent")

    # Script exits
    graph.add_edge("complaint_reply", "log")
    graph.add_edge("fallback_script", "log")
    graph.add_edge("log", END)

    return graph.compile(checkpointer=checkpointer)


def build_graph(
    model: Any | None = None,
    repository: ConversationRepository | None = None,
    checkpointer: Any | None = None,
    full_workflow: bool = False,
    business_client: Any | None = None,
    tool_engine: ToolExecutionEngine | None = None,
):
    if full_workflow:
        return build_workflow_graph(
            model=model,
            repository=repository,
            checkpointer=checkpointer,
            business_client=business_client,
            tool_engine=tool_engine,
        )

    graph = StateGraph(ConversationState)
    graph.add_node("chat", make_chat_node(model))
    graph.add_node("log", make_log_node(repository))

    graph.add_edge(START, "chat")
    graph.add_edge("chat", "log")
    graph.add_edge("log", END)

    return graph.compile(checkpointer=checkpointer)
