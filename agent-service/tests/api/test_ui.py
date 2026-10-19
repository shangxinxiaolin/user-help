from fastapi.testclient import TestClient


def test_ui_serves_html(api_app):
    app, _ = api_app

    with TestClient(app) as client:
        res = client.get("/")
        assert res.status_code == 200
        assert "灵犀客服" in res.text
        assert "app-layout" in res.text

        res_static = client.get("/static/css/style.css")
        assert res_static.status_code == 200
        assert "--primary" in res_static.text
