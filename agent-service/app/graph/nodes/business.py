import re
from typing import Any

from app.graph.state import ConversationState
from app.kb.store import default_kb_store


def make_fetch_order_node(business_client: Any | None = None):
    async def fetch_order_node(state: ConversationState) -> dict:
        query = state.get("resolved_query") or ""
        user_id = state.get("user_id") or ""
        conversation_id = state.get("conversation_id")

        # Extract order id pattern
        order_match = re.search(r"\b(\d{4,10})\b", query)
        order_id = order_match.group(1) if order_match else state.get("order_id")

        if not order_id or not business_client or not user_id:
            return {"order_id": order_id}

        try:
            order_data = await business_client.orders.query_order(
                user_id=user_id,
                order_id=order_id,
                conversation_id=conversation_id,
            )
            return {"order_id": order_id, "order_data": order_data}
        except Exception as e:
            return {"order_id": order_id, "trace": {"fetch_order_error": str(e)}}

    return fetch_order_node


def make_retrieve_policy_node(kb_store: Any | None = None):
    store = kb_store or default_kb_store

    async def retrieve_policy_node(state: ConversationState) -> dict:
        results = await store.search("退款 售后 政策 退货条件", top_k=3)
        evidence_texts = [f"【{r['title']}】：{r['content']}" for r in results]
        return {
            "evidence": "\n".join(evidence_texts),
            "citations": [{"title": r["title"]} for r in results],
        }

    return retrieve_policy_node
