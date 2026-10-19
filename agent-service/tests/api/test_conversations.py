from fastapi.testclient import TestClient


def test_list_and_get_conversation_detail(api_app):
    app, _ = api_app

    with TestClient(app) as client:
        # Create a conversation by chatting
        r1 = client.post("/api/chat", json={"message": "请问发货时间", "user_id": "u1"})
        conv_id = r1.json()["conversation_id"]

        # List conversations
        r2 = client.get("/api/conversations?user_id=u1")
        assert r2.status_code == 200
        conv_list = r2.json()
        assert len(conv_list) >= 1
        assert any(c["id"] == conv_id for c in conv_list)

        # Get detail
        r3 = client.get(f"/api/conversations/{conv_id}?user_id=u1")
        assert r3.status_code == 200
        detail = r3.json()
        assert detail["id"] == conv_id
        assert len(detail["messages"]) >= 2
