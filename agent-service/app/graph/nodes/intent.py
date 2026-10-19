from typing import Any

from langchain_core.messages import HumanMessage

from app.core.coref import resolve_reference
from app.core.intent import classify_intent
from app.graph.nodes.chat import get_last_human_message
from app.graph.state import ConversationState


def make_resolve_reference_node(model: Any | None = None):
    async def resolve_reference_node(state: ConversationState) -> dict:
        try:
            last_human = get_last_human_message(state)
            query = last_human.content if isinstance(last_human.content, str) else ""
        except ValueError:
            query = ""

        messages = state.get("messages", [])
        resolved = await resolve_reference(query, messages, model=model)
        return {"resolved_query": resolved}

    return resolve_reference_node


def make_classify_intent_node(model: Any | None = None):
    async def classify_intent_node(state: ConversationState) -> dict:
        query = state.get("resolved_query")
        if not query:
            try:
                last_human = get_last_human_message(state)
                query = last_human.content if isinstance(last_human.content, str) else ""
            except ValueError:
                query = ""

        intent, confidence, reason = await classify_intent(query, model=model)
        return {
            "intent": intent,
            "intent_confidence": confidence,
            "trace": {"intent_reason": reason},
        }

    return classify_intent_node
