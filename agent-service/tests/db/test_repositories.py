from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.db.base import Base
from app.db.repositories.audit import ToolAuditRepository
from app.db.repositories.flywheel import FlywheelRepository
from app.db.repositories.kb import KnowledgeRepository


@pytest.fixture
async def session_factory(tmp_path: Path):
    database_path = tmp_path / "repos-test.sqlite"
    engine: AsyncEngine = create_async_engine(f"sqlite+aiosqlite:///{database_path}")
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    yield factory
    await engine.dispose()


@pytest.mark.asyncio
async def test_tool_audit_repository(session_factory):
    repo = ToolAuditRepository(session_factory)
    log_id = await repo.record_audit(
        conversation_id=1,
        tool_call_id="call_1",
        tool_name="query_order",
        arguments={"order_id": "1001"},
        result_summary="order found",
        duration_ms=45,
    )
    assert log_id > 0
    logs = await repo.list_by_conversation(1)
    assert len(logs) == 1
    assert logs[0].tool_name == "query_order"
    assert logs[0].duration_ms == 45


@pytest.mark.asyncio
async def test_flywheel_repository(session_factory):
    repo = FlywheelRepository(session_factory)
    qid = await repo.record_low_confidence(
        raw_question="运费多少",
        evidence_confidence=0.15,
        conversation_id=1,
    )
    assert qid > 0

    unmerged = await repo.list_unmerged_questions()
    assert len(unmerged) == 1
    assert unmerged[0].raw_question == "运费多少"

    item = await repo.get_or_create_review_item("运费计算规则", "满99包邮")
    assert item.occurrence_count == 1

    item2 = await repo.get_or_create_review_item("运费计算规则")
    assert item2.occurrence_count == 2

    await repo.mark_question_matched(qid, item.id)
    unmerged_after = await repo.list_unmerged_questions()
    assert len(unmerged_after) == 0

    queue = await repo.list_review_queue()
    assert len(queue) == 1

    updated = await repo.update_review_status(item.id, "approved", "核准：满99包邮", "admin")
    assert updated is not None
    assert updated.status == "approved"
    assert updated.reviewed_by == "admin"


@pytest.mark.asyncio
async def test_knowledge_repository(session_factory):
    repo = KnowledgeRepository(session_factory)
    cid = await repo.add_chunk(
        title="运费规则",
        content="满99包邮，偏远地区除外",
        category="物流",
        is_key_clause=True,
    )
    assert cid > 0
    chunks = await repo.list_chunks(category="物流")
    assert len(chunks) == 1
    assert chunks[0].title == "运费规则"

    # QA extraction staging
    sid = await repo.add_qa_extraction("怎么退款", "去我的订单点击退款", "fp_123", conversation_id=1)
    assert sid > 0
    staging = await repo.list_qa_staging()
    assert len(staging) == 1
    await repo.update_qa_status(sid, "adopted")

    # Eval run
    rid = await repo.record_eval_run("hybrid_rerank", 0.95, 0.9, 0.92, 50)
    assert rid > 0

    # Faith case
    fid = await repo.record_faith_case("发票", "可以开电子发票", "证据缺失", "模型编造发票类型")
    assert fid > 0
