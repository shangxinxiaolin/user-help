from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import get_knowledge_repository
from app.db.repositories.kb import KnowledgeRepository
from app.kb.store import default_kb_store
from app.schemas.kb import (
    KnowledgeChunkRequest,
    KnowledgeChunkResponse,
    KnowledgeSearchRequest,
)


def create_kb_router() -> APIRouter:
    router = APIRouter()

    @router.get("/api/kb/chunks", response_model=list[KnowledgeChunkResponse])
    async def list_chunks(
        category: str | None = None,
        kb_repo: KnowledgeRepository | None = Depends(get_knowledge_repository),
    ) -> list[KnowledgeChunkResponse]:
        if kb_repo is not None:
            chunks = await kb_repo.list_chunks(category=category)
            return [
                KnowledgeChunkResponse(
                    id=c.id,
                    title=c.title,
                    content=c.content,
                    category=c.category,
                    is_key_clause=c.is_key_clause,
                )
                for c in chunks
            ]

        # In-memory store fallback
        mem_chunks = default_kb_store.list_all()
        if category:
            mem_chunks = [c for c in mem_chunks if c.get("category") == category]
        return [
            KnowledgeChunkResponse(
                id=c.get("id", 0),
                title=c["title"],
                content=c["content"],
                category=c.get("category", "通用"),
                is_key_clause=c.get("is_key_clause", False),
            )
            for c in mem_chunks
        ]

    @router.post("/api/kb/chunks", response_model=KnowledgeChunkResponse)
    async def add_chunk(
        request: KnowledgeChunkRequest,
        kb_repo: KnowledgeRepository | None = Depends(get_knowledge_repository),
    ) -> KnowledgeChunkResponse:
        chunk_id = 1
        if kb_repo is not None:
            chunk_id = await kb_repo.add_chunk(
                title=request.title,
                content=request.content,
                category=request.category,
                is_key_clause=request.is_key_clause,
            )

        default_kb_store.add_chunk({
            "id": chunk_id,
            "title": request.title,
            "content": request.content,
            "category": request.category,
            "is_key_clause": request.is_key_clause,
        })

        return KnowledgeChunkResponse(
            id=chunk_id,
            title=request.title,
            content=request.content,
            category=request.category,
            is_key_clause=request.is_key_clause,
        )

    @router.delete("/api/kb/chunks/{chunk_id}")
    async def delete_chunk(
        chunk_id: int,
        kb_repo: KnowledgeRepository | None = Depends(get_knowledge_repository),
    ) -> dict[str, bool]:
        if kb_repo is not None:
            deleted = await kb_repo.delete_chunk(chunk_id)
            if not deleted:
                raise HTTPException(status_code=404, detail="知识块不存在")
        return {"success": True}

    @router.post("/api/kb/search")
    async def search_kb(
        request: KnowledgeSearchRequest,
    ) -> list[dict]:
        return await default_kb_store.search(request.query, top_k=request.top_k)

    return router
