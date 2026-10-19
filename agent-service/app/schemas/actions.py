from pydantic import BaseModel, Field


class ResumeRequest(BaseModel):
    conversation_id: int = Field(description="会话ID")
    user_id: str = Field(description="用户ID")
    confirmed: bool = Field(description="用户是否确认执行操作")
    message: str | None = Field(default=None, description="补充说明或确认回复")


class ResumeResponse(BaseModel):
    conversation_id: int
    answer: str | None = None
    status: str = "ok"
