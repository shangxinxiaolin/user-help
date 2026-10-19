from fastapi import APIRouter, Depends, HTTPException, Request

from app.api.dependencies import get_conversation_repository
from app.db.repositories import ConversationRepository
from app.graph.answer import resolve_answer
from app.graph.runtime import ConversationNotFound, resume_turn
from app.schemas.actions import ResumeRequest, ResumeResponse


def create_actions_router() -> APIRouter:
    router = APIRouter()

    @router.post("/api/actions/resume", response_model=ResumeResponse)
    async def resume_action(
        request: ResumeRequest,
        raw_request: Request,
        repository: ConversationRepository = Depends(get_conversation_repository),
    ) -> ResumeResponse:
        if not request.user_id or not request.user_id.strip():
            raise HTTPException(status_code=422, detail="user_id is required")

        try:
            state = await resume_turn(
                graph=raw_request.app.state.graph,
                conversation_id=request.conversation_id,
                user_id=request.user_id,
                confirmed=request.confirmed,
                repository=repository,
                message=request.message,
            )
        except ConversationNotFound as exc:
            raise HTTPException(status_code=404, detail="会话不存在或不可访问") from exc

        return ResumeResponse(
            conversation_id=state.get("conversation_id", request.conversation_id),
            answer=resolve_answer(state),
            status="confirmed" if request.confirmed else "cancelled",
        )

    return router
