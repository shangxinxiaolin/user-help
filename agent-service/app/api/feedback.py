from fastapi import APIRouter, Depends

from app.api.dependencies import get_flywheel_repository
from app.db.repositories.flywheel import FlywheelRepository
from app.schemas.feedback import FeedbackRequest, FeedbackResponse


def create_feedback_router() -> APIRouter:
    router = APIRouter()

    @router.post("/api/feedback", response_model=FeedbackResponse)
    async def submit_feedback(
        request: FeedbackRequest,
        flywheel_repo: FlywheelRepository | None = Depends(get_flywheel_repository),
    ) -> FeedbackResponse:
        if not request.helpful and flywheel_repo is not None:
            # SPEC 1.5.2 & Design 08: unhelpful feedback enters the low_confidence_questions pool
            await flywheel_repo.record_low_confidence(
                raw_question=request.question,
                evidence_confidence=0.0,
                conversation_id=request.conversation_id,
                source="user_feedback",
            )

        return FeedbackResponse(success=True, message="反馈已成功记录，感谢您的评价！")

    return router
