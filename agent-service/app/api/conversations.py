from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.dependencies import get_conversation_repository
from app.db.repositories import ConversationRepository
from app.schemas.conversations import (
    ConversationDetailResponse,
    ConversationItem,
    MessageItem,
)


def create_conversations_router() -> APIRouter:
    router = APIRouter()

    @router.get("/api/conversations", response_model=list[ConversationItem])
    async def list_conversations(
        user_id: str = Query(description="用户ID"),
        repository: ConversationRepository = Depends(get_conversation_repository),
    ) -> list[ConversationItem]:
        if not user_id.strip():
            raise HTTPException(status_code=422, detail="user_id is required")

        convs = await repository.list_conversations_for_user(user_id)
        return [
            ConversationItem(
                id=c.id,
                user_id=c.user_id,
                status=c.status,
                summary=c.summary,
                created_at=c.created_at,
            )
            for c in convs
        ]

    @router.get(
        "/api/conversations/{conversation_id}",
        response_model=ConversationDetailResponse,
    )
    async def get_conversation_detail(
        conversation_id: int,
        user_id: str = Query(description="用户ID"),
        repository: ConversationRepository = Depends(get_conversation_repository),
    ) -> ConversationDetailResponse:
        conv = await repository.get_conversation_for_user(conversation_id, user_id)
        if conv is None:
            raise HTTPException(status_code=404, detail="会话不存在或不可访问")

        msgs = await repository.list_messages(conversation_id)
        return ConversationDetailResponse(
            id=conv.id,
            user_id=conv.user_id,
            status=conv.status,
            summary=conv.summary,
            messages=[
                MessageItem(
                    id=m.id,
                    conversation_id=m.conversation_id,
                    role=m.role,
                    content=m.content,
                    tool_calls=m.tool_calls,
                    created_at=m.created_at,
                )
                for m in msgs
            ],
        )

    return router
