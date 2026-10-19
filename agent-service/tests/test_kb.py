import pytest
from langchain_core.messages import AIMessage, HumanMessage

from app.kb.mining import compute_qa_fingerprint, mine_qa_from_messages
from app.kb.store import KnowledgeStore


@pytest.mark.asyncio
async def test_knowledge_store_search():
    store = KnowledgeStore()
    results = await store.search("七天无理由怎么退货", top_k=2)
    assert len(results) > 0
    assert any("七天" in r["title"] or "7" in r["content"] for r in results)


@pytest.mark.asyncio
async def test_mine_qa_from_messages_heuristic():
    messages = [
        HumanMessage(content="请问保修期是多久啊？"),
        AIMessage(content="您好，我们商城电子数码类商品享受1年全国联保服务。"),
    ]
    qa = await mine_qa_from_messages(messages)
    assert len(qa) >= 1
    assert "保修" in qa[0]["question"]
    assert "联保" in qa[0]["answer"]

    fp = compute_qa_fingerprint(qa[0]["question"], qa[0]["answer"])
    assert len(fp) == 32
