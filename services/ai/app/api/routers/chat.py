import json
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sse_starlette.sse import EventSourceResponse

from app.api.dependencies.auth import JWTPayload, get_current_user
from app.api.dependencies.rate_limiter import check_rate_limit
from app.api.schemas.chat import ChatRequest, ChatResponse
from app.application.chat.chat_service import ChatService

CurrentUser = Annotated[JWTPayload, Depends(get_current_user)]
RateLimit = Annotated[None, Depends(check_rate_limit)]

router = APIRouter(tags=["chat"])

chat_service = ChatService()


@router.post("/chat")
async def chat(
    request: ChatRequest,
    user: CurrentUser,
    _: RateLimit = None,
):
    conv_id = request.conversation_id or str(uuid.uuid4())

    if request.stream:
        async def event_generator():
            async for chunk in chat_service.stream_chat(
                user_id=user.sub,
                message=request.message,
                conversation_id=conv_id,
                workspace_id=request.workspace_id,
                repo_ids=request.repo_ids,
                history=None,
            ):
                if chunk.get("done"):
                    yield {"event": "done", "data": json.dumps(chunk)}
                else:
                    yield {"event": "chunk", "data": json.dumps(chunk)}

        return EventSourceResponse(event_generator())

    result = await chat_service.chat(
        user_id=user.sub,
        message=request.message,
        conversation_id=conv_id,
        workspace_id=request.workspace_id,
        repo_ids=request.repo_ids,
    )

    usage_info = result.get("usage") or {}
    return ChatResponse(
        conversation_id=conv_id,
        message_id=str(uuid.uuid4()),
        content=result.get("response", ""),
        model=usage_info.get("model", "unknown"),
        usage=usage_info,
        sources=result.get("sources"),
    )


@router.post("/completions")
async def completions(
    request: dict,
    user: CurrentUser,
    _: RateLimit = None,
):
    conv_id = str(uuid.uuid4())
    result = await chat_service.chat(
        user_id=user.sub,
        message=request.get("messages", [{}])[-1].get("content", ""),
        workspace_id=request.get("workspace_id", ""),
    )
    usage_info = result.get("usage") or {}
    return ChatResponse(
        conversation_id=conv_id,
        message_id=str(uuid.uuid4()),
        content=result.get("response", ""),
        model=usage_info.get("model", "unknown"),
        usage=usage_info,
        sources=result.get("sources"),
    )


@router.get("/models")
async def list_models(
    user: CurrentUser,
):
    return {
        "models": [
            {"id": "openrouter/auto", "provider": "openrouter", "free": True, "name": "Auto"},
            {"id": "openai/gpt-4o-mini", "provider": "openai", "free": True},
            {"id": "openai/gpt-4o", "provider": "openai", "free": False},
            {"id": "mistralai/mistral-large", "provider": "openrouter", "free": True},
            {"id": "anthropic/claude-3.5-sonnet", "provider": "anthropic", "free": False},
        ],
        "default": "openai/gpt-4o-mini",
    }
