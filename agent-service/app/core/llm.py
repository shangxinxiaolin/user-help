from typing import Any

from langchain_openai import ChatOpenAI

from app.core.config import get_settings


def get_chat_model(
    streaming: bool = False,
) -> ChatOpenAI:
    settings = get_settings()

    if not settings.chat_api_key:
        raise RuntimeError(
            "CHAT_API_KEY is not configured"
        )

    if not settings.chat_model:
        raise RuntimeError(
            "CHAT_MODEL is not configured"
        )

    kwargs: dict[str, Any] = {
        "api_key": settings.chat_api_key,
        "model": settings.chat_model,
        "streaming": streaming,
    }

    if settings.chat_base_url:
        kwargs["base_url"] = settings.chat_base_url

    return ChatOpenAI(**kwargs)