from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import get_flywheel_repository
from app.db.repositories.flywheel import FlywheelRepository
from app.schemas.review import ReviewItemResponse, ReviewUpdateRequest


def create_review_router() -> APIRouter:
    router = APIRouter()

    @router.get("/api/review/queue", response_model=list[ReviewItemResponse])
    async def list_review_queue(
        status: str | None = None,
        flywheel_repo: FlywheelRepository | None = Depends(get_flywheel_repository),
    ) -> list[ReviewItemResponse]:
        if flywheel_repo is None:
            return []

        items = await flywheel_repo.list_review_queue(status=status)
        return [
            ReviewItemResponse(
                id=item.id,
                normalized_question=item.normalized_question,
                ai_suggested_answer=item.ai_suggested_answer,
                occurrence_count=item.occurrence_count,
                status=item.status,
                reviewed_answer=item.reviewed_answer,
                reviewed_by=item.reviewed_by,
                reviewed_at=item.reviewed_at,
                created_at=item.created_at,
            )
            for item in items
        ]

    @router.get("/api/review/queue/{review_id}", response_model=ReviewItemResponse)
    async def get_review_item(
        review_id: int,
        flywheel_repo: FlywheelRepository | None = Depends(get_flywheel_repository),
    ) -> ReviewItemResponse:
        if flywheel_repo is None:
            raise HTTPException(status_code=404, detail="条目不存在")

        item = await flywheel_repo.get_review_item(review_id)
        if item is None:
            raise HTTPException(status_code=404, detail="条目不存在")

        return ReviewItemResponse(
            id=item.id,
            normalized_question=item.normalized_question,
            ai_suggested_answer=item.ai_suggested_answer,
            occurrence_count=item.occurrence_count,
            status=item.status,
            reviewed_answer=item.reviewed_answer,
            reviewed_by=item.reviewed_by,
            reviewed_at=item.reviewed_at,
            created_at=item.created_at,
        )

    @router.post("/api/review/queue/{review_id}/status", response_model=ReviewItemResponse)
    async def update_review_status(
        review_id: int,
        request: ReviewUpdateRequest,
        flywheel_repo: FlywheelRepository | None = Depends(get_flywheel_repository),
    ) -> ReviewItemResponse:
        if flywheel_repo is None:
            raise HTTPException(status_code=404, detail="条目不存在")

        item = await flywheel_repo.update_review_status(
            review_id=review_id,
            status=request.status,
            reviewed_answer=request.reviewed_answer,
            reviewed_by=request.reviewed_by,
        )
        if item is None:
            raise HTTPException(status_code=404, detail="条目不存在")

        return ReviewItemResponse(
            id=item.id,
            normalized_question=item.normalized_question,
            ai_suggested_answer=item.ai_suggested_answer,
            occurrence_count=item.occurrence_count,
            status=item.status,
            reviewed_answer=item.reviewed_answer,
            reviewed_by=item.reviewed_by,
            reviewed_at=item.reviewed_at,
            created_at=item.created_at,
        )

    return router
