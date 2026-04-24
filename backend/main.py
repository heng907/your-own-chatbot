from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.database import Base, engine
from backend.routers import chat, memory, conversations, mcp_bridge

"""
FastAPI app 的「總入口」。

負責：
1. 建立 FastAPI app 實例
2. 加 CORS middleware（允許瀏覽器跨來源請求）
3. 啟動時建立 DB 表（Base.metadata.create_all）
4. 註冊所有 router（/api/chat, /api/memory...）
5. 靜態檔案 serve（把 frontend/ 資料夾暴露出去）

"""

# 啟動時建立所有 DB 表
Base.metadata.create_all(bind=engine)

app = FastAPI(title="hw2 MyChatGPT Backend", version="1.0.0")

# ── CORS（必須在 include_router 之前）──
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 開發用，允許所有來源
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routes ──
app.include_router(chat.router, prefix="/api")
app.include_router(memory.router, prefix="/api")
app.include_router(conversations.router, prefix="/api")
app.include_router(mcp_bridge.router, prefix="/api")


@app.get("/api/health")
def health():
    return {"status": "ok"}


# ── 讓 FastAPI 直接 serve 前端（最簡單，無 CORS 問題）──
# 取消下面這行的註解後，只需要跑一個 server，
# 直接打開 http://localhost:8000 就能用。
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
