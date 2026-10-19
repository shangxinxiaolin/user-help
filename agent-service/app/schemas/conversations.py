from datetime import datetime
from pydantic import BaseModel


class ConversationItem(BaseModel):
    id: int
    user_id: str
    status: str
    summary: str | None = None
    created_at: datetime


class MessageItem(BaseModel):
    id: int
    conversation_id: int
    role: str
    content: str | None = None
    tool_calls: list | None = None
    created_at: datetime


class ConversationDetailResponse(BaseModel):
    id: int
    user_id: str
    status: str
    summary: str | None = None
    messages: list[MessageItem]
