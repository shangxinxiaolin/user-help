from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse

from app.api.dependencies import get_conversation_repository
from app.db.repositories import ConversationRepository
from app.graph.answer import resolve_answer
from app.graph.runtime import ConversationNotFound, run_turn, stream_turn
from app.schemas.chat import ChatRequest, ChatResponse


def create_chat_router() -> APIRouter:
    router = APIRouter()

    @router.post("/api/chat", response_model=ChatResponse)
    async def chat(
        request: ChatRequest,
        raw_request: Request,
        repository: ConversationRepository = Depends(get_conversation_repository),
    ) -> ChatResponse:
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

        return ChatResponse(
            conversation_id=state.get("conversation_id"),
            answer=resolve_answer(state),
        )

    @router.post("/api/chat/stream")
    async def chat_stream(
        request: ChatRequest,
        raw_request: Request,
        repository: ConversationRepository = Depends(get_conversation_repository),
    ) -> StreamingResponse:
        if request.user_id is None or not request.user_id.strip():
            raise HTTPException(
                status_code=422,
                detail="user_id is required",
            )

        generator = stream_turn(
            graph=raw_request.app.state.graph,
            message=request.message,
            conversation_id=request.conversation_id,
            user_id=request.user_id,
            repository=repository,
        )
        return StreamingResponse(generator, media_type="text/event-stream")

    return router
