from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_
from backend.database import get_db
from backend.models import Conversation, Message
from backend.schemas import ConversationOut, MessageOut
from pydantic import BaseModel
from datetime import datetime


class SearchResultItem(BaseModel):
    conversation_id: str
    conversation_title: str
    message_id: int
    role: str
    content_snippet: str   # 含關鍵字的前後文（最多 120 字）
    created_at: datetime

    model_config = {"from_attributes": True}

router = APIRouter(prefix="/conversations", tags=["conversations"])

"""
列出所有對話（含標題、訊息數）
"""
@router.get("", response_model=list[ConversationOut])
def list_conversations(db: Session = Depends(get_db)):
    convs = db.query(Conversation).order_by(Conversation.updated_at.desc()).all()
    result = []
    for c in convs:
        msg_count = db.query(Message).filter(Message.conversation_id == c.id).count()
        result.append(
            ConversationOut(
                id=c.id,
                title=c.title,
                message_count=msg_count,
                created_at=c.created_at,
                updated_at=c.updated_at,
            )
        )
    return result

"""
搜尋對話內容（關鍵字搜尋 Message.content）
注意：靜態路徑 /search 必須在動態路徑 /{conversation_id} 之前定義，
否則 FastAPI 會把 "search" 當作 conversation_id 的值來匹配。
"""
@router.get("/search", response_model=list[SearchResultItem])
def search_conversations(q: str, db: Session = Depends(get_db)):
    if not q or len(q.strip()) < 1:
        return []

    keyword = q.strip()
    matches = (
        db.query(Message, Conversation)
        .join(Conversation, Message.conversation_id == Conversation.id)
        .filter(
            Message.role.in_(["user", "assistant"]),
            Message.content.ilike(f"%{keyword}%"),
        )
        .order_by(Message.created_at.desc())
        .limit(30)
        .all()
    )

    results = []
    for msg, conv in matches:
        # 取關鍵字附近的內容片段（前後各 50 字）
        content = msg.content
        idx = content.lower().find(keyword.lower())
        start = max(0, idx - 50)
        end = min(len(content), idx + len(keyword) + 50)
        snippet = ("…" if start > 0 else "") + content[start:end] + ("…" if end < len(content) else "")

        results.append(SearchResultItem(
            conversation_id=conv.id,
            conversation_title=conv.title,
            message_id=msg.id,
            role=msg.role,
            content_snippet=snippet,
            created_at=msg.created_at,
        ))

    return results


"""
取得某對話的所有訊息
"""
@router.get("/{conversation_id}/messages", response_model=list[MessageOut])
def get_messages(conversation_id: str, db: Session = Depends(get_db)):
    conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="對話不存在")
    return (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.created_at)
        .all()
    )


"""
刪除對話（cascade 刪除所有訊息）
"""
@router.delete("/{conversation_id}")
def delete_conversation(conversation_id: str, db: Session = Depends(get_db)):
    conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="對話不存在")
    db.delete(conv)
    db.commit()
    return {"deleted": conversation_id}
