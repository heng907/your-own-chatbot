from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import LongTermMemory
from backend.schemas import MemoryItemIn, MemoryItemOut

router = APIRouter(prefix="/memory", tags=["memory"])

"""
讀取所有記憶
"""
@router.get("", response_model=list[MemoryItemOut])
def get_all_memories(db: Session = Depends(get_db)):
    return db.query(LongTermMemory).order_by(LongTermMemory.updated_at.desc()).all()

"""
新增或更新一筆記憶
"""
@router.post("", response_model=MemoryItemOut)
def upsert_memory(item: MemoryItemIn, db: Session = Depends(get_db)):
    existing = db.query(LongTermMemory).filter(LongTermMemory.key == item.key).first()
    if existing:
        existing.value = item.value
        db.commit()
        db.refresh(existing)
        return existing
    new_mem = LongTermMemory(key=item.key, value=item.value)
    db.add(new_mem)
    db.commit()
    db.refresh(new_mem)
    return new_mem

"""
刪除一筆記憶
"""
@router.delete("/{key}")
def delete_memory(key: str, db: Session = Depends(get_db)):
    mem = db.query(LongTermMemory).filter(LongTermMemory.key == key).first()
    if not mem:
        raise HTTPException(status_code=404, detail="記憶不存在")
    db.delete(mem)
    db.commit()
    return {"deleted": key}
