from types import SimpleNamespace

from app.core.llm import get_chat_model


def test_get_chat_model_uses_non_streaming_by_default(
    monkeypatch,
) -> None:
    settings = SimpleNamespace(
        chat_api_key="test-key",
        chat_model="deepseek-chat",
        chat_base_url="https://api.deepseek.com/v1",
    )

    monkeypatch.setattr(
        "app.core.llm.get_settings",
        lambda: settings,
    )

    model = get_chat_model()

    assert model.streaming is False
    assert model.model_name == "deepseek-chat"


def test_get_chat_model_enables_streaming(
    monkeypatch,
) -> None:
    settings = SimpleNamespace(
        chat_api_key="test-key",
        chat_model="deepseek-chat",
        chat_base_url="https://api.deepseek.com/v1",
    )

    monkeypatch.setattr(
        "app.core.llm.get_settings",
        lambda: settings,
    )

    model = get_chat_model(
        streaming=True
    )

    assert model.streaming is True
    assert model.model_name == "deepseek-chat"