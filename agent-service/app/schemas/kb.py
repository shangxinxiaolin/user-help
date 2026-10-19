from pydantic import BaseModel, Field


class KnowledgeChunkRequest(BaseModel):
    title: str = Field(description="知识块标题")
    content: str = Field(description="知识块详细内容")
    category: str = Field(default="通用", description="知识分类")
    is_key_clause: bool = Field(default=False, description="是否为核心关键条款")


class KnowledgeChunkResponse(BaseModel):
    id: int
    title: str
    content: str
    category: str
    is_key_clause: bool


class KnowledgeSearchRequest(BaseModel):
    query: str = Field(description="搜索关键词或问句")
    top_k: int = Field(default=4, description="返回条数")
