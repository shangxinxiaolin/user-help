from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.models.eval_run import EvalRun
from app.db.models.extraction import QAExtractionStaging
from app.db.models.faith_case import FaithCase
from app.db.models.knowledge import KnowledgeChunk


class KnowledgeRepository:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self._session_factory = session_factory

    async def add_chunk(
        self,
        title: str,
        content: str,
        category: str = "通用",
        is_key_clause: bool = False,
        source: str = "manual",
        milvus_id: str | None = None,
    ) -> int:
        async with self._session_factory() as session:
            chunk = KnowledgeChunk(
                title=title,
                content=content,
                category=category,
                is_key_clause=is_key_clause,
                source=source,
                milvus_id=milvus_id,
            )
            session.add(chunk)
            await session.flush()
            chunk_id = chunk.id
            await session.commit()
            return chunk_id

    async def list_chunks(
        self,
        category: str | None = None,
        limit: int = 100,
    ) -> list[KnowledgeChunk]:
        async with self._session_factory() as session:
            query = select(KnowledgeChunk)
            if category:
                query = query.where(KnowledgeChunk.category == category)
            query = query.order_by(KnowledgeChunk.id.desc()).limit(limit)
            result = await session.execute(query)
            return list(result.scalars())

    async def get_chunk(
        self,
        chunk_id: int,
    ) -> KnowledgeChunk | None:
        async with self._session_factory() as session:
            return await session.get(KnowledgeChunk, chunk_id)

    async def delete_chunk(
        self,
        chunk_id: int,
    ) -> bool:
        async with self._session_factory() as session:
            chunk = await session.get(KnowledgeChunk, chunk_id)
            if chunk is not None:
                await session.delete(chunk)
                await session.commit()
                return True
            return False

    async def add_qa_extraction(
        self,
        question: str,
        answer: str,
        fingerprint: str,
        conversation_id: int | None = None,
    ) -> int:
        async with self._session_factory() as session:
            staging = QAExtractionStaging(
                conversation_id=conversation_id,
                question=question,
                answer=answer,
                fingerprint=fingerprint,
                status="extracted",
            )
            session.add(staging)
            await session.flush()
            sid = staging.id
            await session.commit()
            return sid

    async def list_qa_staging(
        self,
        status: str = "extracted",
        limit: int = 100,
    ) -> list[QAExtractionStaging]:
        async with self._session_factory() as session:
            result = await session.execute(
                select(QAExtractionStaging)
                .where(QAExtractionStaging.status == status)
                .order_by(QAExtractionStaging.id.desc())
                .limit(limit)
            )
            return list(result.scalars())

    async def update_qa_status(
        self,
        staging_id: int,
        status: str,
    ) -> None:
        async with self._session_factory() as session:
            staging = await session.get(QAExtractionStaging, staging_id)
            if staging is not None:
                staging.status = status
                await session.commit()

    async def record_faith_case(
        self,
        question: str,
        answer: str,
        evidence: str | None = None,
        judge_reason: str | None = None,
    ) -> int:
        async with self._session_factory() as session:
            case = FaithCase(
                question=question,
                evidence=evidence,
                answer=answer,
                judge_reason=judge_reason,
            )
            session.add(case)
            await session.flush()
            cid = case.id
            await session.commit()
            return cid

    async def record_eval_run(
        self,
        strategy: str,
        recall_rate: float,
        coverage_rate: float,
        faithful_rate: float,
        total_cases: int,
    ) -> int:
        async with self._session_factory() as session:
            run = EvalRun(
                strategy=strategy,
                recall_rate=recall_rate,
                coverage_rate=coverage_rate,
                faithful_rate=faithful_rate,
                total_cases=total_cases,
            )
            session.add(run)
            await session.flush()
            rid = run.id
            await session.commit()
            return rid
