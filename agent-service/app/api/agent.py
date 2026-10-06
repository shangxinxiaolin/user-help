from fastapi import APIRouter, Depends, HTTPException, Request

from app.api.dependencies import get_conversation_repository
from app.db.repositories import ConversationRepository
from app.graph.answer import resolve_answer
from app.graph.runtime import ConversationNotFound, run_turn
from app.schemas.agent import AgentRequest, AgentResponse


def create_agent_router() -> APIRouter:
    router = APIRouter()

    @router.post(
        "/api/agent",
        response_model=AgentResponse,
    )
    async def run_agent(
        request: AgentRequest,
        raw_request: Request,
        repository: ConversationRepository = Depends(
            get_conversation_repository
        ),
    ) -> AgentResponse:
        if request.user_id is None or not request.user_id.strip():
            raise HTTPException(
                status_code=422,
                detail="user_id is required",
            )

        try:
            state = await run_turn(
                graph=raw_request.app.state.graph,
                message=request.message,
                conversation_id=request.conversation_id,
                user_id=request.user_id,
                repository=repository,
            )
        except ConversationNotFound as exc:
            raise HTTPException(
                status_code=404,
                detail="会话不存在或不可访问",
            ) from exc

        return AgentResponse(
            conversation_id=state.get("conversation_id"),
            answer=resolve_answer(state),
        )

    return router
