from fastapi.testclient import TestClient


def test_kb_api_crud_and_search(api_app):
    app, _ = api_app

    with TestClient(app) as client:
        # 1. List chunks
        r1 = client.get("/api/kb/chunks")
        assert r1.status_code == 200
        assert len(r1.json()) >= 1

        # 2. Add chunk
        r2 = client.post(
            "/api/kb/chunks",
            json={
                "title": "测试知识条目",
                "content": "测试知识详细内容",
                "category": "测试",
                "is_key_clause": True,
            },
        )
        assert r2.status_code == 200
        chunk_id = r2.json()["id"]

        # 3. Search
        r3 = client.post(
            "/api/kb/search",
            json={"query": "测试知识", "top_k": 2},
        )
        assert r3.status_code == 200
        assert len(r3.json()) >= 1

        # 4. Delete
        r4 = client.delete(f"/api/kb/chunks/{chunk_id}")
        assert r4.status_code == 200
