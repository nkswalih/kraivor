from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    workspace_id: str = Field(..., description="Workspace/project ID")
    message: str = Field(..., description="User message")
    conversation_id: str | None = Field(None, description="Existing conversation ID")
    repo_ids: list[str] | None = Field(None, description="Repository IDs to scope")
    agent_ids: list[str] | None = Field(None, description="Agent types to invoke")
    stream: bool = Field(True, description="Enable SSE streaming")
    model: str | None = Field(None, description="Preferred model override")
    mode: str = Field("normal", description="Chat mode: normal, web_search, research")


class ChatResponse(BaseModel):
    conversation_id: str
    message_id: str
    content: str
    model: str
    usage: dict | None = None
    sources: list[dict] | None = None


class SSEEvent(BaseModel):
    event: str
    data: str
