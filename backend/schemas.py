from datetime import datetime
from typing import Any
from pydantic import BaseModel

"""
定義「資料傳輸的格式」（Pydantic）。
規定前端送來的 JSON 長什麼樣子、後端回傳的 JSON 長什麼樣子。
"""
# ── 訊息內容（支援純文字 or 多模態 list）──

class ImageUrlDetail(BaseModel):
    url: str                          # base64 data URL 或一般 URL
    detail: str = "auto"


class ImagePart(BaseModel):
    type: str = "image_url"
    image_url: ImageUrlDetail


class TextPart(BaseModel):
    type: str = "text"
    text: str


class MessageIn(BaseModel):
    role: str                         # user / assistant / system / tool
    content: str | list[dict]         # 純文字 或 multimodal parts


# ── Chat Request / Response ──

class ChatRequest(BaseModel):
    messages: list[MessageIn]
    model: str | None = None          # None = 由後端 auto route
    auto_route: bool = True
    use_tools: bool = True
    conversation_id: str | None = None
    system_prompt: str = "你是一個有幫助的 AI 助理，請用繁體中文回答，除非使用者要求其他語言。"
    temperature: float = 0.7
    max_tokens: int = 2048
    top_p: float = 1.0
    memory_turns: int = 6


# ── Memory ──

class MemoryItemIn(BaseModel):
    key: str
    value: str


class MemoryItemOut(BaseModel):
    id: int
    key: str
    value: str
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Conversations ──

class ConversationOut(BaseModel):
    id: str
    title: str
    message_count: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MessageOut(BaseModel):
    id: int
    role: str
    content: str
    model_used: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── MCP ──

class McpCallRequest(BaseModel):
    server: str                       # "fetch" 或 "sqlite"
    tool_name: str
    arguments: dict[str, Any] = {}


class McpToolOut(BaseModel):
    server: str
    name: str
    description: str
    input_schema: dict[str, Any]
