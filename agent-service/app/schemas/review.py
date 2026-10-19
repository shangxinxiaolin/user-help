from datetime import datetime
from pydantic import BaseModel, Field


class ReviewItemResponse(BaseModel):
    id: int
    normalized_question: str
    ai_suggested_answer: str | None = None
    occurrence_count: int
    status: str
    reviewed_answer: str | None = None
    reviewed_by: str | None = None
    reviewed_at: datetime | None = None
    created_at: datetime


class ReviewUpdateRequest(BaseModel):
    status: str = Field(description="审核状态: approved / rejected")
    reviewed_answer: str | None = Field(default=None, description="核准后的正式答案")
    reviewed_by: str = Field(default="admin", description="审核人")
