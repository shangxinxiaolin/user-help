import pytest
from langchain_core.messages import AIMessage, HumanMessage

from app.core.confidence import compute_evidence_confidence
from app.core.coref import resolve_reference, rule_based_coref
from app.core.intent import classify_intent, rule_based_classify
from app.core.memory import assemble_context_messages, estimate_tokens
from app.core.observability import ObservabilityCollector
from app.core.retrieval import hybrid_search
from app.core.taxonomy import classify_topics, rule_based_taxonomy


def test_rule_based_coref():
    history = [
        HumanMessage(content="我买了订单 1001"),
        AIMessage(content="好的，看到您的订单 1001 了"),
    ]
    resolved = rule_based_coref("那个订单到哪了", history)
    assert "1001" in resolved


def test_rule_based_intent():
    intent, conf, _ = rule_based_classify("我想退款")
    assert intent == "退款退货"
    assert conf >= 0.9

    intent2, _, _ = rule_based_classify("快递到哪了")
    assert intent2 == "物流"

    intent3, _, _ = rule_based_classify("转人工客服")
    assert intent3 == "人工"


def test_hybrid_search():
    docs = [
        {"title": "运费规则", "content": "实付满99元包邮，未满收取8元运费", "is_key_clause": True},
        {"title": "发票规则", "content": "确认收货后可开具增值税电子普通发票", "is_key_clause": False},
        {"title": "退换货规定", "content": "自签收之日起7天内支持无理由退货", "is_key_clause": True},
    ]
    results = hybrid_search("运费怎么算包邮吗", docs, top_k=2)
    assert len(results) == 2
    assert results[0]["title"] == "运费规则"
    assert results[0]["score"] > 0


def test_evidence_confidence_gate():
    # 1. High confidence evidence
    high_evidence = [
        {"score": 0.85, "is_key_clause": True},
        {"score": 0.40, "is_key_clause": False},
        {"score": 0.35, "is_key_clause": False},
    ]
    res_high = compute_evidence_confidence(high_evidence)
    assert res_high["is_confident"] is True
    assert res_high["score"] > 0.26

    # 2. Low confidence evidence
    low_evidence = [
        {"score": 0.15, "is_key_clause": False},
        {"score": 0.12, "is_key_clause": False},
    ]
    res_low = compute_evidence_confidence(low_evidence)
    assert res_low["is_confident"] is False
    assert res_low["score"] < 0.26


def test_memory_context_assembly():
    messages = [
        HumanMessage(content=f"用户提问 {i}") if i % 2 == 0 else AIMessage(content=f"这是第 {i} 条很长很长的客服回答内容，超过了五十个字！" * 3)
        for i in range(20)
    ]
    assembled = assemble_context_messages(
        messages=messages,
        system_prompt="人设提示词",
        summary="早期概要",
        recent_turns=3,
    )
    assert len(assembled) > 3
    # Check that older assistant message got truncated
    assert any("[已截短]" in getattr(m, "content", "") for m in assembled)


def test_observability():
    obs = ObservabilityCollector()
    obs.record_turn("物流", input_tokens=100, output_tokens=50)
    obs.record_turn("退款退货", input_tokens=200, output_tokens=80, interrupted=True)
    report = obs.get_cost_report()
    assert len(report) == 2
    metrics = obs.get_summary_metrics()
    assert metrics["total_turns"] == 2
    assert metrics["interrupt_rate"] == 0.5


def test_taxonomy():
    topics = rule_based_taxonomy("我要退货并且开电子发票")
    assert "退换货" in topics
    assert "发票开具" in topics
