from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.models.low_confidence import LowConfidenceQuestion
from app.db.models.review import ReviewQueueItem


class FlywheelRepository:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self._session_factory = session_factory

    async def record_low_confidence(
        self,
        raw_question: str,
        evidence_confidence: float = 0.0,
        conversation_id: int | None = None,
        intent: str | None = None,
        source: str = "evidence_confidence",
    ) -> int:
        async with self._session_factory() as session:
            record = LowConfidenceQuestion(
                conversation_id=conversation_id,
                raw_question=raw_question,
                intent=intent,
                evidence_confidence=evidence_confidence,
                source=source,
            )
            session.add(record)
            await session.flush()
            rec_id = record.id
            await session.commit()
            return rec_id

    async def list_unmerged_questions(
        self,
        limit: int = 100,
    ) -> list[LowConfidenceQuestion]:
        async with self._session_factory() as session:
            result = await session.execute(
                select(LowConfidenceQuestion)
                .where(LowConfidenceQuestion.matched_review_id.is_(None))
                .order_by(LowConfidenceQuestion.id)
                .limit(limit)
            )
            return list(result.scalars())

    async def get_or_create_review_item(
        self,
        normalized_question: str,
        ai_suggested_answer: str | None = None,
    ) -> ReviewQueueItem:
        async with self._session_factory() as session:
            item = await session.scalar(
                select(ReviewQueueItem).where(
                    ReviewQueueItem.normalized_question == normalized_question
                )
            )
            if item is not None:
                item.occurrence_count += 1
                if ai_suggested_answer and not item.ai_suggested_answer:
                    item.ai_suggested_answer = ai_suggested_answer
                await session.commit()
                return item

            new_item = ReviewQueueItem(
                normalized_question=normalized_question,
                ai_suggested_answer=ai_suggested_answer,
                occurrence_count=1,
                status="pending",
            )
            session.add(new_item)
            await session.flush()
            await session.commit()
            return new_item

    async def mark_question_matched(
        self,
        question_id: int,
        review_id: int,
    ) -> None:
        async with self._session_factory() as session:
            q = await session.get(LowConfidenceQuestion, question_id)
            if q is not None:
                q.matched_review_id = review_id
                await session.commit()

    async def list_review_queue(
        self,
        status: str | None = None,
        limit: int = 50,
    ) -> list[ReviewQueueItem]:
        async with self._session_factory() as session:
            query = select(ReviewQueueItem)
            if status:
                query = query.where(ReviewQueueItem.status == status)
            query = query.order_by(ReviewQueueItem.occurrence_count.desc(), ReviewQueueItem.id.desc()).limit(limit)
            result = await session.execute(query)
            return list(result.scalars())

    async def get_review_item(
        self,
        review_id: int,
    ) -> ReviewQueueItem | None:
        async with self._session_factory() as session:
            return await session.get(ReviewQueueItem, review_id)

    async def update_review_status(
        self,
        review_id: int,
        status: str,
        reviewed_answer: str | None = None,
        reviewed_by: str | None = None,
    ) -> ReviewQueueItem | None:
        async with self._session_factory() as session:
            item = await session.get(ReviewQueueItem, review_id)
            if item is not None:
                item.status = status
                if reviewed_answer is not None:
                    item.reviewed_answer = reviewed_answer
                if reviewed_by is not None:
                    item.reviewed_by = reviewed_by
                item.reviewed_at = datetime.now(timezone.utc)
                await session.commit()
            return item
