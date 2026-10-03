from typing import Annotated, TypedDict

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages


def merge_dict(
    current: dict | None,
    update: dict | None,
) -> dict:
    if update is None:
        return {}

    return {
        **(current or {}),
        **update,
    }


class ConversationState(TypedDict, total=False):
    messages: Annotated[
        list[AnyMessage],
        add_messages,
    ]

    summary: str
    summary_upto_msg_id: int

    user_id: str
    conversation_id: int

    resolved_query: str
    intent: str
    intent_confidence: float
    route: str

    order_id: str
    order_data: dict

    evidence: str
    citations: list
    evidence_strong: bool
    evidence_confidence: float
    fallback_source: str
    retrieved_snapshot: list

    answer: str

    steps: int
    tokens_used: int

    suggested_actions: list

    trace: Annotated[
        dict,
        merge_dict,
    ]