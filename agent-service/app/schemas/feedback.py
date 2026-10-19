from pydantic import BaseModel, Field


class FeedbackRequest(BaseModel):
    conversation_id: int = Field(description="会话ID")
    user_id: str = Field(description="用户ID")
    question: str = Field(description="用户提问")
    helpful: bool = Field(description="回答是否有帮助")
    reason: str | None = Field(default=None, description="未解决或不满意的原因")


class FeedbackResponse(BaseModel):
    success: bool = True
    message: str = "反馈已记录"
