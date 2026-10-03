from pydantic import BaseModel, Field

class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    conversation_id: int | None = None
    user_id: str | None = None


class ChatResponse(BaseModel):
    conversation_id: int | None = None
    answer: str
