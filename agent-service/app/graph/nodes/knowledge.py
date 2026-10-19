from typing import Any

from app.core.confidence import compute_evidence_confidence
from app.graph.state import ConversationState
from app.kb.store import default_kb_store


def make_retrieve_knowledge_node(kb_store: Any | None = None):
    store = kb_store or default_kb_store

    async def retrieve_knowledge_node(state: ConversationState) -> dict:
        query = state.get("resolved_query") or ""
        results = await store.search(query, top_k=4)

        evidence_texts = []
        citations = []
        for r in results:
            evidence_texts.append(f"【{r['title']}】：{r['content']}")
            citations.append({"title": r["title"], "score": r.get("score", 0.0)})

        return {
            "retrieved_snapshot": results,
            "evidence": "\n".join(evidence_texts),
            "citations": citations,
        }

    return retrieve_knowledge_node


def make_confidence_check_node(threshold: float = 0.26):
    async def confidence_check_node(state: ConversationState) -> dict:
        snapshot = state.get("retrieved_snapshot", [])
        conf_res = compute_evidence_confidence(snapshot, threshold=threshold)

        return {
            "evidence_confidence": conf_res["score"],
            "evidence_strong": conf_res["is_confident"],
            "trace": {"evidence_gate": conf_res},
        }

    return confidence_check_node
