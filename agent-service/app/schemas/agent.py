from pydantic import BaseModel, Field


class AgentRequest(BaseModel):
    message: str = Field(min_length=1)
    conversation_id: int | None = None
    user_id: str | None = None


class AgentResponse(BaseModel):
    conversation_id: int | None = None
    answer: str
