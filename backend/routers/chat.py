import json
import uuid
import re
import logging
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Conversation, Message, LongTermMemory
from backend.schemas import ChatRequest
from backend.services.openai_client import get_client
from backend.services import model_router
from backend.services.tool_registry import TOOLS, execute_tool
from backend.services.mcp_manager import (
    get_mcp_tool_schemas_for_openai,
    parse_mcp_tool_name,
    call_tool as mcp_call_tool,
)

"""
主要 chat 端點：
1. 接收 ChatRequest
2. 判斷是否有圖片附件
3. Auto route 選模型
4. 注入 long-term memory 到 system prompt
5. 組裝 OpenAI messages（含 system + 歷史對話）
6. 組裝工具清單（內建工具 + MCP 工具）
7. 呼叫 OpenAI（支援 tool use 與 MCP）
8. 串流回傳 SSE
9. 儲存對話到 DB
"""


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["chat"])

# 自動提取記憶的正則
_MEMORY_PATTERNS = [
    (r"我叫([^\s，。,\.]{2,10})", "姓名"),
    (r"我是([^\s，。,\.]{2,20})", "身份"),
    (r"我喜歡([^\s，。,\.]{2,20})", "喜好"),
    (r"我偏好([^\s，。,\.]{2,20})", "偏好"),
    (r"記住([^，。,\.]{4,50})", "備忘"),
    (r"my name is ([^\s,\.]{2,20})", "姓名"),
    (r"i('m| am) ([^\s,\.]{2,20})", "身份"),
    (r"remember that ([^,\.]{4,60})", "備忘"),
]


def _extract_memories(text: str) -> list[tuple[str, str]]:
    """從訊息中自動提取值得記憶的資訊，回傳 [(key, value), ...]"""
    found = []
    lower = text.lower()
    for pattern, label in _MEMORY_PATTERNS:
        m = re.search(pattern, lower if pattern.islower() else text, re.IGNORECASE)
        if m:
            value = m.group(1).strip()
            key = f"auto_{label}_{value[:10]}"
            found.append((key, f"{label}：{value}"))
    return found


def _build_system_content(base_prompt: str, memories: list) -> str:
    """將 long-term memory 注入 system prompt"""
    if not memories:
        return base_prompt
    mem_text = "\n".join(f"- {m.key}: {m.value}" for m in memories)
    return f"{base_prompt}\n\n【使用者背景資訊】\n{mem_text}"


def _sse(data: dict) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


async def _chat_generator(req: ChatRequest, db: Session):
    client = get_client()

    # ── 1. 判斷是否有圖片 ──
    has_image = any(
        isinstance(m.content, list) and
        any(p.get("type") == "image_url" for p in m.content if isinstance(p, dict))
        for m in req.messages
    )

    # ── 2. 選模型 ──
    messages_dicts = [m.model_dump() for m in req.messages]
    if req.auto_route or req.model is None:
        model, reason = model_router.route(messages_dicts, has_image)
    else:
        model, reason = req.model, "手動選擇"

    yield _sse({"type": "model_selected", "model": model, "reason": reason})

    # ── 3. 注入 long-term memory ──
    memories = db.query(LongTermMemory).all()
    system_content = _build_system_content(req.system_prompt, memories)

    # o1/o3 用 developer role；其他用 system
    system_role = "developer" if model.startswith(("o1", "o3")) else "system"
    openai_messages = [{"role": system_role, "content": system_content}]

    # 加入對話歷史（限制輪數）
    history = messages_dicts
    if req.memory_turns > 0:
        history = history[-(req.memory_turns * 2):]
    openai_messages.extend(history)

    # ── 4. 組裝工具清單 ──
    tools = []
    if req.use_tools and not model.startswith(("o1", "o3")):
        tools = list(TOOLS)
        mcp_tools = await get_mcp_tool_schemas_for_openai()
        tools.extend(mcp_tools)

    # ── 5. OpenAI 呼叫（帶 tool loop）──
    full_text = ""
    MAX_TOOL_ROUNDS = 5

    for _ in range(MAX_TOOL_ROUNDS):
        kwargs = {
            "model": model,
            "messages": openai_messages,
            "stream": True,
        }
        if not model.startswith(("o1", "o3")):
            kwargs["temperature"] = req.temperature
            kwargs["top_p"] = req.top_p
            kwargs["max_tokens"] = req.max_tokens
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        # 先用非串流偵測 tool_calls（更簡單可靠）
        kwargs["stream"] = False
        response = await client.chat.completions.create(**kwargs)
        choice = response.choices[0]

        # 如果是 tool call
        if choice.finish_reason == "tool_calls":
            tool_calls = choice.message.tool_calls
            openai_messages.append(choice.message.model_dump(exclude_unset=True))

            for tc in tool_calls:
                fn_name = tc.function.name
                fn_args = json.loads(tc.function.arguments or "{}")

                # 執行工具
                mcp_parsed = parse_mcp_tool_name(fn_name)
                if mcp_parsed:
                    server, tool_name = mcp_parsed
                    result = await mcp_call_tool(server, tool_name, fn_args)
                    tool_type = f"mcp:{server}"
                else:
                    result = await execute_tool(fn_name, fn_args)
                    tool_type = "builtin"

                # 圖片生成特殊處理：emit image_generated event
                if result.startswith("IMAGE_URL:"):
                    image_url = result[len("IMAGE_URL:"):]
                    yield _sse({
                        "type": "image_generated",
                        "prompt": fn_args.get("prompt", ""),
                        "url": image_url,
                        "tool_type": tool_type,
                    })
                    # 給模型的 tool result 改為文字描述
                    result = f"圖片已生成，URL：{image_url}"
                else:
                    yield _sse({
                        "type": "tool_call",
                        "tool": fn_name,
                        "args": fn_args,
                        "result": result,
                        "tool_type": tool_type,
                    })

                openai_messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result,
                })
            continue  # 再跑一輪讓模型消化工具結果

        # 不是 tool call → 串流輸出最終回答
        kwargs["stream"] = True
        stream = await client.chat.completions.create(**kwargs)
        async for chunk in stream:
            delta = chunk.choices[0].delta.content if chunk.choices else None
            if delta:
                full_text += delta
                yield _sse({"type": "text", "content": delta})
        break

    # ── 6. 儲存對話到 DB ──
    try:
        conv_id = req.conversation_id or str(uuid.uuid4())
        conv = db.query(Conversation).filter(Conversation.id == conv_id).first()
        if not conv:
            # 用第一則 user 訊息當 title
            first_user = next(
                (m for m in req.messages if m.role == "user"), None
            )
            title = (
                (str(first_user.content)[:40] + "…")
                if first_user and len(str(first_user.content)) > 40
                else str(first_user.content) if first_user else "新對話"
            )
            conv = Conversation(id=conv_id, title=title)
            db.add(conv)

        # 儲存最後一則 user 訊息
        last_user = next(
            (m for m in reversed(req.messages) if m.role == "user"), None
        )
        if last_user:
            user_content = (
                last_user.content
                if isinstance(last_user.content, str)
                else json.dumps(last_user.content, ensure_ascii=False)
            )
            db.add(Message(
                conversation_id=conv_id,
                role="user",
                content=user_content,
            ))

        # 儲存 assistant 回答
        if full_text:
            db.add(Message(
                conversation_id=conv_id,
                role="assistant",
                content=full_text,
                model_used=model,
            ))

        # 自動提取記憶
        if full_text:
            for key, value in _extract_memories(full_text):
                existing = db.query(LongTermMemory).filter(
                    LongTermMemory.key == key
                ).first()
                if not existing:
                    db.add(LongTermMemory(key=key, value=value))

        db.commit()
        yield _sse({"type": "done", "conversation_id": conv_id})

    except Exception as e:
        logger.error(f"儲存對話失敗：{e}")
        yield _sse({"type": "done", "conversation_id": req.conversation_id or ""})


@router.post("")
async def chat(req: ChatRequest, db: Session = Depends(get_db)):
    return StreamingResponse(
        _chat_generator(req, db),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
